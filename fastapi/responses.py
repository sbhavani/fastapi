import asyncio
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi.exceptions import FastAPIDeprecationWarning
from starlette.responses import FileResponse as FileResponse  # noqa
from starlette.responses import HTMLResponse as HTMLResponse  # noqa
from starlette.responses import JSONResponse as JSONResponse  # noqa
from starlette.responses import PlainTextResponse as PlainTextResponse  # noqa
from starlette.responses import RedirectResponse as RedirectResponse  # noqa
from starlette.responses import Response as Response  # noqa
from starlette.responses import StreamingResponse as StreamingResponse  # noqa
from typing_extensions import deprecated

try:
    import ujson
except ImportError:  # pragma: nocover
    ujson = None  # type: ignore


try:
    import orjson
except ImportError:  # pragma: nocover
    orjson = None  # type: ignore


@deprecated(
    "UJSONResponse is deprecated, FastAPI now serializes data directly to JSON "
    "bytes via Pydantic when a return type or response model is set, which is "
    "faster and doesn't need a custom response class. Read more in the FastAPI "
    "docs: https://fastapi.tiangolo.com/advanced/custom-response/#orjson-or-response-model "
    "and https://fastapi.tiangolo.com/tutorial/response-model/",
    category=FastAPIDeprecationWarning,
    stacklevel=2,
)
class UJSONResponse(JSONResponse):
    """JSON response using the ujson library to serialize data to JSON.

    **Deprecated**: `UJSONResponse` is deprecated. FastAPI now serializes data
    directly to JSON bytes via Pydantic when a return type or response model is
    set, which is faster and doesn't need a custom response class.

    Read more in the
    [FastAPI docs for Custom Response](https://fastapi.tiangolo.com/advanced/custom-response/#orjson-or-response-model)
    and the
    [FastAPI docs for Response Model](https://fastapi.tiangolo.com/tutorial/response-model/).

    **Note**: `ujson` is not included with FastAPI and must be installed
    separately, e.g. `pip install ujson`.
    """

    def render(self, content: Any) -> bytes:
        assert ujson is not None, "ujson must be installed to use UJSONResponse"
        return ujson.dumps(content, ensure_ascii=False).encode("utf-8")


@deprecated(
    "ORJSONResponse is deprecated, FastAPI now serializes data directly to JSON "
    "bytes via Pydantic when a return type or response model is set, which is "
    "faster and doesn't need a custom response class. Read more in the FastAPI "
    "docs: https://fastapi.tiangolo.com/advanced/custom-response/#orjson-or-response-model "
    "and https://fastapi.tiangolo.com/tutorial/response-model/",
    category=FastAPIDeprecationWarning,
    stacklevel=2,
)
class ORJSONResponse(JSONResponse):
    """JSON response using the orjson library to serialize data to JSON.

    **Deprecated**: `ORJSONResponse` is deprecated. FastAPI now serializes data
    directly to JSON bytes via Pydantic when a return type or response model is
    set, which is faster and doesn't need a custom response class.

    Read more in the
    [FastAPI docs for Custom Response](https://fastapi.tiangolo.com/advanced/custom-response/#orjson-or-response-model)
    and the
    [FastAPI docs for Response Model](https://fastapi.tiangolo.com/tutorial/response-model/).

    **Note**: `orjson` is not included with FastAPI and must be installed
    separately, e.g. `pip install orjson`.
    """

    def render(self, content: Any) -> bytes:
        assert orjson is not None, "orjson must be installed to use ORJSONResponse"
        return orjson.dumps(
            content, option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY
        )


@dataclass
class SSEEvent:
    """Server-Sent Event data structure.

    Args:
        data: The event data payload. If not a string, will be converted to string.
        event: The event type identifier (optional).
        id: The event identifier for Last-Event-ID header on reconnection (optional).
        retry: Reconnection interval in milliseconds (optional).
        comment: A comment line (starts with colon, used for keep-alive) (optional).
    """

    data: Any
    event: Optional[str] = None
    id: Optional[str] = None
    retry: Optional[int] = None
    comment: Optional[str] = None

    def encode(self) -> bytes:
        """Encode the SSE event according to the SSE specification."""
        lines = []

        if self.comment:
            lines.append(f":{self.comment}")

        if self.event is not None:
            lines.append(f"event: {self.event}")

        if self.id is not None:
            lines.append(f"id: {self.id}")

        if self.retry is not None:
            lines.append(f"retry: {self.retry}")

        # Data can be multiline - split with separate data: lines
        data_str = str(self.data)
        for line in data_str.split("\n"):
            lines.append(f"data: {line}")

        # End with double newline
        return "\n".join(lines).encode("utf-8") + b"\n\n"


class SSEResponse(StreamingResponse):
    """Server-Sent Events response.

    A streaming response that sends events in SSE format according to the
    W3C Eventsource specification.

    Args:
        content: An async generator yielding SSEEvent objects.
        status_code: HTTP status code (default: 200).
        headers: Additional HTTP headers.
        media_type: Media type (default: text/event-stream).
        background: Background task to run after response completes.

    Example:
        ```python
        from fastapi import FastAPI
        from fastapi.responses import SSEResponse, SSEEvent

        app = FastAPI()

        async def event_generator():
            for i in range(10):
                yield SSEEvent(data=f"message {i}")
                await asyncio.sleep(1)

        @app.get("/events")
        async def main():
            return SSEResponse(event_generator())
        ```
    """

    def __init__(
        self,
        content: AsyncGenerator["SSEEvent", None],
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: str = "text/event-stream",
        background: Optional[Any] = None,
    ) -> None:
        # Set default headers for SSE
        default_headers = {"Cache-Control": "no-cache", "Connection": "keep-alive"}
        if headers:
            default_headers.update(headers)

        super().__init__(
            content=self._stream_events(content),
            status_code=status_code,
            headers=default_headers,
            media_type=media_type,
            background=background,
        )

    async def _stream_events(
        self, content: AsyncGenerator["SSEEvent", None]
    ) -> AsyncGenerator[bytes, None]:
        """Stream SSE events with proper disconnect handling and cleanup."""
        try:
            async for event in content:
                yield event.encode()
        except asyncio.CancelledError:
            # Client disconnected - cleanup will happen in finally
            raise
        finally:
            # Ensure generator is properly closed
            if hasattr(content, "aclose"):
                await content.aclose()


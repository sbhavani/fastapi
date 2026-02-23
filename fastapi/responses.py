from typing import Any, AsyncIterable, Optional, Union

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


import json
from dataclasses import dataclass
from enum import Enum


class SSERetryMode(str, Enum):
    """Enum for SSE retry modes."""

    NONE = "none"
    ONCE = "once"
    ALWAYS = "always"


@dataclass
class SSEEvent:
    """Server-Sent Event data class.

    Represents a single Server-Sent Event to be sent to the client.

    Attributes:
        data: The event payload. Can be a string or any object serializable to JSON.
        event: Optional event type identifier. Used by clients to filter events.
        id: Optional unique event identifier. Enables client resumption with Last-Event-ID.
        retry: Optional retry interval in milliseconds. Sent to client for reconnection timing.
    """

    data: Union[str, Any]
    event: Optional[str] = None
    id: Optional[str] = None
    retry: Optional[int] = None

    def __post_init__(self) -> None:
        """Validate the event fields after initialization."""
        if self.retry is not None and self.retry <= 0:
            raise ValueError("retry must be a positive integer")
        if self.event is not None and not self.event:
            raise ValueError("event must be a non-empty string")

    def encode(self) -> bytes:
        """Encode the event to bytes in SSE format.

        Returns:
            The encoded event as bytes.
        """
        lines: list[str] = []

        if self.event is not None:
            lines.append(f"event: {self.event}")

        if self.id is not None:
            lines.append(f"id: {self.id}")

        # Encode data - can be string or any JSON-serializable object
        if isinstance(self.data, str):
            for line in self.data.split("\n"):
                lines.append(f"data: {line}")
        else:
            # Serialize non-string data as JSON
            json_data = json.dumps(self.data)
            for line in json_data.split("\n"):
                lines.append(f"data: {line}")

        if self.retry is not None:
            lines.append(f"retry: {self.retry}")

        # SSE events must be separated by double newlines
        return ("\n".join(lines) + "\n\n").encode("utf-8")


class SSEResponse(StreamingResponse):
    """Server-Sent Events response class.

    A streaming response that sends events in Server-Sent Events (SSE) format.
    This enables server-to-client real-time communication without WebSockets.

    The response automatically:
    - Sets Content-Type to text/event-stream
    - Sets Cache-Control to prevent caching
    - Formats events according to SSE specification
    - Handles client disconnection gracefully

    Example:
        ```python
        from fastapi import FastAPI
        from fastapi.responses import SSEResponse
        import asyncio

        app = FastAPI()

        async def event_generator():
            for i in range(10):
                yield {"data": {"message": f"Event {i}"}}
                await asyncio.sleep(1)

        @app.get("/events")
        async def main():
            return SSEResponse(event_generator())
        ```
    """

    retry: Optional[int] = None

    def __init__(
        self,
        content: AsyncIterable[Any],
        status_code: int = 200,
        headers: Optional[dict[str, str]] = None,
        media_type: Optional[str] = "text/event-stream",
        retry: Optional[int] = None,
    ) -> None:
        """Initialize an SSEResponse.

        Args:
            content: An async iterable yielding event data. Each item can be a dict
                with 'data', 'event', 'id', and/or 'retry' keys, or an SSEEvent object.
            status_code: The HTTP status code (default: 200).
            headers: Additional headers to include in the response.
            media_type: The media type (default: text/event-stream).
            retry: Default retry interval in milliseconds for reconnection.
        """
        self.retry = retry

        # Build SSE headers
        sse_headers: dict[str, str] = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
        if headers:
            sse_headers.update(headers)

        super().__init__(
            content=self._stream_events(content),
            status_code=status_code,
            headers=sse_headers,
            media_type=media_type,
        )

    async def _stream_events(
        self, content: Any
    ) -> AsyncIterable[bytes]:
        """Stream events in SSE format.

        Args:
            content: The async iterable or iterable of event data.

        Yields:
            Encoded SSE events.
        """
        import inspect

        # Send retry in the initial response if specified
        if self.retry is not None:
            yield f"retry: {self.retry}\n\n".encode("utf-8")

        # Check if content is an async iterable
        if inspect.isasyncgen(content):
            # It's an async generator
            async for event_data in content:
                # Handle both dict and SSEEvent objects
                if isinstance(event_data, SSEEvent):
                    yield event_data.encode()
                elif isinstance(event_data, dict):
                    # Convert dict to SSEEvent for encoding
                    sse_event = SSEEvent(
                        data=event_data.get("data", ""),
                        event=event_data.get("event"),
                        id=event_data.get("id"),
                        retry=event_data.get("retry"),
                    )
                    yield sse_event.encode()
                else:
                    # Raw data
                    sse_event = SSEEvent(data=event_data)
                    yield sse_event.encode()
        elif inspect.iscoroutinefunction(content):
            # It's an async function that returns an async generator
            content = await content()
            async for event_data in content:
                if isinstance(event_data, SSEEvent):
                    yield event_data.encode()
                elif isinstance(event_data, dict):
                    sse_event = SSEEvent(
                        data=event_data.get("data", ""),
                        event=event_data.get("event"),
                        id=event_data.get("id"),
                        retry=event_data.get("retry"),
                    )
                    yield sse_event.encode()
                else:
                    sse_event = SSEEvent(data=event_data)
                    yield sse_event.encode()
        else:
            # It's a regular iterable
            for event_data in content:
                # Handle both dict and SSEEvent objects
                if isinstance(event_data, SSEEvent):
                    yield event_data.encode()
                elif isinstance(event_data, dict):
                    # Convert dict to SSEEvent for encoding
                    sse_event = SSEEvent(
                        data=event_data.get("data", ""),
                        event=event_data.get("event"),
                        id=event_data.get("id"),
                        retry=event_data.get("retry"),
                    )
                    yield sse_event.encode()
                else:
                    # Raw data
                    sse_event = SSEEvent(data=event_data)
                    yield sse_event.encode()

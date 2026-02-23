from dataclasses import dataclass
from typing import Any
from typing import AsyncIterator
from typing import Iterator

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


def sse_event(
    data: str | Any,
    *,
    event: str | None = None,
    id: str | int | None = None,
    retry: int | None = None,
) -> str:
    """Create a formatted Server-Sent Events (SSE) string.

    Args:
        data: Event payload. Can be a string or any JSON-serializable object.
        event: Optional event type for client-side handling (e.g., "message", "update").
        id: Optional unique event identifier for reconnection tracking.
        retry: Optional reconnection time in milliseconds.

    Returns:
        A formatted SSE string with newlines, ready to be encoded to bytes.

    Example:
        >>> sse_event(data="Hello")
        'data: Hello\\n\\n'
        >>> sse_event(data={"status": "ok"})
        'data: {"status": "ok"}\\n\\n'
        >>> sse_event(data="Update", event="update", id=1, retry=5000)
        'id: 1\\nevent: update\\ndata: Update\\nretry: 5000\\n\\n'
    """
    import json

    lines = []

    # Field order: id, event, data, retry (per SSE spec)
    if id is not None:
        lines.append(f"id: {id}")

    if event is not None:
        lines.append(f"event: {event}")

    # Format data - convert to JSON if not string
    if not isinstance(data, str):
        data = json.dumps(data)

    # Handle multi-line data by prefixing each line with "data:"
    for line in data.split("\n"):
        lines.append(f"data: {line}")

    if retry is not None:
        lines.append(f"retry: {retry}")

    # End with double newline
    lines.append("")

    return "\n".join(lines)


@dataclass
class SSEEvent:
    """A Server-Sent Event data class.

    Attributes:
        data: Event payload (string or JSON-serializable).
        event: Optional event type for client-side handling.
        id: Optional unique event identifier for reconnection.
        retry: Optional reconnection time in milliseconds.

    Example:
        >>> event = SSEEvent(data="Hello", event="message")
        >>> str(event)
        'event: message\\ndata: Hello\\n\\n'
    """

    data: str | Any
    event: str | None = None
    id: str | int | None = None
    retry: int | None = None

    def __str__(self) -> str:
        return sse_event(
            data=self.data,
            event=self.event,
            id=self.id,
            retry=self.retry,
        )

    def __bytes__(self) -> bytes:
        return str(self).encode("utf-8")


class SSEResponse(StreamingResponse):
    """Server-Sent Events (SSE) streaming response.

    A streaming response that sends events to the client using the SSE protocol.
    Automatically sets the Content-Type to "text/event-stream".

    Args:
        content: An async or sync iterator yielding SSE event data (strings or bytes).
        status_code: HTTP status code (default 200).
        headers: Additional response headers.
        media_type: Content-Type header value (default "text/event-stream").
        background: Background tasks to run after response is sent.

    Example:
        >>> async def event_generator():
        ...     for i in range(5):
        ...         yield sse_event(data=f"Event {i}")
        >>> return SSEResponse(event_generator())
    """

    def __init__(
        self,
        content: AsyncIterator[bytes] | Iterator[bytes],
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        media_type: str = "text/event-stream",
        background: Any = None,
    ) -> None:
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )

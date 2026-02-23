from typing import Any, AsyncGenerator, AsyncIterator, Generator, Iterator

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


def _format_sse_event(
    event: dict[str, Any],
    encoding: str = "utf-8",
) -> bytes:
    """Format a single event dictionary as SSE format.

    Args:
        event: A dictionary containing the event data. Supported keys:
            - `event`: The event type (string)
            - `data`: The event data (will be converted to string)
            - `id`: The event ID (integer or string)
            - `retry`: Reconnection time in milliseconds (integer)
        encoding: The character encoding to use (default: utf-8)

    Returns:
        The formatted SSE event as bytes.
    """
    lines: list[str] = []

    if "event" in event:
        lines.append(f"event: {event['event']}")

    if "id" in event:
        lines.append(f"id: {event['id']}")

    if "retry" in event:
        lines.append(f"retry: {event['retry']}")

    if "data" in event:
        data = event["data"]
        if isinstance(data, (list, tuple)):
            for item in data:
                for line in str(item).split("\n"):
                    lines.append(f"data: {line}")
        else:
            for line in str(data).split("\n"):
                lines.append(f"data: {line}")

    # Add empty line to terminate the event (required by SSE spec)
    # The event ends with a blank line (i.e., two CRLF sequences)
    lines.append("")

    # Join with CRLF as per SSE spec, then add final CRLF for the blank line
    return ("\r\n".join(lines) + "\r\n").encode(encoding)


def _is_async(obj: Any) -> bool:
    """Check if an object is an async iterator/generator."""
    import inspect

    # Check for async generator object (already created)
    # An async generator has __aiter__ but may also have __iter__
    # We need to check for __anext__ to distinguish from sync iterators
    if hasattr(obj, "__anext__"):
        return True

    # Check for async generator function - inspect is more reliable
    if inspect.isasyncgenfunction(obj):
        return True

    # Check for coroutine function
    if inspect.iscoroutinefunction(obj):
        return True

    return False


def _wrap_sse_content(
    content: Any,
    retry: int | None = None,
) -> AsyncGenerator[bytes, None]:
    """Wrap content to format events as SSE.

    This handles both sync and async iterators that yield event dictionaries.
    """
    # Check if content is async
    is_async = _is_async(content)

    if is_async:
        return _wrap_async_sse_content(content, retry)
    else:
        return _wrap_sync_sse_content(content, retry)


async def _wrap_async_sse_content(
    content: AsyncIterator[Any],
    retry: int | None,
) -> AsyncGenerator[bytes, None]:
    """Wrap async content for SSE."""
    async for event in content:
        # Check if it's already bytes (pre-formatted)
        if isinstance(event, bytes):
            yield event
        # Check if it's a string
        elif isinstance(event, str):
            yield event.encode("utf-8")
        # Assume it's an event dict
        else:
            yield _format_sse_event(event)

    # Send retry directive if specified
    if retry is not None:
        yield f"retry: {retry}\r\n\r\n".encode("utf-8")


def _wrap_sync_sse_content(
    content: Iterator[Any],
    retry: int | None,
) -> Generator[bytes, None, None]:
    """Wrap sync content for SSE."""
    for event in content:
        # Check if it's already bytes (pre-formatted)
        if isinstance(event, bytes):
            yield event
        # Check if it's a string
        elif isinstance(event, str):
            yield event.encode("utf-8")
        # Assume it's an event dict
        else:
            yield _format_sse_event(event)

    # Send retry directive if specified
    if retry is not None:
        yield f"retry: {retry}\r\n\r\n".encode("utf-8")


class SSEResponse(StreamingResponse):
    """Server-Sent Events (SSE) response.

    This is a specialized streaming response that automatically formats events
    according to the SSE protocol.

    Usage with an async generator::

        from fastapi import FastAPI
        from fastapi.responses import SSEResponse

        app = FastAPI()

        async def event_generator():
            yield {"event": "message", "data": "Hello"}
            yield {"data": "World", "id": "123"}
            yield {"event": "close", "data": "Done", "retry": 5000}

        @app.get("/events")
        async def main():
            return SSEResponse(event_generator())

    Usage with a sync generator::

        from fastapi import FastAPI
        from fastapi.responses import SSEResponse

        app = FastAPI()

        def event_generator():
            yield {"event": "message", "data": "Hello"}
            yield {"data": "World", "id": "123"}

        @app.get("/events")
        async def main():
            return SSEResponse(event_generator())

    Or pass pre-formatted SSE data directly::

        from fastapi import FastAPI
        from fastapi.responses import SSEResponse

        app = FastAPI()

        async def event_generator():
            yield "data: Hello\\n\\n"
            yield "data: World\\n\\n"

        @app.get("/events")
        async def main():
            return SSEResponse(event_generator())

    Args:
        content: An async or sync iterator/generator yielding event dictionaries,
            strings, or pre-formatted bytes.
        status_code: HTTP status code (default: 200)
        headers: Additional headers to include in the response.
        media_type: The media type. Defaults to "text/event-stream".
        background: A BackgroundTask to run after the response is sent.
        retry: The reconnection time in milliseconds. If set, a retry directive
            will be sent when the stream ends.
    """

    default_media_type = "text/event-stream"

    def __init__(
        self,
        content: AsyncIterator[Any] | Iterator[Any] | AsyncGenerator[Any, None] | Generator[Any, None, None],
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        media_type: str | None = None,
        background: Any | None = None,
        retry: int | None = None,
    ) -> None:
        self._retry = retry

        # Wrap the content to format events as SSE
        wrapped_content = _wrap_sse_content(content, retry)

        super().__init__(
            content=wrapped_content,
            status_code=status_code,
            headers=headers,
            media_type=media_type or self.default_media_type,
            background=background,
        )


def sse(
    iterator: AsyncIterator[Any] | Iterator[Any],
    *,
    retry: int | None = None,
) -> SSEResponse:
    """Create an SSE response from an iterator of event dictionaries.

    This is a convenience function that creates an SSEResponse with the
    specified retry configuration.

    Usage::

        from fastapi import FastAPI
        from fastapi.responses import sse

        app = FastAPI()

        async def event_generator():
            yield {"data": "Hello"}
            yield {"data": "World"}

        @app.get("/events")
        async def main():
            return sse(event_generator())

    Args:
        iterator: An async or sync iterator yielding event dictionaries.
            Each dictionary can contain:
            - `event`: The event type (string)
            - `data`: The event data (will be converted to string)
            - `id`: The event ID (integer or string)
            - `retry`: Reconnection time in milliseconds (integer)
        retry: Default reconnection time in milliseconds for all events.

    Returns:
        An SSEResponse instance.
    """
    return SSEResponse(iterator, retry=retry)

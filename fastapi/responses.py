from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, AsyncGenerator, Generator, Optional, Union

from fastapi.exceptions import FastAPIDeprecationWarning
from starlette.responses import FileResponse as FileResponse  # noqa
from starlette.responses import HTMLResponse as HTMLResponse  # noqa
from starlette.responses import JSONResponse as JSONResponse  # noqa
from starlette.responses import PlainTextResponse as PlainTextResponse  # noqa
from starlette.responses import RedirectResponse as RedirectResponse  # noqa
from starlette.responses import Response as Response  # noqa
from starlette.responses import StreamingResponse as StreamingResponse  # noqa
from typing_extensions import deprecated

if TYPE_CHECKING:
    from typing import Awaitable, Callable

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
class SSEvent:
    """Server-Sent Events event data.

    Used to construct SSE events with optional event type, id, and retry fields.

    Read more about Server-Sent Events in the
    [FastAPI docs](https://fastapi.tiangolo.com/advanced/custom-response/).
    """

    data: Union[str, Any]
    """The event data payload. Can be a string or any serializable object."""

    event: Optional[str] = None
    """Optional event type identifier for client-side routing."""

    id: Optional[str] = None
    """Optional event ID for client-side tracking."""

    retry: Optional[int] = None
    """Optional reconnection interval in milliseconds."""


def _sse_format_event(
    data: Union[str, Any],
    event: Optional[str] = None,
    id: Optional[str] = None,
    retry: Optional[int] = None,
) -> str:
    """Format a single SSE event according to the W3C specification."""
    lines = []

    if event is not None:
        lines.append(f"event: {event}")

    if id is not None:
        lines.append(f"id: {id}")

    if retry is not None:
        lines.append(f"retry: {retry}")

    # Handle data - can be string or serializable
    if isinstance(data, str):
        # Split by newlines as per SSE spec - each line needs data: prefix
        for line in data.split("\n"):
            lines.append(f"data: {line}")
    else:
        # For non-string data, convert to string
        lines.append(f"data: {data}")

    # Empty line terminates the event
    lines.append("")

    return "\n".join(lines)


class SSEResponse(StreamingResponse):
    """Server-Sent Events (SSE) response.

    A streaming response that automatically formats events according to
    the W3C Server-Sent Events specification.

    Read more about Server-Sent Events in the
    [FastAPI docs](https://fastapi.tiangolo.com/advanced/custom-response/).

    Example:
    ```python
    from fastapi import FastAPI
    from fastapi.responses import SSEResponse

    app = FastAPI()

    @app.get("/events")
    async def events():
        async def event_generator():
            for i in range(5):
                yield f"data: message {i}\\n\\n"

        return SSEResponse(event_generator(), event="message")
    ```
    """

    media_type = "text/event-stream"

    def __init__(
        self,
        content: Union[
            AsyncGenerator[Union[str, "SSEvent"], None],
            Generator[Union[str, "SSEvent"], None, None],
            "Callable[[], AsyncGenerator[Union[str, SSEvent], None]]",
            "Callable[[], Generator[Union[str, SSEvent], None, None]]",
        ],
        status_code: int = 200,
        headers: Optional[dict[str, str]] = None,
        media_type: Optional[str] = None,
        background: Optional[Any] = None,
        *,
        event: Optional[str] = None,
        id: Optional[str] = None,
        retry: Optional[int] = None,
    ) -> None:
        """Create an SSE response.

        Args:
            content: An async or sync generator that yields string data or SSEvent objects.
            status_code: HTTP status code (default 200).
            headers: Optional dict of HTTP headers.
            media_type: Media type. If not specified, defaults to "text/event-stream".
            background: Optional background task.
            event: Default event type for all events (can be overridden by SSEvent objects).
            id: Default event ID for all events (can be overridden by SSEvent objects).
            retry: Default retry interval in milliseconds for reconnection.
        """
        # Default to text/event-stream if not specified
        if media_type is None:
            media_type = "text/event-stream"

        # Wrap the generator if it's callable (deferred execution)
        if callable(content):
            content = content()  # type: ignore[assignment]

        # Wrap the generator to format SSE events
        wrapped_content = self._wrap_generator(content)  # type: ignore[arg-type]

        super().__init__(
            content=wrapped_content,  # type: ignore[arg-type]
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )

        # Store SSE-specific configuration
        self.event = event
        self.id = id
        self.retry = retry

    def _wrap_generator(
        self,
        content: Union[
            AsyncGenerator[Union[str, SSEvent], None],
            Generator[Union[str, SSEvent], None, None],
        ],
    ) -> Union[AsyncGenerator[bytes, None], Generator[bytes, None, None]]:
        """Wrap the content generator to format SSE events."""
        # Import inspect to check if it's an async generator
        import inspect

        if inspect.isasyncgen(content):
            return self._wrap_async_generator(content)  # type: ignore[return-value]
        else:
            return self._wrap_sync_generator(content)  # type: ignore[return-value]

    def _wrap_sync_generator(
        self,
        content: Generator[Union[str, SSEvent], None, None],
    ) -> Generator[bytes, None, None]:
        """Wrap a sync generator to format SSE events."""
        for item in content:
            try:
                # Check if item is an SSEvent object or string
                if isinstance(item, SSEvent):
                    formatted = _sse_format_event(
                        data=item.data,
                        event=item.event or self.event,
                        id=item.id or self.id,
                        retry=item.retry or self.retry,
                    )
                else:
                    # String data - use default event/id/retry
                    formatted = _sse_format_event(
                        data=item,
                        event=self.event,
                        id=self.id,
                        retry=self.retry,
                    )
                yield formatted.encode("utf-8")
            except GeneratorExit:
                # Client disconnected
                break

    async def _wrap_async_generator(
        self,
        content: AsyncGenerator[Union[str, SSEvent], None],
    ) -> AsyncGenerator[bytes, None]:
        """Wrap an async generator to format SSE events."""
        try:
            async for item in content:
                try:
                    # Check if item is an SSEvent object or string
                    if isinstance(item, SSEvent):
                        formatted = _sse_format_event(
                            data=item.data,
                            event=item.event or self.event,
                            id=item.id or self.id,
                            retry=item.retry or self.retry,
                        )
                    else:
                        # String data - use default event/id/retry
                        formatted = _sse_format_event(
                            data=item,
                            event=self.event,
                            id=self.id,
                            retry=self.retry,
                        )
                    yield formatted.encode("utf-8")
                except Exception:
                    # Client disconnected or other error - stop gracefully
                    break
        except Exception:
            # Generator was cancelled or closed - handle gracefully
            pass

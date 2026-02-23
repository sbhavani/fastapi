from typing import Any, AsyncIterator

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


class ServerSentEvent:
    """A Server-Sent Event to be sent to the client.

    Args:
        data: The data to send. Can be a string or bytes. Will be sent as the `data` field.
        event: The event type. Will be sent as the `event` field.
        id: The event ID. Will be sent as the `id` field.
        retry: The retry interval in milliseconds. Will be sent as the `retry` field.
        comment: A comment to send. Comments are ignored by clients but can be used
            to keep the connection alive.
    """

    def __init__(
        self,
        data: str | bytes | None = None,
        event: str | None = None,
        id: int | str | None = None,
        retry: int | None = None,
        comment: str | None = None,
    ) -> None:
        self.data = data
        self.event = event
        self.id = id
        self.retry = retry
        self.comment = comment

    def encode(self) -> bytes:
        """Encode the Server-Sent Event to bytes."""
        lines = []

        if self.comment:
            for line in self.comment.split("\n"):
                lines.append(f": {line}")

        if self.id is not None:
            lines.append(f"id: {self.id}")

        if self.event is not None:
            lines.append(f"event: {self.event}")

        if self.retry is not None:
            lines.append(f"retry: {self.retry}")

        if self.data is not None:
            data_str = self.data if isinstance(self.data, str) else self.data.decode(
                "utf-8"
            )
            for line in data_str.split("\n"):
                lines.append(f"data: {line}")

        # SSE requires double newline at the end to separate events
        lines.append("")
        lines.append("")

        return "\n".join(lines).encode("utf-8")


class SSEResponse(StreamingResponse):
    """Streaming response for Server-Sent Events.

    This extends Starlette's StreamingResponse to provide automatic event formatting,
    retry configuration, and client disconnect handling for SSE.

    Args:
        content: An async iterator or generator yielding ServerSentEvent objects or strings.
        status_code: The HTTP status code (default 200).
        headers: Additional headers to include in the response.
        media_type: The media type (default "text/event-stream").
        background: A background task to run after the response is sent.
        retry: The retry interval in milliseconds. If provided, a `retry` field will be
            sent with each event.
        ping: The interval in seconds between ping events. If provided, blank comments
            will be sent at this interval to keep the connection alive.
        ping_interval: Alias for `ping` for compatibility.
        disconnect_callback: An async callback to call when the client disconnects.

    Example:
        ```python
        from fastapi import FastAPI
        from fastapi.responses import SSEResponse, ServerSentEvent

        app = FastAPI()

        async def sse_events():
            for i in range(5):
                yield ServerSentEvent(data=f"message {i}", event="message")
                await asyncio.sleep(1)

        @app.get("/events")
        async def main():
            return SSEResponse(sse_events())
        ```
    """

    def __init__(
        self,
        content: AsyncIterator[str | ServerSentEvent],
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        media_type: str | None = "text/event-stream",
        background: Any | None = None,
        retry: int | None = None,
        ping: int | None = None,
        ping_interval: int | None = None,
        disconnect_callback: Any | None = None,
    ) -> None:
        self.retry = retry
        self.ping = ping if ping is not None else ping_interval
        self.disconnect_callback = disconnect_callback

        if media_type is None:
            media_type = "text/event-stream"

        super().__init__(
            content=self._stream(content),
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )

    async def _stream(
        self, content: AsyncIterator[str | ServerSentEvent]
    ) -> AsyncIterator[bytes]:
        """Stream SSE events with automatic formatting and client disconnect handling."""
        import asyncio

        async for event in content:
            # Handle string events
            if isinstance(event, str):
                yield event.encode("utf-8")
                continue

            # Handle ServerSentEvent objects
            if isinstance(event, ServerSentEvent):
                # Add retry to each event if configured
                if self.retry is not None and event.retry is None:
                    event.retry = self.retry

                yield event.encode()
                continue

            raise TypeError(
                f"SSEResponse content must be async iterator of str or ServerSentEvent, "
                f"got {type(event)}"
            )

            # Send ping comments if configured
            if self.ping is not None and self.ping > 0:
                await asyncio.sleep(self.ping)
                yield b": ping\n\n"

    async def listen_for_disconnect(self, receive: Any) -> None:
        """Listen for client disconnect.

        This method can be used to handle client disconnection gracefully.
        It checks the ASGI receive channel for disconnect events.

        Args:
            receive: The ASGI receive callable.

        Returns:
            True if the client disconnected, False otherwise.
        """
        while True:
            message = await receive()
            if message.get("type") == "http.disconnect":
                if self.disconnect_callback is not None:
                    await self.disconnect_callback()
                return True

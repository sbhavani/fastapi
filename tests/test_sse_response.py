"""Tests for SSE response."""
import pytest
from fastapi import FastAPI
from fastapi.responses import SSEResponse, sse
from fastapi.testclient import TestClient


def _make_sse_app():
    """Create a FastAPI app with SSE endpoints."""
    app = FastAPI()

    @app.get("/events/async")
    async def async_events():
        async def generator():
            yield {"event": "message", "data": "Hello"}
            yield {"data": "World", "id": "123"}
            yield {"event": "close", "data": "Done", "retry": 5000}

        return SSEResponse(generator())

    @app.get("/events/sync")
    def sync_events():
        def generator():
            yield {"event": "message", "data": "Hello"}
            yield {"data": "World", "id": "123"}
            yield {"event": "close", "data": "Done"}

        return SSEResponse(generator())

    @app.get("/events/sse-helper")
    async def sse_helper_events():
        async def generator():
            yield {"data": "Hello"}
            yield {"data": "World"}

        return sse(generator())

    @app.get("/events/retry")
    async def retry_events():
        async def generator():
            yield {"data": "First"}
            yield {"data": "Second"}

        return SSEResponse(generator(), retry=3000)

    @app.get("/events/preformatted")
    async def preformatted_events():
        async def generator():
            yield "data: Hello\n\n"
            yield "data: World\n\n"

        return SSEResponse(generator())

    @app.get("/events/multiline")
    async def multiline_events():
        async def generator():
            yield {"data": "Line 1\nLine 2\nLine 3"}

        return SSEResponse(generator())

    @app.get("/events/bytes")
    async def bytes_events():
        async def generator():
            yield b"data: Raw bytes\n\n"

        return SSEResponse(generator())

    return app


def test_sse_async_generator():
    """Test SSE response with async generator."""
    app = _make_sse_app()
    client = TestClient(app)
    response = client.get("/events/async")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    # Decode the SSE stream
    content = response.content.decode("utf-8")
    assert "event: message" in content
    assert "data: Hello" in content
    assert "data: World" in content
    assert "id: 123" in content
    assert "event: close" in content
    assert "retry: 5000" in content


def test_sse_sync_generator():
    """Test SSE response with sync generator."""
    app = _make_sse_app()
    client = TestClient(app)
    response = client.get("/events/sync")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    content = response.content.decode("utf-8")
    assert "event: message" in content
    assert "data: Hello" in content


def test_sse_helper():
    """Test sse() helper function."""
    app = _make_sse_app()
    client = TestClient(app)
    response = client.get("/events/sse-helper")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    content = response.content.decode("utf-8")
    assert "data: Hello" in content
    assert "data: World" in content


def test_sse_retry():
    """Test SSE response with retry configuration."""
    app = _make_sse_app()
    client = TestClient(app)
    response = client.get("/events/retry")

    assert response.status_code == 200

    content = response.content.decode("utf-8")
    # The retry should be appended at the end
    assert "retry: 3000" in content


def test_sse_preformatted():
    """Test SSE response with pre-formatted strings."""
    app = _make_sse_app()
    client = TestClient(app)
    response = client.get("/events/preformatted")

    assert response.status_code == 200

    content = response.content.decode("utf-8")
    assert "data: Hello" in content
    assert "data: World" in content


def test_sse_multiline_data():
    """Test SSE response with multiline data."""
    app = _make_sse_app()
    client = TestClient(app)
    response = client.get("/events/multiline")

    assert response.status_code == 200

    content = response.content.decode("utf-8")
    # Each line should be prefixed with "data:"
    assert "data: Line 1" in content
    assert "data: Line 2" in content
    assert "data: Line 3" in content


def test_sse_bytes():
    """Test SSE response with pre-formatted bytes."""
    app = _make_sse_app()
    client = TestClient(app)
    response = client.get("/events/bytes")

    assert response.status_code == 200

    content = response.content.decode("utf-8")
    assert "data: Raw bytes" in content


def test_sse_format_event():
    """Test the internal _format_sse_event function."""
    from fastapi.responses import _format_sse_event

    # Test basic event
    result = _format_sse_event({"data": "Hello"})
    assert result == b"data: Hello\r\n\r\n"

    # Test event with type
    result = _format_sse_event({"event": "message", "data": "Hello"})
    assert result == b"event: message\r\ndata: Hello\r\n\r\n"

    # Test event with id
    result = _format_sse_event({"data": "Hello", "id": "123"})
    assert result == b"id: 123\r\ndata: Hello\r\n\r\n"

    # Test event with retry
    result = _format_sse_event({"data": "Hello", "retry": 5000})
    assert result == b"retry: 5000\r\ndata: Hello\r\n\r\n"

    # Test multiline data
    result = _format_sse_event({"data": "Line 1\nLine 2"})
    assert result == b"data: Line 1\r\ndata: Line 2\r\n\r\n"

    # Test data as list
    result = _format_sse_event({"data": ["item1", "item2"]})
    assert result == b"data: item1\r\ndata: item2\r\n\r\n"


def test_sse_is_async():
    """Test the internal _is_async function."""
    from fastapi.responses import _is_async

    # Async generator
    async def async_gen():
        yield 1

    assert _is_async(async_gen) is True

    # Regular generator
    def sync_gen():
        yield 1

    assert _is_async(sync_gen) is False

    # Async iterator class
    class AsyncIter:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    assert _is_async(AsyncIter()) is True

    # Sync iterator class
    class SyncIter:
        def __iter__(self):
            return self

        def __next__(self):
            raise StopIteration

    assert _is_async(SyncIter()) is False

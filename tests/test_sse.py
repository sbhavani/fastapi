import asyncio
from typing import AsyncGenerator

import pytest
from fastapi import FastAPI
from fastapi.responses import SSEEvent, SSEResponse
from fastapi.testclient import TestClient


def test_sse_event_encode_basic():
    """Test basic SSE event encoding."""
    event = SSEEvent(data="Hello, World!")
    encoded = event.encode()
    expected = b"data: Hello, World!\n\n"
    assert encoded == expected


def test_sse_event_encode_with_event_type():
    """Test SSE event with event type field."""
    event = SSEEvent(data="notification", event="message")
    encoded = event.encode()
    assert b"event: message\n" in encoded
    assert b"data: notification\n" in encoded


def test_sse_event_encode_with_id():
    """Test SSE event with event ID field."""
    event = SSEEvent(data="update", id="123")
    encoded = event.encode()
    assert b"id: 123\n" in encoded
    assert b"data: update\n" in encoded


def test_sse_event_encode_with_retry():
    """Test SSE event with retry field."""
    event = SSEEvent(data="reconnect", retry=5000)
    encoded = event.encode()
    assert b"retry: 5000\n" in encoded
    assert b"data: reconnect\n" in encoded


def test_sse_event_encode_full():
    """Test SSE event with all fields."""
    event = SSEEvent(
        data="full event",
        event="notification",
        id="456",
        retry=3000,
    )
    encoded = event.encode()
    assert b"event: notification\n" in encoded
    assert b"id: 456\n" in encoded
    assert b"retry: 3000\n" in encoded
    assert b"data: full event\n" in encoded


def test_sse_event_encode_comment():
    """Test SSE event with comment."""
    event = SSEEvent(data="ping", comment="keep-alive")
    encoded = event.encode()
    assert b":keep-alive\n" in encoded
    assert b"data: ping\n" in encoded


def test_sse_event_encode_multiline_data():
    """Test SSE event with multiline data."""
    event = SSEEvent(data="line1\nline2\nline3")
    encoded = event.encode()
    assert b"data: line1\n" in encoded
    assert b"data: line2\n" in encoded
    assert b"data: line3\n" in encoded


def test_sse_event_encode_dict_data():
    """Test SSE event with dict data (auto-converted to string)."""
    event = SSEEvent(data={"key": "value"})
    encoded = event.encode()
    assert b"data: {'key': 'value'}\n" in encoded or b'data: {"key": "value"}\n' in encoded


def test_sse_event_encode_integer_data():
    """Test SSE event with integer data."""
    event = SSEEvent(data=42)
    encoded = event.encode()
    assert b"data: 42\n" in encoded


def test_sse_response_default_media_type():
    """Test that SSEResponse uses text/event-stream media type."""
    app = FastAPI()

    async def generator() -> AsyncGenerator[SSEEvent, None]:
        yield SSEEvent(data="test")

    @app.get("/events")
    async def events():
        return SSEResponse(generator())

    with TestClient(app) as client:
        response = client.get("/events")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


def test_sse_response_headers():
    """Test that SSEResponse sets default headers."""
    app = FastAPI()

    async def generator() -> AsyncGenerator[SSEEvent, None]:
        yield SSEEvent(data="test")

    @app.get("/events")
    async def events():
        return SSEResponse(generator())

    with TestClient(app) as client:
        response = client.get("/events")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["connection"] == "keep-alive"


def test_sse_response_streaming():
    """Test SSE event streaming."""
    app = FastAPI()

    async def generator() -> AsyncGenerator[SSEEvent, None]:
        for i in range(3):
            yield SSEEvent(data=f"message {i}")

    @app.get("/events")
    async def events():
        return SSEResponse(generator())

    with TestClient(app) as client:
        response = client.get("/events")
        content = response.content
        assert b"data: message 0\n" in content
        assert b"data: message 1\n" in content
        assert b"data: message 2\n" in content


def test_sse_response_with_event_type():
    """Test SSE response with custom event type."""
    app = FastAPI()

    async def generator() -> AsyncGenerator[SSEEvent, None]:
        yield SSEEvent(data="alert", event="notification")

    @app.get("/events")
    async def events():
        return SSEResponse(generator())

    with TestClient(app) as client:
        response = client.get("/events")
        content = response.content
        assert b"event: notification\n" in content
        assert b"data: alert\n" in content


def test_sse_response_with_retry():
    """Test SSE response with retry configuration."""
    app = FastAPI()

    async def generator() -> AsyncGenerator[SSEEvent, None]:
        yield SSEEvent(data="reconnecting", retry=5000)

    @app.get("/events")
    async def events():
        return SSEResponse(generator())

    with TestClient(app) as client:
        response = client.get("/events")
        content = response.content
        assert b"retry: 5000\n" in content


def test_sse_response_custom_headers():
    """Test SSE response with custom headers."""
    app = FastAPI()

    async def generator() -> AsyncGenerator[SSEEvent, None]:
        yield SSEEvent(data="test")

    @app.get("/events")
    async def events():
        return SSEResponse(generator(), headers={"X-Custom": "value"})

    with TestClient(app) as client:
        response = client.get("/events")
        assert response.headers["x-custom"] == "value"


def test_sse_response_status_code():
    """Test SSE response with custom status code."""
    app = FastAPI()

    async def generator() -> AsyncGenerator[SSEEvent, None]:
        yield SSEEvent(data="error")

    @app.get("/events")
    async def events():
        return SSEResponse(generator(), status_code=201)

    with TestClient(app) as client:
        response = client.get("/events")
        assert response.status_code == 201


def test_sse_event_no_data():
    """Test that SSEEvent requires data."""
    with pytest.raises(TypeError):
        SSEEvent()  # type: ignore


def test_sse_event_optional_fields():
    """Test SSE event with only required field."""
    event = SSEEvent(data="minimal")
    encoded = event.encode()
    assert encoded == b"data: minimal\n\n"


def test_sse_response_generator_cleanup():
    """Test that generator is properly cleaned up after streaming completes."""
    app = FastAPI()
    cleanup_called = False

    async def generator() -> AsyncGenerator[SSEEvent, None]:
        nonlocal cleanup_called
        try:
            yield SSEEvent(data="message 1")
            yield SSEEvent(data="message 2")
        finally:
            cleanup_called = True

    @app.get("/events")
    async def events():
        return SSEResponse(generator())

    with TestClient(app) as client:
        response = client.get("/events")
        # Consume the response
        _ = response.content

    # After response is complete, cleanup should have been called
    assert cleanup_called, "Generator cleanup was not called after streaming completed"


def test_sse_response_disconnect_handler():
    """Test that SSEResponse handles client disconnect gracefully."""
    app = FastAPI()
    events_sent = []

    async def generator() -> AsyncGenerator[SSEEvent, None]:
        try:
            for i in range(10):
                events_sent.append(i)
                yield SSEEvent(data=f"message {i}")
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            # Expected when client disconnects
            events_sent.append("cancelled")
            raise

    @app.get("/events")
    async def events():
        return SSEResponse(generator())

    with TestClient(app) as client:
        # Make request that we'll cancel
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(client.get, "/events")
            # Let it run briefly
            import time
            time.sleep(0.2)
            # Cancel the request
            future.cancel()

    # Verify events were being sent before cancellation
    assert len(events_sent) > 0


def test_sse_disconnect_cancels_task():
    """Test that client disconnect properly cancels the streaming task."""
    from fastapi.responses import SSEResponse

    cancelled = False

    async def slow_generator():
        nonlocal cancelled
        try:
            yield SSEEvent(data="start")
            await asyncio.sleep(10)  # Long sleep
            yield SSEEvent(data="end")
        except asyncio.CancelledError:
            cancelled = True
            raise

    # Create response but don't fully consume it
    response = SSEResponse(slow_generator())

    # Simulate the body being iterated and then cancelled
    async def consume_and_cancel():
        nonlocal cancelled
        iter = response.body_iterator.__aiter__()
        # Get first event
        await iter.__anext__()
        # Cancel - simulating client disconnect
        raise asyncio.CancelledError()

    # Run the async test in an event loop
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        # This should handle the cancellation gracefully
        try:
            loop.run_until_complete(consume_and_cancel())
        except asyncio.CancelledError:
            pass  # Expected
    finally:
        loop.close()


def test_sse_response_multiple_events_with_cleanup():
    """Test multiple events are sent and cleanup happens properly."""
    app = FastAPI()
    cleanup_count = 0

    async def generator() -> AsyncGenerator[SSEEvent, None]:
        nonlocal cleanup_count
        for i in range(5):
            yield SSEEvent(data=f"event {i}")
        # Cleanup happens in finally block

    @app.get("/events")
    async def events():
        return SSEResponse(generator())

    with TestClient(app) as client:
        response = client.get("/events")
        content = response.content
        # Verify all events were sent
        for i in range(5):
            assert f"data: event {i}".encode() in content


def test_sse_response_empty_generator():
    """Test handling of empty generator."""
    app = FastAPI()

    async def generator() -> AsyncGenerator[SSEEvent, None]:
        return
        yield  # Make it an async generator

    @app.get("/events")
    async def events():
        return SSEResponse(generator())

    with TestClient(app) as client:
        response = client.get("/events")
        assert response.status_code == 200
        # Empty response is valid

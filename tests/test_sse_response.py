"""Tests for Server-Sent Events (SSE) responses."""

import pytest
from fastapi import FastAPI
from fastapi.responses import SSEResponse, ServerSentEvent
from fastapi.testclient import TestClient


def test_server_sent_event_data_only():
    """Test ServerSentEvent with only data."""
    event = ServerSentEvent(data="hello")
    encoded = event.encode()
    assert encoded == b"data: hello\n\n"


def test_server_sent_event_with_event_type():
    """Test ServerSentEvent with event type."""
    event = ServerSentEvent(data="hello", event="message")
    encoded = event.encode()
    assert b"event: message\n" in encoded
    assert b"data: hello\n" in encoded


def test_server_sent_event_with_id():
    """Test ServerSentEvent with event ID."""
    event = ServerSentEvent(data="hello", id="1")
    encoded = event.encode()
    assert b"id: 1\n" in encoded
    assert b"data: hello\n" in encoded


def test_server_sent_event_with_retry():
    """Test ServerSentEvent with retry."""
    event = ServerSentEvent(data="hello", retry=5000)
    encoded = event.encode()
    assert b"retry: 5000\n" in encoded
    assert b"data: hello\n" in encoded


def test_server_sent_event_with_comment():
    """Test ServerSentEvent with comment."""
    event = ServerSentEvent(comment="ping")
    encoded = event.encode()
    assert b": ping\n" in encoded


def test_server_sent_event_multiline_data():
    """Test ServerSentEvent with multiline data."""
    event = ServerSentEvent(data="line1\nline2\nline3")
    encoded = event.encode()
    assert b"data: line1\n" in encoded
    assert b"data: line2\n" in encoded
    assert b"data: line3\n" in encoded


def test_server_sent_event_bytes_data():
    """Test ServerSentEvent with bytes data."""
    event = ServerSentEvent(data=b"hello")
    encoded = event.encode()
    assert encoded == b"data: hello\n\n"


def test_server_sent_event_full():
    """Test ServerSentEvent with all fields."""
    event = ServerSentEvent(data="hello", event="message", id="1", retry=5000)
    encoded = event.encode()
    assert b"data: hello\n" in encoded
    assert b"event: message\n" in encoded
    assert b"id: 1\n" in encoded
    assert b"retry: 5000\n" in encoded


def test_sse_response_basic():
    """Test basic SSE response."""
    app = FastAPI()

    @app.get("/events")
    async def events():
        async def generator():
            for i in range(3):
                yield ServerSentEvent(data=f"message {i}")

        return SSEResponse(generator())

    client = TestClient(app)
    with client.stream("GET", "/events") as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        lines = []
        for line in response.iter_lines():
            if line:
                lines.append(line)

        content = "\n".join(lines)
        assert "data: message 0" in content
        assert "data: message 1" in content
        assert "data: message 2" in content


def test_sse_response_with_event_type():
    """Test SSE response with event types."""
    app = FastAPI()

    @app.get("/events")
    async def events():
        async def generator():
            yield ServerSentEvent(data="hello", event="greeting")

        return SSEResponse(generator())

    client = TestClient(app)
    with client.stream("GET", "/events") as response:
        content = ""
        for line in response.iter_lines():
            if line:
                content += line + "\n"

        assert "event: greeting\n" in content
        assert "data: hello\n" in content


def test_sse_response_with_retry():
    """Test SSE response with retry configuration."""
    app = FastAPI()

    @app.get("/events")
    async def events():
        async def generator():
            for i in range(3):
                yield ServerSentEvent(data=f"message {i}")

        return SSEResponse(generator(), retry=5000)

    client = TestClient(app)
    with client.stream("GET", "/events") as response:
        content = ""
        for line in response.iter_lines():
            if line:
                content += line + "\n"

        assert "retry: 5000\n" in content


def test_sse_response_string_content():
    """Test SSE response with string content."""
    app = FastAPI()

    @app.get("/events")
    async def events():
        async def generator():
            yield "data: hello\n\n"

        return SSEResponse(generator())

    client = TestClient(app)
    with client.stream("GET", "/events") as response:
        content = ""
        for line in response.iter_lines():
            if line:
                content += line + "\n"

        assert "data: hello\n" in content


def test_sse_response_custom_headers():
    """Test SSE response with custom headers."""
    app = FastAPI()

    @app.get("/events")
    async def events():
        async def generator():
            yield ServerSentEvent(data="hello")

        return SSEResponse(generator(), headers={"X-Custom": "value"})

    client = TestClient(app)
    response = client.get("/events")
    assert response.status_code == 200
    assert response.headers.get("x-custom") == "value"


def test_sse_response_status_code():
    """Test SSE response with custom status code."""
    app = FastAPI()

    @app.get("/events")
    async def events():
        async def generator():
            yield ServerSentEvent(data="hello")

        return SSEResponse(generator(), status_code=201)

    client = TestClient(app)
    response = client.get("/events")
    assert response.status_code == 201


def test_sse_response_media_type():
    """Test SSE response with custom media type."""
    app = FastAPI()

    @app.get("/events")
    async def events():
        async def generator():
            yield ServerSentEvent(data="hello")

        return SSEResponse(generator(), media_type="text/event-stream")

    client = TestClient(app)
    response = client.get("/events")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


def test_server_sent_event_integer_id():
    """Test ServerSentEvent with integer ID."""
    event = ServerSentEvent(data="hello", id=123)
    encoded = event.encode()
    assert b"id: 123\n" in encoded

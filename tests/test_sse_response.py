"""Tests for SSE (Server-Sent Events) response classes."""

import pytest
from fastapi import FastAPI
from fastapi.responses import SSEEvent, SSEResponse, sse_event
from fastapi.testclient import TestClient


def test_sse_event_basic():
    """Test basic sse_event formatting."""
    result = sse_event(data="Hello")
    assert result == "data: Hello\n"


def test_sse_event_with_dict():
    """Test sse_event with dict data (auto JSON encoding)."""
    result = sse_event(data={"status": "ok"})
    assert result == 'data: {"status": "ok"}\n'


def test_sse_event_with_event_type():
    """Test sse_event with event type field."""
    result = sse_event(data="Update", event="update")
    assert result == "event: update\ndata: Update\n"


def test_sse_event_with_id():
    """Test sse_event with ID field."""
    result = sse_event(data="Hello", id=1)
    assert result == "id: 1\ndata: Hello\n"


def test_sse_event_id_as_string():
    """Test sse_event with ID field as string."""
    result = sse_event(data="Hello", id="123")
    assert result == "id: 123\ndata: Hello\n"


def test_sse_event_id_none_excluded():
    """Test that id=None does not include id field."""
    result = sse_event(data="Hello", id=None)
    assert "id:" not in result
    assert result == "data: Hello\n"


def test_sse_event_id_only():
    """Test sse_event with only id field (no other optional fields)."""
    result = sse_event(data="Hello", id=42)
    lines = result.split("\n")
    assert lines[0] == "id: 42"


def test_sse_event_with_retry():
    """Test sse_event with retry field."""
    result = sse_event(data="Hello", retry=5000)
    assert result == "data: Hello\nretry: 5000\n"


def test_sse_event_retry_zero():
    """Test sse_event with retry=0 (edge case)."""
    result = sse_event(data="Hello", retry=0)
    assert result == "data: Hello\nretry: 0\n"


def test_sse_event_retry_large_value():
    """Test sse_event with large retry value."""
    result = sse_event(data="Hello", retry=3600000)
    assert result == "data: Hello\nretry: 3600000\n"


def test_sse_event_retry_with_data_only():
    """Test sse_event with retry and data only (no event or id)."""
    result = sse_event(data="Message", retry=1000)
    assert result == "data: Message\nretry: 1000\n"


def test_sse_event_retry_none_excluded():
    """Test that retry=None does not include retry field."""
    result = sse_event(data="Hello", retry=None)
    assert "retry:" not in result
    assert result == "data: Hello\n"


def test_sse_event_dataclass_retry_bytes():
    """Test SSEEvent dataclass with retry field bytes conversion."""
    event = SSEEvent(data="Hello", retry=5000)
    result = bytes(event)
    assert result == b"data: Hello\nretry: 5000\n"


def test_sse_event_all_fields():
    """Test sse_event with all fields in correct order."""
    result = sse_event(data="Update", event="update", id=1, retry=5000)
    # Field order: id, event, data, retry
    assert result == "id: 1\nevent: update\ndata: Update\nretry: 5000\n"


def test_sse_event_field_order():
    """Verify field order: id, event, data, retry."""
    result = sse_event(data="test", id="1", event="msg", retry=1000)
    lines = result.split("\n")
    # First line should be id
    assert lines[0] == "id: 1"
    # Second line should be event
    assert lines[1] == "event: msg"
    # Third line should be data
    assert lines[2] == "data: test"
    # Fourth line should be retry
    assert lines[3] == "retry: 1000"


def test_sse_event_multiline_data():
    """Test sse_event with multi-line data."""
    result = sse_event(data="line1\nline2\nline3")
    lines = result.split("\n")
    assert lines[0] == "data: line1"
    assert lines[1] == "data: line2"
    assert lines[2] == "data: line3"


def test_sse_event_multiline_with_event():
    """Test sse_event with multi-line data and event type."""
    result = sse_event(data="line1\nline2", event="update")
    lines = result.split("\n")
    assert lines[0] == "event: update"
    assert lines[1] == "data: line1"
    assert lines[2] == "data: line2"


def test_sse_event_multiline_with_id():
    """Test sse_event with multi-line data and id."""
    result = sse_event(data="line1\nline2", id=1)
    lines = result.split("\n")
    assert lines[0] == "id: 1"
    assert lines[1] == "data: line1"
    assert lines[2] == "data: line2"


def test_sse_event_multiline_with_retry():
    """Test sse_event with multi-line data and retry."""
    result = sse_event(data="line1\nline2", retry=5000)
    lines = result.split("\n")
    assert lines[0] == "data: line1"
    assert lines[1] == "data: line2"
    assert lines[2] == "retry: 5000"


def test_sse_event_multiline_with_empty_lines():
    """Test sse_event with multi-line data containing empty lines."""
    result = sse_event(data="line1\n\nline2")
    lines = result.split("\n")
    assert lines[0] == "data: line1"
    assert lines[1] == "data: "
    assert lines[2] == "data: line2"


def test_sse_event_dataclass_multiline():
    """Test SSEEvent dataclass with multi-line data."""
    event = SSEEvent(data="line1\nline2\nline3")
    result = str(event)
    lines = result.split("\n")
    assert lines[0] == "data: line1"
    assert lines[1] == "data: line2"
    assert lines[2] == "data: line3"


def test_sse_event_with_list():
    """Test sse_event with list data (JSON encoded)."""
    result = sse_event(data=[1, 2, 3])
    assert result == "data: [1, 2, 3]\n"


def test_sse_event_with_number():
    """Test sse_event with number data (JSON encoded)."""
    result = sse_event(data=42)
    assert result == "data: 42\n"


def test_sse_event_with_boolean_true():
    """Test sse_event with boolean True (JSON encoded)."""
    result = sse_event(data=True)
    assert result == "data: true\n"


def test_sse_event_with_boolean_false():
    """Test sse_event with boolean False (JSON encoded)."""
    result = sse_event(data=False)
    assert result == "data: false\n"


def test_sse_event_with_none():
    """Test sse_event with None (JSON encoded as null)."""
    result = sse_event(data=None)
    assert result == "data: null\n"


def test_sse_event_with_float():
    """Test sse_event with float data (JSON encoded)."""
    result = sse_event(data=3.14)
    assert result == "data: 3.14\n"


def test_sse_event_with_nested_dict():
    """Test sse_event with nested dict data (JSON encoded)."""
    result = sse_event(data={"user": {"name": "Alice", "age": 30}})
    assert result == 'data: {"user": {"name": "Alice", "age": 30}}\n'


def test_sse_event_with_complex_structure():
    """Test sse_event with complex nested structure (JSON encoded)."""
    data = {
        "items": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}],
        "total": 2,
        "valid": True
    }
    result = sse_event(data=data)
    assert result == 'data: {"items": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}], "total": 2, "valid": true}\n'


def test_sse_event_with_unicode_in_dict():
    """Test sse_event with unicode characters in dict (JSON encoded)."""
    result = sse_event(data={"message": "Hello 世界 🌍"})
    # json.dumps escapes unicode characters
    assert result == 'data: {"message": "Hello \\u4e16\\u754c \\ud83c\\udf0d"}\n'


def test_sse_event_with_zero():
    """Test sse_event with zero (JSON encoded)."""
    result = sse_event(data=0)
    assert result == "data: 0\n"


def test_sse_event_with_empty_list():
    """Test sse_event with empty list (JSON encoded)."""
    result = sse_event(data=[])
    assert result == "data: []\n"


def test_sse_event_with_empty_dict():
    """Test sse_event with empty dict (JSON encoded)."""
    result = sse_event(data={})
    assert result == "data: {}\n"


def test_sse_event_empty_string():
    """Test sse_event with empty string data."""
    result = sse_event(data="")
    assert result == "data: \n"


# SSEEvent dataclass tests


def test_sse_event_dataclass_basic():
    """Test SSEEvent dataclass basic usage."""
    event = SSEEvent(data="Hello")
    result = str(event)
    assert result == "data: Hello\n"


def test_sse_event_dataclass_with_event():
    """Test SSEEvent with event type."""
    event = SSEEvent(data="Hello", event="message")
    result = str(event)
    assert result == "event: message\ndata: Hello\n"


def test_sse_event_dataclass_bytes():
    """Test SSEEvent bytes conversion."""
    event = SSEEvent(data="Hello")
    result = bytes(event)
    assert result == b"data: Hello\n"


def test_sse_event_dataclass_with_dict():
    """Test SSEEvent dataclass with dict data (auto JSON encoding)."""
    event = SSEEvent(data={"status": "ok"})
    result = str(event)
    assert result == 'data: {"status": "ok"}\n'


def test_sse_event_dataclass_with_list():
    """Test SSEEvent dataclass with list data (JSON encoded)."""
    event = SSEEvent(data=[1, 2, 3])
    result = str(event)
    assert result == "data: [1, 2, 3]\n"


def test_sse_event_dataclass_retry_str():
    """Test SSEEvent dataclass with retry field string conversion."""
    event = SSEEvent(data="Hello", retry=5000)
    result = str(event)
    assert result == "data: Hello\nretry: 5000\n"


def test_sse_event_dataclass_all_fields_str():
    """Test SSEEvent dataclass with all fields combined - string output."""
    event = SSEEvent(data="Update", event="update", id=1, retry=5000)
    result = str(event)
    # Field order: id, event, data, retry
    assert result == "id: 1\nevent: update\ndata: Update\nretry: 5000\n"


def test_sse_event_dataclass_field_order():
    """Test SSEEvent dataclass field order: id, event, data, retry."""
    event = SSEEvent(data="test", id="1", event="msg", retry=1000)
    result = str(event)
    lines = result.split("\n")
    assert lines[0] == "id: 1"
    assert lines[1] == "event: msg"
    assert lines[2] == "data: test"
    assert lines[3] == "retry: 1000"


def test_sse_event_dataclass_attribute_access():
    """Test SSEEvent dataclass attribute access."""
    event = SSEEvent(data="Hello", event="message", id=123, retry=5000)
    assert event.data == "Hello"
    assert event.event == "message"
    assert event.id == 123
    assert event.retry == 5000


def test_sse_event_dataclass_with_number():
    """Test SSEEvent dataclass with number data."""
    event = SSEEvent(data=42)
    result = str(event)
    assert result == "data: 42\n"


def test_sse_event_dataclass_empty_string():
    """Test SSEEvent dataclass with empty string data."""
    event = SSEEvent(data="")
    result = str(event)
    assert result == "data: \n"


def test_sse_event_dataclass_with_id():
    """Test SSEEvent with ID field."""
    event = SSEEvent(data="Hello", id=42)
    result = str(event)
    assert result == "id: 42\ndata: Hello\n"


# SSEResponse tests


def _make_sse_app() -> FastAPI:
    """Create a FastAPI app with SSE endpoint."""
    app = FastAPI()

    @app.get("/events")
    async def events():
        async def generator():
            for i in range(3):
                yield sse_event(data=f"Event {i}")

        return SSEResponse(generator())

    return app


def test_sse_response_status_code():
    """Test SSEResponse returns 200 status."""
    app = _make_sse_app()
    client = TestClient(app)
    response = client.get("/events")
    assert response.status_code == 200


def test_sse_response_content_type():
    """Test SSEResponse returns correct Content-Type."""
    app = _make_sse_app()
    client = TestClient(app)
    response = client.get("/events")
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


def test_sse_response_body():
    """Test SSEResponse returns formatted SSE data."""
    app = _make_sse_app()
    client = TestClient(app)
    response = client.get("/events")
    # Check that we get the SSE formatted events
    content = response.text
    assert "data: Event 0" in content
    assert "data: Event 1" in content
    assert "data: Event 2" in content


def _make_sse_with_retry_app() -> FastAPI:
    """Create a FastAPI app with SSE endpoint with retry."""
    app = FastAPI()

    @app.get("/events-retry")
    async def events_retry():
        async def generator():
            yield sse_event(data="Connected", retry=5000)

        return SSEResponse(generator())

    return app


def test_sse_response_with_retry():
    """Test SSEResponse with retry field."""
    app = _make_sse_with_retry_app()
    client = TestClient(app)
    response = client.get("/events-retry")
    assert "retry: 5000" in response.text


def _make_sse_event_type_app() -> FastAPI:
    """Create a FastAPI app with SSE endpoint with event types."""
    app = FastAPI()

    @app.get("/events-type")
    async def events_type():
        async def generator():
            yield sse_event(data="Message 1", event="message")
            yield sse_event(data="Update 1", event="update")

        return SSEResponse(generator())

    return app


def test_sse_response_with_event_type():
    """Test SSEResponse with event types."""
    app = _make_sse_event_type_app()
    client = TestClient(app)
    response = client.get("/events-type")
    content = response.text
    assert "event: message" in content
    assert "event: update" in content


def _make_sse_with_id_app() -> FastAPI:
    """Create a FastAPI app with SSE endpoint with event IDs."""
    app = FastAPI()

    @app.get("/events-id")
    async def events_id():
        async def generator():
            for i in range(3):
                yield sse_event(data=f"Event {i}", id=i)

        return SSEResponse(generator())

    return app


def test_sse_response_with_id():
    """Test SSEResponse with event IDs."""
    app = _make_sse_with_id_app()
    client = TestClient(app)
    response = client.get("/events-id")
    content = response.text
    assert "id: 0" in content
    assert "id: 1" in content
    assert "id: 2" in content


def _make_sse_custom_status_app() -> FastAPI:
    """Create a FastAPI app with SSE endpoint with custom status."""
    app = FastAPI()

    @app.get("/events-custom")
    async def events_custom():
        async def generator():
            yield sse_event(data="Custom status")

        return SSEResponse(generator(), status_code=201)

    return app


def test_sse_response_custom_status():
    """Test SSEResponse with custom status code."""
    app = _make_sse_custom_status_app()
    client = TestClient(app)
    response = client.get("/events-custom")
    assert response.status_code == 201


def _make_sse_with_headers_app() -> FastAPI:
    """Create a FastAPI app with SSE endpoint with custom headers."""
    app = FastAPI()

    @app.get("/events-headers")
    async def events_headers():
        async def generator():
            yield sse_event(data="With headers")

        return SSEResponse(generator(), headers={"X-Custom": "value"})

    return app


def test_sse_response_custom_headers():
    """Test SSEResponse with custom headers."""
    app = _make_sse_with_headers_app()
    client = TestClient(app)
    response = client.get("/events-headers")
    assert response.headers["x-custom"] == "value"


def _make_sse_ssevent_class_app() -> FastAPI:
    """Create a FastAPI app using SSEEvent class."""
    app = FastAPI()

    @app.get("/events-class")
    async def events_class():
        async def generator():
            event = SSEEvent(data="Hello", event="greeting")
            yield str(event)

        return SSEResponse(generator())

    return app


def test_sse_response_with_sse_event_class():
    """Test SSEResponse with SSEEvent dataclass."""
    app = _make_sse_ssevent_class_app()
    client = TestClient(app)
    response = client.get("/events-class")
    assert "event: greeting" in response.text
    assert "data: Hello" in response.text


# Note: OpenAPI schema integration for SSEResponse works at runtime (media_type is set)
# but requires additional FastAPI core changes to include in OpenAPI documentation


def _make_sse_multiline_app() -> FastAPI:
    """Create a FastAPI app with SSE endpoint with multi-line data."""
    app = FastAPI()

    @app.get("/events-multiline")
    async def events_multiline():
        async def generator():
            yield sse_event(data="line1\nline2\nline3")

        return SSEResponse(generator())

    return app


def test_sse_response_multiline_data():
    """Test SSEResponse with multi-line data."""
    app = _make_sse_multiline_app()
    client = TestClient(app)
    response = client.get("/events-multiline")
    content = response.text
    # Verify each line is properly prefixed with "data:"
    assert "data: line1" in content
    assert "data: line2" in content
    assert "data: line3" in content

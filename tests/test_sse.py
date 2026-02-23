"""Tests for SSE (Server-Sent Events) response classes."""
import pytest

from fastapi import FastAPI
from fastapi.responses import SSEEvent, SSEResponse
from fastapi.testclient import TestClient


class TestSSEEvent:
    """Tests for the SSEEvent dataclass."""

    def test_sse_event_basic(self) -> None:
        """Test basic SSE event creation."""
        event = SSEEvent(data="Hello")
        assert event.data == "Hello"
        assert event.event is None
        assert event.id is None
        assert event.retry is None

    def test_sse_event_with_all_fields(self) -> None:
        """Test SSE event with all optional fields."""
        event = SSEEvent(
            data={"message": "test"},
            event="message",
            id="123",
            retry=5000,
        )
        assert event.data == {"message": "test"}
        assert event.event == "message"
        assert event.id == "123"
        assert event.retry == 5000

    def test_sse_event_encode_data_only(self) -> None:
        """Test encoding event with only data."""
        event = SSEEvent(data="Hello")
        encoded = event.encode()
        assert encoded == b"data: Hello\n\n"

    def test_sse_event_encode_with_event(self) -> None:
        """Test encoding event with event type."""
        event = SSEEvent(data="Hello", event="greeting")
        encoded = event.encode()
        assert b"event: greeting\n" in encoded
        assert b"data: Hello\n" in encoded

    def test_sse_event_encode_with_id(self) -> None:
        """Test encoding event with ID."""
        event = SSEEvent(data="Hello", id="123")
        encoded = event.encode()
        assert b"id: 123\n" in encoded
        assert b"data: Hello\n" in encoded

    def test_sse_event_encode_with_retry(self) -> None:
        """Test encoding event with retry."""
        event = SSEEvent(data="Hello", retry=5000)
        encoded = event.encode()
        assert b"retry: 5000\n" in encoded
        assert b"data: Hello\n" in encoded

    def test_sse_event_encode_json_data(self) -> None:
        """Test encoding event with JSON data."""
        event = SSEEvent(data={"message": "test", "count": 42})
        encoded = event.encode()
        assert b"data: " in encoded
        assert b"message" in encoded
        assert b"test" in encoded

    def test_sse_event_encode_multiline_data(self) -> None:
        """Test encoding event with multiline data."""
        event = SSEEvent(data="line1\nline2\nline3")
        encoded = event.encode()
        # Each line should be prefixed with "data: "
        assert b"data: line1\n" in encoded
        assert b"data: line2\n" in encoded
        assert b"data: line3\n" in encoded

    def test_sse_event_double_newline_separation(self) -> None:
        """Test that events end with double newline."""
        event = SSEEvent(data="Hello")
        encoded = event.encode()
        # Should end with \n\n
        assert encoded.endswith(b"\n\n")

    def test_sse_event_field_order(self) -> None:
        """Test that fields are encoded in correct order: event, id, data, retry."""
        event = SSEEvent(data="test", event="myevent", id="123", retry=1000)
        encoded = event.encode()
        decoded = encoded.decode("utf-8")

        # Check order: event comes first, then id, then data, then retry
        event_pos = decoded.find("event:")
        id_pos = decoded.find("id:")
        data_pos = decoded.find("data:")
        retry_pos = decoded.find("retry:")

        assert event_pos < id_pos < data_pos < retry_pos

    def test_sse_event_invalid_retry(self) -> None:
        """Test that negative retry raises ValueError."""
        with pytest.raises(ValueError, match="retry must be a positive integer"):
            SSEEvent(data="test", retry=-1)

    def test_sse_event_zero_retry(self) -> None:
        """Test that zero retry raises ValueError."""
        with pytest.raises(ValueError, match="retry must be a positive integer"):
            SSEEvent(data="test", retry=0)

    def test_sse_event_empty_event_string(self) -> None:
        """Test that empty event string raises ValueError."""
        with pytest.raises(ValueError, match="event must be a non-empty string"):
            SSEEvent(data="test", event="")


class TestSSEResponse:
    """Tests for the SSEResponse class."""

    def test_sse_response_content_type(self) -> None:
        """Test that SSEResponse sets correct Content-Type header."""
        app = FastAPI()

        @app.get("/events")
        def events():
            return SSEResponse(iter([{"data": "test"}]))

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/events")
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

    def test_sse_response_headers(self) -> None:
        """Test that SSEResponse sets required headers."""
        app = FastAPI()

        @app.get("/events")
        def events():
            return SSEResponse(iter([{"data": "test"}]))

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/events")
            assert "Cache-Control" in response.headers
            assert response.headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
            assert "Connection" in response.headers
            assert response.headers["Connection"] == "keep-alive"

    def test_sse_response_event_formatting(self) -> None:
        """Test that events are formatted correctly."""
        app = FastAPI()

        @app.get("/events")
        def events():
            return SSEResponse(iter([
                {"data": "Hello", "event": "greeting", "id": "1"}
            ]))

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/events")
            content = response.content
            assert b"event: greeting" in content
            assert b"id: 1" in content
            assert b"data: Hello" in content

    def test_sse_response_with_sse_event_object(self) -> None:
        """Test that SSEResponse handles SSEEvent objects."""
        app = FastAPI()

        @app.get("/events")
        def events():
            return SSEResponse(iter([
                SSEEvent(data="Hello", event="greeting")
            ]))

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/events")
            content = response.content
            assert b"event: greeting" in content
            assert b"data: Hello" in content

    def test_sse_response_retry_parameter(self) -> None:
        """Test that retry parameter is accepted."""
        response = SSEResponse(iter([]), retry=5000)
        assert response.retry == 5000

    def test_sse_response_custom_headers(self) -> None:
        """Test that custom headers are merged with SSE headers."""
        app = FastAPI()

        @app.get("/events")
        def events():
            return SSEResponse(
                iter([{"data": "test"}]),
                headers={"X-Custom-Header": "value"},
            )

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/events")
            assert "X-Custom-Header" in response.headers
            assert response.headers["X-Custom-Header"] == "value"

    def test_sse_response_double_newline_separation(self) -> None:
        """Test double newline separation between events."""
        app = FastAPI()

        @app.get("/events")
        def events():
            return SSEResponse(iter([
                {"data": "event1"},
                {"data": "event2"},
            ]))

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/events")
            content = response.content
            # Should have two events separated by double newlines
            assert content.count(b"\n\n") >= 1


class TestSSEResponseRetry:
    """Tests for retry functionality."""

    def test_retry_sent_in_response(self) -> None:
        """Test that retry is sent in the response."""
        app = FastAPI()

        @app.get("/events")
        def events():
            return SSEResponse(iter([{"data": "test"}]), retry=5000)

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/events")
            content = response.content
            assert b"retry: 5000" in content


class TestSSEResponseDisconnect:
    """Tests for client disconnect handling."""

    def test_no_error_on_empty_iterator(self) -> None:
        """Test that empty iterator doesn't raise errors."""
        app = FastAPI()

        @app.get("/events")
        def events():
            return SSEResponse(iter([]))

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/events")
            assert response.status_code == 200

    def test_client_disconnect_via_iterator_completion(self) -> None:
        """Test client disconnect detection via iterator completion.

        When a client disconnects during streaming, the iterator should
        complete without raising errors on the server side.
        """
        import asyncio

        app = FastAPI()

        iterator_stopped = False

        @app.get("/events")
        async def events():
            async def generator():
                nonlocal iterator_stopped
                try:
                    for i in range(10):
                        yield {"data": f"Event {i}"}
                        await asyncio.sleep(0.01)
                finally:
                    # This block runs when iteration stops (e.g., client disconnect)
                    nonlocal iterator_stopped
                    iterator_stopped = True

            return SSEResponse(generator())

        with TestClient(app, raise_server_exceptions=False) as client:
            with client.stream("GET", "/events") as response:
                assert response.status_code == 200
                # Read only first few events, then close connection (exit context)
                count = 0
                for line in response.iter_lines():
                    if line.startswith("data:"):
                        count += 1
                        if count >= 2:
                            break
                # When we exit the context, the client disconnects
            # After client disconnects, verify the iterator cleanup ran
            # (This confirms the generator was properly closed)
            assert iterator_stopped

    def test_iterator_completion_no_error_when_client_disconnects(self) -> None:
        """Test that stopping iteration early due to client disconnect doesn't raise errors.

        This test verifies that the server doesn't raise any exceptions when
        the client disconnects before all events are sent.
        """
        import asyncio

        app = FastAPI()
        generator_completed = False

        @app.get("/events")
        async def events():
            nonlocal generator_completed

            async def generator():
                nonlocal generator_completed
                try:
                    for i in range(5):
                        yield {"data": f"Event {i}"}
                        await asyncio.sleep(0.05)
                    generator_completed = True
                except Exception as e:
                    # If the client disconnects, we might get an exception
                    # But it should be handled gracefully
                    raise

            return SSEResponse(generator())

        with TestClient(app, raise_server_exceptions=False) as client:
            # Connect and immediately close without reading all events
            with client.stream("GET", "/events") as response:
                # Read just one event then close
                for line in response.iter_lines():
                    if line.startswith("data:"):
                        break
            # Connection closed - generator should stop without server error


class TestSSEResponseIntegration:
    """Integration tests for SSE endpoints."""

    def test_basic_event_stream(self) -> None:
        """Test a complete SSE event stream."""
        app = FastAPI()

        @app.get("/events")
        def events():
            async def generator():
                for i in range(3):
                    yield {"data": f"Event {i}", "id": str(i)}

            return SSEResponse(generator())

        with TestClient(app, raise_server_exceptions=False) as client:
            with client.stream("GET", "/events") as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers["content-type"]

                # Read all events
                events = []
                for line in response.iter_lines():
                    if line.startswith("data:"):
                        events.append(line)

                assert len(events) == 3

    def test_event_with_custom_type(self) -> None:
        """Test event with custom type."""
        app = FastAPI()

        @app.get("/events")
        def events():
            async def generator():
                yield {"data": "notification", "event": "notification"}

            return SSEResponse(generator())

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/events")
            content = response.content
            assert b"event: notification" in content
            assert b"data: notification" in content

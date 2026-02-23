import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(
    name="client",
    params=[
        pytest.param("tutorial011_py310"),
    ],
)
def get_client(request: pytest.FixtureRequest):
    mod = importlib.import_module(f"docs_src.custom_response.{request.param}")
    client = TestClient(mod.app)
    return client


def test_get_sse_response(client: TestClient):
    response = client.get("/events")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    # Check that events are formatted correctly
    content = response.text
    assert "data:" in content
    assert "message 0" in content


def test_sse_with_event_type(client: TestClient):
    response = client.get("/events/with-event")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    content = response.text
    assert "event: message" in content
    assert "data:" in content


def test_sse_with_retry(client: TestClient):
    response = client.get("/events/with-retry")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    content = response.text
    assert "retry: 5000" in content
    assert "data:" in content


def test_openapi_schema(client: TestClient):
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    schema = response.json()
    # Check that SSE endpoint is in the schema
    paths = schema.get("paths", {})
    assert "/events" in paths
    event_path = paths["/events"]["get"]
    # Check response media type
    responses = event_path.get("responses", {})
    response_200 = responses.get("200", {})
    content = response_200.get("content", {})
    assert "text/event-stream" in content

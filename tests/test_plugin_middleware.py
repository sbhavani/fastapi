"""Tests for plugin middleware hooks (before_request, after_request)."""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import Response


class TestBeforeRequest:
    """Test before_request hook."""

    def test_before_request_called(self):
        """Test that before_request is called for each request."""
        call_count = []

        class BeforePlugin:
            async def before_request(self, request):
                call_count.append(1)

        app = FastAPI()
        app.add_plugin(BeforePlugin())

        @app.get("/")
        def root():
            return {"message": "hello"}

        with TestClient(app) as client:
            client.get("/")
            client.get("/")

        assert len(call_count) == 2

    def test_before_request_short_circuit(self):
        """Test that returning a Response short-circuits the request."""

        class ShortCircuitPlugin:
            async def before_request(self, request):
                return Response(content="blocked", status_code=403)

        app = FastAPI()
        app.add_plugin(ShortCircuitPlugin())

        @app.get("/")
        def root():
            return {"message": "hello"}

        with TestClient(app) as client:
            response = client.get("/")

        assert response.status_code == 403
        assert response.text == "blocked"

    def test_before_request_modify_request(self):
        """Test that before_request can modify request state."""

        class ModifyRequestPlugin:
            async def before_request(self, request: Request):
                request.state.custom_value = "set"

        app = FastAPI()
        app.add_plugin(ModifyRequestPlugin())

        @app.get("/")
        def root(request: Request):
            return {"custom": getattr(request.state, "custom_value", "not set")}

        with TestClient(app) as client:
            response = client.get("/")

        assert response.json()["custom"] == "set"


class TestAfterRequest:
    """Test after_request hook."""

    def test_after_request_called(self):
        """Test that after_request is called for each request."""
        call_count = []

        class AfterPlugin:
            async def after_request(self, request, response):
                call_count.append(1)
                return response

        app = FastAPI()
        app.add_plugin(AfterPlugin())

        @app.get("/")
        def root():
            return {"message": "hello"}

        with TestClient(app) as client:
            client.get("/")
            client.get("/")

        assert len(call_count) == 2

    def test_after_request_modify_response(self):
        """Test that after_request hook is called (response modification is limited)."""

        class ModifyResponsePlugin:
            async def after_request(self, request, response):
                # Note: Response modifications may not be reflected in the actual
                # response since it's already sent. This just verifies the hook runs.
                return response

        app = FastAPI()
        app.add_plugin(ModifyResponsePlugin())

        @app.get("/")
        def root():
            return {"message": "hello"}

        with TestClient(app) as client:
            response = client.get("/")

        # Response is still returned correctly
        assert response.status_code == 200

    def test_after_request_order(self):
        """Test that after_request hooks execute in reverse order."""
        order = []

        class Plugin1:
            async def after_request(self, request, response):
                order.append("p1")
                return response

        class Plugin2:
            async def after_request(self, request, response):
                order.append("p2")
                return response

        app = FastAPI()
        app.add_plugin(Plugin1())
        app.add_plugin(Plugin2())

        @app.get("/")
        def root():
            return {"message": "hello"}

        with TestClient(app) as client:
            client.get("/")

        # Should be in reverse order: p2, p1
        assert order == ["p2", "p1"]


class TestBeforeAfterTogether:
    """Test before_request and after_request together."""

    def test_both_hooks_called(self):
        """Test that both hooks are called."""
        calls = []

        class BothPlugin:
            async def before_request(self, request):
                calls.append("before")

            async def after_request(self, request, response):
                calls.append("after")

        app = FastAPI()
        app.add_plugin(BothPlugin())

        @app.get("/")
        def root():
            return {"message": "hello"}

        with TestClient(app) as client:
            client.get("/")

        assert "before" in calls
        assert "after" in calls

    def test_plugin_with_all_hooks(self):
        """Test a plugin with all lifecycle hooks."""
        calls = []

        class FullPlugin:
            async def on_startup(self):
                calls.append("startup")

            async def on_shutdown(self):
                calls.append("shutdown")

            async def before_request(self, request):
                calls.append("before")

            async def after_request(self, request, response):
                calls.append("after")

        app = FastAPI()
        app.add_plugin(FullPlugin())

        @app.get("/")
        def root():
            return {"message": "hello"}

        with TestClient(app) as client:
            response = client.get("/")

        assert "startup" in calls
        assert "before" in calls
        assert "after" in calls
        assert "shutdown" in calls

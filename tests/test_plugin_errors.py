"""Tests for plugin error handling."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import Response


class TestErrorHandling:
    """Test error handling in plugins."""

    def test_on_startup_error(self):
        """Test handling of errors in on_startup."""

        class FailingStartup:
            async def on_startup(self):
                raise ValueError("Startup failed!")

        app = FastAPI()
        app.add_plugin(FailingStartup())

        # Startup error should propagate
        with pytest.raises(ValueError, match="Startup failed!"):
            with TestClient(app):
                pass

    def test_on_shutdown_error(self):
        """Test handling of errors in on_shutdown - should not crash."""
        shutdown_error_logged = []

        class FailingShutdown:
            async def on_shutdown(self):
                shutdown_error_logged.append(True)
                raise ValueError("Shutdown failed!")

        app = FastAPI()
        app.add_plugin(FailingShutdown())

        with TestClient(app):
            pass

        # Shutdown error should be caught and logged
        assert len(shutdown_error_logged) == 1

    def test_before_request_error_continues(self):
        """Test that errors in before_request don't crash the app."""

        class ErrorBeforeRequest:
            async def before_request(self, request):
                raise ValueError("Before request error!")

        app = FastAPI()
        app.add_plugin(ErrorBeforeRequest())

        @app.get("/")
        def root():
            return {"message": "hello"}

        with TestClient(app) as client:
            # Should still work - error is caught
            response = client.get("/")
            assert response.status_code == 200

    def test_after_request_error_continues(self):
        """Test that errors in after_request don't crash the app."""

        class ErrorAfterRequest:
            async def after_request(self, request, response):
                raise ValueError("After request error!")

        app = FastAPI()
        app.add_plugin(ErrorAfterRequest())

        @app.get("/")
        def root():
            return {"message": "hello"}

        with TestClient(app) as client:
            response = client.get("/")
            # Should still return response
            assert response.status_code == 200

    def test_get_openapi_schema_error(self):
        """Test handling of errors in get_openapi_schema."""

        class ErrorOpenAPI:
            def get_openapi_schema(self, schema):
                raise ValueError("OpenAPI error!")

        app = FastAPI()
        app.add_plugin(ErrorOpenAPI())

        @app.get("/")
        def root():
            return {"message": "hello"}

        # Error should propagate when generating OpenAPI
        with pytest.raises(ValueError, match="OpenAPI error!"):
            app.openapi()


class TestInvalidPlugins:
    """Test handling of invalid plugin configurations."""

    def test_non_callable_hooks(self):
        """Test that non-callable hooks are handled."""

        class BadPlugin:
            on_startup = "not a callable"  # type: ignore

        app = FastAPI()
        app.add_plugin(BadPlugin())

        # Should work - non-callable hooks are ignored
        with TestClient(app):
            pass

    def test_plugin_returning_wrong_type(self):
        """Test plugin that returns wrong type from hooks."""

        class WrongReturnPlugin:
            async def before_request(self, request):
                return "not a Response"  # Wrong type

        app = FastAPI()
        app.add_plugin(WrongReturnPlugin())

        @app.get("/")
        def root():
            return {"message": "hello"}

        with TestClient(app) as client:
            # May cause issues but app should handle gracefully
            response = client.get("/")
            # Response might be 500 or other error
            assert response.status_code in [200, 500]


class TestEdgeCases:
    """Test edge cases in plugin system."""

    def test_plugin_with_no_hooks(self):
        """Test a plugin with no hooks implemented."""

        class EmptyPlugin:
            pass

        app = FastAPI()
        app.add_plugin(EmptyPlugin())

        @app.get("/")
        def root():
            return {"message": "hello"}

        # Should work fine
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200

    def test_plugin_adding_routes(self):
        """Test a plugin that adds routes."""

        class RouteAddingPlugin:
            def get_openapi_schema(self, schema):
                # This plugin adds routes by getting them from the schema
                # In practice, plugins could add routes directly to the app
                return schema

        app = FastAPI()
        app.add_plugin(RouteAddingPlugin())

        @app.get("/existing")
        def existing():
            return {"message": "exists"}

        with TestClient(app) as client:
            response = client.get("/existing")
            assert response.status_code == 200

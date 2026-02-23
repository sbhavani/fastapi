"""Tests for plugin composability - multiple plugins coexisting."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestPluginComposability:
    """Test that multiple plugins can coexist without conflicts."""

    def test_different_plugin_types(self):
        """Test plugins with different hook combinations."""
        calls = []

        class StartupOnly:
            async def on_startup(self):
                calls.append("startup-only")

        class MiddlewareOnly:
            async def before_request(self, request):
                calls.append("before-middleware")
                return None

            async def after_request(self, request, response):
                calls.append("after-middleware")
                return response

        class OpenAPIOnly:
            def get_openapi_schema(self, schema):
                calls.append("openapi")
                return schema

        class FullPlugin:
            async def on_startup(self):
                calls.append("startup-full")

            async def on_shutdown(self):
                calls.append("shutdown-full")

            async def before_request(self, request):
                calls.append("before-full")
                return None

            async def after_request(self, request, response):
                calls.append("after-full")
                return response

            def get_openapi_schema(self, schema):
                calls.append("openapi-full")
                return schema

        app = FastAPI()
        app.add_plugin(StartupOnly())
        app.add_plugin(MiddlewareOnly())
        app.add_plugin(OpenAPIOnly())
        app.add_plugin(FullPlugin())

        @app.get("/")
        def root():
            return {"message": "hello"}

        with TestClient(app) as client:
            client.get("/")
            # Generate OpenAPI to trigger schema extension hooks
            client.get("/openapi.json")

        # Startup hooks called
        assert "startup-only" in calls
        assert "startup-full" in calls

        # Middleware hooks called
        assert "before-middleware" in calls
        assert "before-full" in calls
        assert "after-middleware" in calls
        assert "after-full" in calls

        # OpenAPI called
        assert "openapi" in calls
        assert "openapi-full" in calls

    def test_plugin_isolation(self):
        """Test that plugins don't interfere with each other."""

        class PluginA:
            def __init__(self):
                self.state = {}

            async def before_request(self, request):
                self.state["a"] = "set by A"
                return None

            async def after_request(self, request, response):
                # Note: Response modifications may not be reflected
                return response

        class PluginB:
            def __init__(self):
                self.state = {}

            async def before_request(self, request):
                self.state["b"] = "set by B"
                return None

            async def after_request(self, request, response):
                return response

        plugin_a = PluginA()
        plugin_b = PluginB()

        app = FastAPI()
        app.add_plugin(plugin_a)
        app.add_plugin(plugin_b)

        @app.get("/")
        def root():
            return {"message": "hello"}

        with TestClient(app) as client:
            response = client.get("/")

        # Response works
        assert response.status_code == 200

        # State is isolated
        assert plugin_a.state.get("a") == "set by A"
        assert plugin_b.state.get("b") == "set by B"

    def test_plugin_order_preserved(self):
        """Test that plugin execution order is preserved."""
        order = []

        class Plugin1:
            async def on_startup(self):
                order.append("startup_1")

            async def on_shutdown(self):
                order.append("shutdown_1")

            async def before_request(self, request):
                order.append("before_1")
                return None

            async def after_request(self, request, response):
                order.append("after_1")
                return response

        class Plugin2:
            async def on_startup(self):
                order.append("startup_2")

            async def on_shutdown(self):
                order.append("shutdown_2")

            async def before_request(self, request):
                order.append("before_2")
                return None

            async def after_request(self, request, response):
                order.append("after_2")
                return response

        app = FastAPI()
        app.add_plugin(Plugin1())
        app.add_plugin(Plugin2())

        @app.get("/")
        def root():
            return {"message": "hello"}

        with TestClient(app) as client:
            client.get("/")

        # Startup hooks execute in registration order (Plugin1, then Plugin2)
        startup_indices = [i for i, x in enumerate(order) if x.startswith("startup_")]
        assert len(startup_indices) == 2
        assert order[startup_indices[0]] == "startup_1"
        assert order[startup_indices[1]] == "startup_2"

        # Before_request hooks execute in registration order (Plugin1, then Plugin2)
        before_indices = [i for i, x in enumerate(order) if x.startswith("before_")]
        assert len(before_indices) == 2
        assert order[before_indices[0]] == "before_1"
        assert order[before_indices[1]] == "before_2"

        # After_request hooks execute in reverse registration order (Plugin2, then Plugin1)
        after_indices = [i for i, x in enumerate(order) if x.startswith("after_")]
        assert len(after_indices) == 2
        assert order[after_indices[0]] == "after_2"
        assert order[after_indices[1]] == "after_1"

        # Shutdown hooks execute in reverse registration order (Plugin2, then Plugin1)
        shutdown_indices = [i for i, x in enumerate(order) if x.startswith("shutdown_")]
        assert len(shutdown_indices) == 2
        assert order[shutdown_indices[0]] == "shutdown_2"
        assert order[shutdown_indices[1]] == "shutdown_1"

    def test_plugins_with_dependencies(self):
        """Test plugins that might have dependencies."""

        class DatabasePlugin:
            def __init__(self):
                self.connected = False

            async def on_startup(self):
                self.connected = True

            async def on_shutdown(self):
                self.connected = False

        class AuthPlugin:
            def __init__(self, db_plugin: DatabasePlugin):
                self.db = db_plugin

            async def on_startup(self):
                # Can access db plugin's resources
                assert self.db.connected

        db_plugin = DatabasePlugin()
        auth_plugin = AuthPlugin(db_plugin)

        app = FastAPI()
        app.add_plugin(db_plugin)
        app.add_plugin(auth_plugin)

        with TestClient(app):
            pass

        # Both plugins should have been called
        assert db_plugin.connected is False  # After shutdown

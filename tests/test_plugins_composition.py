"""Tests for plugin composition - multiple plugins working together."""
import pytest
from fastapi import FastAPI
from fastapi.plugins import PluginProtocol
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response


class TrackingPlugin:
    """Plugin that tracks calls and state."""

    def __init__(self, name: str):
        self.name = name
        self.calls = []

    async def on_startup(self) -> None:
        self.calls.append("startup")

    async def on_shutdown(self) -> None:
        self.calls.append("shutdown")

    async def before_request(self, request: Request) -> Response | None:
        self.calls.append(f"before_{self.name}")
        return None

    async def after_request(
        self, request: Request, response: Response
    ) -> Response:
        self.calls.append(f"after_{self.name}")
        return response


def test_multiple_plugins_no_interference():
    """Test that multiple plugins don't interfere with each other."""
    plugin1 = TrackingPlugin("plugin1")
    plugin2 = TrackingPlugin("plugin2")
    plugin3 = TrackingPlugin("plugin3")

    app = FastAPI()
    app.add_plugin(plugin1)
    app.add_plugin(plugin2)
    app.add_plugin(plugin3)

    @app.get("/")
    def root():
        return {"message": "hello"}

    import asyncio

    async def run_test():
        # Run lifecycle
        await app._plugins.on_startup()
        await app._plugins.on_shutdown()

    asyncio.run(run_test())

    # Each plugin should have its own state
    assert plugin1.calls == ["startup", "shutdown"]
    assert plugin2.calls == ["startup", "shutdown"]
    assert plugin3.calls == ["startup", "shutdown"]


def test_plugin_error_isolation():
    """Test that one plugin's error doesn't affect others."""

    class ErrorPlugin:
        async def on_startup(self) -> None:
            raise RuntimeError("Plugin error")

    plugin1 = TrackingPlugin("working1")
    error_plugin = ErrorPlugin()
    plugin2 = TrackingPlugin("working2")

    app = FastAPI()
    app.add_plugin(plugin1)
    app.add_plugin(error_plugin)
    app.add_plugin(plugin2)

    import asyncio

    async def run_test():
        # Should not raise - errors should be caught
        await app._plugins.on_startup()
        # Working plugins should still have their hooks called
        assert "startup" in plugin1.calls
        assert "startup" in plugin2.calls

    asyncio.run(run_test())


def test_plugin_execution_order_startup():
    """Test execution order for startup across multiple plugins."""
    order = []

    class OrderPlugin:
        def __init__(self, name: str):
            self.name = name

        async def on_startup(self) -> None:
            order.append(self.name)

    app = FastAPI()
    app.add_plugin(OrderPlugin("a"))
    app.add_plugin(OrderPlugin("b"))
    app.add_plugin(OrderPlugin("c"))

    import asyncio

    async def run_test():
        await app._plugins.on_startup()

    asyncio.run(run_test())

    assert order == ["a", "b", "c"]


def test_plugin_execution_order_shutdown():
    """Test execution order for shutdown across multiple plugins."""
    order = []

    class OrderPlugin:
        def __init__(self, name: str):
            self.name = name

        async def on_shutdown(self) -> None:
            order.append(self.name)

    app = FastAPI()
    app.add_plugin(OrderPlugin("a"))
    app.add_plugin(OrderPlugin("b"))
    app.add_plugin(OrderPlugin("c"))

    import asyncio

    async def run_test():
        await app._plugins.on_shutdown()

    asyncio.run(run_test())

    # Should be reverse order
    assert order == ["c", "b", "a"]


def test_plugin_with_different_capabilities():
    """Test plugins with different subsets of capabilities."""

    class StartupOnly:
        async def on_startup(self) -> None:
            self.started = True

    class RequestOnly:
        async def before_request(self, request: Request) -> Response | None:
            self.before_called = True
            return None

        async def after_request(
            self, request: Request, response: Response
        ) -> Response:
            self.after_called = True
            return response

    class OpenAPIOnly:
        @property
        def openapi_schema(self) -> dict | None:
            return {"components": {"test": "value"}}

    class EmptyPlugin:
        pass  # No capabilities

    startup_plugin = StartupOnly()
    request_plugin = RequestOnly()
    openapi_plugin = OpenAPIOnly()
    empty_plugin = EmptyPlugin()

    app = FastAPI()
    app.add_plugin(startup_plugin)
    app.add_plugin(request_plugin)
    app.add_plugin(openapi_plugin)
    app.add_plugin(empty_plugin)

    # All should work without errors
    import asyncio

    async def run_test():
        await app._plugins.on_startup()
        assert startup_plugin.started

    asyncio.run(run_test())

    # Check OpenAPI
    schema = app._plugins.get_openapi_contributions()
    assert "components" in schema
    assert schema["components"]["test"] == "value"


def test_plugin_registry_iteration():
    """Test that we can iterate over registered plugins."""
    plugin1 = TrackingPlugin("p1")
    plugin2 = TrackingPlugin("p2")

    app = FastAPI()
    app.add_plugin(plugin1)
    app.add_plugin(plugin2)

    plugins = list(app.plugins)
    assert len(plugins) == 2
    assert plugin1 in plugins
    assert plugin2 in plugins


def test_plugin_registry_length():
    """Test that len() works on plugin registry."""
    app = FastAPI()
    assert len(app.plugins) == 0

    app.add_plugin(TrackingPlugin("p1"))
    assert len(app.plugins) == 1

    app.add_plugin(TrackingPlugin("p2"))
    assert len(app.plugins) == 2

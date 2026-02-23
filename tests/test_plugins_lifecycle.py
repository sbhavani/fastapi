"""Tests for plugin lifecycle hooks (startup/shutdown)."""
import pytest
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.plugins import PluginProtocol


class LifecycleTracker:
    """Track lifecycle hook calls."""

    def __init__(self, name: str):
        self.name = name
        self.startup_called = False
        self.shutdown_called = False

    async def on_startup(self) -> None:
        self.startup_called = True

    async def on_shutdown(self) -> None:
        self.shutdown_called = True


def test_plugin_startup_called():
    """Test that on_startup is called when app starts."""
    tracker = LifecycleTracker("test")

    app = FastAPI()
    app.add_plugin(tracker)

    # Simulate startup via lifespan
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        await app._plugins.on_startup()
        yield
        # Shutdown
        await app._plugins.on_shutdown()

    # Run lifespan
    import asyncio

    async def run_test():
        async with lifespan(app):
            assert tracker.startup_called, "on_startup should be called"

        assert tracker.shutdown_called, "on_shutdown should be called"

    asyncio.run(run_test())


def test_plugin_startup_order():
    """Test that startup hooks execute in registration order (FIFO)."""
    order = []

    class OrderedPlugin:
        def __init__(self, name: str):
            self.name = name

        async def on_startup(self) -> None:
            order.append(self.name)

    plugin1 = OrderedPlugin("first")
    plugin2 = OrderedPlugin("second")
    plugin3 = OrderedPlugin("third")

    app = FastAPI()
    app.add_plugin(plugin1)
    app.add_plugin(plugin2)
    app.add_plugin(plugin3)

    import asyncio

    async def run_test():
        await app._plugins.on_startup()

    asyncio.run(run_test())

    assert order == ["first", "second", "third"], "Should execute in registration order"


def test_plugin_shutdown_order():
    """Test that shutdown hooks execute in reverse order (LIFO)."""
    order = []

    class OrderedPlugin:
        def __init__(self, name: str):
            self.name = name

        async def on_shutdown(self) -> None:
            order.append(self.name)

    plugin1 = OrderedPlugin("first")
    plugin2 = OrderedPlugin("second")
    plugin3 = OrderedPlugin("third")

    app = FastAPI()
    app.add_plugin(plugin1)
    app.add_plugin(plugin2)
    app.add_plugin(plugin3)

    import asyncio

    async def run_test():
        await app._plugins.on_shutdown()

    asyncio.run(run_test())

    assert order == ["third", "second", "first"], "Should execute in reverse order"


def test_plugin_startup_error_handling():
    """Test that startup errors are handled gracefully."""

    class FailingPlugin:
        async def on_startup(self) -> None:
            raise RuntimeError("Startup failed")

    class WorkingPlugin:
        async def on_startup(self) -> None:
            self.called = True

    failing = FailingPlugin()
    working = WorkingPlugin()

    app = FastAPI()
    app.add_plugin(failing)
    app.add_plugin(working)

    import asyncio

    async def run_test():
        # Should not raise - errors should be caught
        await app._plugins.on_startup()
        # Working plugin should still be called
        assert working.called

    asyncio.run(run_test())


def test_plugin_shutdown_error_handling():
    """Test that shutdown errors are handled gracefully."""

    class FailingPlugin:
        async def on_shutdown(self) -> None:
            raise RuntimeError("Shutdown failed")

    class WorkingPlugin:
        async def on_shutdown(self) -> None:
            self.called = True

    failing = FailingPlugin()
    working = WorkingPlugin()

    app = FastAPI()
    app.add_plugin(failing)
    app.add_plugin(working)

    import asyncio

    async def run_test():
        # Should not raise - errors should be caught
        await app._plugins.on_shutdown()
        # Working plugin should still be called
        assert working.called

    asyncio.run(run_test())

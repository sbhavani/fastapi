"""Tests for plugin lifecycle hooks."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestLifecycleHooks:
    """Test plugin lifecycle hooks."""

    def test_on_startup_called(self):
        """Test that on_startup is called when app starts."""
        startup_called = []

        class StartupPlugin:
            async def on_startup(self):
                startup_called.append(True)

        app = FastAPI()
        app.add_plugin(StartupPlugin())

        with TestClient(app):
            pass  # App startup happens when entering context

        assert len(startup_called) == 1

    def test_on_shutdown_called(self):
        """Test that on_shutdown is called when app stops."""
        shutdown_called = []

        class ShutdownPlugin:
            async def on_shutdown(self):
                shutdown_called.append(True)

        app = FastAPI()
        app.add_plugin(ShutdownPlugin())

        with TestClient(app):
            pass  # App starts

        # App shutdown happens when exiting context
        assert len(shutdown_called) == 1

    def test_lifecycle_order(self):
        """Test that plugins execute in registration order."""
        order = []

        class Plugin1:
            async def on_startup(self):
                order.append(1)

            async def on_shutdown(self):
                order.append(3)

        class Plugin2:
            async def on_startup(self):
                order.append(2)

            async def on_shutdown(self):
                order.append(4)

        app = FastAPI()
        app.add_plugin(Plugin1())
        app.add_plugin(Plugin2())

        with TestClient(app):
            pass

        # Startup: 1, 2 (in order)
        # Shutdown: 4, 3 (in reverse order - Plugin2 then Plugin1)
        assert order[:2] == [1, 2]
        assert order[2:] == [4, 3]


class TestMultiplePlugins:
    """Test multiple plugin lifecycle."""

    def test_multiple_plugins_all_called(self):
        """Test that all plugins have hooks called."""
        startup_order = []
        shutdown_order = []

        class Plugin1:
            async def on_startup(self):
                startup_order.append("p1")

            async def on_shutdown(self):
                shutdown_order.append("p1")

        class Plugin2:
            async def on_startup(self):
                startup_order.append("p2")

            async def on_shutdown(self):
                shutdown_order.append("p2")

        app = FastAPI()
        app.add_plugin(Plugin1())
        app.add_plugin(Plugin2())

        with TestClient(app):
            pass

        assert startup_order == ["p1", "p2"]
        assert shutdown_order == ["p2", "p1"]  # Reverse order

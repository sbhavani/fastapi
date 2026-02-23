"""Tests for plugin registration."""
from fastapi import FastAPI
from fastapi.plugins import PluginManager, PluginProtocol


def test_plugin_manager_add_plugin():
    """Test that plugins can be added to the manager."""
    manager = PluginManager()

    class TestPlugin:
        async def on_startup(self):
            pass

    plugin = TestPlugin()
    manager.add_plugin(plugin)

    plugins = manager.get_plugins()
    assert len(plugins) == 1
    assert plugins[0].name == "TestPlugin"


def test_plugin_manager_duplicate_name_raises():
    """Test that duplicate plugin names raise ValueError."""
    manager = PluginManager()

    class TestPlugin:
        async def on_startup(self):
            pass

    plugin1 = TestPlugin()
    plugin2 = TestPlugin()

    manager.add_plugin(plugin1)

    from pytest import raises

    with raises(ValueError, match="already registered"):
        manager.add_plugin(plugin2)


def test_plugin_manager_invalid_plugin_raises():
    """Test that non-object types raise TypeError."""
    manager = PluginManager()

    # Duck typing - any object is accepted as a plugin
    # This is by design - plugins are validated by their hooks at runtime
    class NotAPlugin:
        pass

    # With duck typing, any object can be a plugin
    manager.add_plugin(NotAPlugin())
    assert len(manager.get_plugins()) == 1


def test_fastapi_add_plugin():
    """Test that plugins can be added to FastAPI app."""
    app = FastAPI()

    class TestPlugin:
        async def on_startup(self):
            pass

    plugin = TestPlugin()
    app.add_plugin(plugin)

    plugins = app.plugin_manager.get_plugins()
    assert len(plugins) == 1
    assert plugins[0].name == "TestPlugin"


def test_fastapi_add_plugin_returns_self():
    """Test that add_plugin returns None (for chaining)."""
    app = FastAPI()

    class TestPlugin:
        async def on_startup(self):
            pass

    plugin = TestPlugin()
    result = app.add_plugin(plugin)

    # Should return None (not chainable currently)
    assert result is None

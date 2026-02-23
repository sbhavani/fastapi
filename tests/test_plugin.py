"""Tests for the FastAPI plugin system."""

import pytest
from fastapi import FastAPI
from fastapi.plugin import Plugin, PluginProtocol, merge_openapi_schemas
from fastapi.requests import Request
from fastapi.responses import Response


def test_plugin_protocol_exists():
    """Test that PluginProtocol is available."""
    assert PluginProtocol is not None


def test_plugin_class_exists():
    """Test that Plugin base class is available."""
    assert Plugin is not None


def test_plugin_base_class_has_hooks():
    """Test that Plugin base class has all hook methods."""
    plugin = Plugin()
    assert hasattr(plugin, "on_startup")
    assert hasattr(plugin, "on_shutdown")
    assert hasattr(plugin, "before_request")
    assert hasattr(plugin, "after_request")
    assert hasattr(plugin, "openapi_schema")


def test_custom_plugin_class():
    """Test creating a custom plugin class."""

    class MyPlugin(Plugin):
        def __init__(self):
            self.startup_called = False
            self.shutdown_called = False
            self.before_called = False
            self.after_called = False

        def on_startup(self, app: FastAPI) -> None:
            self.startup_called = True

        def on_shutdown(self, app: FastAPI) -> None:
            self.shutdown_called = True

        def before_request(self, request: Request) -> None:
            self.before_called = True

        def after_request(self, request: Request, response: Response) -> None:
            self.after_called = True

        def openapi_schema(self):
            return {
                "components": {
                    "schemas": {
                        "CustomSchema": {
                            "type": "object",
                            "properties": {
                                "custom_field": {"type": "string"}
                            }
                        }
                    }
                }
            }

    plugin = MyPlugin()
    assert plugin.startup_called is False
    assert plugin.shutdown_called is False
    assert plugin.before_called is False
    assert plugin.after_called is False


def test_plugin_with_protocol():
    """Test creating a plugin using the Protocol interface."""

    class MyProtocolPlugin:
        def on_startup(self, app: FastAPI) -> None:
            pass

        def on_shutdown(self, app: FastAPI) -> None:
            pass

        def before_request(self, request: Request) -> None:
            pass

        def after_request(self, request: Request, response: Response) -> None:
            pass

        def openapi_schema(self):
            return None

    # Verify it implements the protocol
    assert isinstance(MyProtocolPlugin(), PluginProtocol)


def test_app_plugins_list():
    """Test that FastAPI app has a plugins list."""
    app = FastAPI()
    assert hasattr(app, "plugins")
    assert isinstance(app.plugins, list)
    assert len(app.plugins) == 0


def test_app_with_plugin():
    """Test adding a plugin to the FastAPI app."""

    class TestPlugin(Plugin):
        def __init__(self):
            self.startup_called = False

        def on_startup(self, app: FastAPI) -> None:
            self.startup_called = True

    plugin = TestPlugin()
    app = FastAPI()
    app.plugins.append(plugin)

    assert len(app.plugins) == 1
    assert app.plugins[0] is plugin


def test_merge_openapi_schemas_empty():
    """Test merging with empty base schema."""
    base = {}
    extensions = []
    result = merge_openapi_schemas(base, extensions)
    assert result == {}


def test_merge_openapi_schemas_with_extension():
    """Test merging OpenAPI schemas with extensions."""
    base = {
        "openapi": "3.1.0",
        "info": {"title": "Test", "version": "1.0.0"},
        "paths": {},
        "components": {"schemas": {}},
    }
    extensions = [
        {
            "components": {
                "schemas": {
                    "CustomSchema": {
                        "type": "object",
                        "properties": {"field": {"type": "string"}}
                    }
                }
            }
        }
    ]
    result = merge_openapi_schemas(base, extensions)
    assert "CustomSchema" in result.get("components", {}).get("schemas", {})


def test_merge_openapi_schemas_multiple():
    """Test merging multiple OpenAPI schema extensions."""
    base = {
        "components": {"schemas": {}}
    }
    extensions = [
        {"components": {"schemas": {"Schema1": {"type": "object"}}}},
        {"components": {"schemas": {"Schema2": {"type": "object"}}}},
    ]
    result = merge_openapi_schemas(base, extensions)
    assert "Schema1" in result["components"]["schemas"]
    assert "Schema2" in result["components"]["schemas"]


def test_merge_openapi_schemas_security():
    """Test merging security schemes."""
    base = {"security": []}
    extensions = [
        {"security": [{"apiKey": []}]},
        {"security": [{"oauth2": []}]},
    ]
    result = merge_openapi_schemas(base, extensions)
    assert len(result["security"]) == 2


def test_plugin_openapi_extension():
    """Test that plugin OpenAPI schema is included in app schema."""

    class SchemaPlugin(Plugin):
        def openapi_schema(self):
            return {
                "components": {
                    "schemas": {
                        "PluginSchema": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"}
                            }
                        }
                    }
                }
            }

    app = FastAPI()
    plugin = SchemaPlugin()
    app.plugins.append(plugin)

    schema = app.openapi()
    assert "PluginSchema" in schema.get("components", {}).get("schemas", {})


def test_plugin_protocol_type_check():
    """Test that PluginProtocol works with runtime_checkable."""

    class ValidPlugin:
        def on_startup(self, app: FastAPI) -> None:
            pass

        def on_shutdown(self, app: FastAPI) -> None:
            pass

        def before_request(self, request: Request) -> None:
            pass

        def after_request(self, request: Request, response: Response) -> None:
            pass

        def openapi_schema(self):
            return None

    # This should work because ValidPlugin implements all required methods
    assert isinstance(ValidPlugin(), PluginProtocol)


def test_plugin_no_openapi_return():
    """Test plugin that returns None for openapi_schema."""
    app = FastAPI()

    class NoSchemaPlugin(Plugin):
        def openapi_schema(self):
            return None

    plugin = NoSchemaPlugin()
    app.plugins.append(plugin)

    # Should not raise an error
    schema = app.openapi()
    assert schema is not None


def test_plugin_with_async_hooks():
    """Test plugin with async hooks."""

    class AsyncPlugin(Plugin):
        def __init__(self):
            self.startup_called = False

        async def on_startup(self, app: FastAPI) -> None:
            self.startup_called = True

    plugin = AsyncPlugin()
    assert hasattr(plugin.on_startup, "__code__")
    # Check if it's a coroutine function
    import inspect
    assert inspect.iscoroutinefunction(plugin.on_startup)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

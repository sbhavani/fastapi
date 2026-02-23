"""Tests for plugin OpenAPI schema extension."""
import pytest
from fastapi import FastAPI
from fastapi.plugins import PluginProtocol
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response


class OpenAPIPlugin:
    """Plugin that contributes OpenAPI schema."""

    def __init__(self, schema: dict):
        self._schema = schema

    @property
    def openapi_schema(self) -> dict | None:
        return self._schema


def test_plugin_contributes_security_scheme():
    """Test that plugins can add security schemes to OpenAPI."""
    plugin_schema = {
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "JWT token"
                }
            }
        },
        "security": [{"bearerAuth": []}]
    }

    app = FastAPI()
    app.add_plugin(OpenAPIPlugin(plugin_schema))

    @app.get("/")
    def root():
        return {"message": "hello"}

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()

    # Check security scheme was added
    assert "components" in schema
    assert "securitySchemes" in schema["components"]
    assert "bearerAuth" in schema["components"]["securitySchemes"]


def test_plugin_contributes_paths():
    """Test that plugins can add paths to OpenAPI."""
    plugin_schema = {
        "paths": {
            "/plugin-endpoint": {
                "get": {
                    "summary": "Plugin Endpoint",
                    "responses": {"200": {"description": "OK"}}
                }
            }
        }
    }

    app = FastAPI()
    app.add_plugin(OpenAPIPlugin(plugin_schema))

    @app.get("/")
    def root():
        return {"message": "hello"}

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()

    # Check path was added
    assert "/plugin-endpoint" in schema["paths"]


def test_multiple_plugins_merge():
    """Test that multiple plugins' OpenAPI contributions are merged."""
    plugin1_schema = {
        "components": {
            "securitySchemes": {
                "apiKey": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key"
                }
            }
        }
    }

    plugin2_schema = {
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer"
                }
            }
        }
    }

    app = FastAPI()
    app.add_plugin(OpenAPIPlugin(plugin1_schema))
    app.add_plugin(OpenAPIPlugin(plugin2_schema))

    @app.get("/")
    def root():
        return {"message": "hello"}

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()

    # Both security schemes should be present
    schemes = schema["components"]["securitySchemes"]
    assert "apiKey" in schemes
    assert "bearerAuth" in schemes


def test_plugin_contributes_tags():
    """Test that plugins can add tags to OpenAPI."""
    plugin_schema = {
        "tags": [
            {"name": "Plugin Tag", "description": "Endpoints from plugins"}
        ]
    }

    app = FastAPI()
    app.add_plugin(OpenAPIPlugin(plugin_schema))

    @app.get("/")
    def root():
        return {"message": "hello"}

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()

    # Tags should be present
    assert "tags" in schema
    assert any(tag["name"] == "Plugin Tag" for tag in schema["tags"])


def test_plugin_contributes_servers():
    """Test that plugins can add servers to OpenAPI."""
    plugin_schema = {
        "servers": [
            {"url": "https://api.example.com", "description": "Production server"}
        ]
    }

    app = FastAPI()
    app.add_plugin(OpenAPIPlugin(plugin_schema))

    @app.get("/")
    def root():
        return {"message": "hello"}

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()

    # Servers should be present
    assert "servers" in schema
    assert len(schema["servers"]) >= 1


def test_plugin_with_no_openapi_contribution():
    """Test that plugins without openapi_schema don't affect OpenAPI."""

    class NoOpenAPIPlugin:
        async def on_startup(self) -> None:
            pass

    app = FastAPI()
    app.add_plugin(NoOpenAPIPlugin())

    @app.get("/")
    def root():
        return {"message": "hello"}

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/openapi.json")

    assert response.status_code == 200
    # Should still work without errors


def test_plugin_openapi_schema_as_method():
    """Test that openapi_schema can be a method instead of property."""

    class MethodOpenAPIPlugin:
        def openapi_schema(self) -> dict | None:
            return {
                "components": {
                    "securitySchemes": {
                        "testAuth": {
                            "type": "http",
                            "scheme": "basic"
                        }
                    }
                }
            }

    app = FastAPI()
    app.add_plugin(MethodOpenAPIPlugin())

    @app.get("/")
    def root():
        return {"message": "hello"}

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "testAuth" in schema["components"]["securitySchemes"]

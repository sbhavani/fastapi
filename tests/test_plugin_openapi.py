"""Tests for plugin OpenAPI schema extension."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestOpenAPIExtension:
    """Test plugin OpenAPI schema extension."""

    def test_get_openapi_schema_called(self):
        """Test that get_openapi_schema is called."""
        schema_modified = []

        class OpenAPIPlugin:
            def get_openapi_schema(self, schema):
                schema_modified.append(True)
                schema["components"] = schema.get("components", {})
                schema["components"]["test"] = "added"
                return schema

        app = FastAPI()
        app.add_plugin(OpenAPIPlugin())

        @app.get("/")
        def root():
            return {"message": "hello"}

        # Generate OpenAPI schema
        schema = app.openapi()

        assert len(schema_modified) == 1
        assert schema.get("components", {}).get("test") == "added"

    def test_add_security_scheme(self):
        """Test adding a security scheme to OpenAPI."""

        class SecurityPlugin:
            def get_openapi_schema(self, schema):
                schema.setdefault("components", {})
                schema["components"].setdefault("securitySchemes", {})
                schema["components"]["securitySchemes"]["bearerAuth"] = {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
                return schema

        app = FastAPI()
        app.add_plugin(SecurityPlugin())

        @app.get("/")
        def root():
            return {"message": "hello"}

        schema = app.openapi()

        assert "bearerAuth" in schema["components"]["securitySchemes"]
        assert schema["components"]["securitySchemes"]["bearerAuth"]["type"] == "http"

    def test_add_custom_response(self):
        """Test adding a custom response to OpenAPI."""

        class ResponsePlugin:
            def get_openapi_schema(self, schema):
                schema.setdefault("components", {})
                schema["components"].setdefault("responses", {})
                schema["components"]["responses"]["PluginError"] = {
                    "description": "Plugin custom error",
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"}
                        }
                    }
                }
                return schema

        app = FastAPI()
        app.add_plugin(ResponsePlugin())

        @app.get("/")
        def root():
            return {"message": "hello"}

        schema = app.openapi()

        assert "PluginError" in schema["components"]["responses"]
        assert schema["components"]["responses"]["PluginError"]["description"] == "Plugin custom error"

    def test_multiple_plugins_extend_schema(self):
        """Test that multiple plugins can extend the schema."""

        class Plugin1:
            def get_openapi_schema(self, schema):
                schema.setdefault("components", {})
                schema["components"]["plugin1"] = "value1"
                return schema

        class Plugin2:
            def get_openapi_schema(self, schema):
                schema.setdefault("components", {})
                schema["components"]["plugin2"] = "value2"
                return schema

        app = FastAPI()
        app.add_plugin(Plugin1())
        app.add_plugin(Plugin2())

        @app.get("/")
        def root():
            return {"message": "hello"}

        schema = app.openapi()

        assert schema["components"].get("plugin1") == "value1"
        assert schema["components"].get("plugin2") == "value2"

    def test_plugin_execution_order(self):
        """Test that plugins extend schema in registration order."""
        order = []

        class Plugin1:
            def get_openapi_schema(self, schema):
                order.append(1)
                schema["x-order"] = schema.get("x-order", []) + [1]
                return schema

        class Plugin2:
            def get_openapi_schema(self, schema):
                order.append(2)
                schema["x-order"] = schema.get("x-order", []) + [2]
                return schema

        app = FastAPI()
        app.add_plugin(Plugin1())
        app.add_plugin(Plugin2())

        @app.get("/")
        def root():
            return {"message": "hello"}

        schema = app.openapi()

        # Both plugins should be called
        assert 1 in order
        assert 2 in order
        # x-order should reflect registration order
        assert schema.get("x-order") == [1, 2]

    def test_openapi_available_at_docs(self):
        """Test that plugin extensions appear in /docs endpoint."""

        class SchemaExtensionPlugin:
            def get_openapi_schema(self, schema):
                schema.setdefault("components", {})
                schema["components"]["customField"] = "customValue"
                return schema

        app = FastAPI()
        app.add_plugin(SchemaExtensionPlugin())

        @app.get("/items/{item_id}")
        def read_item(item_id: int):
            return {"item_id": item_id}

        with TestClient(app) as client:
            # Get OpenAPI JSON
            response = client.get("/openapi.json")
            assert response.status_code == 200

            schema = response.json()
            assert schema["components"]["customField"] == "customValue"

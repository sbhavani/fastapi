# Plugin Interface Contract

## Overview

This document defines the public contract that plugin authors must implement to create a valid FastAPI plugin.

## Plugin Protocol

```python
from typing import Any, Awaitable, Callable, Protocol, runtime_checkable
from starlette.requests import Request
from starlette.responses import Response

@runtime_checkable
class PluginProtocol(Protocol):
    """Protocol defining the plugin interface."""

    async def on_startup(self) -> Any:
        """Called when the FastAPI application starts."""
        ...

    async def on_shutdown(self) -> Any:
        """Called when the FastAPI application stops."""
        ...

    async def before_request(self, request: Request) -> Response | None:
        """
        Called before each request is processed.

        Args:
            request: The incoming request

        Returns:
            None to continue processing, or a Response to short-circuit the request
        """
        ...

    async def after_request(self, request: Request, response: Response) -> Response:
        """
        Called after each request is processed.

        Args:
            request: The incoming request
            response: The generated response

        Returns:
            The (potentially modified) response
        """
        ...

    def get_openapi_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Called to extend the OpenAPI schema.

        Args:
            schema: The current OpenAPI schema dict

        Returns:
            The extended schema dict
        """
        ...
```

## Registration Contract

### Method Signature

```python
def add_plugin(self, plugin: PluginProtocol) -> None:
    """
    Register a plugin with the FastAPI application.

    Args:
        plugin: An object implementing PluginProtocol

    Raises:
        TypeError: If plugin does not implement PluginProtocol
        ValueError: If a plugin with the same name is already registered
    """
```

### Usage Example

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello"}

# Register a plugin
app.add_plugin(MyPlugin())

# Or using a class
from fastapi.plugins import PluginProtocol, add_plugin

class MyAuthPlugin:
    async def on_startup(self):
        print("Starting up auth plugin")

    async def before_request(self, request):
        # Validate token
        return None  # Continue processing

app.add_plugin(MyAuthPlugin())
```

## OpenAPI Extension Contract

### Schema Extension Points

Plugins can extend the OpenAPI schema in the following ways:

1. **Add components**: Custom parameters, requestBodies, responses, schemas
2. **Add security schemes**: Authentication definitions
3. **Add paths**: New API routes

### Example: Adding Security Scheme

```python
class AuthPlugin:
    def get_openapi_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        # Ensure components exists
        if "components" not in schema:
            schema["components"] = {}
        if "securitySchemes" not in schema["components"]:
            schema["components"]["securitySchemes"] = {}

        # Add bearer auth
        schema["components"]["securitySchemes"]["bearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }

        return schema
```

## Error Handling

### Startup Errors

- If a plugin's `on_startup` raises an exception, application startup fails
- Plugins are initialized in registration order
- All `on_startup` hooks must complete before the app accepts requests

### Request Processing Errors

- If `before_request` raises, return 500 error
- If `after_request` raises, log error but return original response

### Shutdown Errors

- If a plugin's `on_shutdown` raises, log error but continue with other plugins
- Shutdown errors do not prevent other plugins from running

## Lifecycle Execution Order

```
1. app.add_plugin(plugin)  - Registration
2. App starts (lifespan enters)
3. For each plugin in order: plugin.on_startup()
4. App accepts requests
5. For each request:
   a. For each plugin in order: plugin.before_request()
   b. Route handler executes
   c. For each plugin in reverse order: plugin.after_request()
6. App stops (lifespan exits)
7. For each plugin in reverse order: plugin.on_shutdown()
```

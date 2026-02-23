# Contract: Plugin Protocol

## Overview

This document defines the public interface contract for FastAPI plugins.

## Public API

### 1. app.add_plugin()

**Location**: `FastAPI` class method

**Signature**:
```python
def add_plugin(self, plugin: PluginProtocol) -> None
```

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| plugin | PluginProtocol | Plugin instance to register |

**Returns**: `None`

**Errors**:
- `TypeError`: If plugin doesn't implement required protocol

**Example**:
```python
from fastapi import FastAPI
from myplugins import DatabasePlugin

app = FastAPI()
app.add_plugin(DatabasePlugin())
```

---

### 2. app.plugins

**Location**: `FastAPI` instance attribute

**Type**: `PluginRegistry`

**Access**: Read-only (property)

**Example**:
```python
app = FastAPI()
registry = app.plugins  # Returns PluginRegistry instance
```

---

## PluginProtocol Interface

### Definition

Plugins implement the `PluginProtocol` interface:

```python
from typing import Protocol, Any
from starlette.requests import Request
from starlette.responses import Response

class PluginProtocol(Protocol):
    """Protocol defining the plugin interface."""

    async def on_startup(self) -> None:
        """Called once when the application starts."""
        ...

    async def on_shutdown(self) -> None:
        """Called once when the application stops."""
        ...

    async def before_request(self, request: Request) -> Response | None:
        """Called before each request. Return a Response to short-circuit."""
        ...

    async def after_request(
        self, request: Request, response: Response
    ) -> Response:
        """Called after each request. Can modify the response."""
        ...

    @property
    def openapi_schema(self) -> dict[str, Any] | None:
        """Return OpenAPI schema contributions."""
        ...
```

### Methods

#### on_startup()

**Called**: When the application starts (before accepting requests)

**Execution Order**: In registration order (first registered = first called)

**Error Handling**: Exceptions are logged and do not prevent other plugins

**Example**:
```python
class MyPlugin:
    async def on_startup(self) -> None:
        print("Application is starting!")
        await self.connect_to_database()
```

---

#### on_shutdown()

**Called**: When the application stops (after last request)

**Execution Order**: Reverse registration order (last registered = first called)

**Error Handling**: Exceptions are logged and do not prevent other plugins

**Example**:
```python
class MyPlugin:
    async def on_shutdown(self) -> None:
        print("Application is shutting down!")
        await self.close_database_connections()
```

---

#### before_request()

**Called**: Before each HTTP request is processed

**Execution Order**: In registration order

**Return Value**:
- `None`: Continue to next handler
- `Response`: Short-circuit and return immediately

**Error Handling**: Exceptions are logged and do not prevent other plugins

**Example**:
```python
class MyPlugin:
    async def before_request(self, request: Request) -> Response | None:
        # Add request ID header
        request.state.request_id = str(uuid.uuid4())
        return None  # Continue processing
```

---

#### after_request()

**Called**: After each HTTP request is processed (response generated)

**Execution Order**: Reverse registration order

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| request | Request | The incoming request |
| response | Response | The generated response |

**Returns**: `Response` (can be modified)

**Error Handling**: Exceptions are logged and do not prevent other plugins

**Example**:
```python
class MyPlugin:
    async def after_request(
        self, request: Request, response: Response
    ) -> Response:
        # Add timing header
        if hasattr(request.state, "start_time"):
            duration = time.time() - request.state.start_time
            response.headers["X-Process-Time"] = str(duration)
        return response
```

---

#### openapi_schema

**Called**: When OpenAPI schema is generated

**Return Type**: `dict[str, Any] | None`

**Merged Into**: Base OpenAPI schema

**Example**:
```python
class AuthPlugin:
    @property
    def openapi_schema(self) -> dict[str, Any] | None:
        return {
            "components": {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "description": "JWT token authentication"
                    }
                }
            },
            "security": [
                {"bearerAuth": []}
            ]
        }
```

---

## PluginRegistry Interface

### Definition

```python
class PluginRegistry:
    """Manages registered plugins."""

    def add(self, plugin: PluginProtocol) -> None:
        """Register a plugin."""
        ...

    async def on_startup(self) -> None:
        """Trigger startup for all plugins."""
        ...

    async def on_shutdown(self) -> None:
        """Trigger shutdown for all plugins."""
        ...

    async def before_request(
        self, request: Request
    ) -> Response | None:
        """Run before_request for all plugins."""
        ...

    async def after_request(
        self, request: Request, response: Response
    ) -> Response:
        """Run after_request for all plugins."""
        ...

    def get_openapi_contributions(self) -> dict[str, Any]:
        """Aggregate OpenAPI contributions from all plugins."""
        ...
```

---

## Usage Examples

### Minimal Plugin

```python
from fastapi import FastAPI
from fastapi.plugins import PluginProtocol

class LoggingPlugin:
    async def before_request(self, request):
        print(f"Request: {request.method} {request.url}")

app = FastAPI()
app.add_plugin(LoggingPlugin())
```

### Full-Featured Plugin

```python
from fastapi import FastAPI
from fastapi.plugins import PluginProtocol

class DatabasePlugin:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool = None

    async def on_startup(self) -> None:
        self.pool = await create_pool(self.connection_string)

    async def on_shutdown(self) -> None:
        if self.pool:
            await self.pool.close()

    async def before_request(self, request):
        request.state.db = self.pool
        return None

    async def after_request(self, request, response):
        # Cleanup if needed
        return response

    @property
    def openapi_schema(self) -> dict | None:
        return {
            "paths": {
                "/health": {
                    "get": {
                        "summary": "Health Check",
                        "responses": {"200": {"description": "OK"}}
                    }
                }
            }
        }

app = FastAPI()
app.add_plugin(DatabasePlugin("postgresql://localhost/mydb"))
```

---

## Backward Compatibility

- Adding a plugin does not change existing behavior
- Applications not using plugins are unaffected
- Existing middleware and dependencies work alongside plugins
- OpenAPI schema generation unchanged if no plugins contribute

---

## Error Messages

| Error | Message |
|-------|---------|
| Invalid plugin | "Plugin must implement the PluginProtocol interface" |
| Startup error | "[PluginName] startup error: {exception}" |
| Shutdown error | "[PluginName] shutdown error: {exception}" |
| Request error | "[PluginName] before_request error: {exception}" |

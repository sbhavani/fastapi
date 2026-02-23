# Plugins

FastAPI supports a plugin system that allows you to create reusable extensions with lifecycle hooks and automatic OpenAPI schema integration.

## Installing and Using Plugins

### Registering a Plugin

```python
from fastapi import FastAPI

app = FastAPI()

# Register a plugin
app.add_plugin(MyPlugin())
```

## Creating a Plugin

A plugin is a class that implements the `PluginProtocol` interface. The interface defines several optional hooks:

```python
from fastapi import FastAPI, Request
from fastapi.plugins import PluginProtocol
from starlette.responses import Response

class MyPlugin:
    async def on_startup(self):
        """Called when the app starts."""
        print("Starting up!")

    async def on_shutdown(self):
        """Called when the app stops."""
        print("Shutting down!")

    async def before_request(self, request: Request) -> Response | None:
        """Called before each request."""
        # Return None to continue, or a Response to short-circuit
        return None

    async def after_request(self, request: Request, response: Response) -> Response:
        """Called after each request."""
        return response

    def get_openapi_schema(self, schema: dict) -> dict:
        """Called to extend the OpenAPI schema."""
        return schema
```

## Lifecycle Hooks

### on_startup

Called when the FastAPI application starts. Use this to initialize resources:

```python
async def on_startup(self):
    # Initialize database connection
    self.db = await connect_to_database()
```

### on_shutdown

Called when the FastAPI application stops. Use this to clean up resources:

```python
async def on_shutdown(self):
    # Close database connection
    await self.db.close()
```

### before_request

Called before each request is processed. Can modify the request or short-circuit:

```python
async def before_request(self, request: Request):
    # Add user to request state
    request.state.user = await get_current_user(request)

    # Return a Response to short-circuit the request
    if not request.state.user:
        return JSONResponse(
            status_code=401,
            content={"detail": "Not authenticated"}
        )
```

### after_request

Called after each request is processed. Can modify the response:

```python
async def after_request(self, request: Request, response: Response):
    # Add custom header
    response.headers["X-Process-Time"] = str(time.time() - request.state.start_time)
    return response
```

## OpenAPI Extension

The `get_openapi_schema` hook allows plugins to extend the OpenAPI schema:

### Adding Security Schemes

```python
def get_openapi_schema(self, schema: dict) -> dict:
    schema.setdefault("components", {})
    schema["components"].setdefault("securitySchemes", {})
    schema["components"]["securitySchemes"]["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT"
    }
    return schema
```

### Adding Custom Responses

```python
def get_openapi_schema(self, schema: dict) -> dict:
    schema.setdefault("components", {})
    schema["components"].setdefault("responses", {})
    schema["components"]["responses"]["RateLimited"] = {
        "description": "Rate limit exceeded",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/Error"}
            }
        }
    }
    return schema
```

## Example: Authentication Plugin

Here's a complete example of an authentication plugin:

```python
from fastapi import FastAPI, Request
from fastapi.plugins import PluginProtocol
from starlette.responses import JSONResponse

class AuthPlugin:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    async def on_startup(self):
        # Initialize token store
        self.tokens = {}

    async def before_request(self, request: Request):
        # Check authorization header
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid authorization"}
            )

        token = auth.replace("Bearer ", "")
        if token not in self.tokens:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid token"}
            )

        request.state.user = self.tokens[token]

    def get_openapi_schema(self, schema: dict) -> dict:
        # Add security scheme to OpenAPI
        schema.setdefault("components", {})
        schema["components"].setdefault("securitySchemes", {})
        schema["components"]["securitySchemes"]["bearerAuth"] = {
            "type": "http",
            "scheme": "bearer"
        }
        schema["security"] = [{"bearerAuth": []}]
        return schema


# Usage
app = FastAPI()
app.add_plugin(AuthPlugin(secret_key="your-secret-key"))

@app.get("/protected")
def protected_route(request: Request):
    return {"user": request.state.user}
```

## Plugin Execution Order

- **Startup**: Plugins execute in registration order (first registered = first executed)
- **Shutdown**: Plugins execute in reverse registration order
- **before_request**: Plugins execute in registration order
- **after_request**: Plugins execute in reverse registration order
- **OpenAPI**: Plugins extend schema in registration order

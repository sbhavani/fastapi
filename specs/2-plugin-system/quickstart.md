# Quickstart: FastAPI Plugin System

This guide shows how to use the FastAPI plugin system to create reusable extensions.

## For Plugin Users

### Registering a Plugin

```python
from fastapi import FastAPI

app = FastAPI()

# Import and register a plugin
from my_auth_plugin import AuthPlugin

app.add_plugin(AuthPlugin())

@app.get("/protected")
async def protected_route():
    return {"data": "This route is protected by the plugin"}
```

### Multiple Plugins

Plugins execute in registration order:

```python
app.add_plugin(LoggingPlugin())
app.add_plugin(AuthPlugin())
app.add_plugin(MetricsPlugin())
```

## For Plugin Authors

### Creating a Simple Plugin

```python
import asyncio
from fastapi import FastAPI

class MyPlugin:
    """Example plugin with all lifecycle hooks."""

    async def on_startup(self):
        """Initialize resources on startup."""
        print("Plugin: Starting up")
        self.connections = []

    async def on_shutdown(self):
        """Clean up resources on shutdown."""
        print("Plugin: Shutting down")
        for conn in self.connections:
            await conn.close()

    async def before_request(self, request):
        """Process request before endpoint executes."""
        # Add request ID to state
        request.state.request_id = uuid.uuid4()
        return None  # Continue to endpoint

    async def after_request(self, request, response):
        """Process response after endpoint executes."""
        # Add custom header
        response.headers["X-Plugin"] = "MyPlugin"
        return response

    def get_openapi_schema(self, schema):
        """Extend OpenAPI schema."""
        # Add security scheme
        schema.setdefault("components", {})
        schema["components"].setdefault("securitySchemes", {})
        schema["components"]["securitySchemes"]["myAuth"] = {
            "type": "http",
            "scheme": "bearer"
        }
        return schema


# Register the plugin
app = FastAPI()
app.add_plugin(MyPlugin())
```

### Creating a Plugin with Configuration

```python
from pydantic import BaseModel

class RateLimitConfig(BaseModel):
    requests_per_minute: int = 60

class RateLimitPlugin:
    """Plugin with user-configurable settings."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests = {}

    async def on_startup(self):
        print(f"Rate limiting: {self.config.requests_per_minute} req/min")

    async def before_request(self, request):
        client_id = request.client.host
        # Implement rate limiting logic
        return None


# Usage
app = FastAPI()
app.add_plugin(RateLimitPlugin(RateLimitConfig(requests_per_minute=100)))
```

### Minimal Plugin (Only Startup/Shutdown)

```python
class DatabasePlugin:
    """Plugin that only needs startup/shutdown."""

    async def on_startup(self):
        # Initialize database connection pool
        self.pool = await create_pool()

    async def on_shutdown(self):
        # Close connection pool
        await self.pool.close()


app.add_plugin(DatabasePlugin())
```

## Hooks Reference

| Hook | When Called | Use Case |
|------|-------------|----------|
| on_startup | Before app accepts requests | Initialize connections, load config |
| on_shutdown | Before app stops | Cleanup resources |
| before_request | Each HTTP request | Auth, logging, rate limiting |
| after_request | Each HTTP response | Add headers, modify response |

## OpenAPI Extension

### Adding Custom Response

```python
class ErrorPlugin:
    def get_openapi_schema(self, schema):
        schema.setdefault("components", {})
        schema["components"].setdefault("responses", {})

        schema["components"]["responses"]["PluginError"] = {
            "description": "Plugin custom error",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"}
                }
            }
        }
        return schema
```

## Best Practices

1. **Make hooks optional**: Users should only implement what they need
2. **Handle errors gracefully**: Don't let plugin errors crash the app
3. **Document configuration**: Provide clear defaults and configuration options
4. **Use type hints**: Makes your plugin easier to use and debug
5. **Test independently**: Verify plugin works in isolation before integration

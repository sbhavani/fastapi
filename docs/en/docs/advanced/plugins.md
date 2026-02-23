# Plugins { #plugins }

**FastAPI** supports a formal plugin system that allows you to extend your application with reusable components. Plugins can participate in the application lifecycle, intercept requests/responses, and contribute to the OpenAPI schema.

## Installing a Plugin { #installing-a-plugin }

You can add plugins to your application using the `app.add_plugin()` method:

```Python
from fastapi import FastAPI

app = FastAPI()

app.add_plugin(MyPlugin())
```

## Creating a Plugin { #creating-a-plugin }

A plugin is any class that implements the `PluginProtocol` interface. The protocol defines optional lifecycle hooks:

```Python
from fastapi import FastAPI
from fastapi.plugins import PluginProtocol

class MyPlugin:
    async def on_startup(self) -> None:
        # Called when the application starts
        print("Startup!")

    async def on_shutdown(self) -> None:
        # Called when the application stops
        print("Shutdown!")

    async def before_request(self, request: Request) -> Response | None:
        # Called before each request
        # Return a Response to short-circuit the request
        return None

    async def after_request(self, request: Request, response: Response) -> Response:
        # Called after each request
        # Return the (potentially modified) response
        return response

    def openapi_schema(self) -> dict[str, Any] | None:
        # Return OpenAPI schema contributions
        return None
```

All methods are optional - you only need to implement the hooks your plugin needs.

## Plugin Lifecycle { #plugin-lifecycle }

### Startup Hook { #startup-hook }

The `on_startup()` hook is called when the FastAPI application starts. Use it to initialize resources like database connections:

```Python
class DatabasePlugin:
    def __init__(self):
        self.connection = None

    async def on_startup(self) -> None:
        self.connection = await connect_to_database()

    async def on_shutdown(self) -> None:
        await self.connection.disconnect()
```

/// note | Execution Order

On startup, plugins are called in the order they were registered (FIFO).

///

### Shutdown Hook { #shutdown-hook }

The `on_shutdown()` hook is called when the FastAPI application stops. Use it to clean up resources:

```Python
class CleanupPlugin:
    async def on_shutdown(self) -> None:
        await cleanup_temp_files()
        print("Cleanup complete")
```

/// note | Execution Order

On shutdown, plugins are called in reverse order (LIFO), allowing dependencies to be properly cleaned up.

///

## Request Interception { #request-interception }

### Before Request { #before-request }

The `before_request()` hook is called before each request reaches your route handlers. It can:

- Modify the request
- Add custom logic (e.g., authentication, logging)
- Short-circuit the request by returning a Response

```Python
class AuthPlugin:
    async def before_request(self, request: Request) -> Response | None:
        if request.url.path.startswith("/admin"):
            token = request.headers.get("Authorization")
            if not self.validate_token(token):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid token"}
                )
        return None
```

If any plugin returns a Response, processing stops and that response is returned immediately.

### After Request { #after-request }

The `after_request()` hook is called after each request completes. It can modify the response:

```Python
class ResponseModifierPlugin:
    async def after_request(self, request: Request, response: Response) -> Response:
        response.headers["X-Custom-Header"] = "value"
        return response
```

/// note | Execution Order

The `after_request()` hook is called in reverse order (LIFO), so the last registered plugin's hook runs first. This allows plugins to wrap responses.

///

## OpenAPI Extension { #openapi-extension }

Plugins can automatically contribute to the OpenAPI schema. Return an `openapi_schema()` method with your contributions:

```Python
class OpenAPIPlugin:
    def openapi_schema(self) -> dict[str, Any] | None:
        return {
            "paths": {
                "/api/external": {
                    "get": {
                        "summary": "External API",
                        "responses": {"200": {"description": "External data"}}
                    }
                }
            },
            "components": {
                "securitySchemes": {
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key"
                    }
                }
            },
            "security": [{"ApiKeyAuth": []}]
        }
```

The plugin's schema contributions are merged into the main OpenAPI schema when `/openapi.json` is generated.

/// tip | Supported Contribution Keys

Plugins can contribute to any valid OpenAPI top-level keys: `paths`, `components`, `security`, `tags`, `servers`, and `externalDocs`.

///

## Accessing the Plugin Registry { #accessing-plugin-registry }

You can access the plugin registry to inspect or manage plugins:

```Python
# Access all registered plugins
for plugin in app.plugins:
    print(plugin.__class__.__name__)

# Get the number of plugins
count = len(app.plugins)
```

## Error Handling { #error-handling }

Plugin errors are isolated - if one plugin raises an exception, other plugins continue to execute. Errors are logged but don't prevent the application from functioning.

This ensures that a malfunctioning plugin doesn't break your entire application.

## Complete Example { #complete-example }

Here's a complete example combining all plugin features:

```Python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.plugins import PluginProtocol


class LoggingPlugin:
    """Plugin that logs all requests."""

    async def on_startup(self) -> None:
        print("LoggingPlugin: Starting up")

    async def on_shutdown(self) -> None:
        print("LoggingPlugin: Shutting down")

    async def before_request(self, request: Request) -> None:
        print(f"LoggingPlugin: Before {request.method} {request.url.path}")

    async def after_request(self, request: Request, response) -> None:
        print(f"LoggingPlugin: After {request.method} {request.url.path}")


class APIKeyPlugin:
    """Plugin that enforces API key authentication."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def before_request(self, request: Request):
        # Skip auth for docs and OpenAPI
        if request.url.path in ["/docs", "/openapi.json", "/redoc"]:
            return None

        # Check for API key
        provided_key = request.headers.get("X-API-Key")
        if provided_key != self.api_key:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid API key"}
            )
        return None

    def openapi_schema(self) -> dict | None:
        return {
            "components": {
                "securitySchemes": {
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key"
                    }
                }
            },
            "security": [{"ApiKeyAuth": []}]
        }


class HealthCheckPlugin:
    """Plugin that adds a health check endpoint to OpenAPI."""

    def openapi_schema(self) -> dict | None:
        return {
            "paths": {
                "/health": {
                    "get": {
                        "summary": "Health Check",
                        "description": "Returns the health status of the API",
                        "responses": {
                            "200": {
                                "description": "Service is healthy",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "status": {"type": "string", "example": "healthy"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }


# Create the FastAPI app
app = FastAPI()

# Register plugins - order matters for execution!
app.add_plugin(LoggingPlugin())
app.add_plugin(APIKeyPlugin(api_key="secret-api-key"))
app.add_plugin(HealthCheckPlugin())


@app.get("/items/{item_id}")
async def read_item(item_id: int):
    """Example endpoint."""
    return {"item_id": item_id, "name": "Example Item"}
```

With this setup:

1. **LoggingPlugin** logs all requests and responses
2. **APIKeyPlugin** enforces API key authentication (except for docs)
3. **HealthCheckPlugin** adds a `/health` endpoint to the OpenAPI schema

### Testing the Complete Example

You can test the complete example with:

```bash
# Should work with valid API key
curl -H "X-API-Key: secret-api-key" http://localhost:8000/items/1

# Should return 403 without API key
curl http://localhost:8000/items/1

# Health check is publicly accessible
curl http://localhost:8000/health
```

### Viewing Generated OpenAPI

Visit `/docs` to see the combined OpenAPI schema with:
- The `/items/{item_id}` endpoint from the app
- The `/health` endpoint from **HealthCheckPlugin**
- The `ApiKeyAuth` security scheme from **APIKeyPlugin**

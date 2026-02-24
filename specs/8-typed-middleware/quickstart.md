# Quickstart: Typed Middleware

## Installation

Typed middleware is included in FastAPI. No additional installation required.

## Your First Typed Middleware

```python
from fastapi import FastAPI, Request, Depends
from fastapi.middleware import MiddlewareProtocol
from fastapi.responses import Response
from starlette.types import ASGIApp

# Define typed middleware
class MyMiddleware(MiddlewareProtocol[Request, Response]):
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, request: Request, call_next):
        # Process request
        print(f"Before: {request.url}")
        response = await call_next(request)
        # Process response
        print(f"After: {response.status_code}")
        return response

# Use in app
app = FastAPI()
app.add_typed_middleware(MyMiddleware)
```

## Middleware with Dependencies

```python
from fastapi import Depends

# Dependency
def get_db():
    return DatabasePool()

# Middleware with dependencies
class DatabaseMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp, db: DatabasePool = Depends(get_db)):
        self.app = app
        self.db = db

    async def __call__(self, request, call_next):
        request.state.db = self.db
        return await call_next(request)

app.add_typed_middleware(DatabaseMiddleware)
```

## Controlling Execution Order

```python
# Run AuthMiddleware after CORSMiddleware
app.add_middleware(CORSMiddleware)  # Legacy
app.add_typed_middleware(
    AuthMiddleware,
    depends_on=()  # No dependencies - runs after legacy middleware
)
app.add_typed_middleware(
    RateLimitMiddleware,
    depends_on=(AuthMiddleware,)  # Runs after AuthMiddleware
)
```

## Lifecycle Hooks

```python
class StartupMiddleware(MiddlewareProtocol):
    async def on_startup(self):
        print("App starting up!")

    async def on_shutdown(self):
        print("App shutting down!")

    async def __call__(self, request, call_next):
        return await call_next(request)
```

## Type Safety

```python
# This will be caught by mypy:
class BadMiddleware:
    # Missing required __init__ with ASGIApp
    async def __call__(self, request: Request, call_next):
        return await call_next(request)

app.add_typed_middleware(BadMiddleware)
# Error: doesn't implement MiddlewareProtocol
```

## Migration from Legacy

```python
# Legacy middleware - still works
from starlette.middleware.base import BaseHTTPMiddleware

class LegacyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        return await call_next(request)

app.add_middleware(LegacyMiddleware)

# Add typed middleware alongside
app.add_typed_middleware(AuthMiddleware)
```

## Common Patterns

### Authentication

```python
class AuthMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp, secret: str = "default"):
        self.app = app

    async def __call__(self, request: Request, call_next):
        if "authorization" not in request.headers:
            return Response("Unauthorized", status_code=401)
        return await call_next(request)
```

### Request/Response Logging

```python
class LoggingMiddleware(MiddlewareProtocol):
    async def __call__(self, request: Request, call_next):
        # Log request
        logger.info(f"{request.method} {request.url}")
        response = await call_next(request)
        # Log response
        logger.info(f"Status: {response.status_code}")
        return response
```

### Error Handling

```python
class ErrorHandlerMiddleware(MiddlewareProtocol):
    async def __call__(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            return Response(
                f"Error: {str(e)}",
                status_code=500
            )
```

## Next Steps

- Read the [API Reference](contracts/interfaces.md)
- Understand the [Data Model](data-model.md)
- Learn about [Design Decisions](research.md)

# Interface Contracts: Typed Middleware

## Contract 1: FastAPI.add_typed_middleware()

**Purpose**: Add type-safe middleware to FastAPI application

### Signature

```python
def add_typed_middleware(
    self,
    middleware_class: type[MiddlewareProtocol[RequestT, ResponseT]],
    *,
    dependencies: list[Depends] = [],
    depends_on: tuple[type[MiddlewareProtocol, ...]] = (),
    **kwargs: Any
) -> None
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| middleware_class | type[MiddlewareProtocol] | Yes | Middleware class implementing protocol |
| dependencies | list[Depends] | No | Dependencies for middleware init |
| depends_on | tuple[type, ...] | No | Middleware that must run before |
| **kwargs | Any | No | Additional args passed to middleware |

### Errors

| Error | Condition |
|-------|-----------|
| TypeError | middleware_class doesn't implement MiddlewareProtocol |
| OrderedMiddlewareError | Circular dependencies in depends_on |
| DependencyError | Cannot resolve dependencies |

### Example

```python
from fastapi import FastAPI, Depends
from fastapi.middleware import MiddlewareProtocol

app = FastAPI()

# Simple middleware
app.add_typed_middleware(AuthMiddleware)

# With dependencies
app.add_typed_middleware(
    DatabaseMiddleware,
    dependencies=[Depends(get_db_pool)]
)

# With ordering
app.add_typed_middleware(
    RateLimitMiddleware,
    depends_on=(AuthMiddleware,)
)
```

---

## Contract 2: MiddlewareProtocol

**Purpose**: Define contract for typed middleware

### Class Definition

```python
from typing import Protocol, TypeVar, Generic, Callable, Awaitable
from starlette.requests import Request
from starlette.responses import Response

RequestT = TypeVar("RequestT", bound=Request)
ResponseT = TypeVar("ResponseT", bound=Response)

class MiddlewareProtocol(Protocol[RequestT, ResponseT]):
    def __init__(self, app: ASGIApp, **kwargs: Any) -> None:
        ...

    async def __call__(
        self,
        request: RequestT,
        call_next: Callable[[RequestT], Awaitable[ResponseT]]
    ) -> ResponseT:
        ...
```

### Optional Methods

```python
async def on_startup(self) -> None:
    """Called when app starts"""

async def on_shutdown(self) -> None:
    """Called when app shuts down"""
```

---

## Contract 3: MiddlewareGraph

**Purpose**: Validate middleware ordering

### Methods

```python
class MiddlewareGraph:
    def add_middleware(self, config: MiddlewareConfig) -> None:
        """Add middleware and validate ordering"""

    def validate_order(self) -> list[str]:
        """Validate ordering, return list of errors"""

    def get_execution_order(self) -> list[type]:
        """Return middleware in execution order"""
```

### Validation Rules

1. **Cycle Detection**: No circular `depends_on` relationships
2. **Reference Validation**: All `depends_on` must reference registered middleware
3. **Ordering**: Must produce deterministic execution order

### Error Format

```python
# OrderedMiddlewareError example
OrderedMiddlewareError(
    "Circular dependency detected: AuthMiddleware -> RateLimitMiddleware -> AuthMiddleware"
)
```

---

## Contract 4: Backward Compatibility

### Legacy Middleware (BaseHTTPMiddleware)

```python
# Continues to work as before
from starlette.middleware.base import BaseHTTPMiddleware

class LegacyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        return await call_next(request)

app.add_middleware(LegacyMiddleware)  # Unchanged
```

### Mixed Usage

```python
# Both work together
app.add_middleware(CORSMiddleware)  # Legacy
app.add_typed_middleware(AuthMiddleware)  # New typed

# Execution order:
# 1. CORSMiddleware (added first)
# 2. AuthMiddleware (added second)
```

---

## Integration Points

### With FastAPI App

```python
class FastAPI:
    def add_typed_middleware(
        self,
        middleware_class: type[MiddlewareProtocol],
        *,
        dependencies: list[Depends] = [],
        depends_on: tuple[type[MiddlewareProtocol], ...] = (),
    ) -> None:
        ...
```

### With Dependency Injection

```python
class AuthMiddleware(MiddlewareProtocol):
    def __init__(
        self,
        app: ASGIApp,
        db: Database = Depends(get_db),  # DI works here
        config: AppConfig = Depends(get_config),
    ):
        self.app = app
        self.db = db
        self.config = config
```

### With OpenAPI

- Middleware chain reflected in `/openapi.json`
- Type information preserved in schemas
- Execution order documented

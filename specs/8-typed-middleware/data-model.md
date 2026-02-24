# Data Model: Typed Middleware

## Entities

### 1. MiddlewareProtocol

**Purpose**: Define the contract for typed middleware using structural subtyping

```python
from typing import Protocol, TypeVar, Generic, Callable, Awaitable
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

RequestT = TypeVar("RequestT", bound=Request)
ResponseT = TypeVar("ResponseT", bound=Response)
```

**Attributes**:
- Type parameters: `RequestT`, `ResponseT`
- Methods:
  - `__call__(self, request: RequestT, call_next: Callable[[RequestT], Awaitable[ResponseT]]) -> ResponseT`
  - `on_startup(self) -> None` (optional)
  - `on_shutdown(self) -> None` (optional)

---

### 2. MiddlewareConfig

**Purpose**: Store configuration for typed middleware

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class MiddlewareConfig:
    cls: type  # MiddlewareProtocol subclass
    dependencies: list[Any] = field(default_factory=list)
    depends_on: tuple[type, ...] = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)
```

**Attributes**:
- `cls`: The middleware class
- `dependencies`: List of Depends() instances
- `depends_on`: Tuple of middleware classes that must run before
- `kwargs`: Additional arguments for middleware init

---

### 3. MiddlewareGraph

**Purpose**: Track middleware ordering and detect cycles

```python
from dataclasses import dataclass, field

@dataclass
class MiddlewareGraph:
    nodes: dict[type, MiddlewareConfig] = field(default_factory=dict)
    edges: dict[type, set[type]] = field(default_factory=lambda: defaultdict(set))

    def add_middleware(self, config: MiddlewareConfig) -> None:
        """Add middleware to graph and validate for cycles"""

    def validate_order(self) -> list[str]:
        """Validate middleware ordering, return list of errors"""
```

**Attributes**:
- `nodes`: Map of middleware class to config
- `edges`: Dependency graph (middleware -> depends_on)

**Validation Rules**:
1. No circular dependencies between middleware
2. All `depends_on` references must exist
3. Ordering conflicts detected (e.g., A before B and B before A)

---

### 4. MiddlewareDependency

**Purpose**: Wrapper for middleware dependencies

```python
from typing import Any, Callable
from dataclasses import dataclass

@dataclass
class MiddlewareDependency:
    factory: Callable[..., Any]  # Dependency factory
    use_cache: bool = True
    scope: str = "middleware"  # lifecycle scope
```

---

## Relationships

```
FastAPI App
    │
    ├── add_typed_middleware()
    │       │
    │       └──> MiddlewareConfig
    │               │
    │               ├── cls: MiddlewareProtocol
    │               ├── dependencies: List[Depends]
    │               └── depends_on: Tuple[MiddlewareProtocol]
    │
    └── MiddlewareGraph (validates ordering)
            │
            ├── Nodes: Middleware configs
            └── Edges: Dependency relationships
```

---

## State Transitions

### Middleware Registration Flow

```
User calls add_typed_middleware()
        │
        ▼
Create MiddlewareConfig
        │
        ▼
Add to MiddlewareGraph
        │
        ▼
Validate ordering (check for cycles)
        │
        ▼
[If valid] Add to app middleware stack
[If invalid] Raise OrderedMiddlewareError
```

### Lifecycle

```
App Startup
    │
    ├── Load middleware configs
    ├── Resolve dependencies
    ├── Call on_startup() for each middleware
    └── Build ASGI middleware stack

Request Processing
    │
    └── Middleware chain executes in order

App Shutdown
    │
    ├── Call on_shutdown() for each middleware
    └── Cleanup dependencies
```

---

## Validation Rules

### MiddlewareConfig

| Rule | Description |
|------|-------------|
| Must be Protocol subclass | Class must implement MiddlewareProtocol |
| Dependencies must be valid | All dependencies must be resolvable |
| depends_on must exist | Referenced middleware must be registered |

### MiddlewareGraph

| Rule | Description |
|------|-------------|
| No cycles | `depends_on` cannot create circular references |
| All references valid | All `depends_on` classes must be registered |
| Ordering deterministic | Single valid topological sort must exist |

---

## Example Usage

```python
# Define typed middleware
class AuthMiddleware(MiddlewareProtocol[Request, Response]):
    def __init__(self, app: ASGIApp, db: Database = Depends(get_db)):
        self.app = app
        self.db = db

    async def __call__(self, request, call_next):
        # Type-safe: request is typed as Request
        user = await self.db.get_user(request.headers["authorization"])
        request.state.user = user
        return await call_next(request)

# Register with dependencies and ordering
app.add_typed_middleware(
    AuthMiddleware,
    depends_on=(CORSMiddleware,),  # Run after CORS
)
```

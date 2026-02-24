# Implementation Plan: Typed Middleware

## Feature Overview

Implement type-safe middleware system for FastAPI with compile-time validation, enabling developers to define middleware with full type hints for request/response handling and dependencies.

## Technical Context

### Architecture Overview

The typed middleware system will extend FastAPI's middleware capabilities while maintaining backward compatibility with Starlette's existing middleware. The implementation builds upon:

1. **Existing Middleware Stack**: FastAPI inherits from Starlette's `Starlette` class, which provides `add_middleware()` method
2. **Dependency Injection System**: FastAPI's `fastapi.dependencies` module for resolving middleware dependencies
3. **ASGI Compatibility**: All middleware must conform to ASGI specification (scope, receive, send)

### Key Technical Decisions

#### MiddlewareProtocol Design

Using Python's `Protocol` class (structural subtyping) rather than ABC (structural matching) for maximum flexibility. This allows:
- Type checking without requiring explicit inheritance
- Both class-based and function-based middleware
- Gradual adoption without rewrites

```python
from typing import Protocol, TypeVar, Generic

class MiddlewareProtocol(Protocol):
    async def __call__(self, scope, receive, send) -> None: ...
```

#### Dependency Injection for Middleware

Extending FastAPI's existing DI system to support middleware. Dependencies will be:
- Declared via `Depends` in middleware init
- Resolved at middleware construction time
- Lifecycle-managed (startup/shutdown hooks)

#### Compile-Time Ordering

Using Python's type system to express middleware dependencies:
- `depends_on: tuple[type[MiddlewareProtocol], ...]` class attribute
- Validation at app initialization (not truly compile-time, but pre-runtime)
- Cycle detection using topological sort

### Dependencies & Integration Points

| Component | Integration Point | Notes |
|-----------|-------------------|-------|
| Starlette | `fastapi.applications` | Inherited middleware stack |
| Dependency Injection | `fastapi.dependencies` | Extended for middleware |
| Request/Response | `starlette.requests`, `starlette.responses` | Type-parameterized versions |
| OpenAPI | `fastapi.openapi` | Documentation generation |

### Unknowns (NEEDS CLARIFICATION)

1. **Exact Protocol signature**: Should dispatch method use Request/Response generic types or raw ASGI (scope/receive/send)?
   - *Decision needed*: Type-safe approach (Request[T]) vs ASGI-native approach

2. **Ordering validation timing**: When should middleware ordering be validated?
   - *Option A*: At app startup (runtime but pre-request)
   - *Option B*: Using mypy plugins (requires additional tooling)
   - *Option C*: Both (runtime validation + optional mypy plugin)

3. **Backwards compatibility scope**: Should legacy `BaseHTTPMiddleware` be wrapped or remain as-is?
   - *Decision needed*: Seamless interop vs clean typed-only path

## Constitution Check

### FastAPI Constitution Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Standards-Based | ✅ PASS | Uses OpenAPI, JSON Schema standards |
| II. Type Safety | ✅ PASS | Core feature - type hints throughout |
| III. Test-First | ⚠️ TODO | Tests must be written before implementation |
| IV. Performance | ⚠️ TODO | Must match existing middleware performance |
| V. Developer Experience | ✅ PASS | Improves DX with better type checking |

### Gate Evaluation

- [x] Type safety requirements met (mypy --strict compatible)
- [x] No breaking changes to existing API
- [x] ASGI-compliant design
- [x] Backward compatibility maintained

## Phase 0: Research

### Research Tasks

- [ ] **R1**: Study Starlette's BaseHTTPMiddleware implementation for compatibility patterns
- [ ] **R2**: Research Protocol vs ABC for type-safe middleware in Python
- [ ] **R3**: Analyze dependency injection extension patterns in FastAPI
- [ ] **R4**: Investigate mypy plugin capabilities for compile-time validation

### Research Findings (Placeholder)

*To be completed after research phase*

---

## Phase 1: Design & Contracts

### Data Model

#### MiddlewareProtocol

```python
from typing import Protocol, TypeVar, Generic, Awaitable
from starlette.requests import Request
from starlette.responses import Response

RequestT = TypeVar("RequestT", bound=Request)
ResponseT = TypeVar("ResponseT", bound=Response)

class MiddlewareProtocol(Protocol[RequestT, ResponseT]):
    async def __call__(
        self,
        request: RequestT,
        call_next: Callable[[RequestT], Awaitable[ResponseT]]
    ) -> ResponseT: ...

    # Optional lifecycle hooks
    async def on_startup(self) -> None: ...
    async def on_shutdown(self) -> None: ...
```

#### TypedMiddleware (Implementation Class)

```python
from typing import Generic, TypeVar, Callable, Any
from dataclasses import dataclass

MiddlewareClass = TypeVar("MiddlewareClass", bound=MiddlewareProtocol)

@dataclass
class MiddlewareConfig:
    cls: type[MiddlewareProtocol]
    dependencies: list[Depends] = []
    depends_on: tuple[type[MiddlewareProtocol], ...] = ()
```

#### MiddlewareOrder Validator

```python
from dataclasses import dataclass
from typing import set[type[MiddlewareProtocol]]

@dataclass
class MiddlewareGraph:
    nodes: set[type[MiddlewareProtocol]]
    edges: dict[type[MiddlewareProtocol], set[type[MiddlewareProtocol]]]

    def validate(self) -> list[str]:
        # Returns list of errors (empty if valid)
        # Checks for cycles and ordering conflicts
        ...
```

### Interface Contracts

#### Public API: Adding Typed Middleware

```python
# New method on FastAPI app
app.add_typed_middleware(
    AuthMiddleware,
    dependencies=[Depends(get_db)],
    depends_on=(CORSMiddleware,)  # Must run after CORS
)
```

#### Migration Path

```python
# Legacy middleware continues to work
app.add_middleware(BaseHTTPMiddleware, dispatch=handler)

# New typed middleware
app.add_typed_middleware(AuthMiddleware)

# Mixed usage supported
app.add_middleware(CORSMiddleware)
app.add_typed_middleware(AuthMiddleware)
```

### Quickstart Example

```python
from fastapi import FastAPI, Depends
from fastapi.middleware import MiddlewareProtocol

class AuthMiddleware(MiddlewareProtocol[Request, Response]):
    def __init__(self, app: ASGIApp, db: Database = Depends(get_db)):
        self.app = app
        self.db = db

    async def __call__(self, request, call_next):
        # Type-safe: request is Request
        user = await self.db.get_user(token=request.headers["authorization"])
        request.state.user = user
        return await call_next(request)

app = FastAPI()
app.add_typed_middleware(AuthMiddleware, depends_on=(CORSMiddleware,))
```

---

## Phase 2: Implementation Tasks (Placeholder)

*Tasks will be generated after design approval*

### Task Structure

```
tasks/
├── core-typed-middleware/      # MiddlewareProtocol implementation
├── dependency-injection/       # DI integration
├── ordering-validation/        # Compile-time ordering
├── backward-compat/            # Legacy middleware support
├── documentation/              # OpenAPI integration
└── tests/                      # Test suite
```

---

## Success Criteria Validation

| Criterion | Metric | Validation Method |
|-----------|--------|-------------------|
| Type Safety | mypy --strict passes | Run mypy on test middleware |
| Compile-Time Validation | Errors before runtime | Unit test of validator |
| IDE Support | Autocomplete works | Manual IDE testing |
| Zero Runtime Overhead | <1ms per request | Benchmark comparison |
| Adoption | Legacy works | Integration tests |
| Documentation | OpenAPI reflects middleware | Auto-generated docs |

---

## Open Questions

1. **Protocol signature design**: Type-safe (Request[T]) vs ASGI-native (scope/receive/send)
2. **Validation timing**: Startup vs compile-time vs both
3. **Compatibility depth**: Wrap legacy or coexist

*To be resolved in Phase 0 research*

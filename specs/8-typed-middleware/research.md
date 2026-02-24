# Research: Typed Middleware

## Overview

This document captures research findings for implementing typed middleware in FastAPI.

## Decision 1: Protocol vs ABC for Type Safety

**Question**: Should MiddlewareProtocol use Python's Protocol class or ABC?

### Analysis

**Protocol (Structural Subtyping)**
- Pros:
  - No inheritance required
  - Maximum flexibility for users
  - Better type inference with mypy
  - Works with function-based middleware
- Cons:
  - Less explicit contract

**ABC (Nominal Subtyping)**
- Pros:
  - Explicit contract enforcement
  - Clear inheritance hierarchy
- Cons:
  - Requires inheritance
  - Less flexible

### Decision: Protocol

**Rationale**: FastAPI's philosophy is "minimal boilerplate". Protocol allows:
- Function-based middleware
- Class-based middleware
- Gradual adoption without rewrites

### Alternatives Considered

- ABC: Rejected due to inflexibility
- Hybrid: Too complex for initial implementation

---

## Decision 2: Type-Safe vs ASGI-Native Dispatch

**Question**: Should dispatch method use typed Request/Response or raw ASGI?

### Analysis

**Type-Safe Approach (Request[T])**
```python
async def __call__(
    self,
    request: Request,
    call_next: Callable[[Request], Response]
) -> Response:
```
- Pros: Full type hints, IDE autocomplete
- Cons: Requires Request/Response wrapper

**ASGI-Native Approach (scope/receive/send)**
```python
async def __call__(
    self,
    scope: Scope,
    receive: Receive,
    send: Send
) -> None:
```
- Pros: Direct ASGI compatibility, matches Starlette
- Cons: Less type safety

### Decision: Hybrid Approach

**Rationale**: Provide both:
1. `MiddlewareProtocol` - ASGI-native for compatibility
2. `TypedMiddleware` - Type-safe wrapper for convenience

This allows:
- Full backward compatibility
- New users get type safety
- No runtime overhead for legacy

---

## Decision 3: Middleware Ordering Validation

**Question**: When should middleware ordering be validated?

### Analysis

**Option A: Runtime at Startup**
- Validate when `add_typed_middleware()` is called
- Check for cycles using topological sort
- Actionable error messages

**Option B: Mypy Plugin**
- Validate at type-check time
- Requires additional tooling
- Better IDE integration

**Option C: Both**
- Runtime validation as fallback
- Mypy plugin for early detection

### Decision: Option A (Runtime at Startup)

**Rationale**:
- Works out of the box (no mypy plugin needed)
- Validates all middleware, not just typed ones
- Simpler initial implementation
- Can add mypy plugin later

---

## Decision 4: Dependency Injection for Middleware

**Question**: How should middleware dependencies work?

### Analysis

FastAPI's dependency injection system uses:
- `Depends` for declaring dependencies
- `yield` for cleanup
- `Request` for getting request-scoped values

**Approach**: Extend to middleware
```python
class AuthMiddleware:
    def __init__(self, db: Database = Depends(get_db)):
        self.db = db
```

### Decision: Same DI System

**Rationale**:
- Consistent API for users
- Reuse existing code
- Supports all dependency features (lifecycle, caching, etc.)

---

## Decision 5: Backward Compatibility

**Question**: How to handle existing BaseHTTPMiddleware?

### Analysis

**Option A: Wrap Legacy**
- Convert existing to typed at runtime
- Complex internal logic

**Option B: Coexist**
- Keep existing `add_middleware()` as-is
- New `add_typed_middleware()` for typed
- Interoperable via ASGI stack

### Decision: Option B (Coexist)

**Rationale**:
- No breaking changes
- Clear migration path
- Simpler implementation

---

## References

- [Python Protocol Documentation](https://docs.python.org/3/library/typing.html#typing.Protocol)
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [Starlette Middleware](https://www.starlette.io/middleware/)
- [ASGI Spec](https://asgi.readthedocs.io/)

---

## Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Protocol vs ABC | Protocol | Flexibility, no inheritance needed |
| Dispatch signature | Hybrid | Backward compat + type safety |
| Ordering validation | Runtime | Simpler, works out of box |
| Dependencies | Same DI | Consistent API |
| Legacy support | Coexist | No breaking changes |

# Feature Specification: Typed Middleware

## Overview

Implement type-safe middleware system for FastAPI with compile-time validation, enabling developers to define middleware with full type hints for request/response handling and dependencies.

## Problem Statement

FastAPI currently relies on Starlette's middleware system, which provides minimal type safety. Developers cannot:
- Define middleware with typed request/response objects
- Express middleware dependencies through type hints
- Validate middleware ordering at compile time
- Catch middleware-related type errors before runtime

This lack of type safety leads to runtime errors, reduced IDE support, and slower development iteration.

## User Scenarios & Testing

### Scenario 1: Type-Safe Request/Response Middleware

A developer wants to create authentication middleware that validates JWT tokens and attaches user information to the request. With typed middleware:
- The middleware explicitly declares expected request and response types
- Type errors are caught during development (IDE, mypy)
- Request/response data flows are self-documenting

**Test**: Developer creates middleware; mypy catches type mismatches in dispatch method signature.

### Scenario 2: Middleware with Typed Dependencies

A developer needs middleware that accesses database connections and configuration. With typed dependencies:
- Dependencies are expressed through type hints (e.g., `DatabasePool`, `AppConfig`)
- Dependency injection works similarly to route dependencies
- Testing is simplified with explicit dependency contracts

**Test**: Developer defines middleware with typed dependencies; static analysis validates the contract.

### Scenario 3: Compile-Time Middleware Ordering

A developer adds multiple middleware (CORS, Auth, Rate Limiting) and needs to ensure correct execution order. With compile-time ordering:
- Middleware dependencies are declared explicitly
- Conflicts are detected before runtime
- IDE warns about potential ordering issues

**Test**: Developer declares conflicting middleware order; build fails with actionable error.

### Scenario 4: Migration from Legacy Middleware

Existing FastAPI applications use traditional middleware. Typed middleware should be:
- Backward compatible with existing middleware
- Gradually adoptable (no forced rewrites)
- Interoperable with Starlette middleware

**Test**: Legacy middleware continues to work alongside typed middleware.

## Functional Requirements

### FR-001: MiddlewareProtocol Definition

- Create `MiddlewareProtocol` abstract base class or Protocol that defines the contract for typed middleware
- Protocol must include typed `dispatch` method with type parameters for Request and Response
- Must support both synchronous and asynchronous middleware implementations
- Must be compatible with ASGI specification

### FR-002: Type-Safe Request/Response Handling

- Middleware must declare input and output types via type parameters
- Request and Response objects must use generic type parameters
- Type coercion must work automatically based on declared types
- Invalid type transformations must produce clear error messages

### FR-003: Typed Middleware Dependencies

- Middleware can declare dependencies using FastAPI's dependency injection system
- Dependencies must be resolvable at middleware initialization
- Circular dependency detection must be enforced
- Dependencies must support the same lifecycle management as route dependencies

### FR-004: Compile-Time Middleware Ordering

- Middleware must declare `depends_on` relationships explicitly
- Ordering conflicts must be detected at static analysis time
- Middleware graph must be validated before application startup
- Circular dependencies between middleware must be rejected

### FR-005: Backward Compatibility

- Existing `BaseHTTPMiddleware` and Starlette middleware must continue working
- New typed middleware must be interoperable with legacy middleware
- No breaking changes to existing API surface

### FR-006: Documentation Generation

- Typed middleware must generate OpenAPI documentation automatically
- Middleware execution order must be reflected in API docs
- Type information must be preserved in generated schemas

## Key Entities

### MiddlewareProtocol

- **Type Parameters**: `RequestT`, `ResponseT`
- **Required Methods**: `dispatch(request: RequestT) -> ResponseT`
- **Optional Methods**: `on_startup()`, `on_shutdown()`

### MiddlewareDependency

- **Purpose**: Declare dependencies required by middleware
- **Attributes**: type annotation, factory, lifecycle scope
- **Resolution**: Same DI system as route dependencies

### MiddlewareOrder

- **Purpose**: Validate middleware execution sequence
- **Attributes**: middleware class, dependencies, priority
- **Validation**: Static analysis of dependency graph

## Success Criteria

1. **Type Safety**: Developers can define middleware with full type hints; mypy --strict passes without middleware-related type errors
2. **Compile-Time Validation**: Middleware ordering conflicts are detected before runtime with actionable error messages
3. **IDE Support**: Autocomplete and type checking work in major IDEs (VS Code, PyCharm)
4. **Zero Runtime Overhead**: Typed middleware has no measurable performance impact compared to existing middleware
5. **Adoption**: Existing middleware patterns work without modification; migration path is available
6. **Documentation**: API docs automatically reflect middleware chain and execution order

## Assumptions

- Python version 3.9+ (supports PEP 585 generics)
- mypy is the primary type checker; pyright support is desirable
- Current Starlette middleware behavior is preserved
- Performance must match or exceed current middleware implementation
- Dependency injection system will be extended, not rewritten

## Constraints

- Must maintain backward compatibility with existing FastAPI applications
- Cannot introduce breaking changes to public API
- Must work with ASGI-compatible servers (Uvicorn, Hypercorn)
- Must support both class-based and function-based middleware

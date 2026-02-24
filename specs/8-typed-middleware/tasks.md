# Tasks: Typed Middleware

## Feature: Typed Middleware

**Feature**: Implement type-safe middleware system for FastAPI with compile-time validation
**Branch**: 8-typed-middleware

---

## Phase 1: Setup

- [x] T001 Create MiddlewareProtocol class in fastapi/middleware/typing.py with RequestT and ResponseT type parameters
- [x] T002 Add MiddlewareProtocol exports to fastapi/middleware/__init__.py

---

## Phase 2: Foundational

- [x] T003 Implement MiddlewareConfig dataclass in fastapi/middleware/config.py to store middleware configuration
- [x] T004 [P] Implement MiddlewareGraph class in fastapi/middleware/graph.py for tracking middleware ordering
- [x] T005 Implement cycle detection in MiddlewareGraph using topological sort
- [x] T006 Create OrderedMiddlewareError exception class in fastapi/middleware/exceptions.py
- [x] T007 Add `add_typed_middleware()` method to FastAPI class in fastapi/applications.py
- [x] T008 Integrate MiddlewareGraph validation into add_typed_middleware()

---

## Phase 3: User Story 1 - Type-Safe Request/Response Middleware

**Goal**: Developers can define middleware with typed request/response objects

- [x] T009 [P] [US1] Implement typed dispatch method in MiddlewareProtocol with RequestT and ResponseT type parameters
- [x] T010 [US1] Create TypedMiddleware wrapper class in fastapi/middleware/typed.py to adapt ASGI to type-safe interface
- [x] T011 [US1] Implement type coercion based on declared RequestT/ResponseT types
- [x] T012 [US1] Add clear error messages for invalid type transformations

---

## Phase 4: User Story 2 - Middleware with Typed Dependencies

**Goal**: Middleware can declare dependencies using FastAPI's dependency injection

- [x] T013 [P] [US2] Extend dependency resolution to support middleware in fastapi/dependencies/utils.py
- [x] T014 [US2] Implement dependency injection for middleware __init__ methods
- [x] T015 [US2] Add lifecycle management support (startup/shutdown hooks) for middleware
- [x] T016 [US2] Implement circular dependency detection for middleware dependencies

---

## Phase 5: User Story 3 - Compile-Time Middleware Ordering

**Goal**: Middleware ordering conflicts are detected before runtime

- [x] T017 [P] [US3] Implement depends_on validation in MiddlewareGraph
- [x] T018 [US3] Add reference validation (all depends_on targets must exist)
- [x] T019 [US3] Implement topological sort for deterministic ordering
- [x] T020 [US3] Add comprehensive error messages for ordering conflicts

---

## Phase 6: User Story 4 - Backward Compatibility

**Goal**: Existing middleware patterns work without modification

- [x] T021 [P] [US4] Ensure BaseHTTPMiddleware continues to work via inherited add_middleware()
- [x] T022 [US4] Verify interoperability between legacy and typed middleware in middleware stack
- [x] T023 [US4] Test mixed usage scenarios (legacy + typed middleware)

---

## Phase 7: OpenAPI Documentation

- [x] T024 [P] Integrate middleware chain information into OpenAPI schema generation
- [x] T025 Reflect middleware execution order in API documentation

---

## Phase 8: Tests

- [x] T026 [P] Write unit tests for MiddlewareProtocol in tests/middleware/test_protocol.py
- [x] T027 Write unit tests for MiddlewareGraph cycle detection in tests/middleware/test_graph.py
- [x] T028 Write integration tests for add_typed_middleware() in tests/middleware/test_integration.py
- [x] T029 Write tests for dependency injection in middleware in tests/middleware/test_dependencies.py
- [x] T030 Write tests for backward compatibility in tests/middleware/test_compatibility.py

---

## Phase 9: Polish

- [x] T031 Run mypy --strict and fix any type errors
- [x] T032 Add type stubs for IDE support
- [x] T033 Update quickstart.md with working examples
- [x] T034 Add middleware documentation to docs/

---

## Dependencies

```
Phase 1 (Setup)
    └── Phase 2 (Foundational)
            ├── Phase 3 (US1: Type-Safe)
            ├── Phase 4 (US2: Dependencies)
            ├── Phase 5 (US3: Ordering)
            └── Phase 6 (US4: Compatibility)
                    ├── Phase 7 (OpenAPI)
                    ├── Phase 8 (Tests)
                    └── Phase 9 (Polish)
```

## Parallel Opportunities

- T003 and T004 can run in parallel (different files)
- T009, T013, T017, T021 can run in parallel (different user stories)
- T026, T027, T028 can run in parallel (different test files)

## Independent Test Criteria

| User Story | Test Criteria |
|------------|---------------|
| US1 | mypy catches type mismatches in dispatch method signature |
| US2 | Static analysis validates dependency contracts |
| US3 | Build fails with actionable error on conflicting order |
| US4 | Legacy middleware works alongside typed middleware |

## MVP Scope

User Story 1 (Type-Safe Request/Response) is recommended as MVP as it provides the core typed middleware functionality without the complexity of dependencies, ordering validation, and OpenAPI integration.

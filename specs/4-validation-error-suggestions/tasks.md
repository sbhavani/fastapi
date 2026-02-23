# Tasks: Validation Error Suggestions

**Feature**: Validation Error Suggestions
**Branch**: 4-validation-error-suggestions
**Generated**: 2026-02-23

## Summary

- **Total Tasks**: 24
- **User Stories**: 4
- **Parallel Opportunities**: 8 tasks
- **MVP Scope**: User Story 1 (Field Path Context)

## Dependencies

```
Phase 2 (Foundational)
    ↓
Phase 3 (US1 - Field Path)
    ↓
Phase 4 (US2 - Examples)
    ↓
Phase 5 (US3 - Suggestions)
    ↓
Phase 6 (US4 - Backward Compat)
    ↓
Phase 7 (Polish)
```

## Implementation Strategy

**MVP First**: Phase 3 (User Story 1) delivers the core field path feature. Subsequent phases build on this foundation incrementally.

**Incremental Delivery**:
- Each user story phase is independently testable
- Tests can be added alongside implementation
- Backward compatibility verified in final phase

---

## Phase 1: Setup

No setup tasks required - this feature extends existing FastAPI validation infrastructure.

---

## Phase 2: Foundational

Core infrastructure for error enhancement.

- [X] T001 Create error enhancement module at fastapi/error_enhancement.py
- [X] T002 [P] Implement field path builder function in fastapi/error_enhancement.py
- [X] T003 [P] Implement string similarity function in fastapi/error_enhancement.py
- [X] T004 [P] Implement example value generator function in fastapi/error_enhancement.py

**Independent Test Criteria**: Unit tests pass for all utility functions in isolation.

---

## Phase 3: User Story 1 - Field Path Context

**Goal**: Display complete field path in dot notation for validation errors

**User Story**: As a developer, I want to see the exact location of validation errors in my request data so that I can quickly identify and fix issues.

**Priority**: P1 (Highest)

**Independent Test Criteria**: Validation errors include `field_path` property with correct dot-notation path.

### Implementation Tasks

- [X] T005 [P] [US1] Add field_path generation to exception handler in fastapi/exception_handlers.py
- [X] T006 [P] [US1] Handle array index notation (e.g., items[0].name) in field path builder
- [X] T007 [US1] Test simple field path generation in tests/test_validation_error_suggestions.py

---

## Phase 4: User Story 2 - Example Corrections

**Goal**: Show example valid values in validation errors

**User Story**: As a developer, I want to see examples of valid values in validation errors so that I know what format is expected.

**Priority**: P2

**Independent Test Criteria**: Validation errors include `example` property with valid value format.

### Implementation Tasks

- [X] T008 [P] [US2] Connect example generator to exception handler in fastapi/exception_handlers.py
- [X] T009 [P] [US2] Add format-based example generation (email, URL, date) in fastapi/error_enhancement.py
- [X] T010 [US2] Add expected_type generation to exception handler
- [X] T011 [US2] Test example value generation in tests/test_validation_error_suggestions.py

---

## Phase 5: User Story 3 - Similar Field Suggestions

**Goal**: Suggest correct field names when a typo is detected

**User Story**: As a developer, when I make a typo in a field name, I want the error to suggest the correct field name so that I can quickly fix the mistake.

**Priority**: P3

**Independent Test Criteria**: Validation errors include `suggested_field` property when typo is detected (confidence > 0.6).

### Implementation Tasks

- [X] T012 [US3] Integrate string similarity into exception handler for typo detection
- [X] T013 [US3] Add threshold configuration for similarity matching
- [X] T014 [US3] Test field name suggestion in tests/test_validation_error_suggestions.py

---

## Phase 6: User Story 4 - Backward Compatibility

**Goal**: Ensure existing error handling code continues to work

**User Story**: As a developer, I want my existing error handling code to continue working without modifications so that I can upgrade FastAPI without rewriting my error handling.

**Priority**: P2

**Independent Test Criteria**: All original error fields remain present, new fields are optional (null).

### Implementation Tasks

- [X] T015 [P] [US4] Verify all original error fields preserved in exception handler
- [X] T016 [P] [US4] Add null safety for all new fields
- [X] T017 [US4] Test backward compatibility in tests/test_validation_error_suggestions.py
- [X] T018 [US4] Run existing validation error tests to ensure no regression

---

## Phase 7: Polish & Cross-Cutting Concerns

Final integration and validation.

- [X] T019 [P] Add performance benchmark tests in tests/test_validation_error_performance.py
- [ ] T020 Verify mypy strict type checking passes
- [ ] T021 Update OpenAPI schema if needed for enhanced errors
- [X] T022 Add integration test with nested models in tests/test_validation_error_suggestions.py
- [X] T023 Test with WebSocket validation errors in tests/test_validation_error_suggestions.py
- [X] T024 Run full test suite to verify no regressions

---

## Parallel Execution Examples

### Example 1: Phase 3 (US1) Tasks Can Run in Parallel
```bash
# T005 and T006 are independent:
# - T005 modifies exception_handlers.py
# - T006 modifies error_enhancement.py
# These can be implemented by different developers simultaneously
```

### Example 2: Phase 4 (US2) Tasks Can Run in Parallel
```bash
# T008, T009, and T010 touch different files/functions:
# - T008: Connects existing generator to handler
# - T009: Adds new format-based examples
# - T010: Adds expected_type generation
```

### Example 3: Phase 6 (US4) Tasks Can Run in Parallel
```bash
# T015 and T016 are independent:
# - T015 ensures original fields preserved
# - T016 adds null safety
```

---

## File Paths Reference

| Task | File Path |
|------|-----------|
| T001 | fastapi/error_enhancement.py |
| T002 | fastapi/error_enhancement.py |
| T003 | fastapi/error_enhancement.py |
| T004 | fastapi/error_enhancement.py |
| T005 | fastapi/exception_handlers.py |
| T006 | fastapi/error_enhancement.py |
| T007 | tests/test_validation_error_suggestions.py |
| T008 | fastapi/exception_handlers.py |
| T009 | fastapi/error_enhancement.py |
| T010 | fastapi/exception_handlers.py |
| T011 | tests/test_validation_error_suggestions.py |
| T012 | fastapi/exception_handlers.py |
| T013 | fastapi/error_enhancement.py |
| T014 | tests/test_validation_error_suggestions.py |
| T015 | fastapi/exception_handlers.py |
| T016 | fastapi/error_enhancement.py |
| T017 | tests/test_validation_error_suggestions.py |
| T018 | tests/ (existing tests) |
| T019 | tests/test_validation_error_performance.py |
| T020 | mypy (CI check) |
| T021 | fastapi/openapi/ |
| T022 | tests/test_validation_error_suggestions.py |
| T023 | tests/test_validation_error_suggestions.py |
| T024 | test suite |

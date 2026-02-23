# Tasks: Enhanced Validation Error Messages

**Feature**: Validation Error Message Improvements
**Branch**: 5-validation-error-suggestions
**Created**: 2026-02-23

---

## Implementation Strategy

This feature follows an MVP approach with incremental delivery:
- **MVP (Phase 3)**: Field path context in error responses - core value delivered first
- **Phase 4**: Similar field name suggestions - typo detection
- **Phase 5**: Example value display - type-based examples
- **Phase 6**: WebSocket validation enhancement
- **Phase 7**: Performance optimization and polish

---

## Phase 1: Setup

Project initialization and configuration.

- [x] T001 Create error enhancement module structure in fastapi/error_enhancement.py
- [x] T002 Add type definitions for EnhancedErrorDetail in fastapi/error_enhancement.py

---

## Phase 2: Foundational

Core infrastructure tasks that must complete before user story implementation.

- [x] T003 Implement build_field_path() function in fastapi/error_enhancement.py
- [x] T004 Implement find_similar_field_name() function in fastapi/error_enhancement.py
- [x] T005 Implement get_example_for_type() function in fastapi/error_enhancement.py
- [x] T006 Implement get_expected_type() function in fastapi/error_enhancement.py

---

## Phase 3: User Story 1 - Field Path Context

**Story Goal**: API consumers receive validation errors with clear field path in dot notation

**Independent Test Criteria**:
- When validation fails on nested field, field_path shows full path (e.g., "body.user.profile.age")
- When validation fails on list item, field_path includes index (e.g., "body.items[0].name")
- Original Pydantic error fields (type, loc, msg, input) are preserved

### Implementation Tasks

- [x] T007 [P] [US1] Implement enhance_single_error() function in fastapi/error_enhancement.py
- [x] T008 [P] [US1] Implement enhance_errors() function in fastapi/error_enhancement.py
- [x] T009 [US1] Update request_validation_exception_handler in fastapi/exception_handlers.py
- [x] T010 [US1] Run existing validation error tests to verify backwards compatibility

### Test Tasks

- [x] T011 [US1] Write unit tests for build_field_path() in tests/test_error_enhancement.py
- [x] T012 [US1] Write integration test for nested field path in tests/test_error_enhancement.py

---

## Phase 4: User Story 2 - Similar Field Name Suggestions

**Story Goal**: API consumers receive suggestions for fixing typos in field names

**Independent Test Criteria**:
- When user submits "usernmae" and "username" exists, suggestion is "Did you mean 'username'?"
- When no similar field exists, suggestion is null
- Suggestions only come from valid fields in the same model

### Implementation Tasks

- [x] T013 [P] [US2] Integrate find_similar_field_name() into enhance_single_error() in fastapi/error_enhancement.py
- [x] T014 [US2] Add model field extraction logic in fastapi/error_enhancement.py

### Test Tasks

- [x] T015 [US2] Write unit tests for find_similar_field_name() in tests/test_error_enhancement.py
- [x] T016 [US2] Write integration test for typo suggestion in tests/test_error_enhancement.py

---

## Phase 5: User Story 3 - Example Value Display

**Story Goal**: API consumers receive example values showing valid input format

**Independent Test Criteria**:
- Type errors include expected_type (e.g., "integer", "string")
- Type errors include example (e.g., "Expected an integer, e.g., 25")
- Fields with defaults show default value as example

### Implementation Tasks

- [x] T017 [P] [US3] Integrate get_example_for_type() into enhance_single_error() in fastapi/error_enhancement.py
- [x] T018 [P] [US3] Integrate get_expected_type() into enhance_single_error() in fastapi/error_enhancement.py

### Test Tasks

- [x] T019 [US3] Write unit tests for get_example_for_type() in tests/test_error_enhancement.py
- [x] T020 [US3] Write integration test for example display in tests/test_error_enhancement.py

---

## Phase 6: User Story 4 - WebSocket Validation Enhancement

**Story Goal**: WebSocket validation errors include same enhancements as HTTP

**Independent Test Criteria**:
- WebSocket close frame includes field_path
- WebSocket close frame includes suggestions and examples
- Path prefix is "ws.message" for WebSocket errors

### Implementation Tasks

- [x] T021 [US4] Update websocket_request_validation_exception_handler in fastapi/exception_handlers.py

### Test Tasks

- [x] T022 [US4] Write integration test for WebSocket validation errors in tests/test_error_enhancement.py

---

## Phase 7: Polish & Cross-Cutting Concerns

Performance optimization, configuration, and final integration.

- [x] T023 Add ErrorEnhancementConfig class with enable_suggestions, enable_examples, suggestion_threshold in fastapi/error_enhancement.py
- [x] T024 Run performance benchmark to verify <5ms overhead in tests/test_validation_error_performance.py
- [x] T025 Run mypy type checking on new code in fastapi/error_enhancement.py
- [x] T026 Run full test suite to verify backwards compatibility

---

## Dependencies

```
T001 ──┬── T002 ──┬── T003 ──┬── T007 ──┬── T009 ──┬── T010
       │          │          │          │          │
       │          │          │          │          └──── T012 (T009)
       │          │          │          │
       │          │          │          ├──── T008 ──┬── T010
       │          │          │          │             │
       │          │          │          │             └──── T011 (T007)
       │          │          │          │
       │          │          │          ├──── T013 ──┬── T016 (T013)
       │          │          │          │             │
       │          │          │          │             └──── T014 ──┬── T016
       │          │          │          │                         │
       │          │          │          │                         └──── T015 (T013)
       │          │          │          │
       │          │          │          ├──── T017 ──┬── T020 (T017)
       │          │          │          │             │
       │          │          │          │             └──── T018 ──┬── T020
       │          │          │          │                         │
       │          │          │          │                         └──── T019 (T017)
       │          │          │          │
       │          │          │          └──── T021 ──┬── T022 (T021)
       │          │          │                      │
       │          │          │                      └──── T023 ──┬── T025
       │          │          │                                  │
       │          │          │                                  └──── T024 ──┬── T026
       │          │          │                                              │
       │          │          └──── T004 ──┬── T013                          │
       │          │          │             │                                 │
       │          │          │             ├──── T015 (T004)
       │          │          │             │
       │          │          │             └──── T014 ──┬── T016
       │          │          │                         │
       │          │          └──── T005 ──┬── T017    │
       │          │          │             │           │
       │          │          │             ├──── T019 (T005)
       │          │          │             │
       │          │          │             └──── T018 ──┬── T020
       │          │          │                         │
       │          │          └──── T006 ──┬── T017    │
       │          │                        │           │
       │          │                        └──── T018 ──┬── T020
       │          │                                      │
       └──────────┴──────────────────────────────────────┴── T022
```

---

## Parallel Execution Opportunities

### Task Group A: Independent Functions (T003-T006)
- T003, T004, T005, T006 can run in parallel - no dependencies between them

### Task Group B: US1 Implementation (T007-T008)
- T007 and T008 can run in parallel after T003-T006 complete

### Task Group C: US2 Implementation (T013-T014)
- T013 and T014 can run in parallel

### Task Group D: US3 Implementation (T017-T018)
- T017 and T018 can run in parallel

---

## Suggested MVP Scope

**MVP = Phase 3 (User Story 1) only**

This delivers the core value proposition:
- Field path context in all validation errors
- Maintains backwards compatibility
- Foundation for remaining features

**MVP Tasks**: T001-T012

After MVP is working, proceed to:
- Phase 4: Typo suggestions (T013-T016)
- Phase 5: Examples (T017-T020)
- Phase 6: WebSocket (T021-T022)
- Phase 7: Polish (T023-T026)

---

## Task Count Summary

| Phase | Description | Task Count |
|-------|-------------|------------|
| Phase 1 | Setup | 2 |
| Phase 2 | Foundational | 4 |
| Phase 3 | US1 - Field Path | 6 |
| Phase 4 | US2 - Suggestions | 4 |
| Phase 5 | US3 - Examples | 4 |
| Phase 6 | US4 - WebSocket | 2 |
| Phase 7 | Polish | 4 |
| **Total** | | **26** |

---

## Format Validation

All tasks follow the required checklist format:
- ✅ Each task starts with `- [ ]`
- ✅ Each task has TaskID (T001, T002, etc.)
- ✅ Each user story task has [USN] label
- ✅ Each parallelizable task has [P] marker
- ✅ Each task has clear file path

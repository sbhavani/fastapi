# Implementation Plan: Enhanced Validation Error Messages

**Branch**: 5-validation-error-suggestions
**Feature**: Validation Error Message Improvements
**Created**: 2026-02-23

---

## Technical Context

### Current Implementation

The FastAPI validation error system consists of:

1. **ValidationException** (base class in `fastapi/exceptions.py`)
   - Stores validation errors from Pydantic
   - Provides `errors()` method returning the raw Pydantic error list
   - Includes endpoint context for debugging

2. **RequestValidationError** and **WebSocketRequestValidationError**
   - Extend ValidationException
   - Used for request body and WebSocket message validation

3. **Exception Handlers** (in `fastapi/exception_handlers.py`)
   - `request_validation_exception_handler`: Returns 422 with `{"detail": errors}`
   - `websocket_request_validation_exception_handler`: Closes WebSocket with errors

### Pydantic Error Structure

Pydantic v2 returns errors with this structure:
```python
{
    "type": "string_type",
    "loc": ("body", "user", "age"),
    "msg": "Input should be a valid string",
    "input": 25,
    "url": "https://errors.pydantic.dev/...",
    "ctx": {"expected_type": "str"}
}
```

### Unknowns / NEEDS CLARIFICATION

- **Q1**: Should the enhanced fields be added to each error item in the `detail` array, or as a separate top-level structure?
  - Option A: Add to each error item (e.g., `error["field_path"] = "body.user.age"`)
  - Option B: Add as separate `enhanced_detail` key alongside original `detail`

- **Q2**: How should field path be constructed for the response? Should it use Pydantic's `loc` tuple directly or transform it?
  - Option A: Use Pydantic's `loc` tuple converted to dot notation (e.g., `("body", "user", "age")` → `"body.user.age"`)
  - Option B: Create custom path builder with index support

- **Q3**: Where should the enhancement logic reside?
  - Option A: In exception handlers (fastapi/exception_handlers.py)
  - Option B: In a dedicated error enhancement module (fastapi/error_enhancement.py)
  - Option C: In the ValidationException class itself

---

## Constitution Check

### Core Principles Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Standards-Based** | ✅ PASS | Error format remains valid JSON, compatible with OpenAPI |
| **II. Type Safety** | ✅ PASS | New structures will have proper type annotations |
| **III. Test-First** | ✅ PASS | Tests required before implementation per workflow |
| **IV. Performance** | ⚠️ CONDITIONAL | Must meet <5ms overhead requirement |
| **V. Developer Experience** | ✅ PASS | Core feature directly improves DX |

### Gate Evaluation

- **Type Safety Gate**: Implementation must include type hints and pass mypy strict
- **Test Gate**: Must have unit and integration tests before implementation complete
- **Performance Gate**: Must include benchmark showing <5ms overhead

---

## Phase 0: Research

### Research Questions

1. **String Similarity Algorithms**: What is the best algorithm for detecting typos in field names?
   - Levenshtein distance (edit distance)
   - Jaro-Winkler similarity
   - Fuzzy matching threshold selection

2. **Pydantic v2 Error Extension**: Can we extend Pydantic errors with custom fields without breaking serialization?

3. **Performance Optimization**: How to efficiently calculate suggestions without impacting request latency?

### Research Findings

(To be filled after research phase)

---

## Phase 1: Design

### Data Model

#### EnhancedErrorDetail

```python
class EnhancedErrorDetail(TypedDict, total=False):
    # Original Pydantic error fields
    type: str
    loc: tuple[str, ...]
    msg: str
    input: Any
    url: str
    ctx: dict[str, Any]

    # NEW: Enhancement fields
    field_path: str          # Dot notation: "body.user.age"
    suggestion: str | None   # "Did you mean 'username'?"
    example: str | None      # "Expected an integer, e.g., 25"
    expected_type: str       # Human-readable type: "integer"
```

#### ErrorEnhancementConfig

```python
class ErrorEnhancementConfig:
    enable_suggestions: bool = True
    suggestion_threshold: int = 3  # Max edit distance
    enable_examples: bool = True
    max_path_length: int = 100
```

### Interface Contracts

#### RequestValidationError Response Format

**Before (current)**:
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": ["body", "user", "age"],
      "msg": "Input should be a valid string",
      "input": 25
    }
  ]
}
```

**After (enhanced)**:
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": ["body", "user", "age"],
      "msg": "Input should be a valid string",
      "input": 25,
      "field_path": "body.user.age",
      "expected_type": "string",
      "example": "Expected a string, e.g., \"twenty-five\"",
      "suggestion": null
    }
  ]
}
```

**With typo suggestion**:
```json
{
  "detail": [
    {
      "type": "unknown_field",
      "loc": ["body", "usernmae"],
      "msg": "Extra inputs are not permitted",
      "input": null,
      "field_path": "body.usernmae",
      "expected_type": "object",
      "suggestion": "Did you mean 'username'?"
    }
  ]
}
```

### Module Design

#### New Module: `fastapi/error_enhancement.py`

```python
# Functions to be implemented:
- build_field_path(loc: tuple[str, ...]) -> str
- find_similar_field_name(field_name: str, valid_fields: list[str], threshold: int) -> str | None
- get_example_for_type(field_info: FieldInfo) -> str | None
- get_expected_type(field_info: FieldInfo) -> str
- enhance_validation_error(error: dict, model: type[BaseModel]) -> dict
- enhance_errors(errors: Sequence[dict], model: type[BaseModel]) -> list[dict]
```

#### Modified: `fastapi/exception_handlers.py`

- Update `request_validation_exception_handler` to call enhancement
- Update `websocket_request_validation_exception_handler` to call enhancement

### Quickstart Guide

**For API Consumers**:

When you receive a 422 validation error, the response now includes:

1. **`field_path`**: The exact location of the failed field (e.g., `"body.user.profile.age"`)
2. **`expected_type`**: What type was expected (e.g., `"string"`, `"integer"`)
3. **`example`**: An example of valid input
4. **`suggestion`**: If a typo is detected, the correct field name

**Example Error Response**:
```bash
$ curl -X POST http://localhost:8000/users -d '{"usernmae": "john"}'

{
  "detail": [
    {
      "type": "unknown_field",
      "loc": ["body", "usernmae"],
      "msg": "Extra inputs are not permitted",
      "field_path": "body.usernmae",
      "expected_type": "object",
      "example": "Expected an object with fields: username, email, age",
      "suggestion": "Did you mean 'username'?"
    }
  ]
}
```

---

## Phase 2: Implementation Tasks

(To be generated in tasks.md after plan approval)

---

## Dependencies

- **Pydantic**: Version 2.7.0+ (already dependency)
- **Starlette**: Already used for routing and exceptions
- **No new external dependencies**: String similarity can be implemented with built-in `difflib` or custom implementation

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance overhead | High | Cache field name lists per model; lazy-load suggestions |
| Backwards compatibility | Medium | Preserve original error fields; add new ones |
| Pydantic version changes | Medium | Use abstraction layer; test against multiple Pydantic versions |

## Success Criteria Validation

1. **Error Clarity**: 95% of errors include field_path (automated test)
2. **Suggestion Accuracy**: 90% accuracy when suggestions provided (manual test)
3. **Performance**: <5ms overhead (benchmark test)
4. **Compatibility**: Existing tests pass without modification

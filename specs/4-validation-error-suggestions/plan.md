# Implementation Plan: Validation Error Suggestions

**Feature**: Validation Error Suggestions
**Branch**: 4-validation-error-suggestions
**Plan Version**: 1.0
**Created**: 2026-02-23

## Technical Context

### Current Implementation
- **Validation Errors Source**: Pydantic (the underlying validation library used by FastAPI)
- **Error Format**: Each error is a dictionary with `type`, `loc` (location tuple), and `msg` fields
- **Error Flow**: Pydantic raises `ValidationError` → FastAPI wraps in `RequestValidationError` → Exception handler serializes with `jsonable_encoder`

### Key Files
- `fastapi/exceptions.py`: Contains `ValidationException`, `RequestValidationError` classes
- `fastapi/exception_handlers.py`: Contains `request_validation_exception_handler`
- `fastapi/routing.py`: Where validation is invoked

### Entities from Spec
1. **ValidationError**: Current state has `message`, `type`, `location`; Enhanced adds `field_path`, `suggested_field`, `example`, `expected_type`
2. **FieldSchema**: Stores schema info for generating examples (name, type, format, constraints, example_value)
3. **ErrorContext**: Accumulates context during validation (current_path, parent_objects, field_hierarchy)

### Integration Points
- Pydantic validation errors must be intercepted and enhanced
- JSON Schema generation already exists in FastAPI - can be leveraged for examples
- String similarity for field name suggestions

### Unknowns / NEEDS CLARIFICATION
- [ ] How to intercept Pydantic errors at the right point to add enhancement
- [ ] How to get the field schema from Pydantic models for example generation
- [ ] Similarity threshold value for field name suggestions

---

## Constitution Check

### Principle I: Standards-Based
- **Requirement**: All features MUST support OpenAPI and JSON Schema
- **Status**: ✅ Compatible - Enhanced errors will work with existing OpenAPI schema generation

### Principle II: Type Safety
- **Requirement**: Type checking MUST pass with mypy at strict level
- **Status**: ✅ Will be verified - New types must be properly typed

### Principle III: Test-First Development
- **Requirement**: Tests written before implementation
- **Status**: ✅ Agreed - Test-driven approach will be followed

### Principle IV: Performance
- **Requirement**: No performance penalty for sync code paths
- **Status**: ✅ Will be verified - Error enhancement must be efficient

### Principle V: Developer Experience
- **Requirement**: Error messages MUST be clear and actionable
- **Status**: ✅ Core to this feature - This is the primary goal

### Gate Evaluation
- All principles satisfied - proceed with implementation

---

## Phase 0: Research

### Research Tasks
1. **Pydantic Error Interception**: Research how to intercept and enhance Pydantic validation errors at the right point
2. **Schema Access**: Research how to access Pydantic model field schemas for example generation
3. **String Similarity**: Research efficient string similarity algorithms for typo detection

### Research Outputs
- Document best practices for each unknown in `research.md`
- Resolve all NEEDS CLARIFICATION items

---

## Phase 1: Design & Contracts

### Data Model (data-model.md)

#### Enhanced ValidationError Structure
```json
{
  "type": "string_type",
  "loc": ["body", "user", "email"],
  "msg": "Input should be a valid email address",
  "input": "not-an-email",
  "ctx": {"type": "email"},
  // New enhanced fields:
  "field_path": "user.email",
  "suggested_field": null,
  "example": "user@example.com",
  "expected_type": "string (email format)"
}
```

#### FieldSuggestion Structure
```json
{
  "original": "emal",
  "suggestion": "email",
  "confidence": 0.85
}
```

#### ExampleValue Structure
```json
{
  "field": "email",
  "example": "user@example.com",
  "type": "string",
  "format": "email"
}
```

### Interface Contracts

#### RequestValidationError Enhanced Contract
- **Interface**: JSON error response on 422 status
- **Backward Compatibility**: All original fields preserved, new fields optional
- **New Fields**:
  - `field_path`: Dot-notation path string
  - `suggested_field`: String or null for typo suggestions
  - `example`: Example valid value
  - `expected_type`: Human-readable type description

### Quickstart Guide
- Document migration path for existing applications
- Show before/after error response comparison

---

## Phase 2: Implementation Planning

### Task Breakdown

#### Core Enhancement Tasks
1. Modify `fastapi/exceptions.py`:
   - Add new optional fields to error serialization
   - Create helper functions for field path generation

2. Create error enhancement module:
   - Field path builder (loc tuple → dot notation)
   - Field name similarity finder
   - Example value generator from schema

3. Modify `fastapi/exception_handlers.py`:
   - Enhance errors before serialization
   - Pass schema context to error handler

4. Add tests:
   - Test field path generation
   - Test similarity suggestions
   - Test example generation
   - Test backward compatibility

#### Integration Tasks
5. Integrate with Pydantic validation flow
6. Wire up schema access for example generation
7. Performance optimization for similarity matching

### Dependencies
- Pydantic validation internals
- FastAPI's JSON Schema generation
- String similarity library or custom implementation

### Risks
- Pydantic internal API changes could break interception
- Performance impact of similarity matching on large schemas

---

## Next Steps

1. Complete Phase 0 research to resolve unknowns
2. Generate `data-model.md` with detailed entity definitions
3. Create `contracts/` with interface specifications
4. Generate `quickstart.md` with migration guide

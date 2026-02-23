# Research: Validation Error Suggestions

**Feature**: Validation Error Suggestions
**Created**: 2026-02-23

---

## Research Findings

### 1. Pydantic Error Interception

**Decision**: Intercept errors in the exception handler (`fastapi/exception_handlers.py`)

**Rationale**:
- The `request_validation_exception_handler` receives the `RequestValidationError` which already contains the errors from Pydantic
- The handler has access to the request and can potentially access endpoint information
- This is the single point where all validation errors pass through before being returned to the client

**Implementation approach**:
- Create an error enhancement function that takes the raw errors and model schema
- Enhance each error with field_path, suggested_field, example, and expected_type
- The handler calls this enhancement function before serializing

**Alternatives considered**:
- Intercept in routing.py when creating RequestValidationError - More complex, requires passing schema context
- Subclass RequestValidationError - Would require significant changes to the exception class

---

### 2. Schema Access for Example Generation

**Decision**: Use Pydantic's `model_fields` and JSON schema generation

**Rationale**:
- FastAPI already generates JSON schemas for models using Pydantic
- Pydantic v2 provides `model_fields` to access field metadata
- The field location tuple (`loc`) from errors can be used to traverse the model hierarchy

**Implementation approach**:
- Access the model from the endpoint's depends
- Use `model_fields` to get field constraints and types
- Generate examples from field metadata (e.g., `json_schema_extra`, `field_examples`)

**Alternatives considered**:
- Re-generate JSON schema for each validation - Overhead acceptable for error cases only
- Store pre-computed schemas - Memory tradeoff, may not be worth it

---

### 3. String Similarity for Field Suggestions

**Decision**: Use a simple Levenshtein-based similarity with configurable threshold

**Rationale**:
- Levenshtein distance is well-understood and efficient
- Threshold of 0.6-0.7 provides good balance between false positives and missed suggestions
- Can be optimized later if performance is an issue

**Implementation approach**:
- Compare unknown field names against valid field names in the schema
- Use normalized comparison (lowercase, ignore underscores)
- Only suggest when confidence exceeds threshold

**Alternatives considered**:
- Soundex/phonetic matching - Less effective for typos
- Fuzzy matching libraries - Add dependency, simple implementation sufficient
- Machine learning - Overkill for this use case

---

## Technical Details

### Error Enhancement Pipeline

```
Pydantic ValidationError
    ↓
RequestValidationError(errors, body, endpoint_ctx)
    ↓
request_validation_exception_handler
    ↓
enhance_errors(errors, model_schema)  ← NEW
    ↓
Add: field_path (dot notation from loc)
Add: suggested_field (if typo detected)
Add: example (from schema)
Add: expected_type (from schema)
    ↓
JSONResponse with enhanced errors
```

### Field Path Generation

The `loc` tuple from Pydantic errors contains the path:
- Example: `("body", "user", "address", "zip_code")`
- Convert to dot notation: `"user.address.zip_code"`
- Handle arrays: `("body", "users", 0, "email")` → `"users[0].email"`

### Example Value Sources (Priority Order)

1. `json_schema_extra` on Pydantic field
2. `Field` annotation examples
3. Generated from type hints (e.g., email regex pattern → example@domain.com)
4. Type-based defaults (string → "string", int → 0, bool → true)

---

## Dependencies

- Pydantic v2 (already a dependency)
- No new external dependencies required
- String similarity can be implemented with standard library (difflib)

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Pydantic internal API changes | Use public APIs only (model_fields, model_config) |
| Performance impact | Only enhance on error path, cache schema |
| Large schemas | Limit similarity search scope, early exit |

---

## Conclusion

All unknowns have been resolved. The implementation will:
1. Enhance errors in the exception handler
2. Access model schema via Pydantic's public APIs
3. Use simple Levenshtein similarity with threshold tuning

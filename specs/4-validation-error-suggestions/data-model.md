# Data Model: Validation Error Suggestions

**Feature**: Validation Error Suggestions
**Created**: 2026-02-23

---

## Entity Definitions

### 1. EnhancedValidationError

Represents a single validation error with enhanced context.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | string | Yes | Error type from Pydantic (e.g., "missing", "string_type") |
| loc | tuple[str \| int, ...] | Yes | Location tuple from Pydantic (e.g., ("body", "user", "email")) |
| msg | string | Yes | Human-readable error message |
| input | any | No | The invalid input value |
| ctx | dict | No | Additional context from Pydantic |
| **field_path** | string \| null | No | Dot-notation path (e.g., "user.email") |
| **suggested_field** | string \| null | No | Suggested correct field name if typo detected |
| **example** | string \| null | No | Example of a valid value |
| **expected_type** | string \| null | No | Human-readable expected type |

**JSON Example**:
```json
{
  "type": "string_type",
  "loc": ["body", "user", "email"],
  "msg": "Input should be a valid email address",
  "input": "not-an-email",
  "ctx": {},
  "field_path": "user.email",
  "suggested_field": null,
  "example": "user@example.com",
  "expected_type": "string (email)"
}
```

---

### 2. FieldSchema

Stores schema information for a field to enable example generation.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Field name |
| type | string | Yes | Python type or JSON Schema type |
| format | string \| null | No | JSON Schema format (e.g., "email", "date") |
| constraints | dict | No | Field constraints (min_length, max_length, pattern, etc.) |
| example_value | any | No | Pre-defined example value |
| children | dict[str, FieldSchema] | No | Nested object fields |

**JSON Example**:
```json
{
  "name": "email",
  "type": "string",
  "format": "email",
  "constraints": {"min_length": 3},
  "example_value": "user@example.com",
  "children": {}
}
```

---

### 3. ErrorContext

Accumulates context during validation traversal.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| current_path | list[str \| int] | Yes | Current path being validated |
| parent_objects | list[object] | No | Parent object chain |
| field_hierarchy | list[str] | No | Flattened field path |

---

### 4. FieldSuggestion

Result of field name similarity comparison.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| original | string | Yes | The unknown field name |
| suggestion | string | Yes | The suggested correct name |
| confidence | float | Yes | Similarity score (0.0 to 1.0) |

---

## Validation Rules

### Field Path Generation
- Empty loc tuple → null field_path
- Single element → element as string
- Multiple elements → dot-separated (except array indices use bracket notation)
- Array indices are integers in loc tuple → convert to `[index]` notation

### Example Generation Priority
1. Explicit `example_value` in FieldSchema
2. Format-based examples (email → "user@example.com")
3. Constraint-based examples (enum → first enum value)
4. Type-based defaults (string → "string", int → 0, bool → true)

### Similarity Threshold
- Minimum confidence: 0.6 (60% similar)
- Maximum suggestions: 1 per unknown field
- Case-insensitive comparison
- Ignore underscores and hyphens

---

## State Transitions

### Error Enhancement Flow

```
Raw Pydantic Error
    ↓
Extract loc tuple
    ↓
Build field_path (dot notation)
    ↓
Check for typos (if extra field)
    ↓
Lookup field schema
    ↓
Generate example value
    ↓
Determine expected type
    ↓
Enhanced Error
```

---

## Relationships

```
RequestValidationError
    └── contains many → EnhancedValidationError
                          ├── uses → FieldSchema (for example)
                          └── uses → ErrorContext (during generation)

FieldSuggestion
    └── generated from → FieldSchema (to find valid names)
```

---

## Backward Compatibility

The enhanced fields are **optional**:
- Existing error consumers see original fields only
- New fields are null when not applicable
- Error response structure unchanged (wrapped in "detail" array)

**Original format** (still works):
```json
{
  "detail": [
    {"type": "missing", "loc": ["body", "name"], "msg": "Field required"}
  ]
}
```

**Enhanced format** (new):
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "name"],
      "msg": "Field required",
      "field_path": "name",
      "suggested_field": null,
      "example": "John Doe",
      "expected_type": "string"
    }
  ]
}
```

# Data Model: Validation Error Enhancement

## Entities

### EnhancedErrorDetail

Extends the Pydantic validation error structure with enhancement fields.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `str` | Yes | Pydantic error type (e.g., "string_type") |
| `loc` | `tuple[str, ...]` | Yes | Original Pydantic location tuple |
| `msg` | `str` | Yes | Pydantic error message |
| `input` | `Any` | Yes | The invalid input value |
| `url` | `str` | Yes | Pydantic error URL |
| `ctx` | `dict[str, Any]` | No | Additional context from Pydantic |
| `field_path` | `str` | Yes | Dot-notation path (e.g., "body.user.age") |
| `expected_type` | `str` | Yes | Human-readable expected type |
| `example` | `str \| None` | No | Example of valid input |
| `suggestion` | `str \| None` | No | Typo correction suggestion |

### ErrorEnhancementConfig

Configuration for error enhancement behavior.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enable_suggestions` | `bool` | `True` | Enable similar field name suggestions |
| `suggestion_threshold` | `int` | `3` | Max edit distance for suggestions |
| `enable_examples` | `bool` | `True` | Enable example value display |
| `max_path_length` | `int` | `100` | Maximum field path length |

---

## Relationships

```
RequestValidationError
    |
    +-- errors(): Sequence[dict]  (Pydantic errors)
            |
            +-- [enhanced with field_path]
            +-- [enhanced with suggestion]
            +-- [enhanced with example]
            +-- [enhanced with expected_type]
```

---

## Validation Rules

### Field Path Construction

1. **Root level**: `"body"` for request body
2. **Nested fields**: Dot-separated (`body.user.profile`)
3. **List items**: Index in brackets (`body.items[0]`)
4. **Query params**: `"query.param_name"`
5. **Path params**: `"path.param_name"`
6. **Headers**: `"header.name"`

### Suggestion Logic

1. Extract the failed field name from error location
2. Get list of valid field names from the model
3. Calculate edit distance to each valid field name
4. If minimum distance <= threshold, suggest that field
5. Return formatted suggestion string

### Example Generation

1. **If field has default**: Use default value as example
2. **If field has enum**: Use first enum value
3. **Type-based fallback**:
   - `int` → "e.g., 42"
   - `str` → "e.g., 'string'"
   - `float` → "e.g., 3.14"
   - `bool` → "e.g., true"
   - `list` → "e.g., []"
   - `dict` → "e.g., {}"

---

## State Transitions

### Error Enhancement Flow

```
Request arrives
       |
       v
Pydantic validation
       |
       v
ValidationException raised
       |
       v
Exception handler called
       |
       v
Enhancement applied (field_path, suggestion, example)
       |
       v
JSON response returned
```

### No State Stored

This feature does not maintain any state. Each request is processed independently.

---

## Edge Cases

1. **Empty loc tuple**: Return `"body"` as default path
2. **Very long field path**: Truncate at `max_path_length`
3. **No similar fields found**: Return `suggestion: null`
4. **Multiple suggestions**: Return closest match only
5. **WebSocket errors**: Similar enhancement with path prefix `"ws.message"`

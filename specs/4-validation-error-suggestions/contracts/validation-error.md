# Contract: Enhanced Validation Error Response

**Feature**: Validation Error Suggestions
**Interface Type**: JSON API Response
**Status**: Draft

---

## Interface Overview

This contract defines the enhanced validation error response format returned by FastAPI when request body validation fails (HTTP 422 Unprocessable Entity).

---

## Contract Definition

### RequestValidationError Response

**HTTP Status**: 422 Unprocessable Entity

**Content-Type**: application/json

**Schema** (JSON Schema format):

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/ValidationError"
      }
    }
  },
  "definitions": {
    "ValidationError": {
      "type": "object",
      "properties": {
        "type": {
          "type": "string",
          "description": "Error type from validation system"
        },
        "loc": {
          "type": "array",
          "items": {
            "type": ["string", "integer"]
          },
          "description": "Location tuple in the request body"
        },
        "msg": {
          "type": "string",
          "description": "Human-readable error message"
        },
        "input": {
          "description": "The invalid input value",
          "oneOf": [
            {"type": "string"},
            {"type": "number"},
            {"type": "boolean"},
            {"type": "array"},
            {"type": "object"},
            {"type": "null"}
          ]
        },
        "ctx": {
          "type": "object",
          "description": "Additional context for the error"
        },
        "field_path": {
          "type": ["string", "null"],
          "description": "Dot-notation path to the field (e.g., 'user.address.email')"
        },
        "suggested_field": {
          "type": ["string", "null"],
          "description": "Suggested correct field name if typo detected"
        },
        "example": {
          "type": ["string", "null"],
          "description": "Example of a valid value for this field"
        },
        "expected_type": {
          "type": ["string", "null"],
          "description": "Human-readable expected type description"
        }
      },
      "required": ["type", "loc", "msg"]
    }
  }
}
```

---

## Backward Compatibility

### Guarantees

1. **Original fields always present**: `type`, `loc`, `msg`, `input`, `ctx` remain unchanged
2. **New fields optional**: All enhanced fields (`field_path`, `suggested_field`, `example`, `expected_type`) default to `null`
3. **Structure unchanged**: Response still wrapped in `{"detail": [...]}`
4. **Status code unchanged**: Still returns 422 for validation errors

### Migration Path

Existing code that parses validation errors will continue to work:

```python
# Old code - still works
for error in response.json()["detail"]:
    print(error["type"], error["msg"])

# New code - can use enhancements
for error in response.json()["detail"]:
    print(error.get("field_path"), error.get("example"))
```

---

## Usage Examples

### Example 1: Simple Validation Error

**Request**:
```json
POST /users
{"email": "not-an-email"}
```

**Response**:
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": ["body", "email"],
      "msg": "Input should be a valid email address",
      "input": "not-an-email",
      "ctx": {},
      "field_path": "email",
      "suggested_field": null,
      "example": "user@example.com",
      "expected_type": "string (email)"
    }
  ]
}
```

### Example 2: Nested Field Error

**Request**:
```json
POST /users
{"profile": {"age": "twenty"}}
```

**Response**:
```json
{
  "detail": [
    {
      "type": "int_parsing",
      "loc": ["body", "profile", "age"],
      "msg": "Input should be a valid integer",
      "input": "twenty",
      "ctx": {},
      "field_path": "profile.age",
      "suggested_field": null,
      "example": "25",
      "expected_type": "integer"
    }
  ]
}
```

### Example 3: Typo in Field Name

**Request**:
```json
POST /users
{"emal": "user@example.com"}
```

**Response**:
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "email"],
      "msg": "Field required",
      "input": {"emal": "user@example.com"},
      "ctx": {},
      "field_path": "email",
      "suggested_field": "email",
      "example": "user@example.com",
      "expected_type": "string (email)"
    }
  ]
}
```

### Example 4: Array Index Error

**Request**:
```json
POST /users
{"items": [{"name": "valid"}, {"name": 123}]}
```

**Response**:
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": ["body", "items", 1, "name"],
      "msg": "Input should be a valid string",
      "input": 123,
      "ctx": {},
      "field_path": "items[1].name",
      "suggested_field": null,
      "example": "Item name",
      "expected_type": "string"
    }
  ]
}
```

---

## Error Types Reference

The `type` field indicates the category of validation error. Common types include:

| Type | Description |
|------|-------------|
| missing | Required field not provided |
| string_type | Value is not a string |
| int_type | Value is not an integer |
| float_type | Value is not a float |
| bool_type | Value is not a boolean |
| dict_type | Value is not a dictionary |
| list_type | Value is not a list |
| enum | Value not in allowed values |
| json_invalid | JSON parse error |
| url_parsing | Invalid URL format |
| uuid_parsing | Invalid UUID format |

---

## Implementation Notes

1. **Enhancement is additive**: All new fields are optional
2. **Performance consideration**: Enhancement only happens when errors exist
3. **Schema required**: Example generation needs access to the Pydantic model schema
4. **Typo detection**: Uses string similarity, only suggests high-confidence matches

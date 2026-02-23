# Quickstart: Enhanced Validation Errors

FastAPI now provides enhanced validation error messages that help developers quickly identify and fix validation issues in their API requests.

## What's New

When a validation error occurs, the response now includes:

- **`field_path`**: The exact location of the failed field in dot notation
- **`expected_type`**: What type was expected (e.g., "string", "integer")
- **`example`**: An example of valid input
- **`suggestion`**: If a typo is detected, a suggestion for the correct field name

## Examples

### Type Mismatch

Submit an invalid type:

```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "age": "not-a-number"}'
```

Response:

```json
{
  "detail": [
    {
      "type": "int_parsing",
      "loc": ["body", "age"],
      "msg": "Input should be a valid integer",
      "input": "not-a-number",
      "field_path": "body.age",
      "expected_type": "integer",
      "example": "Expected an integer, e.g., 25",
      "suggestion": null
    }
  ]
}
```

### Field Typo

Submit a misspelled field name:

```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"usernmae": "john", "email": "john@example.com"}'
```

Response:

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
      "example": "Expected an object with fields: username, email, age",
      "suggestion": "Did you mean 'username'?"
    }
  ]
}
```

### Nested Objects

Validation errors in nested objects show the full path:

```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "profile": {"age": "invalid"}}'
```

Response:

```json
{
  "detail": [
    {
      "type": "int_parsing",
      "loc": ["body", "profile", "age"],
      "msg": "Input should be a valid integer",
      "input": "invalid",
      "field_path": "body.profile.age",
      "expected_type": "integer",
      "example": "Expected an integer, e.g., 25",
      "suggestion": null
    }
  ]
}
```

### List Items

Errors in list items include the index:

```bash
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{"items": [{"name": 123}]}'
```

Response:

```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": ["body", "items", 0, "name"],
      "msg": "Input should be a valid string",
      "input": 123,
      "field_path": "body.items[0].name",
      "expected_type": "string",
      "example": "Expected a string, e.g., 'item-name'",
      "suggestion": null
    }
  ]
}
```

## Using the Enhancement

The enhancement is automatic - no code changes required. Existing applications will automatically receive enhanced error responses.

### Disabling Enhancements (Optional)

If needed, you can configure enhancement behavior:

```python
from fastapi import FastAPI
from fastapi.error_enhancement import ErrorEnhancementConfig

app = FastAPI()

# Configure enhancement
app.state.error_enhancement_config = ErrorEnhancementConfig(
    enable_suggestions=False,
    enable_examples=True
)
```

## Migration Guide

### For API Consumers

The enhancement is backward compatible. The new fields are added alongside existing ones:

```python
# Old code still works
errors = response.json()["detail"]
for error in errors:
    print(error["msg"])

# New code can use enhancements
for error in errors:
    print(f"Field: {error.get('field_path')}")
    print(f"Suggestion: {error.get('suggestion')}")
    print(f"Example: {error.get('example')}")
```

### For API Providers

No changes required. The enhancement happens automatically.

If you want to customize enhancement behavior, see the configuration options above.

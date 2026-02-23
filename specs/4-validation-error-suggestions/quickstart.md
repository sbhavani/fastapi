# Quickstart: Validation Error Suggestions

**Feature**: Validation Error Suggestions
**Created**: 2026-02-23

---

## Overview

This guide helps you migrate to the enhanced validation error messages in FastAPI. The new errors include:
- **Field path context**: See exactly where in your data structure the error occurred
- **Similar field suggestions**: Get corrected field names if you made a typo
- **Example values**: See examples of valid input for each field

---

## Before and After

### Before (Original Error)

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "email"],
      "msg": "Field required",
      "input": {},
      "ctx": {}
    }
  ]
}
```

### After (Enhanced Error)

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "email"],
      "msg": "Field required",
      "input": {},
      "ctx": {},
      "field_path": "email",
      "suggested_field": null,
      "example": "user@example.com",
      "expected_type": "string (email)"
    }
  ]
}
```

---

## Migration Guide

### Step 1: Update Error Handling (Optional)

If you currently parse validation errors, your code continues to work. The new fields are optional:

```python
# This code works before and after
for error in response.json()["detail"]:
    print(error["type"], error["msg"])
```

### Step 2: Use New Fields (Optional)

To use the new enhanced fields:

```python
# Handle validation errors with enhanced context
response = client.post("/users", json={"email": "invalid"})

errors = response.json()["detail"]
for error in errors:
    # New: Get the field path
    field = error.get("field_path", "unknown")

    # New: Get example valid value
    example = error.get("example")

    # New: Get suggested correction
    suggestion = error.get("suggested_field")

    # New: Get expected type
    expected = error.get("expected_type")

    print(f"Error in '{field}': {error['msg']}")
    if example:
        print(f"  Example: {example}")
    if suggestion:
        print(f"  Did you mean '{suggestion}'?")
```

---

## New Features Explained

### 1. Field Path Context

The `field_path` shows the exact location of the error using dot notation:

- Simple: `"email"` → root field
- Nested: `"user.address.city"` → nested object
- Arrays: `"users[0].email"` → array item

### 2. Similar Field Suggestions

When you make a typo in a field name, you'll get a suggestion:

```json
{"emal": "test@example.com"}
```

Response:
```json
{
  "msg": "Field required",
  "field_path": "email",
  "suggested_field": "email"
}
```

### 3. Example Values

Each error includes an example of valid input:

| Type | Example |
|------|---------|
| Email | `"user@example.com"` |
| URL | `"https://example.com"` |
| Date | `"2024-01-01"` |
| Integer | `"42"` |
| Boolean | `"true"` |

---

## Configuration

### Disable Enhancements (Optional)

If you need the old behavior, you can override the exception handler:

```python
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def old_validation_handler(request: Request, exc: RequestValidationError):
    # Return original errors without enhancement
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )
```

---

## Common Error Types

| Error Type | Meaning | Solution |
|------------|---------|----------|
| missing | Required field not provided | Add the field |
| string_type | Expected string, got other type | Check the value |
| int_type | Expected integer | Provide a number |
| enum | Value not in allowed list | Use one of the allowed values |
| url_parsing | Invalid URL format | Use valid URL like `https://...` |

---

## Testing Your API

### Test a Simple Error

```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email": "not-an-email"}'
```

Expected response shows `field_path` and `example`.

### Test a Typo

```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"emal": "test@example.com"}'
```

Expected response shows `suggested_field: "email"`.

---

## Next Steps

1. **Update client code**: Use the new fields for better error messages
2. **Update documentation**: Inform API consumers about enhanced errors
3. **Monitor feedback**: Collect user feedback on improved error messages

---

## Support

- For issues: https://github.com/tiangolo/fastapi/issues
- For discussions: https://github.com/tiangolo/fastapi/discussions

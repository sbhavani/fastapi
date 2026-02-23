# Validation Error Contract

## Overview

This document defines the contract for enhanced validation error responses in FastAPI.

## HTTP Validation Error (422 Unprocessable Entity)

### Request

```http
POST /users HTTP/1.1
Content-Type: application/json

{
  "usernmae": "john",
  "age": "not-a-number"
}
```

### Response

```http
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json

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
    },
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

## WebSocket Validation Error

### Request

```javascript
// WebSocket message
{
  "usernmae": "john",
  "age": "not-a-number"
}
```

### Response

```http
// WebSocket close frame (1008 Policy Violation)
{
  "detail": [
    {
      "type": "unknown_field",
      "loc": ["ws", "message", "usernmae"],
      "msg": "Extra inputs are not permitted",
      "input": null,
      "field_path": "ws.message.usernmae",
      "expected_type": "object",
      "example": "Expected an object with fields: username, email, age",
      "suggestion": "Did you mean 'username'?"
    }
  ]
}
```

## Error Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `detail` | `array` | Array of validation errors |
| `detail[].type` | `string` | Pydantic error type identifier |
| `detail[].loc` | `array` | Location tuple (Pydantic native) |
| `detail[].msg` | `string` | Human-readable error message |
| `detail[].input` | `any` | The invalid input that was provided |
| `detail[].field_path` | `string` | **NEW** Dot-notation path to the field |
| `detail[].expected_type` | `string` | **NEW** Human-readable expected type |
| `detail[].example` | `string` | **NEW** Example of valid input |
| `detail[].suggestion` | `string\|null` | **NEW** Suggested correction for typos |

## Backwards Compatibility

- The original Pydantic error fields (`type`, `loc`, `msg`, `input`) are always present
- New enhancement fields are added alongside existing fields
- Consumers that only read `detail` will continue to work
- Consumers can opt-in to reading enhancement fields

## Error Types with Examples

### Type Error

**Request**: `{"age": "not-a-number"}`

**Response**:
```json
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
```

### Missing Field

**Request**: `{}` (when `username` is required)

**Response**:
```json
{
  "type": "missing",
  "loc": ["body", "username"],
  "msg": "Field required",
  "input": null,
  "field_path": "body.username",
  "expected_type": "string",
  "example": "Expected a string, e.g., 'john_doe'",
  "suggestion": null
}
```

### Typo/Similar Field

**Request**: `{"usernmae": "john"}`

**Response**:
```json
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
```

### Nested Field Error

**Request**: `{"user": {"profile": {"age": "invalid"}}}`

**Response**:
```json
{
  "type": "int_parsing",
  "loc": ["body", "user", "profile", "age"],
  "msg": "Input should be a valid integer",
  "input": "invalid",
  "field_path": "body.user.profile.age",
  "expected_type": "integer",
  "example": "Expected an integer, e.g., 25",
  "suggestion": null
}
```

### List Item Error

**Request**: `{"items": [{"name": 123}]}` (name should be string)

**Response**:
```json
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
```

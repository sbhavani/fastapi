# Specification: Enhanced Validation Error Messages

## Feature Overview

**Feature Name**: Validation Error Message Improvements

**Feature Type**: Framework Enhancement

**Core Summary**: Extend FastAPI's validation error responses to include field path context, similar field name suggestions, and example corrections, making it easier for API consumers to understand and fix validation failures.

**Target Users**: API developers and consumers who receive validation errors when submitting invalid request data.

---

## Problem Statement

When FastAPI validation fails, the error messages often lack sufficient context for developers to quickly identify and fix the issue. Users receive generic "validation error" messages without:
- Clear indication of which exact field failed
- Suggestions for fixing common mistakes
- Example values showing valid input formats

This leads to frustration, increased debugging time, and poor developer experience when integrating with FastAPI APIs.

---

## User Scenarios & Testing

### Primary User Scenario: API Consumer Receives Validation Error

1. An API consumer submits a POST request with invalid data to a FastAPI endpoint
2. FastAPI validates the request body against the Pydantic model
3. The validation fails due to incorrect field type or value
4. The API consumer receives an enhanced error response with:
   - The exact field path where validation failed (e.g., "body.user.profile.age")
   - Suggestions for similar field names if a typo is detected (e.g., "Did you mean 'username' instead of 'usernmae'?")
   - Example values showing valid input format (e.g., "Expected an integer, e.g., 25")

### Secondary Scenario: WebSocket Validation

1. A WebSocket client sends a message with invalid data
2. FastAPI validates the message against the expected schema
3. The client receives enhanced validation error with field path context

### Testing Approach

- Unit tests verify enhanced error structure
- Integration tests verify error responses in actual API calls
- Performance tests ensure minimal overhead from enhancement logic

---

## Functional Requirements

### FR-1: Field Path Context

The validation error response MUST include the complete path to the failed field in dot notation.

**Acceptance Criteria**:
- For nested models, the path shows the full location (e.g., `body.user.profile.age`)
- For list items, the path includes the index (e.g., `body.items[2].name`)
- The field path is present in both RequestValidationError and WebSocketRequestValidationError

### FR-2: Similar Field Name Suggestions

When a validation error occurs, the system SHOULD detect if the provided field name is similar to an existing field name and suggest the correct one.

**Acceptance Criteria**:
- Uses string similarity detection to identify potential typos
- Only suggests fields from the same model/schema
- Suggestion is included in the error detail when similarity score exceeds threshold

### FR-3: Example Value Display

The validation error response MUST include an example of valid input for the failed field.

**Acceptance Criteria**:
- Shows expected type (e.g., "Expected an integer")
- Provides example value from the field's type or default
- Examples are derived from the Pydantic model field definition

### FR-4: Backwards Compatibility

The enhanced error format MUST be backwards compatible with existing error handling.

**Acceptance Criteria**:
- Existing error response structure is preserved
- New enhancement fields are added without breaking existing consumers
- Error responses remain valid JSON

### FR-5: Performance

The error enhancement MUST NOT significantly impact request processing performance.

**Acceptance Criteria**:
- Error enhancement adds less than 5ms to response time
- Similar field name calculation is optimized for common cases

---

## Key Entities

### ValidationErrorEnhancement

- **field_path**: String representing the location of the failed field
- **suggestion**: Optional string with similar field name suggestion
- **example**: Example value showing valid input
- **expected_type**: String describing the expected data type

### ErrorResponse

- **detail**: Original error detail (preserved for backwards compatibility)
- **enhanced_detail**: New structure with field_path, suggestion, and example fields

---

## Success Criteria

1. **Developer Satisfaction**: API consumers can resolve validation errors 50% faster based on improved error messages (measured through reduced support tickets and debugging time)

2. **Error Clarity**: 95% of validation errors include field path context

3. **Suggestion Accuracy**: When suggestions are provided, at least 90% are accurate (correct field name)

4. **Performance**: Error enhancement adds minimal latency (<5ms average)

5. **Compatibility**: All existing FastAPI applications continue to work without modification

---

## Assumptions

- Pydantic is used as the validation library and its error structures are stable
- The enhancement applies to RequestValidationError and WebSocketRequestValidationError
- Similar field name detection uses a threshold to determine likely typos
- Example values are derived from Pydantic field types (int, str, float, bool, etc.)
- The feature applies to JSON request bodies; form data and file uploads are out of scope for this initial version

# Validation Error Suggestions

**Feature Name**: Validation Error Suggestions
**Feature Branch**: 4-validation-error-suggestions
**Created**: 2026-02-23
**Status**: Draft

## Overview

Extend FastAPI's ValidationError to provide more informative and actionable error messages. When request data fails validation, the error response should include field path context (showing the exact location in the data structure where the error occurred), suggest similar field names if a typo is likely, and provide example corrections showing valid value formats.

## Problem Statement

Currently, FastAPI's validation errors provide minimal information about why a field failed validation. Developers and API consumers often struggle to understand:
- Where exactly in a nested data structure the error occurred
- What valid values look like for the failing field
- Whether a field name might be a typo of an existing field

This leads to increased debugging time and poorer developer experience when integrating with FastAPI APIs.

## User Scenarios & Testing

### Scenario 1: Simple Field Validation
A developer submits a POST request with an invalid email format to a user registration endpoint. The error response should:
- Show the field path (e.g., "email")
- Display the invalid value that was provided
- Show an example of a valid email format

### Scenario 2: Nested Object Validation
A developer submits a request with invalid data in a deeply nested object. The error response should:
- Display the full field path (e.g., "user.address.zip_code")
- Show context about which parent object contains the error
- Provide the hierarchical path to help locate the issue

### Scenario 3: Typos in Field Names
A developer submits a request with a field name that is close to (but not exactly) a valid field name. The error response should:
- Identify that the field name may be a typo
- Suggest the correct field name (e.g., "Did you mean 'email_address'?")

### Scenario 4: Missing Required Field
A developer omits a required field from the request. The error response should:
- Clearly indicate which field is missing
- Show the field path in the context of the parent object
- Provide an example of what the complete valid structure looks like

### Scenario 5: Type Mismatch
A developer provides a string where an integer is expected. The error response should:
- Show the field path
- Indicate the expected type
- Provide an example of a valid value for that field

## Functional Requirements

### FR-01: Field Path Context
The validation error must include the complete path to the field that failed validation. For nested objects, the path should use dot notation (e.g., "user.profile.age").

**Acceptance Criteria**:
- [ ] Error response includes `field_path` property with dot-notation path
- [ ] Nested array items show index position (e.g., "users[0].email")
- [ ] Path is accurate for all nesting levels

### FR-02: Similar Field Name Suggestions
When a field name in the request does not exactly match any valid field but is structurally similar to one, the error should suggest the correct field name.

**Acceptance Criteria**:
- [ ] String similarity comparison identifies potential typos
- [ ] Suggestion appears when similarity score exceeds threshold
- [ ] Suggestions are only shown for high-confidence matches

### FR-03: Example Corrections
Each validation error should include an example of a valid value for the field that failed validation.

**Acceptance Criteria**:
- [ ] Error includes `example` property showing valid format
- [ ] Examples are context-aware based on field type and constraints
- [ ] Examples are provided for common types (email, date, enum, etc.)

### FR-04: Error Detail Structure
The extended error detail must maintain backward compatibility while adding new helpful properties.

**Acceptance Criteria**:
- [ ] Original error message preserved
- [ ] New fields are optional to maintain compatibility
- [ ] Error detail works with existing OpenAPI schema generation

### FR-05: Performance Impact
The enhanced error generation must not significantly impact request processing performance.

**Acceptance Criteria**:
- [ ] Error generation adds minimal overhead for typical cases
- [ ] Similar field matching is efficient for schemas with many fields

## Success Criteria

### SC-01: Developer Satisfaction
Developers using FastAPI report improved ability to debug validation errors. Measured through:
- 50% reduction in time spent debugging validation issues
- Improved clarity scores in developer surveys

### SC-02: Error Resolution Rate
API consumers can resolve validation errors without needing to consult external documentation more often.
- 70% of validation errors are self-resolvable using only the error message and suggestions

### SC-03: Backward Compatibility
Existing applications that handle ValidationError continue to function without modification.
- 100% backward compatibility for existing error handling code
- No breaking changes to error response structure

### SC-04: Performance
The enhanced validation does not measurably impact API response times.
- Error generation completes instantly for users (minimal perceived delay)
- No impact on requests without validation errors

## Key Entities

### ValidationError
- **Current State**: Contains message, type, and location information
- **Enhanced State**: Adds field_path, suggested_field, example, expected_type properties

### FieldSchema
- **Purpose**: Stores schema information for each field to generate examples
- **Properties**: name, type, format, constraints, example_value

### ErrorContext
- **Purpose**: Accumulates context during validation traversal
- **Properties**: current_path, parent_objects, field_hierarchy

## Assumptions

1. **Validation Library Integration**: This feature will leverage the underlying validation library's existing validation infrastructure.

2. **Schema Compatibility**: Examples and type information will be derived from schema definitions that FastAPI already generates.

3. **Threshold Tuning**: The similarity threshold for field name suggestions will be tuned based on testing with real-world schemas.

4. **Nested Arrays**: Field path notation for arrays will follow convention: `field[index].subfield`

5. **Optional Enhancement**: The new error fields will be optional to ensure backward compatibility with existing error handling.

## Dependencies

- FastAPI's existing validation error handling
- Underlying data validation library
- Schema generation for example extraction
- String similarity comparison for field name matching

## Out of Scope

- Changes to non-validation error handling (e.g., HTTP errors)
- Client-side error message customization
- Error message translation/internationalization
- Validation error logging enhancements
- Bulk error processing optimization

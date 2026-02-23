"""
Error Enhancement Module for FastAPI Validation Errors.

This module provides utilities to enhance validation error messages with:
- Field path context (dot notation)
- Similar field name suggestions (typo detection)
- Example corrections
- Expected type information
"""

from difflib import SequenceMatcher
from typing import Any


# Configuration for similarity matching
SIMILARITY_THRESHOLD = 0.6

# Format-based example values
FORMAT_EXAMPLES: dict[str, str] = {
    "email": "user@example.com",
    "uri": "https://example.com",
    "url": "https://example.com",
    "date": "2024-01-01",
    "date-time": "2024-01-01T12:00:00Z",
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "ipv4": "192.168.1.1",
    "ipv6": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
    "hostname": "example.com",
    "regex": "^[a-zA-Z]+$",
    "json-pointer": "/example/path",
    "json-ref": "#/components/schemas/Example",
}

# Type-based default examples
TYPE_EXAMPLES: dict[str, str] = {
    "string": "string",
    "integer": 0,
    "int": 0,
    "number": 0.0,
    "float": 0.0,
    "boolean": True,
    "bool": True,
    "array": [],
    "object": {},
    "null": None,
}

# Map Pydantic error types to JSON Schema types for example inference
ERROR_TYPE_TO_SCHEMA_TYPE: dict[str, str] = {
    "int_parsing": "integer",
    "int_parsing_failed": "integer",
    "float_parsing": "number",
    "float_parsing_failed": "number",
    "bool_parsing": "boolean",
    "bool_parsing_failed": "boolean",
    "string_type": "string",
    "string_too_short": "string",
    "string_too_long": "string",
    "string_pattern_mismatch": "string",
    "enum": "string",
    "list_type": "array",
    "dict_type": "object",
    "json_type": "object",
    "uuid_type": "string",
    "uuid_parsing": "string",
    "date_time_parsing": "string",
    "date_parsing": "string",
    "time_parsing": "string",
    "email_parsing": "string",
    "email_parsing_failed": "string",
    "uri_type": "string",
    "uri_parsing_failed": "string",
    "url_parsing": "string",
    "url_parsing_failed": "string",
    "missing": "string",
    "none_type": "null",
}


def infer_type_from_error(error_type: str) -> str | None:
    """
    Infer JSON Schema type from Pydantic error type.

    Args:
        error_type: Pydantic error type (e.g., "int_parsing", "string_type")

    Returns:
        JSON Schema type or None if cannot infer
    """
    return ERROR_TYPE_TO_SCHEMA_TYPE.get(error_type)


def build_field_path(loc: tuple[str | int, ...]) -> str | None:
    """
    Build a dot-notation field path from a location tuple.

    Args:
        loc: Location tuple from Pydantic (e.g., ("body", "user", "email"))

    Returns:
        Dot-notation path string (e.g., "user.email") or None if empty

    Examples:
        >>> build_field_path(("body", "email"))
        'email'
        >>> build_field_path(("body", "user", "address", "zip_code"))
        'user.address.zip_code'
        >>> build_field_path(("body", "users", 0, "email"))
        'users[0].email'
    """
    if not loc:
        return None

    # Skip "body" prefix if present (it's an implementation detail)
    path_parts = list(loc)
    if path_parts and path_parts[0] == "body":
        path_parts = path_parts[1:]

    if not path_parts:
        return None

    # Build the path string with array index notation
    result_parts: list[str] = []
    for part in path_parts:
        if isinstance(part, int):
            # Array index - add as [index]
            if result_parts:
                result_parts[-1] = f"{result_parts[-1]}[{part}]"
            else:
                result_parts.append(f"[{part}]")
        else:
            # Regular field name
            if result_parts:
                result_parts.append(str(part))
            else:
                result_parts.append(str(part))

    return ".".join(result_parts)


def get_similarity_score(a: str, b: str) -> float:
    """
    Calculate similarity score between two strings.

    Uses normalized similarity (0.0 to 1.0) with case-insensitive comparison
    and normalization of underscores/hyphens.

    Args:
        a: First string
        b: Second string

    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Normalize strings: lowercase, remove underscores and hyphens
    def normalize(s: str) -> str:
        return s.lower().replace("_", "").replace("-", "")

    norm_a = normalize(a)
    norm_b = normalize(b)

    if not norm_a or not norm_b:
        return 0.0

    return SequenceMatcher(None, norm_a, norm_b).ratio()


def find_similar_field(
    unknown_field: str, valid_fields: list[str], threshold: float = SIMILARITY_THRESHOLD
) -> str | None:
    """
    Find a similar field name from a list of valid fields.

    Args:
        unknown_field: The field name that wasn't found
        valid_fields: List of valid field names to match against
        threshold: Minimum similarity score (default 0.6)

    Returns:
        Suggested field name or None if no match above threshold
    """
    best_match: str | None = None
    best_score = 0.0

    for field in valid_fields:
        score = get_similarity_score(unknown_field, field)
        if score > best_score and score >= threshold:
            best_score = score
            best_match = field

    return best_match


def generate_example_from_format(format_str: str | None) -> str | None:
    """
    Generate an example value from a JSON Schema format.

    Args:
        format_str: JSON Schema format (e.g., "email", "uri", "date")

    Returns:
        Example string or None if format not recognized
    """
    if not format_str:
        return None

    return FORMAT_EXAMPLES.get(format_str.lower())


def generate_example_from_type(type_str: str | None) -> Any:
    """
    Generate an example value from a JSON Schema type.

    Args:
        type_str: JSON Schema type (e.g., "string", "integer")

    Returns:
        Example value based on type, or None if not available
    """
    if not type_str:
        return None

    type_str = type_str.lower()
    if type_str in TYPE_EXAMPLES:
        return TYPE_EXAMPLES[type_str]

    return None


def generate_expected_type(type_str: str | None, format_str: str | None) -> str | None:
    """
    Generate a human-readable expected type description.

    Args:
        type_str: JSON Schema type
        format_str: JSON Schema format

    Returns:
        Human-readable type description or None if not available
    """
    if not type_str:
        return None

    type_str = type_str.lower()

    if format_str:
        format_str = format_str.lower()
        return f"{type_str} ({format_str})"

    return type_str


def enhance_error(
    error: dict[str, Any],
    valid_fields: list[str] | None = None,
    field_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Enhance a single validation error with additional context.

    Args:
        error: Raw validation error dictionary from Pydantic
        valid_fields: List of valid field names for typo detection
        field_schema: Schema information for the field (optional)

    Returns:
        Enhanced error dictionary with new fields
    """
    # Copy original error to preserve all fields
    enhanced = dict(error)

    # Add field_path
    loc = error.get("loc", ())
    field_path = build_field_path(loc)
    enhanced["field_path"] = field_path

    # Get the actual field name from location (last string element)
    field_name: str | None = None
    for part in reversed(loc):
        if isinstance(part, str):
            field_name = part
            break

    # Add suggested_field if there's a valid field list and we have a field name
    if valid_fields and field_name:
        # Check if this might be a typo (error type is 'missing' and field not in valid)
        error_type = error.get("type", "")
        if error_type == "missing" and field_name not in valid_fields:
            suggested = find_similar_field(field_name, valid_fields)
            enhanced["suggested_field"] = suggested
        else:
            enhanced["suggested_field"] = None
    else:
        enhanced["suggested_field"] = None

    # Add example value
    example: Any = None
    type_str: str | None = None
    format_str: str | None = None

    # Try to get example from schema first
    if field_schema:
        example = field_schema.get("example")
        type_str = field_schema.get("type")
        format_str = field_schema.get("format")

    # If no schema example, try format-based
    if example is None:
        example = generate_example_from_format(format_str)

    # If still no example, try type-based (from schema or inferred from error)
    if example is None:
        # Try to infer type from Pydantic error type if not from schema
        if not type_str:
            pydantic_error_type = error.get("type", "")
            type_str = infer_type_from_error(pydantic_error_type)
        example = generate_example_from_type(type_str)

    enhanced["example"] = example

    # Add expected_type (from schema or inferred from error)
    if not type_str:
        pydantic_error_type = error.get("type", "")
        type_str = infer_type_from_error(pydantic_error_type)

    enhanced["expected_type"] = generate_expected_type(type_str, format_str)

    return enhanced


def enhance_errors(
    errors: list[dict[str, Any]],
    valid_fields: list[str] | None = None,
    field_schemas: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Enhance a list of validation errors with additional context.

    Args:
        errors: List of raw validation error dictionaries from Pydantic
        valid_fields: List of valid field names for typo detection
        field_schemas: Dictionary mapping field names to their schemas

    Returns:
        List of enhanced error dictionaries
    """
    enhanced_errors: list[dict[str, Any]] = []

    for error in errors:
        # Extract the field name from location to look up schema
        field_name: str | None = None
        loc = error.get("loc", ())
        for part in reversed(loc):
            if isinstance(part, str):
                field_name = part
                break

        # Get schema for this field if available
        field_schema = None
        if field_schemas and field_name:
            field_schema = field_schemas.get(field_name)

        enhanced = enhance_error(error, valid_fields, field_schema)
        enhanced_errors.append(enhanced)

    return enhanced_errors

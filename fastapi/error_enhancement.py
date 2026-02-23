"""
Error Enhancement Module for FastAPI Validation Errors

This module provides functions to enhance validation error responses with:
- Field path context (dot notation)
- Similar field name suggestions (typo detection)
- Example values showing valid input
- Expected type information
"""
from __future__ import annotations

from dataclasses import dataclass, field
from difflib import get_close_matches
from typing import Any

from fastapi.encoders import jsonable_encoder


@dataclass
class ErrorEnhancementConfig:
    """Configuration for error enhancement behavior."""

    enable_suggestions: bool = True
    enable_examples: bool = True
    suggestion_threshold: int = 3  # Max edit distance for suggestions
    max_path_length: int = 100


def build_field_path(loc: tuple[str, ...], prefix: str = "body") -> str:
    """
    Build a dot-notation field path from Pydantic's location tuple.

    Args:
        loc: Pydantic error location tuple (e.g., ("body", "user", "profile", "age"))
              Note: Pydantic includes "body" in the loc tuple for body validation
        prefix: Prefix to use (e.g., "body" for HTTP, "ws" for WebSocket)

    Returns:
        Dot-notation path (e.g., "body.user.profile.age")
    """
    if not loc:
        return prefix

    # Pydantic includes "body" in the loc for body validation
    # If first element matches our prefix, skip it (already in loc)
    if loc and loc[0] == prefix:
        remaining_loc = loc[1:]
    else:
        remaining_loc = loc

    # Build result
    result = prefix

    # Add remaining loc items
    for item in remaining_loc:
        if isinstance(item, int):
            result += f"[{item}]"
        else:
            result += f".{str(item)}"

    # Truncate if too long
    if len(result) > 100:
        result = result[:97] + "..."

    return result


def find_similar_field_name(
    field_name: str,
    valid_fields: list[str],
    threshold: int = 3,
) -> str | None:
    """
    Find a similar field name that might be a typo.

    Args:
        field_name: The field name that caused the error
        valid_fields: List of valid field names to match against
        threshold: Maximum edit distance to consider as similar

    Returns:
        Suggested field name if similar match found, None otherwise
    """
    if not field_name or not valid_fields:
        return None

    # Use difflib's get_close_matches for similarity detection
    matches = get_close_matches(field_name, valid_fields, n=1, cutoff=0.6)

    if matches:
        return matches[0]

    # Fallback: simple edit distance calculation for better control
    for valid in valid_fields:
        if abs(len(field_name) - len(valid)) > threshold:
            continue
        distance = _edit_distance(field_name, valid)
        if distance <= threshold:
            return valid

    return None


def _edit_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _edit_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


# Type to example mapping
TYPE_EXAMPLES: dict[str, str] = {
    "string": "e.g., 'string'",
    "str": "e.g., 'string'",
    "integer": "e.g., 42",
    "int": "e.g., 42",
    "number": "e.g., 3.14",
    "float": "e.g., 3.14",
    "boolean": "e.g., true",
    "bool": "e.g., true",
    "array": "e.g., []",
    "list": "e.g., []",
    "object": "e.g., {}",
    "dict": "e.g., {}",
    "uuid": "e.g., 'a3fcd804-2c2b-4d84-9a4c-5e6f7g8h9i0j'",
    "email": "e.g., 'user@example.com'",
    "uri": "e.g., 'https://example.com'",
    "url": "e.g., 'https://example.com'",
    "date": "e.g., '2024-01-01'",
    "datetime": "e.g., '2024-01-01T00:00:00Z'",
    "time": "e.g., '12:00:00'",
    "bytes": "e.g., b'bytes'",
    "bytesize": "e.g., 1024",
}


def get_expected_type(ctx: dict[str, Any] | None) -> str:
    """
    Get human-readable expected type from Pydantic error context.

    Args:
        ctx: Pydantic error context dict (may contain expected_type)

    Returns:
        Human-readable type string
    """
    if ctx is None:
        return "unknown"

    # Check for expected_type in context
    if "expected_type" in ctx:
        expected = ctx["expected_type"]
        if isinstance(expected, str):
            return expected

    # Check for union types
    if "union" in ctx:
        return "union"

    return "value"


def get_example_for_type(
    expected_type: str,
    default_value: Any = None,
    enum_values: list[Any] | None = None,
) -> str | None:
    """
    Generate an example string for the expected type.

    Args:
        expected_type: Human-readable type name
        default_value: Optional default value from the field
        enum_values: Optional list of enum values

    Returns:
        Example string or None
    """
    # If enum values exist, use first as example
    if enum_values:
        example_val = enum_values[0]
        return f"Must be one of: {', '.join(repr(v) for v in enum_values[:3])}"

    # If default value exists, use it
    if default_value is not None:
        return f"e.g., {repr(default_value)}"

    # Use type-based example
    return TYPE_EXAMPLES.get(expected_type.lower(), f"Expected {expected_type}")


def get_valid_fields_from_model(model: Any) -> list[str]:
    """
    Extract valid field names from a Pydantic model.

    Args:
        model: Pydantic model class

    Returns:
        List of field names
    """
    try:
        # Pydantic v2
        if hasattr(model, "model_fields"):
            return list(model.model_fields.keys())
        # Fallback for older versions
        if hasattr(model, "__fields__"):
            return list(model.__fields__.keys())
    except Exception:
        pass
    return []


def enhance_single_error(
    error: dict[str, Any],
    model: Any = None,
    config: ErrorEnhancementConfig | None = None,
    prefix: str = "body",
) -> dict[str, Any]:
    """
    Enhance a single Pydantic validation error with additional information.

    Args:
        error: Original Pydantic error dict
        model: Optional Pydantic model for field lookup
        config: Enhancement configuration
        prefix: Path prefix (e.g., "body" or "ws.message")

    Returns:
        Enhanced error dict
    """
    if config is None:
        config = ErrorEnhancementConfig()

    enhanced = dict(error)

    # Add field_path
    loc = error.get("loc", ())
    enhanced["field_path"] = build_field_path(loc, prefix=prefix)

    # Add expected_type
    ctx = error.get("ctx")
    expected_type = get_expected_type(ctx)
    enhanced["expected_type"] = expected_type

    # Add example
    if config.enable_examples:
        example = get_example_for_type(expected_type)
        enhanced["example"] = example
    else:
        enhanced["example"] = None

    # Add suggestion for typos
    if config.enable_suggestions and model is not None:
        # Get the field name from error location
        if loc and isinstance(loc[-1], str):
            error_field = loc[-1]
            valid_fields = get_valid_fields_from_model(model)

            if valid_fields:
                similar = find_similar_field_name(
                    error_field,
                    valid_fields,
                    threshold=config.suggestion_threshold,
                )
                if similar:
                    enhanced["suggestion"] = f"Did you mean '{similar}'?"
                else:
                    enhanced["suggestion"] = None
        else:
            enhanced["suggestion"] = None
    else:
        enhanced["suggestion"] = None

    return enhanced


def enhance_errors(
    errors: list[dict[str, Any]],
    model: Any = None,
    config: ErrorEnhancementConfig | None = None,
    prefix: str = "body",
) -> list[dict[str, Any]]:
    """
    Enhance a list of Pydantic validation errors.

    Args:
        errors: List of original Pydantic error dicts
        model: Optional Pydantic model for field lookup
        config: Enhancement configuration
        prefix: Path prefix (e.g., "body" or "ws.message")

    Returns:
        List of enhanced error dicts
    """
    return [
        enhance_single_error(error, model=model, config=config, prefix=prefix)
        for error in errors
    ]


def get_model_from_request(request: Any) -> Any | None:
    """
    Attempt to extract the Pydantic model from a request.

    This is a best-effort extraction - not all requests will have
    an associated model.

    Args:
        request: Starlette request object

    Returns:
        Pydantic model class if found, None otherwise
    """
    # Try to get body model from request state (set during routing)
    if hasattr(request.state, "_body_model"):
        return request.state._body_model

    # Try to get from body field
    if hasattr(request, "body") and hasattr(request.body, "_field"):
        return getattr(request.body._field, "type_", None)

    return None

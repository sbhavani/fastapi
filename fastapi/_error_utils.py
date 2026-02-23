"""Utilities for enhancing validation error messages with suggestions."""

from __future__ import annotations

import difflib
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi._compat import ModelField


def _get_similar_fields(
    field_name: str, available_fields: Sequence[str], max_suggestions: int = 3
) -> list[str]:
    """Find similar field names using sequence matching.

    Returns a list of similar field names sorted by similarity score.
    """
    if not available_fields:
        return []

    # Get close matches using difflib
    matches = difflib.get_close_matches(
        field_name, available_fields, n=max_suggestions, cutoff=0.6
    )

    return matches


def _get_field_path_str(loc: tuple[str | int, ...]) -> str:
    """Convert a location tuple to a human-readable path string.

    Example: ("body", "user", "name") -> "body -> user -> name"
    """
    if not loc:
        return ""

    path_parts: list[str] = []
    for part in loc:
        if isinstance(part, int):
            path_parts.append(f"[{part}]")
        else:
            if path_parts:
                path_parts.append(" -> ")
            path_parts.append(str(part))

    return "".join(path_parts)


def _get_type_name(type_hint: Any) -> str:
    """Get a human-readable type name from a type hint."""
    from typing import get_origin, get_args

    origin = get_origin(type_hint)

    if origin is list:
        args = get_args(type_hint)
        if args:
            item_type = _get_type_name(args[0])
            return f"list[{item_type}]"
        return "list"

    if origin is dict:
        args = get_args(type_hint)
        if len(args) == 2:
            key_type = _get_type_name(args[0])
            value_type = _get_type_name(args[1])
            return f"dict[{key_type}, {value_type}]"
        return "dict"

    if origin is set:
        args = get_args(type_hint)
        if args:
            item_type = _get_type_name(args[0])
            return f"set[{item_type}]"
        return "set"

    if origin is tuple:
        args = get_args(type_hint)
        if args:
            item_types = [_get_type_name(arg) for arg in args]
            return f"tuple[{', '.join(item_types)}]"
        return "tuple"

    if origin is frozenset:
        args = get_args(type_hint)
        if args:
            item_type = _get_type_name(args[0])
            return f"frozenset[{item_type}]"
        return "frozenset"

    # Handle Union types
    if origin is type(None):
        return "None"

    if hasattr(type_hint, "__name__"):
        return type_hint.__name__

    return str(type_hint)


def _get_example_for_field(field: ModelField) -> Any:
    """Get an example value for a field based on its schema."""
    from fastapi._compat import Undefined

    # Try to get the default value first
    default = field.get_default()
    if default is not Undefined:
        return default

    # Try to get from field_info examples
    examples = getattr(field.field_info, "examples", None)
    if examples:
        return examples[0] if examples else None

    # Try to generate from the type adapter schema
    try:
        schema = field._type_adapter.json_schema()
        if "example" in schema:
            return schema["example"]
        if "default" in schema:
            return schema["default"]
    except Exception:
        pass

    return None


def _get_input_type_name(input_value: Any) -> str:
    """Get a human-readable type name from an input value."""
    if input_value is None:
        return "null"

    type_name = type(input_value).__name__

    # Handle common types more readably
    if isinstance(input_value, dict):
        return "object"
    elif isinstance(input_value, list):
        item_types = set()
        for item in input_value[:3]:  # Check first few items
            item_types.add(type(item).__name__)
        if len(item_types) == 1:
            return f"list[{list(item_types)[0]}]"
        return "list"
    elif isinstance(input_value, str):
        return "string"
    elif isinstance(input_value, bool):
        return "boolean"
    elif isinstance(input_value, int):
        return "integer"
    elif isinstance(input_value, float):
        return "float"

    return type_name


def _generate_suggestion_for_error(
    error: dict[str, Any],
    available_fields: Sequence[str] | None = None,
) -> str | None:
    """Generate a suggestion message for a validation error.

    Args:
        error: The validation error dictionary
        available_fields: Available field names for suggestion

    Returns:
        A suggestion string or None if no suggestion can be made
    """
    error_type = error.get("type", "")
    loc = error.get("loc", ())

    # Get the field name from location
    field_name = None
    for part in reversed(loc):
        if isinstance(part, str):
            field_name = part
            break

    if not field_name or not available_fields:
        return None

    # For missing fields, suggest similar fields
    if error_type == "missing":
        similar = _get_similar_fields(field_name, available_fields)
        if similar:
            return f"Did you mean: {', '.join(similar)}?"

    # For extra fields (fields not in the model)
    if error_type == "unknown":
        similar = _get_similar_fields(field_name, available_fields)
        if similar:
            return f"Did you mean: {', '.join(similar)}?"

    return None


def _generate_example_correction(
    error: dict[str, Any],
    field: ModelField | None = None,
) -> Any | None:
    """Generate an example correction for a validation error.

    Args:
        error: The validation error dictionary
        field: The model field (if available)

    Returns:
        An example correction value or None
    """
    error_type = error.get("type", "")

    # For missing fields, try to get the default or example
    if error_type == "missing" and field:
        return _get_example_for_field(field)

    # For type errors, try to provide the expected type example
    if error_type in ("type_error", "type_error.str", "type_error.int", "type_error.float",
                      "type_error.bool", "type_error.list", "type_error.dict"):
        if field:
            example = _get_example_for_field(field)
            if example is not None:
                return example

        # Try to get from ctx
        ctx = error.get("ctx", {})
        if "expected" in ctx:
            return ctx["expected"]

    return None


def _get_field_from_loc(
    loc: tuple[str | int, ...],
    model_fields: dict[str, ModelField],
) -> ModelField | None:
    """Get a model field from a location tuple.

    This attempts to find the field at the given location.
    """
    if not loc:
        return None

    # Try to find the field by the last string part of the location
    for part in reversed(loc):
        if isinstance(part, str) and part in model_fields:
            return model_fields[part]

    return None


def _extract_field_names_from_errors(
    errors: Sequence[dict[str, Any]],
) -> set[str]:
    """Extract all field names mentioned in error locations.

    This parses error locations to find all valid field names.
    """
    field_names: set[str] = set()

    for error in errors:
        loc = error.get("loc", ())
        for part in loc:
            if isinstance(part, str):
                field_names.add(part)

    return field_names


def enhance_validation_error(
    error: dict[str, Any],
    *,
    available_fields: Sequence[str] | None = None,
    model_fields: dict[str, ModelField] | None = None,
    _available_fields_provided: bool = True,
) -> dict[str, Any]:
    """Enhance a single validation error with additional context and suggestions.

    Args:
        error: The original validation error dictionary
        available_fields: Available field names for suggestion
        model_fields: Mapping of field names to ModelField objects
        _available_fields_provided: Whether available_fields was explicitly provided

    Returns:
        Enhanced error dictionary with additional fields
    """
    enhanced = dict(error)

    # Add field path context
    loc = error.get("loc", ())
    if loc:
        enhanced["path"] = _get_field_path_str(loc)

    # Add suggestion for similar field names
    # Only add suggestions if available_fields was explicitly provided
    if available_fields and _available_fields_provided:
        suggestion = _generate_suggestion_for_error(error, available_fields)
        if suggestion:
            enhanced["suggestion"] = suggestion

    # Add example correction
    if model_fields:
        field = _get_field_from_loc(loc, model_fields)
        if field:
            example = _generate_example_correction(error, field)
            if example is not None:
                enhanced["example"] = example

    return enhanced


def enhance_validation_errors(
    errors: Sequence[dict[str, Any]],
    *,
    available_fields: Sequence[str] | None = None,
    model_fields: dict[str, ModelField] | None = None,
) -> list[dict[str, Any]]:
    """Enhance a list of validation errors with additional context and suggestions.

    Args:
        errors: List of validation error dictionaries
        available_fields: Available field names for suggestion
        model_fields: Mapping of field names to ModelField objects

    Returns:
        List of enhanced error dictionaries
    """
    # Track whether available_fields was explicitly provided
    available_fields_provided = available_fields is not None

    # If no available_fields provided, try to extract from errors
    if not available_fields:
        available_fields = _extract_field_names_from_errors(errors)

    return [
        enhance_validation_error(
            error,
            available_fields=available_fields,
            model_fields=model_fields,
            _available_fields_provided=available_fields_provided,
        )
        for error in errors
    ]

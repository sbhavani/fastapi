from typing import Any


def merge_openapi_schemas(*schemas: dict[str, Any]) -> dict[str, Any]:
    """Deep merge multiple OpenAPI schema dictionaries.

    Later schemas take precedence for conflicting keys.
    Supports merging: paths, components, security, tags, servers.

    Args:
        *schemas: Variable number of OpenAPI schema dictionaries.

    Returns:
        A merged OpenAPI schema dictionary.
    """
    if not schemas:
        return {}

    result: dict[str, Any] = {}

    for schema in schemas:
        if not schema:
            continue
        result = _deep_merge(result, schema)

    return result


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries.

    Args:
        base: The base dictionary.
        override: The dictionary to merge in (takes precedence).

    Returns:
        The merged dictionary.
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        elif key in result and isinstance(result[key], list) and isinstance(value, list):
            # For lists, we concatenate and deduplicate for certain types
            result[key] = _merge_lists(result[key], value, key)
        else:
            result[key] = value

    return result


def _merge_lists(base: list[Any], override: list[Any], key: str) -> list[Any]:
    """Merge two lists based on the key context.

    For some OpenAPI keys like 'security', we want to merge (OR behavior).
    For others like 'paths', we want deep merge (handled elsewhere).

    Args:
        base: The base list.
        override: The list to merge in.
        key: The key this list belongs to.

    Returns:
        The merged list.
    """
    # For security, we want to merge (plugins can add additional security requirements)
    if key == "security":
        # Combine all security requirements
        return base + override

    # For tags and servers, we concatenate
    if key in ("tags", "servers"):
        return base + override

    # Default: override replaces base
    return override


def get_openapi_contribution(plugin_schema: dict[str, Any] | None) -> dict[str, Any]:
    """Validate and normalize a plugin's OpenAPI contribution.

    Args:
        plugin_schema: The raw schema from a plugin.

    Returns:
        A normalized schema dictionary, or empty dict if None.
    """
    if plugin_schema is None:
        return {}

    if not isinstance(plugin_schema, dict):
        return {}

    # Ensure only valid OpenAPI top-level keys
    valid_keys = {"openapi", "info", "servers", "paths", "components", "security", "tags", "externalDocs"}
    return {k: v for k, v in plugin_schema.items() if k in valid_keys}

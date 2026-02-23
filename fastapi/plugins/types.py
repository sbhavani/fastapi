"""Type definitions for the FastAPI plugin system."""

from typing import Any, TypedDict

from starlette.requests import Request
from starlette.responses import Response

__all__ = [
    "OpenAPISchema",
    "OpenAPIPaths",
    "OpenAPIComponents",
    "OpenAPISecurity",
    "OpenAPIServers",
    "OpenAPITags",
    "PluginOpenAPIContribution",
    "RequestHookReturn",
    "PluginInstance",
]


# Type alias for OpenAPI schema contributions
class OpenAPISchema(TypedDict, total=False):
    """Type definition for OpenAPI schema contributions from plugins.

    Plugins can contribute to these top-level OpenAPI keys.
    """
    openapi: str
    info: dict[str, Any]
    servers: list[dict[str, Any]]
    paths: dict[str, Any]
    components: dict[str, Any]
    security: list[dict[str, Any]]
    tags: list[dict[str, Any]]
    externalDocs: dict[str, Any]


# Type alias for OpenAPI paths contribution
OpenAPIPaths = dict[str, Any]

# Type alias for OpenAPI components contribution
OpenAPIComponents = dict[str, Any]

# Type alias for OpenAPI security contribution
OpenAPISecurity = list[dict[str, Any]]

# Type alias for OpenAPI servers contribution
OpenAPIServers = list[dict[str, Any]]

# Type alias for OpenAPI tags contribution
OpenAPITags = list[dict[str, Any]]


class PluginOpenAPIContribution(TypedDict, total=False):
    """Type definition for plugin OpenAPI contribution.

    This is the return type expected from a plugin's openapi_schema() method.
    """
    paths: dict[str, Any]
    components: dict[str, Any]
    security: list[dict[str, Any]]
    tags: list[dict[str, Any]]
    servers: list[dict[str, Any]]


# Type alias for request hook return value
# None means continue processing, Response means short-circuit
RequestHookReturn = Response | None


# Type alias for plugin instance
# Using Any since we use Protocol for structural typing at runtime
PluginInstance = Any

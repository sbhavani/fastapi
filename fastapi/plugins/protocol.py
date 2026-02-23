from typing import Any, Protocol, runtime_checkable

from starlette.requests import Request
from starlette.responses import Response


@runtime_checkable
class PluginProtocol(Protocol):
    """Protocol defining the plugin interface.

    All methods are optional - plugins can implement only the hooks they need.
    """

    async def on_startup(self) -> None:
        """Called once when the application starts."""
        ...

    async def on_shutdown(self) -> None:
        """Called once when the application stops."""
        ...

    async def before_request(self, request: Request) -> Response | None:
        """Called before each request.

        Args:
            request: The incoming request.

        Returns:
            None to continue processing, or a Response to short-circuit the request.
        """
        ...

    async def after_request(
        self, request: Request, response: Response
    ) -> Response:
        """Called after each request.

        Args:
            request: The incoming request.
            response: The generated response.

        Returns:
            The response (potentially modified).
        """
        ...

    def openapi_schema(self) -> dict[str, Any] | None:
        """Return OpenAPI schema contributions.

        Returns:
            A dictionary with OpenAPI schema fragments (paths, components, etc.)
            or None if the plugin doesn't contribute to OpenAPI.
        """
        ...

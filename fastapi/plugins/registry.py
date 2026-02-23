import logging
from typing import Any

from starlette.requests import Request
from starlette.responses import Response

from fastapi.plugins.protocol import PluginProtocol
from fastapi.plugins.utils import get_openapi_contribution, merge_openapi_schemas

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Manages registered plugins and their lifecycle.

    This class coordinates plugin lifecycle hooks and aggregates
    OpenAPI schema contributions from all registered plugins.
    """

    def __init__(self) -> None:
        self._plugins: list[PluginProtocol] = []

    def add(self, plugin: PluginProtocol) -> None:
        """Register a plugin.

        Args:
            plugin: The plugin instance to register.
        """
        self._plugins.append(plugin)
        logger.debug(f"Registered plugin: {plugin.__class__.__name__}")

    def __iter__(self):
        """Iterate over registered plugins."""
        return iter(self._plugins)

    def __len__(self) -> int:
        """Return the number of registered plugins."""
        return len(self._plugins)

    async def on_startup(self) -> None:
        """Call on_startup for all registered plugins.

        Plugins are called in registration order (FIFO).
        Errors are logged and do not prevent other plugins from running.
        """
        for plugin in self._plugins:
            try:
                if hasattr(plugin, "on_startup"):
                    await plugin.on_startup()
            except Exception as e:
                logger.error(
                    f"Plugin {plugin.__class__.__name__} startup error: {e}",
                    exc_info=True,
                )

    async def on_shutdown(self) -> None:
        """Call on_shutdown for all registered plugins.

        Plugins are called in reverse registration order (LIFO).
        Errors are logged and do not prevent other plugins from running.
        """
        # Iterate in reverse order
        for plugin in reversed(self._plugins):
            try:
                if hasattr(plugin, "on_shutdown"):
                    await plugin.on_shutdown()
            except Exception as e:
                logger.error(
                    f"Plugin {plugin.__class__.__name__} shutdown error: {e}",
                    exc_info=True,
                )

    async def before_request(self, request: Request) -> Response | None:
        """Call before_request for all registered plugins.

        Plugins are called in registration order (FIFO).
        If any plugin returns a Response, processing stops and that
        response is returned (short-circuit).

        Args:
            request: The incoming request.

        Returns:
            None to continue processing, or a Response to short-circuit.
        """
        for plugin in self._plugins:
            try:
                if hasattr(plugin, "before_request"):
                    result = await plugin.before_request(request)
                    if result is not None:
                        # Short-circuit: return the response
                        return result
            except Exception as e:
                logger.error(
                    f"Plugin {plugin.__class__.__name__} before_request error: {e}",
                    exc_info=True,
                )
        return None

    async def after_request(
        self, request: Request, response: Response
    ) -> Response:
        """Call after_request for all registered plugins.

        Plugins are called in reverse registration order (LIFO).
        Each plugin receives the response from the previous plugin,
        allowing modification.

        Args:
            request: The incoming request.
            response: The generated response.

        Returns:
            The potentially modified response.
        """
        # Iterate in reverse order
        for plugin in reversed(self._plugins):
            try:
                if hasattr(plugin, "after_request"):
                    response = await plugin.after_request(request, response)
            except Exception as e:
                logger.error(
                    f"Plugin {plugin.__class__.__name__} after_request error: {e}",
                    exc_info=True,
                )
        return response

    def get_openapi_contributions(self) -> dict[str, Any]:
        """Aggregate OpenAPI contributions from all plugins.

        Returns:
            A merged dictionary of all plugin OpenAPI contributions.
        """
        contributions = []
        for plugin in self._plugins:
            try:
                if hasattr(plugin, "openapi_schema"):
                    # Handle both property and method
                    schema = plugin.openapi_schema
                    if callable(schema):
                        schema = schema()
                    if schema is not None:
                        normalized = get_openapi_contribution(schema)
                        if normalized:
                            contributions.append(normalized)
            except Exception as e:
                logger.error(
                    f"Plugin {plugin.__class__.__name__} openapi_schema error: {e}",
                    exc_info=True,
                )

        return merge_openapi_schemas(*contributions)

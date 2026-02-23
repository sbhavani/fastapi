"""
FastAPI Plugin System.

This module provides a formal plugin system for FastAPI applications, including:
- PluginProtocol: A Protocol interface defining the plugin contract
- PluginManager: Manages plugin lifecycle and hook execution

## Plugin Protocol

Plugins can implement the following lifecycle hooks:

- `on_startup`: Called when the application starts
- `on_shutdown`: Called when the application shuts down
- `before_request`: Called before each request is processed
- `after_request`: Called after each request is processed
- `on_openapi_schema`: Called during OpenAPI schema generation to allow extensions

## Example

```python
from fastapi import FastAPI
from fastapi.plugins import PluginProtocol

class MyPlugin(PluginProtocol):
    async def on_startup(self, app: FastAPI) -> None:
        print("App starting up!")

    async def on_shutdown(self, app: FastAPI) -> None:
        print("App shutting down!")

    async def before_request(self, request: Request) -> None:
        print(f"Before request: {request.url}")

    async def after_request(self, request: Request, response: Response) -> None:
        print(f"After request: {response.status_code}")

    def on_openapi_schema(self, schema: dict) -> dict:
        # Add custom OpenAPI extensions
        schema["info"]["x-custom-field"] = "custom value"
        return schema

app = FastAPI()
app.register_plugin(MyPlugin())
```
"""
from typing import Any, Callable, Protocol, TypeVar, Union

from typing_extensions import TypeAlias, TypedDict

from starlette.requests import Request
from starlette.responses import Response


class OpenAPISchema(TypedDict, total=False):
    """Type alias for OpenAPI schema dict."""
    pass


# Type for lifecycle hooks
LifecycleHook: TypeAlias = Callable[..., Any]
BeforeRequestHook: TypeAlias = Callable[[Request], Any]
AfterRequestHook: TypeAlias = Callable[[Request, Response], Any]
OpenAPIExtensionHook: TypeAlias = Callable[[dict[str, Any]], dict[str, Any]]


class PluginProtocol(Protocol):
    """
    Protocol interface for FastAPI plugins.

    This defines the contract that all plugins must follow.
    All methods are optional, so plugins can implement only the hooks they need.

    ## Example

    ```python
    from fastapi import FastAPI
    from fastapi.plugins import PluginProtocol

    class MyPlugin:
        async def on_startup(self, app: FastAPI) -> None:
            # Initialize plugin resources
            pass

        async def on_shutdown(self, app: FastAPI) -> None:
            # Clean up plugin resources
            pass

        async def before_request(self, request: Request) -> None:
            # Do something before each request
            pass

        async def after_request(self, request: Request, response: Response) -> None:
            # Do something after each request
            pass

        def on_openapi_schema(self, schema: dict) -> dict:
            # Modify or extend the OpenAPI schema
            schema["x-plugin-extensions"] = {"name": "my-plugin"}
            return schema
    ```
    """

    async def on_startup(self, app: "FastAPI") -> None:
        """
        Called when the FastAPI application starts.

        Args:
            app: The FastAPI application instance.
        """
        ...

    async def on_shutdown(self, app: "FastAPI") -> None:
        """
        Called when the FastAPI application shuts down.

        Args:
            app: The FastAPI application instance.
        """
        ...

    async def before_request(self, request: Request) -> None:
        """
        Called before each request is processed.

        Args:
            request: The incoming request.
        """
        ...

    async def after_request(self, request: Request, response: Response) -> None:
        """
        Called after each request is processed.

        Args:
            request: The incoming request.
            response: The response that will be sent.
        """
        ...

    def on_openapi_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Called during OpenAPI schema generation to allow plugins to extend the schema.

        This method is called after the base OpenAPI schema is generated but before
        it is cached and returned. Plugins can modify the schema in place or return
        a completely new schema.

        Args:
            schema: The generated OpenAPI schema dictionary.

        Returns:
            The (potentially modified) OpenAPI schema dictionary.
        """
        ...


# Import FastAPI at module level for type hints (avoid circular import at runtime)
# This is done inside type checkers only
FastAPI: type["FastAPI"] | None = None


def _get_fastapi_type() -> type["FastAPI"]:
    """Lazily import FastAPI to avoid circular imports."""
    global FastAPI
    if FastAPI is None:
        from fastapi import FastAPI as _FastAPI
        FastAPI = _FastAPI  # type: ignore[assignment]
    return FastAPI  # type: ignore[return-value]


# Create a runtime checkable version
class _PluginRuntimeCheck:
    """Mixin to make Protocol runtime-checkable."""
    pass


class PluginManager:
    """
    Manages plugin registration and lifecycle for a FastAPI application.

    This class handles:
    - Registering plugins
    - Executing lifecycle hooks in order
    - Coordinating OpenAPI schema extensions

    ## Example

    ```python
    from fastapi import FastAPI
    from fastapi.plugins import PluginManager, PluginProtocol

    app = FastAPI()
    plugin_manager = PluginManager(app)

    class MyPlugin(PluginProtocol):
        pass

    plugin_manager.register(MyPlugin())
    ```
    """

    def __init__(self, app: "FastAPI") -> None:
        """
        Initialize the plugin manager.

        Args:
            app: The FastAPI application instance.
        """
        self._app = app
        self._plugins: list[PluginProtocol] = []

    @property
    def app(self) -> "FastAPI":
        """Get the FastAPI application instance."""
        return self._app

    @property
    def plugins(self) -> list[PluginProtocol]:
        """Get the list of registered plugins."""
        return self._plugins.copy()

    def register(self, plugin: PluginProtocol) -> PluginProtocol:
        """
        Register a plugin with the application.

        Args:
            plugin: An instance of a class implementing PluginProtocol.

        Returns:
            The registered plugin instance (for chaining).

        ## Example

        ```python
        from fastapi import FastAPI
        from fastapi.plugins import PluginManager, PluginProtocol

        class MyPlugin(PluginProtocol):
            pass

        app = FastAPI()
        plugin = MyPlugin()
        app.plugin_manager.register(plugin)
        ```
        """
        self._plugins.append(plugin)
        return plugin

    def unregister(self, plugin: PluginProtocol) -> bool:
        """
        Unregister a plugin from the application.

        Args:
            plugin: The plugin instance to remove.

        Returns:
            True if the plugin was found and removed, False otherwise.
        """
        try:
            self._plugins.remove(plugin)
            return True
        except ValueError:
            return False

    async def on_startup(self) -> None:
        """
        Execute all registered on_startup hooks.

        Called when the application starts. Hooks are executed in the order
        they were registered.
        """
        for plugin in self._plugins:
            if hasattr(plugin, "on_startup"):
                await plugin.on_startup(self._app)

    async def on_shutdown(self) -> None:
        """
        Execute all registered on_shutdown hooks.

        Called when the application shuts down. Hooks are executed in reverse
        order (last registered first) to ensure proper cleanup order.
        """
        for plugin in reversed(self._plugins):
            if hasattr(plugin, "on_shutdown"):
                await plugin.on_shutdown(self._app)

    async def before_request(self, request: Request) -> None:
        """
        Execute all registered before_request hooks.

        Called before each request is processed. Hooks are executed in the
        order they were registered.

        Args:
            request: The incoming request.
        """
        for plugin in self._plugins:
            if hasattr(plugin, "before_request"):
                await plugin.before_request(request)

    async def after_request(self, request: Request, response: Response) -> None:
        """
        Execute all registered after_request hooks.

        Called after each request is processed. Hooks are executed in reverse
        order (last registered first) to ensure proper cleanup order.

        Args:
            request: The incoming request.
            response: The response that will be sent.
        """
        for plugin in reversed(self._plugins):
            if hasattr(plugin, "after_request"):
                await plugin.after_request(request, response)

    def on_openapi_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Execute all registered on_openapi_schema hooks.

        Called during OpenAPI schema generation to allow plugins to extend
        the schema. Hooks are executed in order, with each hook receiving
        the result of the previous hook.

        Args:
            schema: The generated OpenAPI schema dictionary.

        Returns:
            The (potentially modified) OpenAPI schema dictionary.
        """
        for plugin in self._plugins:
            if hasattr(plugin, "on_openapi_schema"):
                schema = plugin.on_openapi_schema(schema)
        return schema


def get_plugin_manager(app: "FastAPI") -> PluginManager:
    """
    Get or create the plugin manager for a FastAPI application.

    If the application already has a _plugin_manager attribute, it will be returned.
    Otherwise, a new PluginManager will be created and attached to the application.

    Args:
        app: The FastAPI application instance.

    Returns:
        The plugin manager for the application.
    """
    if not hasattr(app, "_plugin_manager"):
        app._plugin_manager = PluginManager(app)
    return app._plugin_manager

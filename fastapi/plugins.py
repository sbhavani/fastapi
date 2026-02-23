from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Protocol

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response


class PluginProtocol(Protocol):
    """
    Protocol defining the interface for FastAPI plugins.

    Plugins can implement any of the optional lifecycle hooks to integrate
    with the FastAPI application lifecycle and request processing.

    ## Example

    ```python
    class MyPlugin:
        async def on_startup(self) -> None:
            print("Starting up!")

        async def on_shutdown(self) -> None:
            print("Shutting down!")

        async def before_request(self, request: Request) -> Response | None:
            # Return None to continue processing, or a Response to short-circuit
            return None

        async def after_request(self, request: Request, response: Response) -> Response:
            return response

        def get_openapi_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
            return schema
    ```

    All methods are optional - implement only what you need.
    """

    async def on_startup(self) -> Any:
        """Called when the FastAPI application starts."""
        ...

    async def on_shutdown(self) -> Any:
        """Called when the FastAPI application stops."""
        ...

    async def before_request(self, request: Request) -> Response | None:
        """
        Called before each request is processed.

        Return None to continue processing, or a Response to short-circuit.
        """
        ...

    async def after_request(self, request: Request, response: Response) -> Response:
        """
        Called after each request is processed.

        Can modify and return the response.
        """
        ...

    def get_openapi_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Called to extend the OpenAPI schema.

        Return the modified schema.
        """
        ...


@dataclass(slots=True)
class PluginInstance:
    """Internal representation of a registered plugin."""

    name: str
    instance: PluginProtocol
    order: int


class PluginManager:
    """Manages plugin registration and execution."""

    def __init__(self) -> None:
        self._plugins: list[PluginInstance] = []
        self._next_order = 0

    def add_plugin(self, plugin: PluginProtocol) -> None:
        """Register a plugin with the manager."""
        if not hasattr(plugin, "__class__"):
            raise TypeError(f"Plugin must be an object. Got {type(plugin)}")

        name = type(plugin).__name__

        for existing in self._plugins:
            if existing.name == name:
                raise ValueError(f"Plugin '{name}' is already registered.")

        instance = PluginInstance(name=name, instance=plugin, order=self._next_order)
        self._plugins.append(instance)
        self._next_order += 1

    def get_plugins(self) -> list[PluginInstance]:
        """Get all registered plugins in registration order."""
        return list(self._plugins)

    async def on_startup(self) -> None:
        """Execute all plugin on_startup hooks in registration order."""
        for plugin in self._plugins:
            hook = getattr(plugin.instance, "on_startup", None)
            if hook is not None and callable(hook):
                await hook()

    async def on_shutdown(self) -> None:
        """Execute all plugin on_shutdown hooks in reverse registration order."""
        for plugin in reversed(self._plugins):
            hook = getattr(plugin.instance, "on_shutdown", None)
            if hook is not None and callable(hook):
                try:
                    await hook()
                except Exception:
                    pass

    def get_middleware_plugins(self) -> list[PluginProtocol]:
        """Get plugins that have before_request or after_request hooks."""
        middleware_plugins = []
        for plugin in self._plugins:
            has_before = callable(getattr(plugin.instance, "before_request", None))
            has_after = callable(getattr(plugin.instance, "after_request", None))
            if has_before or has_after:
                middleware_plugins.append(plugin.instance)
        return middleware_plugins

    def extend_openapi_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Extend the OpenAPI schema with all plugin contributions."""
        result = dict(schema)
        for plugin in self._plugins:
            hook = getattr(plugin.instance, "get_openapi_schema", None)
            if hook is not None and callable(hook):
                result = hook(result)
        return result


# Global state for middleware
_plugin_middleware_instance: "PluginMiddleware | None" = None


class PluginMiddleware:
    """
    ASGI middleware that wraps plugin before_request and after_request hooks.

    This middleware is automatically added when a plugin with request hooks
    is registered with the application.
    """

    def __init__(
        self,
        plugins: list[PluginProtocol],
        app: Any = None,
    ) -> None:
        self.app = app
        self.plugins = plugins
        # Track if we've already called send for this request
        self._response_started = False

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        """Process request through plugin hooks."""
        # Skip non-HTTP scopes (like lifespan)
        if scope.get("type") != "http":
            if self.app is not None:
                await self.app(scope, receive, send)
            return

        from starlette.requests import Request
        from starlette.responses import Response

        # Create request from scope
        request = Request(scope, receive)

        # Response state
        status_code = 200
        response_headers: dict[str, Any] = {}

        async def send_wrapper(message: Any) -> None:
            nonlocal status_code, response_headers
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
                response_headers = dict(message.get("headers", []))
                self._response_started = True
            await send(message)

        # Execute before_request hooks in order
        response: Response | None = None
        for plugin in self.plugins:
            before_hook = getattr(plugin, "before_request", None)
            if before_hook is not None and callable(before_hook):
                try:
                    result = await before_hook(request)
                    if result is not None:
                        response = result
                        break
                except Exception:
                    pass

        # If short-circuit with a valid Response, send the response
        if response is not None and callable(response):
            await response(scope, receive, send)
            # Call after_request hooks
            for plugin in reversed(self.plugins):
                after_hook = getattr(plugin, "after_request", None)
                if after_hook is not None and callable(after_hook):
                    try:
                        await after_hook(request, response)
                    except Exception:
                        pass
            return
        elif response is not None:
            # Invalid response type - ignore and continue
            pass

        # No short-circuit - call the app
        await self.app(scope, receive, send_wrapper)

        # After the app has sent its response, call after_request hooks
        # Create a single response object from the sent data
        response = Response(
            content=b"",
            status_code=status_code,
            headers={k.decode("latin-1") if isinstance(k, bytes) else k:
                    v.decode("latin-1") if isinstance(v, bytes) else v
                    for k, v in response_headers.items()}
        )

        # Call after_request hooks in reverse order
        for plugin in reversed(self.plugins):
            after_hook = getattr(plugin, "after_request", None)
            if after_hook is not None and callable(after_hook):
                try:
                    response = await after_hook(request, response) or response
                except Exception:
                    pass


def get_plugin_middleware(plugins: list[PluginProtocol]) -> type:
    """Get a middleware class that uses the provided plugins."""
    global _plugin_middleware_instance

    # Always create a fresh instance and update the global
    _plugin_middleware_instance = PluginMiddleware(plugins)

    class _PluginMiddlewareWrapper:
        def __init__(self, app: Any) -> None:
            self.app = app

        async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
            # Get fresh plugins list from the global instance
            # This ensures we always have the latest plugins
            middleware = _plugin_middleware_instance
            if middleware is None:
                return
            middleware.plugins = middleware.plugins
            middleware.app = self.app
            middleware._response_started = False
            await middleware(scope, receive, send)

    return _PluginMiddlewareWrapper

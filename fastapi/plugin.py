"""
FastAPI Plugin System.

This module provides a formal plugin system for FastAPI applications with:
- Lifecycle hooks (on_startup, on_shutdown, before_request, after_request)
- Automatic OpenAPI schema extension capability
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Protocol, runtime_checkable

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

if TYPE_CHECKING:
    from fastapi import FastAPI


def is_async_callable(obj: Any) -> bool:
    """Check if an object is an async callable."""
    return hasattr(obj, "__call__") and (
        hasattr(obj.__call__, "__code__") and obj.__call__.__code__.co_flags & 0x80
    ) or (
        hasattr(obj, "__code__") and obj.__code__.co_flags & 0x80
    )


@runtime_checkable
class PluginProtocol(Protocol):
    """
    Protocol defining the interface for FastAPI plugins.

    Plugins can implement any of these hooks to integrate with the FastAPI
    application lifecycle and OpenAPI schema generation.

    ## Example

    ```python
    from fastapi import FastAPI
    from fastapi.plugin import PluginProtocol

    class MyPlugin:
        def on_startup(self, app: FastAPI) -> None:
            print("App starting up!")

        def on_shutdown(self, app: FastAPI) -> None:
            print("App shutting down!")

        def before_request(self, request: Request) -> None:
            print(f"Before request: {request.url}")

        def after_request(self, request: Request, response: Response) -> None:
            print(f"After request: {response.status_code}")

        def openapi_schema(self) -> dict[str, Any] | None:
            return {
                "components": {
                    "schemas": {
                        "CustomSchema": {
                            "type": "object",
                            "properties": {
                                "custom_field": {"type": "string"}
                            }
                        }
                    }
                }
            }

    app = FastAPI()
    app.plugins.append(MyPlugin())
    ```
    """

    def on_startup(self, app: FastAPI) -> None | Awaitable[None]:
        """
        Called when the FastAPI application starts.

        This hook is called during the application startup phase, before
        the server begins accepting requests.

        Args:
            app: The FastAPI application instance.
        """
        ...

    def on_shutdown(self, app: FastAPI) -> None | Awaitable[None]:
        """
        Called when the FastAPI application shuts down.

        This hook is called during the application shutdown phase, after
        the server stops accepting new requests but before the event loop closes.

        Args:
            app: The FastAPI application instance.
        """
        ...

    def before_request(self, request: Request) -> None | Awaitable[None]:
        """
        Called before each request is processed.

        This hook is called after the request is received but before
        the route handler is executed.

        Args:
            request: The incoming request object.
        """
        ...

    def after_request(
        self, request: Request, response: Response
    ) -> None | Awaitable[None]:
        """
        Called after each request is processed.

        This hook is called after the route handler is executed but before
        the response is sent to the client.

        Args:
            request: The incoming request object.
            response: The response that will be sent to the client.
        """
        ...

    def openapi_schema(self) -> dict[str, Any] | None:
        """
        Return additional OpenAPI schema components.

        This hook allows plugins to extend the OpenAPI schema with custom
        components like schemas, security schemes, parameters, etc.

        The returned dictionary will be merged into the generated OpenAPI schema.
        Only the top-level keys 'components', 'security', 'tags', 'paths',
        and 'webhooks' are merged. Within 'components', only 'schemas',
        'securitySchemes', 'parameters', 'responses', and 'requestBodies'
        are merged.

        Returns:
            A dictionary containing additional OpenAPI schema components,
            or None if this plugin doesn't add any schema extensions.
        """
        ...


class Plugin:
    """
    Base class for creating FastAPI plugins.

    This class provides a convenient way to create plugins by inheriting
    from it and overriding only the methods you need.

    ## Example

    ```python
    from fastapi import FastAPI
    from fastapi.plugin import Plugin

    class LoggingPlugin(Plugin):
        def on_startup(self, app: FastAPI) -> None:
            print("App starting!")

        def before_request(self, request: Request) -> None:
            print(f"Request: {request.method} {request.url}")

    app = FastAPI()
    app.plugins.append(LoggingPlugin())
    ```
    """

    def on_startup(self, app: FastAPI) -> None | Awaitable[None]:
        """Called when the FastAPI application starts."""
        pass

    def on_shutdown(self, app: FastAPI) -> None | Awaitable[None]:
        """Called when the FastAPI application shuts down."""
        pass

    def before_request(self, request: Request) -> None | Awaitable[None]:
        """Called before each request is processed."""
        pass

    def after_request(
        self, request: Request, response: Response
    ) -> None | Awaitable[None]:
        """Called after each request is processed."""
        pass

    def openapi_schema(self) -> dict[str, Any] | None:
        """
        Return additional OpenAPI schema components.

        Override this method to add custom schema components to the
        generated OpenAPI schema.
        """
        return None


# Type alias for plugins
PluginType = PluginProtocol | Plugin


class PluginMiddleware:
    """
    ASGI middleware that calls plugin before_request and after_request hooks.

    This middleware wraps the application and calls the before_request hook
    before processing the request and the after_request hook after processing.
    """

    def __init__(self, app: ASGIApp, plugins: list[PluginType] | None = None) -> None:
        self.app = app
        self.plugins = plugins if plugins is not None else []

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Look up plugins from the app at runtime to support adding plugins after init
        app = scope.get("app")
        if app is not None and hasattr(app, "plugins"):
            plugins = app.plugins
        else:
            plugins = self.plugins

        if not plugins:
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Call before_request hooks
        for plugin in plugins:
            if hasattr(plugin, "before_request"):
                before_request = plugin.before_request
                if is_async_callable(before_request):
                    await before_request(request)
                else:
                    before_request(request)

        # Create a custom send function to capture the response
        response_started = False
        response_headers = []
        response_status_code = None

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal response_started, response_headers, response_status_code
            if message["type"] == "http.response.start":
                response_started = True
                response_headers = message.get("headers", [])
                response_status_code = message.get("status", 200)
            await send(message)

        # Process the request
        await self.app(scope, receive, send_wrapper)

        # Create a simple response-like object for after_request hooks
        # We use a minimal object to avoid issues with Starlette's Response
        class SimpleResponse:
            def __init__(self, status_code: int, headers: list):
                self.status_code = status_code
                self.headers = headers
                self.body = b""

        response = SimpleResponse(
            status_code=response_status_code or 200,
            headers=response_headers,
        )

        # Call after_request hooks
        for plugin in plugins:
            if hasattr(plugin, "after_request"):
                after_request = plugin.after_request
                if is_async_callable(after_request):
                    await after_request(request, response)
                else:
                    after_request(request, response)


async def call_plugin_hooks(
    app: FastAPI, event: str
) -> None:
    """
    Call a specific lifecycle hook on all registered plugins.

    Args:
        app: The FastAPI application instance.
        event: The hook to call ('on_startup' or 'on_shutdown').
    """
    for plugin in app.plugins:
        hook = getattr(plugin, event, None)
        if hook is not None and hook is not getattr(Plugin, event, None):
            if is_async_callable(hook):
                await hook(app)
            else:
                hook(app)


def merge_openapi_schemas(
    base_schema: dict[str, Any], extensions: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Merge multiple OpenAPI schema extensions into a base schema.

    Only the following top-level keys are merged:
    - components (specifically schemas, securitySchemes, parameters, responses, requestBodies)
    - security
    - tags
    - paths
    - webhooks

    Args:
        base_schema: The base OpenAPI schema to extend.
        extensions: A list of schema extensions to merge.

    Returns:
        The merged OpenAPI schema.
    """
    import copy

    result = copy.deepcopy(base_schema)

    for extension in extensions:
        if not extension:
            continue

        # Merge components
        if "components" in extension:
            if "components" not in result:
                result["components"] = {}
            for key in (
                "schemas",
                "securitySchemes",
                "parameters",
                "responses",
                "requestBodies",
            ):
                if key in extension.get("components", {}):
                    if key not in result["components"]:
                        result["components"][key] = {}
                    result["components"][key].update(
                        extension["components"].get(key, {})
                    )

        # Merge security
        if "security" in extension:
            if "security" not in result:
                result["security"] = []
            for sec in extension["security"]:
                if sec not in result["security"]:
                    result["security"].append(sec)

        # Merge tags
        if "tags" in extension:
            if "tags" not in result:
                result["tags"] = []
            for tag in extension["tags"]:
                if tag not in result["tags"]:
                    result["tags"].append(tag)

        # Merge paths
        if "paths" in extension:
            if "paths" not in result:
                result["paths"] = {}
            for path, path_item in extension["paths"].items():
                if path not in result["paths"]:
                    result["paths"][path] = path_item
                else:
                    # Merge path operations
                    for method, operation in path_item.items():
                        if method not in result["paths"][path]:
                            result["paths"][path][method] = operation

        # Merge webhooks
        if "webhooks" in extension:
            if "webhooks" not in result:
                result["webhooks"] = {}
            result["webhooks"].update(extension["webhooks"])

    return result

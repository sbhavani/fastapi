"""
TypedMiddleware wrapper for adapting ASGI to type-safe interface.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable, TypeVar, get_type_hints

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from fastapi.middleware.exceptions import MiddlewareTypeError
from fastapi.middleware.typing import MiddlewareHooks

if TYPE_CHECKING:
    from fastapi.middleware.typing import MiddlewareProtocol


class TypedMiddleware:
    """
    Wrapper that adapts a type-safe MiddlewareProtocol to ASGI.

    This class wraps a MiddlewareProtocol implementation and provides
    the ASGI-compatible __call__ method while maintaining type safety.
    """

    def __init__(
        self,
        app: ASGIApp,
        middleware_class: type,
        **middleware_kwargs: Any,
    ) -> None:
        self.app = app
        self.middleware_class = middleware_class
        self.middleware_kwargs = middleware_kwargs

        # Create the actual middleware instance
        try:
            self.middleware_instance = middleware_class(app, **middleware_kwargs)
        except TypeError as e:
            raise MiddlewareTypeError(
                f"Failed to instantiate middleware {middleware_class.__name__}: {e}"
            )

        # Validate the middleware implements the protocol
        self._validate_protocol()

    def _validate_protocol(self) -> None:
        """Validate that the middleware implements MiddlewareProtocol."""
        # Check for __call__ method
        if not hasattr(self.middleware_instance, "__call__"):
            raise MiddlewareTypeError(
                f"Middleware {self.middleware_class.__name__} must implement __call__ method"
            )

        # Check for proper signature
        call_method = getattr(self.middleware_instance, "__call__")
        if not callable(call_method):
            raise MiddlewareTypeError(
                f"Middleware {self.middleware_class.__name__}.__call__ must be callable"
            )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI-compatible __call__ method.

        This wraps the scope/receive/send in a Request object,
        calls the type-safe middleware, and returns the Response.
        """
        # Create request from scope
        request = Request(scope, receive)

        # Define the next middleware/handler
        async def call_next(req: Request) -> Response:
            # Call the next app in the chain
            await self.app(scope, receive, send)
            # Note: The response is sent directly via send, so we return a placeholder
            # This is how ASGI works - the app calls send itself
            return Response(status_code=200)  # Placeholder, actual response sent via send

        try:
            # Call the middleware
            response = await self.middleware_instance.__call__(request, call_next)

            # If response was sent directly via send (ASGI style), we're done
            if response is None:
                return

            # Validate response type
            if not isinstance(response, Response):
                expected_type = self._get_response_type()
                raise MiddlewareTypeError(
                    f"Middleware must return Response, got {type(response).__name__}",
                    expected_type=expected_type,
                    actual_type=type(response),
                )

        except Exception as e:
            if isinstance(e, MiddlewareTypeError):
                raise
            raise

    def _get_response_type(self) -> type:
        """Get the declared response type from the middleware class."""
        try:
            hints = get_type_hints(self.middleware_class.__call__)
            return hints.get("return", Response)
        except Exception:
            return Response

    async def on_startup(self) -> None:
        """Call the middleware's on_startup hook if it exists."""
        if hasattr(self.middleware_instance, "on_startup"):
            await self.middleware_instance.on_startup()

    async def on_shutdown(self) -> None:
        """Call the middleware's on_shutdown hook if it exists."""
        if hasattr(self.middleware_instance, "on_shutdown"):
            await self.middleware_instance.on_shutdown()


def create_typed_middleware(
    middleware_class: type,
    app: ASGIApp,
    **kwargs: Any,
) -> TypedMiddleware:
    """
    Factory function to create a TypedMiddleware instance.

    Args:
        middleware_class: The middleware class to wrap.
        app: The next ASGI application.
        **kwargs: Additional arguments for the middleware.

    Returns:
        A TypedMiddleware instance.

    Raises:
        MiddlewareTypeError: If the middleware is invalid.
    """
    return TypedMiddleware(app, middleware_class, **kwargs)


__all__ = [
    "TypedMiddleware",
    "create_typed_middleware",
]

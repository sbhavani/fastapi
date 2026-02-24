"""
Type-safe middleware system for FastAPI.

This module provides the MiddlewareProtocol class and related utilities
for creating type-safe middleware with full type hints.
"""
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Generic, TypeVar, Protocol

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

if TYPE_CHECKING:
    from collections.abc import Coroutine

# Type variables for request and response
RequestT = TypeVar("RequestT", bound=Request)
ResponseT = TypeVar("ResponseT", bound=Response)

# Type for the next middleware in the chain
NextMiddleware = Callable[[Request], Awaitable[Response]]


class MiddlewareProtocol(Protocol[RequestT, ResponseT]):
    """
    Protocol for type-safe middleware in FastAPI.

    This protocol defines the contract for middleware that wants to use
    type-safe request/response handling. Middleware can define their
    expected request and response types using type parameters.

    Example:
        class AuthMiddleware(MiddlewareProtocol[Request, Response]):
            def __init__(self, app: ASGIApp):
                self.app = app

            async def __call__(self, request: Request, call_next) -> Response:
                # Process request
                return await call_next(request)

    Type Parameters:
        RequestT: The type of request this middleware expects (must be Request or subclass)
        ResponseT: The type of response this middleware returns (must be Response or subclass)

    Optional Methods:
        on_startup: Called when the application starts
        on_shutdown: Called when the application shuts down
    """

    def __init__(self, app: ASGIApp, **kwargs: Any) -> None:
        """
        Initialize the middleware.

        Args:
            app: The next middleware or ASGI application in the chain.
            **kwargs: Additional keyword arguments for the middleware.
        """
        ...

    async def __call__(
        self,
        request: RequestT,
        call_next: NextMiddleware,
    ) -> ResponseT:
        """
        Process a request and optionally modify the response.

        Args:
            request: The incoming request.
            call_next: The next middleware or route handler in the chain.

        Returns:
            The response from the next middleware or route handler.
        """
        ...


class MiddlewareHooks:
    """
    Optional mixin for middleware that want startup/shutdown hooks.

    Example:
        class LifecycleMiddleware(MiddlewareProtocol[Request, Response], MiddlewareHooks):
            async def on_startup(self):
                print("Starting up!")

            async def on_shutdown(self):
                print("Shutting down!")
    """

    async def on_startup(self) -> None:
        """
        Called when the application starts.

        Override this method to perform initialization.
        """
        pass

    async def on_shutdown(self) -> None:
        """
        Called when the application shuts down.

        Override this method to perform cleanup.
        """
        pass


# Re-export for convenience
__all__ = [
    "MiddlewareProtocol",
    "MiddlewareHooks",
    "RequestT",
    "ResponseT",
    "NextMiddleware",
]

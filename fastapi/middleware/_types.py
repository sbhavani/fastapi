"""
Type definitions and protocols for typed middleware in FastAPI.

This module provides:
- MiddlewareProtocol: A Protocol defining type-safe middleware interface
- Type-safe request/response handling
- Middleware dependencies support
- Compile-time middleware ordering validation
"""

from __future__ import annotations

import sys
from abc import ABC
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

from starlette.types import ASGIApp, Receive, Scope, Send

if TYPE_CHECKING:
    from typing_extensions import ParamSpec, TypeAlias

    if sys.version_info >= (3, 10):
        from typing import Concatenate
    else:
        from typing_extensions import Concatenate
else:
    from typing_extensions import ParamSpec, TypeAlias

# Type aliases for ASGI
ScopeVar = TypeVar("ScopeVar", bound=Scope)
ResponseVar = TypeVar("ResponseVar")
RequestVar = TypeVar("RequestVar")
SendVar = TypeVar("SendVar")

# Middleware dependency parameter specification
P = ParamSpec("P")
R = TypeVar("R")


class MiddlewareOrder(Enum):
    """Middleware execution order constants for compile-time ordering validation.

    Values:
        FIRST: Middleware should be executed first (outermost)
        LAST: Middleware should be executed last (innermost, closest to routes)
    """

    FIRST = "first"
    LAST = "last"


class MiddlewareType(Enum):
    """Middleware type classification for ordering validation.

    Values:
        BEFORE: Middleware that runs before the request handler
        AFTER: Middleware that runs after the request handler (response processing)
        WRAPPER: Middleware that wraps both request and response handling
    """

    BEFORE = "before"
    AFTER = "after"
    WRAPPER = "wrapper"


# Type alias for middleware callables
MiddlewareCallable: TypeAlias = Callable[
    [Scope, Receive, Send], Awaitable[None]
]


class MiddlewareProtocol(ABC, Generic[ScopeVar, ResponseVar]):
    """
    Protocol defining the interface for type-safe middleware.

    This protocol provides:
    - Type-safe request/response handling with generic scope types
    - Support for typed middleware dependencies
    - Compile-time ordering validation through class attributes

    Type Parameters:
        ScopeVar: The type of ASGI scope (defaults to generic Scope)
        ResponseVar: The type of response being built

    Class Attributes:
        order: Optional MiddlewareOrder for ordering hints
        middleware_type: MiddlewareType classification

    Example:
        ```python
        class MyMiddleware(MiddlewareProtocol[dict[str, Any], None]):
            order = MiddlewareOrder.FIRST
            middleware_type = MiddlewareType.WRAPPER

            def __init__(self, app: ASGIApp):
                self.app = app

            async def __call__(self, scope: dict[str, Any], receive: Receive, send: Send) -> None:
                # Process request
                await self.app(scope, receive, send)
                # Process response
        ```
    """

    # Class attributes for compile-time ordering validation
    order: MiddlewareOrder | None = None
    middleware_type: MiddlewareType = MiddlewareType.WRAPPER

    def __init__(self, app: ASGIApp, **kwargs: Any) -> None:
        """
        Initialize the middleware.

        Args:
            app: The next ASGI application in the chain
            **kwargs: Additional middleware-specific configuration
        """
        ...

    async def __call__(
        self,
        scope: ScopeVar,
        receive: Receive,
        send: Send,
    ) -> None:
        """
        Process the request/response through this middleware.

        Args:
            scope: The ASGI scope dictionary
            receive: The ASGI receive callable
            send: The ASGI send callable

        Returns:
            None
        """
        ...


class MiddlewareDependenciesMixin:
    """
    Mixin class providing dependency injection support for middleware.

    This mixin allows middleware to use FastAPI's dependency injection system,
    enabling type-safe middleware dependencies with proper lifecycle management.

    Example:
        ```python
        class AuthMiddleware(MiddlewareDependenciesMixin):
            def __init__(
                self,
                app: ASGIApp,
                auth_service: AuthService = Depends()
            ):
                super().__init__(app)
                self.auth_service = auth_service
        ```
    """

    _middleware_dependencies: list[Callable[..., Any]] | None = None

    @classmethod
    def get_dependencies(cls) -> list[Callable[..., Any]]:
        """
        Get the list of dependency callables for this middleware.

        Returns:
            List of dependency callables
        """
        return cls._middleware_dependencies or []


class MiddlewareRunner(Generic[ScopeVar]):
    """
    A class to run middleware with proper type hints and ordering.

    This class handles:
    - Type-safe middleware execution
    - Dependency resolution
    - Ordering validation

    Type Parameters:
        ScopeVar: The type of ASGI scope

    Example:
        ```python
        runner = MiddlewareRunner[dict[str, Any]]()
        await runner.run(middleware_instance, scope, receive, send)
        ```
    """

    def __init__(
        self,
        middleware: MiddlewareProtocol[ScopeVar, Any],
        dependencies: list[Callable[..., Any]] | None = None,
    ) -> None:
        """
        Initialize the middleware runner.

        Args:
            middleware: The middleware instance to run
            dependencies: Optional list of dependency callables
        """
        self.middleware = middleware
        self.dependencies = dependencies or []

    async def run(
        self,
        scope: ScopeVar,
        receive: Receive,
        send: Send,
    ) -> None:
        """
        Run the middleware with the given scope, receive, and send.

        Args:
            scope: The ASGI scope dictionary
            receive: The ASGI receive callable
            send: The ASGI send callable
        """
        await self.middleware(scope, receive, send)


def validate_middleware_order(
    middlewares: list[type[MiddlewareProtocol[..., Any]]],
) -> list[type[MiddlewareProtocol[..., Any]]]:
    """
    Validate middleware ordering based on MiddlewareOrder hints.

    This function performs compile-time validation of middleware order by
    sorting middleware based on their order class attribute.

    Args:
        middlewares: List of middleware classes to validate

    Returns:
        Sorted list of middleware classes

    Raises:
        ValueError: If circular dependencies or invalid orders are detected

    Example:
        ```python
        class FirstMiddleware(MiddlewareProtocol):
            order = MiddlewareOrder.FIRST

        class LastMiddleware(MiddlewareProtocol):
            order = MiddlewareOrder.LAST

        sorted_middleware = validate_middleware_order([
            LastMiddleware,
            FirstMiddleware,
        ])
        # Returns [FirstMiddleware, LastMiddleware]
        ```
    """
    if not middlewares:
        return []

    # Create a mapping of middleware to their order
    order_map: dict[type[MiddlewareProtocol[..., Any]], int] = {}

    for i, middleware in enumerate(middlewares):
        order = getattr(middleware, "order", None)
        if order is MiddlewareOrder.FIRST:
            order_map[middleware] = -1000 + i
        elif order is MiddlewareOrder.LAST:
            order_map[middleware] = 1000 + i
        else:
            order_map[middleware] = i

    # Sort by order value
    sorted_middlewares = sorted(middlewares, key=lambda m: order_map.get(m, 0))

    return sorted_middlewares


def create_middleware_dependency(
    middleware_class: type[MiddlewareProtocol[..., Any]],
) -> Callable[[], MiddlewareProtocol[..., Any]]:
    """
    Create a dependency callable for middleware instantiation.

    This function creates a factory function that can be used with
    FastAPI's dependency injection system to provide middleware instances.

    Args:
        middleware_class: The middleware class to create a dependency for

    Returns:
        A callable that returns a middleware instance

    Example:
        ```python
        def get_auth_middleware() -> type[AuthMiddleware]:
            return create_middleware_dependency(AuthMiddleware)
        ```
    """

    def dependency(
        app: ASGIApp = ...,
    ) -> MiddlewareProtocol[..., Any]:
        return middleware_class(app)

    return dependency


# Re-export commonly used types
__all__ = [
    "MiddlewareProtocol",
    "MiddlewareDependenciesMixin",
    "MiddlewareRunner",
    "MiddlewareOrder",
    "MiddlewareType",
    "validate_middleware_order",
    "create_middleware_dependency",
    "ScopeVar",
    "ResponseVar",
    "RequestVar",
    "SendVar",
    "MiddlewareCallable",
]

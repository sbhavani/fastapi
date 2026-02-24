"""
Typed middleware implementation for FastAPI.

This module provides:
- BaseTypedMiddleware: Base class for typed middleware with dependency injection
- TypedMiddlewareMixin: Mixin for adding typing to existing middleware
- Functions for creating and managing typed middleware
"""

from __future__ import annotations

import sys
from collections.abc import Awaitable, Callable
from contextlib import AsyncExitStack
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    TypeVar,
    overload,
)

from starlette.types import ASGIApp, Receive, Scope, Send

from fastapi.params import Depends
from fastapi.dependencies.utils import solve_dependencies

# Type variable for ASGI scope
ScopeT = TypeVar("ScopeT")

if TYPE_CHECKING:
    from typing_extensions import ParamSpec

    if sys.version_info >= (3, 10):
        from typing import Concatenate
    else:
        from typing_extensions import Concatenate
else:
    from typing_extensions import ParamSpec, Concatenate

if TYPE_CHECKING:
    from fastapi.middleware._types import (
        MiddlewareOrder,
        MiddlewareType,
        MiddlewareCallable,
    )

# Type variables
P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
AppType = TypeVar("AppType", bound=ASGIApp)


class MiddlewareError(Exception):
    """Base exception for middleware-related errors."""

    pass


class MiddlewareDependencyError(MiddlewareError):
    """Error raised when middleware dependency resolution fails."""

    pass


class MiddlewareOrderError(MiddlewareError):
    """Error raised when middleware ordering validation fails."""

    pass


class BaseTypedMiddleware(Generic[ScopeT]):
    """
    Base class for typed middleware with dependency injection support.

    This class provides:
    - Type-safe ASGI interface
    - Dependency injection through FastAPI's Depends system
    - Async context management
    - Response type hints

    Type Parameters:
        Scope: The ASGI scope type (e.g., dict for HTTP, dict for WebSocket)

    Example:
        ```python
        class AuthMiddleware(BaseTypedMiddleware[dict[str, Any]]):
            def __init__(
                self,
                app: ASGIApp,
                auth_service: AuthService = Depends()
            ):
                super().__init__(app)
                self.auth_service = auth_service

            async def dispatch(
                self,
                scope: dict[str, Any],
                receive: Receive,
                send: Send
            ) -> None:
                # Validate authentication
                await self.app(scope, receive, send)
        ```
    """

    # Class attributes for ordering (can be overridden in subclasses)
    order: int | None = None
    middleware_type: str = "wrapper"

    def __init__(
        self,
        app: ASGIApp,
        *,
        dependencies: tuple[Depends, ...] | None = None,
    ) -> None:
        """
        Initialize the typed middleware.

        Args:
            app: The next ASGI application in the chain
            dependencies: Optional tuple of Depends for dependency injection
        """
        self.app = app
        self.dependencies = dependencies or ()
        self._async_exit_stack: AsyncExitStack | None = None

    @property
    def dispatch(self) -> Callable[[Scope, Receive, Send], Awaitable[None]]:
        """
        Get the dispatch method for ASGI middleware.

        This property allows the middleware to be used with
        Starlette's Middleware class.

        Returns:
            The async dispatch method
        """
        return self._async_dispatch

    async def _async_dispatch(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """
        Internal dispatch method that handles dependency resolution.

        Args:
            scope: The ASGI scope dictionary
            receive: The ASGI receive callable
            send: The ASGI send callable
        """
        # Create async exit stack for this request
        async with AsyncExitStack() as stack:
            self._async_exit_stack = stack

            # Solve dependencies if any
            if self.dependencies:
                scope_copy = dict(scope)
                # Add middleware to scope for dependency context
                scope_copy["_fastapi_middleware_"] = True

                # Create a minimal request for dependency resolution
                # We'll use a simple approach: just add the app
                solved_deps = await solve_dependencies(
                    scope=scope_copy,
                    receive=receive,
                    send=send,
                    dependencies=self.dependencies,
                )

                # Apply solved dependencies to self
                for dep_name, dep_value in solved_deps.items():
                    setattr(self, dep_name, dep_value)

            # Call the actual dispatch method
            await self.dispatch(scope, receive, send)

    async def dispatch(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """
        Process the request through this middleware.

        This method should be overridden in subclasses to implement
        custom middleware logic.

        Args:
            scope: The ASGI scope dictionary
            receive: The ASGI receive callable
            send: The ASGI send callable

        Example:
            ```python
            class AuthMiddleware(BaseTypedMiddleware[dict[str, Any]]):
                async def dispatch(
                    self,
                    scope: dict[str, Any],
                    receive: Receive,
                    send: Send
                ) -> None:
                    # Check auth headers
                    # ...
                    await self.app(scope, receive, send)
            ```
        """
        await self.app(scope, receive, send)


class TypedMiddlewareMixin(Generic[AppType]):
    """
    Mixin to add typed middleware capabilities to existing middleware classes.

    This mixin can be added to any ASGI middleware class to provide:
    - Type hints for the app parameter
    - Dependency injection support
    - Order and type class attributes for validation

    Type Parameters:
        AppType: The type of ASGI app this middleware wraps

    Example:
        ```python
        class MyMiddleware(TypedMiddlewareMixin[ASGIApp]):
            order = 0
            middleware_type = "wrapper"

            def __init__(
                self,
                app: ASGIApp,
                config: MyConfig = Depends(my_config_provider)
            ):
                super().__init__(app)
                self.config = config
        ```
    """

    # Class attributes for ordering
    order: int | None = None
    middleware_type: str = "wrapper"

    def __init__(self, app: AppType) -> None:
        """Initialize the mixin with an ASGI app."""
        self.app: AppType = app


def create_typed_middleware(
    middleware_class: type[BaseTypedMiddleware[Scope]],
    *,
    dependencies: tuple[Depends, ...] | None = None,
) -> type[BaseTypedMiddleware[Scope]]:
    """
    Create a typed middleware class with dependencies.

    This function wraps a middleware class to add dependency injection
    support while preserving type information.

    Args:
        middleware_class: The middleware class to wrap
        dependencies: Optional tuple of Depends for dependency injection

    Returns:
        A new middleware class with dependencies

    Example:
        ```python
        class MyMiddleware(BaseTypedMiddleware[dict[str, Any]]):
            async def dispatch(self, scope, receive, send):
                ...

        TypedMyMiddleware = create_typed_middleware(
            MyMiddleware,
            dependencies=(Depends(get_config),)
        )
        ```
    """
    original_init = middleware_class.__init__

    def new_init(
        self: BaseTypedMiddleware[Scope],
        app: ASGIApp,
        **kwargs: Any,
    ) -> None:
        # Combine original kwargs with dependencies
        init_kwargs = {"dependencies": dependencies, **kwargs}
        original_init(self, app, **init_kwargs)

    # Create new class with modified init
    new_class = type(
        middleware_class.__name__,
        (middleware_class,),
        {
            "__init__": new_init,
            "order": getattr(middleware_class, "order", None),
            "middleware_type": getattr(middleware_class, "middleware_type", "wrapper"),
        },
    )

    return new_class


def validate_middleware_signature(
    middleware_class: type[BaseTypedMiddleware[Scope]],
) -> bool:
    """
    Validate that a middleware class has the correct signature.

    This function checks that the middleware class:
    - Has an __init__ that accepts an app parameter
    - Has a dispatch method that is awaitable

    Args:
        middleware_class: The middleware class to validate

    Returns:
        True if the middleware class has a valid signature

    Raises:
        MiddlewareError: If the middleware class has an invalid signature
    """
    import inspect

    # Check __init__ signature
    if not hasattr(middleware_class, "__init__"):
        raise MiddlewareError(
            f"Middleware class {middleware_class.__name__} must have an __init__ method"
        )

    init_sig = inspect.signature(middleware_class.__init__)
    params = list(init_sig.parameters.keys())

    if "app" not in params:
        raise MiddlewareError(
            f"Middleware class {middleware_class.__name__} __init__ must accept 'app' parameter"
        )

    # Check dispatch method
    if not hasattr(middleware_class, "dispatch"):
        raise MiddlewareError(
            f"Middleware class {middleware_class.__name__} must have a 'dispatch' method"
        )

    dispatch_method = getattr(middleware_class, "dispatch")
    if not inspect.iscoroutinefunction(dispatch_method):
        raise MiddlewareError(
            f"Middleware class {middleware_class.__name__} dispatch method must be async"
        )

    return True


# Re-export commonly used items
__all__ = [
    "BaseTypedMiddleware",
    "TypedMiddlewareMixin",
    "create_typed_middleware",
    "validate_middleware_signature",
    "MiddlewareError",
    "MiddlewareDependencyError",
    "MiddlewareOrderError",
]

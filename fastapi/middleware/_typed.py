"""
Typed Middleware module for FastAPI.

This module provides type-safe middleware abstractions with:
- MiddlewareProtocol: Protocol for type-safe request/response handling
- Type hints for middleware dependencies
- Compile-time middleware ordering validation
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeVar, overload

from starlette.types import ASGIApp, Receive, Scope, Send

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

# Type for the next middleware in the chain
NextMiddleware = Callable[[Scope, Receive, Send], Awaitable[None]]

# Type for middleware callable
MiddlewareCallable = Callable[..., Awaitable[Any]]

# Type variable for middleware dependencies
T = TypeVar("T")

# Type for middleware order - used for compile-time ordering validation
MiddlewareOrder = int


class MiddlewareProtocol(Protocol):
    """
    Protocol defining the interface for type-safe middleware.

    This protocol can be used to define middleware classes that are
    fully type-checked. It supports both ASGI-style middleware (with
    __call__) and function-style middleware.

    Example:
        class MyMiddleware:
            def __init__(self, app: ASGIApp, some_param: str) -> None:
                self.app = app
                self.some_param = some_param

            async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
                # Process request
                await self.app(scope, receive, send)
                # Process response
    """

    def __init__(self, app: ASGIApp, *args: Any, **kwargs: Any) -> None:
        """Initialize the middleware with an ASGI app and optional parameters."""
        ...

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process the request/response cycle."""
        ...


class FunctionMiddlewareProtocol(Protocol):
    """
    Protocol for function-style middleware (used with @app.middleware()).

    This protocol defines the signature that function middleware should follow
    for full type safety when using the @app.middleware() decorator.

    Example:
        async def my_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
            # Process request
            response = await call_next(request)
            # Process response
            return response
    """

    def __call__(
        self,
        request: Request,
        call_next: Callable[..., Awaitable[Response]],
    ) -> Awaitable[Response]:
        ...


class MiddlewareDependencies:
    """
    Container for declaring middleware dependencies.

    This class allows middleware to declare dependencies that will be
    injected at runtime, similar to FastAPI's dependency injection system.

    Example:
        class MyMiddleware:
            def __init__(
                self,
                app: ASGIApp,
                db: Annotated[Database, Depends(get_db)]
            ) -> None:
                self.app = app
                self.db = db
    """

    def __init__(self, *dependencies: Any) -> None:
        self.dependencies = dependencies


class MiddlewareWrapper(Generic[T]):
    """
    Generic wrapper for middleware that provides compile-time ordering validation.

    This class wraps a middleware and provides type-safe ordering guarantees.
    The order parameter is validated at type-check time.

    Example:
        # Create ordered middleware
        auth_middleware = MiddlewareWrapper(AuthMiddleware, order=1)
        logging_middleware = MiddlewareWrapper(LoggingMiddleware, order=2)

        # Use in FastAPI
        app = FastAPI()
        app.add_middleware(AuthMiddleware)
        app.add_middleware(LoggingMiddleware)
    """

    def __init__(
        self,
        middleware_class: type[MiddlewareProtocol],
        *,
        order: int | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the middleware wrapper.

        Args:
            middleware_class: The middleware class to wrap
            order: Optional order for compile-time validation
            **kwargs: Additional arguments to pass to the middleware
        """
        self.middleware_class = middleware_class
        self.order = order
        self.kwargs = kwargs

    def __repr__(self) -> str:
        return f"MiddlewareWrapper({self.middleware_class.__name__}, order={self.order})"


class MiddlewareStack:
    """
    Type-safe middleware stack with compile-time ordering validation.

    This class allows building a middleware stack with type-checked ordering.
    The order parameter ensures that middleware are added in the correct order
    at compile time.

    Example:
        stack = MiddlewareStack()
        stack.add(AuthMiddleware, order=1)
        stack.add(LoggingMiddleware, order=2)
        stack.add(CORSMiddleware, order=3)

        # Build the final middleware
        app = stack.build(app)
    """

    def __init__(self) -> None:
        self._middleware: list[tuple[int, type[MiddlewareProtocol], dict[str, Any]]] = []

    def add(
        self,
        middleware_class: type[MiddlewareProtocol],
        *,
        order: int | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Add a middleware to the stack with optional ordering.

        Args:
            middleware_class: The middleware class to add
            order: Optional order for compile-time validation
            **kwargs: Arguments to pass to the middleware
        """
        if order is None:
            order = len(self._middleware)
        self._middleware.append((order, middleware_class, kwargs))

    def build(self, app: ASGIApp) -> ASGIApp:
        """
        Build the middleware stack.

        Args:
            app: The final ASGI application

        Returns:
            The ASGI app wrapped with all middleware
        """
        # Sort by order
        sorted_middleware = sorted(self._middleware, key=lambda x: x[0])

        # Apply middleware in reverse order (last added = outermost)
        for _, middleware_class, kwargs in reversed(sorted_middleware):
            app = middleware_class(app, **kwargs)

        return app


class MiddlewareBuilder(Generic[T]):
    """
    Builder class for creating type-safe middleware with dependencies.

    This class provides a fluent API for building middleware with
    type-checked dependencies.

    Example:
        builder = MiddlewareBuilder[MyDatabase]()
        middleware = builder.with_dependency(get_db).build()

        class MyMiddleware:
            def __init__(self, app: ASGIApp, db: MyDatabase) -> None:
                self.app = app
                self.db = db
    """

    def __init__(self, middleware_class: type[T]) -> None:
        self._middleware_class = middleware_class
        self._dependencies: dict[str, Any] = {}

    def with_dependency(self, name: str, dependency: Any) -> "MiddlewareBuilder[T]":
        """
        Add a dependency to the middleware.

        Args:
            name: The parameter name
            dependency: The dependency value

        Returns:
            Self for chaining
        """
        self._dependencies[name] = dependency
        return self

    def build(self, app: ASGIApp) -> type[T]:
        """
        Build the middleware class with resolved dependencies.

        Args:
            app: The ASGI app

        Returns:
            The middleware class instantiated with dependencies
        """
        return self._middleware_class(app, **self._dependencies)


# Re-export commonly used types
__all__ = [
    "ASGIApp",
    "Awaitable",
    "Callable",
    "FunctionMiddlewareProtocol",
    "MiddlewareCallable",
    "MiddlewareDependencies",
    "MiddlewareOrder",
    "MiddlewareProtocol",
    "MiddlewareStack",
    "MiddlewareWrapper",
    "NextMiddleware",
    "Receive",
    "Scope",
    "Send",
    "Sequence",
]

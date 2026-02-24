"""
Dependency injection utilities for typed middleware.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi.dependencies.utils import (
    get_middleware_dependant,
    solve_middleware_dependencies_sync,
)

if TYPE_CHECKING:
    from collections.abc import Coroutine


class MiddlewareDependencyResolver:
    """
    Resolves dependencies for middleware using FastAPI's dependency injection system.

    This class allows middleware to declare dependencies that will be resolved
    at middleware initialization time, similar to how route dependencies work.
    """

    def __init__(self) -> None:
        self._cache: dict[type, Any] = {}

    def resolve(
        self,
        middleware_class: type,
        app: Any,
        dependency_overrides: dict[type, Any] | None = None,
        dependency_overrides_provider: Any | None = None,
    ) -> Any:
        """
        Resolve dependencies for a middleware class.

        Args:
            middleware_class: The middleware class to instantiate.
            app: The ASGI app to pass to the middleware.
            dependency_overrides: Optional dict to override dependencies (deprecated, use dependency_overrides_provider).
            dependency_overrides_provider: Optional provider for dependency overrides.

        Returns:
            An instance of the middleware with resolved dependencies.
        """
        import inspect

        # Get the signature of __init__ to find non-dependency parameters
        sig = inspect.signature(middleware_class.__init__)
        params = sig.parameters

        # Get the middleware dependant (extracts dependencies)
        middleware_dependant = get_middleware_dependant(
            middleware_class=middleware_class,
            name=middleware_class.__name__,
        )

        # Handle both old (dict) and new (provider) override patterns
        actual_provider: Any | None = None
        if dependency_overrides is not None:
            # Create a simple provider-like object for backward compatibility
            class SimpleOverrideProvider:
                def __init__(self, overrides: dict[type, Any]) -> None:
                    self.dependency_overrides = overrides

            actual_provider = SimpleOverrideProvider(dependency_overrides)
        elif dependency_overrides_provider is not None:
            actual_provider = dependency_overrides_provider

        # Solve the dependencies using FastAPI's dependency injection
        values: dict[str, Any] = {}
        if middleware_dependant.dependencies:
            values = solve_middleware_dependencies_sync(
                middleware_dependant=middleware_dependant,
                dependency_overrides_provider=actual_provider,
            )

        # Build kwargs for middleware instantiation
        kwargs: dict[str, Any] = {"app": app}

        # Add resolved dependency values
        kwargs.update(values)

        # Add non-dependency parameters with their defaults
        for param_name, param in params.items():
            if param_name in ("self", "app"):
                continue

            # Skip parameters that were already resolved as dependencies
            if param_name in values:
                continue

            # Check if there's a default value
            if param.default is not inspect.Parameter.empty:
                kwargs[param_name] = param.default

        return middleware_class(**kwargs)


# Global resolver instance
_resolver = MiddlewareDependencyResolver()


def resolve_middleware_dependencies(
    middleware_class: type,
    app: Any,
    dependency_overrides: dict[type, Any] | None = None,
    dependency_overrides_provider: Any | None = None,
) -> Any:
    """
    Resolve dependencies for a middleware class.

    This is a convenience function that uses the global resolver.

    Args:
        middleware_class: The middleware class to instantiate.
        app: The ASGI app to pass to the middleware.
        dependency_overrides: Optional dict to override dependencies (deprecated, use dependency_overrides_provider).
        dependency_overrides_provider: Optional provider for dependency overrides.

    Returns:
        An instance of the middleware with resolved dependencies.
    """
    return _resolver.resolve(
        middleware_class,
        app,
        dependency_overrides=dependency_overrides,
        dependency_overrides_provider=dependency_overrides_provider,
    )


__all__ = [
    "MiddlewareDependencyResolver",
    "resolve_middleware_dependencies",
]

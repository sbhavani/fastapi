"""
Middleware configuration dataclasses for FastAPI.

This module contains the MiddlewareConfig dataclass which stores
configuration for typed middleware including dependencies, ordering constraints,
and initialization parameters.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MiddlewareConfig:
    """
    Configuration for a typed middleware.

    This dataclass stores all configuration needed to register and initialize
    a typed middleware in the FastAPI application.

    Attributes:
        cls: The middleware class (must implement MiddlewareProtocol).
        dependencies: List of dependencies (as Depends() callables) to inject
            into the middleware.
        depends_on: Tuple of middleware classes that must run before this one.
            Used for compile-time ordering validation.
        kwargs: Additional keyword arguments for middleware initialization.

    Example:
        config = MiddlewareConfig(
            cls=AuthMiddleware,
            dependencies=[Depends(get_current_user)],
            depends_on=(LoggingMiddleware,),
            kwargs={"exclude_paths": ["/health"]}
        )
    """
    cls: type
    dependencies: list[Any] = field(default_factory=list)
    depends_on: tuple[type, ...] = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "MiddlewareConfig",
]

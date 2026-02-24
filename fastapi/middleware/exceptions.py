"""
Exception classes for typed middleware.
"""


class MiddlewareError(Exception):
    """Base exception for middleware-related errors."""
    pass


class OrderedMiddlewareError(MiddlewareError):
    """
    Raised when there are ordering conflicts between middleware.

    This can happen when:
    - There are circular dependencies in the middleware chain
    - Middleware have conflicting depends_on requirements
    - The middleware graph cannot be topologically sorted
    """

    def __init__(self, message: str, conflicts: list[str] | None = None) -> None:
        super().__init__(message)
        self.conflicts = conflicts or []

    def __str__(self) -> str:
        if self.conflicts:
            lines = [super().__str__()]
            lines.append("")
            lines.append("Conflicts detected:")
            for conflict in self.conflicts:
                lines.append(f"  - {conflict}")
            return "\n".join(lines)
        return super().__str__()


class MiddlewareDependencyError(MiddlewareError):
    """
    Raised when middleware dependencies cannot be resolved.

    This can happen when:
    - A dependency cannot be instantiated
    - A circular dependency is detected between middleware
    - A required dependency is missing
    """

    def __init__(
        self,
        message: str,
        middleware: type | None = None,
        dependency: type | None = None,
    ) -> None:
        super().__init__(message)
        self.middleware = middleware
        self.dependency = dependency


class MiddlewareTypeError(MiddlewareError):
    """
    Raised when middleware has invalid type annotations.

    This can happen when:
    - A middleware doesn't implement MiddlewareProtocol correctly
    - Type coercion fails
    - Request/Response types are incompatible
    """

    def __init__(
        self,
        message: str,
        expected_type: type | None = None,
        actual_type: type | None = None,
    ) -> None:
        super().__init__(message)
        self.expected_type = expected_type
        self.actual_type = actual_type


__all__ = [
    "MiddlewareError",
    "OrderedMiddlewareError",
    "MiddlewareDependencyError",
    "MiddlewareTypeError",
]

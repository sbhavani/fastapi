from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Generic, Sequence, TypeVar, get_type_hints

from fastapi.params import Depends
from typing_extensions import Protocol, Self

if TYPE_CHECKING:
    from fastapi import FastAPI
    from starlette.requests import Request
    from starlette.responses import Response


TRequest = TypeVar("TRequest")
TResponse = TypeVar("TResponse")
TDep = TypeVar("TDep")


__all__ = [
    # Protocol and context
    "MiddlewareProtocol",
    "MiddlewareContext",
    # Registration and container
    "MiddlewareRegistration",
    "DependencyContainer",
    "ConstructorParam",
    # Dependency functions
    "extract_constructor_params",
    "instantiate_middleware",
    # Decorators
    "priority",
    "before",
    "after",
    # Exceptions
    "MiddlewareError",
    "MiddlewareOrderingError",
    "MiddlewareDependencyError",
]


class MiddlewareProtocol(Protocol[TRequest, TResponse]):
    """Protocol defining typed middleware contract."""

    async def dispatch(
        self,
        context: MiddlewareContext[TRequest, TResponse],
    ) -> TResponse: ...


class MiddlewareError(Exception):
    """Base exception for typed middleware errors."""
    pass


class MiddlewareOrderingError(MiddlewareError):
    """Raised when middleware ordering constraints cannot be satisfied."""

    conflicting_middleware: tuple[str, str] | None

    def __init__(
        self,
        message: str,
        conflicting_middleware: tuple[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.conflicting_middleware = conflicting_middleware


class MiddlewareDependencyError(MiddlewareError):
    """Raised when middleware dependencies cannot be resolved."""

    middleware: str | None
    missing_dependencies: Sequence[str]

    def __init__(
        self,
        message: str,
        middleware: str | None = None,
        missing_dependencies: Sequence[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.middleware = middleware
        self.missing_dependencies = list(missing_dependencies) if missing_dependencies else []


class DependencyContainer(Generic[TDep]):
    """Type-safe dependency injection container for middleware."""

    def __init__(self) -> None:
        self._dependencies: dict[type[Any], Any] = {}

    def register(self, dependency_type: type[TDep], instance: TDep) -> None:
        """Register a dependency instance."""
        self._dependencies[dependency_type] = instance

    def get(self, dependency_type: type[TDep]) -> TDep:
        """Retrieve typed dependency."""
        if dependency_type not in self._dependencies:
            raise MiddlewareDependencyError(
                f"Dependency {dependency_type} not registered",
            )
        return self._dependencies[dependency_type]

    def has(self, dependency_type: type[Any]) -> bool:
        """Check if a dependency is registered."""
        return dependency_type in self._dependencies

    def validate(self) -> None:
        """Validate all dependencies are available. No-op for runtime validation."""
        pass


@dataclass
class ConstructorParam:
    """Represents a constructor parameter for a middleware class."""

    name: str
    type: type[Any]
    has_default: bool
    default: Any
    is_depends: bool
    depends_dependency: Callable[..., Any] | None


def extract_constructor_params(
    middleware_class: type[MiddlewareProtocol[Any, Any]],
) -> list[ConstructorParam]:
    """Extract constructor parameters from a middleware class.

    Returns a list of ConstructorParam objects describing each parameter
    that can be injected via FastAPI's dependency injection.
    """
    params: list[ConstructorParam] = []

    try:
        # Get the __init__ method
        init_method = middleware_class.__init__

        # Get type hints
        try:
            hints = get_type_hints(init_method)
        except Exception:
            hints = {}

        # Get signature
        sig = inspect.signature(init_method)

        for param_name, param in sig.parameters.items():
            # Skip self/cls
            if param_name in ("self", "cls"):
                continue

            # Skip *args and **kwargs
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue

            # Get the type annotation
            annotation = param.annotation
            if annotation is inspect.Parameter.empty:
                # Try to get from type hints
                annotation = hints.get(param_name, Any)

            # Check if it's a Depends
            is_depends = isinstance(param.default, Depends)
            depends_dependency = param.default.dependency if is_depends else None

            params.append(ConstructorParam(
                name=param_name,
                type=annotation,
                has_default=param.default is not inspect.Parameter.empty,
                default=param.default if param.default is not inspect.Parameter.empty else None,
                is_depends=is_depends,
                depends_dependency=depends_dependency,
            ))

    except (ValueError, TypeError, AttributeError):
        pass

    return params


def instantiate_middleware(
    middleware_class: type[MiddlewareProtocol[Any, Any]],
    container: DependencyContainer[Any],
    dependency_overrides: dict[type[Any], Callable[..., Any]] | None = None,
) -> MiddlewareProtocol[Any, Any]:
    """Instantiate a middleware class with resolved dependencies.

    Args:
        middleware_class: The middleware class to instantiate
        container: The dependency container with registered dependencies
        dependency_overrides: Optional dict mapping types to override functions

    Returns:
        An instance of the middleware class

    Raises:
        MiddlewareDependencyError: If a dependency cannot be resolved
    """
    if dependency_overrides is None:
        dependency_overrides = {}

    params = extract_constructor_params(middleware_class)
    kwargs: dict[str, Any] = {}

    for param in params:
        # Check for override first
        if param.type in dependency_overrides:
            kwargs[param.name] = dependency_overrides[param.type]()
            continue

        # Check if it's an explicit Depends with a dependency function
        if param.is_depends and param.depends_dependency is not None:
            try:
                # Call the dependency function to get the instance
                kwargs[param.name] = param.depends_dependency()
            except Exception as e:
                raise MiddlewareDependencyError(
                    f"Failed to resolve dependency '{param.name}' for {middleware_class.__name__}: {e}",
                    middleware=middleware_class.__name__,
                    missing_dependencies=[param.name],
                ) from e
            continue

        # Try to get from container
        try:
            kwargs[param.name] = container.get(param.type)
        except MiddlewareDependencyError:
            # If no default and not in container, that's an error
            if not param.has_default:
                raise MiddlewareDependencyError(
                    f"Cannot resolve dependency '{param.name}' of type {param.type} "
                    f"for {middleware_class.__name__}. Either register it or provide a default value.",
                    middleware=middleware_class.__name__,
                    missing_dependencies=[param.name],
                )

    # Create the instance
    try:
        return middleware_class(**kwargs)
    except TypeError as e:
        raise MiddlewareDependencyError(
            f"Failed to instantiate {middleware_class.__name__}: {e}",
            middleware=middleware_class.__name__,
        ) from e


@dataclass
class MiddlewareRegistration(Generic[TRequest, TResponse]):
    """Configuration for registering middleware with ordering constraints."""

    middleware_class: type[MiddlewareProtocol[TRequest, TResponse]]
    constructor_params: Sequence[ConstructorParam] = field(default_factory=list)
    priority: int = 0
    before: Sequence[str] = field(default_factory=list)
    after: Sequence[str] = field(default_factory=list)
    name: str | None = None
    dependency_container: DependencyContainer[Any] | None = None

    def __post_init__(self) -> None:
        if self.name is None:
            self.name = self.middleware_class.__name__


class MiddlewareContext(Generic[TRequest, TResponse]):
    """Type-safe context for middleware execution."""

    def __init__(
        self,
        request: TRequest,
        response: TResponse,
        dependencies: DependencyContainer[Any],
        app: FastAPI,
    ) -> None:
        self._request = request
        self._response = response
        self._dependencies = dependencies
        self._app = app

    @property
    def request(self) -> TRequest:
        """The incoming request (fully typed)."""
        return self._request

    @property
    def response(self) -> TResponse:
        """The response object (fully typed)."""
        return self._response

    def set_response(self, response: TResponse) -> None:
        """Set the response object."""
        self._response = response

    def get_dependency(self, dependency_type: type[TDep]) -> TDep:
        """Get typed dependency from container."""
        return self._dependencies.get(dependency_type)

    @property
    def app(self) -> FastAPI:
        """Reference to the application instance."""
        return self._app

    # Type-safe request accessors

    @property
    def method(self) -> str:
        """HTTP method (e.g., 'GET', 'POST')."""
        from starlette.requests import Request

        if isinstance(self._request, Request):
            return self._request.method
        return getattr(self._request, "method", "")  # type: ignore[return-value]

    @property
    def path(self) -> str:
        """Request path."""
        from starlette.requests import Request

        if isinstance(self._request, Request):
            return self._request.url.path
        return getattr(self._request, "path", "")  # type: ignore[return-value]

    @property
    def url(self) -> "URL":
        """Full URL of the request."""
        from starlette.requests import Request
        from starlette.datastructures import URL

        if isinstance(self._request, Request):
            return self._request.url
        return getattr(self._request, "url", URL("/"))  # type: ignore[return-value]

    @property
    def headers(self) -> "Headers":
        """Request headers."""
        from starlette.requests import Request
        from starlette.datastructures import Headers

        if isinstance(self._request, Request):
            return self._request.headers
        return getattr(self._request, "headers", Headers())  # type: ignore[return-value]

    @property
    def query_params(self) -> "QueryParams":
        """Query parameters."""
        from starlette.requests import Request
        from starlette.datastructures import QueryParams

        if isinstance(self._request, Request):
            return self._request.query_params
        return getattr(self._request, "query_params", QueryParams())  # type: ignore[return-value]

    @property
    def path_params(self) -> dict[str, Any]:
        """Path parameters."""
        from starlette.requests import Request

        if isinstance(self._request, Request):
            return self._request.path_params
        return getattr(self._request, "path_params", {})  # type: ignore[return-value]

    @property
    def state(self) -> "State":
        """Request state for sharing data between middleware."""
        from starlette.requests import Request
        from starlette.datastructures import State

        if isinstance(self._request, Request):
            return self._request.state
        # Fallback for custom request types
        if hasattr(self._request, "state"):
            return self._request.state  # type: ignore[return-value]
        return State()  # type: ignore[return-value]

    @property
    def client(self) -> tuple[str, int] | None:
        """Client address (host, port)."""
        from starlette.requests import Request

        if isinstance(self._request, Request):
            return self._request.client
        return getattr(self._request, "client", None)  # type: ignore[return-value]

    # Type-safe response accessors

    @property
    def status_code(self) -> int:
        """Response status code."""
        from starlette.responses import Response

        if isinstance(self._response, Response):
            return self._response.status_code
        return getattr(self._response, "status_code", 200)  # type: ignore[return-value]

    def set_status_code(self, status_code: int) -> None:
        """Set response status code."""
        from starlette.responses import Response

        if isinstance(self._response, Response):
            self._response.status_code = status_code
        elif hasattr(self._response, "status_code"):
            self._response.status_code = status_code

    @property
    def response_headers(self) -> dict[str, str]:
        """Response headers as a dictionary."""
        from starlette.responses import Response

        if isinstance(self._response, Response):
            # Response.headers is a MutableMultiDict
            return dict(self._response.headers)
        if hasattr(self._response, "headers"):
            return dict(self._response.headers)  # type: ignore[return-value]
        return {}

    def set_header(self, name: str, value: str) -> None:
        """Set a response header."""
        from starlette.responses import Response

        if isinstance(self._response, Response):
            self._response.headers[name] = value
        elif hasattr(self._response, "headers"):
            self._response.headers[name] = value

    def add_header(self, name: str, value: str) -> None:
        """Add a response header (appends if already exists)."""
        from starlette.responses import Response

        if isinstance(self._response, Response):
            self._response.headers.append(name, value)
        elif hasattr(self._response, "headers"):
            existing = self._response.headers.get(name, "")
            if existing:
                self._response.headers[name] = f"{existing}, {value}"
            else:
                self._response.headers[name] = value

    def set_body(self, body: bytes | str) -> None:
        """Set response body."""
        from starlette.responses import Response

        if isinstance(self._response, Response):
            if isinstance(body, str):
                body = body.encode()
            self._response.body = body
        elif hasattr(self._response, "body"):
            self._response.body = body


def priority(value: int) -> Callable[[type[Self]], type[Self]]:
    """Set middleware priority (higher = runs first)."""
    def decorator(cls: type[Self]) -> type[Self]:
        cls.__middleware_priority__ = value  # type: ignore[attr-defined]
        return cls
    return decorator


def before(*middleware_names: str) -> Callable[[type[Self]], type[Self]]:
    """Declare this middleware must run before named middleware."""
    def decorator(cls: type[Self]) -> type[Self]:
        if not hasattr(cls, "__middleware_before__"):
            cls.__middleware_before__ = []  # type: ignore[attr-defined]
        cls.__middleware_before__.extend(middleware_names)  # type: ignore[union-attr]
        return cls
    return decorator


def after(*middleware_names: str) -> Callable[[type[Self]], type[Self]]:
    """Declare this middleware must run after named middleware."""
    def decorator(cls: type[Self]) -> type[Self]:
        if not hasattr(cls, "__middleware_after__"):
            cls.__middleware_after__ = []  # type: ignore[attr-defined]
        cls.__middleware_after__.extend(middleware_names)  # type: ignore[union-attr]
        return cls
    return decorator


_typed_middleware_registry: dict[str, MiddlewareRegistration[Any, Any]] = {}


def validate_ordering_constraints(
    registrations: dict[str, MiddlewareRegistration[Any, Any]],
    new_registration: MiddlewareRegistration[Any, Any],
) -> None:
    """Validate that ordering constraints are satisfiable."""
    if not new_registration.name:
        return

    all_names = set(registrations.keys()) | {new_registration.name}

    # Check before constraints
    for target in new_registration.before:
        if target not in all_names:
            raise MiddlewareOrderingError(
                f"Middleware '{new_registration.name}' specifies 'before: {target}' "
                f"but middleware '{target}' does not exist",
                conflicting_middleware=(new_registration.name, target),
            )

    # Check after constraints
    for target in new_registration.after:
        if target not in all_names:
            raise MiddlewareOrderingError(
                f"Middleware '{new_registration.name}' specifies 'after: {target}' "
                f"but middleware '{target}' does not exist",
                conflicting_middleware=(new_registration.name, target),
            )

    # Check for circular dependencies
    _check_circular_dependencies(registrations, new_registration)


def _check_circular_dependencies(
    registrations: dict[str, MiddlewareRegistration[Any, Any]],
    new_registration: MiddlewareRegistration[Any, Any],
) -> None:
    """Check for circular ordering dependencies."""
    if not new_registration.name:
        return

    # Build graph
    graph: dict[str, set[str]] = {name: set() for name in registrations}
    graph[new_registration.name] = set()

    for name, reg in registrations.items():
        for target in reg.before:
            if target in graph:
                graph[target].add(name)
        for target in reg.after:
            if name in graph:
                graph[name].add(target)

    # Add new edges from new registration
    for target in new_registration.before:
        if target in graph:
            graph[target].add(new_registration.name)
    for target in new_registration.after:
        if new_registration.name in graph:
            graph[new_registration.name].add(target)

    # DFS to detect cycles
    visited: set[str] = set()
    rec_stack: set[str] = set()

    def has_cycle(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)

        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                if has_cycle(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    for node in graph:
        if node not in visited:
            if has_cycle(node):
                raise MiddlewareOrderingError(
                    f"Circular dependency detected in middleware ordering",
                    conflicting_middleware=(new_registration.name, node),
                )


def extract_dependencies(
    middleware_class: type[MiddlewareProtocol[Any, Any]],
) -> list[Depends]:
    """Extract dependency specifications from middleware constructor."""
    import inspect

    dependencies: list[Depends] = []

    try:
        sig = inspect.signature(middleware_class.__init__)
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            if param.annotation is inspect.Parameter.empty:
                continue

            default = param.default
            if isinstance(default, Depends):
                dependencies.append(default)
            elif default is inspect.Parameter.empty:
                # This is likely an injected dependency without explicit Depends
                # We'll handle this in dependency resolution
                pass
    except (ValueError, TypeError):
        pass

    return dependencies


def resolve_dependencies(
    middleware_class: type[MiddlewareProtocol[Any, Any]],
    container: DependencyContainer[Any],
) -> dict[type[Any], Any]:
    """Resolve dependencies for a middleware class."""
    import inspect
    from fastapi.dependencies.utils import solve_dependencies

    resolved: dict[type[Any], Any] = {}

    try:
        hints = get_type_hints(middleware_class.__init__)
    except Exception:
        hints = {}

    try:
        sig = inspect.signature(middleware_class.__init__)
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            if param.annotation is inspect.Parameter.empty:
                continue

            ann = hints.get(param_name, param.annotation)

            # Check if it's a Depends
            if isinstance(param.default, Depends):
                # For explicit Depends, we'll store the info for FastAPI to resolve
                resolved[ann] = param.default
            else:
                # Try to resolve from container or create placeholder
                try:
                    resolved[ann] = container.get(ann)
                except MiddlewareDependencyError:
                    # We'll create a placeholder that FastAPI can fill in
                    resolved[ann] = None

    except (ValueError, TypeError):
        pass

    return resolved

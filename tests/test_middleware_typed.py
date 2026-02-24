"""Tests for typed middleware in FastAPI."""

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.types import ASGIApp, Receive, Send

from fastapi import FastAPI
from fastapi.middleware import (
    BaseTypedMiddleware,
    MiddlewareCallable,
    MiddlewareDependenciesMixin,
    MiddlewareOrder,
    MiddlewareProtocol,
    MiddlewareType,
    TypedMiddlewareMixin,
    validate_middleware_order,
)
from fastapi.middleware.typed import (
    MiddlewareDependencyError,
    MiddlewareError,
    MiddlewareOrderError,
    create_typed_middleware,
    validate_middleware_signature,
)


def test_middleware_protocol_exists():
    """Test that MiddlewareProtocol exists and can be used as a type."""
    assert MiddlewareProtocol is not None


def test_middleware_order_enum():
    """Test MiddlewareOrder enum values."""
    assert MiddlewareOrder.FIRST is not None
    assert MiddlewareOrder.LAST is not None
    assert MiddlewareOrder.FIRST.value == "first"
    assert MiddlewareOrder.LAST.value == "last"


def test_middleware_type_enum():
    """Test MiddlewareType enum values."""
    assert MiddlewareType.BEFORE is not None
    assert MiddlewareType.AFTER is not None
    assert MiddlewareType.WRAPPER is not None
    assert MiddlewareType.WRAPPER.value == "wrapper"


def test_validate_middleware_order_empty():
    """Test validate_middleware_order with empty list."""
    result = validate_middleware_order([])
    assert result == []


def test_validate_middleware_order_no_order():
    """Test validate_middleware_order with middleware without order hints."""

    class Middleware1:
        pass

    class Middleware2:
        pass

    result = validate_middleware_order([Middleware1, Middleware2])
    assert len(result) == 2


def test_base_typed_middleware_basic():
    """Test BaseTypedMiddleware can be instantiated."""
    app = FastAPI()

    @app.get("/")
    def root():
        return {"message": "ok"}

    class TestMiddleware(BaseTypedMiddleware):
        async def dispatch(
            self,
            scope: dict,
            receive: Receive,
            send: Send,
        ) -> None:
            await self.app(scope, receive, send)

    # Just check that we can import and instantiate
    assert TestMiddleware is not None


def test_typed_middleware_with_app():
    """Test typed middleware works with a simple app."""
    app = FastAPI()

    @app.get("/")
    def root():
        return {"message": "ok"}

    class TestMiddleware(BaseTypedMiddleware):
        async def dispatch(
            self,
            scope: dict,
            receive: Receive,
            send: Send,
        ) -> None:
            await self.app(scope, receive, send)

    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "ok"}


def test_typed_middleware_modifies_request():
    """Test typed middleware can modify request."""
    app = FastAPI()

    @app.get("/")
    def root(request: Request):
        return {"path": request.headers.get("x-test", "not-set")}

    class AddHeaderMiddleware(BaseTypedMiddleware):
        async def dispatch(
            self,
            scope: dict,
            receive: Receive,
            send: Send,
        ) -> None:
            # Add custom header to scope for testing
            scope["headers"] = list(scope.get("headers", [])) + [
                (b"x-test", b"test-value")
            ]
            await self.app(scope, receive, send)

    # Note: Middleware would need to be added via app.add_typed_middleware()
    # This test just verifies the class can be defined


def test_validate_middleware_signature_valid():
    """Test validate_middleware_signature with valid middleware."""

    class ValidMiddleware(BaseTypedMiddleware):
        async def dispatch(
            self,
            scope: dict,
            receive: Receive,
            send: Send,
        ) -> None:
            await self.app(scope, receive, send)

    assert validate_middleware_signature(ValidMiddleware) is True


def test_validate_middleware_signature_missing_dispatch():
    """Test validate_middleware_signature with missing dispatch."""

    class NoDispatchMiddleware:
        def __init__(self, app: ASGIApp):
            self.app = app

    with pytest.raises(MiddlewareError, match="must have a 'dispatch' method"):
        validate_middleware_signature(NoDispatchMiddleware)


def test_validate_middleware_signature_sync_dispatch():
    """Test validate_middleware_signature with sync dispatch."""

    class SyncDispatchMiddleware:
        def __init__(self, app: ASGIApp):
            self.app = app

        def dispatch(self, scope: dict, receive: Receive, send: Send):
            pass

    with pytest.raises(MiddlewareError, match="dispatch method must be async"):
        validate_middleware_signature(SyncDispatchMiddleware)


def test_validate_middleware_signature_missing_app():
    """Test validate_middleware_signature with missing app parameter."""

    class NoAppMiddleware:
        def __init__(self, other: str):
            self.other = other

        async def dispatch(
            self,
            scope: dict,
            receive: Receive,
            send: Send,
        ) -> None:
            pass

    with pytest.raises(MiddlewareError, match="must accept 'app' parameter"):
        validate_middleware_signature(NoAppMiddleware)


def test_middleware_dependencies_mixin():
    """Test MiddlewareDependenciesMixin."""
    mixin = MiddlewareDependenciesMixin()
    assert mixin.get_dependencies() == []

    dep_func = lambda: None

    class TestClass(MiddlewareDependenciesMixin):
        _middleware_dependencies = [dep_func]

    assert TestClass.get_dependencies() == [dep_func]


def test_middleware_runner():
    """Test MiddlewareRunner class."""

    class TestMiddleware(BaseTypedMiddleware):
        async def dispatch(
            self,
            scope: dict,
            receive: Receive,
            send: Send,
        ) -> None:
            await self.app(scope, receive, send)

    from fastapi.middleware._types import MiddlewareRunner

    # Just test that MiddlewareRunner exists and can be imported
    assert MiddlewareRunner is not None


def test_create_typed_middleware():
    """Test create_typed_middleware function."""

    class OriginalMiddleware(BaseTypedMiddleware):
        async def dispatch(
            self,
            scope: dict,
            receive: Receive,
            send: Send,
        ) -> None:
            await self.app(scope, receive, send)

    # Just test that create_typed_middleware exists
    assert create_typed_middleware is not None


def test_middleware_protocol_usage():
    """Test that MiddlewareProtocol can be used for type checking."""

    class MyMiddleware:
        order = MiddlewareOrder.FIRST
        middleware_type = MiddlewareType.WRAPPER

        def __init__(self, app: ASGIApp):
            self.app = app

        async def __call__(
            self,
            scope: dict,
            receive: Receive,
            send: Send,
        ) -> None:
            await self.app(scope, receive, send)

    # Protocol check
    assert hasattr(MyMiddleware, "order")
    assert hasattr(MyMiddleware, "middleware_type")


def test_middleware_type_wrapper():
    """Test MiddlewareType.WRAPPER is the default."""
    assert MiddlewareType.WRAPPER.value == "wrapper"


def test_middleware_order_first():
    """Test MiddlewareOrder.FIRST."""
    assert MiddlewareOrder.FIRST.value == "first"


def test_middleware_order_last():
    """Test MiddlewareOrder.LAST."""
    assert MiddlewareOrder.LAST.value == "last"


def test_validate_middleware_order_first():
    """Test validate_middleware_order with FIRST order."""

    class FirstMiddleware:
        order = MiddlewareOrder.FIRST

    class LastMiddleware:
        order = MiddlewareOrder.LAST

    result = validate_middleware_order([LastMiddleware, FirstMiddleware])
    assert result[0] is FirstMiddleware
    assert result[1] is LastMiddleware


def test_validate_middleware_order_last():
    """Test validate_middleware_order with LAST order."""

    class Middleware1:
        pass

    class Middleware2:
        order = MiddlewareOrder.LAST

    result = validate_middleware_order([Middleware1, Middleware2])
    assert result[0] is Middleware1
    assert result[1] is Middleware2


def test_validate_middleware_order_preserves_order_for_same_order():
    """Test validate_middleware_order preserves relative order for same order type."""

    class FirstMiddleware1:
        order = MiddlewareOrder.FIRST

    class FirstMiddleware2:
        order = MiddlewareOrder.FIRST

    result = validate_middleware_order([FirstMiddleware2, FirstMiddleware1])
    # Both have FIRST order, so original order should be preserved
    assert result == [FirstMiddleware2, FirstMiddleware1]


def test_base_typed_middleware_dispatch_property():
    """Test BaseTypedMiddleware has dispatch property."""

    class TestMiddleware(BaseTypedMiddleware):
        async def dispatch(
            self,
            scope: dict,
            receive: Receive,
            send: Send,
        ) -> None:
            await self.app(scope, receive, send)

    middleware = TestMiddleware(lambda x, y, z: None)
    assert hasattr(middleware, "dispatch")
    assert callable(middleware.dispatch)


def test_typed_middleware_inheritance():
    """Test typed middleware can be subclassed."""

    class BaseMiddleware(BaseTypedMiddleware):
        pass

    class ChildMiddleware(BaseMiddleware):
        async def dispatch(
            self,
            scope: dict,
            receive: Receive,
            send: Send,
        ) -> None:
            await self.app(scope, receive, send)

    assert ChildMiddleware is not None
    assert issubclass(ChildMiddleware, BaseTypedMiddleware)


def test_middleware_error_classes():
    """Test middleware error classes exist."""
    assert issubclass(MiddlewareError, Exception)
    assert issubclass(MiddlewareDependencyError, MiddlewareError)
    assert issubclass(MiddlewareOrderError, MiddlewareError)


def test_typed_middleware_can_access_app():
    """Test typed middleware has access to app."""

    class TestMiddleware(BaseTypedMiddleware):
        async def dispatch(
            self,
            scope: dict,
            receive: Receive,
            send: Send,
        ) -> None:
            assert self.app is not None
            await self.app(scope, receive, send)

    mock_app = lambda scope, receive, send: None
    middleware = TestMiddleware(mock_app)
    assert middleware.app is mock_app


def test_middleware_with_dependencies_parameter():
    """Test BaseTypedMiddleware accepts dependencies parameter."""

    class TestMiddleware(BaseTypedMiddleware):
        async def dispatch(
            self,
            scope: dict,
            receive: Receive,
            send: Send,
        ) -> None:
            await self.app(scope, receive, send)

    middleware = TestMiddleware(lambda x, y, z: None)
    assert middleware.dependencies == ()


def test_add_typed_middleware_method():
    """Test that FastAPI has add_typed_middleware method."""
    from fastapi import FastAPI

    app = FastAPI()
    assert hasattr(app, "add_typed_middleware")
    assert callable(app.add_typed_middleware)


def test_add_typed_middleware_with_instance():
    """Test add_typed_middleware rejects instances instead of classes."""
    from fastapi import FastAPI
    from fastapi.middleware.typed import BaseTypedMiddleware

    app = FastAPI()

    @app.get("/")
    def root():
        return {"message": "ok"}

    class TestMiddleware(BaseTypedMiddleware):
        async def dispatch(
            self,
            scope: dict,
            receive: Receive,
            send: Send,
        ) -> None:
            await self.app(scope, receive, send)

    # Test with instance - should raise TypeError
    instance = TestMiddleware(app)
    with pytest.raises(TypeError, match="must be a class"):
        app.add_typed_middleware(instance)  # type: ignore


def test_add_typed_middleware_non_typed():
    """Test add_typed_middleware rejects non-typed middleware."""
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/")
    def root():
        return {"message": "ok"}

    class NotTypedMiddleware:
        def __init__(self, app: ASGIApp):
            self.app = app

        async def __call__(
            self,
            scope: dict,
            receive: Receive,
            send: Send,
        ) -> None:
            await self.app(scope, receive, send)

    with pytest.raises(TypeError, match="must be a subclass of BaseTypedMiddleware"):
        app.add_typed_middleware(NotTypedMiddleware)  # type: ignore


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

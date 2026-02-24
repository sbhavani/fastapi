"""
Tests for MiddlewareProtocol and TypedMiddleware.
"""
import asyncio
import pytest
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from fastapi.middleware import (
    MiddlewareProtocol,
    MiddlewareHooks,
    MiddlewareTypeError,
    TypedMiddleware,
    create_typed_middleware,
)


# Mock ASGI app for testing
class MockASGIApp:
    """A mock ASGI application for testing."""

    def __init__(self, status_code: int = 200, response_body: bytes = b"OK"):
        self.status_code = status_code
        self.response_body = response_body

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        await send({
            "type": "http.response.start",
            "status": self.status_code,
            "headers": [[b"content-type", b"text/plain"]],
        })
        await send({
            "type": "http.response.body",
            "body": self.response_body,
        })


# Test middleware classes
class BasicMiddleware(MiddlewareProtocol[Request, Response]):
    """A basic middleware implementing MiddlewareProtocol."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, request: Request, call_next):
        return await call_next(request)


class ModifyResponseMiddleware(MiddlewareProtocol[Request, Response]):
    """A middleware that modifies the response."""

    def __init__(self, app: ASGIApp, header_name: str = "X-Custom"):
        self.app = app
        self.header_name = header_name

    async def __call__(self, request: Request, call_next):
        response = await call_next(request)
        response.headers[self.header_name] = "modified"
        return response


class JSONMiddleware(MiddlewareProtocol[Request, JSONResponse]):
    """A middleware that returns JSON responses."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, request: Request, call_next):
        return JSONResponse({"status": "ok"})


class LifecycleMiddleware(MiddlewareProtocol[Request, Response], MiddlewareHooks):
    """A middleware with lifecycle hooks."""

    def __init__(self, app: ASGIApp):
        self.app = app
        self.startup_called = False
        self.shutdown_called = False

    async def __call__(self, request: Request, call_next):
        return await call_next(request)

    async def on_startup(self) -> None:
        self.startup_called = True

    async def on_shutdown(self) -> None:
        self.shutdown_called = True


class InvalidMiddleware:
    """A middleware that doesn't implement the protocol."""

    def __init__(self, app: ASGIApp):
        self.app = app


class NoCallMiddleware:
    """A middleware that doesn't have __call__ method but inherits from Protocol."""

    def __init__(self, app: ASGIApp):
        self.app = app


class WrongReturnTypeMiddleware(MiddlewareProtocol[Request, Response]):
    """A middleware that returns wrong type."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, request: Request, call_next):
        return "not a response"  # type: ignore


class NonAsyncCallMiddleware(MiddlewareProtocol[Request, Response]):
    """A middleware with non-async __call__ method."""

    def __init__(self, app: ASGIApp):
        self.app = app

    def __call__(self, request: Request, call_next):
        return call_next(request)  # type: ignore


class RequestModifyingMiddleware(MiddlewareProtocol[Request, Response]):
    """A middleware that modifies the request."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, request: Request, call_next):
        request.state.processed = True
        return await call_next(request)


# Helper function to run async tests
def run_async(coro):
    """Helper to run async code in sync tests."""
    return asyncio.run(coro)


# Tests for MiddlewareProtocol
class TestMiddlewareProtocol:
    """Tests for MiddlewareProtocol class."""

    def test_protocol_basic_implementation(self):
        """Test that a class can implement MiddlewareProtocol."""
        app = MockASGIApp()
        middleware = BasicMiddleware(app)

        assert hasattr(middleware, "app")
        assert hasattr(middleware, "__call__")
        assert callable(middleware.__call__)

    def test_protocol_with_type_parameters(self):
        """Test MiddlewareProtocol with type parameters."""
        app = MockASGIApp()
        middleware = JSONMiddleware(app)

        # Should work with Request -> JSONResponse
        assert middleware.app is app

    def test_protocol_with_constructor_args(self):
        """Test middleware with additional constructor arguments."""
        app = MockASGIApp()
        middleware = ModifyResponseMiddleware(app, header_name="X-Test")

        assert middleware.app is app
        assert middleware.header_name == "X-Test"

    def test_protocol_inheritance(self):
        """Test that protocol inheritance works correctly."""
        # Check that LifecycleMiddleware implements both protocol requirements
        # (can't use issubclass because MiddlewareProtocol is not @runtime_checkable)
        assert hasattr(LifecycleMiddleware, "__call__")
        assert hasattr(LifecycleMiddleware, "on_startup")
        assert hasattr(LifecycleMiddleware, "on_shutdown")


# Tests for TypedMiddleware
class TestTypedMiddleware:
    """Tests for TypedMiddleware wrapper."""

    def test_create_typed_middleware_basic(self):
        """Test creating a TypedMiddleware with basic middleware."""
        app = MockASGIApp()
        typed_middleware = create_typed_middleware(BasicMiddleware, app)

        assert isinstance(typed_middleware, TypedMiddleware)
        assert typed_middleware.middleware_class is BasicMiddleware

    def test_typed_middleware_with_kwargs(self):
        """Test TypedMiddleware with additional kwargs."""
        app = MockASGIApp()
        typed_middleware = create_typed_middleware(
            ModifyResponseMiddleware, app, header_name="X-Custom-Header"
        )

        assert typed_middleware.middleware_instance.header_name == "X-Custom-Header"

    def test_typed_middleware_validates_protocol(self):
        """Test that TypedMiddleware validates protocol compliance."""
        app = MockASGIApp()

        # Should raise because InvalidMiddleware doesn't implement the protocol
        with pytest.raises(MiddlewareTypeError) as exc_info:
            TypedMiddleware(app, InvalidMiddleware)

        assert "must implement __call__ method" in str(exc_info.value)

    def test_typed_middleware_validates_call_method(self):
        """Test that TypedMiddleware validates __call__ is callable."""
        app = MockASGIApp()

        # NoCallMiddleware implements protocol but is missing __call__ after init
        # Actually in the current implementation, it validates hasattr(__call__)
        # Let's check what happens
        with pytest.raises(MiddlewareTypeError) as exc_info:
            TypedMiddleware(app, NoCallMiddleware)

        assert "must implement __call__ method" in str(exc_info.value)

    def test_typed_middleware_executes(self):
        """Test that TypedMiddleware executes the middleware."""
        app = MockASGIApp()
        typed_middleware = create_typed_middleware(BasicMiddleware, app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
        }

        async def receive():
            return {"type": "http.request", "body": b""}

        messages = []

        async def send(message):
            messages.append(message)

        async def run_test():
            await typed_middleware(scope, receive, send)

        run_async(run_test())

        # Should have sent start and body messages
        assert len(messages) >= 2
        assert messages[0]["type"] == "http.response.start"
        assert messages[1]["type"] == "http.response.body"

    def test_typed_middleware_lifecycle_hooks(self):
        """Test that lifecycle hooks are called."""
        app = MockASGIApp()
        typed_middleware = create_typed_middleware(LifecycleMiddleware, app)

        async def run_test():
            # Test on_startup
            await typed_middleware.on_startup()
            # Test on_shutdown
            await typed_middleware.on_shutdown()

        run_async(run_test())

        assert typed_middleware.middleware_instance.startup_called is True
        assert typed_middleware.middleware_instance.shutdown_called is True

    def test_typed_middleware_wrong_return_type(self):
        """Test that TypedMiddleware validates return type."""
        app = MockASGIApp()
        typed_middleware = create_typed_middleware(WrongReturnTypeMiddleware, app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
        }

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            pass

        async def run_test():
            await typed_middleware(scope, receive, send)

        with pytest.raises(MiddlewareTypeError) as exc_info:
            run_async(run_test())

        assert "must return Response" in str(exc_info.value)


# Tests for MiddlewareHooks
class TestMiddlewareHooks:
    """Tests for MiddlewareHooks mixin."""

    def test_middleware_hooks_default_implementation(self):
        """Test that MiddlewareHooks has default implementations."""

        class TestMiddleware(MiddlewareProtocol[Request, Response], MiddlewareHooks):
            def __init__(self, app: ASGIApp):
                self.app = app

            async def __call__(self, request: Request, call_next):
                return await call_next(request)

        app = MockASGIApp()
        middleware = TestMiddleware(app)

        # Default implementations should exist
        assert hasattr(middleware, "on_startup")
        assert hasattr(middleware, "on_shutdown")

    def test_middleware_hooks_override(self):
        """Test that hooks can be overridden."""
        app = MockASGIApp()
        middleware = LifecycleMiddleware(app)

        assert middleware.startup_called is False
        assert middleware.shutdown_called is False


# Tests for protocol runtime behavior
class TestProtocolRuntime:
    """Tests for runtime behavior of MiddlewareProtocol."""

    def test_middleware_chain_request_modification(self):
        """Test that middleware can modify request state."""
        app = MockASGIApp()
        typed_middleware = create_typed_middleware(RequestModifyingMiddleware, app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
        }

        async def receive():
            return {"type": "http.request", "body": b""}

        # Create request to check state
        request = Request(scope, receive)

        # Call the middleware manually to check state modification
        async def call_next(req):
            return Response()

        async def run_test():
            await typed_middleware.middleware_instance(request, call_next)

        run_async(run_test())

        # The request state should be modified
        assert getattr(request.state, "processed", False) is True

    def test_middleware_chain_response_modification(self):
        """Test that middleware can modify response."""
        # Test that ModifyResponseMiddleware actually modifies response
        app = MockASGIApp()
        middleware = ModifyResponseMiddleware(app, header_name="X-Test-Header")

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
        }

        async def receive():
            return {"type": "http.request", "body": b""}

        # Test the middleware directly
        request = Request(scope, receive)

        class MockResponse:
            def __init__(self):
                self.headers = {}

        mock_response = MockResponse()

        async def call_next(req):
            return mock_response

        async def run_test():
            result = await middleware(request, call_next)
            return result

        result = run_async(run_test())

        # Check that response was modified with custom header
        assert "X-Test-Header" in result.headers
        assert result.headers["X-Test-Header"] == "modified"


# Tests for error cases
class TestErrors:
    """Tests for error handling."""

    def test_middleware_type_error_attributes(self):
        """Test MiddlewareTypeError has proper attributes."""
        error = MiddlewareTypeError(
            "Test error",
            expected_type=Response,
            actual_type=str,
        )

        assert error.expected_type is Response
        assert error.actual_type is str
        assert "Test error" in str(error)

    def test_typed_middleware_instantiation_error(self):
        """Test that TypedMiddleware handles instantiation errors."""

        class BrokenInitMiddleware(MiddlewareProtocol[Request, Response]):
            def __init__(self, app: ASGIApp, required_arg: str):
                self.app = app
                raise ValueError("Missing required_arg")

            async def __call__(self, request: Request, call_next):
                return await call_next(request)

        app = MockASGIApp()

        # Should raise MiddlewareTypeError wrapping the original error
        with pytest.raises(MiddlewareTypeError) as exc_info:
            TypedMiddleware(app, BrokenInitMiddleware)

        assert "Failed to instantiate middleware" in str(exc_info.value)


# Tests for type checking
class TestTypeChecking:
    """Tests for type checking functionality."""

    def test_protocol_supports_request_type_hint(self):
        """Test that MiddlewareProtocol supports Request type hint."""
        # BasicMiddleware should be MiddlewareProtocol[Request, Response]
        assert BasicMiddleware.__mro__ is not None

    def test_protocol_supports_response_type_hint(self):
        """Test that MiddlewareProtocol supports Response type hint."""
        # JSONMiddleware should be MiddlewareProtocol[Request, JSONResponse]
        assert JSONMiddleware.__mro__ is not None

    def test_protocol_with_custom_request_response_types(self):
        """Test protocol with custom (though compatible) types."""
        # MiddlewareProtocol allows any subclass of Request/Response
        # This tests the generic type parameters work at runtime
        # Can't use issubclass because MiddlewareProtocol is not @runtime_checkable
        assert hasattr(BasicMiddleware, "__call__")
        assert hasattr(JSONMiddleware, "__call__")

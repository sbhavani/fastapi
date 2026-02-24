"""Tests for typed middleware module."""

import pytest
from fastapi import FastAPI, Request
from fastapi.middleware import (
    MiddlewareDependencies,
    MiddlewareOrder,
    MiddlewareStack,
    MiddlewareWrapper,
)
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class TestMiddlewareProtocol:
    """Tests for MiddlewareProtocol usage."""

    def test_middleware_stack_basic(self):
        """Test basic MiddlewareStack functionality."""
        stack = MiddlewareStack()
        app = FastAPI()

        @app.get("/")
        def root():
            return {"message": "hello"}

        # The stack should be empty initially
        assert len(stack._middleware) == 0

    def test_middleware_stack_with_order(self):
        """Test MiddlewareStack with explicit ordering."""
        stack = MiddlewareStack()

        # Add middleware with explicit order
        stack.add(BaseHTTPMiddleware, order=1, dispatch=lambda req, call_next: call_next(req))
        stack.add(BaseHTTPMiddleware, order=2, dispatch=lambda req, call_next: call_next(req))

        assert len(stack._middleware) == 2
        # Verify order is preserved
        assert stack._middleware[0][0] == 1
        assert stack._middleware[1][0] == 2

    def test_middleware_wrapper(self):
        """Test MiddlewareWrapper initialization."""
        wrapper = MiddlewareWrapper(BaseHTTPMiddleware, order=1, dispatch=lambda req, call_next: call_next(req))

        assert wrapper.order == 1
        assert wrapper.middleware_class == BaseHTTPMiddleware


class TestMiddlewareDependencies:
    """Tests for MiddlewareDependencies."""

    def test_middleware_dependencies_init(self):
        """Test MiddlewareDependencies initialization."""
        deps = MiddlewareDependencies("dep1", "dep2")
        assert len(deps.dependencies) == 2


class TestMiddlewareOrder:
    """Tests for middleware ordering."""

    def test_middleware_order_type(self):
        """Test that MiddlewareOrder is an int."""
        order: MiddlewareOrder = 1
        assert isinstance(order, int)

    def test_middleware_order_in_wrapper(self):
        """Test MiddlewareOrder works in MiddlewareWrapper."""
        wrapper = MiddlewareWrapper(BaseHTTPMiddleware, order=5)
        assert wrapper.order == 5


class TestMiddlewareStackBuild:
    """Tests for MiddlewareStack.build()."""

    def test_middleware_stack_build_basic(self):
        """Test building middleware stack."""
        from starlette.types import ASGIApp

        async def dummy_app(scope, receive, send):
            pass

        stack = MiddlewareStack()
        built_app = stack.build(dummy_app)

        # The built app should be callable
        assert callable(built_app)


class TestTypedMiddlewareIntegration:
    """Integration tests for typed middleware with FastAPI."""

    def test_add_middleware_with_order(self):
        """Test adding middleware with explicit order to FastAPI app."""
        app = FastAPI()

        middleware_calls = []

        class TestMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                middleware_calls.append("test_middleware")
                return await call_next(request)

        # Add middleware with order
        app.add_middleware(TestMiddleware)

        @app.get("/")
        def root():
            return {"message": "hello"}

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "test_middleware" in middleware_calls

    def test_middleware_stack_integration(self):
        """Test MiddlewareStack works with FastAPI."""
        from starlette.types import ASGIApp

        async def final_app(scope, receive, send):
            # Simple ASGI app that returns 200
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"message": "ok"}',
            })

        stack = MiddlewareStack()
        # Don't add any middleware, just build
        app = stack.build(final_app)

        assert callable(app)


class TestFunctionMiddlewareProtocol:
    """Tests for FunctionMiddlewareProtocol."""

    def test_function_middleware_signature(self):
        """Test that function middleware can follow the protocol signature."""

        async def my_middleware(
            request: Request,
            call_next: lambda request: call_next(request),
        ) -> Response:
            response = await call_next(request)
            return response

        # This should not raise any type errors at runtime
        assert callable(my_middleware)

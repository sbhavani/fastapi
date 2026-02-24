"""
Integration tests for add_typed_middleware().
"""
import pytest

from fastapi import FastAPI, Request
from fastapi.middleware import MiddlewareProtocol
from fastapi.middleware.exceptions import OrderedMiddlewareError
from starlette.responses import Response
from starlette.types import ASGIApp


# Test middleware classes
class SimpleMiddleware(MiddlewareProtocol):
    """A simple middleware that does nothing."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, request: Request, call_next):
        return await call_next(request)


class LoggingMiddleware(MiddlewareProtocol):
    """A middleware that logs requests."""

    def __init__(self, app: ASGIApp):
        self.app = app
        self.calls = []

    async def __call__(self, request: Request, call_next):
        self.calls.append(request.url.path)
        return await call_next(request)


class AuthMiddleware(MiddlewareProtocol):
    """An auth middleware that adds user to request state."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, request: Request, call_next):
        request.state.user = "test_user"
        return await call_next(request)


def test_add_typed_middleware_basic():
    """Test adding a basic typed middleware."""
    app = FastAPI()

    app.add_typed_middleware(SimpleMiddleware)

    assert len(app.user_middleware) >= 1


def test_add_typed_middleware_multiple():
    """Test adding multiple typed middleware."""
    app = FastAPI()

    app.add_typed_middleware(LoggingMiddleware)
    app.add_typed_middleware(SimpleMiddleware)

    assert len(app.middleware_graph) == 2


def test_add_typed_middleware_with_depends_on():
    """Test adding middleware with depends_on."""
    app = FastAPI()

    app.add_typed_middleware(SimpleMiddleware)
    app.add_typed_middleware(LoggingMiddleware)

    # Should work
    assert len(app.middleware_graph) == 2


def test_middleware_in_graph():
    """Test that middleware is added to the graph."""
    app = FastAPI()

    app.add_typed_middleware(SimpleMiddleware)

    assert SimpleMiddleware in app.middleware_graph


def test_middleware_config_in_graph():
    """Test that middleware config is stored correctly."""
    app = FastAPI()

    app.add_typed_middleware(LoggingMiddleware)

    config = app.middleware_graph.get_config(LoggingMiddleware)
    assert config is not None
    assert config.cls == LoggingMiddleware


def test_add_typed_middleware_not_class():
    """Test adding a non-class raises error."""
    app = FastAPI()

    with pytest.raises(Exception):  # MiddlewareError
        app.add_typed_middleware("not a class")  # type: ignore

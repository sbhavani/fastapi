"""
Tests for dependency injection in middleware.
"""
import pytest

from fastapi import Depends, FastAPI, Request
from fastapi.middleware import MiddlewareProtocol
from fastapi.middleware.dependencies import MiddlewareDependencyResolver
from starlette.responses import Response
from starlette.types import ASGIApp


# Test dependencies
def get_db():
    """A test database dependency."""
    return {"connection": "test_db"}


def get_config():
    """A test config dependency."""
    return {"debug": True}


# Test middleware with dependencies
class DbMiddleware(MiddlewareProtocol):
    """Middleware that uses a database dependency."""

    def __init__(self, app: ASGIApp, db: dict = Depends(get_db)):
        self.app = app
        self.db = db

    async def __call__(self, request: Request, call_next):
        request.state.db = self.db
        return await call_next(request)


class ConfigMiddleware(MiddlewareProtocol):
    """Middleware that uses config dependency."""

    def __init__(self, app: ASGIApp, config: dict = Depends(get_config)):
        self.app = app
        self.config = config

    async def __call__(self, request: Request, call_next):
        return await call_next(request)


class MultipleDepsMiddleware(MiddlewareProtocol):
    """Middleware with multiple dependencies."""

    def __init__(
        self,
        app: ASGIApp,
        db: dict = Depends(get_db),
        config: dict = Depends(get_config),
    ):
        self.app = app
        self.db = db
        self.config = config

    async def __call__(self, request: Request, call_next):
        return await call_next(request)


def test_resolver_basic():
    """Test resolving basic dependencies."""
    resolver = MiddlewareDependencyResolver()

    # Mock app
    mock_app = object()

    # Resolve dependencies
    instance = resolver.resolve(DbMiddleware, mock_app)

    assert isinstance(instance, DbMiddleware)
    assert instance.db == {"connection": "test_db"}


def test_resolver_multiple_deps():
    """Test resolving multiple dependencies."""
    resolver = MiddlewareDependencyResolver()

    mock_app = object()

    instance = resolver.resolve(MultipleDepsMiddleware, mock_app)

    assert isinstance(instance, MultipleDepsMiddleware)
    assert instance.db == {"connection": "test_db"}
    assert instance.config == {"debug": True}


def test_resolver_with_overrides():
    """Test resolving with dependency overrides."""
    resolver = MiddlewareDependencyResolver()

    mock_app = object()

    # Override the get_db dependency
    overrides = {get_db: lambda: {"connection": "override_db"}}

    instance = resolver.resolve(DbMiddleware, mock_app, dependency_overrides=overrides)

    assert instance.db == {"connection": "override_db"}


def test_resolver_no_dependencies():
    """Test resolving middleware with no dependencies."""

    class NoDepsMiddleware:
        def __init__(self, app: ASGIApp):
            self.app = app

        async def __call__(self, request: Request, call_next):
            return await call_next(request)

    resolver = MiddlewareDependencyResolver()
    mock_app = object()

    instance = resolver.resolve(NoDepsMiddleware, mock_app)

    assert isinstance(instance, NoDepsMiddleware)
    assert instance.app == mock_app


def test_resolve_middleware_dependencies_function():
    """Test the convenience function."""
    from fastapi.middleware.dependencies import resolve_middleware_dependencies

    mock_app = object()

    instance = resolve_middleware_dependencies(DbMiddleware, mock_app)

    assert isinstance(instance, DbMiddleware)
    assert instance.db == {"connection": "test_db"}

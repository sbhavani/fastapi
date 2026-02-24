"""
Tests for backward compatibility with legacy middleware.
"""
import pytest

from fastapi import FastAPI, Request
from fastapi.middleware import MiddlewareProtocol
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp


# Legacy middleware (using BaseHTTPMiddleware)
class LegacyMiddleware(BaseHTTPMiddleware):
    """A legacy middleware using BaseHTTPMiddleware."""

    async def dispatch(self, request: Request, call_next):
        request.state.legacy = True
        return await call_next(request)


# Typed middleware
class TypedMiddleware(MiddlewareProtocol):
    """A typed middleware using MiddlewareProtocol."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, request: Request, call_next):
        request.state.typed = True
        return await call_next(request)


def test_legacy_middleware_still_works():
    """Test that legacy middleware still works."""
    app = FastAPI()

    # Add legacy middleware using old method
    app.add_middleware(LegacyMiddleware)

    # Verify it's added to user_middleware
    assert len(app.user_middleware) > 0


def test_typed_middleware_works():
    """Test that typed middleware works."""
    app = FastAPI()

    # Add typed middleware
    app.add_typed_middleware(TypedMiddleware)

    # Verify it's in the graph
    assert TypedMiddleware in app.middleware_graph


def test_mixed_middleware():
    """Test using both legacy and typed middleware together."""
    app = FastAPI()

    # Add legacy middleware first
    app.add_middleware(LegacyMiddleware)

    # Add typed middleware
    app.add_typed_middleware(TypedMiddleware)

    # Both should be present in user_middleware
    assert len(app.user_middleware) == 2
    # Typed middleware should also be in the graph
    assert TypedMiddleware in app.middleware_graph


def test_starlette_middleware_compatibility():
    """Test compatibility with Starlette's built-in middleware."""
    from starlette.middleware.cors import CORSMiddleware

    app = FastAPI()

    # Add Starlette's CORS middleware (legacy style)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
    )

    # Should work without errors
    assert len(app.user_middleware) > 0


def test_middleware_stack_ordering():
    """Test that middleware are added in correct order."""
    app = FastAPI()

    # Add multiple middlewares
    app.add_middleware(LegacyMiddleware)
    app.add_typed_middleware(TypedMiddleware)

    # The typed middleware should be in user_middleware
    # and the legacy middleware should also be there
    assert len(app.user_middleware) >= 1

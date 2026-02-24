"""Tests for typed middleware functionality."""
from typing import Any, Generic, TypeVar

import pytest
from fastapi import FastAPI, Request
from fastapi.middleware.typed import (
    MiddlewareProtocol,
    MiddlewareContext,
    MiddlewareRegistration,
    DependencyContainer,
    priority,
    before,
    after,
    MiddlewareError,
    MiddlewareOrderingError,
    MiddlewareDependencyError,
)
from fastapi.responses import Response


TRequest = TypeVar("TRequest")
TResponse = TypeVar("TResponse")


class TestMiddlewareProtocol:
    """Tests for MiddlewareProtocol."""

    def test_protocol_can_be_implemented(self):
        """Test that MiddlewareProtocol can be implemented by a class."""

        class TestMiddleware:
            async def dispatch(
                self, context: MiddlewareContext[Request, Response]
            ) -> Response:
                return context.response

        # Verify it implements the protocol (structural typing)
        middleware: MiddlewareProtocol[Request, Response] = TestMiddleware()
        assert middleware is not None

    def test_protocol_with_optional_on_error(self):
        """Test that on_error method is optional."""

        class TestMiddlewareWithoutOnError:
            async def dispatch(
                self, context: MiddlewareContext[Request, Response]
            ) -> Response:
                return context.response

        middleware: MiddlewareProtocol[Request, Response] = TestMiddlewareWithoutOnError()
        assert middleware is not None


class TestMiddlewareContext:
    """Tests for MiddlewareContext."""

    def test_context_properties(self):
        """Test MiddlewareContext properties."""
        app = FastAPI()
        container = DependencyContainer[Any]()
        request = Request(
            scope={"type": "http", "method": "GET", "path": "/"},
            receive=lambda: None,
        )
        response = Response(content=b"test")

        context = MiddlewareContext(
            request=request,
            response=response,
            dependencies=container,
            app=app,
        )

        assert context.request is request
        assert context.response is response
        assert context.app is app

    def test_set_response(self):
        """Test set_response method."""
        app = FastAPI()
        container = DependencyContainer[Any]()
        request = Request(
            scope={"type": "http", "method": "GET", "path": "/"},
            receive=lambda: None,
        )
        response1 = Response(content=b"test1")
        response2 = Response(content=b"test2")

        context = MiddlewareContext(
            request=request,
            response=response1,
            dependencies=container,
            app=app,
        )

        context.set_response(response2)
        assert context.response is response2


class TestDependencyContainer:
    """Tests for DependencyContainer."""

    def test_register_and_get(self):
        """Test registering and retrieving dependencies."""
        container = DependencyContainer[Any]()

        class TestDep:
            value = "test"

        container.register(TestDep, TestDep())
        retrieved = container.get(TestDep)
        assert retrieved.value == "test"

    def test_get_missing_dependency(self):
        """Test that getting missing dependency raises error."""
        container = DependencyContainer[Any]()

        class TestDep:
            pass

        with pytest.raises(MiddlewareDependencyError):
            container.get(TestDep)

    def test_validate(self):
        """Test validate method is a no-op."""
        container = DependencyContainer[Any]()
        # Should not raise
        container.validate()


class TestDecorators:
    """Tests for priority, before, after decorators."""

    def test_priority_decorator(self):
        """Test priority decorator sets attribute."""
        @priority(100)
        class TestMiddleware:
            pass

        assert hasattr(TestMiddleware, "__middleware_priority__")
        assert TestMiddleware.__middleware_priority__ == 100

    def test_before_decorator(self):
        """Test before decorator sets attribute."""
        @before("middleware1", "middleware2")
        class TestMiddleware:
            pass

        assert hasattr(TestMiddleware, "__middleware_before__")
        assert "middleware1" in TestMiddleware.__middleware_before__
        assert "middleware2" in TestMiddleware.__middleware_before__

    def test_after_decorator(self):
        """Test after decorator sets attribute."""
        @after("middleware1", "middleware2")
        class TestMiddleware:
            pass

        assert hasattr(TestMiddleware, "__middleware_after__")
        assert "middleware1" in TestMiddleware.__middleware_after__
        assert "middleware2" in TestMiddleware.__middleware_after__


class TestMiddlewareRegistration:
    """Tests for MiddlewareRegistration."""

    def test_registration_defaults(self):
        """Test MiddlewareRegistration default values."""

        class TestMiddleware:
            pass

        registration = MiddlewareRegistration(
            middleware_class=TestMiddleware,
        )

        assert registration.middleware_class is TestMiddleware
        assert registration.priority == 0
        assert registration.before == []
        assert registration.after == []
        assert registration.name == "TestMiddleware"

    def test_registration_with_custom_values(self):
        """Test MiddlewareRegistration with custom values."""

        class TestMiddleware:
            pass

        registration = MiddlewareRegistration(
            middleware_class=TestMiddleware,
            priority=50,
            before=["other1"],
            after=["other2"],
            name="custom_name",
        )

        assert registration.priority == 50
        assert registration.before == ["other1"]
        assert registration.after == ["other2"]
        assert registration.name == "custom_name"


class TestOrderingValidation:
    """Tests for ordering constraint validation."""

    def test_validate_missing_target_before(self):
        """Test validation fails when before target doesn't exist."""
        from fastapi.middleware.typed import validate_ordering_constraints

        registration = MiddlewareRegistration(
            middleware_class=type("Test", (), {}),
            name="test",
            before=["nonexistent"],
        )

        with pytest.raises(MiddlewareOrderingError) as exc_info:
            validate_ordering_constraints({}, registration)

        assert "nonexistent" in str(exc_info.value)

    def test_validate_missing_target_after(self):
        """Test validation fails when after target doesn't exist."""
        from fastapi.middleware.typed import validate_ordering_constraints

        registration = MiddlewareRegistration(
            middleware_class=type("Test", (), {}),
            name="test",
            after=["nonexistent"],
        )

        with pytest.raises(MiddlewareOrderingError) as exc_info:
            validate_ordering_constraints({}, registration)

        assert "nonexistent" in str(exc_info.value)

    def test_validate_circular_dependency_before_before(self):
        """Test validation fails when circular dependency exists (A before B, B before A)."""
        from fastapi.middleware.typed import validate_ordering_constraints

        # A says before B, B says before A - this creates a cycle
        reg_a = MiddlewareRegistration(
            middleware_class=type("A", (), {}),
            name="A",
            before=["B"],
        )
        reg_b = MiddlewareRegistration(
            middleware_class=type("B", (), {}),
            name="B",
            before=["A"],
        )

        with pytest.raises(MiddlewareOrderingError) as exc_info:
            validate_ordering_constraints({"B": reg_b}, reg_a)

        assert "Circular dependency" in str(exc_info.value)

    def test_validate_circular_dependency_after_after(self):
        """Test validation fails when circular dependency exists (A after B, B after A)."""
        from fastapi.middleware.typed import validate_ordering_constraints

        # A says after B, B says after A - this creates a cycle
        reg_a = MiddlewareRegistration(
            middleware_class=type("A", (), {}),
            name="A",
            after=["B"],
        )
        reg_b = MiddlewareRegistration(
            middleware_class=type("B", (), {}),
            name="B",
            after=["A"],
        )

        with pytest.raises(MiddlewareOrderingError) as exc_info:
            validate_ordering_constraints({"B": reg_b}, reg_a)

        assert "Circular dependency" in str(exc_info.value)

    def test_validate_circular_dependency_chain(self):
        """Test validation fails when circular dependency chain B, B before exists (A before C, C before A)."""
        from fastapi.middleware.typed import validate_ordering_constraints

        # A before B, B before C, C before A creates a cycle
        # Existing registrations: A before B, B before C
        reg_a = MiddlewareRegistration(
            middleware_class=type("A", (), {}),
            name="A",
            before=["B"],
        )
        reg_b = MiddlewareRegistration(
            middleware_class=type("B", (), {}),
            name="B",
            before=["C"],
        )
        # New registration: C before A (completing the cycle)
        reg_c = MiddlewareRegistration(
            middleware_class=type("C", (), {}),
            name="C",
            before=["A"],
        )

        with pytest.raises(MiddlewareOrderingError) as exc_info:
            validate_ordering_constraints(
                {"A": reg_a, "B": reg_b},
                reg_c,
            )

        assert "Circular dependency" in str(exc_info.value)


class TestAddTypedMiddleware:
    """Tests for FastAPI.add_typed_middleware method."""

    def test_add_typed_middleware_basic(self):
        """Test adding typed middleware to app."""
        app = FastAPI()

        class TestMiddleware:
            async def dispatch(
                self, context: MiddlewareContext[Request, Response]
            ) -> Response:
                return context.response

        app.add_typed_middleware(TestMiddleware)
        assert hasattr(app, "_typed_middleware_registry")
        assert "TestMiddleware" in app._typed_middleware_registry

    def test_add_typed_middleware_with_priority(self):
        """Test adding typed middleware with priority."""
        app = FastAPI()

        class TestMiddleware:
            pass

        app.add_typed_middleware(TestMiddleware, priority=100)
        assert app._typed_middleware_registry["TestMiddleware"].priority == 100

    def test_add_typed_middleware_with_decorator_priority(self):
        """Test adding typed middleware with priority decorator."""
        app = FastAPI()

        @priority(200)
        class DecoratedMiddleware:
            pass

        app.add_typed_middleware(DecoratedMiddleware)
        assert app._typed_middleware_registry["DecoratedMiddleware"].priority == 200

    def test_add_typed_middleware_with_decorator_before(self):
        """Test adding typed middleware with before decorator."""
        app = FastAPI()

        class OtherMiddleware:
            pass

        @before("OtherMiddleware")
        class TestMiddleware:
            pass

        app.add_typed_middleware(OtherMiddleware)
        app.add_typed_middleware(TestMiddleware)
        assert "OtherMiddleware" in app._typed_middleware_registry["TestMiddleware"].before

    def test_add_typed_middleware_with_decorator_after(self):
        """Test adding typed middleware with after decorator."""
        app = FastAPI()

        class OtherMiddleware:
            pass

        @after("OtherMiddleware")
        class TestMiddleware:
            pass

        app.add_typed_middleware(OtherMiddleware)
        app.add_typed_middleware(TestMiddleware)
        assert "OtherMiddleware" in app._typed_middleware_registry["TestMiddleware"].after

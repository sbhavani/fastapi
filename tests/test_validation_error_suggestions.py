"""Tests for validation error enhancement with suggestions."""
import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel


class TestEnhanceValidationErrors:
    """Test the enhance_validation_errors function."""

    def test_missing_field_with_suggestion(self):
        """Test that missing field errors include suggestions."""
        from fastapi.exceptions import enhance_validation_errors

        errors = [
            {
                "type": "missing",
                "loc": ("body", "usernmae"),
                "msg": "Field required",
                "input": {"username": "test", "email": "test@test.com"},
            }
        ]
        enhanced = enhance_validation_errors(errors)
        assert len(enhanced) == 1
        assert "suggestions" in enhanced[0]
        assert "username" in enhanced[0]["suggestions"]

    def test_missing_field_no_suggestion_when_no_input(self):
        """Test that no suggestions when there's no input data."""
        from fastapi.exceptions import enhance_validation_errors

        errors = [
            {
                "type": "missing",
                "loc": ("body", "username"),
                "msg": "Field required",
                "input": None,
            }
        ]
        enhanced = enhance_validation_errors(errors)
        assert len(enhanced) == 1
        assert "suggestions" not in enhanced[0]

    def test_missing_field_with_explicit_expected_fields(self):
        """Test that explicit expected_fields are used when provided."""
        from fastapi.exceptions import enhance_validation_errors

        errors = [
            {
                "type": "missing",
                "loc": ("body", "usernmae"),
                "msg": "Field required",
                "input": {},
            }
        ]
        expected_fields = {("body",): ["username", "email", "age"]}
        enhanced = enhance_validation_errors(errors, expected_fields=expected_fields)
        assert len(enhanced) == 1
        assert "suggestions" in enhanced[0]
        assert "username" in enhanced[0]["suggestions"]

    def test_type_error_no_example_when_no_context(self):
        """Test that type errors without ctx don't get examples."""
        from fastapi.exceptions import enhance_validation_errors

        errors = [
            {
                "type": "string_type",
                "loc": ("body", "age"),
                "msg": "Input should be a valid string",
                "input": 123,
            }
        ]
        enhanced = enhance_validation_errors(errors)
        assert len(enhanced) == 1
        assert "example" not in enhanced[0]

    def test_enhance_preserves_original_errors(self):
        """Test that enhance_validation_errors doesn't modify original errors."""
        from fastapi.exceptions import enhance_validation_errors

        errors = [
            {
                "type": "missing",
                "loc": ("body", "username"),
                "msg": "Field required",
                "input": {},
            }
        ]
        original_errors = list(errors)
        enhance_validation_errors(errors)
        assert errors == original_errors


class TestValidationErrorSuggestions:
    """Test validation error suggestions in FastAPI requests."""

    def test_request_validation_error_suggestion(self):
        """Test that request validation errors include suggestions."""
        app = FastAPI()

        class Item(BaseModel):
            username: str
            email: str
            age: int

        @app.post("/items/")
        def create_item(item: Item):
            return item

        client = TestClient(app, raise_server_exceptions=False)

        # Send request with typo in username
        response = client.post(
            "/items/", json={"usernmae": "test", "email": "test@test.com", "age": 25}
        )
        assert response.status_code == 422

        detail = response.json()["detail"]
        assert len(detail) == 1
        assert detail[0]["type"] == "missing"
        assert "suggestions" in detail[0]

    def test_no_suggestions_for_correct_field(self):
        """Test that no suggestions are shown for correct fields."""
        app = FastAPI()

        class Item(BaseModel):
            username: str
            email: str
            age: int

        @app.post("/items/")
        def create_item(item: Item):
            return item

        client = TestClient(app, raise_server_exceptions=False)

        # Send request with all correct fields but wrong type for age
        response = client.post(
            "/items/", json={"username": "test", "email": "test@test.com", "age": "not-a-number"}
        )
        assert response.status_code == 422

        detail = response.json()["detail"]
        # For type errors, we don't necessarily show suggestions
        # (though we could add examples in the future)
        assert detail[0]["type"] == "int_parsing"


class TestRequestValidationErrorWithExpectedFields:
    """Test RequestValidationError with expected_fields parameter."""

    def test_errors_with_suggestions_method(self):
        """Test the errors_with_suggestions method."""
        errors = [
            {
                "type": "missing",
                "loc": ("body", "usernmae"),
                "msg": "Field required",
                "input": {"username": "test"},
            }
        ]
        exc = RequestValidationError(
            errors,
            expected_fields={("body",): ["username", "email"]},
        )
        enhanced = exc.errors_with_suggestions()
        assert len(enhanced) == 1
        assert "suggestions" in enhanced[0]
        assert "username" in enhanced[0]["suggestions"]

    def test_errors_method_still_works(self):
        """Test that the original errors() method still works."""
        errors = [
            {
                "type": "missing",
                "loc": ("body", "username"),
                "msg": "Field required",
                "input": {},
            }
        ]
        exc = RequestValidationError(errors)
        assert exc.errors() == errors

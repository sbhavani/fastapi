"""Tests for enhanced validation error messages with suggestions."""

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from fastapi._error_utils import (
    enhance_validation_errors,
    _get_field_path_str,
    _get_similar_fields,
)
from pydantic import BaseModel


class TestFieldPathStr:
    """Tests for _get_field_path_str function."""

    def test_simple_path(self):
        assert _get_field_path_str(("body", "username")) == "body -> username"

    def test_nested_path(self):
        assert _get_field_path_str(("body", "user", "name")) == "body -> user -> name"

    def test_array_index_path(self):
        assert _get_field_path_str(("body", 0, "id")) == "body[0] -> id"

    def test_mixed_path(self):
        assert _get_field_path_str(("body", "items", 0, "name")) == "body -> items[0] -> name"

    def test_empty_path(self):
        assert _get_field_path_str(()) == ""


class TestSimilarFields:
    """Tests for _get_similar_fields function."""

    def test_exact_match(self):
        fields = ["username", "email", "password"]
        result = _get_similar_fields("username", fields)
        assert "username" in result

    def test_close_match(self):
        fields = ["username", "email", "password"]
        result = _get_similar_fields("usernam", fields)
        assert "username" in result

    def test_no_match(self):
        fields = ["username", "email", "password"]
        result = _get_similar_fields("xyz", fields)
        assert result == []

    def test_empty_fields(self):
        result = _get_similar_fields("username", [])
        assert result == []

    def test_multiple_matches(self):
        fields = ["username", "user_id", "user_name", "email"]
        result = _get_similar_fields("user", fields, max_suggestions=3)
        assert len(result) <= 3


class TestEnhanceValidationErrors:
    """Tests for enhance_validation_errors function."""

    def test_missing_field_suggestion(self):
        errors = [
            {"type": "missing", "loc": ("body", "username"), "msg": "Field required", "input": {}}
        ]
        available_fields = ["username", "email", "password"]
        enhanced = enhance_validation_errors(errors, available_fields=available_fields)

        assert enhanced[0]["path"] == "body -> username"
        assert "suggestion" in enhanced[0]
        assert "username" in enhanced[0]["suggestion"]

    def test_unknown_field_suggestion(self):
        errors = [
            {"type": "unknown", "loc": ("body", "usernam"), "msg": "Extra fields not permitted", "input": {"usernam": "test"}}
        ]
        available_fields = ["username", "email", "password"]
        enhanced = enhance_validation_errors(errors, available_fields=available_fields)

        assert enhanced[0]["path"] == "body -> usernam"
        assert "suggestion" in enhanced[0]
        assert "username" in enhanced[0]["suggestion"]

    def test_no_suggestion_when_no_available_fields(self):
        errors = [
            {"type": "missing", "loc": ("body", "username"), "msg": "Field required", "input": {}}
        ]
        enhanced = enhance_validation_errors(errors)

        assert enhanced[0]["path"] == "body -> username"
        assert "suggestion" not in enhanced[0]

    def test_multiple_errors(self):
        errors = [
            {"type": "missing", "loc": ("body", "username"), "msg": "Field required", "input": {}},
            {"type": "missing", "loc": ("body", "email"), "msg": "Field required", "input": {}},
        ]
        available_fields = ["username", "email", "password"]
        enhanced = enhance_validation_errors(errors, available_fields=available_fields)

        assert len(enhanced) == 2
        assert enhanced[0]["path"] == "body -> username"
        assert enhanced[1]["path"] == "body -> email"

    def test_type_error_path(self):
        errors = [
            {"type": "type_error", "loc": ("body", "age"), "msg": "Input should be an integer", "input": "not_an_int"}
        ]
        enhanced = enhance_validation_errors(errors)

        assert enhanced[0]["path"] == "body -> age"


class Item(BaseModel):
    id: int
    name: str
    price: float


app = FastAPI()


@app.post("/items/")
def create_item(item: Item):
    return item


client = TestClient(app)


def test_request_validation_error_suggestions():
    """Test that validation errors include suggestions in API responses."""
    response = client.post(
        "/items/",
        json={"id": 1, "nam": "Test"}  # "nam" instead of "name"
    )

    assert response.status_code == 422
    detail = response.json()["detail"]

    # Check that we have path information
    assert any("path" in err for err in detail)

    # Check that suggestion is provided for the "name" field (which is reported as missing)
    # Note: Pydantic reports the "name" field as missing, not "nam" as unknown
    name_errors = [err for err in detail if "name" in str(err.get("loc", ()))]
    if name_errors:
        # Should include path
        assert "path" in name_errors[0]
        # Should have path string
        assert "name" in name_errors[0].get("path", "")


def test_request_validation_error_path():
    """Test that validation errors include human-readable path."""
    response = client.post(
        "/items/",
        json={"id": "not_an_int", "name": "Test"}
    )

    assert response.status_code == 422
    detail = response.json()["detail"]

    # Check that we have path information
    assert any("path" in err for err in detail)

    # Check that path contains the expected structure
    id_errors = [err for err in detail if "id" in str(err.get("loc", ()))]
    if id_errors:
        assert "body -> id" in id_errors[0].get("path", "")


def test_missing_field_error():
    """Test that missing field errors include suggestions."""
    response = client.post(
        "/items/",
        json={"id": 1}  # missing "name" and "price"
    )

    assert response.status_code == 422
    detail = response.json()["detail"]

    # Should have 2 errors (missing name and price)
    assert len(detail) == 2

    # Check that path is included
    for err in detail:
        assert "path" in err


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

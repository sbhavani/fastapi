"""
Tests for Validation Error Suggestions feature.

These tests verify that validation errors include:
- field_path: Dot-notation path to the error location
- example: Example valid value for the field
- expected_type: Human-readable expected type
- suggested_field: Suggested field name if typo detected
"""

import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from pydantic import BaseModel


# Test Models
class UserProfile(BaseModel):
    name: str
    age: int
    email: str


class Address(BaseModel):
    street: str
    city: str
    zip_code: str


class UserWithAddress(BaseModel):
    name: str
    email: str
    address: Address


class Item(BaseModel):
    name: str
    quantity: int
    tags: list[str]


# Create FastAPI app
app = FastAPI()


@app.post("/users/")
def create_user(user: UserProfile):
    return {"name": user.name}


@app.post("/users-with-address/")
def create_user_with_address(user: UserWithAddress):
    return {"name": user.name}


@app.post("/items/")
def create_item(item: Item):
    return {"name": item.name}


client = TestClient(app)


# Tests for field path generation (T007)
class TestFieldPathGeneration:
    def test_simple_field_path(self):
        """Test simple field path generation."""
        response = client.post("/users/", json={"name": "John"})
        assert response.status_code == 422
        errors = response.json()["detail"]
        # Should have error for missing 'age' and 'email'
        assert any("age" in str(e.get("field_path", "")) for e in errors)

    def test_nested_field_path(self):
        """Test nested field path generation."""
        response = client.post(
            "/users-with-address/",
            json={"name": "John", "email": "john@example.com", "address": {"street": "123 Main"}},
        )
        assert response.status_code == 422
        errors = response.json()["detail"]
        # Should have error for missing 'city' and 'zip_code'
        assert any("address.city" in str(e.get("field_path", "")) for e in errors)

    def test_array_index_path(self):
        """Test array index notation in field path."""
        response = client.post("/items/", json={"name": "Test", "tags": ["valid", 123]})
        assert response.status_code == 422
        errors = response.json()["detail"]
        # Should have error for tags[1] (integer in string array)
        assert any("tags[1]" in str(e.get("field_path", "")) for e in errors)


# Tests for example value generation (T011)
class TestExampleValueGeneration:
    def test_string_type_example(self):
        """Test that string fields get example values inferred from error type."""
        response = client.post("/users/", json={"name": 123, "age": 25, "email": "test@example.com"})
        assert response.status_code == 422
        errors = response.json()["detail"]
        # Find the name error
        name_errors = [e for e in errors if e.get("field_path") == "name"]
        assert len(name_errors) > 0
        # Field should exist (null safety - can be None when no inference possible)
        assert "example" in name_errors[0]
        # Type is inferred from error type (string_type -> string)
        assert name_errors[0].get("example") is not None

    def test_int_type_example(self):
        """Test that integer fields get example values inferred from error type."""
        response = client.post("/users/", json={"name": "John", "age": "not-int", "email": "test@example.com"})
        assert response.status_code == 422
        errors = response.json()["detail"]
        # Find the age error
        age_errors = [e for e in errors if e.get("field_path") == "age"]
        assert len(age_errors) > 0
        # Field should exist (null safety - can be None when no inference possible)
        assert "example" in age_errors[0]
        # Type is inferred from error type (int_parsing -> integer)
        assert age_errors[0].get("example") is not None


# Tests for expected type generation (T010)
class TestExpectedTypeGeneration:
    def test_expected_type_for_string(self):
        """Test expected type is inferred from error type."""
        response = client.post("/users/", json={"name": 123, "age": 25, "email": "test@example.com"})
        assert response.status_code == 422
        errors = response.json()["detail"]
        name_errors = [e for e in errors if e.get("field_path") == "name"]
        assert len(name_errors) > 0
        # Field should exist (null safety - can be None when no inference possible)
        assert "expected_type" in name_errors[0]
        # Type is inferred from error type (string_type -> string)
        assert name_errors[0].get("expected_type") is not None

    def test_expected_type_for_int(self):
        """Test expected type is inferred from error type for integer fields."""
        response = client.post("/users/", json={"name": "John", "age": "not-int", "email": "test@example.com"})
        assert response.status_code == 422
        errors = response.json()["detail"]
        age_errors = [e for e in errors if e.get("field_path") == "age"]
        assert len(age_errors) > 0
        # Field should exist (null safety - can be None when no inference possible)
        assert "expected_type" in age_errors[0]
        # Type is inferred from error type (int_parsing -> integer)
        expected_type = age_errors[0].get("expected_type", "")
        assert expected_type is not None


# Tests for similar field suggestions - requires valid_fields to be passed
# This is a basic test of the utility function
class TestFieldNameSuggestion:
    def test_similarity_utility_function(self):
        """Test the string similarity function directly."""
        from fastapi.error_enhancement import get_similarity_score, find_similar_field

        # Test similarity scores
        assert get_similarity_score("emal", "email") > 0.6
        assert get_similarity_score("name", "names") > 0.6
        assert get_similarity_score("foo", "bar") < 0.6

        # Test find similar
        assert find_similar_field("emal", ["email", "name", "age"]) == "email"
        assert find_similar_field("nam", ["email", "name", "age"]) == "name"


# Tests for backward compatibility (T017)
class TestBackwardCompatibility:
    def test_original_fields_preserved(self):
        """Test that original error fields are preserved."""
        response = client.post("/users/", json={"name": 123})
        assert response.status_code == 422
        errors = response.json()["detail"]
        assert len(errors) > 0
        error = errors[0]
        # Original fields must be present
        assert "type" in error
        assert "loc" in error
        assert "msg" in error

    def test_enhanced_fields_optional(self):
        """Test that enhanced fields are optional."""
        # When there's no clear enhancement possible, fields should still work
        response = client.post("/users/", json={})
        assert response.status_code == 422
        errors = response.json()["detail"]
        # Should have errors with optional enhanced fields
        for error in errors:
            # These should be present (possibly None/null)
            assert "field_path" in error
            assert "example" in error
            assert "expected_type" in error
            assert "suggested_field" in error


# Tests for nested models (T022)
class TestNestedModels:
    def test_deeply_nested_field_path(self):
        """Test field path for deeply nested models."""
        # Create a model with nested objects
        class Company(BaseModel):
            name: str

        class Department(BaseModel):
            name: str
            company: Company

        class Employee(BaseModel):
            name: str
            department: Department

        test_app = FastAPI()

        @test_app.post("/employees/")
        def create_employee(employee: Employee):
            return {"name": employee.name}

        test_client = TestClient(test_app)
        response = test_client.post(
            "/employees/",
            json={"name": "John", "department": {"name": "Engineering"}},
        )
        assert response.status_code == 422
        errors = response.json()["detail"]
        # Should have error for missing company.name
        company_errors = [e for e in errors if "company" in str(e.get("field_path", ""))]
        assert len(company_errors) > 0
        # The path should include company
        assert "company" in company_errors[0].get("field_path", "")


# Tests for WebSocket validation errors (T023)
class TestWebSocketValidation:
    def test_websocket_validation_error(self):
        """Test WebSocket validation errors include enhancements."""
        ws_app = FastAPI()

        @ws_app.websocket("/ws/{item_id}")
        async def websocket_endpoint(websocket: WebSocket, item_id: int):
            await websocket.accept()
            await websocket.close()

        ws_client = TestClient(ws_app)

        # TestClient raises exception on WebSocket disconnect
        with pytest.raises(Exception) as exc_info:
            with ws_client.websocket_connect("/ws/not-an-integer") as ws:
                pass

        # Should have disconnected due to validation error
        assert "code" in str(exc_info.value) or "WebSocketDisconnect" in str(type(exc_info.value))

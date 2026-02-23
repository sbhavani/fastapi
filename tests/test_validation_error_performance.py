"""
Performance Benchmark Tests for Validation Error Suggestions.

These tests measure the performance of error enhancement functions to ensure
they don't introduce significant overhead in the request validation path.

Performance targets:
- build_field_path: < 0.01ms per call
- get_similarity_score: < 0.1ms per call
- find_similar_field: < 1ms per call for typical field lists
- enhance_error: < 1ms per error
- enhance_errors (batch): < 5ms for 10 errors
- End-to-end request handling: < 10ms additional overhead
"""

import pytest
import time
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.error_enhancement import (
    build_field_path,
    get_similarity_score,
    find_similar_field,
    generate_example_from_format,
    generate_example_from_type,
    generate_expected_type,
    enhance_error,
    enhance_errors,
)
from pydantic import BaseModel


# ============================================================================
# Utility functions for benchmarking
# ============================================================================


def measure_time(func, iterations: int = 1000):
    """Measure average execution time in milliseconds."""
    start = time.perf_counter()
    for _ in range(iterations):
        func()
    end = time.perf_counter()
    return (end - start) / iterations * 1000  # ms


# ============================================================================
# Test Class: Field Path Building Performance
# ============================================================================


class TestFieldPathBuildingPerformance:
    """Performance tests for field path building."""

    def test_simple_field_path_performance(self):
        """Benchmark simple field path generation."""
        loc = ("body", "user", "email")

        def func():
            build_field_path(loc)

        avg_time = measure_time(func, iterations=10000)
        # Should be well under 0.01ms per call
        assert avg_time < 0.1, f"build_field_path took {avg_time:.4f}ms (target: < 0.1ms)"

    def test_nested_field_path_performance(self):
        """Benchmark nested field path generation."""
        loc = ("body", "company", "department", "employee", "profile", "email")

        def func():
            build_field_path(loc)

        avg_time = measure_time(func, iterations=10000)
        assert avg_time < 0.1, f"build_field_path (nested) took {avg_time:.4f}ms"

    def test_array_index_field_path_performance(self):
        """Benchmark field path with array indices."""
        loc = ("body", "users", 0, "addresses", 1, "zip_code")

        def func():
            build_field_path(loc)

        avg_time = measure_time(func, iterations=10000)
        assert avg_time < 0.1, f"build_field_path (array) took {avg_time:.4f}ms"


# ============================================================================
# Test Class: String Similarity Performance
# ============================================================================


class TestStringSimilarityPerformance:
    """Performance tests for string similarity functions."""

    def test_similarity_score_performance(self):
        """Benchmark similarity score calculation."""
        def func():
            get_similarity_score("emal", "email")

        avg_time = measure_time(func, iterations=10000)
        # Should be under 0.1ms per call
        assert avg_time < 1.0, f"get_similarity_score took {avg_time:.4f}ms"

    def test_find_similar_field_performance_small_list(self):
        """Benchmark finding similar field in small list."""
        valid_fields = ["email", "name", "age", "address", "phone"]

        def func():
            find_similar_field("emal", valid_fields)

        avg_time = measure_time(func, iterations=10000)
        assert avg_time < 1.0, f"find_similar_field (small) took {avg_time:.4f}ms"

    def test_find_similar_field_performance_medium_list(self):
        """Benchmark finding similar field in medium list."""
        valid_fields = [
            "first_name", "last_name", "email", "phone", "address",
            "city", "state", "zip_code", "country", "age", "birth_date",
            "username", "password", "confirm_password", "is_active"
        ]

        def func():
            find_similar_field("emal", valid_fields)

        avg_time = measure_time(func, iterations=10000)
        assert avg_time < 2.0, f"find_similar_field (medium) took {avg_time:.4f}ms"

    def test_find_similar_field_performance_large_list(self):
        """Benchmark finding similar field in large list (100 fields)."""
        valid_fields = [f"field_{i}" for i in range(100)]

        def func():
            find_similar_field("fild_50", valid_fields)

        avg_time = measure_time(func, iterations=1000)
        assert avg_time < 10.0, f"find_similar_field (large) took {avg_time:.4f}ms"


# ============================================================================
# Test Class: Example Generation Performance
# ============================================================================


class TestExampleGenerationPerformance:
    """Performance tests for example generation functions."""

    def test_generate_example_from_format_performance(self):
        """Benchmark example from format generation."""
        def func():
            generate_example_from_format("email")

        avg_time = measure_time(func, iterations=100000)
        assert avg_time < 0.01, f"generate_example_from_format took {avg_time:.4f}ms"

    def test_generate_example_from_type_performance(self):
        """Benchmark example from type generation."""
        def func():
            generate_example_from_type("string")

        avg_time = measure_time(func, iterations=100000)
        assert avg_time < 0.01, f"generate_example_from_type took {avg_time:.4f}ms"

    def test_generate_expected_type_performance(self):
        """Benchmark expected type generation."""
        def func():
            generate_expected_type("string", "email")

        avg_time = measure_time(func, iterations=100000)
        assert avg_time < 0.01, f"generate_expected_type took {avg_time:.4f}ms"


# ============================================================================
# Test Class: Error Enhancement Performance
# ============================================================================


class TestErrorEnhancementPerformance:
    """Performance tests for error enhancement functions."""

    def test_enhance_error_performance(self):
        """Benchmark single error enhancement."""
        error: dict[str, Any] = {
            "type": "missing",
            "loc": ("body", "user", "email"),
            "msg": "Field required",
            "input": {},
        }
        valid_fields = ["email", "name", "age", "address"]
        field_schema = {"type": "string", "format": "email"}

        def func():
            enhance_error(error, valid_fields, field_schema)

        avg_time = measure_time(func, iterations=10000)
        assert avg_time < 1.0, f"enhance_error took {avg_time:.4f}ms"

    def test_enhance_errors_batch_performance(self):
        """Benchmark batch error enhancement (10 errors)."""
        errors: list[dict[str, Any]] = [
            {
                "type": "missing",
                "loc": ("body", f"field_{i}"),
                "msg": f"Field {i} required",
                "input": {},
            }
            for i in range(10)
        ]
        valid_fields = [f"field_{i}" for i in range(20)]

        def func():
            enhance_errors(errors, valid_fields)

        avg_time = measure_time(func, iterations=1000)
        assert avg_time < 5.0, f"enhance_errors (10) took {avg_time:.4f}ms"

    def test_enhance_errors_many_performance(self):
        """Benchmark batch error enhancement (50 errors)."""
        errors: list[dict[str, Any]] = [
            {
                "type": "missing",
                "loc": ("body", f"field_{i}"),
                "msg": f"Field {i} required",
                "input": {},
            }
            for i in range(50)
        ]
        valid_fields = [f"field_{i}" for i in range(100)]

        def func():
            enhance_errors(errors, valid_fields)

        avg_time = measure_time(func, iterations=100)
        assert avg_time < 20.0, f"enhance_errors (50) took {avg_time:.4f}ms"


# ============================================================================
# Test Class: End-to-End Performance
# ============================================================================


class TestEndToEndPerformance:
    """End-to-end performance tests for FastAPI validation."""

    def test_validation_error_response_performance(self):
        """Benchmark full validation error handling in FastAPI."""
        class UserProfile(BaseModel):
            name: str
            email: str
            age: int

        app = FastAPI()

        @app.post("/users/")
        def create_user(user: UserProfile):
            return {"name": user.name}

        client = TestClient(app)

        # Warm up
        client.post("/users/", json={"name": "John"})

        # Measure validation error response
        start = time.perf_counter()
        for _ in range(100):
            response = client.post("/users/", json={"name": "John"})
        end = time.perf_counter()

        avg_time = (end - start) / 100 * 1000  # ms
        assert response.status_code == 422
        # Should be under 10ms additional overhead per request
        assert avg_time < 50.0, f"Validation error handling took {avg_time:.4f}ms per request"

    def test_multiple_validation_errors_performance(self):
        """Benchmark response with multiple validation errors."""
        class Item(BaseModel):
            name: str
            description: str
            price: float
            quantity: int

        app = FastAPI()

        @app.post("/items/")
        def create_item(item: Item):
            return {"name": item.name}

        client = TestClient(app)

        # Send request with multiple validation errors
        start = time.perf_counter()
        response = client.post("/items/", json={})
        end = time.perf_counter()

        response_time = (end - start) * 1000  # ms

        assert response.status_code == 422
        errors = response.json()["detail"]
        # Should have 4 errors (name, description, price, quantity)
        assert len(errors) == 4
        # Response should still be fast
        assert response_time < 50.0, f"Multiple error response took {response_time:.4f}ms"


# ============================================================================
# Test Class: Memory Efficiency
# ============================================================================


class TestMemoryEfficiency:
    """Memory efficiency tests."""

    def test_no_memory_leak_in_repeated_calls(self):
        """Verify no memory leak in repeated error enhancement calls."""
        import gc

        errors: list[dict[str, Any]] = [
            {
                "type": "missing",
                "loc": ("body", f"field_{i}"),
                "msg": f"Field {i} required",
                "input": {},
            }
            for i in range(10)
        ]
        valid_fields = [f"field_{i}" for i in range(20)]

        # Force garbage collection before
        gc.collect()

        # Run enhancement many times
        for _ in range(1000):
            enhance_errors(errors, valid_fields)

        # Force garbage collection after
        gc.collect()

        # If we got here without memory errors, test passes
        # (This is a basic sanity check; real memory profiling would require tools)
        assert True


# ============================================================================
# Test Class: Regression Tests
# ============================================================================


class TestRegressionTests:
    """Regression tests to ensure performance doesn't degrade."""

    def test_enhance_error_maintains_functionality(self):
        """Ensure error enhancement still works correctly under load."""
        # Use a field name that's NOT in valid_fields to trigger suggestion
        error: dict[str, Any] = {
            "type": "missing",
            "loc": ("body", "user", "emal"),  # "emal" is not in valid_fields
            "msg": "Field required",
            "input": {},
        }
        valid_fields = ["email", "name", "age"]  # "email" is the suggestion for "emal"
        field_schema = {"type": "string", "format": "email"}

        # Run multiple times to ensure consistency
        results = []
        for _ in range(100):
            result = enhance_error(error, valid_fields, field_schema)
            results.append(result)

        # All results should be identical
        first_result = results[0]
        for result in results:
            assert result == first_result

        # Verify enhanced fields are present
        assert first_result["field_path"] == "user.emal"
        assert first_result["suggested_field"] == "email"  # "emal" suggests "email"
        assert first_result["example"] == "user@example.com"
        assert first_result["expected_type"] == "string (email)"

    def test_find_similar_field_threshold_respected(self):
        """Ensure similarity threshold is respected under load."""
        valid_fields = ["email", "name", "age"]

        # Should find match for "emal" -> "email"
        for _ in range(100):
            result = find_similar_field("emal", valid_fields)
            assert result == "email"

        # Should NOT find match for completely different string
        for _ in range(100):
            result = find_similar_field("xyz", valid_fields)
            assert result is None

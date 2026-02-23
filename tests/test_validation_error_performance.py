"""
Performance tests for validation error enhancement.

Verifies that error enhancement adds minimal latency (<5ms).
"""
import time
from typing import Any

import pytest
from pydantic import BaseModel

from fastapi.error_enhancement import (
    ErrorEnhancementConfig,
    enhance_errors,
)


class UserModel(BaseModel):
    username: str
    email: str
    age: int


def create_sample_errors(count: int = 10) -> list[dict[str, Any]]:
    """Create sample Pydantic-style errors for testing."""
    errors = []
    for i in range(count):
        errors.append({
            "type": "string_type",
            "loc": ("body", f"field{i}"),
            "msg": "Input should be a valid string",
            "input": 123,
        })
    return errors


def benchmark_enhance_errors(iterations: int = 1000) -> float:
    """
    Benchmark the enhance_errors function.

    Returns average time per call in milliseconds.
    """
    errors = create_sample_errors(10)
    config = ErrorEnhancementConfig(
        enable_suggestions=True,
        enable_examples=True,
    )

    # Warmup
    for _ in range(10):
        enhance_errors(errors, model=UserModel, config=config)

    # Benchmark
    start = time.perf_counter()
    for _ in range(iterations):
        enhance_errors(errors, model=UserModel, config=config)
    end = time.perf_counter()

    total_time_ms = (end - start) * 1000
    avg_time_ms = total_time_ms / iterations

    return avg_time_ms


class TestPerformance:
    """Performance tests for error enhancement."""

    def test_enhance_errors_performance(self):
        """Test that enhance_errors completes within performance budget."""
        avg_time = benchmark_enhance_errors(iterations=1000)

        # Performance requirement: <5ms average
        assert avg_time < 5.0, f"Expected <5ms, got {avg_time:.2f}ms"

    def test_enhance_single_error_performance(self):
        """Test single error enhancement performance."""
        from fastapi.error_enhancement import enhance_single_error

        error = {
            "type": "string_type",
            "loc": ("body", "username"),
            "msg": "Input should be a valid string",
            "input": 123,
        }
        config = ErrorEnhancementConfig()

        # Warmup
        for _ in range(10):
            enhance_single_error(error, model=UserModel, config=config)

        # Benchmark
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            enhance_single_error(error, model=UserModel, config=config)
        end = time.perf_counter()

        total_time_ms = (end - start) * 1000
        avg_time_ms = total_time_ms / iterations

        assert avg_time_ms < 1.0, f"Expected <1ms, got {avg_time_ms:.2f}ms"

    def test_build_field_path_performance(self):
        """Test field path building performance."""
        from fastapi.error_enhancement import build_field_path

        loc = ("body", "user", "profile", "age", "details", "info")

        # Warmup
        for _ in range(10):
            build_field_path(loc)

        # Benchmark
        iterations = 10000
        start = time.perf_counter()
        for _ in range(iterations):
            build_field_path(loc)
        end = time.perf_counter()

        total_time_ms = (end - start) * 1000
        avg_time_ms = total_time_ms / iterations

        assert avg_time_ms < 0.1, f"Expected <0.1ms, got {avg_time_ms:.4f}ms"

    def test_find_similar_field_name_performance(self):
        """Test similarity finding performance."""
        from fastapi.error_enhancement import find_similar_field_name

        valid_fields = ["username", "email", "age", "address", "phone", "profile"]

        # Warmup
        for _ in range(10):
            find_similar_field_name("usernmae", valid_fields)

        # Benchmark
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            find_similar_field_name("usernmae", valid_fields)
        end = time.perf_counter()

        total_time_ms = (end - start) * 1000
        avg_time_ms = total_time_ms / iterations

        assert avg_time_ms < 1.0, f"Expected <1ms, got {avg_time_ms:.2f}ms"

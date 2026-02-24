"""
Tests for MiddlewareGraph cycle detection and ordering.
"""
import pytest

from fastapi.middleware.graph import MiddlewareConfig, MiddlewareGraph
from fastapi.middleware.exceptions import OrderedMiddlewareError


# Helper middleware classes for testing
class MiddlewareA:
    pass


class MiddlewareB:
    pass


class MiddlewareC:
    pass


class MiddlewareD:
    pass


def test_add_middleware_simple():
    """Test adding a single middleware to the graph."""
    graph = MiddlewareGraph()
    config = MiddlewareConfig(cls=MiddlewareA)

    graph.add_middleware(config)

    assert len(graph) == 1
    assert MiddlewareA in graph


def test_add_middleware_with_dependencies():
    """Test adding middleware with depends_on."""
    graph = MiddlewareGraph()

    # Add A first
    config_a = MiddlewareConfig(cls=MiddlewareA)
    graph.add_middleware(config_a)

    # Add B that depends on A
    config_b = MiddlewareConfig(cls=MiddlewareB, depends_on=(MiddlewareA,))
    graph.add_middleware(config_b)

    assert len(graph) == 2
    assert MiddlewareB in graph


def test_cycle_detection_direct():
    """Test detection of direct circular dependency (A -> A)."""
    graph = MiddlewareGraph()

    # Add A that depends on itself
    config = MiddlewareConfig(cls=MiddlewareA, depends_on=(MiddlewareA,))

    with pytest.raises(OrderedMiddlewareError) as exc_info:
        graph.add_middleware(config)

    assert "Circular dependency detected" in str(exc_info.value)


def test_cycle_detection_indirect():
    """Test detection of indirect circular dependency (A -> B -> C -> A)."""
    graph = MiddlewareGraph()

    # Add A
    config_a = MiddlewareConfig(cls=MiddlewareA)
    graph.add_middleware(config_a)

    # Add B that depends on A
    config_b = MiddlewareConfig(cls=MiddlewareB, depends_on=(MiddlewareA,))
    graph.add_middleware(config_b)

    # Add C that depends on B
    config_c = MiddlewareConfig(cls=MiddlewareC, depends_on=(MiddlewareB,))
    graph.add_middleware(config_c)

    # Add A that depends on C - creates cycle
    config_a_cycle = MiddlewareConfig(cls=MiddlewareA, depends_on=(MiddlewareC,))

    with pytest.raises(OrderedMiddlewareError) as exc_info:
        graph.add_middleware(config_a_cycle)

    assert "Circular dependency detected" in str(exc_info.value)


def test_reference_validation_missing():
    """Test that referencing non-existent middleware raises error."""
    graph = MiddlewareGraph()

    # Add A
    config_a = MiddlewareConfig(cls=MiddlewareA)
    graph.add_middleware(config_a)

    # Add B that depends on C (which doesn't exist)
    config_b = MiddlewareConfig(cls=MiddlewareB, depends_on=(MiddlewareC,))

    with pytest.raises(OrderedMiddlewareError) as exc_info:
        graph.add_middleware(config_b)

    assert "which is not registered" in str(exc_info.value)


def test_topological_sort_simple():
    """Test topological sort returns correct order."""
    graph = MiddlewareGraph()

    # Add C first (no dependencies)
    config_c = MiddlewareConfig(cls=MiddlewareC)
    graph.add_middleware(config_c)

    # Add B that depends on C
    config_b = MiddlewareConfig(cls=MiddlewareB, depends_on=(MiddlewareC,))
    graph.add_middleware(config_b)

    # Add A that depends on B
    config_a = MiddlewareConfig(cls=MiddlewareA, depends_on=(MiddlewareB,))
    graph.add_middleware(config_a)

    # Get execution order
    order = graph.get_execution_order()

    # Should be C, B, A (C has no deps, B depends on C, A depends on B)
    assert order == [MiddlewareC, MiddlewareB, MiddlewareA]


def test_topological_sort_complex():
    """Test topological sort with multiple branches."""
    graph = MiddlewareGraph()

    # Add D first (no dependencies)
    config_d = MiddlewareConfig(cls=MiddlewareD)
    graph.add_middleware(config_d)

    # Add C that depends on D
    config_c = MiddlewareConfig(cls=MiddlewareC, depends_on=(MiddlewareD,))
    graph.add_middleware(config_c)

    # Add B that depends on D
    config_b = MiddlewareConfig(cls=MiddlewareB, depends_on=(MiddlewareD,))
    graph.add_middleware(config_b)

    # Add A that depends on B and C
    config_a = MiddlewareConfig(cls=MiddlewareA, depends_on=(MiddlewareB, MiddlewareC))
    graph.add_middleware(config_a)

    # Get execution order
    order = graph.get_execution_order()

    # D must come first, A must come last
    assert order[0] == MiddlewareD
    assert order[-1] == MiddlewareA


def test_validate_order_no_errors():
    """Test that validate_order returns empty list for valid graph."""
    graph = MiddlewareGraph()

    config_a = MiddlewareConfig(cls=MiddlewareA)
    graph.add_middleware(config_a)

    config_b = MiddlewareConfig(cls=MiddlewareB, depends_on=(MiddlewareA,))
    graph.add_middleware(config_b)

    errors = graph.validate_order()

    assert errors == []


def test_get_config():
    """Test getting middleware config."""
    graph = MiddlewareGraph()

    # Add MiddlewareB first (with no dependencies)
    config_b = MiddlewareConfig(cls=MiddlewareB)
    graph.add_middleware(config_b)

    # Add MiddlewareA that depends on MiddlewareB
    config = MiddlewareConfig(cls=MiddlewareA, depends_on=(MiddlewareB,))
    graph.add_middleware(config)

    retrieved = graph.get_config(MiddlewareA)

    assert retrieved is not None
    assert retrieved.cls == MiddlewareA
    assert retrieved.depends_on == (MiddlewareB,)


def test_get_config_missing():
    """Test getting config for non-existent middleware."""
    graph = MiddlewareGraph()

    retrieved = graph.get_config(MiddlewareA)

    assert retrieved is None


def test_len():
    """Test len() returns correct count."""
    graph = MiddlewareGraph()

    assert len(graph) == 0

    graph.add_middleware(MiddlewareConfig(cls=MiddlewareA))
    assert len(graph) == 1

    graph.add_middleware(MiddlewareConfig(cls=MiddlewareB))
    assert len(graph) == 2


def test_contains():
    """Test __contains__ works correctly."""
    graph = MiddlewareGraph()
    config = MiddlewareConfig(cls=MiddlewareA)

    graph.add_middleware(config)

    assert MiddlewareA in graph
    assert MiddlewareB not in graph

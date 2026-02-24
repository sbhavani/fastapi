"""
MiddlewareGraph tracks middleware ordering and validates dependencies.
"""
from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from fastapi.middleware.config import MiddlewareConfig
from fastapi.middleware.exceptions import OrderedMiddlewareError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fastapi.middleware.typing import MiddlewareProtocol


class MiddlewareGraph:
    """
    Tracks middleware ordering and validates dependencies.

    This class maintains a graph of middleware dependencies and provides
    validation for:
    - Cycle detection (no circular dependencies)
    - Reference validation (all depends_on targets exist)
    - Topological sorting (deterministic execution order)
    """

    def __init__(self) -> None:
        self.nodes: dict[type, MiddlewareConfig] = {}
        self.edges: dict[type, set[type]] = defaultdict(set)

    def add_middleware(self, config: MiddlewareConfig) -> None:
        """
        Add a middleware to the graph.

        Args:
            config: The middleware configuration.

        Raises:
            OrderedMiddlewareError: If the middleware creates a cycle.
        """
        middleware_cls = config.cls

        # Store the config
        self.nodes[middleware_cls] = config

        # Add edges based on depends_on
        for dep in config.depends_on:
            self.edges[middleware_cls].add(dep)

        # Validate immediately
        errors = self.validate_order()
        if errors:
            # Remove the added middleware if validation fails
            del self.nodes[middleware_cls]
            for dep in config.depends_on:
                self.edges[middleware_cls].discard(dep)
            raise OrderedMiddlewareError(
                f"Cannot add middleware {middleware_cls.__name__}: {errors[0]}",
                conflicts=errors,
            )

    def validate_order(self) -> list[str]:
        """
        Validate middleware ordering.

        Returns:
            List of error messages (empty if valid).
        """
        errors: list[str] = []

        # Check 1: Reference validation - all depends_on targets must exist
        errors.extend(self._validate_references())

        # Check 2: Cycle detection
        errors.extend(self._detect_cycles())

        return errors

    def _validate_references(self) -> list[str]:
        """
        Validate that all depends_on references point to registered middleware.

        Returns:
            List of error messages.
        """
        errors: list[str] = []

        for middleware_cls, config in self.nodes.items():
            for dep in config.depends_on:
                if dep not in self.nodes:
                    errors.append(
                        f"Middleware {middleware_cls.__name__} depends on "
                        f"{dep.__name__}, which is not registered"
                    )

        return errors

    def _detect_cycles(self) -> list[str]:
        """
        Detect circular dependencies in the middleware chain.

        Uses DFS to find cycles in the dependency graph.

        Returns:
            List of error messages describing cycles found.
        """
        errors: list[str] = []

        # Use DFS to detect cycles
        visited: set[type] = set()
        rec_stack: set[type] = set()

        def dfs(node: type, path: list[type]) -> list[list[type]]:
            """Returns list of cycles found from this node."""
            cycles: list[list[type]] = []
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.edges.get(node, set()):
                if neighbor not in visited:
                    cycles.extend(dfs(neighbor, path.copy()))
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)

            rec_stack.remove(node)
            return cycles

        # Run DFS from each unvisited node
        for node in self.nodes:
            if node not in visited:
                cycles = dfs(node, [])
                for cycle in cycles:
                    cycle_str = " -> ".join(m.__name__ for m in cycle[:-1])
                    errors.append(
                        f"Circular dependency detected: {cycle_str}"
                    )

        return errors

    def get_execution_order(self) -> list[type]:
        """
        Get the middleware in execution order using topological sort.

        The order is determined by resolving all depends_on relationships.

        Returns:
            List of middleware classes in execution order.

        Raises:
            OrderedMiddlewareError: If topological sort fails.
        """
        # Kahn's algorithm for topological sort
        in_degree: dict[type, int] = defaultdict(int)

        # Calculate in-degrees
        for node in self.nodes:
            in_degree[node] = 0

        for node, deps in self.edges.items():
            for dep in deps:
                if dep in self.nodes:
                    in_degree[node] += 1

        # Start with nodes that have no dependencies
        queue = [node for node in self.nodes if in_degree[node] == 0]
        result: list[type] = []

        while queue:
            # Sort to ensure deterministic order
            queue.sort(key=lambda x: x.__name__)
            node = queue.pop(0)
            result.append(node)

            # Reduce in-degree for dependent nodes
            for dependent in self.nodes:
                if node in self.edges.get(dependent, set()):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        if len(result) != len(self.nodes):
            # This shouldn't happen if validate_order passed
            raise OrderedMiddlewareError(
                "Cannot determine middleware execution order: circular dependency likely"
            )

        return result

    def __len__(self) -> int:
        return len(self.nodes)

    def __contains__(self, middleware_cls: type) -> bool:
        return middleware_cls in self.nodes

    def get_config(self, middleware_cls: type) -> MiddlewareConfig | None:
        """Get the configuration for a middleware class."""
        return self.nodes.get(middleware_cls)


__all__ = [
    "MiddlewareGraph",
    "MiddlewareConfig",
]

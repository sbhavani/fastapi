# Implementation Plan: Plugin System

## Branch
`1-plugin-system`

## Feature
Formal Plugin System with Lifecycle Hooks and OpenAPI Extension

## Technical Context

### Architecture Overview

The plugin system will integrate with FastAPI's existing architecture:

1. **Plugin Registry**: A collection stored on the FastAPI app instance that maintains registered plugins
2. **Lifecycle Integration**: Hooks integrated with FastAPI's existing lifespan event system (`_DefaultLifespan` in `routing.py`)
3. **Request Pipeline**: Plugin request hooks execute as middleware-like layers
4. **OpenAPI Extension**: Plugin contributions merged into `openapi_schema` at generation time

### Key Technical Decisions

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Protocol Definition | `Protocol` class from `typing` | Type-safe interface for plugins, matches Python typing best practices |
| Lifecycle Hooks | Integrate with lifespan | LeverAPI startup/shutdown infrastructure |
| Requestages existing Fast Hooks | Execute before/after routing | Similar execution model to middleware but with plugin-specific context |
| OpenAPI Merging | Post-generation merge | Non-invasive, preserves existing OpenAPI generation logic |
| Plugin Storage | List on app instance | Simple, follows pattern used by `routes`, `middleware` |

### Integration Points

1. **FastAPI app instance** - Store plugin registry at `app._plugins`
2. **APIRouter lifespan** - Integrate plugin lifecycle with `_DefaultLifespan`
3. **get_openapi()** - Extend to accept plugin contributions
4. **Request processing** - Add plugin request hooks to the ASGI pipeline

### Module Structure

```
fastapi/
  plugins/
    __init__.py       # Public API exports
    protocol.py       # PluginProtocol interface
    registry.py       # PluginRegistry class
    types.py          # Type definitions
```

### Unknowns (NEEDS CLARIFICATION)

None identified - the spec is well-defined with clear requirements.

### Dependencies

- Python `typing.Protocol` (stdlib)
- FastAPI existing lifespan handling (`routing.py:_DefaultLifespan`)
- FastAPI OpenAPI generation (`openapi/utils.py:get_openapi`)

---

## Constitution Check

### I. Standards-Based
- **Status**: COMPLIANT
- **Evidence**: Plugin OpenAPI contributions follow OpenAPI 3.0+ specification; plugins can extend paths, components, security schemes

### II. Type Safety (NON-NEGOTIABLE)
- **Status**: COMPLIANT
- **Evidence**: PluginProtocol uses `typing.Protocol` for type-safe interface; mypy will validate plugin implementations

### III. Test-First Development
- **Status**: APPLIES
- **Evidence**: Implementation will include comprehensive tests for all hooks and OpenAPI extension

### IV. Performance
- **Status**: COMPLIANT
- **Evidence**: Plugin hooks use async/await; no blocking in request path; OpenAPI generation is cached

### V. Developer Experience
- **Status**: COMPLIANT
- **Evidence**: Simple `app.add_plugin()` API; optional hooks allow minimal implementation; clear error messages

---

## Phase 0: Research

### Research Summary

The implementation will leverage existing FastAPI patterns:

1. **Protocol-based interface**: Following Python's `typing.Protocol` for structural subtyping
2. **Lifespan integration**: Extending the existing `_DefaultLifespan` to call plugin hooks
3. **Middleware-like request hooks**: Executing in registration order (startup) and reverse order (shutdown)
4. **OpenAPI merging**: Deep merge of plugin contributions into the generated schema

### Design Patterns

| Pattern | Application |
|---------|-------------|
| Registry | Plugin collection with add/iterate/clear operations |
| Hook | Optional async methods called at lifecycle points |
| Merge | Deep dictionary merge for OpenAPI contributions |
| Error Isolation | Try/except with logging for each plugin hook |

---

## Phase 1: Design

### Data Model

#### PluginProtocol

```python
class PluginProtocol(Protocol):
    """Protocol defining the plugin interface."""

    async def on_startup(self) -> None:
        """Called once when the application starts."""
        ...

    async def on_shutdown(self) -> None:
        """Called once when the application stops."""
        ...

    async def before_request(self, request: Request) -> None | Response:
        """Called before each request. Can return a Response to short-circuit."""
        ...

    async def after_request(
        self, request: Request, response: Response
    ) -> Response:
        """Called after each request. Can modify the response."""
        ...

    def openapi_schema(self) -> dict[str, Any] | None:
        """Return OpenAPI schema contributions."""
        ...
```

#### PluginRegistry

```python
class PluginRegistry:
    """Manages registered plugins and their lifecycle."""

    def __init__(self) -> None:
        self._plugins: list[PluginProtocol] = []

    def add(self, plugin: PluginProtocol) -> None:
        """Register a plugin."""
        ...

    async def on_startup(self) -> None:
        """Call on_startup for all plugins."""
        ...

    async def on_shutdown(self) -> None:
        """Call on_shutdown for all plugins (reverse order)."""
        ...

    async def before_request(self, request: Request) -> Response | None:
        """Call before_request for all plugins."""
        ...

    async def after_request(
        self, request: Request, response: Response
    ) -> Response:
        """Call after_request for all plugins (reverse order)."""
        ...

    def get_openapi_contributions(self) -> dict[str, Any]:
        """Aggregate OpenAPI contributions from all plugins."""
        ...
```

### Interface Contracts

#### Public API

1. **`app.add_plugin(plugin: PluginProtocol) -> None`**
   - Register a plugin with the application
   - Raises `TypeError` if plugin doesn't implement Protocol

2. **`app.plugins: PluginRegistry`**
   - Read-only access to the plugin registry

#### Plugin Protocol

- All methods are optional (default no-op implementation)
- Async methods: `on_startup`, `on_shutdown`, `before_request`, `after_request`
- Sync property/method: `openapi_schema`

### Hook Execution Order

| Hook | Execution Order |
|------|-----------------|
| on_startup | Registration order (FIFO) |
| on_shutdown | Reverse registration order (LIFO) |
| before_request | Registration order (FIFO) |
| after_request | Reverse registration order (LIFO) |

### Error Handling

- Each plugin hook wrapped in try/except
- Errors logged with plugin identifier
- Processing continues to next plugin
- Application lifecycle continues regardless of plugin errors

### OpenAPI Merging Strategy

- Deep merge of plugin contributions into base schema
- Keys: `paths`, `components`, `security`, `tags`, `servers`
- Later plugins can override earlier ones (last-wins for conflicts)

---

## Next Steps

### Phase 2: Implementation Tasks

1. Create `fastapi/plugins/` module
2. Implement `PluginProtocol` in `protocol.py`
3. Implement `PluginRegistry` in `registry.py`
4. Add `add_plugin()` method to FastAPI app
5. Integrate lifecycle hooks with lifespan
6. Add request pipeline hooks
7. Extend OpenAPI generation
8. Write comprehensive tests
9. Add documentation

---

## Artifacts

- **SPEC**: `specs/1-plugin-system/spec.md`
- **Plan**: `specs/1-plugin-system/plan.md`
- **Research**: `specs/1-plugin-system/research.md`
- **Data Model**: `specs/1-plugin-system/data-model.md`
- **Contracts**: `specs/1-plugin-system/contracts/plugin-protocol.md`

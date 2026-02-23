# Data Model: Plugin System

## Entities

### 1. PluginProtocol

The interface defining the contract for all plugins.

**Type**: Protocol (structural interface)

**Fields/Methods**:

| Field/Method | Type | Required | Description |
|--------------|------|----------|-------------|
| `on_startup()` | `Coroutine[Any, Any, None]` | No | Called when app starts |
| `on_shutdown()` | `Coroutine[Any, Any, None]` | No | Called when app stops |
| `before_request(request: Request)` | `Coroutine[Any, Any, Response \| None]` | No | Called before each request; can return Response to short-circuit |
| `after_request(request: Request, response: Response)` | `Coroutine[Any, Any, Response]` | No | Called after each request; can modify response |
| `openapi_schema` | `dict[str, Any] \| None` | No | OpenAPI schema contributions |

**Validation Rules**:
- All methods are optional - implementers can omit any method
- Methods default to no-op implementations
- Type checking validates conformance via structural subtyping

---

### 2. PluginRegistry

Manages registered plugins and coordinates their lifecycle.

**Type**: Class

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `_plugins` | `list[PluginProtocol]` | Internal storage for registered plugins |

**Methods**:

| Method | Parameters | Return | Description |
|--------|------------|--------|-------------|
| `add()` | `plugin: PluginProtocol` | `None` | Register a new plugin |
| `on_startup()` | None | `Coroutine[Any, Any, None]` | Call on_startup for all plugins |
| `on_shutdown()` | None | `Coroutine[Any, Any, None]` | Call on_shutdown for all plugins (reverse order) |
| `before_request()` | `request: Request` | `Coroutine[Any, Any, Response \| None]` | Call before_request for all plugins |
| `after_request()` | `request: Request, response: Response` | `Coroutine[Any, Any, Response]` | Call after_request for all plugins |
| `get_openapi_contributions()` | None | `dict[str, Any]` | Aggregate OpenAPI contributions |

**Validation Rules**:
- `add()` validates plugin implements PluginProtocol
- Duplicate plugins allowed (registered separately)
- Empty registry returns empty contributions

---

### 3. Plugin Instance

A concrete implementation of PluginProtocol registered with the application.

**Type**: Object (implements PluginProtocol)

**Example**:
```python
class DatabasePlugin:
    async def on_startup(self) -> None:
        await self.pool.connect()

    async def on_shutdown(self) -> None:
        await self.pool.disconnect()

    def openapi_schema(self) -> dict:
        return {
            "components": {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer"
                    }
                }
            }
        }
```

---

### 4. OpenAPI Contribution

A dictionary of OpenAPI schema fragments contributed by a plugin.

**Type**: `dict[str, Any]`

**Structure**:
```python
{
    "paths": {...},        # Optional: Path definitions
    "components": {...},   # Optional: Schema/components
    "security": [...],      # Optional: Security requirements
    "tags": [...],         # Optional: Tag definitions
    "servers": [...]       # Optional: Server definitions
}
```

**Validation Rules**:
- Must be valid OpenAPI 3.0 dictionary structure
- Merged with base schema via deep merge
- Conflicts resolved by last-plugin-wins

---

## Relationships

```
FastAPI App
    |
    +-- plugins: PluginRegistry
            |
            +-- _plugins: list[PluginProtocol]
                    |
                    +-- Plugin Instance 1
                    +-- Plugin Instance 2
                    +-- ...
```

---

## State Transitions

### Plugin Lifecycle

```
Registered
    |
    v
[App Startup] --> on_startup() called
    |
    v
[Request Handling] --> before_request() / after_request() called per request
    |
    v
[App Shutdown] --> on_shutdown() called
```

### OpenAPI Generation

```
Base OpenAPI Schema
    |
    v
Plugin Contributions (aggregated from all plugins)
    |
    v
Merged OpenAPI Schema (returned by get_openapi())
```

---

## Edge Cases

1. **No plugins registered**: All hooks are no-ops; OpenAPI unchanged
2. **Plugin raises exception**: Error logged; next plugin continues
3. **Plugin returns Response in before_request**: Short-circuits request handling
4. **Plugin modifies response**: Changes visible to client
5. **Multiple plugins with same OpenAPI key**: Last plugin wins
6. **Plugin is sync while app is async**: Framework handles conversion

# Data Model: Plugin System

## Entities

### 1. PluginProtocol

**Description**: Interface defining the contract for all plugins.

**Type**: `typing.Protocol` (runtime checkable)

**Fields/Methods**:

| Field/Method | Type | Required | Description |
|--------------|------|----------|-------------|
| on_startup | Callable[[], Awaitable[Any]] \| None | No | Async callable executed on app startup |
| on_shutdown | Callable[[], Awaitable[Any]] \| None | No | Async callable executed on app shutdown |
| before_request | Callable[[Request], Awaitable[Response \| None]] \| None | No | Async callable executed before each request; returning Response skips endpoint |
| after_request | Callable[[Request, Response], Awaitable[Response]] \| None | No | Async callable executed after request, can modify response |
| get_openapi_schema | Callable[[dict[str, Any]], dict[str, Any]] \| None | No | Callback to extend OpenAPI schema |

### 2. PluginInstance

**Description**: Internal representation of a registered plugin.

**Type**: Dataclass

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| name | str | Plugin identifier (class name) |
| instance | PluginProtocol | The plugin object |
| order | int | Execution order (lower = earlier) |

### 3. PluginManager

**Description**: Manages plugin registration and execution.

**Type**: Class

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| plugins | list[PluginInstance] | Ordered list of registered plugins |

**Methods**:

| Method | Description |
|--------|-------------|
| add_plugin(plugin) | Register a new plugin |
| get_plugins() | Get all registered plugins |
| on_startup() | Execute all startup hooks |
| on_shutdown() | Execute all shutdown hooks |

## Validation Rules

1. Plugin name must be unique (raise on duplicate)
2. Lifecycle hooks must be async callables if provided
3. before_request must accept Request, return Response | None
4. after_request must accept Request and Response, return Response
5. get_openapi_schema must accept dict, return dict

## State Transitions

```
Unregistered → Registered: add_plugin() called
Registered → Active: on_startup() executed
Active → Shutting Down: on_shutdown() executing
Shutting Down → Unregistered: cleanup complete
```

## Relationships

```
FastAPI app
    │
    ├── has_one ──► PluginManager
    │
    └── uses ──► PluginProtocol (interface)
                     │
                     ├── on_startup ──► lifespan startup
                     ├── on_shutdown ──► lifespan shutdown
                     ├── before_request ──► middleware
                     ├── after_request ──► middleware
                     └── get_openapi_schema ──► openapi()
```

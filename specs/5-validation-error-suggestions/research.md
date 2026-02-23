# Research: Validation Error Enhancement

## Decision 1: String Similarity Algorithm

**Question**: What algorithm should be used to detect typos in field names?

### Options Evaluated

1. **Levenshtein Distance (Edit Distance)**
   - Pros: Simple, well-understood, works well for short strings
   - Cons: O(n*m) time complexity
   - Implementation: `python-Levenshtein` package or custom

2. **Jaro-Winkler Similarity**
   - Pros: Better for names, prefixes weighted higher
   - Cons: More complex implementation

3. **Python difflib (built-in)**
   - Pros: No external dependencies, included in standard library
   - Cons: Less accurate for typos

### Decision: Use difflib with custom threshold

**Rationale**: For field names (typically <50 chars), `difflib.get_close_matches` provides sufficient accuracy without external dependencies. A custom edit-distance function can be added if accuracy is insufficient.

**Threshold**: Edit distance of 3 or less (configurable) indicates likely typo

---

## Decision 2: Error Enhancement Location

**Question**: Where should enhancement logic reside?

### Options Evaluated

1. **In exception handlers** (`exception_handlers.py`)
   - Pros: Direct access to request context
   - Cons: Mixes concerns, harder to test

2. **In dedicated module** (`error_enhancement.py`)
   - Pros: Single responsibility, easier to test
   - Cons: Additional module to maintain

3. **In ValidationException class**
   - Pros: Encapsulated, errors enhanced at source
   - Cons: Tighter coupling with exception logic

### Decision: Dedicated module with exception handler integration

**Rationale**: Separates enhancement logic from exception handling, allowing reuse and easier testing. The exception handler calls the enhancement functions.

---

## Decision 3: Field Path Format

**Question**: How should the field path be formatted in the response?

### Options Evaluated

1. **Pydantic loc tuple** - `["body", "user", "age"]`
   - Pros: Already provided by Pydantic
   - Cons: Less readable for API consumers

2. **Dot notation** - `"body.user.age"`
   - Pros: More readable, common pattern
   - Cons: Requires conversion

3. **JSON Pointer** - `"/body/user/age"`
   - Pros: Standard format (RFC 6901)
   - Cons: Less intuitive for web developers

### Decision: Dot notation with index for arrays

**Format**: `body.user.profile.age` for nested, `body.items[2].name` for list items

**Rationale**: Most intuitive for Python/web developers, consistent with error message conventions

---

## Decision 4: Example Value Generation

**Question**: How to generate meaningful examples?

### Options Evaluated

1. **Use Pydantic field default**
   - If field has default, show it as example

2. **Use type-based examples**
   - For `int`: "e.g., 42"
   - For `str`: "e.g., 'example'"
   - For `bool`: "e.g., true"

3. **Use JSON Schema example**
   - If schema includes example, use it

### Decision: Type-based with default override

**Rationale**: Most fields don't have defaults, so type-based examples are more universally applicable. When defaults exist, they provide more context.

---

## Implementation Approach Summary

1. **New file**: `fastapi/error_enhancement.py`
   - `build_field_path(loc)`: Convert Pydantic loc to dot notation
   - `find_similar_field_name()`: Find close matches in model fields
   - `get_example_for_type()`: Generate type-based examples
   - `enhance_errors()`: Main enhancement function

2. **Modified**: `fastapi/exception_handlers.py`
   - Import enhancement functions
   - Apply enhancement before returning response

3. **Testing**:
   - Unit tests for enhancement functions
   - Integration tests for actual API errors
   - Performance benchmarks

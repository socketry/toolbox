# Debugger Abstraction Architecture

## Overview

The debugger abstraction provides a unified Python API that works with both GDB and LLDB, allowing Ruby debugging extensions to work across platforms and debuggers.

## Design Goals

1. **Zero-cost abstraction**: Thin wrapper with no performance overhead
2. **Progressive enhancement**: Easy to add debugger-specific code when needed
3. **Maintainable**: Clear separation between common and debugger-specific code
4. **Testable**: Can test with either debugger
5. **Future-proof**: Easy to extend to other debuggers if needed

## Directory Structure

```
data/ruby/gdb/
├── debugger.py              # Main entry point - auto-detection and export
├── debugger/
│   ├── __init__.py          # Package initialization
│   ├── gdb.py               # GDB backend implementation
│   ├── lldb.py              # LLDB backend implementation
│   ├── README.md            # User documentation
│   ├── MIGRATION.md         # Migration guide
│   ├── API_COMPARISON.md    # GDB vs LLDB API reference
│   ├── ARCHITECTURE.md      # This file
│   └── example.py           # Usage example
```

## Component Diagram

```
┌─────────────────────────────────────────────────────┐
│              User Code (object.py, etc)             │
│                                                     │
│  import debugger                                    │
│  value = debugger.parse_and_eval("$var")           │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│                   debugger.py                       │
│                                                     │
│  - Auto-detect GDB or LLDB                         │
│  - Load appropriate backend                         │
│  - Export unified interface                         │
└─────────────────────────────────────────────────────┘
                          │
                          ├─────────────┐
                          ▼             ▼
            ┌──────────────────┐  ┌──────────────────┐
            │  debugger/gdb.py │  │ debugger/lldb.py │
            │                  │  │                  │
            │  GDB Backend     │  │  LLDB Backend    │
            └──────────────────┘  └──────────────────┘
                          │             │
                          ▼             ▼
                    ┌──────────┐  ┌───────────┐
                    │   GDB    │  │   LLDB    │
                    └──────────┘  └───────────┘
```

## API Layers

### Layer 1: Native Debugger API
The raw Python API provided by GDB or LLDB.

**GDB Example:**
```python
import gdb
value = gdb.parse_and_eval("$var")
flags = int(value.cast(gdb.lookup_type("struct RBasic").pointer())['flags'])
```

**LLDB Example:**
```python
import lldb
frame = lldb.debugger.GetSelectedTarget().GetProcess().GetSelectedThread().GetSelectedFrame()
value = frame.EvaluateExpression("$var")
flags = value.Cast(lldb.debugger.GetSelectedTarget().FindFirstType("struct RBasic").GetPointerType()).GetChildMemberWithName('flags').GetValueAsUnsigned()
```

### Layer 2: Backend Wrappers
Debugger-specific implementations of the unified interface.

**debugger/gdb.py:**
```python
class Value:
    def __init__(self, gdb_value):
        self._value = gdb_value
    
    def cast(self, type_obj):
        return Value(self._value.cast(type_obj._type))
```

**debugger/lldb.py:**
```python
class Value:
    def __init__(self, lldb_value):
        self._value = lldb_value
    
    def cast(self, type_obj):
        return Value(self._value.Cast(type_obj._type))
```

### Layer 3: Unified Interface
The common API that works with both debuggers.

**debugger.py:**
```python
# Auto-detect and load backend
try:
    import gdb
    from debugger import gdb as _backend
except ImportError:
    import lldb
    from debugger import lldb as _backend

# Export unified interface
Value = _backend.Value
parse_and_eval = _backend.parse_and_eval
```

### Layer 4: User Code
Ruby debugging extensions that use the unified API.

```python
import debugger

value = debugger.parse_and_eval("$var")
rbasic = value.cast(debugger.lookup_type("struct RBasic").pointer())
flags = int(rbasic.dereference()['flags'])
```

## Class Hierarchy

```
Value (Abstract Concept)
├── debugger.Value        → Exported from debugger.py
├── gdb.Value         → Wraps gdb.Value
└── lldb.Value        → Wraps lldb.SBValue

Type (Abstract Concept)
├── debugger.Type         → Exported from debugger.py
├── gdb.Type          → Wraps gdb.Type
└── lldb.Type         → Wraps lldb.SBType

Command (Abstract Concept)
├── debugger.Command      → Exported from debugger.py
├── gdb.Command       → Wraps gdb.Command
└── lldb.Command      → Custom implementation
```

## Data Flow

### Expression Evaluation

```
User: debugger.parse_and_eval("$var")
  │
  ├─→ GDB path:
  │   debugger.py → debugger/gdb.py → gdb.parse_and_eval()
  │                                  → gdb.Value
  │                                  → debugger.gdb.Value(gdb_value)
  │                                  → return to user
  │
  └─→ LLDB path:
      debugger.py → debugger/lldb.py → frame.EvaluateExpression()
                                      → lldb.SBValue
                                      → debugger.lldb.Value(sbvalue)
                                      → return to user
```

## Key Design Decisions

### 1. Runtime Detection
**Decision**: Detect debugger at import time by trying to import `gdb` or `lldb`.

**Rationale**:
- Simple and reliable
- No configuration needed
- Fails fast if neither debugger is available

**Alternative considered**: Environment variable to specify debugger
- Rejected: More complex, error-prone

### 2. Backend Module Structure
**Decision**: Separate modules (`debugger/gdb.py`, `debugger/lldb.py`) implementing the same interface.

**Rationale**:
- Clear separation of concerns
- Easy to maintain each backend independently
- Can optimize each backend for its debugger
- Easy to add new backends

**Alternative considered**: Single module with `if` statements
- Rejected: Would become unmaintainable

### 3. Wrapper Classes vs Functions
**Decision**: Use wrapper classes for values and types, functions for utilities.

**Rationale**:
- Values/types need state (the native object)
- Wrappers enable method chaining: `value.cast(type).dereference()['field']`
- Functions for stateless operations are simpler

**Alternative considered**: All functions, no classes
- Rejected: Would lose method chaining, harder to use

### 4. Native Value Access
**Decision**: Provide `.native` property to access underlying GDB/LLDB value.

**Rationale**:
- Escape hatch for debugger-specific operations
- Enables progressive migration (don't need to abstract everything at once)
- Useful for debugging the abstraction itself

**Alternative considered**: No access to native values
- Rejected: Too restrictive, would require abstracting everything

### 5. Error Handling
**Decision**: Export debugger-specific exception types as `debugger.Error` and `debugger.MemoryError`.

**Rationale**:
- Users expect to catch errors
- Different debuggers have different error types
- Mapping to common exceptions simplifies user code

**Alternative considered**: Define our own exception hierarchy
- Rejected: Overengineered for this use case

## Extension Points

### Adding New Debuggers
To add support for a new debugger (e.g., `pdb`, `rr`):

1. Create `debugger/new_debugger.py`
2. Implement the required interface:
   - `Value` class
   - `Type` class
   - `Command` class
   - `parse_and_eval()` function
   - `lookup_type()` function
   - Constants: `COMMAND_DATA`, `COMMAND_USER`, etc.
3. Update `debugger.py` detection logic
4. Test with Ruby debugging commands

### Adding New Operations
To add a new operation to the abstraction:

1. Add method/function to both backends
2. Export from `debugger.py`
3. Document in README.md
4. Add to API_COMPARISON.md
5. Update MIGRATION.md if it affects existing code

## Performance Considerations

### Wrapper Overhead
- **Minimal**: Wrappers just delegate to native objects
- **No data copying**: Wrappers hold references, not copies
- **Method call overhead**: One extra function call per operation (~10-100ns)

### Backend Detection
- **Once per import**: Detection happens at module import time
- **Cached**: Backend module is imported once and reused

### Type Lookups
- **Backend-specific caching**: Each backend can cache types as appropriate
- GDB caches types automatically
- LLDB requires manual caching (can be added to backend)

## Testing Strategy

### Unit Tests
Test each backend independently:
```python
# test_gdb_backend.py
from debugger import gdb

def test_value_cast():
    # Test GDB backend in isolation
    pass

# test_lldb_backend.py
from debugger import lldb

def test_value_cast():
    # Test LLDB backend in isolation
    pass
```

### Integration Tests
Test unified interface with both debuggers:
```python
# test_integration.py
import debugger

def test_value_operations():
    # This test runs with whichever debugger is available
    value = debugger.parse_and_eval("$var")
    assert int(value) >= 0
```

### Comparison Tests
Run same code with both debuggers and compare results:
```bash
# Run with GDB
gdb --batch -ex "py exec(open('test.py').read())" > gdb_output.txt

# Run with LLDB
lldb --batch -o "script exec(open('test.py').read())" > lldb_output.txt

# Compare
diff gdb_output.txt lldb_output.txt
```

## Future Enhancements

### Potential Additions
1. **Async support**: For debuggers with async APIs
2. **Type inference**: Automatic type detection and casting
3. **Pretty printing**: Unified pretty-printer registration
4. **Breakpoint abstraction**: Common breakpoint API
5. **Memory profiling**: Unified memory access patterns
6. **Symbol lookup**: Cross-debugger symbol resolution

### LLDB Improvements Needed
1. Context caching (target, process, thread, frame)
2. Better convenience variable implementation
3. Command registration improvements
4. Error handling refinement
5. Testing with real Ruby processes

## References

- [GDB Python API Documentation](https://sourceware.org/gdb/current/onlinedocs/gdb/Python-API.html)
- [LLDB Python API Documentation](https://lldb.llvm.org/use/python-reference.html)
- [Python Abstract Base Classes](https://docs.python.org/3/library/abc.html)
- [Strategy Pattern](https://refactoring.guru/design-patterns/strategy)


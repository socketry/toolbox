# Unified Debugger Abstraction Layer

This directory contains a unified abstraction layer that allows Ruby debugging scripts to work with both **GDB** and **LLDB**.

## Architecture

```
debugger.py              # Main interface - auto-detects and loads backend
├── debugger/
    ├── __init__.py      # Package marker
    ├── gdb.py           # GDB backend implementation
    ├── lldb.py          # LLDB backend implementation
    ├── example.py       # Example usage
    ├── MIGRATION.md     # Migration guide from GDB-only code
    └── README.md        # This file
```

## How It Works

1. **Auto-detection**: `debugger.py` detects which debugger is running by trying to import `gdb` or `lldb`
2. **Backend loading**: Loads the appropriate backend implementation (`debugger/gdb.py` or `debugger/lldb.py`)
3. **Unified API**: Exports a common interface that works identically in both debuggers

## Core API

### Value Operations

```python
import debugger

# Evaluate expressions
value = debugger.parse_and_eval("$var")

# Type operations
rbasic_type = debugger.lookup_type("struct RBasic")
basic = value.cast(rbasic_type.pointer())

# Dereferencing and field access
flags = basic.dereference()['flags']

# Convert to integer
val_int = int(value)

# Pointer arithmetic
next_value = value + 1
```

### Type Operations

```python
# Lookup types
value_type = debugger.lookup_type("VALUE")
rstring_type = debugger.lookup_type("struct RString")

# Get pointer type
ptr_type = value_type.pointer()
```

### Commands

```python
class MyCommand(debugger.Command):
    def __init__(self):
        super().__init__("my-command", debugger.COMMAND_DATA)
    
    def invoke(self, arg, from_tty):
        value = debugger.parse_and_eval(arg)
        print(f"Value: {value}")

# Register
MyCommand()
```

### Utilities

```python
# Set convenience variables
debugger.set_convenience_variable('my_var', value)

# Execute commands
debugger.execute("bt")

# Invalidate frame cache (for context switching)
debugger.invalidate_cached_frames()
```

### Exception Handling

```python
try:
    value = debugger.parse_and_eval("$var")
except debugger.Error:
    print("Evaluation failed")
except debugger.MemoryError:
    print("Memory access failed")
```

### Debugger Detection

```python
if debugger.DEBUGGER_NAME == 'gdb':
    # GDB-specific code
    pass
elif debugger.DEBUGGER_NAME == 'lldb':
    # LLDB-specific code
    pass
```

## Design Principles

### 1. Minimal Surface Area
The abstraction only covers common operations needed for Ruby debugging:
- Value evaluation and type casting
- Memory access and pointer arithmetic
- Command registration
- Basic utilities

### 2. Zero-Cost Abstraction
The wrapper is thin - just API translation. No performance overhead.

### 3. Escape Hatches
You can always access native values:
```python
value = debugger.parse_and_eval("$var")
native_value = value.native  # Get gdb.Value or lldb.SBValue
```

### 4. Progressive Enhancement
Start with the common API, add debugger-specific code where needed:
```python
if debugger.DEBUGGER_NAME == 'gdb':
    # GDB-specific advanced features
    import gdb.unwinder
    # ...
elif debugger.DEBUGGER_NAME == 'lldb':
    # LLDB-specific advanced features
    # ...
```

## What's Covered

✅ **Fully abstracted** (works identically):
- Expression evaluation
- Type lookups and casting
- Value dereferencing
- Field/array access
- Pointer arithmetic
- Integer conversion
- Command registration
- Basic error handling

⚠️ **Partially abstracted** (may have quirks):
- Convenience variables (LLDB implementation is limited)
- Command execution
- Frame cache invalidation

❌ **Not abstracted** (debugger-specific):
- Frame unwinders (completely different between debuggers)
- Breakpoint management
- Debugger-specific configuration

## Migration Path

### Phase 1: Core Operations (Easy)
Replace `gdb` imports with `debugger` imports. Most code works unchanged.

**Effort**: Low  
**Compatibility**: 95%+

### Phase 2: Commands (Medium)
Update command class inheritance. Minor changes needed.

**Effort**: Medium  
**Compatibility**: 90%+

### Phase 3: Advanced Features (Hard)
Add conditional code for debugger-specific features.

**Effort**: High  
**Compatibility**: Varies by feature

## Testing

### With GDB
```bash
# Load ruby-gdb with debugger abstraction
gdb --batch -ex "python exec(open('debugger/example.py').read())"
```

### With LLDB
```bash
# Load with LLDB (when LLDB backend is fully implemented)
lldb --batch -o "script exec(open('debugger/example.py').read())"
```

## Current Status

- ✅ GDB backend: Fully implemented and tested
- 🚧 LLDB backend: Proof-of-concept, needs testing and refinement
- 📝 Migration guide: Complete
- 📚 Documentation: Complete
- 🧪 Examples: Basic example provided

## Next Steps

1. **Test LLDB backend** with real Ruby processes
2. **Migrate existing commands** to use abstraction (starting with simple ones)
3. **Handle edge cases** discovered during migration
4. **Add integration tests** that work in both debuggers
5. **Document LLDB-specific setup** and usage patterns

## Benefits

### For Users
- **Choice**: Use GDB or LLDB based on platform/preference
- **Better macOS support**: LLDB is the native debugger on macOS
- **Cross-platform**: Same tools work on Linux (GDB) and macOS (LLDB)

### For Developers
- **Cleaner code**: Single implementation for both debuggers
- **Easier testing**: Can test with either debugger
- **Future-proof**: Easy to add support for new debuggers

## References

- [GDB Python API](https://sourceware.org/gdb/current/onlinedocs/gdb/Python-API.html)
- [LLDB Python API](https://lldb.llvm.org/use/python-reference.html)
- [Facebook Folly Fibers GDB script](https://github.com/facebook/folly/blob/main/folly/fibers/scripts/gdb.py) - Inspiration for fiber debugging


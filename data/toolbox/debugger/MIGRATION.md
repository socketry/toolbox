# Migration Guide: GDB → Unified Debugger API

This guide shows how to migrate existing GDB-specific code to use the unified debugger interface.

## Import Changes

**Before (GDB-only):**
```python
import gdb
import constants
```

**After (GDB + LLDB):**
```python
import debugger
import constants
```

## Value Operations

**Before:**
```python
# Parse and evaluate
value = gdb.parse_and_eval("$var")

# Type casting
basic = value.cast(gdb.lookup_type("struct RBasic").pointer())

# Dereferencing
flags = basic.dereference()['flags']

# Integer conversion
val_int = int(value)
```

**After:**
```python
# Parse and evaluate
value = debugger.parse_and_eval("$var")

# Type casting
basic = value.cast(debugger.lookup_type("struct RBasic").pointer())

# Dereferencing
flags = basic.dereference()['flags']

# Integer conversion
val_int = int(value)
```

## Type Lookups

**Before:**
```python
rbasic_type = gdb.lookup_type('struct RBasic').pointer()
value_type = gdb.lookup_type('VALUE')
```

**After:**
```python
rbasic_type = debugger.lookup_type('struct RBasic').pointer()
value_type = debugger.lookup_type('VALUE')
```

## Command Definition

**Before:**
```python
class MyCommand(gdb.Command):
    def __init__(self):
        super(MyCommand, self).__init__("my-command", gdb.COMMAND_DATA)
    
    def invoke(self, arg, from_tty):
        try:
            value = gdb.parse_and_eval(arg)
            print(f"Value: {value}")
        except gdb.error as e:
            print(f"Error: {e}")

# Register
MyCommand()
```

**After:**
```python
class MyCommand(debugger.Command):
    def __init__(self):
        super(MyCommand, self).__init__("my-command", debugger.COMMAND_DATA)
    
    def invoke(self, arg, from_tty):
        try:
            value = debugger.parse_and_eval(arg)
            print(f"Value: {value}")
        except debugger.Error as e:
            print(f"Error: {e}")

# Register
MyCommand()
```

## Exception Handling

**Before:**
```python
try:
    value = gdb.parse_and_eval("invalid")
except gdb.error:
    print("Parse error")
except gdb.MemoryError:
    print("Memory error")
```

**After:**
```python
try:
    value = debugger.parse_and_eval("invalid")
except debugger.Error:
    print("Parse error")
except debugger.MemoryError:
    print("Memory error")
```

## Convenience Variables

**Before:**
```python
gdb.set_convenience_variable('fiber', fiber_value)
```

**After:**
```python
debugger.set_convenience_variable('fiber', fiber_value)
```

## Executing Commands

**Before:**
```python
gdb.execute(f"bt", from_tty=True)
```

**After:**
```python
debugger.execute(f"bt", from_tty=True)
```

## Working with Native Values

If you need to access the native debugger value (e.g., for debugger-specific operations):

```python
value = debugger.parse_and_eval("$var")

# Get native GDB or LLDB value
native_value = value.native

# Now you can use debugger-specific APIs
if debugger.DEBUGGER_NAME == 'gdb':
    # GDB-specific code
    print(native_value.type.code)
elif debugger.DEBUGGER_NAME == 'lldb':
    # LLDB-specific code
    print(native_value.GetType().GetTypeClass())
```

## Checking Current Debugger

```python
import debugger

if debugger.DEBUGGER_NAME == 'gdb':
    print("Running under GDB")
elif debugger.DEBUGGER_NAME == 'lldb':
    print("Running under LLDB")
```

## Advanced: Frame Unwinders

Frame unwinders are highly debugger-specific. For these, you'll need conditional code:

```python
import debugger

if debugger.DEBUGGER_NAME == 'gdb':
    import gdb.unwinder
    
    class MyUnwinder(gdb.unwinder.Unwinder):
        # GDB-specific unwinder
        pass
    
    gdb.unwinder.register_unwinder(None, MyUnwinder())

elif debugger.DEBUGGER_NAME == 'lldb':
    # LLDB uses frame recognizers instead
    # Implementation would be completely different
    pass
```

## Migration Strategy

1. **Phase 1**: Convert core value/type operations (easy, API is 1:1)
2. **Phase 2**: Convert command definitions (straightforward)
3. **Phase 3**: Handle debugger-specific features with conditional code
4. **Phase 4**: Add LLDB-specific implementations for advanced features

## Compatibility Notes

- Most core operations have identical APIs between debuggers
- Advanced features (unwinders, frame recognizers) require conditional code
- LLDB requires more explicit context (target, process, thread, frame)
- Some operations may have performance differences between debuggers


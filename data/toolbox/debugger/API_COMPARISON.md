# GDB vs LLDB Python API Comparison

Quick reference for equivalent operations in GDB and LLDB Python APIs.

## Expression Evaluation

| Operation | GDB | LLDB |
|-----------|-----|------|
| **Evaluate expression** | `gdb.parse_and_eval("$var")` | `frame.EvaluateExpression("$var")` |
| **Context** | Global | Requires frame context |
| **Return type** | `gdb.Value` | `lldb.SBValue` |

## Value Operations

| Operation | GDB | LLDB |
|-----------|-----|------|
| **To integer** | `int(value)` | `value.GetValueAsUnsigned()` |
| **To string** | `str(value)` | `value.GetValue()` |
| **Cast** | `value.cast(type)` | `value.Cast(type)` |
| **Dereference** | `value.dereference()` | `value.Dereference()` |
| **Address of** | `value.address` | `value.AddressOf()` |
| **Field access** | `value['field']` | `value.GetChildMemberWithName('field')` |
| **Array access** | `value[0]` | `value.GetChildAtIndex(0)` |
| **Pointer arithmetic** | `value + offset` | Manual calculation with `CreateValueFromAddress()` |

## Type Operations

| Operation | GDB | LLDB |
|-----------|-----|------|
| **Lookup type** | `gdb.lookup_type("struct Foo")` | `target.FindFirstType("struct Foo")` |
| **Pointer type** | `type.pointer()` | `type.GetPointerType()` |
| **Type name** | `str(type)` | `type.GetName()` |
| **Type size** | `type.sizeof` | `type.GetByteSize()` |
| **Get value type** | `value.type` | `value.GetType()` |

## Command Registration

### GDB
```python
class MyCommand(gdb.Command):
    def __init__(self):
        super(MyCommand, self).__init__("my-cmd", gdb.COMMAND_DATA)
    
    def invoke(self, arg, from_tty):
        print(f"Args: {arg}")

MyCommand()  # Auto-registers
```

### LLDB
```python
def my_command(debugger, command, result, internal_dict):
    print(f"Args: {command}")

def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand(
        'command script add -f my_module.my_command my-cmd'
    )
```

## Convenience Variables

| Operation | GDB | LLDB |
|-----------|-----|------|
| **Set variable** | `gdb.set_convenience_variable('var', value)` | Variables are more limited, use persistent expressions |
| **Prefix** | `$var` | `$var` |

## Executing Commands

| Operation | GDB | LLDB |
|-----------|-----|------|
| **Execute** | `gdb.execute("bt")` | `interpreter.HandleCommand("bt", result)` |
| **Context** | Global | Requires interpreter from debugger |

## Exception Handling

| Operation | GDB | LLDB |
|-----------|-----|------|
| **General error** | `gdb.error` | No specific exception class |
| **Memory error** | `gdb.MemoryError` | No specific exception class |
| **Type error** | Python `TypeError` | Python `TypeError` |

## Context Objects

### GDB
```python
# Most operations are global
value = gdb.parse_and_eval("$var")
type = gdb.lookup_type("int")
```

### LLDB
```python
# Most operations require context
debugger = lldb.debugger
target = debugger.GetSelectedTarget()
process = target.GetProcess()
thread = process.GetSelectedThread()
frame = thread.GetSelectedFrame()

value = frame.EvaluateExpression("$var")
type = target.FindFirstType("int")
```

## Frame Operations

| Operation | GDB | LLDB |
|-----------|-----|------|
| **Get frame** | `gdb.selected_frame()` | `thread.GetSelectedFrame()` |
| **Frame info** | `frame.name()`, `frame.pc()` | `frame.GetFunctionName()`, `frame.GetPC()` |
| **Locals** | `frame.read_var("x")` | `frame.FindVariable("x")` |
| **Registers** | `frame.read_register("rax")` | `frame.FindRegister("rax")` |

## Frame Unwinding

### GDB
```python
import gdb.unwinder

class MyUnwinder(gdb.unwinder.Unwinder):
    def __init__(self):
        super(MyUnwinder, self).__init__("My Unwinder")
    
    def __call__(self, pending_frame):
        # Return gdb.unwinder.UnwindInfo or None
        frame_id = gdb.unwinder.FrameId(sp, pc)
        unwind_info = pending_frame.create_unwind_info(frame_id)
        unwind_info.add_saved_register("rip", saved_rip)
        return unwind_info

gdb.unwinder.register_unwinder(None, MyUnwinder())
```

### LLDB
```python
# LLDB uses frame recognizers instead
# Completely different approach
```

## Memory Access

| Operation | GDB | LLDB |
|-----------|-----|------|
| **Read memory** | `inferior.read_memory(addr, size)` | `process.ReadMemory(addr, size, error)` |
| **Write memory** | `inferior.write_memory(addr, data)` | `process.WriteMemory(addr, data, error)` |
| **Context** | Via `gdb.selected_inferior()` | Via `target.GetProcess()` |

## Type System Differences

### GDB
- Types are cached and reused
- Can create pointer types easily: `type.pointer()`
- Can get type of value: `value.type`

### LLDB
- Types are fetched from target
- Pointer types via `GetPointerType()`
- Type info via `value.GetType()`

## Key Differences Summary

| Aspect | GDB | LLDB |
|--------|-----|------|
| **API Style** | Global functions | Object-oriented with context |
| **Context** | Implicit | Explicit (debugger → target → process → thread → frame) |
| **Naming** | snake_case | PascalCase methods |
| **Command registration** | Class-based | Function + registration |
| **Frame unwinding** | Custom unwinders | Frame recognizers |
| **Error handling** | Specific exception types | Generic errors |
| **Convenience variables** | Full support | Limited |

## Abstraction Challenges

### Easy to Abstract
- Basic value operations (cast, dereference, field access)
- Type lookups
- Integer/string conversion
- Expression evaluation (with frame context in LLDB)

### Medium Difficulty
- Command registration (different patterns)
- Convenience variables (limited in LLDB)
- Memory access (requires different context objects)

### Hard to Abstract
- Frame unwinding (fundamentally different)
- Debugger-specific configuration
- Event handling
- Breakpoint management (different APIs)

## Best Practices

1. **Cache context objects** (LLDB): Fetching debugger/target/frame is expensive
2. **Handle errors consistently**: Both debuggers can throw Python exceptions
3. **Use native types when needed**: `.native` property for escape hatch
4. **Test with both debuggers**: Subtle behavior differences exist
5. **Document LLDB quirks**: More explicit context requirements


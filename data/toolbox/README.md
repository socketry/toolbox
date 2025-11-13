# Ruby Toolbox Extensions

This directory contains Ruby debugging extensions that work with both GDB and LLDB through automatic debugger detection.

## Structure

```
data/toolbox/
├── init.py                  # Single entry point for both debuggers
├── debugger.py              # Auto-detects GDB or LLDB
├── debugger/                # Abstraction layer implementations
│   ├── gdb.py              # GDB backend
│   ├── lldb.py             # LLDB backend
│   └── *.md                # Documentation
│
# Ruby debugging extensions (currently GDB-specific, migrating to abstraction)
├── object.py               # Object inspection (rb-object-print)
├── fiber.py                # Fiber debugging (rb-fiber-scan-heap, rb-fiber-switch)
├── heap.py                 # Heap scanning (rb-heap-scan)
├── stack.py                # Stack inspection
│
# Support modules
├── value.py                # Ruby VALUE interpretation
├── constants.py            # Ruby constant lookups
├── command.py              # Command argument parsing
├── format.py               # Output formatting
│
# Ruby type wrappers
├── rbasic.py               # RBasic
├── rstring.py              # RString
├── rarray.py               # RArray
├── rhash.py                # RHash
├── rstruct.py              # RStruct
├── rsymbol.py              # RSymbol
├── rfloat.py               # RFloat
├── rbignum.py              # RBignum
├── rclass.py               # RClass
└── rexception.py           # RException
```

## How It Works

### 1. Single Entry Point

Both GDB and LLDB load the same `init.py` file:

**GDB** (~/.gdbinit):
```gdb
source /path/to/data/toolbox/init.py
```

**LLDB** (~/.lldbinit):
```lldb
command script import /path/to/data/toolbox/init.py
```

### 2. Auto-Detection

`init.py` imports `debugger.py`, which automatically detects which debugger is running:

```python
import debugger  # Auto-detects!

if debugger.DEBUGGER_NAME == 'gdb':
    print("Running in GDB")
elif debugger.DEBUGGER_NAME == 'lldb':
    print("Running in LLDB")
```

### 3. Unified Abstraction

The `debugger` module provides a common API:

```python
import debugger

# These work in both GDB and LLDB:
value = debugger.parse_and_eval("$var")
type = debugger.lookup_type("struct RBasic")
value_cast = value.cast(type.pointer())
```

### 4. Extension Loading

`init.py` loads all Ruby debugging extensions, which register commands with the debugger.

## Installation

### GDB
```bash
gem install toolbox
bake toolbox:gdb:install
```

This adds to `~/.gdbinit`:
```gdb
# Ruby Toolbox GDB Extensions
source /path/to/gem/data/toolbox/init.py
```

### LLDB
```bash
gem install toolbox
bake toolbox:lldb:install
```

This adds to `~/.lldbinit`:
```lldb
# Ruby Toolbox LLDB Extensions
command script import /path/to/gem/data/toolbox/init.py
```

## Available Commands

### Object Inspection
- `rb-object-print <expression> [--depth N]` - Print Ruby objects with recursion

### Fiber Debugging
- `rb-fiber-scan-heap [--limit N]` - Scan heap for fiber objects
- `rb-fiber-scan-switch <index>` - Switch to a fiber from scan cache
- `rb-fiber-switch <fiber_value>` - Switch to a specific fiber
- `rb-fiber-scan-stack-trace-all` - Print stack traces for all cached fibers

### Heap Scanning
- `rb-heap-scan [--type TYPE] [--limit N]` - Scan Ruby heap for objects

### Stack Inspection
- `rb-stack-print` - Print Ruby stack (coming soon)

## Migration Status

### ✅ Fully Abstracted
- Command argument parsing
- Output formatting
- Constant lookups

### 🚧 Partially Abstracted
- Object inspection (uses `gdb` directly, needs migration to `debugger`)
- Fiber debugging (uses `gdb` directly, needs migration to `debugger`)
- Heap scanning (uses `gdb` directly, needs migration to `debugger`)

### 📋 Migration Plan
1. Update extension modules to import `debugger` instead of `gdb`
2. Replace `gdb.parse_and_eval()` with `debugger.parse_and_eval()`
3. Replace `gdb.lookup_type()` with `debugger.lookup_type()`
4. Test with both GDB and LLDB
5. Add LLDB-specific handling where needed

## Testing

Test with GDB:
```bash
gdb -q ruby
(gdb) help rb-object-print
(gdb) help rb-fiber-scan-heap
```

Test with LLDB (once migrated):
```bash
lldb ruby
(lldb) help rb-object-print
(lldb) help rb-fiber-scan-heap
```

## Documentation

- [debugger/README.md](debugger/README.md) - Abstraction layer documentation
- [debugger/ARCHITECTURE.md](debugger/ARCHITECTURE.md) - Architecture details
- [debugger/API_COMPARISON.md](debugger/API_COMPARISON.md) - GDB vs LLDB API reference
- [debugger/MIGRATION.md](debugger/MIGRATION.md) - Migration guide for code

## Python Module Notes

### Why `init.py` not `__init__.py`?

- `__init__.py` makes a directory a Python *package*
- `init.py` is a regular Python file loaded explicitly by debuggers
- GDB uses `source init.py`, LLDB uses `command script import init.py`
- Neither requires package structure, so we use a simple `init.py`

### Import Path Setup

`init.py` adds its directory to `sys.path` so extensions can import each other:

```python
import os, sys
toolbox_dir = os.path.dirname(os.path.abspath(__file__))
if toolbox_dir not in sys.path:
    sys.path.insert(0, toolbox_dir)
```

This allows:
```python
import debugger      # data/toolbox/debugger.py
import object        # data/toolbox/object.py
import fiber         # data/toolbox/fiber.py
from debugger import gdb   # data/toolbox/debugger/gdb.py
```

## Contributing

When adding new extensions:

1. Use the `debugger` abstraction for portability
2. Test with both GDB and LLDB
3. Add documentation and examples
4. Update this README

## See Also

- [GDB Python API](https://sourceware.org/gdb/current/onlinedocs/gdb/Python-API.html)
- [LLDB Python API](https://lldb.llvm.org/use/python-reference.html)
- [Ruby VM Internals](https://docs.ruby-lang.org/en/master/extension_rdoc.html)


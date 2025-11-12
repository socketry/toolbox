# Object Inspection

This guide explains how to use `rb-object-print` to inspect Ruby objects, hashes, arrays, and structs in GDB.

## Why Object Inspection Matters

When debugging Ruby programs or analyzing core dumps, you often need to inspect complex data structures that are difficult to read in their raw memory representation. Standard GDB commands show pointer addresses and raw memory, but not the logical structure of Ruby objects.

Use `rb-object-print` when you need:

- **Understand exception objects**: See the full exception hierarchy, message, and backtrace data
- **Inspect fiber storage**: View thread-local data and fiber-specific variables
- **Debug data corruption**: Check the contents of hashes and arrays for unexpected values
- **Analyze VM state**: Examine objects on the VM stack without manual pointer arithmetic

## Basic Usage

The `rb-object-print` command recursively prints Ruby objects in a human-readable format.

### Syntax

~~~
rb-object-print <expression> [--depth N] [--debug]
~~~

Where:
- `<expression>`: Any GDB expression that evaluates to a Ruby VALUE
- `--depth N`: Maximum recursion depth (default: 1)
- `--debug`: Enable diagnostic output for troubleshooting

### Simple Values

Print immediate values and special constants:

~~~
(gdb) rb-object-print 0        # Qfalse
(gdb) rb-object-print 8        # Qnil  
(gdb) rb-object-print 20       # Qtrue
(gdb) rb-object-print 85       # Fixnum: 42
~~~

These work without any Ruby process running, making them useful for learning and testing.

### Expressions

Use any valid GDB expression:

~~~
(gdb) rb-object-print $ec->errinfo                    # Exception object
(gdb) rb-object-print $ec->cfp->sp[-1]                # Top of VM stack
(gdb) rb-object-print $ec->storage                    # Fiber storage hash
(gdb) rb-object-print (VALUE)0x00007f8a12345678      # Object at specific address
~~~

## Inspecting Hashes

Ruby hashes have two internal representations (ST table and AR table). The command automatically detects and displays both:

### Small Hashes (AR Table)

For hashes with fewer than 8 entries, Ruby uses an array-based implementation:

~~~
(gdb) rb-object-print $some_hash
AR Table at 0x7f8a1c123456 (size=4, bound=3):
  [   0] K: :name
         V: "Alice"
  [   1] K: :age  
         V: Fixnum: 30
  [   2] K: :active
         V: Qtrue
~~~

### Large Hashes (ST Table)

For larger hashes, Ruby uses a hash table:

~~~
(gdb) rb-object-print $large_hash
ST Table at 0x7f8a1c789abc (15 entries):
  [   0] K: :user_id
         V: Fixnum: 12345
  [   1] K: :session_data
         V: <RString>
  ...
~~~

### Controlling Depth

Prevent overwhelming output from deeply nested structures:

~~~
(gdb) rb-object-print $nested_hash --depth 1   # Only top level
(gdb) rb-object-print $nested_hash --depth 2   # One level of nesting
(gdb) rb-object-print $nested_hash --depth 5   # Deep inspection
~~~

At depth 1, nested hashes/arrays show as `<RHash>` or `<RArray>`. Increase depth to expand them.

## Inspecting Arrays

Arrays also have two representations based on size:

### Embedded Arrays

Small arrays (up to 3 elements on 64-bit) are stored inline:

~~~
(gdb) rb-object-print $small_array
Embedded Array at 0x7f8a1c234567 (length 3)
  [   0] I: Fixnum: 1
  [   1] I: Fixnum: 2
  [   2] I: Fixnum: 3
~~~

### Heap Arrays

Larger arrays allocate separate memory:

~~~
(gdb) rb-object-print $big_array --depth 2
Heap Array at 0x7f8a1c345678 (length 100)
  [   0] I: Fixnum: 1
  [   1] I: "first item"
  ...
~~~

## Inspecting Structs

Ruby Struct objects work similarly to arrays:

~~~
(gdb) rb-object-print $struct_instance
Heap Struct at 0x7f8a1c456789 (length 4)
  [   0] I: "John"
  [   1] I: Fixnum: 25
  [   2] I: "Engineer"
  [   3] I: Qtrue
~~~

## Practical Examples

### Debugging Exception in Fiber

When a fiber has an exception, inspect it:

~~~
(gdb) rb-scan-fibers
(gdb) rb-fiber 5              # Shows fiber with exception
(gdb) set $ec = ...           # (shown in output)
(gdb) rb-object-print $ec->errinfo --depth 3
~~~

This reveals the full exception structure including any nested causes.

### Inspecting Method Arguments

Break at a method and examine arguments on the stack:

~~~
(gdb) break some_method
(gdb) run
(gdb) rb-object-print $ec->cfp->sp[-1]  # Last argument
(gdb) rb-object-print $ec->cfp->sp[-2]  # Second-to-last argument
~~~

### Examining Fiber Storage

Thread-local variables are stored in fiber storage:

~~~
(gdb) rb-scan-fibers
(gdb) rb-fiber 0
(gdb) rb-object-print $ec->storage --depth 2
~~~

This shows all thread-local variables and their values.

## Debugging with --debug Flag

When `rb-object-print` doesn't show what you expect, use `--debug`:

~~~
(gdb) rb-object-print $suspicious_value --debug
DEBUG: Evaluated '$suspicious_value' to 0x7f8a1c567890
DEBUG: Loaded constant RUBY_T_MASK = 31
DEBUG: Object at 0x7f8a1c567890 with flags=0x20040005, type=0x5
...
~~~

This shows:
- How the expression was evaluated
- What constants were loaded
- Object type detection logic
- Any errors encountered

Use this to troubleshoot:
- Unexpected output format
- Missing nested structures
- Type detection issues
- Access errors

## Best Practices

### Choose Appropriate Depth

- **Depth 1**: Quick overview, minimal output (default)
- **Depth 2-3**: Common for most debugging tasks
- **Depth 5+**: Only for deep investigation, can be verbose

### Work with Core Dumps

The command works perfectly with core dumps since it only reads memory:

~~~
$ gdb ruby core.12345
(gdb) source ~/.local/share/gdb/ruby/init.gdb
(gdb) rb-object-print $ec->errinfo
~~~

No running process needed!

### Combine with Standard GDB

Use standard GDB commands alongside Ruby extensions:

~~~
(gdb) info locals              # See C variables
(gdb) rb-object-print $val     # Interpret as Ruby object
(gdb) x/10gx $ec->cfp->sp      # Raw memory view
~~~

## Common Pitfalls

### Accessing Deallocated Objects

If an object address is invalid, you'll see an error:

~~~
(gdb) rb-object-print (VALUE)0xdeadbeef
[Error printing object: Cannot access memory at address 0xdeadbeef]
~~~

Always verify the address is valid before inspecting.

### Depth Too Low

If you see `<RHash>` or `<RArray>` where you expected expanded content:

~~~
(gdb) rb-object-print $hash       # Shows: <RHash>
(gdb) rb-object-print $hash --depth 2   # Shows actual content
~~~

Increase `--depth` to see nested structures.

### Missing Debug Symbols

Without debug symbols, some type information may be unavailable:

~~~
Python Exception <class 'gdb.error'>: No type named RBasic
~~~

Solution: Install Ruby with debug symbols or use a debug build.

## See Also

- {ruby Ruby::GDB::fiber-debugging Fiber debugging} for inspecting fiber-specific data
- {ruby Ruby::GDB::stack-inspection Stack inspection} for examining call frames
- {ruby Ruby::GDB::heap-debugging Heap debugging} for scanning objects


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
(gdb) rb-object-print 0        # <T_FALSE>
(gdb) rb-object-print 8        # <T_NIL>
(gdb) rb-object-print 20       # <T_TRUE>
(gdb) rb-object-print 85       # <T_FIXNUM> 42
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
<T_HASH@0x7f8a1c123456>
[   0] K: <T_SYMBOL> :name
       V: <T_STRING@0x7f8a1c111111> 'Alice'
[   1] K: <T_SYMBOL> :age
       V: <T_FIXNUM> 30
[   2] K: <T_SYMBOL> :active
       V: <T_TRUE>
~~~

### Large Hashes (ST Table)

For larger hashes, Ruby uses a hash table (output format is similar):

~~~
(gdb) rb-object-print $large_hash
<T_HASH@0x7f8a1c789abc>
[   0] K: <T_SYMBOL> :user_id
       V: <T_FIXNUM> 12345
[   1] K: <T_SYMBOL> :session_data
       V: <T_STRING@0x7f8a1c222222> '...'
  ...
~~~

### Controlling Depth

Prevent overwhelming output from deeply nested structures:

~~~
(gdb) rb-object-print $nested_hash --depth 1   # Only top level
<T_HASH@0x7f8a1c123456>
[   0] K: <T_SYMBOL> :data
       V: <T_HASH@0x7f8a1c234567>  # Nested hash not expanded

(gdb) rb-object-print $nested_hash --depth 2   # Expand one level
<T_HASH@0x7f8a1c123456>
[   0] K: <T_SYMBOL> :data
       V: <T_HASH@0x7f8a1c234567>
       [   0] K: <T_SYMBOL> :nested_key
              V: <T_STRING@0x7f8a1c345678> 'value'
~~~

At depth 1, nested structures show their type and address but aren't expanded. Increase depth to expand them.

## Inspecting Arrays

Arrays also have two representations based on size:

### Arrays

Arrays display their elements with type information:

~~~
(gdb) rb-object-print $array
<T_ARRAY@0x7f8a1c234567>
[   0] <T_FIXNUM> 1
[   1] <T_FIXNUM> 2
[   2] <T_FIXNUM> 3
~~~

For arrays with nested objects:

~~~
(gdb) rb-object-print $array --depth 2
<T_ARRAY@0x7f8a1c345678>
[   0] <T_STRING@0x7f8a1c111111> 'first item'
[   1] <T_HASH@0x7f8a1c222222>
[   0] K: <T_SYMBOL> :key
       V: <T_FIXNUM> 123
  ...
~~~

## Inspecting Structs

Ruby Struct objects work similarly to arrays:

~~~
(gdb) rb-object-print $struct_instance
<T_STRUCT@0x7f8a1c456789>
[   0] <T_STRING@0x7f8a1c111111> 'John'
[   1] <T_FIXNUM> 25
[   2] <T_STRING@0x7f8a1c222222> 'Engineer'
[   3] <T_TRUE>
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

If you see `<T_HASH@...>` or `<T_ARRAY@...>` without expanded content at depth 1:

~~~
(gdb) rb-object-print $hash       # Shows: <T_HASH@0x...>
(gdb) rb-object-print $hash --depth 2   # Shows actual content with keys/values
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


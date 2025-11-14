# Getting Started

This guide explains how to install and use Toolbox for debugging Ruby programs and core dumps with GDB or LLDB.

## Installation

Install the gem:

~~~ bash
$ gem install toolbox
~~~

### Installing GDB Extensions

Install the GDB extensions (automatically adds to `~/.gdbinit`):

~~~ bash
$ bake -g toolbox toolbox:gdb:install
~~~

This adds a single line to your `~/.gdbinit` that sources the extensions from the gem's data directory. The extensions will then load automatically every time you start GDB.

To install to a custom `.gdbinit` location:

~~~ bash
$ bake -g toolbox toolbox:gdb:install gdbinit=/path/to/custom/gdbinit
~~~

### Installing LLDB Extensions

Install the LLDB extensions (automatically adds to `~/.lldbinit`):

~~~ bash
$ bake -g toolbox toolbox:lldb:install
~~~

This adds a command script import line to your `~/.lldbinit` that loads the extensions from the gem's data directory. The extensions will then load automatically every time you start LLDB.

To install to a custom `.lldbinit` location:

~~~ bash
$ bake -g toolbox toolbox:lldb:install lldbinit=/path/to/custom/lldbinit
~~~

### Verifying Installation

Check GDB installation status:

~~~ bash
$ bake -g toolbox toolbox:gdb:info
Ruby Toolbox GDB Extensions v0.1.0
Status: ✓ Installed
~~~

Check LLDB installation status:

~~~ bash
$ bake -g toolbox toolbox:lldb:info
Ruby Toolbox LLDB Extensions v0.1.0
Status: ✓ Installed
~~~

Test that extensions load automatically:

~~~ bash
$ gdb --batch -ex "help rb-print"
Recursively print Ruby hash and array structures...
~~~

### Uninstalling

To remove the GDB extensions:

~~~ bash
$ bake -g toolbox toolbox:gdb:uninstall
~~~

To remove the LLDB extensions:

~~~ bash
$ bake -g toolbox toolbox:lldb:uninstall
~~~

This removes the source line from your `~/.gdbinit` or `~/.lldbinit`.

## Core Concepts

Ruby GDB provides specialized commands for debugging Ruby at multiple levels:

- **Context Setup** (`rb-context`) - Get current execution context and set up convenience variables
- **Object Inspection** (`rb-print`) - View Ruby objects, hashes, arrays, and structs with proper formatting
- **Fiber Debugging** (`rb-fiber-*`) - Scan heap for fibers, inspect state, and switch contexts
- **Stack Analysis** (`rb-stack-trace`) - Examine combined VM (Ruby) and C (native) stack frames
- **Heap Navigation** (`rb-heap-scan`) - Scan the Ruby heap to find objects by type

## Quick Start

### Debugging a Running Process

Start your Ruby program under GDB:

~~~ bash
$ gdb --args ruby my_script.rb
~~~

Set a breakpoint and run:

~~~
(gdb) break rb_vm_exec
(gdb) run
~~~

Once stopped, use Ruby debugging commands:

~~~
(gdb) rb-stack-trace                     # Show combined Ruby/C backtrace
(gdb) rb-fiber-scan-heap                 # Scan heap for fibers
(gdb) rb-heap-scan --type RUBY_T_STRING --limit 5  # Find strings
~~~

### Debugging a Core Dump

When your Ruby program crashes, you can analyze the core dump:

~~~ bash
$ gdb ruby core.dump
~~~

Diagnose the issue (extensions load automatically if installed):

~~~
(gdb) rb-fiber-scan-heap                 # Scan heap for all fibers
(gdb) rb-fiber-scan-stack-trace-all      # Show backtraces for all fibers
(gdb) rb-fiber-scan-switch 0             # Switch to main fiber
(gdb) rb-print $errinfo --depth 2 # Print exception (now $errinfo is set)
(gdb) rb-heap-scan --type RUBY_T_HASH --limit 10  # Find hashes
~~~

## Common Workflows

### Inspecting Exception Objects

When a Ruby exception occurs, you can inspect it in detail:

~~~
(gdb) break rb_exc_raise
(gdb) run
(gdb) rb-context
(gdb) rb-print $errinfo --depth 2
~~~

This shows the exception class, message, and any nested structures. The `rb-context` command displays the current execution context and sets up `$ec`, `$cfp`, and `$errinfo` convenience variables.

### Debugging Fiber Issues

When working with fibers, you often need to see what each fiber is doing:

~~~
(gdb) rb-fiber-scan-heap                # Scan heap for all fibers
(gdb) rb-fiber-scan-stack-trace-all     # Show backtraces for all fibers  
(gdb) rb-fiber-scan-switch 5            # Switch GDB to fiber #5's context
(gdb) rb-stack-trace                    # Now shows fiber's combined backtrace
~~~

### Examining Complex Data Structures

Ruby hashes and arrays can contain nested structures:

~~~
(gdb) rb-print $some_hash --depth 2
<T_HASH@...>
[   0] K: <T_SYMBOL> :name
       V: <T_STRING@...> "Alice"
[   1] K: <T_SYMBOL> :age
       V: <T_FIXNUM> 30
~~~

The `--depth` flag controls how deep to recurse into nested objects.

## Requirements

- GDB with Python support (GDB 7.0+) or LLDB with Python support.
- Ruby 3.3+ recommended.

### Platform Support

- **Linux**: Full support with all features (GDB or LLDB).
- **macOS**: 
  - Ruby head: Full support.
  - Ruby 3.4.x: Limited support (see below).
- **BSD**: Should work similar to Linux (untested).

### macOS + Ruby 3.4.x Limitation

On macOS with LLDB and Ruby <= 3.4.x, some commands including `rb-fiber-scan-heap` will not work due to a `dsymutil` bug that drops `struct RTypedData` from debug symbols. This appears fixed in `ruby-head`.

**Workarounds:**
- Use Ruby head: `ruby-install ruby-head -- CFLAGS="-g -O0"`
- Use GDB instead of LLDB (works with Ruby 3.4.x)
- Other commands like `rb-print`, `rb-stack-trace`, `rb-context` work fine

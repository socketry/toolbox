# Getting Started

This guide explains how to install and use Ruby GDB extensions for debugging Ruby programs and core dumps.

## Installation

Install the gem:

~~~ bash
$ gem install ruby-gdb
~~~

### Installing GDB Extensions

Install the extensions (automatically adds to `~/.gdbinit`):

~~~ bash
$ bake ruby:gdb:install
~~~

This adds a single line to your `~/.gdbinit` that sources the extensions from the gem's data directory. The extensions will then load automatically every time you start GDB.

To install to a custom `.gdbinit` location:

~~~ bash
$ bake ruby:gdb:install gdbinit=/path/to/custom/gdbinit
~~~

### Verifying Installation

Check installation status:

~~~ bash
$ bake ruby:gdb:info
Ruby GDB Extensions v0.1.0
Status: ✓ Installed
~~~

Test that extensions load automatically:

~~~ bash
$ gdb --batch -ex "help rb-object-print"
Recursively print Ruby hash and array structures...
~~~

### Uninstalling

To remove the extensions:

~~~ bash
$ bake ruby:gdb:uninstall
~~~

This removes the source line from your `~/.gdbinit`.

## Core Concepts

Ruby GDB provides specialized commands for debugging Ruby at multiple levels:

- **Object Inspection** - View Ruby objects, hashes, arrays, and structs with {ruby Ruby::GDB::object-inspection proper formatting}
- **Fiber Debugging** - Navigate and inspect fiber state, backtraces, and exceptions
- **Stack Analysis** - Examine both VM (Ruby) and C (native) stack frames
- **Heap Navigation** - Scan the Ruby heap to find objects and understand memory usage

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
(gdb) rb-object-print $ec->cfp->sp[-1]   # Print top of VM stack
(gdb) rb-scan-fibers                     # List all fibers
(gdb) rb-fiber-bt 0                      # Show fiber backtrace
~~~

### Debugging a Core Dump

When your Ruby program crashes, you can analyze the core dump:

~~~ bash
$ gdb ruby core.dump
~~~

Load the Ruby extensions and diagnose the issue:

~~~
(gdb) source ~/.local/share/gdb/ruby/init.gdb
(gdb) rb-diagnose-exit          # Check for exceptions and signals
(gdb) rb-scan-fibers           # List all fibers
(gdb) rb-fiber-bt 0            # Show fiber backtraces
(gdb) rb-object-print $errinfo # Print exception objects
~~~

## Common Workflows

### Inspecting Exception Objects

When a Ruby exception occurs, you can inspect it in detail:

~~~
(gdb) break rb_exc_raise
(gdb) run
(gdb) rb-object-print $ec->errinfo --depth 2
~~~

This shows the exception class, message, and any nested structures.

### Debugging Fiber Issues

When working with fibers, you often need to see what each fiber is doing:

~~~
(gdb) rb-scan-fibers           # Scan heap for all fibers
(gdb) rb-all-fiber-bt          # Show backtraces for all fibers
(gdb) rb-fiber 5               # Inspect specific fiber
(gdb) rb-fiber-switch 5        # Switch GDB to fiber's stack
(gdb) bt                       # Now shows fiber's C backtrace
~~~

### Examining Complex Data Structures

Ruby hashes and arrays can contain nested structures:

~~~
(gdb) rb-object-print $some_hash --depth 3
(gdb) rb-object-print $ec->storage --depth 2
~~~

The `--depth` flag controls how deep to recurse into nested objects.

## Next Steps

- Learn about {ruby Ruby::GDB::object-inspection inspecting Ruby objects} in detail
- Explore {ruby Ruby::GDB::fiber-debugging fiber debugging} capabilities
- Understand {ruby Ruby::GDB::stack-inspection stack analysis} techniques
- Master {ruby Ruby::GDB::heap-debugging heap navigation} for memory issues

## Requirements

- GDB with Python support (GDB 7.0+)
- Ruby 3.0+ recommended (works with 2.x with limitations)
- For best results: Ruby built with debug symbols (`--with-debug-symbols` or install `ruby-debug` package)

## Platform Support

These extensions work on:

- **Linux**: Full support with all features
- **macOS**: Viewing core dumps works; running processes may require code signing or disabling SIP
- **BSD**: Should work similar to Linux (untested)

For production debugging, Linux with Ruby debug symbols provides the best experience.


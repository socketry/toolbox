# Fiber Debugging

This guide explains how to debug Ruby fibers using GDB, including inspecting fiber state, backtraces, and switching between fiber contexts.

## Why Fiber Debugging is Critical

When debugging concurrent Ruby applications, fibers can be in various states - running, suspended, or terminated. Unlike traditional debugging where you see one call stack, fiber-based programs have multiple execution contexts simultaneously. Understanding what each fiber is doing and why it stopped is essential for diagnosing deadlocks, exceptions, and state corruption.

Use fiber debugging when you need:

- **Diagnose deadlocks**: See which fibers are waiting and on what
- **Find hidden exceptions**: Discover exceptions in suspended fibers that haven't propagated yet
- **Understand concurrency**: Visualize what all fibers are doing at a point in time
- **Debug async code**: Navigate between fiber contexts to trace execution flow

## Scanning for Fibers

The first step in fiber debugging is finding all fibers in the heap.

### Basic Scan

Scan the entire Ruby heap for fiber objects:

~~~
(gdb) rb-fiber-scan-heap
Scanning heap for Fiber objects...
  Checked 45000 objects, found 12 fiber(s)...

Found 12 fiber(s):

Fiber #0: <T_DATA@...> → <struct rb_fiber_struct@...>
  Status: SUSPENDED
  Stack: <void *@...>
  VM Stack: <VALUE *@...>
  CFP: <rb_control_frame_t@...>
  
Fiber #1: <T_DATA@...> → <struct rb_fiber_struct@...>
  Status: SUSPENDED
  ...
~~~

### Limiting Results

For large applications, limit the scan:

~~~
(gdb) rb-fiber-scan-heap --limit 10    # Find first 10 fibers only
~~~

### Caching Results

Cache fiber addresses for faster subsequent access:

~~~
(gdb) rb-fiber-scan-heap --cache            # Save to fibers.json
(gdb) rb-fiber-scan-heap --cache my.json    # Custom cache file
~~~

Later, load from cache instantly:

~~~
(gdb) rb-fiber-scan-heap --cache
Loaded 12 fiber(s) from fibers.json
~~~

This is especially useful with core dumps where heap scanning is slow.

## Inspecting Specific Fibers

After scanning, you can switch to a specific fiber's context or view all backtraces.

### View All Fiber Backtraces

See Ruby-level call stacks for all fibers at once:

~~~
(gdb) rb-fiber-scan-stack-trace-all
Found 12 fiber(s)

Fiber #0: <T_DATA@...> → <struct rb_fiber_struct@...>
  Status: RESUMED
  [No backtrace - fiber is running]

Fiber #1: <T_DATA@...> → <struct rb_fiber_struct@...>
  Status: SUSPENDED
  /app/lib/connection.rb:123:in `read'
  /app/lib/connection.rb:89:in `receive'
  /app/lib/server.rb:56:in `handle_client'
  ...

Fiber #5: <T_DATA@...> → <struct rb_fiber_struct@...>
  Status: SUSPENDED  
  Exception: IOError: Connection reset
  /app/lib/connection.rb:45:in `write'
  ...
~~~

This gives you a complete overview of what every fiber is doing.

## Switching Fiber Context

The most powerful feature: switch GDB's view to a fiber's stack (even in core dumps!).

### Basic Usage

~~~
(gdb) rb-fiber-scan-heap
(gdb) rb-fiber-scan-switch 5
Switching to Fiber #5: VALUE 0x...
Switched to Fiber: <T_DATA@...> → <struct rb_fiber_struct@...>
  Status: SUSPENDED

Convenience variables set:
  $fiber     = Current fiber VALUE
  $fiber_ptr = Current fiber pointer (struct rb_fiber_struct *)
  $ec        = Execution context (rb_execution_context_t *)
  $errinfo   = Exception being handled (VALUE)

Now try:
  bt          # Show C backtrace of fiber
  rb-stack-trace  # Show combined Ruby/C backtrace
  info locals     # Show local variables
~~~

After switching, all standard GDB commands work with the fiber's context:

~~~
(gdb) rb-stack-trace            # Combined Ruby/C backtrace
(gdb) bt                        # C backtrace of fiber
#0  0x00007f8a1c567890 in fiber_setcontext
#1  0x00007f8a1c567900 in rb_fiber_yield
#2  0x00007f8a1c234567 in rb_io_wait_readable
...

(gdb) frame 2
(gdb) info locals              # Local C variables in that frame
~~~

### Switching by VALUE

You can also switch to a specific fiber by its VALUE or address:

~~~
(gdb) rb-fiber-switch 0x7f8a1c800500
~~~

### Switching Back

Return to normal stack view:

~~~
(gdb) rb-fiber-scan-switch off
~~~

## Analyzing Fiber State

After switching to a fiber with `rb-fiber-scan-switch`, you can use standard GDB commands to inspect the fiber's state:

~~~
(gdb) rb-fiber-scan-switch 5
(gdb) bt                    # Show C backtrace
(gdb) frame <n>             # Switch to specific frame
(gdb) info locals           # Show local variables
(gdb) rb-print $errinfo  # Print exception if present
~~~

The fiber switch command sets up several convenience variables:
- `$fiber` - The fiber VALUE
- `$fiber_ptr` - Pointer to `struct rb_fiber_struct`
- `$ec` - The fiber's execution context
- `$errinfo` - Exception being handled (if any)

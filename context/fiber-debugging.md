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
(gdb) rb-scan-fibers
Scanning 1250 heap pages...
  Checked 45000 objects, found 12 fiber(s)...
Scan complete: checked 67890 objects

Found 12 fiber(s):

Fiber #0: 0x7f8a1c800000
  Status: RESUMED
  Stack: base=0x7f8a1d000000, size=1048576
  VM Stack: 0x7f8a1c900000, size=4096
  CFP: 0x7f8a1c901000

Fiber #1: 0x7f8a1c800100
  Status: SUSPENDED
  Exception: RuntimeError: Connection failed
  ...
~~~

### Limiting Results

For large applications, limit the scan:

~~~
(gdb) rb-scan-fibers 10    # Find first 10 fibers only
~~~

### Caching Results

Cache fiber addresses for faster subsequent access:

~~~
(gdb) rb-scan-fibers --cache            # Save to fibers.json
(gdb) rb-scan-fibers --cache my.json    # Custom cache file
~~~

Later, load from cache instantly:

~~~
(gdb) rb-scan-fibers --cache
Loaded 12 fiber address(es) from fibers.json
~~~

This is especially useful with core dumps where heap scanning is slow.

## Inspecting Specific Fibers

After scanning, inspect fibers by index:

### Fiber Overview

~~~
(gdb) rb-fiber 5
Fiber #5: 0x7f8a1c800500
  Status: SUSPENDED
  Exception: IOError: Connection reset
  Stack: base=0x7f8a1e000000, size=1048576
  VM Stack: 0x7f8a1c950000, size=4096
  CFP: 0x7f8a1c951000
  EC: 0x7f8a1c800600

Available commands:
  rb-fiber-bt 5         - Show backtrace
  rb-fiber-vm-stack 5   - Show VM stack
  rb-fiber-c-stack 5    - Show C/machine stack info
~~~

This shows at a glance whether the fiber has an exception and what its state is.

### Fiber Backtraces

See the Ruby-level call stack:

~~~
(gdb) rb-fiber-bt 5
Backtrace for fiber 0x7f8a1c800500:
  45: /app/lib/connection.rb:123:in `read'
  44: /app/lib/connection.rb:89:in `receive'
  43: /app/lib/server.rb:56:in `handle_client'
  42: /app/lib/server.rb:34:in `block in run'
  41: /gems/async-2.0/lib/async/task.rb:45:in `run'
  ...
~~~

Show backtraces for all non-terminated fibers:

~~~
(gdb) rb-all-fiber-bt
~~~

## Switching Fiber Context

The most powerful feature: switch GDB's view to a fiber's stack (even in core dumps!).

### Basic Usage

~~~
(gdb) rb-scan-fibers
(gdb) rb-fiber-switch 5
Switched to Fiber #5: 0x7f8a1c800500
  Status: SUSPENDED
  Exception: IOError: Connection reset

Convenience variables set:
  $fiber   = Current fiber (struct rb_fiber_struct *)
  $ec      = Execution context (rb_execution_context_t *)
  $errinfo = Exception being handled (VALUE)

Now try:
  bt          # Show C backtrace of fiber
  frame <n>   # Switch to frame N
  info locals # Show local variables
  rp $errinfo # Pretty print exception
~~~

After switching, all standard GDB commands work with the fiber's context:

~~~
(gdb) bt                        # C backtrace of fiber
#0  0x00007f8a1c567890 in fiber_setcontext
#1  0x00007f8a1c567900 in rb_fiber_yield
#2  0x00007f8a1c234567 in rb_io_wait_readable
...

(gdb) frame 2
(gdb) info locals              # Local C variables in that frame
(gdb) rb-object-print $ec->cfp->sp[-1]  # Ruby values on VM stack
~~~

### Switching Back

Return to normal stack view:

~~~
(gdb) rb-fiber-switch off
Fiber unwinder deactivated. Switched back to normal stack view.
~~~

## Analyzing Fiber State

### VM Stack Inspection

View the Ruby VM stack for a fiber:

~~~
(gdb) rb-fiber-vm-stack 5
VM Stack for Fiber #5:
  Base: 0x7f8a1c950000
  Size: 4096 VALUEs (32768 bytes)
  CFP:  0x7f8a1c951000
~~~

### VM Control Frames

Walk through each Ruby method frame:

~~~
(gdb) rb-fiber-vm-frames 5
VM Control Frames for Fiber #5:
  ...

Frame #0 (depth 45):
  CFP Address: 0x7f8a1c951000
  PC:         0x7f8a1c234500
  SP:         0x7f8a1c950100
  Location:   /app/lib/connection.rb:123
  Method:     read
  Frame Type: VM_FRAME_MAGIC_METHOD
  Stack Depth: 256 slots
~~~

### Stack Top Values

See what's on top of the VM stack:

~~~
(gdb) rb-fiber-stack-top 5 20
VM Stack Top for Fiber #5:

Top 20 VALUE(s) on stack (newest first):

  [ -1] 0x00007f8a1c888888  T_STRING      "Hello"
  [ -2] 0x0000000000000015  Fixnum(10)    Fixnum: 10
  [ -3] 0x00007f8a1c999999  T_HASH        <hash:0x7f8a1c999999>
  ...
~~~

## Diagnosing Crashes

When Ruby crashes, find out why:

~~~
(gdb) rb-diagnose-exit
================================================================================
DIAGNOSING RUBY EXIT/CRASH
================================================================================

[1] Main Thread Exception:
--------------------------------------------------------------------------------
  Main thread has exception: NoMethodError
  VALUE: 0x7f8a1c777777
  Use: rb-object-print (VALUE)0x7f8a1c777777

[2] Fibers with Exceptions:
--------------------------------------------------------------------------------
  Fiber #5 (SUSPENDED): RuntimeError
    Fiber: 0x7f8a1c800500, errinfo: 0x7f8a1c666666
  Fiber #8 (SUSPENDED): IOError
    Fiber: 0x7f8a1c800800, errinfo: 0x7f8a1c555555

[3] Interrupt Flags:
--------------------------------------------------------------------------------
  interrupt_flag: 0x00000002
  interrupt_mask: 0x00000000
  WARNING: Interrupts pending!
    - TRAP

[4] Signal Information (from core dump):
--------------------------------------------------------------------------------
  Program terminated with signal SIGSEGV, Segmentation fault.
...
~~~

This comprehensive overview helps quickly identify the root cause.

## Advanced Techniques

### Finding Fibers by Stack Address

If you know a stack address, find the owning fiber:

~~~
(gdb) info frame
... rsp = 0x7f8a1e000500 ...

(gdb) rb-fiber-from-stack 0x7f8a1e000000
Searching for fiber with stack base 0x7f8a1e000000...

Found fiber: 0x7f8a1c800300
  Status: SUSPENDED
  Stack: base=0x7f8a1e000000, size=1048576
~~~

### Searching Fibers by Function

Find which fibers are blocked in a specific C function:

~~~
(gdb) rb-fiber-c-stack-search pthread_cond_wait
Scanning 12 fiber(s)...

  Match: Fiber #3 - found at 0x7f8a1e000450
  Match: Fiber #7 - found at 0x7f8a1e100780

Search complete: 2 fiber(s) matched.
~~~

Use this to find all fibers waiting on locks or I/O.

### Debug Unwinder Issues

If fiber switching doesn't work as expected:

~~~
(gdb) rb-fiber-debug-unwind 5
Debug unwinding for Fiber #5: 0x7f8a1c800500

Coroutine context:
  fiber->context.stack_pointer = 0x7f8a1e000480

Saved registers on coroutine stack:
  [0x7f8a1e000480+0]  = R15: 0x0000000000000000
  [0x7f8a1e000480+8]  = R14: 0x00007f8a1c567890
  ...
  [0x7f8a1e000480+48] = RIP: 0x00007f8a1ab12345

Validation:
  ✓ RIP looks like a valid code address
    Symbol: fiber_setcontext + 123
  ✓ RSP is within fiber's stack range
~~~

## Best Practices

### Scan Once, Use Indices

After scanning fibers, use indices for all operations:

~~~
(gdb) rb-scan-fibers           # Scan once
(gdb) rb-fiber 5               # Use index thereafter
(gdb) rb-fiber-bt 5
(gdb) rb-fiber-switch 5
~~~

The cache persists throughout your GDB session.

### Check Fiber Status First

Before inspecting, check the fiber's status:

~~~
(gdb) rb-fiber 5
  Status: TERMINATED           # Won't have useful context
  
(gdb) rb-fiber 3
  Status: SUSPENDED            # Good candidate for inspection
~~~

CREATED and TERMINATED fibers may not have valid saved contexts.

### Use Convenience Variables

After switching to a fiber, use the set convenience variables:

~~~
(gdb) rb-fiber-switch 5
(gdb) rb-object-print $errinfo      # Pre-set to fiber's exception
(gdb) rb-object-print $ec->storage  # Fiber-local storage
~~~

## Common Pitfalls

### Fiber Not Suspended

Only SUSPENDED fibers have fully saved context:

~~~
Fiber status: CREATED (0)
  Note: CREATED fibers may not have been suspended yet
~~~

CREATED fibers haven't yielded yet, so they don't have saved register state.

### Core Dump Limitations

Core dumps capture memory but not CPU registers. Switching to the current fiber may show incomplete stacks. For complete debugging, use live process debugging when possible.

### macOS Code Signing

On macOS, GDB may not be able to attach to running Ruby processes due to code signing restrictions. Core dump analysis works without issues.

## See Also

- {ruby Ruby::GDB::object-inspection Object inspection} for examining fiber storage and exception objects
- {ruby Ruby::GDB::stack-inspection Stack inspection} for understanding VM frames
- {ruby Ruby::GDB::heap-debugging Heap debugging} for finding fiber objects


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

Fiber #0: <VALUE:0x7f8a1c800000>
  Status: RESUMED
  Stack: 0x7f8a1d000000
  
Fiber #1: <VALUE:0x7f8a1c800100>
  Status: SUSPENDED
  ...
~~~

### Limiting Results

For large applications, limit the scan:

~~~
(gdb) rb-fiber-scan-heap 10    # Find first 10 fibers only
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

Fiber #0: <VALUE:0x7f8a1c800000>
  Status: RESUMED
  [No backtrace - fiber is running]

Fiber #1: <VALUE:0x7f8a1c800100>
  Status: SUSPENDED
  /app/lib/connection.rb:123:in `read'
  /app/lib/connection.rb:89:in `receive'
  /app/lib/server.rb:56:in `handle_client'
  ...

Fiber #5: <VALUE:0x7f8a1c800500>
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
Switched to Fiber #5
  Status: SUSPENDED
  
Now you can use standard GDB commands with this fiber's context:
  rb-stack-trace      # Show combined backtrace
  bt                  # Show C backtrace  
  info locals         # Show C local variables
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
(gdb) rb-fiber-scan-heap           # Scan once
(gdb) rb-fiber-scan-switch 5       # Switch to fiber #5
(gdb) rb-stack-trace               # View backtrace
~~~

The cache persists throughout your GDB session.

### Check Fiber Status

CREATED and TERMINATED fibers may not have valid saved contexts. The scan output shows status:

~~~
Fiber #5: <VALUE:0x7f8a1c800500>
  Status: TERMINATED           # Won't have useful context
  
Fiber #3: <VALUE:0x7f8a1c800300>
  Status: SUSPENDED            # Good candidate for inspection
~~~

Focus on SUSPENDED and RESUMED fibers for debugging.

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


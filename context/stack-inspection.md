# Stack Inspection

This guide explains how to inspect both Ruby VM stacks and native C stacks when debugging Ruby programs.

## Understanding Ruby's Dual Stack System

Ruby programs operate with two distinct stacks that serve different purposes. Understanding both is crucial for effective debugging, especially when tracking down segfaults, stack overflows, or unexpected behavior in C extensions.

Use stack inspection when you need:

- **Trace execution flow**: Understand the sequence of method calls that led to the current state
- **Debug C extensions**: See both Ruby and native frames when extensions are involved
- **Find stack overflows**: Identify deep recursion in either Ruby or C code
- **Understand fiber switches**: See where fibers yield and resume

## The Two Stack Types

### VM Stack (Ruby Level)

The VM stack holds:
- Ruby method call frames (control frames)
- Local variables and temporaries
- Method arguments
- Block parameters
- Return values

This is what you see with Ruby's `caller` method at runtime.

### C Stack (Native Level)

The C/machine stack holds:
- Native function call frames
- C local variables
- Saved registers
- Return addresses

This is what GDB's `bt` command shows by default.

## Inspecting VM Stacks

### Current Frame Information

See the current Ruby control frame:

~~~
(gdb) set $ec = ruby_current_execution_context_ptr
(gdb) set $cfp = $ec->cfp
(gdb) p $cfp->pc       # Program counter
(gdb) p $cfp->sp       # Stack pointer
(gdb) p $cfp->iseq     # Instruction sequence
(gdb) p $cfp->ep       # Environment pointer
~~~

### Combined Stack Trace

The simplest way to see both Ruby and C frames:

~~~
(gdb) rb-fiber-scan-heap
(gdb) rb-fiber-scan-switch 5
(gdb) rb-stack-trace
Combined Ruby/C backtrace for Fiber #5:
  [C] fiber_setcontext
  [R] /app/lib/connection.rb:123:in `read'
  [C] rb_io_wait_readable
  [R] /app/lib/connection.rb:89:in `receive'
  ...
~~~

This shows both levels of the call stack in order.

### Detailed Frame Information

For advanced debugging, you can inspect the raw VM frames:

~~~
(gdb) set $ec = ruby_current_execution_context_ptr
(gdb) set $cfp = $ec->cfp

# Current frame details:
(gdb) p $cfp->pc       # Program counter
(gdb) p $cfp->sp       # Stack pointer  
(gdb) p $cfp->iseq     # Instruction sequence
(gdb) p $cfp->ep       # Environment pointer
~~~

## Inspecting C Stacks

### C Backtrace with GDB

After switching to a fiber, use standard GDB commands to inspect the C stack:

~~~
(gdb) rb-fiber-scan-switch 5
(gdb) bt                    # Show C backtrace
(gdb) frame 2               # Switch to specific frame
(gdb) info args             # Show function arguments
(gdb) info locals           # Show local variables
~~~

The fiber unwinder automatically integrates with GDB's backtrace functionality, so `bt` shows the correct C stack for the selected fiber.

## Practical Examples

### Finding Where Execution Stopped

Identify the exact location in both Ruby and C:

~~~
(gdb) rb-fiber-scan-heap
(gdb) rb-fiber-scan-switch 5         # Switch to fiber context
(gdb) rb-stack-trace                 # Combined backtrace
  [R] /app/lib/connection.rb:123:in `read'
  [C] rb_fiber_yield
  [C] rb_io_wait_readable
  [R] /app/lib/connection.rb:89:in `receive'
~~~

This shows the fiber is suspended in `read`, waiting for I/O.

### Debugging Deep Recursion

Detect excessive call depth:

~~~
(gdb) rb-fiber-scan-heap
(gdb) rb-fiber-scan-switch 5
(gdb) rb-stack-trace | grep "/app/lib/parser.rb:45" | wc -l
134                            # Same line appearing 134 times!
~~~

Identifies a recursion issue in the parser.

### Examining Stack Values

See what values are on the current frame's stack:

~~~
(gdb) rb-fiber-scan-switch 5
(gdb) set $sp = $ec->cfp->sp

# Print values on stack
(gdb) rb-object-print *(VALUE*)($sp - 1)  # Top of stack
(gdb) rb-object-print *(VALUE*)($sp - 2)  # Second value
(gdb) rb-object-print *(VALUE*)($sp - 3)  # Third value
~~~

### Tracking Fiber Switches

See the call stack across fiber boundaries:

~~~
(gdb) rb-fiber-scan-switch 5
(gdb) bt
#0  fiber_setcontext
#1  rb_fiber_yield            # Fiber yielded here
#2  rb_io_wait_readable       # Waiting for I/O
#3  some_io_operation

(gdb) frame 3
(gdb) info locals              # C variables at I/O call
~~~

## Combining VM and C Stacks

For the complete picture, use the combined stack trace:

~~~
(gdb) rb-fiber-scan-switch 5
(gdb) rb-stack-trace
Combined Ruby/C backtrace:
  [R] /app/lib/connection.rb:123:in `read'
  [C] rb_io_wait_readable
  [C] rb_io_read
  [R] /app/lib/connection.rb:89:in `receive'
  [C] rb_fiber_yield
  [R] /app/lib/server.rb:56:in `handle_client'
  ...
~~~

Or separately:

~~~
(gdb) rb-stack-trace --values          # Ruby perspective with stack values
(gdb) bt                               # C perspective only
~~~

The combined view reveals the full execution path through both Ruby and C code.

## Best Practices

### Start with Combined Backtraces

Always use the combined backtrace first for full context:

~~~
(gdb) rb-fiber-scan-stack-trace-all    # Overview of all fibers
(gdb) rb-fiber-scan-switch 5           # Switch to specific fiber
(gdb) rb-stack-trace                   # Detailed combined backtrace
~~~

This gives both Ruby and C context immediately.

### Use Fiber Switching for Deep Inspection

For detailed C-level inspection, switch to the fiber and use standard GDB commands:

~~~
(gdb) rb-fiber-scan-switch 5
(gdb) bt                        # C backtrace only
(gdb) frame 2                   # Navigate frames
(gdb) info args                 # See C function arguments
(gdb) info locals               # See C local variables
~~~

### Check Frame Types

Different frame types have different data available:

~~~
Frame Type: VM_FRAME_MAGIC_METHOD     # Regular Ruby method
Frame Type: VM_FRAME_MAGIC_CFUNC      # C function called from Ruby
Frame Type: VM_FRAME_MAGIC_BLOCK      # Block/lambda
Frame Type: VM_FRAME_MAGIC_IFUNC      # Internal function
~~~

C function frames don't have ISEQ (instruction sequence) data.

## Common Pitfalls

### Confusing Stack Direction

Ruby's VM stack grows up (toward higher addresses):

~~~
VM Stack: 0x7f8a1c950000 - 0x7f8a1c960000
Current SP: 0x7f8a1c950100      # Near the base
~~~

But the C stack typically grows down:

~~~
Stack Start: 0x7f8a1e100000
Stack End:   0x7f8a1e000000     # Lower address
~~~

Pay attention to which stack you're examining.

### Accessing Out-of-Bounds

Don't access stack beyond valid range:

~~~
(gdb) rb-fiber-stack-top 5 10000   # Might read invalid memory
~~~

Check the stack depth first.

### Terminated Fiber Stacks

Terminated fibers don't have valid saved contexts:

~~~
(gdb) rb-fiber 8
  Status: TERMINATED            # No useful stack data
~~~

Focus on SUSPENDED and RESUMED fibers for debugging.

## Troubleshooting

### Stack Appears Empty

If `rb-stack-trace` shows no frames:

1. Ensure you've switched to a fiber: `rb-fiber-scan-switch 5`
2. Check fiber status in scan output (avoid TERMINATED fibers)
3. Try C-only backtrace: `bt`

### C Backtrace Too Short

After `rb-fiber-scan-switch`, if `bt` shows few frames:

1. The fiber may be newly created
2. Use: `rb-stack-trace` for the combined view
3. The C backtrace only shows where the fiber was suspended

The combined `rb-stack-trace` gives the full picture.

## See Also

- {ruby Ruby::GDB::object-inspection Object inspection} for examining stack values
- {ruby Ruby::GDB::fiber-debugging Fiber debugging} for fiber-specific commands
- {ruby Ruby::GDB::heap-debugging Heap debugging} for finding objects on the heap


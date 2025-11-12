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

### VM Stack for a Fiber

Show detailed VM stack information:

~~~
(gdb) rb-fiber-vm-stack 5
VM Stack for Fiber #5:
  Base: 0x7f8a1c950000
  Size: 4096 VALUEs (32768 bytes)
  CFP:  0x7f8a1c951000

Use GDB commands to examine:
  x/4096gx 0x7f8a1c950000         # Examine as hex values
  p *((VALUE *)0x7f8a1c950000)@100  # Print first 100 values
~~~

### Walking Control Frames

See detailed information about each Ruby method call:

~~~
(gdb) rb-fiber-vm-frames 5
VM Control Frames for Fiber #5:
  Fiber: 0x7f8a1c800500 (status: SUSPENDED)

Frame #0 (depth 45):
  CFP Address: 0x7f8a1c951000
  PC:         0x7f8a1c234500
  SP:         0x7f8a1c950100
  EP:         0x7f8a1c950200
  Self:       0x7f8a1c888888
  Location:   /app/lib/connection.rb:123
  Method:     read
  Frame Type: VM_FRAME_MAGIC_METHOD
  Stack Depth: 256 slots

Frame #1 (depth 44):
  ...
~~~

This shows the complete Ruby call chain.

### Values on Stack Top

Inspect the current values being computed:

~~~
(gdb) rb-fiber-stack-top 5 10
VM Stack Top for Fiber #5:

Top 10 VALUE(s) on stack (newest first):

  [ -1] 0x00007f8a1c888888  T_STRING      "data"
  [ -2] 0x0000000000000015  Fixnum(10)    Fixnum: 10
  [ -3] 0x00007f8a1c999999  T_HASH        <hash:len=3>
  [ -4] 0x0000000000000000  Qfalse        Qfalse
  ...
~~~

This is useful for understanding what values are being passed between methods.

## Inspecting C Stacks

### C Stack Information

View native stack details for a fiber:

~~~
(gdb) rb-fiber-c-stack 5
C/Machine Stack for Fiber #5:
  Fiber: 0x7f8a1c800500
  Stack Base:    0x7f8a1e000000
  Stack Size:    1048576 bytes
  Stack Start:   0x7f8a1e000000
  Stack End:     0x7f8a1e0f0000
  Stack Used:    983040 bytes (grows down)
~~~

### Walking C Frames

Attempt to walk the native call stack:

~~~
(gdb) rb-fiber-c-frames 5
C/Native Stack Frames for Fiber #5:
  ...

Frame #0: (initial context)
  SP: 0x7f8a1e0f0000

Frame #1:
  FP: 0x7f8a1e0f0010
  Return Address: 0x7f8a1ab12345 - fiber_setcontext

Frame #2:
  FP: 0x7f8a1e0f0080
  Return Address: 0x7f8a1ab12400 - rb_fiber_yield
...
~~~

Note: For suspended fibers, this may be incomplete. Use `rb-fiber-switch` for accurate C backtraces.

## Practical Examples

### Finding Where Execution Stopped

Identify the exact location in both Ruby and C:

~~~
(gdb) rb-fiber-bt 5             # Ruby backtrace
  45: /app/lib/connection.rb:123:in `read'

(gdb) rb-fiber-switch 5         # Switch to fiber context
(gdb) bt                        # C backtrace
#0  fiber_setcontext
#1  rb_fiber_yield
#2  rb_io_wait_readable
#3  rb_io_read
~~~

This shows the fiber is suspended in `read`, waiting for I/O.

### Debugging Deep Recursion

Detect excessive call depth:

~~~
(gdb) rb-fiber-vm-frames 5 | grep "Frame #" | wc -l
134                            # 134 Ruby frames!

(gdb) rb-fiber-vm-frames 5 | grep "Location"
  Location:   /app/lib/parser.rb:45
  Location:   /app/lib/parser.rb:45
  Location:   /app/lib/parser.rb:45
  ...                          # Same method recursing
~~~

Identifies a recursion issue in the parser.

### Examining Method Arguments

See what was passed to a method:

~~~
(gdb) rb-fiber-vm-frames 5
Frame #0:
  Stack Depth: 3 slots         # Method has 3 values on stack

(gdb) rb-fiber-stack-top 5 3
  [ -1] 0x00007f8a1c888888  T_STRING      "filename.txt"
  [ -2] 0x00000000000000b5  Fixnum(90)    Fixnum: 90
  [ -3] 0x00007f8a1c777777  T_HASH        <options>

(gdb) rb-object-print 0x00007f8a1c777777 --depth 2
AR Table (options hash with mode, encoding, etc.)
~~~

### Tracking Fiber Switches

See the call stack across fiber boundaries:

~~~
(gdb) rb-fiber-switch 5
(gdb) bt
#0  fiber_setcontext
#1  rb_fiber_yield            # Fiber yielded here
#2  rb_io_wait_readable       # Waiting for I/O
#3  some_io_operation

(gdb) frame 3
(gdb) info locals              # C variables at I/O call
~~~

## Combining VM and C Stacks

For the complete picture, inspect both:

~~~
(gdb) rb-fiber-bt 5                    # Ruby perspective
  45: /app/lib/connection.rb:123:in `read'
  44: /app/lib/connection.rb:89:in `receive'
  
(gdb) rb-fiber-switch 5                # Switch context
(gdb) bt                               # C perspective  
#0  fiber_setcontext
#1  rb_fiber_yield
#2  rb_io_wait_readable
#3  rb_io_read
#4  rb_io_sysread_internal
~~~

This shows:
- Ruby level: `read` method in connection.rb
- C level: Suspended in `rb_io_wait_readable`

The combination reveals the full execution path.

## Best Practices

### Start with Ruby Backtraces

Always check Ruby-level backtraces first:

~~~
(gdb) rb-all-fiber-bt           # Overview of all fibers
(gdb) rb-fiber-bt 5             # Detailed Ruby backtrace
~~~

This gives context before diving into C-level details.

### Use Fiber Switching for Accuracy

For the most accurate C stack views, switch to the fiber:

~~~
(gdb) rb-fiber-switch 5
(gdb) bt                        # Accurate backtrace
(gdb) frame 2                   # Navigate frames
(gdb) info args                 # See C function arguments
~~~

Walking frames manually (`rb-fiber-c-frames`) is best-effort only.

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

If `rb-fiber-bt` shows no frames:

1. Check fiber status: `rb-fiber 5`
2. Verify it's not TERMINATED
3. Try: `rb-fiber-vm-frames 5` for raw frame data
4. Use: `rb-fiber-debug-unwind 5` to see saved register state

### C Backtrace Too Short

After `rb-fiber-switch`, if `bt` shows few frames:

1. The fiber may be newly created
2. Check: `rb-fiber-bt 5` for Ruby-level frames
3. Compare with: `rb-fiber-vm-frames 5` for all VM frames

The C backtrace only shows where the fiber was suspended, not the full Ruby call chain.

## See Also

- {ruby Ruby::GDB::object-inspection Object inspection} for examining stack values
- {ruby Ruby::GDB::fiber-debugging Fiber debugging} for fiber-specific commands
- {ruby Ruby::GDB::heap-debugging Heap debugging} for finding objects on the heap


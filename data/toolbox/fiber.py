import gdb
import gdb.unwinder
import re
import struct
import json
import os
import sys

# Import command parser
import command
import value
import format
import heap
import rexception

# Global cache of fibers
_fiber_cache = []

# Global fiber unwinder instance
_fiber_unwinder = None

# Global current fiber (managed by rb-fiber-switch command)
_current_fiber = None

def parse_fiber_index(arg):
    """Parse fiber index from argument string.
    
    Returns:
        (index, error_message) - index is None if parsing failed
    """
    if not arg or not arg.strip():
        return None, "Usage: provide <index>"
    
    arguments = command.parse_arguments(arg)
    
    if not arguments.expressions:
        return None, "Error: No index provided"
    
    try:
        index = int(arguments.expressions[0])
        return index, None
    except ValueError:
        return None, f"Error: invalid index '{arguments.expressions[0]}'"

def get_current_fiber():
    """Get the currently selected fiber (if any).
    
    Returns:
        RubyFiber instance or None
    """
    return _current_fiber

def set_current_fiber(fiber):
    """Set the currently selected fiber.
    
    Args:
        fiber: RubyFiber instance or None
    
    Note: Should only be called by rb-fiber-switch command.
    """
    global _current_fiber
    _current_fiber = fiber

class RubyFiber:
    """Wrapper for Ruby Fiber objects.
    
    Wraps a Fiber VALUE and provides high-level interface for fiber introspection.
    """
    
    # Fiber status constants
    FIBER_STATUS = {
        0: "CREATED",
        1: "RESUMED",
        2: "SUSPENDED",
        3: "TERMINATED"
    }
    
    def __init__(self, fiber_value):
        """Initialize with a Fiber VALUE.
        
        Args:
            fiber_value: A GDB value representing a Ruby Fiber object (VALUE)
        """
        self.value = fiber_value
        self._pointer = None
        self._ec = None
        self._exception = None
        
    def _extract_fiber_pointer(self):
        """Extract struct rb_fiber_struct* from the Fiber VALUE."""
        if self._pointer is None:
            # Cast to RTypedData and extract the data pointer
            rtypeddata_type = gdb.lookup_type('struct RTypedData').pointer()
            typed_data = self.value.cast(rtypeddata_type)
            
            rb_fiber_struct_type = gdb.lookup_type('struct rb_fiber_struct').pointer()
            self._pointer = typed_data['data'].cast(rb_fiber_struct_type)
        
        return self._pointer
    
    @property
    def pointer(self):
        """Get the struct rb_fiber_struct* pointer."""
        return self._extract_fiber_pointer()
    
    @property
    def address(self):
        """Get the raw address of the fiber struct."""
        return int(self.pointer)
    
    @property
    def status(self):
        """Get fiber status as string (CREATED, RESUMED, etc.)."""
        status_code = int(self.pointer['status'])
        return self.FIBER_STATUS.get(status_code, f"UNKNOWN({status_code})")
    
    @property
    def stack_base(self):
        """Get fiber stack base pointer."""
        return self.pointer['stack']['base']
    
    @property
    def stack_size(self):
        """Get fiber stack size."""
        return int(self.pointer['stack']['size'])
    
    @property
    def ec(self):
        """Get execution context (rb_execution_context_t*)."""
        if self._ec is None:
            self._ec = self.pointer['cont']['saved_ec'].address
        return self._ec
    
    @property
    def vm_stack(self):
        """Get VM stack pointer."""
        return self.ec['vm_stack']
    
    @property
    def vm_stack_size(self):
        """Get VM stack size."""
        return int(self.ec['vm_stack_size'])
    
    @property
    def cfp(self):
        """Get control frame pointer."""
        return self.ec['cfp']
    
    @property
    def exception(self):
        """Get current exception RException object (if any).
        
        Returns:
            RException instance or None
        """
        if self._exception is None:
            try:
                errinfo_val = self.ec['errinfo']
                
                # Only process if it's a real object (not nil or other immediate value)
                if value.is_object(errinfo_val) and not value.is_nil(errinfo_val):
                    try:
                        self._exception = rexception.RException(errinfo_val)
                    except Exception:
                        # If we can't create RException, return None
                        pass
            except Exception:
                pass
        
        return self._exception
    
    @property
    def exception_info(self):
        """Get formatted exception string (if any).
        
        Returns:
            Formatted exception string or None
        """
        exc = self.exception
        if exc:
            return str(exc)
        return None
    
    def print_info(self, terminal):
        """Print summary information about this fiber.
        
        Args:
            terminal: Terminal instance for formatted output
        """
        # Print fiber VALUE and address
        print(f"Fiber VALUE: ", end='')
        print(terminal.print_type_tag('T_DATA', int(self.value), None))
        print(f"  Address: ", end='')
        print(terminal.print_type_tag('struct rb_fiber_struct', self.address, None))
        
        # Print status
        print(f"  Status: {self.status}")
        
        # Print exception if present
        exc_info = self.exception_info
        if exc_info:
            print(f"  Exception: {exc_info}")
        
        # Print Stack with formatted pointer
        stack_type = str(self.stack_base.type)
        print(f"  Stack: ", end='')
        print(terminal.print_type_tag(stack_type, int(self.stack_base), f'size={self.stack_size}'))
        
        # Print VM Stack with formatted pointer
        vm_stack_type = str(self.vm_stack.type)
        print(f"  VM Stack: ", end='')
        print(terminal.print_type_tag(vm_stack_type, int(self.vm_stack), f'size={self.vm_stack_size}'))
        
        # Print CFP
        print(f"  CFP: ", end='')
        print(terminal.print_type_tag('rb_control_frame_t', int(self.cfp), None))


class RubyFiberScanHeapCommand(gdb.Command):
    """Scan heap and list all Ruby fibers.

    Usage: rb-fiber-scan-heap [limit] [--cache [filename]]
    Examples: rb-fiber-scan-heap                    # Find all fibers
              rb-fiber-scan-heap 10                 # Find first 10 fibers
              rb-fiber-scan-heap --cache            # Use fibers.json cache
              rb-fiber-scan-heap --cache my.json    # Use custom cache file
    """

    def __init__(self):
        super(RubyFiberScanHeapCommand, self).__init__("rb-fiber-scan-heap", gdb.COMMAND_USER)
        self.heap = heap.RubyHeap()
    
    def usage(self):
        """Print usage information."""
        print("Usage: rb-fiber-scan-heap [limit] [--cache [filename]]")
        print("Examples:")
        print("  rb-fiber-scan-heap                    # Find all fibers")
        print("  rb-fiber-scan-heap 10                 # Find first 10 fibers")
        print("  rb-fiber-scan-heap --cache            # Use fibers.json cache")
        print("  rb-fiber-scan-heap --cache my.json    # Use custom cache file")

    def save_cache(self, fiber_values, filename):
        """Save fiber VALUE addresses to cache file.
        
        Args:
            fiber_values: List of Fiber VALUEs
            filename: Path to cache file
        """
        try:
            data = {
                'version': 1,
                'fiber_count': len(fiber_values),
                'fibers': [int(f) for f in fiber_values]  # Store VALUE addresses
            }
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Saved {len(fiber_values)} fiber VALUE(s) to {filename}")
            return True
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")
            return False

    def load_cache(self, filename):
        """Load fiber VALUE addresses from cache file.
        
        Args:
            filename: Path to cache file
        
        Returns:
            List of VALUEs or None if loading failed
        """
        try:
            with open(filename, 'r') as f:
                data = json.load(f)

            if data.get('version') != 1:
                print(f"Warning: Unknown cache version, ignoring cache")
                return None

            fiber_addrs = data.get('fibers', [])
            print(f"Loaded {len(fiber_addrs)} fiber VALUE address(es) from {filename}")

            # Initialize heap to ensure we have type information
            if not self.heap.initialize():
                return None

            # Reconstruct VALUEs from addresses
            value_type = gdb.lookup_type('VALUE')
            fibers = []
            for addr in fiber_addrs:
                try:
                    fiber_val = gdb.Value(addr).cast(value_type)
                    fibers.append(fiber_val)
                except (gdb.error, gdb.MemoryError):
                    print(f"Warning: Could not access VALUE at 0x{addr:x}")

            print(f"Successfully reconstructed {len(fibers)} fiber VALUE(s)")
            return fibers

        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Warning: Failed to load cache: {e}")
            return None

    def invoke(self, arg, from_tty):
        global _fiber_cache

        # Create terminal for formatting
        terminal = format.create_terminal(from_tty)

        # Parse arguments using the robust parser
        arguments = command.parse_arguments(arg if arg else "")
        
        # Get limit from first expression (positional argument)
        limit = None
        if arguments.expressions:
            try:
                limit = int(arguments.expressions[0])
                if limit <= 0:
                    print("Error: limit must be positive")
                    self.usage()
                    return
            except ValueError:
                print(f"Error: invalid limit '{arguments.expressions[0]}'")
                self.usage()
                return
        
        # Check for --cache flag
        use_cache = arguments.has_flag('cache')
        cache_file = arguments.get_option('cache', 'fibers.json')

        # Try to load from cache if requested
        if use_cache:
            loaded_fibers = self.load_cache(cache_file)
            if loaded_fibers is not None:
                # Successfully loaded from cache
                _fiber_cache = loaded_fibers

                print(f"\nLoaded {len(loaded_fibers)} fiber(s) from cache:\n")

                for i, fiber_val in enumerate(loaded_fibers):
                    try:
                        fiber_obj = RubyFiber(fiber_val)
                        self._print_fiber_info(terminal, i, fiber_obj)
                    except:
                        print(f"Fiber #{i}: VALUE 0x{int(fiber_val):x}")
                        print(f"  (error creating RubyFiber)")
                        print()

                print(f"Fibers cached. Use 'rb-fiber-scan-switch <index>' to switch to a fiber.")
                return
            else:
                print(f"Cache file '{cache_file}' not found, proceeding with scan...")
                print()

        # Initialize heap scanner
        if not self.heap.initialize():
            return

        # Get fiber_data_type for matching
        fiber_data_type = gdb.parse_and_eval('&fiber_data_type')

        if limit:
            print(f"Scanning heap for first {limit} Fiber object(s)...", file=sys.stderr)
        else:
            print("Scanning heap for Fiber objects...", file=sys.stderr)

        # Use RubyHeap to find fibers (returns VALUEs)
        fiber_values = self.heap.find_typed_data(fiber_data_type, limit=limit, progress=True)

        # Cache the VALUEs for later use
        _fiber_cache = fiber_values

        if limit and len(fiber_values) >= limit:
            print(f"\nFound {len(fiber_values)} fiber(s) (limit reached):\n")
        else:
            print(f"\nFound {len(fiber_values)} fiber(s):\n")

        for i, fiber_val in enumerate(fiber_values):
            fiber_obj = RubyFiber(fiber_val)
            self._print_fiber_info(terminal, i, fiber_obj)

        # Save to cache if requested
        if use_cache and fiber_values:
            self.save_cache(fiber_values, cache_file)
            print()

        print(f"Fibers cached. Use 'rb-fiber-scan-switch <index>' to switch to a fiber.")

    def _print_fiber_info(self, terminal, index, fiber_obj):
        """Print formatted fiber information.
        
        Args:
            terminal: Terminal instance for formatting
            index: Fiber index in cache
            fiber_obj: RubyFiber instance
        """
        # Print fiber index with VALUE and pointer
        print(f"Fiber #{index}: ", end='')
        print(terminal.print_type_tag('T_DATA', int(fiber_obj.value)), end='')
        print(' → ', end='')
        print(terminal.print_type_tag('struct rb_fiber_struct', fiber_obj.address))
        
        # Print status
        print(f"  Status: {fiber_obj.status}")
        
        # Print exception if present (catch errors for terminated fibers)
        try:
            exc_info = fiber_obj.exception_info
            if exc_info:
                print(f"  Exception: {exc_info}")
        except Exception:
            # Silently skip exception info if we can't read it
            pass
        
        # Print Stack with formatted pointer
        stack_type = str(fiber_obj.stack_base.type)
        print(f"  Stack: ", end='')
        print(terminal.print_type_tag(stack_type, int(fiber_obj.stack_base), f'size={fiber_obj.stack_size}'))
        
        # Print VM Stack with formatted pointer
        vm_stack_type = str(fiber_obj.vm_stack.type)
        print(f"  VM Stack: ", end='')
        print(terminal.print_type_tag(vm_stack_type, int(fiber_obj.vm_stack), f'size={fiber_obj.vm_stack_size}'))
        
        # Print CFP
        cfp_type = str(fiber_obj.cfp.type).replace(' *', '')  # Remove pointer marker for display
        print(f"  CFP: ", end='')
        print(terminal.print_type_tag(cfp_type, int(fiber_obj.cfp)))
        print()


class RubyFiberScanSwitchCommand(gdb.Command):
    """Switch to a fiber from the scan heap cache.

    Usage: rb-fiber-scan-switch <index>
    Example: rb-fiber-scan-switch 0
             rb-fiber-scan-switch 2
    
    Note: This command requires a fiber cache populated by 'rb-fiber-scan-heap'.
    """

    def __init__(self):
        super(RubyFiberScanSwitchCommand, self).__init__("rb-fiber-scan-switch", gdb.COMMAND_USER)
    
    def usage(self):
        """Print usage information."""
        print("Usage: rb-fiber-scan-switch <index>")
        print("Examples:")
        print("  rb-fiber-scan-switch 0    # Switch to fiber #0")
        print("  rb-fiber-scan-switch 2    # Switch to fiber #2")
        print()
        print("Note: Run 'rb-fiber-scan-heap' first to populate the fiber cache.")

    def invoke(self, arg, from_tty):
        global _fiber_cache

        if not arg or not arg.strip():
            self.usage()
            return

        # Check if cache is populated
        if not _fiber_cache:
            print("Error: No fibers in cache. Run 'rb-fiber-scan-heap' first.")
            return

        # Parse index
        try:
            index = int(arg.strip())
        except ValueError:
            print(f"Error: Invalid index '{arg}'. Must be an integer.")
            self.usage()
            return

        # Validate index
        if index < 0 or index >= len(_fiber_cache):
            print(f"Error: Index {index} out of range [0, {len(_fiber_cache)-1}]")
            print(f"\nRun 'rb-fiber-scan-heap' to see available fibers.")
            return

        # Get fiber VALUE from cache
        fiber_value = _fiber_cache[index]

        print(f"Switching to Fiber #{index}: VALUE 0x{int(fiber_value):x}")

        # Delegate to rb-fiber-switch command
        # This command manages the global _current_fiber state
        try:
            gdb.execute(f"rb-fiber-switch 0x{int(fiber_value):x}", from_tty=from_tty)
        except gdb.error as e:
            print(f"Error switching to fiber: {e}")
            import traceback
            traceback.print_exc()


class RubyFiberUnwinder(gdb.unwinder.Unwinder):
    """Custom unwinder for Ruby fibers.

    This allows GDB to unwind a fiber's stack even in a core dump,
    by extracting saved register state from the fiber's jmp_buf.

    Based on similar technique from Facebook Folly:
    https://github.com/facebook/folly/blob/main/folly/fibers/scripts/gdb.py
    """

    def __init__(self):
        super(RubyFiberUnwinder, self).__init__("Ruby Fiber Unwinder")
        self.active_fiber = None
        self.unwound_first_frame = False

    def __call__(self, pending_frame):
        """Called by GDB when unwinding frames."""
        # Only unwind if we have an active fiber set
        if not self.active_fiber:
            return None

        # Only unwind the first frame, then let GDB continue normally
        if self.unwound_first_frame:
            return None

        try:
            # Ruby uses its own coroutine implementation, not setjmp/longjmp!
            # Registers are saved in fiber->context.stack_pointer
            # See coroutine/amd64/Context.S for the layout

            coroutine_ctx = self.active_fiber['context']
            stack_ptr = coroutine_ctx['stack_pointer']

            # The stack_pointer points to the saved register area
            # From Context.S (x86-64):
            #   [stack_pointer + 0]  = R15
            #   [stack_pointer + 8]  = R14
            #   [stack_pointer + 16] = R13
            #   [stack_pointer + 24] = R12
            #   [stack_pointer + 32] = RBX
            #   [stack_pointer + 40] = RBP
            #   [stack_pointer + 48] = Return address (RIP)

            if int(stack_ptr) == 0:
                return None

            # Cast to uint64 pointer to read saved registers
            uint64_ptr = stack_ptr.cast(gdb.lookup_type('uint64_t').pointer())

            # Read saved registers (keep as gdb.Value)
            r15 = uint64_ptr[0]
            r14 = uint64_ptr[1]
            r13 = uint64_ptr[2]
            r12 = uint64_ptr[3]
            rbx = uint64_ptr[4]
            rbp = uint64_ptr[5]

            # After coroutine_transfer executes 'addq $48, %rsp', RSP points to the return address
            # After 'ret' pops the return address, RSP = stack_ptr + 48 + 8
            # We want to create an unwind frame AS IF we're in the caller of coroutine_transfer
            # So RSP should be pointing AFTER the return address was popped
            rsp_value = int(stack_ptr) + 48 + 8
            rsp = gdb.Value(rsp_value).cast(gdb.lookup_type('uint64_t'))

            # The return address (RIP) is at [stack_ptr + 48]
            # This is what 'ret' will pop and jump to
            rip_ptr = gdb.Value(int(stack_ptr) + 48).cast(gdb.lookup_type('uint64_t').pointer())
            rip = rip_ptr.dereference()

            # Sanity check
            if int(rsp) == 0 or int(rip) == 0:
                return None

            # Create frame ID
            frame_id = gdb.unwinder.FrameId(int(rsp), int(rip))

            # Create unwind info
            unwind_info = pending_frame.create_unwind_info(frame_id)

            # Add saved registers
            unwind_info.add_saved_register("rip", rip)
            unwind_info.add_saved_register("rsp", rsp)
            unwind_info.add_saved_register("rbp", rbp)
            unwind_info.add_saved_register("rbx", rbx)
            unwind_info.add_saved_register("r12", r12)
            unwind_info.add_saved_register("r13", r13)
            unwind_info.add_saved_register("r14", r14)
            unwind_info.add_saved_register("r15", r15)

            # Mark that we've unwound the first frame
            self.unwound_first_frame = True

            return unwind_info

        except (gdb.error, gdb.MemoryError) as e:
            # If we can't read the fiber context, bail
            return None

    def activate_fiber(self, fiber):
        """Activate unwinding for a specific fiber."""
        self.active_fiber = fiber
        self.unwound_first_frame = False
        gdb.invalidate_cached_frames()

    def deactivate(self):
        """Deactivate fiber unwinding."""
        self.active_fiber = None
        self.unwound_first_frame = False
        gdb.invalidate_cached_frames()


class RubyFiberSwitchCommand(gdb.Command):
    """Switch GDB's stack view to a specific fiber.

    Usage: rb-fiber-switch <fiber_value_or_address>
           rb-fiber-switch off

    Examples: 
        rb-fiber-switch 0x7fffdc409ca8    # VALUE address
        rb-fiber-switch $fiber_val         # GDB variable
        rb-fiber-switch off                # Deactivate unwinder

    This uses a custom unwinder to make GDB follow the fiber's saved
    stack, allowing you to use 'bt', 'up', 'down', 'frame', etc.
    Works even with core dumps!

    Based on technique from Facebook Folly fibers.
    """

    def __init__(self):
        super(RubyFiberSwitchCommand, self).__init__("rb-fiber-switch", gdb.COMMAND_USER)
        self._ensure_unwinder()
    
    def usage(self):
        """Print usage information."""
        print("Usage: rb-fiber-switch <fiber_value_or_address>")
        print("       rb-fiber-switch off")
        print("Examples:")
        print("  rb-fiber-switch 0x7fffdc409ca8    # VALUE address")
        print("  rb-fiber-switch $fiber             # GDB variable")
        print("  rb-fiber-switch off                # Deactivate unwinder")
        print()
        print("After switching, you can use: bt, up, down, frame, info locals, etc.")

    def _ensure_unwinder(self):
        """Ensure the fiber unwinder is registered."""
        global _fiber_unwinder
        if _fiber_unwinder is None:
            _fiber_unwinder = RubyFiberUnwinder()
            gdb.unwinder.register_unwinder(None, _fiber_unwinder, replace=True)

    def invoke(self, arg, from_tty):
        global _fiber_unwinder

        if not arg:
            self.usage()
            return

        # Check for deactivate
        if arg and arg.lower() in ('off', 'none', 'deactivate'):
            _fiber_unwinder.deactivate()
            set_current_fiber(None)
            print("Fiber unwinder deactivated. Switched back to normal stack view.")
            print("Try: bt")
            return

        # Parse the argument as a VALUE
        try:
            # Evaluate the expression to get a VALUE
            fiber_value = gdb.parse_and_eval(arg)
            
            # Ensure it's cast to VALUE type
            try:
                value_type = gdb.lookup_type('VALUE')
            except gdb.error as lookup_err:
                print(f"Error: Could not lookup type 'VALUE': {lookup_err}")
                print("This usually means Ruby symbols aren't fully loaded yet.")
                print(f"Try running the process further or checking symbol loading.")
                return
            
            fiber_value = fiber_value.cast(value_type)
            
        except (gdb.error, RuntimeError) as e:
            print(f"Error: Could not evaluate '{arg}' as a VALUE")
            print(f"Details: {e}")
            import traceback
            traceback.print_exc()
            print()
            self.usage()
            return

        # Create RubyFiber wrapper
        try:
            fiber_obj = RubyFiber(fiber_value)
        except Exception as e:
            print(f"Error: Could not create RubyFiber from VALUE 0x{int(fiber_value):x}")
            print(f"Details: {e}")
            import traceback
            traceback.print_exc()
            return

        # Check if fiber is in a switchable state
        if fiber_obj.status in ('CREATED', 'TERMINATED'):
            print(f"Warning: Fiber is {fiber_obj.status}, may not have valid saved context")
            print()

        # Update global current fiber state
        set_current_fiber(fiber_obj)

        # Get the fiber pointer for unwinder
        fiber_ptr = fiber_obj.pointer

        # Activate the unwinder for this fiber
        _fiber_unwinder.activate_fiber(fiber_ptr)

        # Set convenience variables for the fiber context
        ec = fiber_ptr['cont']['saved_ec'].address
        gdb.set_convenience_variable('fiber', fiber_value)
        gdb.set_convenience_variable('fiber_ptr', fiber_ptr)
        gdb.set_convenience_variable('ec', ec)

        # Set errinfo if present (check for real object, not special constant)
        errinfo_val = ec['errinfo']
        errinfo_int = int(errinfo_val)
        is_special = (errinfo_int & 0x03) != 0 or errinfo_int == 0
        if not is_special:
            gdb.set_convenience_variable('errinfo', errinfo_val)

        # Create terminal for formatting
        terminal = format.create_terminal(from_tty)

        # Print switch confirmation
        print(f"Switched to Fiber: ", end='')
        print(terminal.print_type_tag('T_DATA', int(fiber_value), None), end='')
        print(' → ', end='')
        print(terminal.print_type_tag('struct rb_fiber_struct', fiber_obj.address, None))
        print(f"  Status: {fiber_obj.status}")
        
        # Print exception if present (catch errors for terminated fibers)
        try:
            exc_info = fiber_obj.exception_info
            if exc_info:
                print(f"  Exception: {exc_info}")
        except Exception:
            # Silently skip exception info if we can't read it
            pass
        print()

        # Set tag retval if present
        try:
            tag = ec['tag']
            if int(tag) != 0:
                tag_retval = tag['retval']
                tag_state = int(tag['state'])
                retval_int = int(tag_retval)
                is_retval_special = (retval_int & 0x03) != 0 or retval_int == 0
                if not is_retval_special:
                    gdb.set_convenience_variable('retval', tag_retval)
        except:
            tag = None
            is_retval_special = True

        print("Convenience variables set:")
        print(f"  $fiber     = Current fiber VALUE")
        print(f"  $fiber_ptr = Current fiber pointer (struct rb_fiber_struct *)")
        print(f"  $ec        = Execution context (rb_execution_context_t *)")
        if not is_special:
            print(f"  $errinfo   = Exception being handled (VALUE)")
        if tag and not is_retval_special:
            print(f"  $retval    = Return value from 'return' (VALUE)")
        print()
        print("Now try:")
        print("  bt          # Show C backtrace of fiber")
        print("  frame <n>   # Switch to frame N")
        print("  up/down     # Move up/down frames")
        print("  info locals # Show local variables")
        if not is_special:
            print("  rp $errinfo # Pretty print exception")
        if tag and not is_retval_special:
            print("  rp $retval  # Pretty print return value (in ensure blocks)")
        print()
        print("Useful VALUES to inspect:")
        print("  $ec->tag->retval        # Return value (in ensure after 'return')")
        print("  $ec->cfp->sp[-1]        # Top of VM stack")
        print("  $fiber_ptr->cont.value  # Fiber yield/return value")
        print()
        print("NOTE: Frame #0 is synthetic (created by the unwinder) and may look odd.")
        print("      The real fiber context starts at frame #1.")
        print("      Use 'frame 1' to skip to the actual fiber_setcontext frame.")
        print()
        print("To switch back:")
        print("  rb-fiber-switch off")


class RubyFiberScanStackTraceAllCommand(gdb.Command):
    """Print stack traces for all fibers in the scan cache.

    Usage: rb-fiber-scan-stack-trace-all

    This command prints the Ruby stack trace for each fiber that was
    found by 'rb-fiber-scan-heap'. Run that command first to populate
    the fiber cache.
    """

    def __init__(self):
        super(RubyFiberScanStackTraceAllCommand, self).__init__("rb-fiber-scan-stack-trace-all", gdb.COMMAND_USER)
    
    def usage(self):
        """Print usage information."""
        print("Usage: rb-fiber-scan-stack-trace-all")
        print()
        print("Note: Run 'rb-fiber-scan-heap' first to populate the fiber cache.")

    def invoke(self, arg, from_tty):
        global _fiber_cache

        # Check if cache is populated
        if not _fiber_cache:
            print("Error: No fibers in cache. Run 'rb-fiber-scan-heap' first.")
            return

        # Import stack module to use print_fiber_backtrace
        import stack

        print(f"Printing stack traces for {len(_fiber_cache)} fiber(s)\n")
        print("=" * 80)

        for i, fiber_value in enumerate(_fiber_cache):
            try:
                # Create RubyFiber wrapper to get fiber info
                fiber_obj = RubyFiber(fiber_value)
                
                print(f"\nFiber #{i}: VALUE 0x{int(fiber_value):x} → {fiber_obj.status}")
                print("-" * 80)

                # Use stack.print_fiber_backtrace with the fiber pointer
                stack.print_fiber_backtrace(fiber_obj.pointer, from_tty=from_tty)
                
            except Exception as e:
                print(f"\nFiber #{i}: VALUE 0x{int(fiber_value):x}")
                print("-" * 80)
                print(f"Error printing backtrace: {e}")
                import traceback
                traceback.print_exc()
            
            print()


# Register commands
RubyFiberScanHeapCommand()
RubyFiberScanSwitchCommand()
RubyFiberSwitchCommand()
RubyFiberScanStackTraceAllCommand()

"""Ruby execution context utilities and commands."""

import debugger
import format
import value
import rexception


class RubyContext:
    """Wrapper for Ruby execution context (rb_execution_context_t).
    
    Provides a high-level interface for working with Ruby execution contexts,
    including inspection, convenience variable setup, and information display.
    
    Example:
        ctx = RubyContext.current()
        if ctx:
            ctx.print_info(terminal)
            ctx.setup_convenience_variables()
    """
    
    def __init__(self, ec):
        """Create a RubyContext wrapper.
        
        Args:
            ec: Execution context pointer (rb_execution_context_t *)
        """
        self.ec = ec
        self._cfp = None
        self._errinfo = None
        self._vm_stack = None
        self._vm_stack_size = None
    
    @classmethod
    def current(cls):
        """Get the current execution context from the running thread.
        
        Tries multiple approaches in order of preference:
        1. ruby_current_ec - TLS variable (works in GDB, some LLDB)
        2. rb_current_ec_noinline() - function call (works in most cases)
        3. rb_current_ec() - macOS-specific function
        
        Returns:
            RubyContext instance, or None if not available
        """
        # Try ruby_current_ec variable first
        try:
            ec = debugger.parse_and_eval('ruby_current_ec')
            if ec is not None and int(ec) != 0:
                return cls(ec)
        except debugger.Error:
            pass
        
        # Fallback to rb_current_ec_noinline() function
        try:
            ec = debugger.parse_and_eval('rb_current_ec_noinline()')
            if ec is not None and int(ec) != 0:
                return cls(ec)
        except debugger.Error:
            pass
        
        # Last resort: rb_current_ec() (macOS-specific)
        try:
            ec = debugger.parse_and_eval('rb_current_ec()')
            if ec is not None and int(ec) != 0:
                return cls(ec)
        except debugger.Error:
            pass
        
        return None
    
    @property
    def cfp(self):
        """Get control frame pointer (lazy load)."""
        if self._cfp is None:
            try:
                self._cfp = self.ec['cfp']
            except Exception:
                pass
        return self._cfp
    
    @property
    def errinfo(self):
        """Get exception VALUE (lazy load)."""
        if self._errinfo is None:
            try:
                self._errinfo = self.ec['errinfo']
            except Exception:
                pass
        return self._errinfo
    
    @property
    def has_exception(self):
        """Check if there's a real exception (not nil/special value)."""
        if self.errinfo is None:
            return False
        return rexception.is_exception(self.errinfo)
    
    @property
    def vm_stack(self):
        """Get VM stack pointer (lazy load)."""
        if self._vm_stack is None:
            try:
                self._vm_stack = self.ec['vm_stack']
            except Exception:
                pass
        return self._vm_stack
    
    @property
    def vm_stack_size(self):
        """Get VM stack size (lazy load)."""
        if self._vm_stack_size is None:
            try:
                self._vm_stack_size = int(self.ec['vm_stack_size'])
            except Exception:
                pass
        return self._vm_stack_size
    
    def setup_convenience_variables(self):
        """Set up convenience variables for this execution context.
        
        Sets:
            $ec       - Execution context pointer
            $cfp      - Control frame pointer
            $errinfo  - Current exception (if any)
        
        Returns:
            dict with keys: 'ec', 'cfp', 'errinfo' (values are the set variables)
        """
        result = {}
        
        # Set $ec
        debugger.set_convenience_variable('ec', self.ec)
        result['ec'] = self.ec
        
        # Set $cfp (control frame pointer)
        if self.cfp is not None:
            debugger.set_convenience_variable('cfp', self.cfp)
            result['cfp'] = self.cfp
        else:
            result['cfp'] = None
        
        # Set $errinfo if there's an exception
        if self.has_exception:
            debugger.set_convenience_variable('errinfo', self.errinfo)
            result['errinfo'] = self.errinfo
        else:
            result['errinfo'] = None
        
        return result
    
    def print_info(self, terminal):
        """Print detailed information about this execution context.
        
        Args:
            terminal: Terminal formatter for output
        """
        print("Execution Context:")
        print(f"  $ec = ", end='')
        print(terminal.print_type_tag('rb_execution_context_t', int(self.ec), None))
        
        # VM Stack info
        if self.vm_stack is not None and self.vm_stack_size is not None:
            print(f"  VM Stack: ", end='')
            print(terminal.print_type_tag('VALUE', int(self.vm_stack), f'size={self.vm_stack_size}'))
        else:
            print(f"  VM Stack: <unavailable>")
        
        # Control Frame info
        if self.cfp is not None:
            print(f"  $cfp = ", end='')
            print(terminal.print_type_tag('rb_control_frame_t', int(self.cfp), None))
        else:
            print(f"  $cfp = <unavailable>")
        
        # Exception info
        if self.has_exception:
            print(f"  $errinfo = ", end='')
            print(terminal.print_type_tag('VALUE', int(self.errinfo), None))
            print("    Exception present!")
        else:
            errinfo_int = int(self.errinfo) if self.errinfo else 0
            if errinfo_int == 4:  # Qnil
                print("  Exception: None")
            elif errinfo_int == 0:  # Qfalse
                print("  Exception: None (false)")
            else:
                print(f"  Exception: None")
        
        # Tag info (for ensure blocks)
        try:
            tag = self.ec['tag']
            tag_int = int(tag)
            if tag_int != 0:
                print(f"  Tag: ", end='')
                print(terminal.print_type_tag('rb_vm_tag', tag_int, None))
                try:
                    retval = tag['retval']
                    retval_int = int(retval)
                    is_retval_special = (retval_int & 0x03) != 0 or retval_int == 0
                    if not is_retval_special:
                        print(f"    $retval available (in ensure block)")
                except Exception:
                    pass
        except Exception:
            pass


class RubyContextCommand(debugger.Command):
    """Show current execution context and set convenience variables.
    
    This command automatically discovers the current thread's execution context
    and displays detailed information about it, while also setting up convenience
    variables for easy inspection.
    
    Usage:
        rb-context
    
    Displays:
        - Execution context pointer and details
        - VM stack information
        - Control frame pointer
        - Exception information (if any)
    
    Sets these convenience variables:
        $ec       - Current execution context (rb_execution_context_t *)
        $cfp      - Current control frame pointer
        $errinfo  - Current exception (if any)
    
    Example:
        (gdb) rb-context
        Execution Context:
          $ec = <rb_execution_context_t *@0x...>
          VM Stack: <VALUE *@0x...> size=1024
          $cfp = <rb_control_frame_t *@0x...>
          Exception: None
        
        (gdb) rb-object-print $errinfo
        (gdb) rb-object-print $ec->cfp->sp[-1]
    """
    
    def __init__(self):
        super(RubyContextCommand, self).__init__("rb-context", debugger.COMMAND_USER)
    
    def invoke(self, arg, from_tty):
        """Execute the rb-context command."""
        try:
            terminal = format.create_terminal(from_tty)
            
            # Get current execution context
            ctx = RubyContext.current()
            
            if ctx is None:
                print("Error: Could not get current execution context")
                print()
                print("Possible reasons:")
                print("  • Ruby symbols not loaded (compile with debug symbols)")
                print("  • Process not stopped at a Ruby frame")
                print("  • Ruby not fully initialized yet")
                print()
                print("Try:")
                print("  • Break at a Ruby function: break rb_vm_exec")
                print("  • Use rb-fiber-scan-switch to switch to a fiber")
                print("  • Ensure Ruby debug symbols are available")
                return
            
            # Print context information
            ctx.print_info(terminal)
            
            # Set convenience variables
            vars = ctx.setup_convenience_variables()
            
            print()
            print("Convenience variables set:")
            print(f"  $ec      - Execution context")
            if vars.get('cfp'):
                print(f"  $cfp     - Control frame pointer")
            if vars.get('errinfo'):
                print(f"  $errinfo - Exception object")
            
            print()
            print("Now you can use:")
            print("  rb-object-print $errinfo")
            print("  rb-object-print $ec->cfp->sp[-1]")
            print("  rb-stack-trace")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()


# Register command
RubyContextCommand()


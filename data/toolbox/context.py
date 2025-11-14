"""Ruby execution context utilities and commands."""

import debugger
import command
import format
import value as rvalue
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
	
	@property
	def storage(self):
		"""Get fiber storage VALUE."""
		try:
			return self.ec['storage']
		except Exception:
			return None
	
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
		# Cache property lookups
		vm_stack = self.vm_stack
		vm_stack_size = self.vm_stack_size
		cfp = self.cfp
		storage = self.storage
		errinfo = self.errinfo
		has_exception = self.has_exception
		
		terminal.print("Execution Context:")
		terminal.print(f"  $ec = ", end='')
		terminal.print_type_tag('rb_execution_context_t', int(self.ec), None)
		terminal.print()
		
		# VM Stack info
		if vm_stack is not None and vm_stack_size is not None:
			terminal.print(f"  VM Stack: ", end='')
			terminal.print_type_tag('VALUE', int(vm_stack))
			terminal.print()
		else:
			terminal.print(f"  VM Stack: <unavailable>")
		
		# Control Frame info
		if cfp is not None:
			terminal.print(f"  $cfp = ", end='')
			terminal.print_type_tag('rb_control_frame_t', int(cfp), None)
			terminal.print()
		else:
			terminal.print(f"  $cfp = <unavailable>")
		
		# Storage info
		if storage is not None and not rvalue.is_nil(storage):
			terminal.print(f"  Storage: ", end='')
			terminal.print_type_tag('VALUE', int(storage), None)
			terminal.print()
		
		# Exception info
		if has_exception:
			terminal.print("  $errinfo = ", end='')
			terminal.print_type_tag('VALUE', int(errinfo), None)
			terminal.print()
			terminal.print("    Exception present!")
		else:
			errinfo_int = int(errinfo) if errinfo else 0
			if errinfo_int == 4:  # Qnil
				terminal.print("  Exception: None")
			elif errinfo_int == 0:  # Qfalse
				terminal.print("  Exception: None (false)")
			else:
				terminal.print("  Exception: None")
		
		# Tag info (for ensure blocks)
		try:
			tag = self.ec['tag']
			tag_int = int(tag)
			if tag_int != 0:
				terminal.print("  Tag: ", end='')
				terminal.print_type_tag('rb_vm_tag', tag_int, None)
				terminal.print()
				try:
					retval = tag['retval']
					retval_int = int(retval)
					is_retval_special = (retval_int & 0x03) != 0 or retval_int == 0
					if not is_retval_special:
						terminal.print("    $retval available (in ensure block)")
				except Exception:
					pass
		except Exception:
			pass


class RubyContextHandler:
	"""Show current execution context and set convenience variables."""
	
	USAGE = command.Usage(
		summary="Show current execution context and set convenience variables",
		parameters=[],
		options={},
		flags=[],
		examples=[
			("rb-context", "Display execution context info"),
			("rb-context; rb-print $errinfo", "Show context then print exception")
		]
	)
	
	def invoke(self, arguments, terminal):
		"""Execute the rb-context command."""
		try:
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


class RubyContextStorageHandler:
	"""Print the fiber storage from the current execution context."""
	
	USAGE = command.Usage(
		summary="Print fiber storage from current execution context",
		parameters=[],
		options={'depth': (int, 1, 'Recursion depth for nested objects')},
		flags=[('debug', 'Show debug information')],
		examples=[
			("rb-context-storage", "Print storage with default depth"),
			("rb-context-storage --depth 3", "Print storage with depth 3")
		]
	)
	
	def invoke(self, arguments, terminal):
		"""Execute the rb-context-storage command."""
		try:
			# Get current execution context
			ctx = RubyContext.current()
			
			if ctx is None:
				print("Error: Could not get current execution context")
				print("\nTry:")
				print("  • Run rb-context first to set up execution context")
				print("  • Break at a Ruby function")
				print("  • Use rb-fiber-scan-switch to switch to a fiber")
				return
			
			# Get storage
			storage_val = ctx.storage
			
			if storage_val is None:
				print("Error: Could not access fiber storage")
				return
			
			# Check if it's nil
			if rvalue.is_nil(storage_val):
				print("Fiber storage: nil")
				return
			
			# Parse arguments (--depth, --debug, etc.)
			arguments = command.parse_arguments(arg if arg else "")
			
			# Get depth flag
			depth = 1  # Default depth
			depth_str = arguments.get_option('depth')
			if depth_str:
				try:
					depth = int(depth_str)
				except ValueError:
					print(f"Error: invalid depth '{depth_str}'")
					return
			
			# Get debug flag
			debug = arguments.has_flag('debug')
			
			# Use print module to print the storage
			import print as print_module
			printer = print_module.RubyObjectPrinter()
			
			# Build arguments for the printer
			flags_set = {'debug'} if debug else set()
			args_for_printer = command.Arguments([storage_val], flags_set, {'depth': depth})
			
			printer.invoke(args_for_printer, terminal)
			
		except Exception as e:
			print(f"Error: {e}")
			import traceback
			traceback.print_exc()


# Register commands
debugger.register("rb-context", RubyContextHandler, usage=RubyContextHandler.USAGE)
debugger.register("rb-context-storage", RubyContextStorageHandler, usage=RubyContextStorageHandler.USAGE)

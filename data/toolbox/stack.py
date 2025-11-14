"""Stack inspection commands for Ruby processes."""

import debugger
import sys

# Import Ruby GDB modules
import command
import constants
import context
import format
import value as rvalue
import rstring
import rexception
import rsymbol


def print_fiber_backtrace(fiber_ptr, from_tty=True):
	"""Print backtrace for a Ruby fiber.
	
	Args:
		fiber_ptr: Fiber struct pointer (rb_fiber_struct *)
		from_tty: Whether output is to terminal (for formatting)
	"""
	printer = RubyStackPrinter()
	printer.print_fiber_backtrace(fiber_ptr, from_tty)


def print_ec_backtrace(ec, from_tty=True):
	"""Print backtrace for an execution context.
	
	Args:
		ec: Execution context pointer (rb_execution_context_t *)
		from_tty: Whether output is to terminal (for formatting)
	"""
	printer = RubyStackPrinter()
	printer.print_backtrace(ec, from_tty)


class RubyStackPrinter:
	"""Helper class for printing Ruby stack traces.
	
	This class provides the core logic for printing backtraces that can be
	used both by commands and programmatically from other modules.
	"""
	
	def __init__(self):
		# Cached type lookups
		self._rbasic_type = None
		self._value_type = None
		self._cfp_type = None
		self._rstring_type = None
		self.show_values = False
		self.terminal = None
		
	def _initialize_types(self):
		"""Initialize cached type lookups."""
		if self._rbasic_type is None:
			self._rbasic_type = constants.type_struct('struct RBasic').pointer()
		if self._value_type is None:
			self._value_type = constants.type_struct('VALUE')
		if self._cfp_type is None:
			self._cfp_type = constants.type_struct('rb_control_frame_t').pointer()
		if self._rstring_type is None:
			self._rstring_type = constants.type_struct('struct RString').pointer()
	
	def print_fiber_backtrace(self, fiber_ptr, from_tty=True):
		"""Print backtrace for a Ruby fiber.
		
		Args:
			fiber_ptr: Fiber struct pointer (rb_fiber_struct *)
			from_tty: Whether output is to terminal (for formatting)
		"""
		try:
			self._initialize_types()
			self.terminal = format.create_terminal(from_tty)
			
			# Get execution context from fiber
			ec = fiber_ptr['cont']['saved_ec'].address
			
			print(f"Backtrace for fiber {fiber_ptr}:")
			self.print_backtrace(ec, from_tty)
			
		except (debugger.Error, RuntimeError) as e:
			print(f"Error printing fiber backtrace: {e}")
	
	def print_backtrace(self, ec, from_tty=True):
		"""Print backtrace for an execution context.
		
		Args:
			ec: Execution context pointer (rb_execution_context_t *)
			from_tty: Whether output is to terminal (for formatting)
		"""
		try:
			self._initialize_types()
			if self.terminal is None:
				self.terminal = format.create_terminal(from_tty)
			
			cfp = ec['cfp']
			vm_stack = ec['vm_stack']
			vm_stack_size = int(ec['vm_stack_size'])
			
			# Check for exception
			errinfo_val = ec['errinfo']
			errinfo_int = int(errinfo_val)
			
			# Check if it's a real exception object (not nil or other immediate/special value)
			if not rvalue.is_immediate(errinfo_val) and not rvalue.is_nil(errinfo_val):
				try:
					exc_class = self._get_exception_class(errinfo_val)
					exc_msg = self._get_exception_message(errinfo_val)
					
					# Set as GDB convenience variable for manual inspection
					debugger.set_convenience_variable('errinfo', errinfo_val)
					
					if exc_msg:
						print(f"Currently handling: {exc_class}: {exc_msg} (VALUE: 0x{errinfo_int:x}, $errinfo)")
					else:
						print(f"Currently handling: {exc_class} (VALUE: 0x{errinfo_int:x}, $errinfo)")
					print()
				except:
					# Set convenience variable even if we can't decode
					debugger.set_convenience_variable('errinfo', errinfo_val)
					print(f"Currently handling exception (VALUE: 0x{errinfo_int:x}, $errinfo)")
					print()
			
			# Calculate end of control frames
			cfpend = (vm_stack + vm_stack_size).cast(self._cfp_type) - 1
			
			frame_num = 0
			current_cfp = cfp
			
			while current_cfp < cfpend:
				try:
					self._print_frame(current_cfp, frame_num)
					frame_num += 1
					current_cfp += 1
				except (debugger.Error, RuntimeError) as e:
					print(f"  #{frame_num}: [error reading frame: {e}]")
					break
			
			if frame_num == 0:
				print("  (no frames)")
				
		except (debugger.Error, RuntimeError) as e:
			print(f"Error printing backtrace: {e}")
	
	def _print_frame(self, cfp, depth):
		"""Print a single control frame.
		
		Args:
			cfp: Control frame pointer (rb_control_frame_t *)
			depth: Frame depth/number
		"""
		iseq = cfp['iseq']
		
		if iseq is None or int(iseq) == 0:
			# C function frame - try to extract method info from EP
			try:
				ep = cfp['ep']
				
				# Check if this is a valid C frame
				if int(ep) != 0:
					ep0 = int(ep[0])
					if (ep0 & 0xffff0001) == 0x55550001:
						# Valid C frame, try to extract method entry
						env_me_cref = ep[-2]
						
						try:
							me_type = constants.type_struct('rb_callable_method_entry_t').pointer()
							me = env_me_cref.cast(me_type)
							
							# Get the C function pointer
							cfunc = me['def']['body']['cfunc']['func']
							
							# Get the method ID
							method_id = me['def']['original_id']
							
							# Try to get symbol for the C function
							func_addr = int(cfunc)
							func_name = debugger.lookup_symbol(func_addr)
							if func_name:
								func_name = f" ({func_name})"
							else:
								func_name = f" (0x{func_addr:x})"
							
							# Print C frame with cyan/dimmed formatting
							self.terminal.print(
								format.metadata, f"  #{depth}: ",
								format.dim, "[C function", func_name, "]",
								format.reset
							)
							return
						except:
							pass
			except:
				pass
			
			# Fallback if we couldn't extract info
			self.terminal.print(
				format.metadata, f"  #{depth}: ",
				format.dim, "[C function or native frame]",
				format.reset
			)
			return
		
		pc = cfp['pc']
		
		if int(pc) == 0:
			self.terminal.print(
				format.metadata, f"  #{depth}: ",
				format.error, "???:???:in '???'",
				format.reset
			)
			return
		
		# Check if it's an ifunc (internal function)
		RUBY_IMMEDIATE_MASK = 0x03
		RUBY_FL_USHIFT = 12
		RUBY_T_IMEMO = 0x1a
		RUBY_IMEMO_MASK = 0x0f
		
		iseq_val = int(iseq.cast(self._value_type))
		if not (iseq_val & RUBY_IMMEDIATE_MASK):
			try:
				flags = int(iseq['flags'])
				expected = ((RUBY_T_IMEMO << RUBY_FL_USHIFT) | RUBY_T_IMEMO)
				mask = ((RUBY_IMEMO_MASK << RUBY_FL_USHIFT) | 0x1f)
				
				if (flags & mask) == expected:
					# It's an ifunc
					self.terminal.print(
						format.metadata, f"  #{depth}: ",
						format.dim, "[ifunc]",
						format.reset
					)
					return
			except:
				pass
		
		try:
			# Get location information
			body = iseq['body']
			if body is None:
				self.terminal.print(
					format.metadata, f"  #{depth}: ",
					format.error, "???:???:in '???'",
					format.reset
				)
				return
				
			location = body['location']
			if location is None:
				self.terminal.print(
					format.metadata, f"  #{depth}: ",
					format.error, "???:???:in '???'",
					format.reset
				)
				return
				
			pathobj = location['pathobj']
			label = location['label']
			
			# Get path string - pathobj can be a string or an array [path, realpath]
			path = self._extract_path_from_pathobj(pathobj)
			label_str = self._value_to_string(label)
			
			# Calculate line number
			lineno = self._get_lineno(cfp)
			
			# Print Ruby frame with highlighting
			self.terminal.print(
				format.metadata, f"  #{depth}: ",
				format.string, path,
				format.reset, ":",
				format.metadata, str(lineno),
				format.reset, ":in '",
				format.method, label_str,
				format.reset, "'"
			)
			
			# If --values flag is set, print stack values
			if self.show_values:
				self._print_stack_values(cfp, iseq)
			
		except (debugger.Error, RuntimeError) as e:
			self.terminal.print(
				format.metadata, f"  #{depth}: ",
				format.error, f"[error reading frame info: {e}]",
				format.reset
			)
	
	def _print_stack_values(self, cfp, iseq):
		"""Print Ruby VALUEs on the control frame's stack pointer.
		
		Args:
			cfp: Control frame pointer (rb_control_frame_t *)
			iseq: Instruction sequence pointer
		"""
		try:
			sp = cfp['sp']
			ep = cfp['ep']
			
			if int(sp) == 0 or int(ep) == 0:
				return
			
			# Try to get local table information for better labeling
			local_names = []
			local_size = 0
			try:
				if int(iseq) != 0:
					iseq_body = iseq['body']
					local_table_size = int(iseq_body['local_table_size'])
					
					if local_table_size > 0:
						local_size = local_table_size
						local_table = iseq_body['local_table']
						
						# Read local variable names (they're stored as IDs/symbols)
						# Local table is stored in reverse order (last local first)
						for i in range(min(local_table_size, 20)):  # Cap at 20
							try:
								local_id = local_table[local_table_size - 1 - i]
								# Try to convert ID to symbol name using RubySymbol
								if int(local_id) != 0:
									sym = rsymbol.RubySymbol(local_id)
									name = sym.to_str()
									if name:
										local_names.append(name)
									else:
										local_names.append(f"local_{i}")
								else:
									local_names.append(f"local_{i}")
							except:
								local_names.append(f"local_{i}")
			except:
				pass
			
			# Environment pointer typically points to the local variable area
			# Stack grows downward, so we start from sp and go down
			value_ptr = sp - 1
			
			# Print a reasonable number of stack values
			max_values = 10
			values_printed = 0
			
			self.terminal.print(format.dim, "    Stack values:", format.reset)
			
			# Calculate offset from ep to show position
			while value_ptr >= ep and values_printed < max_values:
				try:
					val = value_ptr[0]
					val_int = int(val)
					
					# Calculate offset from ep for labeling
					offset = int(value_ptr - ep)
					
					# Try to determine if this is a local variable
					label = f"sp[-{values_printed + 1}]"
					if offset < local_size and offset < len(local_names):
						label = f"{local_names[offset]} (ep[{offset}])"
					
					# Try to get a brief representation of the value
					val_str = self._format_value_brief(val)
					
					self.terminal.print(
						format.metadata, f"      {label:20s} ",
						format.dim, f"= ",
						format.reset, val_str,
						format.reset
					)
					
					values_printed += 1
					value_ptr -= 1
				except (debugger.Error, debugger.MemoryError):
					break
			
			if values_printed == 0:
				self.terminal.print(format.dim, "      (empty stack)", format.reset)
				
		except (debugger.Error, RuntimeError) as e:
			# Silently skip if we can't read stack values
			pass
	
	def _format_value_brief(self, val):
		"""Get a brief string representation of a VALUE.
		
		Args:
			val: Ruby VALUE
			
		Returns:
			Brief string description
		"""
		try:
			# Use value.py's interpret function to get the typed object
			obj = rvalue.interpret(val)
			
			# Get string representation
			obj_str = str(obj)
			
			# Truncate if too long
			if len(obj_str) > 60:
				return obj_str[:57] + "..."
			
			return obj_str
			
		except Exception as e:
			return f"<error: {e}>"
	
	def _get_lineno(self, cfp):
		"""Get line number for a control frame.
		
		Args:
			cfp: Control frame pointer
			
		Returns:
			Line number as int or "???" if unavailable
		"""
		try:
			iseq = cfp['iseq']
			pc = cfp['pc']
			
			if int(pc) == 0:
				return "???"
			
			iseq_body = iseq['body']
			iseq_encoded = iseq_body['iseq_encoded']
			iseq_size = int(iseq_body['iseq_size'])
			
			pc_offset = int(pc - iseq_encoded)
			
			if pc_offset < 0 or pc_offset >= iseq_size:
				return "???"
			
			# Try to get line info
			insns_info = iseq_body['insns_info']
			positions = insns_info['positions']
			
			if int(positions) != 0:
				position = positions[pc_offset]
				lineno = int(position['lineno'])
				if lineno >= 0:
					return lineno
			
			# Fall back to first_lineno
			return int(iseq_body['location']['first_lineno'])
			
		except:
			return "???"
	
	def _get_exception_class(self, exc_value):
		"""Get the class name of an exception object.
		
		Delegates to rexception.RException for proper exception handling.
		
		Args:
			exc_value: Exception VALUE
			
		Returns:
			Class name as string
		"""
		try:
			exc = rexception.RException(exc_value)
			return exc.class_name
		except Exception:
			# Fallback if RException can't be created
			try:
				rbasic = exc_value.cast(self._rbasic_type)
				klass = rbasic['klass']
				return f"Exception(klass=0x{int(klass):x})"
			except:
				raise
	
	def _get_exception_message(self, exc_value):
		"""Get the message from an exception object.
		
		Delegates to rexception.RException for proper exception handling.
		
		Args:
			exc_value: Exception VALUE
			
		Returns:
			Message string or None if unavailable
		"""
		try:
			exc = rexception.RException(exc_value)
			return exc.message
		except Exception:
			# If RException can't be created, return None
			return None
	
	def _value_to_string(self, val):
		"""Convert a Ruby VALUE to a Python string.
		
		Args:
			val: Ruby VALUE
			
		Returns:
			String representation
		"""
		try:
			# Use the rvalue.interpret infrastructure for proper type handling
			obj = rvalue.interpret(val)
			
			# For strings, get the actual content
			if hasattr(obj, 'to_str'):
				return obj.to_str()
			
			# For immediates and other types, convert to string
			obj_str = str(obj)
			
			# Strip the type tag if present (e.g., "<T_FIXNUM> 42" -> "42")
			if obj_str.startswith('<'):
				# Find the end of the type tag
				end_tag = obj_str.find('>')
				if end_tag != -1 and end_tag + 2 < len(obj_str):
					# Return the part after the tag and space
					return obj_str[end_tag + 2:]
			
			return obj_str
			
		except Exception as e:
			return f"<error:{e}>"
	
	def _extract_path_from_pathobj(self, pathobj):
		"""Extract file path from pathobj (can be string or array).
		
		Args:
			pathobj: Ruby VALUE (either T_STRING or T_ARRAY)
			
		Returns:
			File path as string
		"""
		try:
			# Interpret the pathobj to get its type
			obj = rvalue.interpret(pathobj)
			
			# If it's an array, get the first element (the path)
			if hasattr(obj, 'length') and hasattr(obj, 'get_item'):
				if obj.length() > 0:
					path_value = obj.get_item(0)
					return self._value_to_string(path_value)
			
			# Otherwise, treat it as a string directly
			return self._value_to_string(pathobj)
			
		except Exception as e:
			return f"<error:{e}>"


class RubyStackTraceHandler:
	"""Print combined C and Ruby backtrace for current fiber or thread."""
	
	USAGE = command.Usage(
		summary="Print combined C and Ruby backtrace",
		parameters=[],
		options={},
		flags=[('values', 'Show stack VALUEs in addition to backtrace')],
		examples=[
			("rb-stack-trace", "Show backtrace for current fiber/thread"),
			("rb-stack-trace --values", "Show backtrace with stack VALUEs")
		]
	)
	
	def __init__(self):
		self.printer = RubyStackPrinter()
	
	def invoke(self, arguments, terminal):
		"""Execute the stack trace command."""
		try:
			# Get flags
			self.printer.show_values = arguments.has_flag('values')
			
			# Set terminal for formatting
			self.printer.terminal = terminal
			
			# Check if a fiber is currently selected
			# Import here to avoid circular dependency
			import fiber
			current_fiber = fiber.get_current_fiber()
			
			if current_fiber:
				# Use the selected fiber's execution context
				print(f"Stack trace for selected fiber:")
				print(f"  Fiber: ", end='')
				self.printer.terminal.print_type_tag('T_DATA', int(current_fiber.value), None)
				print()
				print()
				
				ec = current_fiber.pointer['cont']['saved_ec'].address
				self.printer.print_backtrace(ec, True)
			else:
				# Use current thread's execution context
				print("Stack trace for current thread:")
				print()
				
				try:
					ctx = context.RubyContext.current()
					
					if ctx is None:
						print("Error: No execution context available")
						print("Either select a fiber with 'rb-fiber-switch' or ensure Ruby is running")
						print("\nTroubleshooting:")
						print("  - Check if Ruby symbols are loaded")
						print("  - Ensure the process is stopped at a Ruby frame")
						return
					
					self.printer.print_backtrace(ctx.ec, True)
				except debugger.Error as e:
					print(f"Error getting execution context: {e}")
					print("Try selecting a fiber first with 'rb-fiber-switch'")
					return
					
		except Exception as e:
			print(f"Error: {e}")
			import traceback
			traceback.print_exc()


# Register commands
debugger.register("rb-stack-trace", RubyStackTraceHandler, usage=RubyStackTraceHandler.USAGE)

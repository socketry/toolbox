"""
LLDB backend implementation for unified debugger interface.

Note: This is a proof-of-concept implementation. Full LLDB support
would require more extensive testing and edge case handling.
"""

import lldb

# Command categories (LLDB doesn't have exact equivalents, using symbolic constants)
COMMAND_DATA = 0
COMMAND_USER = 1

# Exception types
Error = RuntimeError  # LLDB doesn't have a specific error type
MemoryError = RuntimeError  # Map to RuntimeError for now


class Value:
	"""Wrapper for LLDB values providing unified interface."""
	
	def __init__(self, lldb_value):
		"""Initialize with an LLDB value.
		
		Args:
			lldb_value: Native lldb.SBValue object
		"""
		self._value = lldb_value
	
	def __int__(self):
		"""Convert value to integer."""
		return self._value.GetValueAsUnsigned()
	
	def __str__(self):
		"""Convert value to string."""
		return self._value.GetValue() or str(self._value.GetValueAsUnsigned())
	
	def cast(self, type_obj):
		"""Cast this value to a different type.
		
		Args:
			type_obj: Type object to cast to
		
		Returns:
			New Value with cast type
		"""
		if isinstance(type_obj, Type):
			return Value(self._value.Cast(type_obj._type))
		else:
			# Assume it's a native LLDB type
			return Value(self._value.Cast(type_obj))
	
	def dereference(self):
		"""Dereference this pointer value.
		
		Returns:
			Value at the address
		"""
		return Value(self._value.Dereference())
	
	def address(self):
		"""Get the address of this value.
		
		Returns:
			Value representing the address
		"""
		return Value(self._value.AddressOf())
	
	def __getitem__(self, key):
		"""Access struct field or array element.
		
		Args:
			key: Field name (str) or array index (int)
		
		Returns:
			Value of the field/element
		"""
		if isinstance(key, str):
			return Value(self._value.GetChildMemberWithName(key))
		else:
			return Value(self._value.GetChildAtIndex(key))
	
	def __add__(self, offset):
		"""Pointer arithmetic: add offset.
		
		Args:
			offset: Integer offset to add
		
		Returns:
			New Value with adjusted pointer
		"""
		# LLDB requires more explicit pointer arithmetic
		# Get the type size and calculate new address
		type_size = self._value.GetType().GetPointeeType().GetByteSize()
		new_addr = self._value.GetValueAsUnsigned() + (offset * type_size)
		
		# Create a new value at the calculated address
		target = lldb.debugger.GetSelectedTarget()
		addr_value = target.CreateValueFromAddress(
			"temp", 
			lldb.SBAddress(new_addr, target),
			self._value.GetType()
		)
		return Value(addr_value)
	
	@property
	def type(self):
		"""Get the type of this value.
		
		Returns:
			Type object
		"""
		return Type(self._value.GetType())
	
	@property
	def native(self):
		"""Get the underlying native LLDB value.
		
		Returns:
			lldb.SBValue object
		"""
		return self._value


class Type:
	"""Wrapper for LLDB types providing unified interface."""
	
	def __init__(self, lldb_type):
		"""Initialize with an LLDB type.
		
		Args:
			lldb_type: Native lldb.SBType object
		"""
		self._type = lldb_type
	
	def __str__(self):
		"""Convert type to string."""
		return self._type.GetName()
	
	def pointer(self):
		"""Get pointer type to this type.
		
		Returns:
			Type representing pointer to this type
		"""
		return Type(self._type.GetPointerType())
	
	@property
	def native(self):
		"""Get the underlying native LLDB type.
		
		Returns:
			lldb.SBType object
		"""
		return self._type


# Global registry of LLDB command wrappers
_lldb_command_wrappers = {}

class Command:
	"""Base class for debugger commands.
	
	Subclass this and implement invoke() to create custom commands.
	"""
	
	# Registry of commands for LLDB
	_commands = {}
	
	def __init__(self, name, category=COMMAND_DATA):
		"""Initialize and register a command.
		
		Args:
			name: Command name (e.g., "rb-object-print")
			category: Command category (not used in LLDB)
		"""
		self.name = name
		self.category = category
		
		# Register in our command registry
		Command._commands[name] = self
		
		# Note: LLDB command registration happens in init.py after all commands are loaded
		# This is because LLDB needs the wrapper functions to be in a module's namespace,
		# and that's easier to manage from the init script
	
	def invoke(self, arg, from_tty):
		"""Handle command invocation.
		
		Override this method in subclasses.
		
		Args:
			arg: Command arguments as string
			from_tty: True if command invoked from terminal
		"""
		raise NotImplementedError("Subclasses must implement invoke()")
	
	@classmethod
	def get_command(cls, name):
		"""Get a registered command by name.
		
		Args:
			name: Command name
		
		Returns:
			Command instance or None
		"""
		return cls._commands.get(name)


def parse_and_eval(expression):
	"""Evaluate an expression in the debugger.
	
	Args:
		expression: Expression string (e.g., "$var", "ruby_current_vm_ptr", "42")
	
	Returns:
		Value object representing the result
	"""
	target = lldb.debugger.GetSelectedTarget()
	
	# If no target is selected, use the dummy target for constant evaluation
	if not target.IsValid():
		target = lldb.debugger.GetDummyTarget()
	
	# Try to evaluate with a frame context if available (for variables, memory access, etc.)
	process = target.GetProcess()
	if process.IsValid():
		thread = process.GetSelectedThread()
		if thread.IsValid():
			frame = thread.GetSelectedFrame()
			if frame.IsValid():
				# We have a full context - use frame evaluation
				result = frame.EvaluateExpression(expression)
				if result.IsValid():
					return Value(result)
	
	# Fallback to target-level evaluation (works for constants, globals, type casts)
	# This works even with core dumps or dummy targets
	result = target.EvaluateExpression(expression)
	
	if not result.IsValid():
		raise Error(f"Failed to evaluate expression: {expression}")
	
	# Check if the expression evaluation had an error (even if result is "valid")
	# LLDB returns valid=True with value=0 for undefined symbols
	error = result.GetError()
	if error.Fail():
		raise Error(f"Failed to evaluate expression '{expression}': {error.GetCString()}")
	
	return Value(result)


def lookup_type(type_name):
	"""Look up a type by name.
	
	Args:
		type_name: Type name (e.g., "struct RString", "VALUE")
	
	Returns:
		Type object
	"""
	target = lldb.debugger.GetSelectedTarget()
	
	# LLDB's FindFirstType searches the type system
	lldb_type = target.FindFirstType(type_name)
	
	if not lldb_type.IsValid():
		raise Error(f"Failed to find type: {type_name}")
	
	return Type(lldb_type)


def set_convenience_variable(name, value):
	"""Set an LLDB convenience variable.
	
	Args:
		name: Variable name (without $ prefix)
		value: Value to set (can be Value wrapper or native value)
	
	Note: LLDB doesn't have direct convenience variables like GDB.
	This implementation uses expression evaluation to set variables.
	"""
	if isinstance(value, Value):
		native_value = value._value
	else:
		native_value = value
	
	# LLDB approach: use expression to create a persistent variable
	# Variables in LLDB are prefixed with $
	target = lldb.debugger.GetSelectedTarget()
	frame = target.GetProcess().GetSelectedThread().GetSelectedFrame()
	
	# Create a persistent variable by evaluating an expression
	if hasattr(native_value, 'GetValue'):
		# It's an SBValue
		addr = native_value.GetValueAsUnsigned()
		type_name = native_value.GetType().GetName()
		frame.EvaluateExpression(f"({type_name})0x{addr:x}", lldb.SBExpressionOptions())
	# For now, simplified implementation
	# Full implementation would require more complex value handling


def execute(command, from_tty=False):
	"""Execute a debugger command.
	
	Args:
		command: Command string to execute
		from_tty: Whether command is from terminal (unused in LLDB)
	"""
	debugger = lldb.debugger
	interpreter = debugger.GetCommandInterpreter()
	
	result = lldb.SBCommandReturnObject()
	interpreter.HandleCommand(command, result)
	
	if not result.Succeeded():
		raise Error(f"Command failed: {result.GetError()}")


def invalidate_cached_frames():
	"""Invalidate cached frame information.
	
	Note: LLDB handles frame caching differently than GDB.
	This is a no-op for now.
	"""
	# LLDB typically invalidates frames automatically when the
	# process state changes. Manual invalidation is rarely needed.
	pass


def get_enum_value(enum_name, member_name):
	"""Get an enum member value.
	
	Args:
		enum_name: The enum type name (e.g., 'ruby_value_type')
		member_name: The member name (e.g., 'RUBY_T_STRING')
	
	Returns:
		Integer value of the enum member
	
	Raises:
		Error if enum member cannot be found
	
	Note: In LLDB, enum members must be accessed with the enum prefix:
	(int)enum_name::member_name
	"""
	enum_expr = f"(int){enum_name}::{member_name}"
	return int(parse_and_eval(enum_expr))


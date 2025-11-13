"""
GDB backend implementation for unified debugger interface.
"""

import gdb

# Command categories
COMMAND_DATA = gdb.COMMAND_DATA
COMMAND_USER = gdb.COMMAND_USER

# Exception types
Error = gdb.error
MemoryError = gdb.MemoryError


class Value:
	"""Wrapper for GDB values providing unified interface."""
	
	def __init__(self, gdb_value):
		"""Initialize with a GDB value.
		
		Args:
			gdb_value: Native gdb.Value object
		"""
		self._value = gdb_value
	
	def __int__(self):
		"""Convert value to integer."""
		return int(self._value)
	
	def __str__(self):
		"""Convert value to string."""
		return str(self._value)
	
	def cast(self, type_obj):
		"""Cast this value to a different type.
		
		Args:
			type_obj: Type object to cast to
		
		Returns:
			New Value with cast type
		"""
		if isinstance(type_obj, Type):
			return Value(self._value.cast(type_obj._type))
		else:
			# Assume it's a native GDB type
			return Value(self._value.cast(type_obj))
	
	def dereference(self):
		"""Dereference this pointer value.
		
		Returns:
			Value at the address
		"""
		return Value(self._value.dereference())
	
	@property
	def address(self):
		"""Get the address of this value.
		
		Returns:
			Value representing the address
		"""
		return Value(self._value.address)
	
	def __getitem__(self, key):
		"""Access struct field or array element.
		
		Args:
			key: Field name (str) or array index (int)
		
		Returns:
			Value of the field/element
		"""
		return Value(self._value[key])
	
	def __add__(self, offset):
		"""Pointer arithmetic: add offset.
		
		Args:
			offset: Integer offset to add
		
		Returns:
			New Value with adjusted pointer
		"""
		return Value(self._value + offset)
	
	@property
	def type(self):
		"""Get the type of this value.
		
		Returns:
			Type object
		"""
		return Type(self._value.type)
	
	@property
	def native(self):
		"""Get the underlying native GDB value.
		
		Returns:
			gdb.Value object
		"""
		return self._value


class Type:
	"""Wrapper for GDB types providing unified interface."""
	
	def __init__(self, gdb_type):
		"""Initialize with a GDB type.
		
		Args:
			gdb_type: Native gdb.Type object
		"""
		self._type = gdb_type
	
	def __str__(self):
		"""Convert type to string."""
		return str(self._type)
	
	def pointer(self):
		"""Get pointer type to this type.
		
		Returns:
			Type representing pointer to this type
		"""
		return Type(self._type.pointer())
	
	@property
	def native(self):
		"""Get the underlying native GDB type.
		
		Returns:
			gdb.Type object
		"""
		return self._type


class Command:
	"""Base class for debugger commands.
	
	Subclass this and implement invoke() to create custom commands.
	"""
	
	def __init__(self, name, category=COMMAND_DATA):
		"""Initialize and register a command.
		
		Args:
			name: Command name (e.g., "rb-object-print")
			category: Command category (COMMAND_DATA or COMMAND_USER)
		"""
		self.name = name
		self.category = category
		
		# Create a GDB command that delegates to our invoke method
		class GDBCommandWrapper(gdb.Command):
			def __init__(wrapper_self, wrapped):
				super(GDBCommandWrapper, wrapper_self).__init__(name, category)
				wrapper_self.wrapped = wrapped
			
			def invoke(wrapper_self, arg, from_tty):
				wrapper_self.wrapped.invoke(arg, from_tty)
		
		# Register the wrapper
		self._wrapper = GDBCommandWrapper(self)
	
	def invoke(self, arg, from_tty):
		"""Handle command invocation.
		
		Override this method in subclasses.
		
		Args:
			arg: Command arguments as string
			from_tty: True if command invoked from terminal
		"""
		raise NotImplementedError("Subclasses must implement invoke()")


def parse_and_eval(expression):
	"""Evaluate an expression in the debugger.
	
	Args:
		expression: Expression string (e.g., "$var", "ruby_current_vm_ptr")
	
	Returns:
		Value object representing the result
	"""
	return Value(gdb.parse_and_eval(expression))


def lookup_type(type_name):
	"""Look up a type by name.
	
	Args:
		type_name: Type name (e.g., "struct RString", "VALUE")
	
	Returns:
		Type object
	"""
	return Type(gdb.lookup_type(type_name))


def set_convenience_variable(name, value):
	"""Set a GDB convenience variable.
	
	Args:
		name: Variable name (without $ prefix)
		value: Value to set (can be Value wrapper or native value)
	"""
	if isinstance(value, Value):
		gdb.set_convenience_variable(name, value._value)
	else:
		gdb.set_convenience_variable(name, value)


def execute(command, from_tty=False):
	"""Execute a debugger command.
	
	Args:
		command: Command string to execute
		from_tty: Whether command is from terminal
	"""
	gdb.execute(command, from_tty=from_tty)


def invalidate_cached_frames():
	"""Invalidate cached frame information.
	
	Call this when switching contexts (e.g., fiber switching).
	"""
	gdb.invalidate_cached_frames()


def get_enum_value(enum_name, member_name):
	"""Get an enum member value.
	
	Args:
		enum_name: The enum type name (e.g., 'ruby_value_type')
		member_name: The member name (e.g., 'RUBY_T_STRING')
	
	Returns:
		Integer value of the enum member
	
	Raises:
		Error if enum member cannot be found
	
	Note: In GDB, enum members are imported into the global namespace,
	so we can just evaluate the member name directly.
	"""
	# GDB imports enum members globally, so just evaluate the name
	return int(gdb.parse_and_eval(member_name))


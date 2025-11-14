"""
GDB backend implementation for unified debugger interface.
"""

import gdb
import format

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
	
	def __eq__(self, other):
		"""Compare values for equality.
		
		Compares by address/integer value to avoid GDB conversion issues.
		
		Args:
			other: Another Value, gdb.Value, or integer
		
		Returns:
			True if values are equal
		"""
		if isinstance(other, Value):
			return int(self._value) == int(other._value)
		elif isinstance(other, gdb.Value):
			return int(self._value) == int(other)
		else:
			return int(self._value) == int(other)
	
	def __hash__(self):
		"""Return hash of value for use in sets/dicts.
		
		Returns:
			Hash of the integer value
		"""
		return hash(int(self._value))
	
	def __lt__(self, other):
		"""Less than comparison for pointer ordering.
		
		Args:
			other: Another Value, gdb.Value, or integer
		
		Returns:
			True if this value is less than other
		"""
		if isinstance(other, Value):
			return int(self._value) < int(other._value)
		elif isinstance(other, gdb.Value):
			return int(self._value) < int(other)
		else:
			return int(self._value) < int(other)
	
	def __le__(self, other):
		"""Less than or equal comparison for pointer ordering.
		
		Args:
			other: Another Value, gdb.Value, or integer
		
		Returns:
			True if this value is less than or equal to other
		"""
		if isinstance(other, Value):
			return int(self._value) <= int(other._value)
		elif isinstance(other, gdb.Value):
			return int(self._value) <= int(other)
		else:
			return int(self._value) <= int(other)
	
	def __gt__(self, other):
		"""Greater than comparison for pointer ordering.
		
		Args:
			other: Another Value, gdb.Value, or integer
		
		Returns:
			True if this value is greater than other
		"""
		if isinstance(other, Value):
			return int(self._value) > int(other._value)
		elif isinstance(other, gdb.Value):
			return int(self._value) > int(other)
		else:
			return int(self._value) > int(other)
	
	def __ge__(self, other):
		"""Greater than or equal comparison for pointer ordering.
		
		Args:
			other: Another Value, gdb.Value, or integer
		
		Returns:
			True if this value is greater than or equal to other
		"""
		if isinstance(other, Value):
			return int(self._value) >= int(other._value)
		elif isinstance(other, gdb.Value):
			return int(self._value) >= int(other)
		else:
			return int(self._value) >= int(other)
	
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
			Value of the field/element, or None if field doesn't exist or is invalid
		"""
		try:
			result = self._value[key]
			return Value(result)
		except (gdb.error, KeyError, AttributeError):
			return None
	
	def __add__(self, other):
		"""Add to this value (pointer arithmetic).
		
		Args:
			other: Value, gdb.Value, or integer to add
		
		Returns:
			Value result of addition
		"""
		if isinstance(other, Value):
			return Value(self._value + other._value)
		elif isinstance(other, gdb.Value):
			return Value(self._value + other)
		else:
			return Value(self._value + other)
	
	def __radd__(self, other):
		"""Reverse add - when Value is on the right side of +.
		
		Args:
			other: Value, gdb.Value, or integer to add
		
		Returns:
			Integer result of addition
		"""
		return self.__add__(other)
	
	def __sub__(self, other):
		"""Subtract from this value (pointer arithmetic).
		
		Args:
			other: Value, gdb.Value, or integer to subtract
		
		Returns:
			Value result of subtraction
		"""
		if isinstance(other, Value):
			return Value(self._value - other._value)
		elif isinstance(other, gdb.Value):
			return Value(self._value - other)
		else:
			return Value(self._value - other)
	
	def __rsub__(self, other):
		"""Reverse subtract - when Value is on the right side of -.
		
		Args:
			other: Value, gdb.Value, or integer to subtract from
		
		Returns:
			Integer result of subtraction
		"""
		if isinstance(other, Value):
			return int(other._value) - int(self._value)
		elif isinstance(other, gdb.Value):
			return int(other) - int(self._value)
		else:
			return int(other) - int(self._value)

	
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
	
	def array(self, count):
		"""Get array type of this type.
		
		Args:
			count: Number of elements in the array
		
		Returns:
			Type representing array of this type
		"""
		return Type(self._type.array(count))
	
	@property
	def native(self):
		"""Get the underlying native GDB type.
		
		Returns:
			gdb.Type object
		"""
		return self._type
	
	@property
	def sizeof(self):
		"""Get the size of this type in bytes.
		
		Returns:
			Size in bytes as integer
		"""
		return self._type.sizeof


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


def execute(command, from_tty=False, to_string=False):
	"""Execute a debugger command.
	
	Args:
		command: Command string to execute
		from_tty: Whether command is from terminal
		to_string: If True, return command output as string
	
	Returns:
		String output if to_string=True, None otherwise
	"""
	return gdb.execute(command, from_tty=from_tty, to_string=to_string)


def lookup_symbol(address):
	"""Look up symbol name for an address.
	
	Args:
		address: Memory address (as integer)
	
	Returns:
		Symbol name string, or None if no symbol found
	"""
	try:
		symbol_info = execute(f"info symbol 0x{address:x}", to_string=True)
		return symbol_info.split()[0]
	except:
		return None


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


def read_memory(address, size):
	"""Read memory from the debugged process.
	
	Args:
		address: Memory address (as integer or pointer value)
		size: Number of bytes to read
	
	Returns:
		bytes object containing the memory contents
	
	Raises:
		MemoryError: If memory cannot be read
	"""
	# Convert to integer address if needed
	if hasattr(address, '__int__'):
		address = int(address)
	
	try:
		inferior = gdb.selected_inferior()
		return inferior.read_memory(address, size).tobytes()
	except gdb.MemoryError as e:
		raise MemoryError(f"Cannot read {size} bytes at 0x{address:x}: {e}")


def read_cstring(address, max_length=256):
	"""Read a NUL-terminated C string from memory.
	
	Args:
		address: Memory address (as integer or pointer value)
		max_length: Maximum bytes to read before giving up
	
	Returns:
		Tuple of (bytes, actual_length) where actual_length is the string
		length not including the NUL terminator
	
	Raises:
		MemoryError: If memory cannot be read
	"""
	# Convert to integer address if needed
	if hasattr(address, '__int__'):
		address = int(address)
	
	try:
		inferior = gdb.selected_inferior()
		buffer = inferior.read_memory(address, max_length).tobytes()
		n = buffer.find(b'\x00')
		if n == -1:
			n = max_length
		return (buffer[:n], n)
	except gdb.MemoryError as e:
		raise MemoryError(f"Cannot read memory at 0x{address:x}: {e}")


def create_value(address, value_type):
	"""Create a typed Value from a memory address.
	
	Args:
		address: Memory address (as integer, pointer value, or gdb.Value)
		value_type: Type object (or native gdb.Type) to cast to
	
	Returns:
		Value object representing the typed value at that address
	
	Examples:
		>>> rbasic_type = debugger.lookup_type('struct RBasic').pointer()
		>>> obj = debugger.create_value(0x7fff12345678, rbasic_type)
	"""
	# Unwrap Type if needed
	if isinstance(value_type, Type):
		value_type = value_type._type
	
	# Handle different address types
	if isinstance(address, Value):
		# It's already a wrapped Value, get the native value
		address = address._value
	elif isinstance(address, gdb.Value):
		# It's a native gdb.Value, use it directly
		pass
	else:
		# Convert to integer address if needed
		if hasattr(address, '__int__'):
			address = int(address)
		# Create a gdb.Value from the integer
		address = gdb.Value(address)
	
	
	return Value(address.cast(value_type))


def create_value_from_int(int_value, value_type):
	"""Create a typed Value from an integer (not a memory address to read from).
	
	This is used when the integer itself IS the value (like VALUE which is a pointer).
	
	Args:
		int_value: Integer value, or Value object that will be converted to int
		value_type: Type object (or native gdb.Type) to cast to
	
	Returns:
		Value object with the integer value
	
	Examples:
		>>> value_type = debugger.lookup_type('VALUE')
		>>> obj_address = page['start']  # Value object
		>>> obj = debugger.create_value_from_int(obj_address, value_type)
	"""
	# Convert to integer if needed (handles Value objects via __int__)
	if hasattr(int_value, '__int__'):
		int_value = int(int_value)
	
	# Unwrap Type if needed
	if isinstance(value_type, Type):
		value_type = value_type._type
	
	# Create a gdb.Value from the integer
	int_val = gdb.Value(int_value)
	return Value(int_val.cast(value_type))


def create_value_from_address(address, value_type):
	"""Create a typed Value from a memory address.
	
	In GDB, this is equivalent to casting the address to a pointer type
	and dereferencing it.
	
	Args:
		address: Memory address (as integer, or Value object representing a pointer)
		value_type: Type object (or native gdb.Type) representing the type
	
	Returns:
		Value object representing the data at that address
	
	Examples:
		>>> rbasic_type = debugger.lookup_type('struct RBasic')
		>>> array_type = rbasic_type.array(100)
		>>> page_start = page['start']  # Value object
		>>> page_array = debugger.create_value_from_address(page_start, array_type)
	"""
	# Convert to integer if needed (handles Value objects via __int__)
	if hasattr(address, '__int__'):
		address = int(address)
	
	# Unwrap Type if needed
	if isinstance(value_type, Type):
		value_type = value_type._type
	
	# Create a pointer to the type and dereference it
	# This is GDB's way of saying "interpret this address as this type"
	ptr_type = value_type.pointer()
	addr_val = gdb.Value(address).cast(ptr_type)
	return Value(addr_val.dereference())


def register(name, handler_class, usage=None, category=COMMAND_USER):
	"""Register a command with GDB using a handler class.
	
	This creates a wrapper Command that handles parsing, terminal setup,
	and delegates to the handler class for actual command logic.
	
	Args:
		name: Command name (e.g., "rb-object-print")
		handler_class: Class to instantiate for handling the command
		usage: Optional command.Usage specification for validation/help
		category: Command category (COMMAND_USER, etc.)
	
	Example:
		class PrintHandler:
			def invoke(self, arguments, terminal):
				depth = arguments.get_option('depth', 1)
				print(f"Depth: {depth}")
		
		usage = command.Usage(
			summary="Print something",
			options={'depth': (int, 1)},
			flags=['debug']
		)
		debugger.register("my-print", PrintHandler, usage=usage)
	
	Returns:
		The registered Command instance
	"""
	class RegisteredCommand(Command):
		def __init__(self):
			super(RegisteredCommand, self).__init__(name, category)
			self.usage_spec = usage
			self.handler_class = handler_class
		
		def invoke(self, arg, from_tty):
			"""GDB entry point - parses arguments and delegates to handler."""
			# Create terminal first (needed for help text)
			import format
			terminal = format.create_terminal(from_tty)
			
			try:
				# Parse and validate arguments
				if self.usage_spec:
					arguments = self.usage_spec.parse(arg if arg else "")
				else:
					# Fallback to basic parsing without validation
					import command
					arguments = command.parse_arguments(arg if arg else "")
				
				# Instantiate handler and invoke
				handler = self.handler_class()
				handler.invoke(arguments, terminal)
				
			except ValueError as e:
				# Validation error - show colored help
				print(f"Error: {e}")
				if self.usage_spec:
					print()
					self.usage_spec.print_to(terminal, name)
			except Exception as e:
				print(f"Error: {e}")
				import traceback
				traceback.print_exc()
	
	# Instantiate and register the command with GDB
	return RegisteredCommand()







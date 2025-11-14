"""
LLDB backend implementation for unified debugger interface.

Note: This is a proof-of-concept implementation. Full LLDB support
would require more extensive testing and edge case handling.
"""

import lldb
import format

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
	
	def __eq__(self, other):
		"""Compare values for equality.
		
		Compares by address/integer value to avoid debugger conversion issues.
		
		Args:
			other: Another Value, lldb.SBValue, or integer
		
		Returns:
			True if values are equal
		"""
		if isinstance(other, Value):
			return self._value.GetValueAsUnsigned() == other._value.GetValueAsUnsigned()
		elif isinstance(other, lldb.SBValue):
			return self._value.GetValueAsUnsigned() == other.GetValueAsUnsigned()
		else:
			return self._value.GetValueAsUnsigned() == int(other)
	
	def __hash__(self):
		"""Return hash of value for use in sets/dicts.
		
		Returns:
			Hash of the integer value
		"""
		return hash(self._value.GetValueAsUnsigned())
	
	def __lt__(self, other):
		"""Less than comparison for pointer ordering.
		
		Args:
			other: Another Value, lldb.SBValue, or integer
		
		Returns:
			True if this value is less than other
		"""
		if isinstance(other, Value):
			return self._value.GetValueAsUnsigned() < other._value.GetValueAsUnsigned()
		elif isinstance(other, lldb.SBValue):
			return self._value.GetValueAsUnsigned() < other.GetValueAsUnsigned()
		else:
			return self._value.GetValueAsUnsigned() < int(other)
	
	def __le__(self, other):
		"""Less than or equal comparison for pointer ordering.
		
		Args:
			other: Another Value, lldb.SBValue, or integer
		
		Returns:
			True if this value is less than or equal to other
		"""
		if isinstance(other, Value):
			return self._value.GetValueAsUnsigned() <= other._value.GetValueAsUnsigned()
		elif isinstance(other, lldb.SBValue):
			return self._value.GetValueAsUnsigned() <= other.GetValueAsUnsigned()
		else:
			return self._value.GetValueAsUnsigned() <= int(other)
	
	def __gt__(self, other):
		"""Greater than comparison for pointer ordering.
		
		Args:
			other: Another Value, lldb.SBValue, or integer
		
		Returns:
			True if this value is greater than other
		"""
		if isinstance(other, Value):
			return self._value.GetValueAsUnsigned() > other._value.GetValueAsUnsigned()
		elif isinstance(other, lldb.SBValue):
			return self._value.GetValueAsUnsigned() > other.GetValueAsUnsigned()
		else:
			return self._value.GetValueAsUnsigned() > int(other)
	
	def __ge__(self, other):
		"""Greater than or equal comparison for pointer ordering.
		
		Args:
			other: Another Value, lldb.SBValue, or integer
		
		Returns:
			True if this value is greater than or equal to other
		"""
		if isinstance(other, Value):
			return self._value.GetValueAsUnsigned() >= other._value.GetValueAsUnsigned()
		elif isinstance(other, lldb.SBValue):
			return self._value.GetValueAsUnsigned() >= other.GetValueAsUnsigned()
		else:
			return self._value.GetValueAsUnsigned() >= int(other)
	
	def __add__(self, other):
		"""Add to this value.
		
		Args:
			other: Value, SBValue, or integer to add
		
		Returns:
			Integer result of addition
		"""
		if isinstance(other, Value):
			return self._value.GetValueAsUnsigned() + other._value.GetValueAsUnsigned()
		elif isinstance(other, lldb.SBValue):
			return self._value.GetValueAsUnsigned() + other.GetValueAsUnsigned()
		else:
			return self._value.GetValueAsUnsigned() + int(other)
	
	def __radd__(self, other):
		"""Reverse add - when Value is on the right side of +.
		
		Args:
			other: Value, SBValue, or integer to add
		
		Returns:
			Integer result of addition
		"""
		return self.__add__(other)
	
	def __sub__(self, other):
		"""Subtract from this value.
		
		Args:
			other: Value, SBValue, or integer to subtract
		
		Returns:
			Integer result of subtraction
		"""
		if isinstance(other, Value):
			return self._value.GetValueAsUnsigned() - other._value.GetValueAsUnsigned()
		elif isinstance(other, lldb.SBValue):
			return self._value.GetValueAsUnsigned() - other.GetValueAsUnsigned()
		else:
			return self._value.GetValueAsUnsigned() - int(other)
	
	def __rsub__(self, other):
		"""Reverse subtract - when Value is on the right side of -.
		
		Args:
			other: Value, SBValue, or integer to subtract from
		
		Returns:
			Integer result of subtraction
		"""
		if isinstance(other, Value):
			return other._value.GetValueAsUnsigned() - self._value.GetValueAsUnsigned()
		elif isinstance(other, lldb.SBValue):
			return other.GetValueAsUnsigned() - self._value.GetValueAsUnsigned()
		else:
			return int(other) - self._value.GetValueAsUnsigned()
	
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
	
	@property
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
			Value of the field/element, or None if field doesn't exist or is invalid
		"""
		if isinstance(key, str):
			result = self._value.GetChildMemberWithName(key)
			# Check if the result is valid
			if result.IsValid() and not result.GetError().Fail():
				return Value(result)
			else:
				return None
		else:
			# For integer index: check if this is a pointer type or array type
			# Both need pointer-style arithmetic (arrays for flexible array members)
			type_obj = self._value.GetType()
			if type_obj.IsPointerType() or type_obj.IsArrayType():
				# For arrays, treat the array address as a pointer to the element type
				if type_obj.IsArrayType():
					# Get the element type from the array
					element_type = type_obj.GetArrayElementType()
					# The address of the array IS the address of the first element
					base_addr = self._value.GetLoadAddress()
				else:
					# For pointers, get the pointee type and dereference
					element_type = type_obj.GetPointeeType()
					base_addr = self._value.GetValueAsUnsigned()
				
				type_size = element_type.GetByteSize()
				new_addr = base_addr + (key * type_size)
				
				# Optimization: if element type is a pointer, we can use CreateValueFromAddress
				# which is much faster than reading memory and creating SBData
				target = lldb.debugger.GetSelectedTarget()
				if element_type.IsPointerType():
					# Fast path for pointer arrays: use CreateValueFromAddress
					# CreateValueFromAddress needs an SBAddress
					sb_addr = lldb.SBAddress(new_addr, target)
					result = target.CreateValueFromAddress(
						f"element_{key}",
						sb_addr,
						element_type
					)
					return Value(result)
				else:
					# Slow path for struct/primitive arrays: read memory
					process = target.GetProcess()
					error = lldb.SBError()
					
					# Read the value from memory
					data = process.ReadMemory(new_addr, type_size, error)
					if error.Fail():
						raise MemoryError(f"Failed to read memory at 0x{new_addr:x}: {error.GetCString()}")
					
					# Create an SBData from the bytes
					sb_data = lldb.SBData()
					sb_data.SetData(error, data, target.GetByteOrder(), element_type.GetByteSize())
					
					# Create a value from the data
					result = target.CreateValueFromData(
						f"element_{key}",
						sb_data,
						element_type
					)
					return Value(result)
			else:
				# For structs, use GetChildAtIndex
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
		
		# Create a new pointer value using CreateValueFromExpression
		target = lldb.debugger.GetSelectedTarget()
		addr_value = target.CreateValueFromExpression(
			"temp", 
			f"({self._value.GetType().GetName()})0x{new_addr:x}"
		)
		return Value(addr_value)
	
	def __sub__(self, offset):
		"""Pointer arithmetic: subtract offset.
		
		Args:
			offset: Integer offset to subtract (or another Value for pointer difference)
		
		Returns:
			New Value with adjusted pointer, or integer difference if subtracting pointers
		"""
		if isinstance(offset, (Value, type(self._value))):
			# Subtracting two pointers - return the difference in elements
			other_value = offset if isinstance(offset, Value) else Value(offset)
			type_size = self._value.GetType().GetPointeeType().GetByteSize()
			addr_diff = self._value.GetValueAsUnsigned() - other_value._value.GetValueAsUnsigned()
			return addr_diff // type_size
		else:
			# Subtracting integer offset from pointer
			type_size = self._value.GetType().GetPointeeType().GetByteSize()
			new_addr = self._value.GetValueAsUnsigned() - (offset * type_size)
			
			# Create a new pointer value using CreateValueFromExpression
			target = lldb.debugger.GetSelectedTarget()
			addr_value = target.CreateValueFromExpression(
				"temp", 
				f"({self._value.GetType().GetName()})0x{new_addr:x}"
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
	
	def array(self, count):
		"""Get array type of this type.
		
		Args:
			count: Number of elements in the array (count - 1 for LLDB)
		
		Returns:
			Type representing array of this type
		"""
		return Type(self._type.GetArrayType(count + 1))
	
	@property
	def native(self):
		"""Get the underlying native LLDB type.
		
		Returns:
			lldb.SBType object
		"""
		return self._type
	
	@property
	def sizeof(self):
		"""Get the size of this type in bytes.
		
		Returns:
			Size in bytes as integer
		"""
		return self._type.GetByteSize()


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
	
	Raises:
		Error: If type cannot be found in debug symbols
	"""
	target = lldb.debugger.GetSelectedTarget()
	
	# LLDB's FindFirstType searches loaded debug symbols
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


def execute(command, from_tty=False, to_string=False):
	"""Execute a debugger command.
	
	Args:
		command: Command string to execute
		from_tty: Whether command is from terminal (unused in LLDB)
		to_string: If True, return command output as string
	
	Returns:
		String output if to_string=True, None otherwise
	"""
	debugger = lldb.debugger
	interpreter = debugger.GetCommandInterpreter()
	
	result = lldb.SBCommandReturnObject()
	interpreter.HandleCommand(command, result)
	
	if not result.Succeeded():
		raise Error(f"Command failed: {result.GetError()}")
	
	if to_string:
		return result.GetOutput()
	return None


def lookup_symbol(address):
	"""Look up symbol name for an address.
	
	Args:
		address: Memory address (as integer)
	
	Returns:
		Symbol name string, or None if no symbol found
	"""
	try:
		symbol_info = execute(f"image lookup -a 0x{address:x}", to_string=True)
		# LLDB output format: "Summary: module`symbol_name at file:line"
		# or "Symbol: ... name = "symbol_name""
		for line in symbol_info.split('\n'):
			if 'Summary:' in line:
				# Extract symbol from "Summary: ruby`rb_f_puts at io.c:8997:1"
				if '`' in line:
					start = line.index('`') + 1
					# Symbol ends at ' at ' or end of line
					if ' at ' in line[start:]:
						end = start + line[start:].index(' at ')
					else:
						end = len(line)
					return line[start:end].strip()
			elif 'Symbol:' in line and 'name = "' in line:
				# Alternative format
				start = line.index('name = "') + 8
				end = line.index('"', start)
				return line[start:end]
		return None
	except:
		return None


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
	
	process = lldb.debugger.GetSelectedTarget().GetProcess()
	error = lldb.SBError()
	data = process.ReadMemory(address, size, error)
	
	if not error.Success():
		raise MemoryError(f"Cannot read {size} bytes at 0x{address:x}: {error}")
	
	return bytes(data)


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
	
	process = lldb.debugger.GetSelectedTarget().GetProcess()
	error = lldb.SBError()
	data = process.ReadMemory(address, max_length, error)
	
	if not error.Success():
		raise MemoryError(f"Cannot read memory at 0x{address:x}: {error}")
	
	buffer = bytes(data)
	n = buffer.find(b'\x00')
	if n == -1:
		n = max_length
	return (buffer[:n], n)


def create_value(address, value_type):
	"""Create a typed Value from a memory address.
	
	Args:
		address: Memory address (as integer, pointer value, or lldb.SBValue)
		value_type: Type object (or native lldb.SBType) to cast to
	
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
		# It's already a wrapped Value, just cast it
		return Value(address._value.Cast(value_type))
	elif isinstance(address, lldb.SBValue):
		# It's a native lldb.SBValue, cast it directly
		return Value(address.Cast(value_type))
	else:
		# Convert to integer address if needed
		if hasattr(address, '__int__'):
			address = int(address)
		
		target = lldb.debugger.GetSelectedTarget()
		
		# For array types, use expression evaluation (CreateValueFromData doesn't work for large arrays)
		if value_type.IsArrayType():
			type_name = value_type.GetName()
			expr = f"*({type_name}*)0x{address:x}"
			addr_value = target.CreateValueFromExpression(
				f"array_0x{address:x}",
				expr
			)
			return Value(addr_value)
		
		# OPTIMIZATION: For simple types like VALUE (unsigned long), use CreateValueFromData
		# which avoids expression evaluation and is much faster for bulk operations
		process = target.GetProcess()
		
		# For scalar types (integers/pointers), we can read and create directly
		type_size = value_type.GetByteSize()
		error = lldb.SBError()
		data_bytes = process.ReadMemory(address, type_size, error)
		
		if error.Fail():
			# Fall back to expression-based approach if memory read fails
			type_name = value_type.GetName()
			expr = f"({type_name})0x{address:x}"
			addr_value = target.CreateValueFromExpression(
				f"addr_0x{address:x}",
				expr
			)
			return Value(addr_value)
		
		# Create SBData from the memory bytes
		sb_data = lldb.SBData()
		sb_data.SetData(error, data_bytes, target.GetByteOrder(), type_size)
		
		# Create value from the data (no expression evaluation!)
		# Note: This creates a value-by-value, but for VALUE (unsigned long) that's correct
		addr_value = target.CreateValueFromData(
			f"val_0x{address:x}",
			sb_data,
			value_type
		)
		
		# Store the original address as metadata so we can use it for debugging
		# The value itself contains the VALUE integer read from that address
		return Value(addr_value)


def create_value_from_address(address, value_type):
	"""Create a typed Value from a memory address.
	
	This uses CreateValueFromAddress to create a value of the given type at the
	specified address. This is more efficient than CreateValueFromExpression
	and supports array types directly.
	
	Args:
		address: Memory address (as integer, or Value object representing a pointer)
		value_type: Type object (or native lldb.SBType) representing the type
	
	Returns:
		Value object representing the data at that address
	
	Examples:
		>>> rbasic_type = debugger.lookup_type('struct RBasic')
		>>> array_type = rbasic_type.array(100)
		>>> page_start = page['start']  # Value object
		>>> page_array = debugger.create_value_from_address(page_start, array_type)
	"""
	# Convert to integer address if needed (handles Value objects via __int__)
	if hasattr(address, '__int__'):
		address = int(address)
	
	# Unwrap Type if needed
	if isinstance(value_type, Type):
		value_type = value_type._type
	
	target = lldb.debugger.GetSelectedTarget()
	
	# CreateValueFromAddress takes an SBAddress, not an integer
	# We need to create an SBAddress from the load address
	sb_addr = target.ResolveLoadAddress(address)
	if not sb_addr.IsValid():
		raise MemoryError(f"Invalid address: 0x{address:x}")
	
	# CreateValueFromAddress takes an address and creates a value of the given type
	# reading from that memory location
	addr_value = target.CreateValueFromAddress(
		f"val_at_0x{address:x}",
		sb_addr,
		value_type
	)
	
	if not addr_value.IsValid():
		raise MemoryError(f"Failed to create value from address 0x{address:x}")
	
	return Value(addr_value)


def create_value_from_int(int_value, value_type):
	"""Create a typed Value from an integer (not a memory address to read from).
	
	This is used when the integer itself IS the value (like VALUE which is a pointer).
	Unlike create_value(), this doesn't read from memory - it creates a value containing
	the integer itself.
	
	Args:
		int_value: Integer value, or Value object that will be converted to int
		value_type: Type object (or native lldb.SBType) to cast to
	
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
	
	# Create SBData with the integer value
	target = lldb.debugger.GetSelectedTarget()
	type_size = value_type.GetByteSize()
	
	# Convert integer to bytes (little-endian for x86_64)
	int_bytes = int_value.to_bytes(type_size, byteorder='little', signed=False)
	
	# Create SBData from bytes
	error = lldb.SBError()
	sb_data = lldb.SBData()
	sb_data.SetData(error, int_bytes, target.GetByteOrder(), type_size)
	
	# Create value from data
	result = target.CreateValueFromData(
		f"int_0x{int_value:x}",
		sb_data,
		value_type
	)
	
	return Value(result)


def register(name, handler_class, usage=None, category=COMMAND_USER):
	"""Register a command with LLDB using a handler class.
	
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
			"""LLDB entry point - parses arguments and delegates to handler."""
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
	
	# Instantiate and register the command with LLDB
	return RegisteredCommand()



import debugger
import constants
import format

def type_of(value):
	"""Get the Ruby type of a VALUE.
	
	Returns the RUBY_T_* constant value (e.g., RUBY_T_STRING, RUBY_T_ARRAY),
	or None if the type cannot be determined.
	"""
	basic = value.cast(constants.type_struct('struct RBasic').pointer())
	flags = int(basic.dereference()['flags'])
	RUBY_T_MASK = constants.type('RUBY_T_MASK')
	return flags & RUBY_T_MASK

def is_type(value, ruby_type_constant):
	"""Check if a VALUE is of a specific Ruby type.
	
	Arguments:
		value: The GDB value to check
		ruby_type_constant: String name of the constant (e.g., 'RUBY_T_STRING')
	
	Returns:
		True if the value is of the specified type, False otherwise
	"""
	type_flag = type_of(value)
	expected_type = constants.get(ruby_type_constant)
	return type_flag == expected_type

# Map of type constants to their names for display
TYPE_NAMES = {
	'RUBY_T_NONE': 'None',
	'RUBY_T_OBJECT': 'Object',
	'RUBY_T_CLASS': 'Class',
	'RUBY_T_MODULE': 'Module',
	'RUBY_T_FLOAT': 'Float',
	'RUBY_T_STRING': 'String',
	'RUBY_T_REGEXP': 'Regexp',
	'RUBY_T_ARRAY': 'Array',
	'RUBY_T_HASH': 'Hash',
	'RUBY_T_STRUCT': 'Struct',
	'RUBY_T_BIGNUM': 'Bignum',
	'RUBY_T_FILE': 'File',
	'RUBY_T_DATA': 'Data',
	'RUBY_T_MATCH': 'Match',
	'RUBY_T_COMPLEX': 'Complex',
	'RUBY_T_RATIONAL': 'Rational',
	'RUBY_T_NIL': 'Nil',
	'RUBY_T_TRUE': 'True',
	'RUBY_T_FALSE': 'False',
	'RUBY_T_SYMBOL': 'Symbol',
	'RUBY_T_FIXNUM': 'Fixnum',
	'RUBY_T_UNDEF': 'Undef',
	'RUBY_T_IMEMO': 'IMemo',
	'RUBY_T_NODE': 'Node',
	'RUBY_T_ICLASS': 'IClass',
	'RUBY_T_ZOMBIE': 'Zombie',
}

def type_name(value):
	"""Get the human-readable type name for a VALUE.
	
	Returns:
		String like 'String', 'Array', 'Hash', etc., or 'Unknown'
	"""
	type_flag = type_of(value)
	
	# Try to find matching type name
	for const_name, display_name in TYPE_NAMES.items():
		if constants.get(const_name) == type_flag:
			return display_name
	
	return f'Unknown(0x{type_flag:x})'

class RBasic:
	"""Generic Ruby object wrapper for unhandled types.
	
	This provides a fallback for types that don't have specialized handlers.
	"""
	def __init__(self, value):
		self.value = value
		self.basic = value.cast(constants.type_struct('struct RBasic').pointer())
		self.flags = int(self.basic.dereference()['flags'])
		self.type_flag = self.flags & constants.type('RUBY_T_MASK')
	
	def __str__(self):
		type_str = type_name(self.value)
		return f"<{type_str}:0x{int(self.value):x}>"
	
	def print_to(self, terminal):
		"""Print formatted basic object representation."""
		type_str = type_name(self.value)
		addr = int(self.value)
		# Note: Using : instead of @ for basic objects
		import format as fmt
		terminal.print(fmt.metadata, '<', fmt.reset, fmt.type, type_str, fmt.reset, end='')
		terminal.print(fmt.metadata, f':0x{addr:x}>', fmt.reset, end='')
	
	def print_recursive(self, printer, depth):
		"""Print this basic object (no recursion)."""
		printer.print(self)

import debugger

# Global shared cache for Ruby constants
_CACHE = {}

# Global shared cache for debugger type lookups
_TYPE_CACHE = {}

# Default values for Ruby type constants (ruby_value_type enum)
_TYPE_DEFAULTS = {
	'RUBY_T_NONE': 0x00,
	'RUBY_T_OBJECT': 0x01,
	'RUBY_T_CLASS': 0x02,
	'RUBY_T_MODULE': 0x03,
	'RUBY_T_FLOAT': 0x04,
	'RUBY_T_STRING': 0x05,
	'RUBY_T_REGEXP': 0x06,
	'RUBY_T_ARRAY': 0x07,
	'RUBY_T_HASH': 0x08,
	'RUBY_T_STRUCT': 0x09,
	'RUBY_T_BIGNUM': 0x0a,
	'RUBY_T_FILE': 0x0b,
	'RUBY_T_DATA': 0x0c,
	'RUBY_T_MATCH': 0x0d,
	'RUBY_T_COMPLEX': 0x0e,
	'RUBY_T_RATIONAL': 0x0f,
	'RUBY_T_NIL': 0x11,
	'RUBY_T_TRUE': 0x12,
	'RUBY_T_FALSE': 0x13,
	'RUBY_T_SYMBOL': 0x14,
	'RUBY_T_FIXNUM': 0x15,
	'RUBY_T_UNDEF': 0x16,
	'RUBY_T_IMEMO': 0x1a,
	'RUBY_T_NODE': 0x1b,
	'RUBY_T_ICLASS': 0x1c,
	'RUBY_T_ZOMBIE': 0x1d,
	'RUBY_T_MOVED': 0x1e,
	'RUBY_T_MASK': 0x1f,
}

# Default values for Ruby flag constants (ruby_fl_type enum)
_FLAG_DEFAULTS = {
	'RUBY_FL_USHIFT': 12,
	'RUBY_FL_USER1': 1 << 13,
	'RUBY_FL_USER2': 1 << 14,
	'RUBY_FL_USER3': 1 << 15,
	'RUBY_FL_USER4': 1 << 16,
	'RUBY_FL_USER5': 1 << 17,
	'RUBY_FL_USER6': 1 << 18,
	'RUBY_FL_USER7': 1 << 19,
	'RUBY_FL_USER8': 1 << 20,
	'RUBY_FL_USER9': 1 << 21,
}

def get(name, default=None):
	"""Get a Ruby constant value, with caching.
	
	Arguments:
		name: The constant name (e.g., 'RUBY_T_STRING', 'RUBY_FL_USER1')
		default: Default value if constant cannot be found
	
	Returns:
		The integer value of the constant, or default if not found
	
	Raises:
		Exception if constant not found and no default provided
	"""
	if name in _CACHE:
		return _CACHE[name]
	
	# Try direct evaluation (works in GDB with debug info, LLDB with macros/variables)
	try:
		val = int(debugger.parse_and_eval(name))
		# Only cache if we got a non-zero value or if it's a known zero constant
		if val != 0 or name in ['Qfalse', 'RUBY_Qfalse', 'RUBY_T_NONE']:
			_CACHE[name] = val
		return val
	except Exception:
		pass
	
	# Couldn't find the constant
	if default is None:
		raise Exception(f"Constant {name} not found and no default provided")
	
	# Return default but don't cache (might be available later with a process)
	return default

def get_enum(enum_name, member_name, default=None):
	"""Get an enum member value from a specific enum.
	
	This is more explicit than get() and works better in LLDB.
	
	Arguments:
		enum_name: The enum type name (e.g., 'ruby_value_type')
		member_name: The member name (e.g., 'RUBY_T_STRING')
		default: Default value if enum member cannot be found
	
	Returns:
		The integer value of the enum member, or default if not found
	
	Raises:
		Exception if member not found and no default provided
	
	Examples:
		>>> constants.get_enum('ruby_value_type', 'RUBY_T_STRING', 0x05)
		5
	"""
	cache_key = f"{enum_name}::{member_name}"
	
	if cache_key in _CACHE:
		return _CACHE[cache_key]
	
	# Use the debugger abstraction (handles GDB vs LLDB differences)
	try:
		val = debugger.get_enum_value(enum_name, member_name)
		_CACHE[cache_key] = val
		return val
	except Exception:
		pass
	
	# Couldn't find the enum member
	if default is None:
		raise Exception(f"Enum member {enum_name}::{member_name} not found and no default provided")
	
	return default

def type_struct(type_name):
	"""Get a C struct/type from the debugger, with caching.
	
	Arguments:
		type_name: The type name (e.g., 'struct RString', 'struct RArray', 'VALUE')
	
	Returns:
		The debugger type object
	
	Raises:
		Exception if type cannot be found
	
	Examples:
		>>> rbasic_type = constants.type_struct('struct RBasic')
		>>> value_type = constants.type_struct('VALUE')
	"""
	if type_name in _TYPE_CACHE:
		return _TYPE_CACHE[type_name]
	
	dbg_type = debugger.lookup_type(type_name)
	_TYPE_CACHE[type_name] = dbg_type
	return dbg_type

def type(name):
	"""Get a Ruby type constant (RUBY_T_*) value.
	
	This is a convenience wrapper around get_enum() for ruby_value_type enum.
	Uses built-in defaults for all standard Ruby type constants.
	
	Arguments:
		name: The type constant name (e.g., 'RUBY_T_STRING', 'RUBY_T_ARRAY')
	
	Returns:
		The integer value of the type constant
	
	Raises:
		Exception if constant is not found and not in default table
	
	Examples:
		>>> constants.type('RUBY_T_STRING')
		5
	"""
	default = _TYPE_DEFAULTS.get(name)
	return get_enum('ruby_value_type', name, default)

def flag(name):
	"""Get a Ruby flag constant (RUBY_FL_*) value.
	
	This is a convenience wrapper around get_enum() for ruby_fl_type enum.
	Uses built-in defaults for all standard Ruby flag constants.
	
	Arguments:
		name: The flag constant name (e.g., 'RUBY_FL_USER1', 'RUBY_FL_USHIFT')
	
	Returns:
		The integer value of the flag constant
	
	Raises:
		Exception if constant is not found and not in default table
	
	Examples:
		>>> constants.flag('RUBY_FL_USER1')
		8192
	"""
	default = _FLAG_DEFAULTS.get(name)
	return get_enum('ruby_fl_type', name, default)

def clear():
	"""Clear the constants and type caches.
	
	Useful when switching between different Ruby processes or versions.
	"""
	_CACHE.clear()
	_TYPE_CACHE.clear()

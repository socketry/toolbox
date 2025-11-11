import gdb

# Global shared cache for Ruby constants
_CACHE = {}

# Global shared cache for GDB type lookups
_TYPE_CACHE = {}

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
	try:
		val = int(gdb.parse_and_eval(name))
		_CACHE[name] = val
		return val
	except Exception:
		if default is None:
			raise
		_CACHE[name] = default
		return default

def get_type(type_name):
	"""Get a GDB type, with caching.
	
	Arguments:
		type_name: The type name (e.g., 'struct RString', 'struct RArray')
	
	Returns:
		The GDB type object
	
	Raises:
		Exception if type cannot be found
	"""
	if type_name in _TYPE_CACHE:
		return _TYPE_CACHE[type_name]
	
	gdb_type = gdb.lookup_type(type_name)
	_TYPE_CACHE[type_name] = gdb_type
	return gdb_type

def clear():
	"""Clear the constants and type caches.
	
	Useful when switching between different Ruby processes or versions.
	"""
	_CACHE.clear()
	_TYPE_CACHE.clear()

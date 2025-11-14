"""
Unified debugger abstraction layer for GDB and LLDB.

This module provides a common interface for debugger operations,
automatically loading the appropriate backend (GDB or LLDB) at runtime.
"""

import sys
import os

# Detect which debugger we're running under
_backend = None
DEBUGGER_NAME = None

# Add parent directory to path so we can import debugger.gdb / debugger.lldb
_toolbox_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _toolbox_dir not in sys.path:
	sys.path.insert(0, _toolbox_dir)

# Try importing the real GDB or LLDB modules first
# We need to verify they're the actual debugger modules, not namespace packages
_gdb_available = False
_lldb_available = False

try:
	import gdb as _gdb_module
	# Verify it's the real GDB module by checking for a key attribute
	if hasattr(_gdb_module, 'COMMAND_DATA'):
		_gdb_available = True
except ImportError:
	pass

try:
	import lldb as _lldb_module
	# Verify it's the real LLDB module by checking for a key class
	if hasattr(_lldb_module, 'SBDebugger'):
		_lldb_available = True
except ImportError:
	pass

# Now load the appropriate backend based on which module is available
if _gdb_available:
	from debugger import gdb_backend as _backend
	DEBUGGER_NAME = 'gdb'
elif _lldb_available:
	from debugger import lldb_backend as _backend
	DEBUGGER_NAME = 'lldb'
else:
	raise RuntimeError("Must be run under GDB or LLDB - neither module found")

if _backend is None:
	raise RuntimeError("Failed to load debugger backend")

# Export the backend's interface
Value = _backend.Value
Type = _backend.Type
Command = _backend.Command
Error = _backend.Error
MemoryError = _backend.MemoryError

parse_and_eval = _backend.parse_and_eval
lookup_type = _backend.lookup_type
set_convenience_variable = _backend.set_convenience_variable
execute = _backend.execute
lookup_symbol = _backend.lookup_symbol
invalidate_cached_frames = _backend.invalidate_cached_frames
get_enum_value = _backend.get_enum_value
read_memory = _backend.read_memory
read_cstring = _backend.read_cstring
create_value = _backend.create_value
create_value_from_int = _backend.create_value_from_int
create_value_from_address = _backend.create_value_from_address
register = _backend.register

# Constants
COMMAND_DATA = _backend.COMMAND_DATA
COMMAND_USER = _backend.COMMAND_USER

__all__ = [
	'DEBUGGER_NAME',
	'Value',
	'Type',
	'Command',
	'Error',
	'MemoryError',
	'parse_and_eval',
	'lookup_type',
	'set_convenience_variable',
	'execute',
	'lookup_symbol',
	'invalidate_cached_frames',
	'get_enum_value',
	'read_memory',
	'read_cstring',
	'create_value',
	'create_value_from_int',
	'create_value_from_address',
	'register',
	'COMMAND_DATA',
	'COMMAND_USER',
]

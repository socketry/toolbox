"""
Ruby Toolbox - Unified entry point for GDB and LLDB

This module auto-detects which debugger is running and loads
the appropriate Ruby debugging extensions.
"""

import os
import sys

# Get the directory containing this file (data/toolbox)
toolbox_dir = os.path.dirname(os.path.abspath(__file__))

# Add to Python path for imports
if toolbox_dir not in sys.path:
	sys.path.insert(0, toolbox_dir)

# Load debugger abstraction (auto-detects GDB or LLDB)
import debugger

# Load Ruby debugging extensions
loaded_extensions = []
failed_extensions = []

# Try to load each extension individually
extensions_to_load = [
	('print', 'rb-print'),
	('context', 'rb-context, rb-context-storage'),
	('fiber', 'rb-fiber-scan-heap, rb-fiber-switch'),
	('stack', 'rb-stack-trace'),
	('heap', 'rb-heap-scan'),
]

for module_name, commands in extensions_to_load:
	try:
		if module_name == 'print':
			import print as print_module
		elif module_name == 'context':
			import context
		elif module_name == 'fiber':
			import fiber
		elif module_name == 'stack':
			import stack
		elif module_name == 'heap':
			import heap
		loaded_extensions.append((module_name, commands))
	except Exception as e:
		# Catch all exceptions during module load
		failed_extensions.append((module_name, str(e)))
		import traceback
		print(f"Failed to load {module_name}: {e}", file=sys.stderr)
		traceback.print_exc(file=sys.stderr)

# Silently load - no status messages printed by default
# Users can run 'help' to see available commands

# For LLDB, register commands that were successfully loaded
if debugger.DEBUGGER_NAME == 'lldb':
	import lldb
	
	# Get all registered commands
	for cmd_name, cmd_obj in debugger.Command._commands.items():
		# Create a wrapper function in this module's namespace
		func_name = f"_cmd_{cmd_name.replace('-', '_')}"
		
		# Create closure that captures cmd_obj
		def make_wrapper(command_obj):
			def wrapper(debugger_obj, command, result, internal_dict):
				try:
					# Check if stdout is a TTY
					from_tty = sys.stdout.isatty()
					command_obj.invoke(command, from_tty=from_tty)
				except Exception as e:
					print(f"Error: {e}")
					import traceback
					traceback.print_exc()
			return wrapper
		
		# Add to this module's globals
		globals()[func_name] = make_wrapper(cmd_obj)
		
		# Register with LLDB
		# The module is imported as 'init' by LLDB
		result = lldb.SBCommandReturnObject()
		cmd_str = f"command script add -f init.{func_name} {cmd_name}"
		lldb.debugger.GetCommandInterpreter().HandleCommand(cmd_str, result)
		
		# Silently ignore registration failures


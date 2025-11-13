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

# Print initialization message
print(f"Ruby Toolbox loaded for {debugger.DEBUGGER_NAME.upper()}")
print(f"  Extensions: {toolbox_dir}")

# Load Ruby debugging extensions
loaded_extensions = []
failed_extensions = []

# Try to load each extension individually
extensions_to_load = [
	('object', 'rb-object-print'),
	('fiber', 'rb-fiber-scan-heap, rb-fiber-switch'),
	('stack', 'rb-stack-print'),
	('heap', 'rb-heap-scan'),
]

for module_name, commands in extensions_to_load:
	try:
		if module_name == 'object':
			import object
		elif module_name == 'fiber':
			import fiber
		elif module_name == 'stack':
			import stack
		elif module_name == 'heap':
			import heap
		loaded_extensions.append((module_name, commands))
	except ImportError as e:
		failed_extensions.append((module_name, str(e)))

# Print status
if loaded_extensions:
	print("✓ Ruby debugging commands loaded:")
	for module_name, commands in loaded_extensions:
		print(f"  {module_name}: {commands}")

if failed_extensions:
	print(f"\n⚠️  Some extensions failed to load (need migration to debugger abstraction):")
	for module_name, error in failed_extensions:
		# Simplify the error message
		if "No module named 'gdb'" in error:
			print(f"  {module_name}: needs migration from gdb to debugger")
		else:
			print(f"  {module_name}: {error}")

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
					command_obj.invoke(command, from_tty=True)
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
		
		if not result.Succeeded():
			print(f"  Warning: Could not register {cmd_name}: {result.GetError()}")


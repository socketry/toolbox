"""
Example: Unified debugger abstraction in action

This demonstrates how the same code works in both GDB and LLDB.
"""

import debugger

# Example 1: Simple value inspection
def inspect_ruby_value(expression):
	"""Inspect a Ruby VALUE, working in both GDB and LLDB."""
	print(f"Inspecting: {expression}")
	print(f"Debugger: {debugger.DEBUGGER_NAME}")
	print()
	
	try:
		# Parse the expression
		value = debugger.parse_and_eval(expression)
		print(f"Raw value: 0x{int(value):x}")
		
		# Check if it's immediate (encoded in the value itself)
		val_int = int(value)
		if val_int == 0 or (val_int & 0x03) != 0:
			print("Type: Immediate value (fixnum, symbol, special constant)")
			return
		
		# It's a heap object - examine its RBasic structure
		rbasic_type = debugger.lookup_type("struct RBasic").pointer()
		basic = value.cast(rbasic_type)
		
		# Read flags
		flags = int(basic.dereference()['flags'])
		type_flag = flags & 0x1f  # RUBY_T_MASK
		
		type_names = {
			0x05: "T_STRING",
			0x07: "T_ARRAY",
			0x08: "T_HASH",
			0x0a: "T_STRUCT",
			0x0c: "T_DATA",
			0x0e: "T_SYMBOL",
			0x11: "T_FLOAT",
			0x13: "T_BIGNUM",
		}
		
		type_name = type_names.get(type_flag, f"UNKNOWN(0x{type_flag:02x})")
		print(f"Type: {type_name}")
		print(f"Flags: 0x{flags:x}")
		
	except debugger.Error as e:
		print(f"Error: {e}")
	except debugger.MemoryError as e:
		print(f"Memory error: {e}")


# Example 2: Simple command
class RubyInspectCommand(debugger.Command):
	"""Inspect a Ruby value - works in both GDB and LLDB!
	
	Usage: rb-inspect <expression>
	Example: rb-inspect $var
	         rb-inspect ruby_current_vm_ptr
	"""
	
	def __init__(self):
		super(RubyInspectCommand, self).__init__(
			"rb-inspect-demo", 
			debugger.COMMAND_DATA
		)
	
	def invoke(self, arg, from_tty):
		if not arg:
			print("Usage: rb-inspect-demo <expression>")
			return
		
		inspect_ruby_value(arg.strip())


# Register the command
RubyInspectCommand()

print(f"Loaded debugger abstraction layer ({debugger.DEBUGGER_NAME})")
print("Try: rb-inspect-demo ruby_current_vm_ptr")


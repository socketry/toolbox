"""Print command for Ruby values."""

import debugger
import sys

# Import utilities
import command
import constants
import value as rvalue
import rstring
import rarray
import rhash
import rsymbol
import rstruct
import rfloat
import rbignum
import rbasic
import format


class RubyObjectPrinter:
	"""Print Ruby objects with recursive descent into nested structures."""
	
	USAGE = command.Usage(
		summary="Print Ruby objects with recursive inspection",
		parameters=[('value', 'VALUE or expression to print')],
		options={
			'depth': (int, 1, 'Maximum recursion depth for nested objects')
		},
		flags=[
			('debug', 'Show internal structure and debug information')
		],
		examples=[
			("rb-print $errinfo", "Print exception object"),
			("rb-print $ec->storage --depth 3", "Print fiber storage with depth 3"),
			("rb-print $ec->cfp->sp[-1] --debug", "Print top of stack with debug info")
		]
	)
	
	def invoke(self, arguments, terminal):
		"""Execute the print command.
		
		Args:
			arguments: Parsed Arguments object
			terminal: Terminal formatter (already configured for TTY/non-TTY)
		"""
		# Get options
		max_depth = arguments.get_option('depth', 1)
		debug_mode = arguments.has_flag('debug')
		
		# Validate depth
		if max_depth < 1:
			print("Error: --depth must be >= 1")
			return
		
		# Create printer
		printer = format.Printer(terminal, max_depth, debug_mode)
		
		# Process each expression
		for expression in arguments.expressions:
			try:
				# Evaluate the expression
				ruby_value = debugger.parse_and_eval(expression)
				
				# Interpret the value and let it print itself recursively
				ruby_object = rvalue.interpret(ruby_value)
				ruby_object.print_recursive(printer, max_depth)
			except debugger.Error as e:
				print(f"Error evaluating expression '{expression}': {e}")
			except Exception as e:
				print(f"Error processing '{expression}': {type(e).__name__}: {e}")
				if debug_mode:
					import traceback
					traceback.print_exc(file=sys.stderr)


# Register command using new interface
debugger.register("rb-print", RubyObjectPrinter, usage=RubyObjectPrinter.USAGE)


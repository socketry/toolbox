import debugger
import sys

# Import utilities
import command
import constants
import value
import rstring
import rarray
import rhash
import rsymbol
import rstruct
import rfloat
import rbignum
import rbasic
import format

class RubyObjectPrintCommand(debugger.Command):
	"""Recursively print Ruby hash and array structures.
	Usage: rb-object-print <expression> [max_depth] [--debug]
	Examples:
		rb-object-print $errinfo          # Print exception object
		rb-object-print $ec->storage      # Print fiber storage
		rb-object-print 0x7f7a12345678    # Print object at address
		rb-object-print $var 2            # Print with max depth 2

	Default max_depth is 1 if not specified.
	Add --debug flag to enable debug output."""
	
	def __init__(self):
		super(RubyObjectPrintCommand, self).__init__("rb-object-print", debugger.COMMAND_DATA)
	
	def usage(self):
		"""Print usage information."""
		print("Usage: rb-object-print <expression> [--depth N] [--debug]")
		print("Examples:")
		print("  rb-object-print $errinfo")
		print("  rb-object-print $ec->storage --depth 2")
		print("  rb-object-print foo + 10")
		print("  rb-object-print $ec->cfp->sp[-1] --depth 3 --debug")
	
	def invoke(self, argument, from_tty):
		# Parse arguments using the robust parser
		arguments = command.parse_arguments(argument if argument else "")
		
		# Validate that we have at least one expression
		if not arguments.expressions:
			self.usage()
			return
		
		# Apply flags
		debug_mode = arguments.has_flag('debug')
		
		# Apply options
		max_depth = arguments.get_option('depth', 1)
		
		# Validate depth
		if max_depth < 1:
			print("Error: --depth must be >= 1")
			return
		
		# Create terminal and printer
		terminal = format.create_terminal(from_tty)
		printer = format.Printer(terminal, max_depth, debug_mode)
		
		# Process each expression
		for expression in arguments.expressions:
			try:
				# Evaluate the expression
				ruby_value = debugger.parse_and_eval(expression)
				
				# Interpret the value and let it print itself recursively
				ruby_object = value.interpret(ruby_value)
				ruby_object.print_recursive(printer, max_depth)
			except debugger.Error as e:
				print(f"Error evaluating expression '{expression}': {e}")
			except Exception as e:
				print(f"Error processing '{expression}': {type(e).__name__}: {e}")
				if debug_mode:
					import traceback
					traceback.print_exc(file=sys.stderr)

# Register command
RubyObjectPrintCommand()

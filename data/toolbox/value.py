import sys
import constants
import format


import rbasic
import rfloat
import rsymbol
import rstring
import rarray
import rhash
import rstruct
import rbignum

class RImmediate:
	"""Wrapper for Ruby immediate values (fixnum, nil, true, false)."""
	
	def __init__(self, value):
		self.value = value
		self.val_int = int(value)
	
	def __str__(self):
		if self.val_int == 0:
			return "<T_FALSE>"
		elif self.val_int == 0x04 or self.val_int == 0x08:
			return "<T_NIL>"
		elif self.val_int == 0x14:
			return "<T_TRUE>"
		elif (self.val_int & 0x01) != 0:
			# Fixnum - shift right to get actual value
			return str(self.val_int >> 1)
		else:
			# Unknown immediate
			return f"<Immediate:0x{self.val_int:x}>"
	
	def print_to(self, terminal):
		"""Print this value with formatting to the given terminal."""
		if self.val_int == 0:
			terminal.print_type_tag('T_FALSE')
		elif self.val_int == 0x04 or self.val_int == 0x08:
			terminal.print_type_tag('T_NIL')
		elif self.val_int == 0x14:
			terminal.print_type_tag('T_TRUE')
		elif (self.val_int & 0x01) != 0:
			# Fixnum - shift right to get actual value
			terminal.print_type_tag('T_FIXNUM')
			terminal.print(' ', end='')
			terminal.print(format.number, str(self.val_int >> 1), format.reset, end='')
		else:
			# Unknown immediate
			terminal.print_type_tag('Immediate', self.val_int)
	
	def print_recursive(self, printer, depth):
		"""Print this immediate value (no recursion needed)."""
		printer.print(self)

def is_nil(value):
	"""Check if a Ruby VALUE is nil.
	
	Arguments:
		value: A GDB value representing a Ruby VALUE
	
	Returns:
		True if the value is nil (Qnil), False otherwise
	"""
	val_int = int(value)
	# Qnil can be 0x04 or 0x08 depending on Ruby version
	return val_int == 0x04 or val_int == 0x08

def is_immediate(value):
	"""Check if a Ruby VALUE is an immediate value.
	
	Immediate values include fixnum, symbols, nil, true, false.
	They are encoded directly in the VALUE, not as heap objects.
	
	Arguments:
		value: A GDB value representing a Ruby VALUE
	
	Returns:
		True if the value is immediate, False if it's a heap object
	"""
	val_int = int(value)
	# Check for special constants (Qfalse=0, Qnil=0x04/0x08, Qtrue=0x14)
	# or immediate values (fixnum, symbol, flonum) which have low bits set
	return val_int == 0 or (val_int & 0x03) != 0

def is_object(value):
	"""Check if a Ruby VALUE is a heap object (not immediate).
	
	Arguments:
		value: A GDB value representing a Ruby VALUE
	
	Returns:
		True if the value is a heap object, False if it's immediate
	"""
	return not is_immediate(value)

def is_exception(value):
	"""Check if a Ruby VALUE is an exception object.
	
	Arguments:
		value: A GDB value representing a Ruby VALUE
	
	Returns:
		True if the value appears to be an exception object, False otherwise
	"""
	if not is_object(value):
		return False
	
	try:
		# Check if it's a T_OBJECT or T_DATA (exceptions can be either)
		basic = value.cast(constants.type_struct("struct RBasic").pointer())
		flags = int(basic.dereference()['flags'])
		type_flag = flags & constants.type("RUBY_T_MASK")
		
		# Exceptions are typically T_OBJECT, but could also be T_DATA
		# We can't reliably determine if it's an exception without checking the class hierarchy
		# So we just check if it's an object type that could be an exception
		t_object = constants.type("RUBY_T_OBJECT")
		t_data = constants.type("RUBY_T_DATA")
		
		return type_flag == t_object or type_flag == t_data
	except Exception:
		return False

def interpret(value):
	"""Interpret a Ruby VALUE and return the appropriate typed object.
	
	This is a factory function that examines the value and returns the
	most specific type wrapper available (RString, RArray, RHash, etc.),
	or RBasic as a fallback for unhandled types.
	
	For immediate values (fixnum, flonum, symbol, nil, true, false), it returns
	the appropriate wrapper (RImmediate, RFloat, RSymbol).
	
	Arguments:
		value: A GDB value representing a Ruby VALUE
	
	Returns:
		An instance of the appropriate type class (never None)
	"""
	val_int = int(value)
	
	# Check for immediate flonum (must be before fixnum check)
	if rfloat.is_flonum(value):
		return rfloat.RFloat(value)
	
	# Check if it's a symbol (immediate or heap)
	if rsymbol.is_symbol(value):
		return rsymbol.RSymbol(value)
	
	# Handle special constants and fixnum (anything with low bits set)
	if val_int == 0 or val_int == 0x04 or val_int == 0x08 or val_int == 0x14 or (val_int & 0x01) != 0:
		return RImmediate(value)
	
	# It's a heap object, examine its type
	try:
		basic = value.cast(constants.type_struct("struct RBasic").pointer())
		flags = int(basic.dereference()['flags'])
		type_flag = flags & constants.type("RUBY_T_MASK")
		
		# Map type flags to their corresponding factory functions
		if type_flag == constants.type("RUBY_T_STRING"):
			return rstring.RString(value)
		elif type_flag == constants.type("RUBY_T_ARRAY"):
			return rarray.RArray(value)
		elif type_flag == constants.type("RUBY_T_HASH"):
			return rhash.RHash(value)
		elif type_flag == constants.type("RUBY_T_STRUCT"):
			return rstruct.RStruct(value)
		elif type_flag == constants.type("RUBY_T_SYMBOL"):
			return rsymbol.RSymbol(value)
		elif type_flag == constants.type("RUBY_T_FLOAT"):
			return rfloat.RFloat(value)
		elif type_flag == constants.type("RUBY_T_BIGNUM"):
			return rbignum.RBignum(value)
		else:
			# Unknown type - return generic RBasic
			return rbasic.RBasic(value)
	except Exception as e:
		# If we can't examine it, return a generic wrapper
		print(f"DEBUG interpret: exception {e}, returning RBasic", file=sys.stderr)
		return rbasic.RBasic(value)

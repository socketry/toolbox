import gdb
import constants
import rbasic
import struct
import format

class RFloatImmediate:
	"""Flonum - immediate float encoding (Ruby 3.4+)"""
	def __init__(self, value):
		self.value = int(value)
	
	def float_value(self):
		# Flonum decoding from Ruby's rb_float_flonum_value
		# Special case for 0.0
		if self.value == 0x8000000000000002:
			return 0.0
		
		v = self.value
		b63 = (v >> 63) & 1
		# e: xx1... -> 011...
		#    xx0... -> 100...
		#      ^b63
		adjusted = (2 - b63) | (v & ~0x03)
		# RUBY_BIT_ROTR(x, 3) rotates right by 3 bits
		# Which is: (x >> 3) | (x << (64 - 3))
		rotated = ((adjusted >> 3) | (adjusted << 61)) & 0xFFFFFFFFFFFFFFFF
		
		# Pack as unsigned long long, then unpack as double
		return struct.unpack('d', struct.pack('Q', rotated))[0]
	
	def __str__(self):
		return f"<T_FLOAT> {self.float_value()}"
	
	def print_to(self, terminal):
		"""Return formatted float representation."""
		tag = terminal.print(
			format.metadata, '<',
			format.type, 'T_FLOAT',
			format.metadata, '>',
			format.reset
		)
		num_val = terminal.print(format.number, str(self.float_value()), format.reset)
		return f"{tag} {num_val}"
	
	def print_recursive(self, printer, depth):
		"""Print this float (no recursion needed)."""
		printer.print(self)

class RFloatObject:
	"""Heap-allocated float object"""
	def __init__(self, value):
		self.value = value.cast(constants.get_type('struct RFloat'))
	
	def float_value(self):
		return float(self.value['float_value'])
	
	def __str__(self):
		addr = int(self.value.address)
		return f"<T_FLOAT@0x{addr:x}> {self.float_value()}"
	
	def print_to(self, terminal):
		"""Return formatted float representation."""
		addr = int(self.value.address)
		tag = terminal.print(
			format.metadata, '<',
			format.type, 'T_FLOAT',
			format.metadata, f'@0x{addr:x}>',
			format.reset
		)
		num_val = terminal.print(format.number, str(self.float_value()), format.reset)
		return f"{tag} {num_val}"
	
	def print_recursive(self, printer, depth):
		"""Print this float (no recursion needed)."""
		printer.print(self)

def is_flonum(value):
	"""Check if value is an immediate flonum"""
	val_int = int(value)
	# FLONUM_MASK = 0x03, FLONUM_FLAG = 0x02
	FLONUM_MASK = constants.get('RUBY_FLONUM_MASK', 0x03)
	FLONUM_FLAG = constants.get('RUBY_FLONUM_FLAG', 0x02)
	return (val_int & FLONUM_MASK) == FLONUM_FLAG

def RFloat(value):
	"""Factory function for float values - handles both flonums and heap objects"""
	# Check for immediate flonum first
	if is_flonum(value):
		return RFloatImmediate(value)
	
	# Check for heap-allocated T_FLOAT
	if rbasic.is_type(value, 'RUBY_T_FLOAT'):
		return RFloatObject(value)
	
	return None

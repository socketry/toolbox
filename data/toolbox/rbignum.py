import debugger
import constants
import rbasic
import format

class RBignumObject:
	def __init__(self, value):
		self.value = value
		self.rbignum = value.cast(constants.type_struct('struct RBignum').pointer())
		self.basic = value.cast(constants.type_struct('struct RBasic').pointer())
		self.flags = int(self.basic.dereference()['flags'])
	
	def is_embedded(self):
		# Check if FL_USER1 flag is set (RBIGNUM_EMBED_FLAG)
		FL_USER1 = 1 << (constants.flag('RUBY_FL_USHIFT') + 1)
		return bool(self.flags & FL_USER1)
	
	def __len__(self):
		if self.is_embedded():
			# Embedded length is stored in flags
			# Extract length from FL_USER2 onwards
			return (self.flags >> (constants.flag('RUBY_FL_USHIFT') + 2)) & 0x1F
		else:
			return int(self.rbignum.dereference()['as']['heap']['len'])
	
	def __str__(self):
		addr = int(self.value)
		if self.is_embedded():
			return f"<T_BIGNUM@0x{addr:x} embedded length={len(self)}>"
		else:
			return f"<T_BIGNUM@0x{addr:x} heap length={len(self)}>"
	
	def print_to(self, terminal):
		"""Print formatted bignum representation."""
		addr = int(self.value)
		storage = "embedded" if self.is_embedded() else "heap"
		details = f"{storage} length={len(self)}"
		terminal.print_type_tag('T_BIGNUM', addr, details)
	
	def print_recursive(self, printer, depth):
		"""Print this bignum (no recursion needed)."""
		printer.print(self)

def RBignum(value):
	if rbasic.is_type(value, 'RUBY_T_BIGNUM'):
		return RBignumObject(value)
	
	return None

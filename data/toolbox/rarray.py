import debugger
import rbasic
import constants
import format

class RArrayBase:
	"""Base class for RArray variants."""
	
	def __init__(self, value):
		"""value is a VALUE pointing to a T_ARRAY object."""
		self.value = value
		self.rarray = value.cast(constants.type_struct('struct RArray').pointer())
		self.basic = value.cast(constants.type_struct('struct RBasic').pointer())
		self.flags = int(self.basic.dereference()['flags'])
	
	def length(self):
		"""Get array length. Must be implemented by subclasses."""
		raise NotImplementedError
	
	def items_ptr(self):
		"""Get pointer to array items. Must be implemented by subclasses."""
		raise NotImplementedError
	
	def get_item(self, index):
		"""Get item at index."""
		if index < 0 or index >= self.length():
			raise IndexError(f"Index {index} out of range")
		items = self.items_ptr()
		return items[index]
	
	def __len__(self):
		"""Support len() function."""
		return self.length()
	
	def __getitem__(self, index):
		"""Support indexing."""
		return self.get_item(index)
	
	def print_recursive(self, printer, depth):
		"""Print this array recursively."""
		# Print the array header
		printer.print(self)
		
		# If depth is 0, don't recurse into elements
		if depth <= 0:
			if len(self) > 0:
				printer.print_with_indent(printer.max_depth - depth, "  ...")
			return
		
		# Print each element
		for i in range(len(self)):
			printer.print_item_label(printer.max_depth - depth, i)
			try:
				element = self[i]
				printer.print_value(element, depth - 1)
			except Exception as e:
				print(f"Error accessing element {i}: {e}")

class RArrayEmbedded(RArrayBase):
	"""Embedded array (small arrays stored directly in struct)."""
	
	def length(self):
		# Extract length from flags using Ruby's encoding
		# Length is stored in RUBY_FL_USER3|RUBY_FL_USER4 bits, shifted by RUBY_FL_USHIFT+3
		mask = constants.flag("RUBY_FL_USER3") | constants.flag("RUBY_FL_USER4")
		shift = constants.flag("RUBY_FL_USHIFT") + 3
		return (self.flags & mask) >> shift
	
	def items_ptr(self):
		return self.rarray.dereference()['as']['ary']
	
	def __str__(self):
		"""Return string representation of array."""
		addr = int(self.value)
		return f"<T_ARRAY@0x{addr:x} embedded length={len(self)}>"
	
	def print_to(self, terminal):
		"""Print this array with formatting."""
		addr = int(self.value)
		details = f"embedded length={len(self)}"
		terminal.print_type_tag('T_ARRAY', addr, details)

class RArrayHeap(RArrayBase):
	"""Heap array (larger arrays with separate memory allocation)."""
	
	def length(self):
		return int(self.rarray.dereference()['as']['heap']['len'])
	
	def items_ptr(self):
		return self.rarray.dereference()['as']['heap']['ptr']
	
	def __str__(self):
		"""Return string representation of array."""
		addr = int(self.value)
		return f"<T_ARRAY@0x{addr:x} heap length={len(self)}>"
	
	def print_to(self, terminal):
		"""Print this array with formatting."""
		addr = int(self.value)
		details = f"heap length={len(self)}"
		terminal.print_type_tag('T_ARRAY', addr, details)

def RArray(value):
	"""Factory function that returns the appropriate RArray variant.
	
	Caller should ensure value is a RUBY_T_ARRAY before calling this function.
	"""
	# Get flags to determine embedded vs heap
	basic = value.cast(constants.type_struct('struct RBasic').pointer())
	flags = int(basic.dereference()['flags'])
	
	# Check if array is embedded or heap-allocated using flags
	if (flags & constants.get("RARRAY_EMBED_FLAG")) != 0:
		return RArrayEmbedded(value)
	else:
		return RArrayHeap(value)

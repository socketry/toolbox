import debugger
import rbasic
import constants
import format


class RStructBase:
	"""Base class for Ruby struct variants."""
	
	def __init__(self, value):
		"""value is a VALUE pointing to a T_STRUCT object."""
		self.value = value
		self.rstruct = value.cast(constants.type_struct('struct RStruct').pointer())
	
	def length(self):
		"""Get the number of fields in the struct."""
		raise NotImplementedError("Subclass must implement length()")
	
	def items_ptr(self):
		"""Get pointer to the struct's data array."""
		raise NotImplementedError("Subclass must implement items_ptr()")
	
	def __len__(self):
		"""Support len(struct) syntax."""
		return self.length()
	
	def __getitem__(self, index):
		"""Support struct[i] syntax to access fields."""
		length = self.length()
		if index < 0 or index >= length:
			raise IndexError(f"struct index out of range: {index} (length: {length})")
		
		ptr = self.items_ptr()
		return ptr[index]


class RStructEmbedded(RStructBase):
	"""Ruby struct with embedded storage (small structs)."""
	
	def length(self):
		"""Get length from flags for embedded struct."""
		flags = int(self.rstruct.dereference()['basic']['flags'])
		
		# Extract length from FL_USER1 and FL_USER2 flags
		RUBY_FL_USER1 = constants.flag("RUBY_FL_USER1")
		RUBY_FL_USER2 = constants.flag("RUBY_FL_USER2")
		RUBY_FL_USHIFT = constants.flag("RUBY_FL_USHIFT")
		
		mask = RUBY_FL_USER1 | RUBY_FL_USER2
		shift = RUBY_FL_USHIFT + 1
		return (flags & mask) >> shift
	
	def items_ptr(self):
		"""Get pointer to embedded data array."""
		return self.rstruct.dereference()['as']['ary']
	
	def __str__(self):
		"""Return string representation of struct."""
		addr = int(self.value)
		return f"<T_STRUCT@0x{addr:x} embedded length={len(self)}>"
	
	def print_to(self, terminal):
		"""Print formatted struct representation."""
		addr = int(self.value)
		details = f"embedded length={len(self)}"
		terminal.print_type_tag('T_STRUCT', addr, details)
	
	def print_recursive(self, printer, depth):
		"""Print this struct recursively."""
		printer.print(self)
		
		if depth <= 0:
			if len(self) > 0:
				printer.print_with_indent(printer.max_depth - depth, "  ...")
			return
		
		# Print each field
		for i in range(len(self)):
			printer.print_item_label(printer.max_depth - depth, i)
			printer.print_value(self[i], depth - 1)


class RStructHeap(RStructBase):
	"""Ruby struct with heap-allocated storage (large structs)."""
	
	def length(self):
		"""Get length from heap structure."""
		return int(self.rstruct.dereference()['as']['heap']['len'])
	
	def items_ptr(self):
		"""Get pointer to heap-allocated data array."""
		return self.rstruct.dereference()['as']['heap']['ptr']
	
	def __str__(self):
		"""Return string representation of struct."""
		addr = int(self.value)
		return f"<T_STRUCT@0x{addr:x} heap length={len(self)}>"
	
	def print_to(self, terminal):
		"""Print formatted struct representation."""
		addr = int(self.value)
		details = f"heap length={len(self)}"
		terminal.print_type_tag('T_STRUCT', addr, details)
	
	def print_recursive(self, printer, depth):
		"""Print this struct recursively."""
		printer.print(self)
		
		if depth <= 0:
			if len(self) > 0:
				printer.print_with_indent(printer.max_depth - depth, "  ...")
			return
		
		# Print each field
		for i in range(len(self)):
			printer.print_item_label(printer.max_depth - depth, i)
			printer.print_value(self[i], depth - 1)


def RStruct(value):
	"""
	Factory function to create the appropriate RStruct variant.
	
	Caller should ensure value is a RUBY_T_STRUCT before calling this function.
	
	Returns:
		RStructEmbedded or RStructHeap instance
	"""
	# Cast to RStruct pointer to read flags
	rstruct_type = constants.type_struct("struct RStruct").pointer()
	rstruct = value.cast(rstruct_type)
	flags = int(rstruct.dereference()['basic']['flags'])
	
	# Feature detection: check for RSTRUCT_EMBED_LEN_MASK flag
	# If struct uses embedded storage, the length is encoded in flags
	RSTRUCT_EMBED_LEN_MASK = constants.get("RSTRUCT_EMBED_LEN_MASK")
	if RSTRUCT_EMBED_LEN_MASK is None:
		# Fallback: try to detect by checking if as.heap exists
		try:
			_ = rstruct.dereference()['as']['heap']
			return RStructHeap(value)
		except Exception:
			return RStructEmbedded(value)
	
	# Check if embedded flag is set
	if flags & RSTRUCT_EMBED_LEN_MASK:
		return RStructEmbedded(value)
	else:
		return RStructHeap(value)

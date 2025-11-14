import debugger
import rbasic
import constants
import format

class RHashBase:
	"""Base class for RHash variants."""
	
	def __init__(self, value):
		"""value is a VALUE pointing to a T_HASH object."""
		self.value = value
		self.rhash = value.cast(constants.type_struct('struct RHash').pointer())
		self.basic = value.cast(constants.type_struct('struct RBasic').pointer())
		self.flags = int(self.basic.dereference()['flags'])
	
	def size(self):
		"""Get hash size. Must be implemented by subclasses."""
		raise NotImplementedError
	
	def pairs(self):
		"""Iterate over (key, value) pairs. Must be implemented by subclasses."""
		raise NotImplementedError

class RHashSTTable(RHashBase):
	"""Hash using ST table structure (older or larger hashes)."""
	
	def __init__(self, value):
		super().__init__(value)
		# Calculate st_table pointer
		rhash_size = debugger.parse_and_eval("sizeof(struct RHash)")
		st_table_addr = int(value) + int(rhash_size)
		st_table_type = constants.type_struct("st_table")
		self.st_table = debugger.create_value_from_address(st_table_addr, st_table_type).address
	
	def size(self):
		return int(self.st_table.dereference()['num_entries'])
	
	def pairs(self):
		"""Yield (key, value) pairs."""
		num_entries = self.size()
		for i in range(num_entries):
			key = self.st_table.dereference()['entries'][i]['key']
			value = self.st_table.dereference()['entries'][i]['record']
			yield (key, value)
	
	def __str__(self):
		"""Return string representation of hash."""
		addr = int(self.value)
		return f"<T_HASH@0x{addr:x} ST-Table entries={self.size()}>"
	
	def print_to(self, terminal):
		"""Print this hash with formatting."""
		addr = int(self.value)
		details = f"ST-Table entries={self.size()}"
		terminal.print_type_tag('T_HASH', addr, details)
	
	def print_recursive(self, printer, depth):
		"""Print this hash recursively."""
		printer.print(self)
		
		if depth <= 0:
			if self.size() > 0:
				printer.print_with_indent(printer.max_depth - depth, "  ...")
			return
		
		# Print each key-value pair
		for i, (key, value) in enumerate(self.pairs()):
			printer.print_key_label(printer.max_depth - depth, i)
			printer.print_value(key, depth - 1)
			printer.print_value_label(printer.max_depth - depth)
			printer.print_value(value, depth - 1)

class RHashARTable(RHashBase):
	"""Hash using AR table structure (newer, smaller hashes)."""
	
	def __init__(self, value):
		super().__init__(value)
		# Feature detection: check if as.ar field exists (Ruby 3.2)
		# vs embedded after RHash (Ruby 3.3+)
		as_union = self.rhash.dereference()['as']
		if as_union is not None:
			# Ruby 3.2 layout: ar_table is accessed via as.ar pointer
			self.ar_table = as_union['ar']
		else:
			# Ruby 3.3+: ar_table is embedded directly after RHash structure
			rhash_size = debugger.parse_and_eval("sizeof(struct RHash)")
			ar_table_addr = int(self.rhash) + int(rhash_size)
			ar_table_type = constants.type_struct("struct ar_table_struct")
			self.ar_table = debugger.create_value_from_address(ar_table_addr, ar_table_type).address
		
		# Get array table size and bound from flags
		self.ar_size = ((self.flags & constants.get("RHASH_AR_TABLE_SIZE_MASK")) >> constants.get("RHASH_AR_TABLE_SIZE_SHIFT"))
		self.ar_bound = ((self.flags & constants.get("RHASH_AR_TABLE_BOUND_MASK")) >> constants.get("RHASH_AR_TABLE_BOUND_SHIFT"))
	
	def size(self):
		return self.ar_size
	
	def bound(self):
		"""Get the bound (capacity) of the AR table."""
		return self.ar_bound
	
	def pairs(self):
		"""Yield (key, value) pairs, skipping undefined/deleted entries."""
		RUBY_Qundef = constants.get("RUBY_Qundef")
		for i in range(int(self.ar_bound)):
			key = self.ar_table.dereference()['pairs'][i]['key']
			# Skip undefined/deleted entries
			if int(key) != RUBY_Qundef:
				value = self.ar_table.dereference()['pairs'][i]['val']
				yield (key, value)
	
	def __str__(self):
		"""Return string representation of hash."""
		addr = int(self.value)
		return f"<T_HASH@0x{addr:x} AR-Table size={self.size()} bound={self.bound()}>"
	
	def print_to(self, terminal):
		"""Print this hash with formatting."""
		addr = int(self.value)
		details = f"AR-Table size={self.size()} bound={self.bound()}"
		terminal.print_type_tag('T_HASH', addr, details)
	
	def print_recursive(self, printer, depth):
		"""Print this hash recursively."""
		printer.print(self)
		
		if depth <= 0:
			if self.size() > 0:
				printer.print_with_indent(printer.max_depth - depth, "  ...")
			return
		
		# Print each key-value pair
		for i, (key, value) in enumerate(self.pairs()):
			printer.print_key_label(printer.max_depth - depth, i)
			printer.print_value(key, depth - 1)
			printer.print_value_label(printer.max_depth - depth)
			printer.print_value(value, depth - 1)

def RHash(value):
	"""Factory function that returns the appropriate RHash variant.
	
	Caller should ensure value is a RUBY_T_HASH before calling this function.
	"""
	# Get flags to determine ST table vs AR table
	basic = value.cast(constants.type_struct('struct RBasic').pointer())
	flags = int(basic.dereference()['flags'])
	
	if (flags & constants.get("RHASH_ST_TABLE_FLAG")) != 0:
		return RHashSTTable(value)
	else:
		return RHashARTable(value)

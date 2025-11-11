import gdb
import rbasic
import constants
import format


class RubySymbol:
	"""Ruby symbol from ID (integer identifier)."""
	
	def __init__(self, symbol_id):
		"""Initialize from a symbol ID.
		
		Args:
			symbol_id: Integer symbol ID
		"""
		self.symbol_id = int(symbol_id)
		self._name = None
	
	def to_str(self):
		"""Get symbol name from global symbol table, or None if not found."""
		if self._name is not None:
			return self._name
		
		try:
			# rb_id_to_serial
			tLAST_OP_ID = constants.get("tLAST_OP_ID", 163)
			ID_ENTRY_UNIT = 512
			ID_ENTRY_SIZE = 2
			
			id_val = self.symbol_id
			
			if id_val > tLAST_OP_ID:
				try:
					RUBY_ID_SCOPE_SHIFT = int(constants.get("RUBY_ID_SCOPE_SHIFT"))
				except Exception:
					RUBY_ID_SCOPE_SHIFT = 3  # Default value
				serial = id_val >> RUBY_ID_SCOPE_SHIFT
			else:
				serial = id_val
			
			# Access ruby_global_symbols
			global_symbols = gdb.parse_and_eval("ruby_global_symbols")
			
			# Ruby 3.5+ changed from last_id to next_id
			try:
				last_id = int(global_symbols['last_id'])
			except (gdb.error, KeyError):
				# Ruby 3.5+ uses next_id instead
				last_id = int(global_symbols['next_id']) - 1
			
			if not serial or serial > last_id:
				return None
			
			idx = serial // ID_ENTRY_UNIT
			
			# Get ids array
			ids = global_symbols['ids'].cast(constants.get_type("struct RArray").pointer())
			
			# Import rarray to access the array
			import rarray
			arr = rarray.RArray(global_symbols['ids'])
			if arr is None:
				return None
			
			# Get the symbols entry
			entry_val = arr[idx]
			
			# Get the symbol from the entry
			entry_arr = rarray.RArray(entry_val)
			if entry_arr is None:
				return None
			
			ids_idx = (serial % ID_ENTRY_UNIT) * ID_ENTRY_SIZE
			sym_val = entry_arr[ids_idx]
			
			# Get the string from the symbol
			import rstring
			str_obj = rstring.RString(sym_val)
			if str_obj is None:
				return None
			
			self._name = str_obj.to_str()
			return self._name
			
		except Exception:
			return None
	
	def __str__(self):
		"""Return symbol representation."""
		name = self.to_str()
		if name:
			return f":{name}"
		else:
			return f":id_0x{self.symbol_id:x}"


class RSymbolImmediate:
	"""Ruby immediate symbol (encoded in VALUE)."""
	
	def __init__(self, value):
		self.value = value
		self._ruby_symbol = None
	
	def id(self):
		"""Get the symbol ID."""
		return get_id(self.value)
	
	def ruby_symbol(self):
		"""Get RubySymbol instance for this symbol."""
		if self._ruby_symbol is None:
			self._ruby_symbol = RubySymbol(self.id())
		return self._ruby_symbol
	
	def to_str(self):
		"""Get symbol name from global symbol table, or None if not found."""
		return self.ruby_symbol().to_str()
	
	def __str__(self):
		"""Return symbol representation."""
		name = self.to_str()
		if name:
			return f"<T_SYMBOL> :{name}"
		else:
			return f"<T_SYMBOL> :id_0x{self.id():x}"
	
	def print_to(self, terminal):
		"""Return formatted symbol representation."""
		name = self.to_str()
		if name:
			tag = terminal.print(
				format.metadata, '<',
				format.type, 'T_SYMBOL',
				format.metadata, '>',
				format.reset
			)
			symbol_val = terminal.print(format.symbol, f':{name}', format.reset)
			return f"{tag} {symbol_val}"
		else:
			tag = terminal.print(
				format.metadata, '<',
				format.type, 'T_SYMBOL',
				format.metadata, '>',
				format.reset
			)
			symbol_val = terminal.print(format.symbol, f':id_0x{self.id():x}', format.reset)
			return f"{tag} {symbol_val}"
	
	def print_recursive(self, printer, depth):
		"""Print this symbol (no recursion needed)."""
		printer.print(self)


class RSymbolObject:
	"""Ruby T_SYMBOL heap object."""
	
	def __init__(self, value):
		self.value = value
		self.rsymbol = value.cast(constants.get_type("struct RSymbol").pointer())
		self._ruby_symbol = None
	
	def id(self):
		"""Get the symbol ID."""
		return int(self.rsymbol.dereference()['id'])
	
	def ruby_symbol(self):
		"""Get RubySymbol instance for this symbol."""
		if self._ruby_symbol is None:
			self._ruby_symbol = RubySymbol(self.id())
		return self._ruby_symbol
	
	def fstr(self):
		"""Get the frozen string containing the symbol name."""
		return self.rsymbol.dereference()['fstr']
	
	def to_str(self):
		"""Get symbol name as a string."""
		try:
			import rstring
			fstr_val = self.fstr()
			str_obj = rstring.RString(fstr_val)
			if str_obj:
				return str_obj.to_str()
			return None
		except Exception:
			return None
	
	def __str__(self):
		"""Return symbol representation."""
		name = self.to_str()
		addr = int(self.value)
		if name:
			return f"<T_SYMBOL@0x{addr:x}> :{name}"
		else:
			fstr_val = self.fstr()
			return f"<T_SYMBOL@0x{addr:x}> :<Symbol:0x{int(fstr_val):x}>"
	
	def print_to(self, terminal):
		"""Return formatted symbol representation."""
		name = self.to_str()
		addr = int(self.value)
		if name:
			tag = terminal.print(
				format.metadata, '<',
				format.type, 'T_SYMBOL',
				format.metadata, f'@0x{addr:x}>',
				format.reset
			)
			symbol_val = terminal.print(format.symbol, f':{name}', format.reset)
			return f"{tag} {symbol_val}"
		else:
			fstr_val = self.fstr()
			tag = terminal.print(
				format.metadata, '<',
				format.type, 'T_SYMBOL',
				format.metadata, f'@0x{addr:x}>',
				format.reset
			)
			symbol_val = terminal.print(format.symbol, f':<Symbol:0x{int(fstr_val):x}>', format.reset)
			return f"{tag} {symbol_val}"
	
	def print_recursive(self, printer, depth):
		"""Print this symbol (no recursion needed)."""
		printer.print(self)



def is_symbol(value):
	"""
	Check if a VALUE is a symbol using the logic from Ruby's .gdbinit.
	
	From .gdbinit:
	  if (($arg0) & ~(~(VALUE)0<<RUBY_SPECIAL_SHIFT)) == RUBY_SYMBOL_FLAG
	
	This checks if the low bits (after masking RUBY_SPECIAL_SHIFT) match RUBY_SYMBOL_FLAG.
	"""
	try:
		val_int = int(value)
		
		# Get Ruby constants
		RUBY_SPECIAL_SHIFT = constants.get("RUBY_SPECIAL_SHIFT")
		RUBY_SYMBOL_FLAG = constants.get("RUBY_SYMBOL_FLAG")
		
		if RUBY_SPECIAL_SHIFT is None or RUBY_SYMBOL_FLAG is None:
			# Fallback to simple check
			return (val_int & 0xFF) == 0x0C
		
		# Create mask for low bits: ~(~0 << RUBY_SPECIAL_SHIFT)
		# This gives us RUBY_SPECIAL_SHIFT low bits set to 1
		mask = ~(~0 << RUBY_SPECIAL_SHIFT)
		
		# Check if masked value equals RUBY_SYMBOL_FLAG
		return (val_int & mask) == RUBY_SYMBOL_FLAG
	except Exception:
		# Fallback to simple check
		return (int(value) & 0xFF) == 0x0C


def get_id(value):
	"""
	Extract symbol ID from a VALUE using the logic from Ruby's .gdbinit.
	
	From .gdbinit:
	  set $id = (($arg0) >> RUBY_SPECIAL_SHIFT)
	"""
	try:
		RUBY_SPECIAL_SHIFT = constants.get("RUBY_SPECIAL_SHIFT")
		if RUBY_SPECIAL_SHIFT is None:
			# Fallback to shift by 8
			return int(value) >> 8
		return int(value) >> RUBY_SPECIAL_SHIFT
	except Exception:
		# Fallback to shift by 8
		return int(value) >> 8


def RSymbol(value):
	"""
	Factory function to create the appropriate RSymbol variant.
	
	Returns:
		RSymbolImmediate, RSymbolObject, or None
	"""
	# Check if it's an immediate symbol
	if is_symbol(value):
		return RSymbolImmediate(value)
	
	# Check if it's a T_SYMBOL object
	if rbasic.is_type(value, 'RUBY_T_SYMBOL'):
		return RSymbolObject(value)
	
	return None

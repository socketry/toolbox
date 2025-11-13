import debugger
import rbasic
import constants
import format

# Type code for arrays (same in GDB and LLDB)
_TYPE_CODE_ARRAY = 1

def _char_ptr_type():
	"""Return char* type for GDB."""
	return constants.type_struct('char').pointer()

class RStringBase:
	"""Base class for RString variants with common functionality."""
	
	def __init__(self, value):
		"""value is a VALUE pointing to a T_STRING object."""
		self.value = value
		self.rstring = value.cast(constants.type_struct('struct RString').pointer())
		self.basic = value.cast(constants.type_struct('struct RBasic').pointer())
		self.flags = int(self.basic.dereference()['flags'])
	
	def _is_embedded(self):
		"""Check if string is embedded. Must be implemented by subclasses."""
		raise NotImplementedError
	
	def length(self):
		"""Get string length. Must be implemented by subclasses."""
		raise NotImplementedError
	
	def data_ptr(self):
		"""Get pointer to string data. Must be implemented by subclasses."""
		raise NotImplementedError
	
	def read_bytes(self, max_fallback_scan=256):
		"""Return (bytes, length). If declared length is 0, will fallback to scanning for NUL up to max_fallback_scan."""
		pointer = self.data_ptr()
		length = self.length()
		
		# Memory reading is debugger-specific for now
		# TODO: Add memory reading to debugger abstraction
		if debugger.DEBUGGER_NAME == 'gdb':
			import gdb as _gdb
			inferior = _gdb.selected_inferior()
		else:  # lldb
			import lldb as _lldb
			# LLDB memory reading is different, using process.ReadMemory()
			process = _lldb.debugger.GetSelectedTarget().GetProcess()
			error = _lldb.SBError()
			if length and length > 0:
				data = process.ReadMemory(pointer, length, error)
				if not error.Success():
					return (b"", 0)
				return (bytes(data), length)
			# Fallback for LLDB
			data = process.ReadMemory(pointer, max_fallback_scan, error)
			if not error.Success():
				return (b"", 0)
			buffer = bytes(data)
			n = buffer.find(b'\x00')
			if n == -1:
				n = max_fallback_scan
			return (buffer[:n], n)
		
		if length and length > 0:
			return (inferior.read_memory(pointer, length).tobytes(), length)
		
		# Fallback: scan for NUL terminator when length is unavailable (e.g., symbol table strings)
		buffer = inferior.read_memory(pointer, max_fallback_scan).tobytes()
		n = buffer.find(b'\x00')
		if n == -1:
			n = max_fallback_scan
		return (buffer[:n], n)
	
	def to_str(self, encoding='utf-8'):
		"""Convert to Python string."""
		data, length = self.read_bytes()
		return data.decode(encoding, errors='replace')
	
	def __str__(self):
		"""Return the string with type tag and metadata."""
		addr = int(self.value)
		storage = "embedded" if self._is_embedded() else "heap"
		content = self.to_str()
		return f"<T_STRING@0x{addr:x} {storage} length={self.length()}> {repr(content)}"
	
	def print_to(self, terminal):
		"""Print this string with formatting."""
		addr = int(self.value)
		storage = "embedded" if self._is_embedded() else "heap"
		content = self.to_str()
		tag = terminal.print(
			format.metadata, '<',
			format.type, 'T_STRING',
			format.metadata, f'@0x{addr:x} {storage} length={self.length()}>',
			format.reset
		)
		# Use repr() to properly escape quotes, newlines, etc.
		string_val = terminal.print(format.string, repr(content), format.reset)
		return f"{tag} {string_val}"
	
	def print_recursive(self, printer, depth):
		"""Print this string (no recursion needed for strings)."""
		printer.print(self)

class RString34(RStringBase):
	"""Ruby 3.4+ strings: top-level len, as.embed.ary, FL_USER1 set = heap."""
	
	def _is_embedded(self):
		FL_USER1 = constants.flag('RUBY_FL_USER1')
		# FL_USER1 set => heap (not embedded)
		return (self.flags & FL_USER1) == 0
	
	def length(self):
		return int(self.rstring.dereference()['len'])
	
	def data_ptr(self):
		if not self._is_embedded():
			return self.rstring.dereference()['as']['heap']['ptr']
		# Embedded: use as.embed.ary
		ary = self.rstring.dereference()['as']['embed']['ary']
		try:
			if ary.type.code == _TYPE_CODE_ARRAY:
				return ary.address.cast(_char_ptr_type())
			return ary
		except Exception:
			return ary.address.cast(_char_ptr_type())

class RString33(RStringBase):
	"""Ruby 3.3 strings: top-level len, as.embed.len exists, FL_USER1 set = embedded."""
	
	def _is_embedded(self):
		FL_USER1 = constants.flag('RUBY_FL_USER1')
		# FL_USER1 set => embedded
		return (self.flags & FL_USER1) != 0
	
	def length(self):
		return int(self.rstring.dereference()['len'])
	
	def data_ptr(self):
		if not self._is_embedded():
			return self.rstring.dereference()['as']['heap']['ptr']
		# Embedded: use as.embed.ary
		ary = self.rstring.dereference()['as']['embed']['ary']
		try:
			if ary.type.code == _TYPE_CODE_ARRAY:
				return ary.address.cast(_char_ptr_type())
			return ary
		except Exception:
			return ary.address.cast(_char_ptr_type())

class RString32RVARGC(RStringBase):
	"""Ruby 3.2 with RVARGC: as.embed.len for embedded, as.embed.ary for data."""
	
	def _is_embedded(self):
		FL_USER1 = constants.flag('RUBY_FL_USER1')
		# FL_USER1 set => heap (not embedded)
		return (self.flags & FL_USER1) == 0
	
	def length(self):
		if self._is_embedded():
			return int(self.rstring.dereference()['as']['embed']['len'])
		else:
			return int(self.rstring.dereference()['as']['heap']['len'])
	
	def data_ptr(self):
		if not self._is_embedded():
			return self.rstring.dereference()['as']['heap']['ptr']
		# Embedded: use as.embed.ary
		ary = self.rstring.dereference()['as']['embed']['ary']
		try:
			if ary.type.code == _TYPE_CODE_ARRAY:
				return ary.address.cast(_char_ptr_type())
			return ary
		except Exception:
			return ary.address.cast(_char_ptr_type())

class RString32Legacy(RStringBase):
	"""Legacy Ruby 3.2: embedded length in FL_USER2..6, data in as.ary."""
	
	def _is_embedded(self):
		FL_USER1 = constants.flag('RUBY_FL_USER1')
		# FL_USER1 set => heap (not embedded)
		return (self.flags & FL_USER1) == 0
	
	def length(self):
		if self._is_embedded():
			FL2 = constants.flag('RUBY_FL_USER2')
			FL3 = constants.flag('RUBY_FL_USER3')
			FL4 = constants.flag('RUBY_FL_USER4')
			FL5 = constants.flag('RUBY_FL_USER5')
			FL6 = constants.flag('RUBY_FL_USER6')
			USHIFT = constants.flag('RUBY_FL_USHIFT')
			mask = FL2 | FL3 | FL4 | FL5 | FL6
			return (self.flags & mask) >> (USHIFT + 2)
		else:
			return int(self.rstring.dereference()['as']['heap']['len'])
	
	def data_ptr(self):
		if not self._is_embedded():
			return self.rstring.dereference()['as']['heap']['ptr']
		# Embedded: use as.ary (not as.embed.ary)
		ary = self.rstring.dereference()['as']['ary']
		try:
			if ary.type.code == _TYPE_CODE_ARRAY:
				return ary.address.cast(_char_ptr_type())
			return ary
		except Exception:
			return ary.address.cast(_char_ptr_type())

def RString(value):
	"""Factory function that detects the RString variant and returns the appropriate instance.
	
	Caller should ensure value is a RUBY_T_STRING before calling this function.
	
	Detects at runtime whether the process uses:
	- Ruby 3.4+: top-level len field, as.embed.ary (no embed.len), FL_USER1 set = heap
	- Ruby 3.3: top-level len field, as.embed.len exists, FL_USER1 set = embedded
	- Ruby 3.2 with RVARGC: as.embed.len for embedded, as.embed.ary for data
	- Legacy 3.2: embedded length in FL_USER2..6, data in as.ary
	"""
	rstring = value.cast(constants.type_struct('struct RString').pointer())
	
	# Try top-level len field (Ruby 3.3+/3.4+)
	try:
		_ = rstring.dereference()['len']
		# Now check if embed structure has len field (3.3) or just ary (3.4+)
		try:
			_ = rstring.dereference()['as']['embed']['len']
			return RString33(value)
		except Exception:
			return RString34(value)
	except Exception:
		pass
	
	# Try RVARGC embedded len field (3.2 RVARGC)
	try:
		_ = rstring.dereference()['as']['embed']['len']
		return RString32RVARGC(value)
	except Exception:
		pass
	
	# Fallback to legacy 3.2
	return RString32Legacy(value)

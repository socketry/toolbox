import debugger
import constants
import format
import value
import rstring
import rclass

class RException:
	"""Wrapper for Ruby exception objects."""
	
	def __init__(self, exception_value):
		"""Initialize with a Ruby exception VALUE.
		
		Args:
			exception_value: A GDB value representing a Ruby exception object
		"""
		self.value = exception_value
		self._basic = None
		self._klass = None
		self._class_name = None
		self._message = None
		
		# Validate it's an object
		if value.is_immediate(exception_value):
			raise ValueError("Exception VALUE cannot be an immediate value")
	
	@property
	def klass(self):
		"""Get the exception's class (klass pointer)."""
		if self._klass is None:
			if self._basic is None:
				self._basic = self.value.cast(constants.type_struct('struct RBasic').pointer())
			self._klass = self._basic['klass']
		return self._klass
	
	@property
	def class_name(self):
		"""Get the exception class name as a string."""
		if self._class_name is None:
			self._class_name = self._get_class_name()
		return self._class_name
	
	@property
	def message(self):
		"""Get the exception message as a string (None if unavailable)."""
		if self._message is None:
			self._message = self._get_message()
		return self._message
	
	def _get_class_name(self):
		"""Extract class name from klass pointer.
		
		Uses the rclass module to get the class name.
		"""
		try:
			return rclass.get_class_name(self.klass)
		except Exception:
			# Fallback if we can't read the class
			return f"Exception(klass=0x{int(self.klass):x})"
	
	def _get_message(self):
		"""Extract message from exception object.
		
		Walks instance variables to find 'mesg' ivar.
		Returns None if message is unavailable (common in core dumps).
		"""
		try:
			# Exception objects store message in 'mesg' instance variable
			# For now, return None as full ivar walking is complex
			# TODO: Implement full instance variable walking for core dumps
			return None
		except Exception:
			return None
	
	def __str__(self):
		"""Return formatted string 'ClassName: message' or just 'ClassName'."""
		class_name = self.class_name
		msg = self.message
		
		if msg:
			return f"{class_name}: {msg}"
		else:
			return class_name
	
	def print_to(self, terminal):
		"""Print this exception with formatting to the given terminal."""
		class_name = self.class_name
		msg = self.message
		
		# Print class name with type formatting
		class_output = terminal.print(
			format.type, class_name,
			format.reset
		)
		
		if msg:
			# Print message with string formatting
			msg_output = terminal.print(
				format.string, f': {msg}',
				format.reset
			)
			return f"{class_output}{msg_output}"
		else:
			return class_output
	
	def print_recursive(self, printer, depth):
		"""Print this exception (no recursion needed for exceptions)."""
		printer.print(self)

def is_exception(val):
	"""Check if a VALUE is an exception object.
	
	Args:
		val: A GDB value representing a Ruby VALUE
	
	Returns:
		True if the value appears to be an exception object, False otherwise
	"""
	if not value.is_object(val):
		return False
	
	try:
		# Check if it's a T_OBJECT or T_DATA (exceptions can be either)
		basic = val.cast(constants.type_struct("struct RBasic").pointer())
		flags = int(basic['flags'])
		type_flag = flags & constants.type("RUBY_T_MASK")
		
		# Exceptions are typically T_OBJECT, but could also be T_DATA
		t_object = constants.type("RUBY_T_OBJECT")
		t_data = constants.type("RUBY_T_DATA")
		
		return type_flag == t_object or type_flag == t_data
	except Exception:
		return False

def RExceptionFactory(val):
	"""Factory function to create RException or return None.
	
	Args:
		val: A GDB value representing a Ruby VALUE
	
	Returns:
		RException instance if val is an exception, None otherwise
	"""
	if is_exception(val):
		try:
			return RException(val)
		except Exception:
			return None
	return None

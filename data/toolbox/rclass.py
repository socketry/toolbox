import debugger
import constants
import value as rvalue
import rstring

class RClass:
	"""Wrapper for Ruby class objects (klass pointers)."""
	
	def __init__(self, klass_value):
		"""Initialize with a klass VALUE.
		
		Args:
			klass_value: A GDB value representing a Ruby class (klass pointer)
		"""
		self.klass = klass_value
		self._name = None
	
	def name(self):
		"""Get the class name as a string.
		
		Returns:
			Class name string, or formatted anonymous class representation
		"""
		if self._name is None:
			self._name = self._get_class_name()
		return self._name
	
	def _get_class_name(self):
		"""Extract class name from klass pointer.
		
		Tries multiple strategies across Ruby versions:
		1. Check against well-known global class pointers (rb_eStandardError, etc.)
		2. Try rb_classext_struct.classpath (Ruby 3.4+)
		3. Fall back to anonymous class format
		
		Returns:
			Class name string
		"""
		try:
			# Strategy 1: Check well-known exception classes
			# This works in core dumps since we're just comparing pointers
			well_known = [
				('rb_eException', 'Exception'),
				('rb_eStandardError', 'StandardError'),
				('rb_eSystemExit', 'SystemExit'),
				('rb_eInterrupt', 'Interrupt'),
				('rb_eSignal', 'SignalException'),
				('rb_eFatal', 'fatal'),
				('rb_eScriptError', 'ScriptError'),
				('rb_eLoadError', 'LoadError'),
				('rb_eNotImpError', 'NotImplementedError'),
				('rb_eSyntaxError', 'SyntaxError'),
				('rb_eSecurityError', 'SecurityError'),
				('rb_eNoMemError', 'NoMemoryError'),
				('rb_eTypeError', 'TypeError'),
				('rb_eArgError', 'ArgumentError'),
				('rb_eIndexError', 'IndexError'),
				('rb_eKeyError', 'KeyError'),
				('rb_eRangeError', 'RangeError'),
				('rb_eNameError', 'NameError'),
				('rb_eNoMethodError', 'NoMethodError'),
				('rb_eRuntimeError', 'RuntimeError'),
				('rb_eFrozenError', 'FrozenError'),
				('rb_eIOError', 'IOError'),
				('rb_eEOFError', 'EOFError'),
				('rb_eLocalJumpError', 'LocalJumpError'),
				('rb_eSysStackError', 'SystemStackError'),
				('rb_eRegexpError', 'RegexpError'),
				('rb_eThreadError', 'ThreadError'),
				('rb_eZeroDivError', 'ZeroDivisionError'),
				('rb_eFloatDomainError', 'FloatDomainError'),
				('rb_eStopIteration', 'StopIteration'),
				('rb_eMathDomainError', 'Math::DomainError'),
				('rb_eEncCompatError', 'Encoding::CompatibilityError'),
			]
			
			klass_addr = int(self.klass)
			for var_name, class_name in well_known:
				try:
					known_klass = debugger.parse_and_eval(var_name)
					if int(known_klass) == klass_addr:
						return class_name
				except:
					# Variable might not exist in this Ruby version
					continue
			
			# Strategy 2: Try modern rb_classext_struct.classpath (Ruby 3.4+)
			try:
				rclass = self.klass.cast(constants.type_struct('struct RClass').pointer())
				# Try to access classext.classpath
				try:
					# Try embedded classext (RCLASS_EXT_EMBEDDED)
					rclass_size = debugger.parse_and_eval("sizeof(struct RClass)")
					classext_addr = int(self.klass) + int(rclass_size)
					classext_type = constants.type_struct('rb_classext_t')
					classext_ptr = debugger.create_value_from_address(classext_addr, classext_type).address
					classpath_val = classext_ptr['classpath']
				except:
					# Try pointer-based classext
					try:
						classext_ptr = rclass['ptr']
						classpath_val = classext_ptr['classpath']
					except:
						classpath_val = None
				
				if classpath_val and int(classpath_val) != 0 and not rvalue.is_nil(classpath_val):
					# Decode the classpath string
					class_name_obj = rvalue.interpret(classpath_val)
					if hasattr(class_name_obj, 'to_str'):
						class_name = class_name_obj.to_str()
						if class_name and not class_name.startswith('<'):
							return class_name
			except:
				pass
			
			# Strategy 3: Fall back to anonymous class format
			return f"#<Class:0x{int(self.klass):x}>"
		except Exception as e:
			# Ultimate fallback
			return f"#<Class:0x{int(self.klass):x}>"
	
	def __str__(self):
		"""Return the class name."""
		return self.name()

def get_class_name(klass_value):
	"""Get the name of a class from its klass pointer.
	
	Args:
		klass_value: A GDB value representing a Ruby class (klass pointer)
	
	Returns:
		Class name string
	"""
	rc = RClass(klass_value)
	return rc.name()

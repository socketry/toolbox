"""
ANSI color codes for GDB output formatting.

This module provides utilities for colorizing GDB output to make metadata
less prominent and values more readable.
"""

import sys
import rvalue

class Style:
	"""Sentinel object representing a style."""
	def __init__(self, name):
		self.name = name
	
	def __repr__(self):
		return f"Style({self.name})"

# Style sentinels
reset = Style('reset')
metadata = Style('metadata')
address = Style('address')
type = Style('type')
value = Style('value')
string = Style('string')
number = Style('number')
symbol = Style('symbol')
method = Style('method')  # Alias for symbol (method names)
error = Style('error')
bold = Style('bold')
dim = Style('dim')
title = Style('title')  # For section headers in help text
placeholder = Style('placeholder')  # For help text placeholders (parameters, options)
example = Style('example')  # For example commands in help text

class Text:
	"""Plain text output without any formatting."""
	
	def __init__(self, output=None):
		"""Initialize text terminal.
		
		Args:
			output: Output stream (default: sys.stdout)
		"""
		self.output = output or sys.stdout
	
	def print(self, *args, end='\n'):
		"""Print arguments to output stream.
		
		Args:
			*args: Arguments to print (strings, Style sentinels, or objects with print_to)
			end: String appended after the last arg (default: newline)
		"""
		for arg in args:
			if isinstance(arg, Style):
				# Skip style sentinels in plain text mode
				continue
			elif hasattr(arg, 'print_to'):
				# Let object print itself
				arg.print_to(self)
			else:
				self.output.write(str(arg))
		self.output.write(end)
	
	def print_type_tag(self, type_name, addr=None, details=None):
		"""Print a type tag like <T_ARRAY@0xABCD embedded length=3>.
		
		Arguments:
			type_name: Type name (e.g., "T_ARRAY", "void *")
			addr: Optional hex address (as integer or hex string without 0x)
			details: Optional details string (e.g., "embedded length=3")
		"""
		if isinstance(addr, int):
			addr = f"{addr:x}"
		
		self.print(metadata, '<', reset, type, type_name, reset, end='')
		
		if addr:
			# @ symbol in dim, address in magenta
			self.print(metadata, '@', reset, address, f'0x{addr}', reset, end='')
		
		if details:
			self.print(metadata, f' {details}', reset, end='')
		
		self.print(metadata, '>', reset, end='')

class XTerm(Text):
	"""ANSI color/style output for terminal."""
	
	# ANSI codes
	RESET = '\033[0m'
	BOLD = '\033[1m'
	DIM = '\033[2m'
	
	RED = '\033[31m'
	GREEN = '\033[32m'
	YELLOW = '\033[33m'
	BLUE = '\033[34m'
	MAGENTA = '\033[35m'
	CYAN = '\033[36m'
	WHITE = '\033[37m'
	
	BRIGHT_RED = '\033[91m'
	BRIGHT_GREEN = '\033[92m'
	BRIGHT_YELLOW = '\033[93m'
	BRIGHT_BLUE = '\033[94m'
	BRIGHT_MAGENTA = '\033[95m'
	BRIGHT_CYAN = '\033[96m'
	
	def __init__(self, output=None):
		"""Initialize ANSI terminal.
		
		Args:
			output: Output stream (default: sys.stdout)
		"""
		super().__init__(output)
		# Map style sentinels to ANSI codes
		self.style_map = {
			reset: self.RESET,
			metadata: self.DIM,         # Type tag brackets <>
			address: self.MAGENTA,      # Memory addresses in type tags
			type: self.CYAN,            # Type names (T_ARRAY, VALUE, etc.)
			string: self.GREEN,
			number: self.CYAN,
			symbol: self.YELLOW,
			method: self.YELLOW,        # Same as symbol
			error: self.RED,
			bold: self.BOLD,
			dim: self.DIM,
			title: self.BOLD,           # Section headers in help text
			placeholder: self.BLUE,     # Help text placeholders
			example: self.GREEN,        # Example commands in help text
		}
	
	def print(self, *args, end='\n'):
		"""Print arguments to output stream with ANSI formatting.
		
		Args:
			*args: Arguments to print (strings, Style sentinels, or objects with print_to)
			end: String appended after the last arg (default: newline)
		"""
		for arg in args:
			if isinstance(arg, Style):
				# Print ANSI code for style
				self.output.write(self.style_map.get(arg, ''))
			elif hasattr(arg, 'print_to'):
				# Let object print itself
				arg.print_to(self)
			else:
				self.output.write(str(arg))
		self.output.write(end)

# Helper for creating the appropriate terminal based on TTY status
def create_terminal(from_tty):
	"""Create a terminal instance based on whether we're in a TTY."""
	if from_tty:
		return XTerm()
	else:
		return Text()

class Printer:
	"""Printer that combines terminal formatting with recursive printing logic."""
	
	def __init__(self, terminal, max_depth, debug_mode=False):
		self.terminal = terminal
		self.max_depth = max_depth
		self.debug_mode = debug_mode
	
	def debug(self, message):
		"""Print debug messages only when debug mode is enabled."""
		if self.debug_mode:
			print(f"DEBUG: {message}", file=sys.stderr)
	
	def print(self, *args):
		"""Print arguments using the terminal's formatting."""
		self.terminal.print(*args)
	
	def print_indent(self, depth):
		"""Print indentation based on depth."""
		print("  " * depth, end='')
	
	def print_with_indent(self, depth, message, end='\n'):
		"""Print a message with proper indentation based on depth."""
		self.print_indent(depth)
		print(message, end=end)
	
	def print_key_label(self, depth, index):
		"""Print a consistently formatted key label."""
		self.print_with_indent(depth, f"[{index:>4}] K: ", end='')
	
	def print_value_label(self, depth):
		"""Print a consistently formatted value label."""
		self.print_with_indent(depth, f"       V: ", end='')
	
	def print_item_label(self, depth, index):
		"""Print a consistently formatted array item label."""
		self.print_with_indent(depth, f"[{index:>4}] I: ", end='')
	
	def print_value(self, ruby_value, depth):
		"""Print a Ruby value at the given depth."""
		value_int = int(ruby_value)
		self.debug(f"print_value: value=0x{value_int:x}, depth={depth}")
		
		ruby_object = rvalue.interpret(ruby_value)
		ruby_object.print_recursive(self, depth)

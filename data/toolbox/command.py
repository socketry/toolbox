class Arguments:
	"""Structured result from parsing GDB command arguments.
	
	Attributes:
		expressions: List of expressions to evaluate (e.g., ["$var", "$ec->cfp->sp[-1]"])
		flags: Set of boolean flags (e.g., {'debug'})
		options: Dict of options with values (e.g., {'depth': 3})
	"""
	def __init__(self, expressions, flags, options):
		self.expressions = expressions
		self.flags = flags
		self.options = options
	
	def has_flag(self, flag_name):
		"""Check if a boolean flag is present"""
		return flag_name in self.flags
	
	def get_option(self, option_name, default=None):
		"""Get an option value with optional default"""
		return self.options.get(option_name, default)


class Usage:
	"""Command specification DSL for declarative command interfaces.
	
	Defines what parameters, options, and flags a command accepts,
	enabling validation and help text generation.
	
	Example:
		usage = Usage(
			summary="Print Ruby objects with recursion",
			parameters=['value'],
			options={'depth': (int, 1), 'limit': (int, None)},
			flags=['debug', 'verbose']
		)
		
		arguments = usage.parse("$var --depth 3 --debug")
		# arguments.expressions = ['$var']
		# arguments.options = {'depth': 3}
		# arguments.flags = {'debug'}
	"""
	
	def __init__(self, summary, parameters=None, options=None, flags=None, examples=None):
		"""Define command interface.
		
		Args:
			summary: One-line command description
			parameters: List of parameter names or tuples (name, description)
			options: Dict of {name: (type, default, description)}
			flags: List of flag names or tuples (name, description)
			examples: List of example command strings with descriptions
		
		Example:
			Usage(
				summary="Scan heap for objects",
				parameters=[('type_name', 'Ruby type to search for')],
				options={
					'limit': (int, None, 'Maximum objects to find'),
					'depth': (int, 1, 'Recursion depth')
				},
				flags=[
					('terminated', 'Include terminated fibers'),
					('cache', 'Use cached results')
				],
				examples=[
					("rb-heap-scan --type RUBY_T_STRING", "Find all strings"),
					("rb-heap-scan --type RUBY_T_HASH --limit 10", "Find first 10 hashes")
				]
			)
		"""
		self.summary = summary
		self.parameters = self._normalize_params(parameters or [])
		self.options = options or {}
		self.flags = self._normalize_flags(flags or [])
		self.examples = examples or []
	
	def _normalize_params(self, params):
		"""Normalize parameters to list of (name, description) tuples."""
		normalized = []
		for param in params:
			if isinstance(param, tuple):
				normalized.append(param)
			else:
				normalized.append((param, None))
		return normalized
	
	def _normalize_flags(self, flags):
		"""Normalize flags to list of (name, description) tuples."""
		normalized = []
		for flag in flags:
			if isinstance(flag, tuple):
				normalized.append(flag)
			else:
				normalized.append((flag, None))
		return normalized
	
	def parse(self, argument_string):
		"""Parse and validate command arguments.
		
		Args:
			argument_string: Raw argument string from debugger
		
		Returns:
			Arguments object with validated and type-converted values
		
		Raises:
			ValueError: If validation fails (wrong parameter count, invalid types, etc.)
		"""
		# Use existing parser to extract raw arguments
		arguments = parse_arguments(argument_string)
		
		# Validate parameter count
		if len(arguments.expressions) != len(self.parameters):
			if len(self.parameters) == 0 and len(arguments.expressions) > 0:
				raise ValueError(f"Command takes no parameters, got {len(arguments.expressions)}")
			elif len(self.parameters) == 1:
				raise ValueError(f"Command requires 1 parameter, got {len(arguments.expressions)}")
			else:
				raise ValueError(f"Command requires {len(self.parameters)} parameters, got {len(arguments.expressions)}")
		
		# Validate and convert option types
		converted_options = {}
		for option_name, option_value in arguments.options.items():
			if option_name not in self.options:
				raise ValueError(f"Unknown option: --{option_name}")
			
			# Unpack option spec (handle 2-tuple or 3-tuple)
			opt_spec = self.options[option_name]
			option_type = opt_spec[0]
			option_default = opt_spec[1]
			
			# Convert to specified type
			try:
				if option_type == int:
					converted_options[option_name] = int(option_value)
				elif option_type == str:
					converted_options[option_name] = str(option_value)
				elif option_type == bool:
					converted_options[option_name] = bool(option_value)
				else:
					# Custom type converter
					converted_options[option_name] = option_type(option_value)
			except (ValueError, TypeError) as e:
				raise ValueError(f"Invalid value for --{option_name}: {option_value} (expected {option_type.__name__})")
		
		# Add defaults for missing options
		for option_name, opt_spec in self.options.items():
			option_default = opt_spec[1]
			if option_name not in converted_options and option_default is not None:
				converted_options[option_name] = option_default
		
		# Validate flags
		flag_names = {flag[0] for flag in self.flags}
		for flag_name in arguments.flags:
			if flag_name not in flag_names:
				raise ValueError(f"Unknown flag: --{flag_name}")
		
		# Return new Arguments with converted options
		return Arguments(arguments.expressions, arguments.flags, converted_options)
	
	def print_to(self, terminal, command_name):
		"""Print help text from usage specification.
		
		Args:
			terminal: Terminal for colored output
			command_name: Name of the command (e.g., "rb-print")
		"""
		import format as fmt
		
		# Summary with color
		terminal.print(fmt.bold, self.summary, fmt.reset)
		terminal.print()
		
		# Print usage line
		terminal.print("Usage: ", end='')
		terminal.print(fmt.bold, command_name, fmt.reset, end='')
		
		for param_name, _ in self.parameters:
			terminal.print(' ', end='')
			terminal.print(fmt.placeholder, f"<{param_name}>", fmt.reset, end='')
		
		# Add option placeholders
		for option_name in self.options.keys():
			terminal.print(' ', end='')
			terminal.print(fmt.placeholder, f"[--{option_name} N]", fmt.reset, end='')
		
		# Add flag placeholders
		for flag_name, _ in self.flags:
			terminal.print(' ', end='')
			terminal.print(fmt.placeholder, f"[--{flag_name}]", fmt.reset, end='')
		
		terminal.print()
		terminal.print()
		
		# Parameter descriptions
		if self.parameters:
			terminal.print(fmt.title, "Parameters:", fmt.reset)
			
			for param_name, param_desc in self.parameters:
				terminal.print("  ", fmt.symbol, param_name, fmt.reset, end='')
				if param_desc:
					terminal.print(f" - {param_desc}")
				else:
					terminal.print()
			terminal.print()
		
		# Option descriptions
		if self.options:
			terminal.print(fmt.title, "Options:", fmt.reset)
			
			for option_name, opt_spec in self.options.items():
				opt_type, opt_default = opt_spec[0], opt_spec[1]
				opt_desc = opt_spec[2] if len(opt_spec) > 2 else None
				
				type_str = opt_type.__name__ if hasattr(opt_type, '__name__') else str(opt_type)
				default_str = f" (default: {opt_default})" if opt_default is not None else ""
				
				terminal.print("  ", fmt.symbol, f"--{option_name}", fmt.reset, end='')
				terminal.print(fmt.placeholder, f" <{type_str}>", fmt.reset, end='')
				terminal.print(default_str)
				
				if opt_desc:
					terminal.print(f"      {opt_desc}")
			terminal.print()
		
		# Flag descriptions
		if self.flags:
			terminal.print(fmt.title, "Flags:", fmt.reset)
			
			for flag_name, flag_desc in self.flags:
				terminal.print("  ", fmt.symbol, f"--{flag_name}", fmt.reset, end='')
				if flag_desc:
					terminal.print(f" - {flag_desc}")
				else:
					terminal.print()
			terminal.print()
		
		# Examples section
		if self.examples:
			terminal.print(fmt.title, "Examples:", fmt.reset)
			
			for example_cmd, example_desc in self.examples:
				terminal.print(fmt.example, f"  {example_cmd}", fmt.reset)
				if example_desc:
					terminal.print(f"      {example_desc}")

class ArgumentParser:
	"""Parse GDB command arguments handling nested brackets, quotes, and flags.
	
	This parser correctly handles:
	- Nested brackets: $ec->cfp->sp[-1]
	- Nested parentheses: ((struct foo*)bar)->baz
	- Quotes: "string value"
	- Flags: --debug, --depth 3
	- Complex expressions: foo + 10, bar->ptr[idx * 2]
	"""
	
	def __init__(self, argument_string):
		self.argument_string = argument_string.strip()
		self.position = 0
		self.length = len(self.argument_string)
	
	def parse(self):
		"""Parse the argument string and return (expressions, flags, options)
		
		Returns:
			tuple: (expressions: list[str], flags: set, options: dict)
			- expressions: List of expressions to evaluate
			- flags: Set of boolean flags (e.g., {'debug'})
			- options: Dict of options with values (e.g., {'depth': 3})
		"""
		flags = set()
		options = {}
		expressions = []
		
		while self.position < self.length:
			self.skip_whitespace()
			if self.position >= self.length:
				break
			
			if self.peek() == '-' and self.peek(1) == '-':
				# Parse a flag or option
				flag_name, flag_value = self.parse_flag()
				if flag_value is None:
					flags.add(flag_name)
				else:
					options[flag_name] = flag_value
			else:
				# Parse an expression
				expression = self.parse_expression()
				if expression:
					expressions.append(expression)
		
		return expressions, flags, options
	
	def peek(self, offset=0):
		"""Peek at character at current position + offset"""
		position = self.position + offset
		if position < self.length:
			return self.argument_string[position]
		return None
	
	def consume(self, count=1):
		"""Consume and return count characters"""
		result = self.argument_string[self.position:self.position + count]
		self.position += count
		return result
	
	def skip_whitespace(self):
		"""Skip whitespace characters"""
		while self.position < self.length and self.argument_string[self.position].isspace():
			self.position += 1
	
	def parse_flag(self):
		"""Parse a flag starting with --
		
		Returns:
			tuple: (flag_name: str, value: str|None)
			- For boolean flags: ('debug', None)
			- For valued flags: ('depth', '3')
		"""
		# Consume '--'
		self.consume(2)
		
		# Read flag name
		flag_name = ''
		while self.position < self.length and self.argument_string[self.position].isalnum():
			flag_name += self.consume()
		
		# Check if flag has a value
		self.skip_whitespace()
		
		# If next character is not another flag and not end of string, it might be a value
		if self.position < self.length and not (self.peek() == '-' and self.peek(1) == '-'):
			# Try to parse a value - it could start with $, digit, or letter
			if self.peek() and not self.peek().isspace():
				value = ''
				while self.position < self.length and not self.argument_string[self.position].isspace():
					if self.peek() == '-' and self.peek(1) == '-':
						break
					value += self.consume()
				
				# Try to convert to int if it's a number
				try:
					return flag_name, int(value)
				except ValueError:
					return flag_name, value
		
		return flag_name, None
	
	def parse_expression(self):
		"""Parse a single expression, stopping at whitespace (unless nested) or flags.
		
		An expression can be:
		- A quoted string: "foo" or 'bar'
		- A parenthesized expression: (x + y)
		- A variable with accessors: $ec->cfp->sp[-1]
		- Any combination that doesn't contain unquoted/unnested whitespace
		"""
		expression = ''
		
		while self.position < self.length:
			self.skip_whitespace()
			if self.position >= self.length:
				break
			
			character = self.peek()
			
			# Stop at flags
			if character == '-' and self.peek(1) == '-':
				break
			
			# Handle quoted strings - these are complete expressions
			if character in ('"', "'"):
				quoted = self.parse_quoted_string(character)
				expression += quoted
				# After a quoted string, we're done with this expression
				break
			
			# Handle parentheses - collect the whole balanced expression
			if character == '(':
				expression += self.parse_balanced('(', ')')
				continue
			
			# Handle brackets
			if character == '[':
				expression += self.parse_balanced('[', ']')
				continue
			
			# Handle braces
			if character == '{':
				expression += self.parse_balanced('{', '}')
				continue
			
			# Stop at whitespace (this separates expressions)
			if character.isspace():
				break
			
			# Regular character - part of a variable name, operator, etc.
			expression += self.consume()
		
		return expression.strip()
	
	def parse_quoted_string(self, quote_character):
		"""Parse a quoted string, handling escapes"""
		result = self.consume()  # Opening quote
		
		while self.position < self.length:
			character = self.peek()
			
			if character == '\\':
				# Escape sequence
				result += self.consume()
				if self.position < self.length:
					result += self.consume()
			elif character == quote_character:
				# Closing quote
				result += self.consume()
				break
			else:
				result += self.consume()
		
		return result
	
	def parse_balanced(self, open_character, close_character):
		"""Parse a balanced pair of delimiters (e.g., parentheses, brackets)"""
		result = self.consume()  # Opening delimiter
		depth = 1
		
		while self.position < self.length and depth > 0:
			character = self.peek()
			
			# Handle quotes inside balanced delimiters
			if character in ('"', "'"):
				result += self.parse_quoted_string(character)
				continue
			
			if character == open_character:
				depth += 1
			elif character == close_character:
				depth -= 1
			
			result += self.consume()
		
		return result

def parse_arguments(input):
	"""Convenience function to parse argument string.
	
	Arguments:
		input: The raw argument string from GDB command
	
	Returns:
		Arguments: Structured object with expressions, flags, and options
	
	Examples:
		>>> arguments = parse_arguments("$var --debug")
		>>> arguments.expressions
		['$var']
		>>> arguments.has_flag('debug')
		True
		
		>>> arguments = parse_arguments('"foo" "bar" --depth 3')
		>>> arguments.expressions
		['"foo"', '"bar"']
		>>> arguments.get_option('depth')
		3
		
		>>> arguments = parse_arguments("$ec->cfp->sp[-1] --debug --depth 2")
		>>> arguments.expressions
		['$ec->cfp->sp[-1]']
		>>> arguments.has_flag('debug')
		True
		>>> arguments.get_option('depth')
		2
	"""
	parser = ArgumentParser(input)
	expressions, flags, options = parser.parse()
	return Arguments(expressions, flags, options)

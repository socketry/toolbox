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

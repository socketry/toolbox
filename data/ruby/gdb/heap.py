import gdb
import sys

# Constants
RBASIC_FLAGS_TYPE_MASK = 0x1f

class RubyHeap:
	"""Ruby heap scanning infrastructure.
	
	Provides methods to iterate through the Ruby heap and find objects
	by type. Returns VALUEs (not extracted pointers) for maximum flexibility.
	"""
	
	def __init__(self):
		"""Initialize heap scanner (call initialize() to set up VM pointers)."""
		self.vm_ptr = None
		self.objspace = None
		
		# Cached type lookups
		self._rbasic_type = None
		self._value_type = None
		self._char_ptr_type = None
	
	def initialize(self):
		"""Initialize VM and objspace pointers.
		
		Returns:
			True if initialization successful, False otherwise
		"""
		try:
			self.vm_ptr = gdb.parse_and_eval('ruby_current_vm_ptr')
			if int(self.vm_ptr) == 0:
				print("Error: ruby_current_vm_ptr is NULL")
				print("Make sure Ruby is fully initialized and the process is running.")
				return False

			# Ruby 3.3+ moved objspace into a gc struct
			try:
				self.objspace = self.vm_ptr['gc']['objspace']
			except (gdb.error, KeyError):
				# Ruby 3.2 and earlier have objspace directly in VM
				self.objspace = self.vm_ptr['objspace']
			
			if int(self.objspace) == 0:
				print("Error: objspace is NULL")
				print("Make sure the Ruby GC has been initialized.")
				return False

			# Cache commonly used type lookups
			self._rbasic_type = gdb.lookup_type('struct RBasic').pointer()
			self._value_type = gdb.lookup_type('VALUE')
			self._char_ptr_type = gdb.lookup_type('char').pointer()

			return True
		except gdb.error as e:
			print(f"Error initializing: {e}")
			print("Make sure you're debugging a Ruby process with debug symbols.")
			return False
		except gdb.MemoryError as e:
			print(f"Memory error during initialization: {e}")
			print("The Ruby VM may not be fully initialized yet.")
			print("Try breaking at a point where Ruby is running (e.g., after rb_vm_exec).")
			return False
	
	def _get_page(self, page_index):
		"""Get a heap page by index, handling Ruby version differences.
		
		Args:
			page_index: Index of the page to retrieve
			
		Returns:
			Page object, or None on error
		"""
		try:
			# Ruby 3.3+ uses rb_darray with 'data' field, Ruby 3.2- uses direct pointer
			try:
				return self.objspace['heap_pages']['sorted']['data'][page_index]
			except (gdb.error, KeyError):
				# Ruby 3.2 and earlier: sorted is a direct pointer array
				return self.objspace['heap_pages']['sorted'][page_index]
		except (gdb.MemoryError, gdb.error):
			return None
	
	def iterate_heap(self):
		"""Yield all objects from the Ruby heap.
		
		Yields:
			Tuple of (VALUE, flags, address) for each object on the heap
		"""
		for obj, flags, address in self.iterate_heap_from(None):
			yield obj, flags, address
	
	def scan(self, type_flag=None, limit=None, from_address=None):
		"""Scan heap for objects matching a specific Ruby type flag.
		
		Args:
			type_flag: Ruby type constant (e.g., RUBY_T_STRING, RUBY_T_DATA), or None for all types
			limit: Maximum number of objects to find (None for no limit)
			from_address: Address to continue from (for pagination)
		
		Returns:
			Tuple of (objects, next_address) where:
			- objects: List of VALUEs matching the type
			- next_address: The next address to scan from (for pagination), or None if no more objects
		"""
		if from_address:
			print(f"DEBUG: scan() called with from_address=0x{from_address:x}", file=sys.stderr)
		else:
			print(f"DEBUG: scan() called with from_address=None", file=sys.stderr)
		objects = []
		next_address = None
		
		# Iterate heap, starting from the address if specified
		for obj, flags, obj_address in self.iterate_heap_from(from_address):
			# Check type (lower 5 bits of flags) if type_flag is specified
			if type_flag is not None:
				if (flags & RBASIC_FLAGS_TYPE_MASK) != type_flag:
					continue
			
			# If we've already hit the limit, this is the next address to continue from
			if limit and len(objects) >= limit:
				next_address = obj_address
				break
			
			objects.append(obj)
		
		# Return the next address to scan from (the first object we didn't include)
		return objects, next_address
	
	def _find_page_for_address(self, address):
		"""Find which heap page contains the given address.
		
		Args:
			address: Memory address to search for
			
		Returns:
			Page index if found, None otherwise
		"""
		if not self.objspace:
			return None
		
		try:
			allocated_pages = int(self.objspace['heap_pages']['allocated_pages'])
		except (gdb.MemoryError, gdb.error):
			return None
		
		# Linear search through pages
		# TODO: Could use binary search since pages are sorted
		for i in range(allocated_pages):
			page = self._get_page(i)
			if page is None:
				continue
			
			try:
				start = int(page['start'])
				total_slots = int(page['total_slots'])
				slot_size = int(page['slot_size'])
				
				# Check if address falls within this page's range
				page_end = start + (total_slots * slot_size)
				if start <= address < page_end:
					return i
			except (gdb.MemoryError, gdb.error):
				continue
		
		return None
	
	def iterate_heap_from(self, from_address=None):
		"""Yield all objects from the Ruby heap, optionally starting from a specific address.
		
		Args:
			from_address: If specified, finds the page containing this address and starts from there.
			              If None, starts from the beginning of the heap.
		
		Yields:
			Tuple of (VALUE, flags, address) for each object on the heap
		"""
		# If we have a from_address, find which page contains it
		start_page = 0
		start_address = None
		if from_address is not None:
			print(f"DEBUG: iterate_heap_from called with from_address=0x{from_address:x}", file=sys.stderr)
			start_page = self._find_page_for_address(from_address)
			print(f"DEBUG: _find_page_for_address returned {start_page}", file=sys.stderr)
			if start_page is None:
				# Address not found in any page, start from beginning
				print(f"Warning: Address 0x{from_address:x} not found in heap, starting from beginning", file=sys.stderr)
				start_page = 0
			else:
				# Remember to skip within the page to this address
				start_address = from_address
				print(f"DEBUG: Will start from page {start_page}, address 0x{start_address:x}", file=sys.stderr)
		
		# Delegate to the page-based iterator
		for obj, flags, obj_address in self._iterate_heap_from_page(start_page, start_address):
			yield obj, flags, obj_address
	
	def _iterate_heap_from_page(self, start_page=0, skip_until_address=None):
		"""Yield all objects from the Ruby heap, starting from a specific page.
		
		Args:
			start_page: Page index to start from (default: 0)
			skip_until_address: If specified, calculate the slot index and start from there (for first page only)
		
		Yields:
			Tuple of (VALUE, flags, address) for each object on the heap
		"""
		if not self.objspace:
			return

		try:
			allocated_pages = int(self.objspace['heap_pages']['allocated_pages'])
		except gdb.MemoryError as e:
			print(f"Error reading heap_pages: {e}")
			print("The heap may not be initialized yet.")
			return

		for i in range(start_page, allocated_pages):
			page = self._get_page(i)
			if page is None:
				continue
			
			try:
				start = int(page['start'])
				total_slots = int(page['total_slots'])
				slot_size = int(page['slot_size'])
			except (gdb.MemoryError, gdb.error) as e:
				print(f"Error reading page {i}: {e}", file=sys.stderr)
				continue

			# OPTIMIZATION: Create base pointer once per page
			try:
				base_ptr = gdb.Value(start).cast(self._rbasic_type)
			except (gdb.error, RuntimeError):
				continue

			# For the first page, calculate which slot to start from
			start_slot = 0
			if i == start_page and skip_until_address is not None:
				# Calculate slot index from address
				offset_from_page_start = skip_until_address - start
				start_slot = offset_from_page_start // slot_size
				
				# DEBUG
				print(f"DEBUG: Resuming from address 0x{skip_until_address:x}", file=sys.stderr)
				print(f"DEBUG: Page {i} starts at 0x{start:x}, slot_size={slot_size}", file=sys.stderr)
				print(f"DEBUG: Starting at slot {start_slot}", file=sys.stderr)
				
				# Ensure we don't go out of bounds
				if start_slot >= total_slots:
					continue  # Skip this entire page
				if start_slot < 0:
					start_slot = 0

			# Iterate through objects using pointer arithmetic (much faster!)
			for j in range(start_slot, total_slots):
				try:
					# Calculate byte offset and address
					byte_offset = j * slot_size
					obj_address = start + byte_offset

					# Use pointer arithmetic (much faster than creating new Value)
					obj_ptr = (base_ptr.cast(self._char_ptr_type) + byte_offset).cast(self._rbasic_type)

					# Read the flags
					flags = int(obj_ptr['flags'])

					# Skip free objects
					if flags == 0:
						continue

					# Yield the VALUE, flags, and address
					obj = obj_ptr.cast(self._value_type)
					yield obj, flags, obj_address
				except (gdb.error, RuntimeError):
					continue
	
	def find_typed_data(self, data_type, limit=None, progress=False):
		"""Find RTypedData objects matching a specific type.
		
		Args:
			data_type: Pointer to rb_data_type_struct to match
			limit: Maximum number of objects to find (None for no limit)
			progress: If True, print progress to stderr
		
		Returns:
			List of VALUEs (not extracted data pointers) matching the type
		"""
		objects = []
		
		# T_DATA constant
		T_DATA = 0x0c
		
		# Get RTypedData type for casting
		rtypeddata_type = gdb.lookup_type('struct RTypedData').pointer()
		
		try:
			if progress:
				allocated_pages = int(self.objspace['heap_pages']['allocated_pages'])
				print(f"Scanning {allocated_pages} heap pages...", file=sys.stderr)
		except (gdb.MemoryError, gdb.error):
			pass
		
		objects_checked = 0
		
		for obj, flags, address in self.iterate_heap():
			# Check if we've reached the limit
			if limit and len(objects) >= limit:
				if progress:
					print(f"Reached limit of {limit} object(s), stopping scan", file=sys.stderr)
				break
			
			objects_checked += 1
			
			# Print progress every 10000 objects
			if progress and objects_checked % 10000 == 0:
				print(f"  Checked {objects_checked} objects, found {len(objects)} match(es)...", file=sys.stderr)
			
			# Check if it's T_DATA
			if (flags & RBASIC_FLAGS_TYPE_MASK) != T_DATA:
				continue
			
			# Cast to RTypedData and check type
			try:
				typed_data = obj.cast(rtypeddata_type)
				
				if typed_data['type'] == data_type:
					# Return the VALUE, not the extracted data pointer
					objects.append(obj)
					if progress:
						print(f"  Found object #{len(objects)} at VALUE 0x{int(obj):x}", file=sys.stderr)
			except (gdb.error, RuntimeError):
				continue
		
		if progress:
			if limit and len(objects) >= limit:
				print(f"Scan complete: checked {objects_checked} objects (stopped at limit)", file=sys.stderr)
			else:
				print(f"Scan complete: checked {objects_checked} objects", file=sys.stderr)
		
		return objects


class RubyHeapScanCommand(gdb.Command):
	"""Scan the Ruby heap for objects, optionally filtered by type.
	
	Usage: rb-heap-scan [--type TYPE] [--limit N] [--from $heap]
	
	TYPE can be:
	  - A Ruby type constant like RUBY_T_STRING, RUBY_T_ARRAY, RUBY_T_HASH
	  - A numeric value (e.g., 0x05 for T_STRING)
	  - Omit --type to scan all objects
	
	Options:
	  --type TYPE    Filter by Ruby type (omit to scan all objects)
	  --limit N      Stop after finding N objects (default: 10)
	  --from ADDR    Start scanning from the given address (for pagination)
	
	Pagination:
	  The address of the last found object is saved to $heap, allowing you to paginate:
	    rb-heap-scan --type RUBY_T_STRING --limit 10           # First page
	    rb-heap-scan --type RUBY_T_STRING --limit 10 --from $heap   # Next page
	
	The $heap variable contains the address of the last scanned object.
	
	Examples:
	  rb-heap-scan --type RUBY_T_STRING
	  rb-heap-scan --type RUBY_T_ARRAY --limit 20
	  rb-heap-scan --type 0x05          # T_STRING
	  rb-heap-scan --limit 100          # All objects
	  rb-heap-scan --from $heap         # Continue from last scan
	"""
	
	def __init__(self):
		super(RubyHeapScanCommand, self).__init__("rb-heap-scan", gdb.COMMAND_USER)
	
	def usage(self):
		"""Print usage information."""
		print("Usage: rb-heap-scan [--type TYPE] [--limit N] [--from $heap]")
		print("Examples:")
		print("  rb-heap-scan --type RUBY_T_STRING              # Find up to 10 strings")
		print("  rb-heap-scan --type RUBY_T_ARRAY --limit 5     # Find up to 5 arrays")
		print("  rb-heap-scan --type 0x05 --limit 100           # Find up to 100 T_STRING objects")
		print("  rb-heap-scan --limit 20                        # Scan 20 objects (any type)")
		print("  rb-heap-scan --type RUBY_T_STRING --from $heap # Continue from last scan")
		print()
		print("Pagination:")
		print("  The address of the last object is saved to $heap for pagination:")
		print("    rb-heap-scan --type RUBY_T_STRING --limit 10        # First page")
		print("    rb-heap-scan --type RUBY_T_STRING --from $heap      # Next page")
	
	def _parse_type(self, type_arg):
		"""Parse a type argument and return the type value.
		
		Args:
			type_arg: String type argument (constant name or numeric value)
			
		Returns:
			Integer type value, or None on error
		"""
		import constants
		
		# Try as a constant name first
		type_value = constants.get(type_arg)
		
		if type_value is None:
			# Try parsing as a number (hex or decimal)
			try:
				if type_arg.startswith('0x') or type_arg.startswith('0X'):
					type_value = int(type_arg, 16)
				else:
					type_value = int(type_arg)
			except ValueError:
				print(f"Error: Unknown type constant '{type_arg}'")
				print("Use a constant like RUBY_T_STRING or a numeric value like 0x05")
				return None
		
		# Validate type value is reasonable (0-31 for the 5-bit type field)
		if not (0 <= type_value <= 31):
			print(f"Warning: Type value {type_value} (0x{type_value:x}) is outside valid range 0-31")
		
		return type_value
	
	def invoke(self, arg, from_tty):
		"""Execute the heap scan command."""
		try:
			# Parse arguments
			import command
			arguments = command.parse_arguments(arg if arg else "")
			
			print(f"DEBUG: Raw arg string: '{arg}'", file=sys.stderr)
			
			# Check if we're continuing from a previous scan
			from_option = arguments.get_option('from')
			print(f"DEBUG: from_option = {from_option}", file=sys.stderr)
			if from_option is not None:
				try:
					# $heap should be an address (pointer value)
					from_address = int(gdb.parse_and_eval(from_option))
					print(f"DEBUG: Parsed from_address = 0x{from_address:x}", file=sys.stderr)
				except (gdb.error, ValueError, TypeError) as e:
					# If $heap doesn't exist or is void/invalid, start from the beginning
					print(f"Note: {from_option} is not set or invalid, wrapping around to start of heap", file=sys.stderr)
					from_address = None
			else:
				# New scan
				from_address = None
			
			# Get limit (default 10)
			limit = 10
			limit_value = arguments.get_option('limit')
			if limit_value is not None:
				try:
					limit = int(limit_value)
				except (ValueError, TypeError):
					print("Error: --limit must be a number")
					return
			
			# Get type (optional)
			type_value = None
			type_option = arguments.get_option('type')
			if type_option is not None:
				type_value = self._parse_type(type_option)
				if type_value is None:
					return
			
			# Initialize heap
			heap = RubyHeap()
			if not heap.initialize():
				return
			
			# Print search description
			if type_value is not None:
				type_desc = f"type 0x{type_value:02x}"
			else:
				type_desc = "all types"
			
			if from_address:
				print(f"Scanning heap for {type_desc}, limit={limit}, continuing from address 0x{from_address:x}...")
			else:
				print(f"Scanning heap for {type_desc}, limit={limit}...")
			print()
			
			# Find objects
			objects, next_address = heap.scan(type_value, limit=limit, from_address=from_address)
			
			if not objects:
				print("No objects found")
				if from_address:
					print("(You may have reached the end of the heap)")
				return
			
			# Import format for terminal output
			import format
			terminal = format.create_terminal(from_tty)
			
			# Import value module for interpretation
			import value as value_module
			
			print(f"Found {len(objects)} object(s):")
			print()
			
			for i, obj in enumerate(objects):
				obj_int = int(obj)
				
				# Set as convenience variable
				var_name = f"heap{i}"
				gdb.set_convenience_variable(var_name, obj)
				
				# Try to interpret and display the object
				try:
					interpreted = value_module.interpret(obj)
					
					print(terminal.print(
						format.metadata, f"  [{i}] ",
						format.dim, f"${var_name} = ",
						format.reset, interpreted
					))
				except Exception as e:
					print(terminal.print(
						format.metadata, f"  [{i}] ",
						format.dim, f"${var_name} = ",
						format.error, f"<error: {e}>"
					))
			
			print()
			print(terminal.print(
				format.dim, 
				f"Objects saved in $heap0 through $heap{len(objects)-1}",
				format.reset
			))
			
			# Save next address to $heap for pagination
			if next_address is not None:
				# Save the next address to continue from
				gdb.set_convenience_variable('heap', gdb.Value(next_address).cast(gdb.lookup_type('void').pointer()))
				print(terminal.print(
					format.dim,
					f"Next scan address saved to $heap: 0x{next_address:016x}",
					format.reset
				))
				print(terminal.print(
					format.dim,
					f"Run 'rb-heap-scan --type {type_option if type_option else '...'} --from $heap' for next page",
					format.reset
				))
			else:
				# Reached the end of the heap - unset $heap so next scan starts fresh
				gdb.set_convenience_variable('heap', None)
				print(terminal.print(
					format.dim,
					f"Reached end of heap (no more objects to scan)",
					format.reset
				))
			
		except Exception as e:
			print(f"Error: {e}")
			import traceback
			traceback.print_exc()


# Register commands
RubyHeapScanCommand()

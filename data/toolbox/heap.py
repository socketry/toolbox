import debugger
import sys
import command
import constants
import format

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
		self._flags_offset = None
		self._value_size = None
	
	def initialize(self):
		"""Initialize VM and objspace pointers.
		
		Returns:
			True if initialization successful, False otherwise
		"""
		try:
			self.vm_ptr = debugger.parse_and_eval('ruby_current_vm_ptr')
			if int(self.vm_ptr) == 0:
				print("Error: ruby_current_vm_ptr is NULL")
				print("Make sure Ruby is fully initialized and the process is running.")
				return False

			# Ruby 3.3+ moved objspace into a gc struct, Ruby 3.2- has it directly in VM
			# Try gc.objspace first (Ruby 3.3+), fall back to vm.objspace (Ruby 3.2-)
			gc_struct = self.vm_ptr['gc']
			if gc_struct is not None:
				# Ruby 3.3+ path
				self.objspace = gc_struct['objspace']
			else:
				# Ruby 3.2- path
				self.objspace = self.vm_ptr['objspace']
			
			if self.objspace is None:
				print("Error: Could not access objspace field")
				print(f"VM pointer type: {self.vm_ptr.type}")
				print("Make sure you're debugging a Ruby process with debug symbols.")
				return False
			
			# Check if objspace is NULL (can happen if GC not initialized)
			try:
				objspace_int = int(self.objspace)
			except (debugger.Error, TypeError, ValueError) as e:
				print(f"Error: Can't convert objspace to int: {e}")
				return False
				return False
			
			if objspace_int == 0:
				print("Error: objspace is NULL")
				print("Make sure the Ruby GC has been initialized.")
				return False

			# Cache commonly used type lookups
			self._rbasic_type = constants.type_struct('struct RBasic').pointer()
			self._value_type = constants.type_struct('VALUE')
			self._char_ptr_type = constants.type_struct('char').pointer()
			
			# Cache flags field offset for fast memory access
			# This is critical for LLDB performance where field lookup is expensive
			try:
				# Get a dummy RBasic to find the flags offset
				rbasic_struct = constants.type_struct('struct RBasic')
				# In RBasic, 'flags' is the first field (offset 0)
				# We need to find its offset programmatically for portability
				fields = rbasic_struct.fields()
				flags_field = next((f for f in fields if f.name == 'flags'), None)
				if flags_field:
					self._flags_offset = flags_field.bitpos // 8
				else:
					# Flags is typically the first field (offset 0)
					self._flags_offset = 0
				self._value_size = self._value_type.sizeof
			except (debugger.Error, AttributeError):
				# Fallback: flags is at offset 0 (first field in RBasic)
				self._flags_offset = 0
				self._value_size = 8

			return True
		except debugger.Error as e:
			print(f"Error initializing: {e}")
			print("Make sure you're debugging a Ruby process with debug symbols.")
			return False
		except debugger.MemoryError as e:
			print(f"Memory error during initialization: {e}")
			print("The Ruby VM may not be fully initialized yet.")
			print("Try breaking at a point where Ruby is running (e.g., after rb_vm_exec).")
			return False
	
	def _read_flags_fast(self, obj_address):
		"""Read flags field directly from memory without field lookup.
		
		This is a critical optimization for LLDB where GetChildMemberWithName
		is expensive. By reading flags directly using the cached offset,
		we avoid thousands of field lookups during heap iteration.
		
		Args:
			obj_address: Memory address of the RBasic object
		
		Returns:
			Integer flags value
		"""
		try:
			flags_address = obj_address + self._flags_offset
			# Read VALUE-sized memory at flags offset
			flags_bytes = debugger.read_memory(flags_address, self._value_size)
			# Convert bytes to integer (little-endian on x86_64)
			return int.from_bytes(flags_bytes, byteorder='little', signed=False)
		except (debugger.Error, debugger.MemoryError):
			# Fallback to field access if direct memory read fails
			obj_ptr = debugger.create_value(obj_address, self._rbasic_type)
			return int(obj_ptr['flags'])
	
	def _get_page(self, page_index):
		"""Get a heap page by index, handling Ruby version differences.
		
		Args:
			page_index: Index of the page to retrieve
			
		Returns:
			Page object, or None on error
		"""
		try:
			# Ruby 3.3+ uses rb_darray with 'data' field, Ruby 3.2- uses direct pointer
			sorted_field = self.objspace['heap_pages']['sorted']
			if sorted_field is not None:
				data_field = sorted_field['data']
				if data_field is not None:
					# Ruby 3.3+: rb_darray with 'data' field
					return data_field[page_index]
			# Ruby 3.2 and earlier: sorted is a direct pointer array
			return self.objspace['heap_pages']['sorted'][page_index]
		except (debugger.MemoryError, debugger.Error):
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
		except (debugger.MemoryError, debugger.Error):
			return None
		
		# Linear search through pages
		# TODO: Could use binary search since pages are sorted
		for i in range(allocated_pages):
			page = self._get_page(i)
			if page is None:
				continue
			
			try:
				start = page['start']  # Keep as Value object
				total_slots = int(page['total_slots'])
				slot_size = int(page['slot_size'])
				
				# Check if address falls within this page's range
				# Convert to int for arithmetic comparison
				page_end = int(start) + (total_slots * slot_size)
				if int(start) <= address < page_end:
					return i
			except (debugger.MemoryError, debugger.Error):
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
			start_page = self._find_page_for_address(from_address)
			if start_page is None:
				# Address not found in any page, start from beginning
				print(f"Warning: Address 0x{from_address:x} not found in heap, starting from beginning", file=sys.stderr)
				start_page = 0
			else:
				# Remember to skip within the page to this address
				start_address = from_address

		
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
		except debugger.MemoryError as e:
			print(f"Error reading heap_pages: {e}")
			print("The heap may not be initialized yet.")
			return

		# Cache types for pointer arithmetic and casting
		rbasic_type = constants.type_struct('struct RBasic')
		rbasic_ptr_type = rbasic_type.pointer()
		char_ptr_type = constants.type_struct('char').pointer()

		for i in range(start_page, allocated_pages):
			page = self._get_page(i)
			if page is None:
				continue
			
			try:
				# Get start address - in some Ruby versions it's a pointer, in others it's an integer
				start_value = page['start']
				# Try to cast to char* (for pointer types), but if it fails or is already int-like, just use int
				try:
					start_char_ptr = start_value.cast(char_ptr_type)
					start_int = int(start_char_ptr)
				except (debugger.Error, AttributeError):
					# start is already an integer value (e.g., Ruby 3.2 uses uintptr_t)
					start_int = int(start_value)
				
				total_slots = int(page['total_slots'])
				slot_size = int(page['slot_size'])
			except (debugger.MemoryError, debugger.Error) as e:
				print(f"Error reading page {i}: {e}", file=sys.stderr)
				continue
			
			# Skip pages with invalid dimensions
			if total_slots <= 0 or slot_size <= 0:
				print(f"Warning: Page {i} has invalid dimensions (total_slots={total_slots}, slot_size={slot_size}), skipping", file=sys.stderr)
				continue

			# For the first page, calculate which slot to start from
			start_slot = 0
			if i == start_page and skip_until_address is not None:
				# Calculate slot index from address
				offset_from_page_start = int(skip_until_address) - start_int
				start_slot = offset_from_page_start // slot_size
				
				# Ensure we don't go out of bounds
				if start_slot >= total_slots:
					continue  # Skip this entire page
				if start_slot < 0:
					start_slot = 0

			# POINTER ARITHMETIC + BULK READ APPROACH:
			# 
			# Ruby heap pages contain variable-width allocations (slot_size bytes each).
			# We treat the page start as a char* for byte-wise pointer arithmetic:
			# 1. Cast page start to char* (byte pointer)
			# 2. Add byte offset: char_ptr + (slot_index * slot_size)
			# 3. Cast result to RBasic* to get the object pointer
			#
			# For performance, we also:
			# - Read all flags in one bulk memory read (fast Python bytes)
			# - Extract flags using byte slicing (pure Python, no debugger overhead)
			#
			# This approach is both semantically correct (proper pointer arithmetic)
			# and performant (~370ms for 17k objects).
			try:
				# Step 1: Read all flags for this page in one memory read (FAST)
				page_size = total_slots * slot_size
				flags_data = None
				try:
					page_data = debugger.read_memory(start_int, page_size)
					flags_data = page_data
				except (debugger.Error, debugger.MemoryError):
					# If bulk read fails, we'll read flags individually
					flags_data = None
				
				# Step 2: Iterate through slots using integer arithmetic for speed
				for j in range(start_slot, total_slots):
					try:
						# Integer arithmetic for speed: start_int + byte_offset
						byte_offset = j * slot_size
						obj_address = start_int + byte_offset

						# Read flags from bulk-read memory (FAST - pure Python byte manipulation)
						if flags_data is not None:
							try:
								flags_offset_in_page = byte_offset + self._flags_offset
								flags_bytes = flags_data[flags_offset_in_page:flags_offset_in_page + self._value_size]
								flags = int.from_bytes(flags_bytes, byteorder='little', signed=False)
							except (IndexError, ValueError):
								# Fall back to direct read
								flags = self._read_flags_fast(obj_address)
						else:
							# No bulk data, read directly
							flags = self._read_flags_fast(obj_address)

						# Skip free objects (most common case - skip early)
						if flags == 0:
							continue

						# Create VALUE for live objects
						# The obj_address IS the VALUE (pointer to the heap slot)
						obj = debugger.create_value_from_int(obj_address, self._value_type)
						yield obj, flags, obj_address
					except (debugger.Error, RuntimeError):
						continue
						
			except (debugger.Error, debugger.MemoryError) as e:
				# If reading page failed, skip it
				print(f"Failed to read page {i}: {e}, skipping", file=sys.stderr)
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
		rtypeddata_type = constants.type_struct('struct RTypedData').pointer()
		
		try:
			if progress:
				allocated_pages = int(self.objspace['heap_pages']['allocated_pages'])
				print(f"Scanning {allocated_pages} heap pages...", file=sys.stderr)
		except (debugger.MemoryError, debugger.Error):
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
				type_field = typed_data['type']
				
				# Check if field access failed (returns None when type is incomplete)
				if type_field is None:
					# On first failure, print a helpful error message once
					if not hasattr(self, '_incomplete_type_warning_shown'):
						self._incomplete_type_warning_shown = True
						print("\nError: struct RTypedData debug symbols are incomplete", file=sys.stderr)
						print("Cannot access RTypedData fields with this Ruby version.", file=sys.stderr)
						print("\nThis is a known issue with Ruby 3.4.x on macOS:", file=sys.stderr)
						print("  • A dsymutil bug drops RTypedData from debug symbols", file=sys.stderr)
						print("  • Caused by complex 'const T *const' type in the struct", file=sys.stderr)
						print("  • Fixed in Ruby head (commit ce51ef30df)", file=sys.stderr)
						print("\nWorkarounds:", file=sys.stderr)
						print("  • Use Ruby head: ruby-install ruby-head -- CFLAGS=\"-g -O0\"", file=sys.stderr)
						print("  • Or use GDB on Linux (works with Ruby 3.4.x)", file=sys.stderr)
						print("\nSee: https://socketry.github.io/toolbox/guides/getting-started/", file=sys.stderr)
						print(file=sys.stderr)
					# Can't scan without complete type info
					break
				
				# Compare type pointers
				if type_field == data_type:
					# Return the VALUE, not the extracted data pointer
					objects.append(obj)
					if progress:
						print(f"  Found object #{len(objects)} at VALUE 0x{int(obj):x}", file=sys.stderr)
			except (debugger.Error, RuntimeError):
				continue
		
		if progress:
			if limit and len(objects) >= limit:
				print(f"Scan complete: checked {objects_checked} objects (stopped at limit)", file=sys.stderr)
			else:
				print(f"Scan complete: checked {objects_checked} objects", file=sys.stderr)
		
		return objects


class RubyHeapScanHandler:
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
	
	USAGE = command.Usage(
		summary="Scan the Ruby heap for objects, optionally filtered by type",
		parameters=[],
		options={
			'type': (str, None, 'Filter by Ruby type (e.g., RUBY_T_STRING, RUBY_T_ARRAY, or 0x05)'),
			'limit': (int, 10, 'Maximum objects to find'),
			'from': (str, None, 'Start address for pagination (use $heap)')
		},
		flags=[],
		examples=[
			("rb-heap-scan --type RUBY_T_STRING", "Find up to 10 strings"),
			("rb-heap-scan --type RUBY_T_ARRAY --limit 20", "Find first 20 arrays"),
			("rb-heap-scan --from $heap", "Continue from last scan (pagination)")
		]
	)
	
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
	
	def invoke(self, arguments, terminal):
		"""Execute the heap scan command."""
		try:
			# Check if we're continuing from a previous scan
			from_option = arguments.get_option('from')
			if from_option is not None:
				try:
					# $heap should be an address (pointer value)
					from_address = int(debugger.parse_and_eval(from_option))
				except (debugger.Error, ValueError, TypeError) as e:
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
			
			import value as value_module
			
			print(f"Found {len(objects)} object(s):")
			print()
			
			for i, obj in enumerate(objects):
				# Set as convenience variable
				obj_int = int(obj)
				var_name = f"heap{i}"
				debugger.set_convenience_variable(var_name, obj)
				
				# Try to interpret and display the object
				try:
					interpreted = value_module.interpret(obj)
					
					terminal.print(
						format.metadata, f"  [{i}] ",
						format.dim, f"${var_name} = ",
						format.reset, interpreted
					)
				except Exception as e:
					terminal.print(
						format.metadata, f"  [{i}] ",
						format.dim, f"${var_name} = ",
						format.error, f"<error: {e}>"
					)
			
			print()
			terminal.print(
				format.dim, 
				f"Objects saved in $heap0 through $heap{len(objects)-1}",
				format.reset
			)
			
			# Save next address to $heap for pagination
			if next_address is not None:
				# Save the next address to continue from
				void_ptr_type = constants.type_struct('void').pointer()
				debugger.set_convenience_variable('heap', debugger.create_value(next_address, void_ptr_type))
				terminal.print(
					format.dim,
					f"Next scan address saved to $heap: 0x{next_address:016x}",
					format.reset
				)
				terminal.print(
					format.dim,
					f"Run 'rb-heap-scan --type {type_option if type_option else '...'} --from $heap' for next page",
					format.reset
				)
			else:
				# Reached the end of the heap - unset $heap so next scan starts fresh
				debugger.set_convenience_variable('heap', None)
				terminal.print(
					format.dim,
					f"Reached end of heap (no more objects to scan)",
					format.reset
				)
			
		except Exception as e:
			print(f"Error: {e}")
			import traceback
			traceback.print_exc()


# Register commands
debugger.register("rb-heap-scan", RubyHeapScanHandler, usage=RubyHeapScanHandler.USAGE)

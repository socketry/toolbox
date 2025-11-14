# Heap Debugging

This guide explains how to navigate Ruby's heap to find objects, diagnose memory issues, and understand object relationships.

## Why Heap Debugging Matters

Ruby's garbage collector manages thousands to millions of objects across heap pages. When debugging memory leaks, performance issues, or trying to find specific objects, you need to navigate this heap efficiently. Standard GDB cannot understand Ruby's object layout or page structure, making manual heap inspection tedious and error-prone.

Use heap debugging when you need:

- **Find leaked objects**: Locate objects that should have been garbage collected
- **Discover fiber instances**: Find all fibers in a crashed or hung application
- **Track object relationships**: See what objects reference others
- **Diagnose memory bloat**: Understand what types of objects consume memory

## Heap Structure Overview

Ruby's heap is organized as:

1. **Heap Pages**: Fixed-size pages allocated from the system
2. **Slots**: Each page contains fixed-size slots for objects
3. **Objects**: Ruby objects (RBasic, RHash, RArray, etc.) stored in slots
4. **Object Space**: The global heap manager (`objspace`)

## Scanning the Heap

### Finding Objects by Type

Scan the heap for specific types of Ruby objects:

~~~
(gdb) rb-heap-scan --type RUBY_T_STRING --limit 10
Scanning heap for type 0x05, limit=10...

Found 10 object(s):

  [0] $heap0 = <T_STRING@...> "..."
  [1] $heap1 = <T_STRING@...> "..."
  ...
  [9] $heap9 = <T_STRING@...> "..."

Objects saved in $heap0 through $heap9
Next scan address saved to $heap: 0x...
Run 'rb-heap-scan --from $heap ...' for next page
~~~

### Finding Fibers

Find all fiber objects:

~~~
(gdb) rb-fiber-scan-heap
Scanning heap for Fiber objects...
  Checked 45000 objects, found 12 fiber(s)...

Found 12 fiber(s):

Fiber #0: <T_DATA@...> → <struct rb_fiber_struct@...>
  Status: SUSPENDED
  Stack: <void *@...>
  VM Stack: <VALUE *@...>
  CFP: <rb_control_frame_t@...>
  ...
~~~

This uses a specialized scanner optimized for fibers.

### How Heap Scanning Works

The scanner:

1. Accesses `ruby_current_vm_ptr->gc->objspace`
2. Iterates through `heap_pages->sorted->data[]`
3. For each page, checks `total_slots` objects
4. Identifies objects by their `flags` field (bits 0-4 = type)
5. Filters for specific types if `--type` is specified

### Common Types

Ruby type constants and their numeric values:

~~~
RUBY_T_STRING  = 0x05    # Strings
RUBY_T_ARRAY   = 0x07    # Arrays  
RUBY_T_HASH    = 0x08    # Hashes
RUBY_T_DATA    = 0x0c    # Data objects (like Fibers)
RUBY_T_OBJECT  = 0x01    # Generic objects
~~~

Examples:

~~~
(gdb) rb-heap-scan --type RUBY_T_STRING --limit 20
(gdb) rb-heap-scan --type 0x08 --limit 10  # Same as RUBY_T_HASH
(gdb) rb-heap-scan --limit 100             # All types
~~~

### Pagination

Continue scanning from where you left off:

~~~
(gdb) rb-heap-scan --type RUBY_T_STRING --limit 10
Scanning heap for type 0x05, limit=10...

Found 10 object(s):
  [0] $heap0 = <T_STRING@...> "..."
  ...
Objects saved in $heap0 through $heap9
Next scan address saved to $heap: 0x...

(gdb) rb-heap-scan --type RUBY_T_STRING --limit 10 --from $heap
Scanning heap for type 0x05, limit=10...
Starting from saved position: 0x...

Found 10 object(s):
  [0] $heap0 = <T_STRING@...> "..."
  ...
~~~

## Understanding Object Layout

### Object Headers (RBasic)

Every Ruby object starts with:

~~~ruby
struct RBasic {
    VALUE flags;    # Type and flag information
    VALUE klass;    # Object's class
}
~~~

The `flags` field encodes:
- Object type (bits 0-4): T_STRING, T_HASH, T_ARRAY, etc.
- GC flags (bit 5-11): Mark bits, frozen status, etc.
- Type-specific flags (bits 12+): Embedded vs heap, size info, etc.

### Type Detection

Check an object's type:

~~~
(gdb) set $obj = (VALUE)0x7f8a1c888888
(gdb) set $basic = (struct RBasic *)$obj
(gdb) p/x $basic->flags
$1 = 0x20040005

(gdb) p/x $basic->flags & 0x1f
$2 = 0x5                        # T_STRING (0x05)
~~~

Or use Ruby commands:

~~~python
obj_type = flags & 0x1f
type_names = {
    0x05: "T_STRING",
    0x07: "T_ARRAY", 
    0x08: "T_HASH",
    0x0c: "T_DATA",
    ...
}
~~~

## Practical Examples

### Finding All Objects of a Type

Scan for all string objects (requires custom script):

~~~python
python
for obj, flags in iterate_heap():
    if (flags & 0x1f) == 0x05:  # T_STRING
        print(f"String at {obj}")
end
~~~

### Locating Large Arrays

Find arrays consuming significant memory:

~~~python
python
for obj, flags in iterate_heap():
    if (flags & 0x1f) == 0x07:  # T_ARRAY
        rarray = obj.cast(gdb.lookup_type("struct RArray").pointer())
        if (flags & (1 << 12)) == 0:  # Heap array (not embedded)
            length = int(rarray["as"]["heap"]["len"])
            if length > 1000:
                print(f"Large array at {obj}: {length} elements")
end
~~~

### Finding Objects by Content

Search for strings containing specific text:

~~~python
python
import gdb

def find_strings_containing(search_text):
    """Find all Ruby strings containing specific text"""
    matches = []
    for obj, flags in iterate_heap():
        if (flags & 0x1f) == 0x05:  # T_STRING
            try:
                rstring = obj.cast(gdb.lookup_type("struct RString").pointer())
                length = int(rstring["len"])
                
                # Read string content (simplified)
                if length < 1000:  # Reasonable size
                    # ... (read string bytes) ...
                    if search_text in string_content:
                        matches.append(obj)
            except:
                pass
    return matches
end
~~~

## Memory Analysis

### Heap Page Statistics

Understand heap organization:

~~~
(gdb) p ruby_current_vm_ptr->gc->objspace->heap_pages->allocated_pages
$1 = 1250                       # Total pages allocated

(gdb) p ruby_current_vm_ptr->gc->objspace->heap_pages->sorted->meta->length
$2 = 1250                       # Accessible pages

# Average objects per page:
(gdb) p 67890 / 1250
$3 = 54                         # ~54 objects per page
~~~

### Object Slot Details

Examine a specific heap page:

~~~
(gdb) set $page = ruby_current_vm_ptr->gc->objspace->heap_pages->sorted->data[0]
(gdb) p $page->start           # First object address
$4 = 0x7f8a1c000000

(gdb) p $page->total_slots     # Objects in this page
$5 = 64

(gdb) p $page->slot_size       # Bytes per slot
$6 = 40
~~~

### Memory Consumption

Calculate memory usage by type:

~~~python
python
type_counts = {}
type_memory = {}

for obj, flags in iterate_heap():
    obj_type = flags & 0x1f
    type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
    # Each object consumes at minimum one slot
    type_memory[obj_type] = type_memory.get(obj_type, 0) + 40  # slot_size

for obj_type in sorted(type_counts.keys()):
    count = type_counts[obj_type]
    memory_kb = type_memory[obj_type] / 1024
    print(f"Type 0x{obj_type:02x}: {count:6} objects, {memory_kb:8.1f} KB")
end
~~~

## Advanced Techniques

### Custom Heap Iterators

The fiber scanning code provides a reusable heap iterator:

~~~python
python
# In your custom GDB script:
from fiber import RubyFiberDebug

debug = RubyFiberDebug()
if debug.initialize():
    for obj, flags in debug.iterate_heap():
        # Your custom logic here
        pass
end
~~~

### Finding Objects by Reference

Locate what holds a reference to an object:

~~~python
python
target_address = 0x7f8a1c888888

for obj, flags in iterate_heap():
    obj_type = flags & 0x1f
    
    # Check if this is a hash
    if obj_type == 0x08:
        rhash = obj.cast(gdb.lookup_type("struct RHash").pointer())
        # ... iterate hash entries ...
        # ... check if any value == target_address ...
    
    # Check if this is an array
    elif obj_type == 0x07:
        # ... iterate array elements ...
end
~~~

This helps track down unexpected object retention.

### Heap Fragmentation Analysis

Check how objects are distributed across pages:

~~~python
python
page_utilization = []

objspace = gdb.parse_and_eval("ruby_current_vm_ptr->gc->objspace")
allocated_pages = int(objspace["heap_pages"]["allocated_pages"])

for i in range(allocated_pages):
    page = objspace["heap_pages"]["sorted"]["data"][i]
    total_slots = int(page["total_slots"])
    
    # Count non-free objects
    used_slots = 0
    # ... iterate and count ...
    
    utilization = (used_slots / total_slots) * 100
    page_utilization.append(utilization)
    
average = sum(page_utilization) / len(page_utilization)
print(f"Average page utilization: {average:.1f}%")
end
~~~

Low utilization indicates fragmentation.

## Best Practices

### Cache Fiber Results

Don't scan repeatedly in the same session:

~~~
(gdb) rb-fiber-scan-heap --cache fibers.json    # Scan once
(gdb) rb-fiber-scan-switch 5                    # Use cached results
~~~

Later in the same session, just load the cache:

~~~
(gdb) rb-fiber-scan-heap --cache                # Instant load
(gdb) rb-fiber-scan-stack-trace-all             # View all backtraces
~~~

### Limit Scans in Production

For production core dumps with millions of objects:

~~~
(gdb) rb-fiber-scan-heap 20             # Find first 20 fibers only
(gdb) rb-heap-scan --limit 100          # Find first 100 objects of any type
~~~

Often you only need a few objects to diagnose issues.

### Use Object Inspection Together

Combine heap scanning with object inspection:

~~~
(gdb) rb-heap-scan --type RUBY_T_HASH --limit 5
Scanning heap for type 0x08, limit=5...

Found 5 object(s):

  [0] $heap0 = <T_HASH@...>
  [1] $heap1 = <T_HASH@...>
  ...

(gdb) rb-object-print $heap0 --depth 2
<T_HASH@...>
[   0] K: <T_SYMBOL> :key
       V: <T_FIXNUM> 123
  ...
~~~

## Common Pitfalls

### Stale Cache Files

If you load a cache from a different core dump:

~~~
(gdb) rb-fiber-scan-heap --cache
Loaded fiber addresses from fibers.json
Warning: Could not access fiber at 0x7f8a1c800500
...
~~~

Delete the cache and rescan:

~~~ bash
$ rm fibers.json
~~~

### Scanning Uninitialized VM

If you scan too early during Ruby initialization:

~~~
(gdb) rb-fiber-scan-heap
Error: ruby_current_vm_ptr is NULL
Make sure Ruby is fully initialized and the process is running.
~~~

Set a breakpoint after VM initialization:

~~~
(gdb) break rb_vm_exec
(gdb) run
(gdb) rb-fiber-scan-heap           # Now works
~~~

### Memory Errors in Core Dumps

Some heap pages may be unmapped in core dumps:

~~~
Scanning 5000 heap pages...
Error reading page 1234: Cannot access memory at address 0x...
~~~

This is normal - continue with accessible pages.

## Performance Optimization

### Targeted Scanning

Instead of scanning the entire heap, use known addresses:

~~~
(gdb) rb-fiber-from-stack 0x7f8a1e000000
Searching for fiber with stack base 0x7f8a1e000000...
Found fiber: 0x7f8a1c800300
~~~

### Heap Iteration Caching

The scanner caches GDB type lookups for performance:

- `struct RBasic`
- `struct RTypedData`
- `struct rb_fiber_struct`

This makes subsequent iterations much faster.

## See Also

- {ruby Ruby::GDB::fiber-debugging Fiber debugging} for working with found fibers
- {ruby Ruby::GDB::object-inspection Object inspection} for examining heap objects
- {ruby Ruby::GDB::stack-inspection Stack inspection} for understanding object references


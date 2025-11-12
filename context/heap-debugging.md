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

### Finding All Fibers

The most common use case - find every fiber in the application:

~~~
(gdb) rb-scan-fibers
Scanning 1250 heap pages...
  Checked 45000 objects, found 5 fiber(s)...
  Found fiber #1 at 0x7f8a1c800000
  Found fiber #2 at 0x7f8a1c800100
  ...
Scan complete: checked 67890 objects

Found 12 fiber(s):
...
~~~

This iterates through all heap pages and identifies fiber objects by their type metadata.

### How Heap Scanning Works

The scanner:

1. Accesses `ruby_current_vm_ptr->gc->objspace`
2. Iterates through `heap_pages->sorted->data[]`
3. For each page, checks `total_slots` objects
4. Identifies objects by their `flags` field
5. Filters for specific types (e.g., T_DATA with `fiber_data_type`)

### Performance Considerations

Heap scanning can be slow in large applications:

~~~
Scanning 5000 heap pages...
  Checked 100000 objects, found 50 fiber(s)...
  Checked 200000 objects, found 125 fiber(s)...
  ...
~~~

Progress updates appear every 10,000 objects. For faster subsequent access, use caching:

~~~
(gdb) rb-scan-fibers --cache
... (scan happens) ...
Saved 125 fiber address(es) to fibers.json

# Later (even in a new GDB session):
(gdb) rb-scan-fibers --cache
Loaded 125 fiber address(es) from fibers.json
Successfully reconstructed 125 fiber object(s)
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
(gdb) rb-scan-fibers --cache fibers.json    # Scan once
(gdb) rb-fiber 5                            # Use cached results
(gdb) rb-fiber-bt 5
...
# Later in session:
(gdb) rb-fiber 10                           # Still using cache
~~~

### Limit Scans in Production

For production core dumps with millions of objects:

~~~
(gdb) rb-scan-fibers 20         # Find first 20 fibers only
~~~

Often you only need a few fibers to diagnose issues.

### Use Object Inspection Together

Combine heap scanning with object inspection:

~~~
(gdb) rb-scan-fibers
Fiber #5 has exception: IOError

(gdb) rb-fiber 5
(gdb) set $ec = ...             # (shown in output)
(gdb) rb-object-print $ec->errinfo --depth 3
~~~

## Common Pitfalls

### Stale Cache Files

If you load a cache from a different core dump:

~~~
(gdb) rb-scan-fibers --cache
Loaded 125 fiber address(es) from fibers.json
Warning: Could not access fiber at 0x7f8a1c800500
Warning: Could not access fiber at 0x7f8a1c800600
...
~~~

Delete the cache and rescan:

~~~ bash
$ rm fibers.json
~~~

### Scanning Uninitialized VM

If you scan too early during Ruby initialization:

~~~
(gdb) rb-scan-fibers
Error: ruby_current_vm_ptr is NULL
Make sure Ruby is fully initialized and the process is running.
~~~

Set a breakpoint after VM initialization:

~~~
(gdb) break rb_vm_exec
(gdb) run
(gdb) rb-scan-fibers           # Now works
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


# Ruby::GDB

Ruby debugging extensions for GDB, providing commands for inspecting Ruby objects, fibers, and VM internals.

[![Development Status](https://github.com/socketry/ruby-gdb/workflows/Test/badge.svg)](https://github.com/socketry/ruby-gdb/actions?workflow=Test)

## Features

### Object Inspection (`object.py`)

  - `rb-object-print <expression> [--depth N] [--debug]` - Recursively print Ruby hashes, arrays, and structs
      - Supports immediate values (Fixnum, Qnil, Qtrue, Qfalse)
      - Deep inspection of Hash objects (ST table and AR table)
      - Deep inspection of Array objects (embedded and heap)
      - Deep inspection of Struct objects
      - Configurable depth for recursive printing
      - Debug mode for troubleshooting

### Fiber Debugging (`fiber.py`)

  - `rb-scan-fibers [limit] [--cache [file]]` - Scan heap and list all Ruby fibers
  - `rb-fiber <index>` - Inspect cached fiber by index
  - `rb-fiber-bt <index|addr>` - Print Ruby backtrace for a fiber
  - `rb-fiber-vm-stack <index>` - Show VM stack info
  - `rb-fiber-vm-frames <index>` - Walk VM control frames (CFPs)
  - `rb-fiber-stack-top <index> [count]` - Show values on top of VM stack
  - `rb-fiber-c-stack <index>` - Show C/machine stack info
  - `rb-fiber-switch <index>` - Switch GDB to fiber's stack (works in core dumps\!)
  - `rb-diagnose-exit` - Diagnose why Ruby exited (exceptions/signals)
  - And more...

## Installation

### Using Bake

``` bash
# Install to XDG data directory (~/.local/share/gdb/ruby)
bake ruby:gdb:install

# Install to custom prefix
bake ruby:gdb:install prefix=/usr/local

# Show installation info
bake ruby:gdb:info

# Uninstall
bake ruby:gdb:uninstall
```

### Manual Installation

1.  Copy the Python scripts to a location GDB can find:
    
    ``` bash
    mkdir -p ~/.local/share/gdb/ruby
    cp data/ruby/gdb/*.py ~/.local/share/gdb/ruby/
    ```

2.  Add to your `~/.gdbinit`:
    
    ``` gdb
    source ~/.local/share/gdb/ruby/init.gdb
    ```

## Usage

### Basic Object Inspection

``` gdb
# In GDB, after hitting a breakpoint in Ruby code:
(gdb) rb-object-print $ec->cfp->sp[-1]  # Print top of stack
(gdb) rb-object-print $errinfo           # Print exception object
(gdb) rb-object-print 0x7f7a12345678     # Print object at address
(gdb) rb-object-print $var --depth 3     # Print with depth 3
(gdb) rb-object-print $var --debug       # Enable debug output
```

### Fiber Debugging

``` gdb
# Scan for all fibers
(gdb) rb-scan-fibers

# Inspect specific fiber
(gdb) rb-fiber 0
(gdb) rb-fiber-bt 0

# Switch to fiber's stack (even in core dumps!)
(gdb) rb-fiber-switch 290
(gdb) bt  # Now shows fiber's C backtrace

# Diagnose crashes
(gdb) rb-diagnose-exit
```

## Development

### Running Tests

``` bash
# Run all tests (compare against snapshots)
bundle exec sus

# Update snapshots (when GDB output changes)
UPDATE_SNAPSHOTS=1 bundle exec sus
```

### Testing Approach

Tests use a snapshot-based approach:

1.  Each test has a `.gdb` script in `fixtures/ruby/gdb/`
2.  On first run, the test generates a `.txt` snapshot file with expected output
3.  Subsequent runs compare actual output against the snapshot
4.  Run with `UPDATE_SNAPSHOTS=1` to regenerate snapshots after changes

### Testing Requirements

  - GDB must be installed
  - Tests automatically normalize GDB output to be version-independent

## Requirements

  - Ruby 3.0+
  - GDB with Python support
  - Ruby built with debug symbols (recommended)

## Contributing

We welcome contributions to this project.

1.  Fork it.
2.  Create your feature branch (`git checkout -b my-new-feature`).
3.  Commit your changes (`git commit -am 'Add some feature'`).
4.  Push to the branch (`git push origin my-new-feature`).
5.  Create new Pull Request.

### Developer Certificate of Origin

In order to protect users of this project, we require all contributors to comply with the [Developer Certificate of Origin](https://developercertificate.org/). This ensures that all contributions are properly licensed and attributed.

### Community Guidelines

This project is best served by a collaborative and respectful environment. Treat each other professionally, respect differing viewpoints, and engage constructively. Harassment, discrimination, or harmful behavior is not tolerated. Communicate clearly, listen actively, and support one another. If any issues arise, please inform the project maintainers.

## See Also

  - [GDB Python API Documentation](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Python-API.html)
  - [Ruby VM Internals](https://docs.ruby-lang.org/en/master/extension_rdoc.html)

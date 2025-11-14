# Toolbox

Ruby debugging toolbox for GDB and LLDB, providing commands for inspecting Ruby objects, fibers, and VM internals across multiple debuggers.

[![Development Status](https://github.com/socketry/toolbox/workflows/Test/badge.svg)](https://github.com/socketry/toolbox/actions?workflow=Test)

## Features

  - **Multi-debugger support**: Works with both GDB and LLDB through a unified abstraction layer.
  - **Object inspection**: Pretty-print Ruby objects, hashes, arrays, and complex structures.
  - **Fiber debugging**: Navigate and inspect Ruby fibers with full backtraces.
  - **Heap scanning**: Search the Ruby heap for objects and diagnose memory issues.
  - **Stack inspection**: Examine both Ruby VM stacks and native C stacks.
  - **Easy installation**: Simple bake tasks for both GDB and LLDB.

## Usage

Please see the [project documentation](https://socketry.github.io/toolbox/) for more details.

  - [Getting Started](https://socketry.github.io/toolbox/guides/getting-started/index) - This guide explains how to install and use Toolbox for debugging Ruby programs and core dumps with GDB or LLDB.

  - [Object Inspection](https://socketry.github.io/toolbox/guides/object-inspection/index) - This guide explains how to use `rb-print` to inspect Ruby objects, hashes, arrays, and structs in GDB.

  - [Stack Inspection](https://socketry.github.io/toolbox/guides/stack-inspection/index) - This guide explains how to inspect both Ruby VM stacks and native C stacks when debugging Ruby programs.

  - [Fiber Debugging](https://socketry.github.io/toolbox/guides/fiber-debugging/index) - This guide explains how to debug Ruby fibers using GDB, including inspecting fiber state, backtraces, and switching between fiber contexts.

  - [Heap Debugging](https://socketry.github.io/toolbox/guides/heap-debugging/index) - This guide explains how to navigate Ruby's heap to find objects, diagnose memory issues, and understand object relationships.

## Releases

Please see the [project releases](https://socketry.github.io/toolbox/releases/index) for all releases.

### v0.2.0

  - Introduce support for `lldb` using debugger shims.

### v0.1.0

  - Initial release.

## See Also

  - [GDB Python API Documentation](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Python-API.html)
  - [LLDB Python API Documentation](https://lldb.llvm.org/use/python-reference.html)
  - [Ruby VM Internals](https://docs.ruby-lang.org/en/master/extension_rdoc.html)

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

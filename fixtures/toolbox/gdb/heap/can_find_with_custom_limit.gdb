# Test scanning with custom limit

# Reduce GDB verbosity
set verbose off
set confirm off
set pagination off
set print thread-events off

source data/toolbox/init.py

# Enable pending breakpoints
set breakpoint pending on

# Break at rb_f_puts after the strings are created
break rb_f_puts
run

echo ===RUBY-GDB-OUTPUT-START===\n
rb-heap-scan --type RUBY_T_STRING --limit 15
echo ===RUBY-GDB-OUTPUT-END===\n

quit

# Test rb-fiber-scan-switch command

# Reduce GDB verbosity
set verbose off
set confirm off
set pagination off
set print thread-events off

source data/toolbox/init.py

# Enable pending breakpoints
set breakpoint pending on

# Break at rb_f_puts after the fiber is created
break rb_f_puts
run

# Scan for fibers first
echo ===RUBY-GDB-OUTPUT-START===\n
rb-fiber-scan-heap 1
echo \n
rb-fiber-scan-switch 0
echo ===RUBY-GDB-OUTPUT-END===\n

quit

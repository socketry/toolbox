# Test rb-fiber-scan-heap command

# Reduce GDB verbosity
set verbose off
set confirm off
set pagination off
set print thread-events off

source data/toolbox/init.py

# Enable pending breakpoints
set breakpoint pending on

# Break at rb_f_puts after the fiber is created and suspended
break rb_f_puts
run

# Get the fiber VALUE from argv[0]
set $fiber_value = argv[0]

# Now scan the heap for fibers
# We should find at least 1 fiber (the one we created)
echo ===TOOLBOX-OUTPUT-START===\n
rb-fiber-scan-heap 1
echo ===TOOLBOX-OUTPUT-END===\n

quit

# Test cache save and load

# Reduce GDB verbosity
set verbose off
set confirm off
set pagination off
set print thread-events off

source data/toolbox/init.py

# Enable pending breakpoints
set breakpoint pending on

break rb_f_puts
run

# Save fibers to cache
echo ===TOOLBOX-OUTPUT-START===\n
rb-fiber-scan-heap --cache test_fibers.json
echo \n
echo ===TOOLBOX-OUTPUT-END===\n

quit

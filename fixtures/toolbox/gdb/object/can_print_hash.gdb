# Test printing a Ruby hash using a global variable

# Reduce GDB verbosity
set verbose off
set confirm off
set pagination off
set print thread-events off

source data/toolbox/init.py

# Enable pending breakpoints (for when symbols load from shared libraries)
set breakpoint pending on

# Break at the point where the global variable is set
break rb_f_puts
run

# Get the hash from argv[0] - the first argument to puts
# argv is a pointer to an array of VALUE, so argv[0] is the hash
set $hash = argv[0]

# Print the hash
echo ===TOOLBOX-OUTPUT-START===\n
rb-print $hash
echo ===TOOLBOX-OUTPUT-END===\n

quit



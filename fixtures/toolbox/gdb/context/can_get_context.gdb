# Test rb-context command

source data/toolbox/init.py

# Break at rb_f_puts in inner_method
set breakpoint pending on
b rb_f_puts
run

# Get current execution context and print info
echo ===TOOLBOX-OUTPUT-START===\n
rb-context
echo ===TOOLBOX-OUTPUT-END===\n

quit


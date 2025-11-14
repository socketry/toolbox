# Test rb-context command with exception

source data/toolbox/init.py

# Break at rb_f_puts in the rescue block
# At this point the exception should be in errinfo
set breakpoint pending on
b rb_f_puts
run

# Get current execution context - should show exception
echo ===TOOLBOX-OUTPUT-START===\n
rb-context
echo ===TOOLBOX-OUTPUT-END===\n

quit


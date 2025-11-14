source data/toolbox/init.py

# Break at rb_f_puts in inner_method (make pending to handle lazy loading)
set breakpoint pending on
b rb_f_puts
run

# Print the Ruby stack trace
echo ===TOOLBOX-OUTPUT-START===\n
rb-stack-trace
echo ===TOOLBOX-OUTPUT-END===\n

quit

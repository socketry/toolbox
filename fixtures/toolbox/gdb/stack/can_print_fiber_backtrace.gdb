# Test rb-stack-trace command with a fiber

source data/toolbox/init.py

# Break at rb_f_puts in the fiber (make pending to handle lazy loading)
set breakpoint pending on
break rb_f_puts
run

# Print the Ruby stack trace for the fiber
python print("===TOOLBOX-OUTPUT-START===")
rb-stack-trace
python print("===TOOLBOX-OUTPUT-END===")

quit

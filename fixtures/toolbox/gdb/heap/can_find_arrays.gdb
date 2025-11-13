# Test scanning for T_ARRAY objects on the heap

source data/toolbox/init.py

set breakpoint pending on
break ruby_process_options

run
# Create some arrays
call (void)rb_eval_string("[1, 2]; [3, 4]; [5, 6]")
echo ===TOOLBOX-OUTPUT-START===\n
rb-heap-scan --type RUBY_T_ARRAY --limit 3
echo ===TOOLBOX-OUTPUT-END===\n
quit

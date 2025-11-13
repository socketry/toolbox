# Test scanning for T_STRING objects on the heap

source data/toolbox/init.py

set breakpoint pending on
break ruby_process_options

run
# Create some strings
call (void)rb_eval_string("'test1'; 'test2'; 'test3'; 'test4'; 'test5'")
echo ===RUBY-GDB-OUTPUT-START===\n
rb-heap-scan --type RUBY_T_STRING --limit 5
echo ===RUBY-GDB-OUTPUT-END===\n
quit

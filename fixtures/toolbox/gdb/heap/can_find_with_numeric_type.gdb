# Test scanning with numeric type constant

source data/toolbox/init.py

set breakpoint pending on
break ruby_process_options

run
# Create some hashes (T_HASH = 0x0b)
call (void)rb_eval_string("{a: 1}; {b: 2}; {c: 3}")
echo ===TOOLBOX-OUTPUT-START===\n
rb-heap-scan --type 0x0b --limit 3
echo ===TOOLBOX-OUTPUT-END===\n
quit

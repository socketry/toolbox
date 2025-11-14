# Test printing float values

source data/toolbox/init.py

set breakpoint pending on
break ruby_process_options

run
set $value = rb_eval_string("[3.14, -2.718, 0.0]")
echo ===TOOLBOX-OUTPUT-START===\n
rb-print $value
echo ===TOOLBOX-OUTPUT-END===\n
quit

# Test printing float values

source data/toolbox/init.py

set breakpoint pending on
break ruby_process_options

run
set $value = rb_eval_string("[3.14, -2.718, 0.0]")
echo ===RUBY-GDB-OUTPUT-START===\n
rb-object-print $value
echo ===RUBY-GDB-OUTPUT-END===\n
quit

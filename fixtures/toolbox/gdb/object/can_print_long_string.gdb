# Test printing long heap-allocated string

source data/toolbox/init.py

set breakpoint pending on
break ruby_process_options

run
set $value = rb_eval_string("'This is a much longer string that will be heap allocated instead of embedded in the RString structure'")
echo ===TOOLBOX-OUTPUT-START===\n
rb-print $value
echo ===TOOLBOX-OUTPUT-END===\n
quit

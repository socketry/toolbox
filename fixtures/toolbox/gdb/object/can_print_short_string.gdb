# Test printing short embedded string

source data/toolbox/init.py

set breakpoint pending on
break ruby_process_options

run
set $value = rb_eval_string("'Hello'")
echo ===TOOLBOX-OUTPUT-START===\n
rb-print $value
echo ===TOOLBOX-OUTPUT-END===\n
quit

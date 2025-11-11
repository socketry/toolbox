# Test printing short symbol

source data/ruby/gdb/init.py

set breakpoint pending on
break ruby_process_options

run
set $value = rb_eval_string(":hello")
echo ===RUBY-GDB-OUTPUT-START===\n
rb-object-print $value
echo ===RUBY-GDB-OUTPUT-END===\n
quit

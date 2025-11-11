# Test printing short embedded string

source data/ruby/gdb/init.py

set breakpoint pending on
break ruby_process_options

run
set $value = rb_eval_string("'Hello'")
echo ===RUBY-GDB-OUTPUT-START===\n
rb-object-print $value
echo ===RUBY-GDB-OUTPUT-END===\n
quit

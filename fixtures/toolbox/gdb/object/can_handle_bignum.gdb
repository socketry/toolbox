# Test printing bignum values

source data/toolbox/init.py

set breakpoint pending on
break ruby_process_options

run
set $value = rb_eval_string("[123456789012345678901234567890, -999999999999999999999999999999]")
echo ===RUBY-GDB-OUTPUT-START===\n
rb-object-print $value
echo ===RUBY-GDB-OUTPUT-END===\n
quit

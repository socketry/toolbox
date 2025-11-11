# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

hash = {a: 1, b: 2, c: 3}

# Pass the hash directly to puts (not .inspect)
# This way the hash VALUE is the argument to rb_f_puts
puts hash

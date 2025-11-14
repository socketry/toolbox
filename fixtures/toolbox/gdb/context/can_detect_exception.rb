# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

def method_with_error
	# This will raise an exception
	raise StandardError, "Test exception"
rescue => e
	# Re-raise to get into exception handling state
	raise
end

def outer_method
	method_with_error
rescue => e
	# We'll break here where exception has been caught
	# At this point, errinfo should still contain the exception
	puts "Caught: #{e.message}"
end

outer_method


# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

def inner_method
	# This is where we'll break and test rb-context
	puts "In inner method"
end

def middle_method
	inner_method
end

def outer_method
	middle_method
end

outer_method


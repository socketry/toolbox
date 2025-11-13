# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

fiber = Fiber.new do
	raise "Test exception in fiber"
end

# Start the fiber so it has state
begin
	fiber.resume
rescue => e
	# Expected
end

puts "Fiber created"

# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

fiber = Fiber.new do
	Fiber.yield "yielded"
end

fiber.resume

puts "Fiber ready"

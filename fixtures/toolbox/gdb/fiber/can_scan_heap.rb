# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

fiber = Fiber.new do
	# Fiber body - we'll suspend here
	Fiber.yield :suspended
end

# Start the fiber so it gets suspended
fiber.resume

# At this point, we have a fiber in SUSPENDED state
# that rb-fiber-scan-heap should be able to find
# Pass the fiber to puts so we can access it in GDB
puts fiber

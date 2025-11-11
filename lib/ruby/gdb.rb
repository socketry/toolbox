# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

require_relative "gdb/version"

module Ruby
	module GDB
		# Path to the GDB extension scripts.
		def self.data_path
			File.expand_path("../../data", __dir__)
		end
		
		# Path to the object.py script.
		def self.object_script_path
			File.join(data_path, "ruby", "gdb", "object.py")
		end
		
		# Path to the fiber.py script.
		def self.fiber_script_path
			File.join(data_path, "ruby", "gdb", "fiber.py")
		end
		
		# Get the XDG data home directory.
		def self.xdg_data_home
			ENV["XDG_DATA_HOME"] || File.join(Dir.home, ".local", "share")
		end
		
		# Installation path for GDB scripts.
		def self.install_path(prefix: nil)
			if prefix
				File.join(prefix, "share", "gdb", "ruby")
			else
				File.join(xdg_data_home, "gdb", "ruby")
			end
		end
	end
end

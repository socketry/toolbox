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
		
		# Path to the init.py script.
		def self.init_script_path
			File.join(data_path, "ruby", "gdb", "init.py")
		end
		
		
		
	end
end

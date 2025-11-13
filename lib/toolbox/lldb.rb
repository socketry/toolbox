# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

require_relative "../toolbox"

module Toolbox
	module LLDB
		# Path to the unified toolbox extensions.
		def self.data_path
			File.join(Toolbox.data_path, "toolbox")
		end
		
		# Path to the init.py script (shared with GDB).
		def self.init_script_path
			File.join(data_path, "init.py")
		end
	end
end


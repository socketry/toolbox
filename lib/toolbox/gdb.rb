# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

require_relative "../toolbox"

module Toolbox
	module GDB
		# Path to the toolbox data directory.
		def self.data_path
			Toolbox.data_path
		end
		
		# Path to the init script for GDB.
		def self.init_script_path
			File.join(data_path, "toolbox", "init.py")
		end
	end
end

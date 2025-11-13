# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

require_relative "../toolbox"
require "fileutils"
require "open3"
require "tempfile"

module Toolbox
	module Fixtures
		# Get the base fixtures directory
		def fixtures_path
			File.expand_path("../../../fixtures/toolbox", __dir__)
		end
		
		# Get subdirectory for specific debugger (gdb or lldb)
		def fixtures_path_for(debugger)
			File.join(fixtures_path, debugger.to_s)
		end
	end
end


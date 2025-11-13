# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

require_relative "toolbox/version"

module Toolbox
	# Path to the toolbox data directory.
	def self.data_path
		File.expand_path("../data", __dir__)
	end
end


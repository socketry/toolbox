# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

require "toolbox/gdb"
require "toolbox/test_cases"

describe Toolbox::GDB do
	it "has data path" do
		expect(File.directory?(Toolbox::GDB.data_path)).to be == true
	end
	
	it "has init script path" do
		path = Toolbox::GDB.init_script_path
		expect(path).to be_a(String)
		expect(File.exist?(path)).to be == true
	end
	
	describe "test cases" do
		def run_test_case(test_case)
			command = [
				"gdb",
				"--batch", "-x", test_case[:input_path],
				"--args", RbConfig.ruby
			]
			
			if script_path = test_case[:script_path]
				command << script_path
			end
			
			test_case[:command] = command
			
			return Open3.capture2(*command)
		end
		
		with "object" do
			include_context Toolbox::TestCases, "gdb/object", "*.gdb"
		end
		
		with "fiber" do
			include_context Toolbox::TestCases, "gdb/fiber", "*.gdb"
		end
		
		with "heap" do
			include_context Toolbox::TestCases, "gdb/heap", "*.gdb"
		end
		
		with "stack" do
			include_context Toolbox::TestCases, "gdb/stack", "*.gdb"
		end
		
		with "context" do
			include_context Toolbox::TestCases, "gdb/context", "*.gdb"
		end
	end
end

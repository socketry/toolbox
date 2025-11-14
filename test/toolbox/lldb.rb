# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

require "toolbox/lldb"
require "toolbox/test_cases"

describe Toolbox::LLDB do
	it "has data path" do
		expect(File.directory?(Toolbox::LLDB.data_path)).to be == true
	end
	
	it "has init script path" do
		path = Toolbox::LLDB.init_script_path
		expect(path).to be_a(String)
		expect(File.exist?(path)).to be == true
	end
	
	describe "test cases" do
		def run_test_case(test_case)
			command = [
				"lldb",
				"--batch", "--source", test_case[:input_path], "--source-quietly",
				RbConfig.ruby
			]
			
			if script_path = test_case[:script_path]
				command << "--" << script_path
			end
			
			test_case[:command] = command
			
			return Open3.capture2(*command)
		end
		
		with "object" do
			include_context Toolbox::TestCases, "lldb/object", "*.lldb"
		end
		
		with "fiber" do
			include_context Toolbox::TestCases, "lldb/fiber", "*.lldb"
		end
		
		with "heap" do
			include_context Toolbox::TestCases, "lldb/heap", "*.lldb"
		end
		
		with "stack" do
			include_context Toolbox::TestCases, "lldb/stack", "*.lldb"
		end
		
		with "context" do
			include_context Toolbox::TestCases, "lldb/context", "*.lldb"
		end
	end
end

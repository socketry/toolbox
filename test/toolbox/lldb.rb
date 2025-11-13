# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

require "toolbox"
require "toolbox/lldb"
require "sus"

describe Toolbox::LLDB do
	it "has data path" do
		expect(File.directory?(Toolbox::LLDB.data_path)).to be == true
	end
	
	it "has init script path" do
		path = Toolbox::LLDB.init_script_path
		expect(path).to be_a(String)
		expect(File.exist?(path)).to be == true
	end
	
	it "shares the same init.py as GDB" do
		gdb_init = Toolbox::GDB.init_script_path
		lldb_init = Toolbox::LLDB.init_script_path
		
		expect(gdb_init).to be == lldb_init
	end
end

describe "LLDB initialization" do
	it "can load init.py script" do
		init_path = Toolbox::LLDB.init_script_path
		
		expect(File.exist?(init_path)).to be == true
		expect(File.readable?(init_path)).to be == true
		
		# Check that it's valid Python
		content = File.read(init_path)
		expect(content).to include("import debugger")
		expect(content).to include("Ruby Toolbox")
	end
	
	it "has debugger abstraction available" do
		debugger_py = File.join(Toolbox::LLDB.data_path, "debugger.py")
		
		expect(File.exist?(debugger_py)).to be == true
		
		content = File.read(debugger_py)
		expect(content).to include("import lldb")
		expect(content).to include("DEBUGGER_NAME")
	end
	
	it "has LLDB backend available" do
		lldb_backend = File.join(Toolbox::LLDB.data_path, "debugger", "lldb.py")
		
		expect(File.exist?(lldb_backend)).to be == true
		
		content = File.read(lldb_backend)
		expect(content).to include("class Value:")
		expect(content).to include("class Type:")
		expect(content).to include("class Command:")
	end
end

# Integration test - only runs if LLDB is available
describe "LLDB integration" do
	let(:init_script) {Toolbox::LLDB.init_script_path}
	
	it "can load extensions in LLDB" do
		# Try to load the init script in LLDB
		cmd = [
			"lldb",
			"--batch",
			"-o", "command script import #{init_script}",
			"-o", "quit"
		]
		
		require "open3"
		stdout, stderr, status = Open3.capture3(*cmd)
		output = stdout + stderr
		
		# Should see our initialization message
		expect(output).to include("Ruby Toolbox")
		
		# Should not have errors
		expect(output).not_to include("Error")
		expect(output).not_to include("Traceback")
		
		# Check exit status
		expect(status.success?).to be == true
	end
end


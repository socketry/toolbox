# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

require "toolbox"
require "toolbox/gdb"
require "toolbox/lldb"
require "toolbox/lldb/fixtures"
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

# Integration test - only runs if LLDB is available
describe "LLDB integration" do
	it "can load extensions in LLDB" do
		# Try to load the init script in LLDB
		init_script = Toolbox::LLDB.init_script_path
		cmd = [
			"lldb",
			"--batch",
			"-o", "command script import #{init_script}",
			"-o", "quit"
		]
		
		require "open3"
		stdout, stderr, status = Open3.capture3(*cmd)
		output = stdout + stderr
		
		# Should not have errors (loads silently)
		expect(output).not.to be(:include?, "Error")
		expect(output).not.to be(:include?, "Traceback")
		
		# Check exit status
		expect(status.success?).to be == true
	end
end

describe "rb-object-print command" do
	include Toolbox::LLDB::Fixtures
	
	# Automatically discover all test cases from object/ subdirectory
	Toolbox::LLDB::Fixtures.test_cases("object") do |name, test_case|
		it name, unique: test_case[:name] do
			result = run_test_case(test_case, update_snapshots: ENV["UPDATE_SNAPSHOTS"])
			
			if result[:created]
				# First run - snapshot was created
				expect(result[:success?]).to be == true
			elsif result[:updated]
				# Snapshot was updated
				expect(result[:success?]).to be == true
			elsif result[:success?]
				# Snapshot matches
				expect(result[:match]).to be == true
			else
				# Snapshot mismatch - show diff
				puts "\n" + "=" * 80
				puts "SNAPSHOT MISMATCH: #{test_case[:name]}"
				puts "=" * 80
				puts "\nExpected output:"
				puts result[:expected]
				puts "\nActual output:"
				puts result[:output]
				
				if result[:raw_output]
					puts "\nRaw LLDB output (unfiltered):"
					puts result[:raw_output]
				end
				
				puts "\nDiff (line by line):"
				result[:diff]&.each do |d|
					puts "  Line #{d[:line]}:"
					puts "    Expected: #{d[:expected].inspect}"
					puts "    Actual:   #{d[:actual].inspect}"
				end
				puts "\nTo update snapshot, run:"
				puts "  UPDATE_SNAPSHOTS=1 bundle exec sus"
				puts "=" * 80
				
				expect(result[:success?]).to be == true
			end
		end
	end
end

describe "rb-fiber-scan-heap command" do
	include Toolbox::LLDB::Fixtures
	
	# Automatically discover all test cases from fiber/ subdirectory
	Toolbox::LLDB::Fixtures.test_cases("fiber") do |name, test_case|
		it name, unique: test_case[:name] do
			result = run_test_case(test_case, update_snapshots: ENV["UPDATE_SNAPSHOTS"])
			
			if result[:created]
				# First run - snapshot was created
				expect(result[:success?]).to be == true
			elsif result[:updated]
				# Snapshot was updated
				expect(result[:success?]).to be == true
			elsif result[:success?]
				# Snapshot matches
				expect(result[:match]).to be == true
			else
				# Snapshot mismatch - show diff
				puts "\n" + "=" * 80
				puts "SNAPSHOT MISMATCH: #{test_case[:name]}"
				puts "=" * 80
				puts "\nExpected output:"
				puts result[:expected]
				puts "\nActual output:"
				puts result[:output]
				
				if result[:raw_output]
					puts "\nRaw LLDB output (unfiltered):"
					puts result[:raw_output]
				end
				
				puts "\nDiff (line by line):"
				result[:diff]&.each do |d|
					puts "  Line #{d[:line]}:"
					puts "    Expected: #{d[:expected].inspect}"
					puts "    Actual:   #{d[:actual].inspect}"
				end
				puts "\nTo update snapshot, run:"
				puts "  UPDATE_SNAPSHOTS=1 bundle exec sus"
				puts "=" * 80
				
				expect(result[:success?]).to be == true
			end
		end
	end
end

describe "rb-heap-scan command" do
	include Toolbox::LLDB::Fixtures
	
	# Automatically discover all test cases from heap/ subdirectory
	Toolbox::LLDB::Fixtures.test_cases("heap") do |name, test_case|
		it name, unique: test_case[:name] do
			result = run_test_case(test_case, update_snapshots: ENV["UPDATE_SNAPSHOTS"])
			
			if result[:created]
				# First run - snapshot was created
				expect(result[:success?]).to be == true
			elsif result[:updated]
				# Snapshot was updated
				expect(result[:success?]).to be == true
			elsif result[:success?]
				# Snapshot matches
				expect(result[:match]).to be == true
			else
				# Snapshot mismatch - show diff
				puts "\n" + "=" * 80
				puts "SNAPSHOT MISMATCH: #{test_case[:name]}"
				puts "=" * 80
				puts "\nExpected output:"
				puts result[:expected]
				puts "\nActual output:"
				puts result[:output]
				
				if result[:raw_output]
					puts "\nRaw LLDB output (unfiltered):"
					puts result[:raw_output]
				end
				
				puts "\nDiff (line by line):"
				result[:diff]&.each do |d|
					puts "  Line #{d[:line]}:"
					puts "    Expected: #{d[:expected].inspect}"
					puts "    Actual:   #{d[:actual].inspect}"
				end
				puts "\nTo update snapshot, run:"
				puts "  UPDATE_SNAPSHOTS=1 bundle exec sus"
				puts "=" * 80
				
				expect(result[:success?]).to be == true
			end
		end
	end
end


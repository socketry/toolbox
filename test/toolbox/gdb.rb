# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

require "toolbox"
require "toolbox/gdb"
require "toolbox/gdb/fixtures"
require "sus"

describe Toolbox::GDB do
	include Toolbox::GDB::Fixtures
	
	it "has data path" do
		expect(File.directory?(Toolbox::GDB.data_path)).to be == true
	end
	
	it "has init script path" do
		path = Toolbox::GDB.init_script_path
		expect(path).to be_a(String)
		expect(File.exist?(path)).to be == true
	end
end

describe "rb-object-print command" do
	include Toolbox::GDB::Fixtures
	
	# Automatically discover all test cases from object/ subdirectory
	Toolbox::GDB::Fixtures.test_cases("object") do |name, test_case|
		it name, unique: test_case do
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
				puts "SNAPSHOT MISMATCH: #{test_case}"
				puts "=" * 80
				puts "\nExpected output:"
				puts result[:expected]
				puts "\nActual output:"
				puts result[:output]
				
				if result[:raw_output]
					puts "\nRaw GDB output (unfiltered):"
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
	include Toolbox::GDB::Fixtures
	
	# Automatically discover all test cases from fiber/ subdirectory
	Toolbox::GDB::Fixtures.test_cases("fiber") do |name, test_case|
		it name, unique: test_case do
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
				puts "SNAPSHOT MISMATCH: #{test_case}"
				puts "=" * 80
				puts "\nExpected output:"
				puts result[:expected]
				puts "\nActual output:"
				puts result[:output]
				
				if result[:raw_output]
					puts "\nRaw GDB output (unfiltered):"
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
	include Toolbox::GDB::Fixtures
	
	# Automatically discover all test cases from heap/ subdirectory
	Toolbox::GDB::Fixtures.test_cases("heap") do |name, test_case|
		it name, unique: test_case do
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
				puts "SNAPSHOT MISMATCH: #{test_case}"
				puts "=" * 80
				puts "\nExpected output:"
				puts result[:expected]
				puts "\nActual output:"
				puts result[:output]
				
				if result[:raw_output]
					puts "\nRaw GDB output (unfiltered):"
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


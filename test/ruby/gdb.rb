# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

require "ruby/gdb"
require "ruby/gdb/fixtures"
require "sus"

describe Ruby::GDB do
	include Ruby::GDB::Fixtures
	
	it "has a version number" do
		expect(Ruby::GDB::VERSION).to be_a(String)
	end
	
	it "has data path" do
		expect(File.directory?(Ruby::GDB.data_path)).to be == true
	end
end

describe "rb-object-print command" do
	include Ruby::GDB::Fixtures
	
	# Automatically discover all test cases from object/ subdirectory
	Ruby::GDB::Fixtures.test_cases("object") do |name, test_case|
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
	include Ruby::GDB::Fixtures
	
	# Automatically discover all test cases from fiber/ subdirectory
	Ruby::GDB::Fixtures.test_cases("fiber") do |name, test_case|
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
	include Ruby::GDB::Fixtures
	
	# Automatically discover all test cases from heap/ subdirectory
	Ruby::GDB::Fixtures.test_cases("heap") do |name, test_case|
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

describe "Installation" do
	include Ruby::GDB::Fixtures
	
	it "has init script path" do
		path = Ruby::GDB.init_script_path
		expect(path).to be_a(String)
		expect(File.exist?(path)).to be == true
	end
	
	it "has data path" do
		path = Ruby::GDB.data_path
		expect(path).to be_a(String)
		expect(Dir.exist?(path)).to be == true
	end
end

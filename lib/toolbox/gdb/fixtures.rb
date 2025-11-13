# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

require_relative "../../toolbox"
require_relative "../../toolbox/fixtures"
require "fileutils"
require "open3"
require "tempfile"

module Toolbox
	module GDB
		module Fixtures
			include Toolbox::Fixtures
			
			# Get the fixtures directory for GDB tests
			def fixtures_path
				fixtures_path_for(:gdb)
			end
			
			# Discover test cases from a subdirectory
			# @param subdir [String] Subdirectory name (e.g., "object", "fiber", "heap")
			# @yield [name, test_case] Block to call for each test case
			def self.test_cases(subdir)
				fixtures_dir = File.expand_path("../../../fixtures/toolbox/gdb/#{subdir}", __dir__)
				return unless Dir.exist?(fixtures_dir)
				
				# Find all .gdb script files
				Dir.glob(File.join(fixtures_dir, "*.gdb")).sort.each do |gdb_script|
					base_name = File.basename(gdb_script, ".gdb")
					
					# Expected .txt snapshot file
					txt_file = gdb_script.sub(/\.gdb$/, ".txt")
					
					# Optional .rb Ruby script (for setting up test state)
					rb_file = gdb_script.sub(/\.gdb$/, ".rb")
					rb_file = File.exist?(rb_file) ? rb_file : nil
					
					test_case = {
						name: "#{subdir}/#{base_name}",
						gdb_script: gdb_script,
						ruby_script: rb_file,
						snapshot_file: txt_file
					}
					
					yield base_name, test_case
				end
			end
			
			# Run a test case
			# @param test_case [Hash] Test case configuration
			# @param update_snapshots [Boolean] If true, update snapshot files
			# @return [Hash] Result with :success?, :output, :expected, etc.
			def run_test_case(test_case, update_snapshots: false)
				gdb_script = test_case[:gdb_script]
				ruby_script = test_case[:ruby_script]
				snapshot_file = test_case[:snapshot_file]
				
				# If there's a Ruby script, run it with GDB
				if ruby_script
					result = run_ruby_with_gdb(ruby_script, gdb_script)
				else
					# Just run the GDB script
					result = run_gdb_script(gdb_script)
				end
				
				output = result[:output]
				raw_output = result[:raw_output]
				
				# Check if snapshot exists
				if File.exist?(snapshot_file)
					expected = File.read(snapshot_file)
					
					if output == expected
						# Match!
						return {success?: true, match: true, output: output, expected: expected}
					elsif update_snapshots
						# Update the snapshot
						File.write(snapshot_file, output)
						return {success?: true, updated: true, output: output, expected: expected}
					else
						# Mismatch - return details for debugging
						diff = compute_diff(expected, output)
						return {
							success?: false,
							match: false,
							output: output,
							raw_output: raw_output,
							expected: expected,
							diff: diff
						}
					end
				else
					# No snapshot yet - create it if update mode is enabled
					if update_snapshots
						File.write(snapshot_file, output)
						return {success?: true, created: true, output: output}
					else
						return {
							success?: false,
							error: "No snapshot file found: #{snapshot_file}",
							output: output
						}
					end
				end
			end
			
			private
			
			# Run a Ruby script under GDB with a GDB script
			def run_ruby_with_gdb(ruby_script, gdb_script)
				# Create a temporary GDB command file that:
				# 1. Loads the Toolbox extensions
				# 2. Runs the Ruby script
				# 3. Executes the test GDB commands
				# 4. Quits
				temp_gdb = Tempfile.new(["test", ".gdb"])
				begin
					temp_gdb.write("source #{Toolbox::GDB.init_script_path}\n")
					temp_gdb.write("run #{ruby_script}\n")
					temp_gdb.write(File.read(gdb_script))
					temp_gdb.write("\nquit\n")
					temp_gdb.close
					
					# Run GDB in batch mode
					cmd = ["gdb", "--batch", "--command=#{temp_gdb.path}", "ruby"]
					stdout, stderr, status = Open3.capture3(*cmd)
					
					# Filter and normalize output
					filtered_output = filter_gdb_output(stdout + stderr)
					
					{output: filtered_output, raw_output: stdout + stderr, status: status}
				ensure
					temp_gdb.close
					temp_gdb.unlink
				end
			end
			
			# Run a GDB script directly (no Ruby process)
			def run_gdb_script(gdb_script)
				temp_gdb = Tempfile.new(["test", ".gdb"])
				begin
					temp_gdb.write("source #{Toolbox::GDB.init_script_path}\n")
					temp_gdb.write(File.read(gdb_script))
					temp_gdb.write("\nquit\n")
					temp_gdb.close
					
					# Run GDB in batch mode
					cmd = ["gdb", "--batch", "--command=#{temp_gdb.path}"]
					stdout, stderr, status = Open3.capture3(*cmd)
					
					# Filter and normalize output
					filtered_output = filter_gdb_output(stdout + stderr)
					
					{output: filtered_output, raw_output: stdout + stderr, status: status}
				ensure
					temp_gdb.close
					temp_gdb.unlink
				end
			end
			
			# Filter GDB output to remove noise
			def filter_gdb_output(output)
				lines = output.lines
				filtered = []
				
				lines.each do |line|
					# Skip GDB startup messages
					next if line.match?(/^Reading symbols from/)
					next if line.match?(/^Loaded '/)
					next if line.match?(/^Starting program:/)
					next if line.match?(/^\[New Thread/)
					next if line.match?(/^\[Thread.*exited/)
					next if line.match?(/^\[Inferior.*exited/)
					next if line.match?(/^During symbol reading/)
					next if line.match?(/warning:.*minimal symbol/)
					next if line.match?(/^Python Exception/)
					next if line.match?(/^Error while/)
					
					# Keep command echoes and output
					filtered << line
				end
				
				filtered.join
			end
			
			# Compute line-by-line diff
			def compute_diff(expected, actual)
				expected_lines = expected.lines
				actual_lines = actual.lines
				
				max_lines = [expected_lines.size, actual_lines.size].max
				diff = []
				
				(0...max_lines).each do |i|
					exp = expected_lines[i]
					act = actual_lines[i]
					
					if exp != act
						diff << {
							line: i + 1,
							expected: exp&.chomp,
							actual: act&.chomp
						}
					end
				end
				
				diff
			end
		end
	end
end


# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

require "open3"
require "timeout"
require_relative "../debugger"

module Toolbox
	module GDB
		# Helper module for running GDB with test fixtures
		module Fixtures
			include Toolbox::Debugger::Fixtures
			# Get the fixtures directory
			def fixtures_dir
				File.expand_path(__dir__)
			end
			
			module_function :fixtures_dir
			
			# Automatically discover test cases from .gdb files in a subdirectory
			# @parameter subdir [String] Subdirectory name (e.g., "object", "fiber")
			# @yields {|name, test_case| ...} The test name and test case hash.
			def self.test_cases(subdir)
				pattern = File.join(subdir, "*.gdb")
				Dir.glob(pattern, base: fixtures_dir).sort.each do |relative_path|
					test_name = File.basename(relative_path, ".gdb")
					# Path without extension for run_test_case
					path_without_ext = relative_path.chomp(".gdb")
					
					test_case = {
						name: path_without_ext,
						path: path_without_ext
					}
					
					yield test_name, test_case
				end
			end
			
			# Run a GDB script (without a Ruby process)
			# @parameter script_name [String] Name of the .gdb script (e.g., "print_fixnum.gdb")
			# @parameter timeout [Integer] Timeout in seconds
			# @returns [Hash] Result with :stdout, :stderr, :status, :success?
			def run_gdb_script(script_name, timeout: 10)
				script_path = File.join(fixtures_dir, script_name)
				
				raise "Script not found: #{script_path}" unless File.exist?(script_path)
				
				# Always pass the Ruby executable so 'run' command works
				cmd = ["gdb", "--batch", "-x", script_path, "--args", RbConfig.ruby]
				
				stdout, status = Open3.capture2(*cmd)
				
				{
					stdout: stdout,
					status: status,
					success?: status.success?
				}
			rescue Errno::ENOENT
				nil
			rescue Timeout::Error
				raise "GDB script timed out after #{timeout} seconds"
			end
			
			# Run a Ruby script under GDB with a GDB command script
			# @param ruby_script [String] Name of the Ruby script (e.g., "simple_values.rb")
			# @param gdb_script [String] Name of the GDB script (e.g., "inspect_values.gdb")
			# @param timeout [Integer] Timeout in seconds
			# @return [Hash] Result with :stdout, :stderr, :status, :success?
			def run_ruby_with_gdb(ruby_script, gdb_script, timeout: 30)
				ruby_path = File.join(fixtures_dir, ruby_script)
				gdb_path = File.join(fixtures_dir, gdb_script)
				
				raise "Ruby script not found: #{ruby_path}" unless File.exist?(ruby_path)
				raise "GDB script not found: #{gdb_path}" unless File.exist?(gdb_path)
				
				cmd = ["gdb", "--batch", "-x", gdb_path, "--args", RbConfig.ruby, ruby_path]
				
				stdout, status = Open3.capture2(*cmd)
				
				{
					stdout: stdout,
					status: status,
					success?: status.success?
				}
			rescue Errno::ENOENT
				nil
			rescue Timeout::Error
				raise "GDB with Ruby script timed out after #{timeout} seconds"
			end
			
			# Run a test case with snapshot comparison
			# @param test_case [String, Hash] Base name of the test (e.g., "object/can_print_fixnum") or test case hash
			# @param update_snapshots [Boolean] If true, update the expected output file
			# @return [Hash] Result with :success?, :output, :expected, :diff
			def run_test_case(test_case, update_snapshots: false)
				# Support both old string format and new hash format
				test_name = test_case.is_a?(Hash) ? test_case[:path] : test_case
				
				puts "DEBUG run_test_case: test_name=#{test_name}" if ENV["DEBUG"]
				
				gdb_script = "#{test_name}.gdb"
				ruby_script = "#{test_name}.rb"
				output_file = "#{test_name}.txt"
				output_path = File.join(fixtures_dir, output_file)
				
				# Check if there's a Ruby script to run with GDB
				ruby_script_path = File.join(fixtures_dir, ruby_script)
				if File.exist?(ruby_script_path)
					puts "DEBUG: Running with Ruby script: #{ruby_script_path}" if ENV["DEBUG"]
					# Run Ruby script under GDB
					result = run_ruby_with_gdb(ruby_script, gdb_script)
				else
					puts "DEBUG: Running GDB script only" if ENV["DEBUG"]
					# Run GDB script standalone
					result = run_gdb_script(gdb_script)
				end
				
				puts "DEBUG: result present=#{!result.nil?}, success=#{result && result[:success?]}" if ENV["DEBUG"]
				
				return {success?: false, error: "GDB script failed", raw_output: result ? result[:stdout] : nil} unless result && result[:success?]
				
				puts "DEBUG: result=#{result.inspect[0..200]}" if ENV["DEBUG"]
				
				actual_output = normalize_output(result[:stdout])
				
				puts "DEBUG: actual_output=#{actual_output.inspect[0..200]}" if ENV["DEBUG"]
				
				# If updating snapshots, write the output and return success
				if update_snapshots
					File.write(output_path, actual_output)
					return {
						success?: true,
						output: actual_output,
						updated: true
					}
				end
				
				# Compare with expected output
				unless File.exist?(output_path)
					# No expected output file - create it
					File.write(output_path, actual_output)
					return {
						success?: true,
						output: actual_output,
						expected: nil,
						created: true
					}
				end
				
				expected_output = File.read(output_path)
				
				if actual_output == expected_output
					{
						success?: true,
						output: actual_output,
						expected: expected_output,
						match: true
					}
				else
					{
						success?: false,
						output: actual_output,
						expected: expected_output,
						diff: compute_diff(expected_output, actual_output),
						raw_output: result[:stdout]
					}
				end
			end
		end
	end
end

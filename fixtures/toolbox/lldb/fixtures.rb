# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

require "fileutils"
require "open3"

module Toolbox
	module LLDB
		module Fixtures
			# Discover test cases from a subdirectory
			# @param subdir [String] Subdirectory name (e.g., "object", "fiber", "heap")
			# @yield [name, test_case] Block to call for each test case
			def self.test_cases(subdir)
				fixtures_dir = File.expand_path("../../../fixtures/toolbox/lldb/#{subdir}", __dir__)
				return unless Dir.exist?(fixtures_dir)
				
				# Find all .lldb script files
				Dir.glob(File.join(fixtures_dir, "*.lldb")).sort.each do |lldb_script|
					base_name = File.basename(lldb_script, ".lldb")
					
					# Expected .txt snapshot file
					txt_file = lldb_script.sub(/\.lldb$/, ".txt")
					
					# Optional .rb Ruby script (for setting up test state)
					rb_file = lldb_script.sub(/\.lldb$/, ".rb")
					rb_file = File.exist?(rb_file) ? rb_file : nil
					
					test_case = {
						name: "#{subdir}/#{base_name}",
						lldb_script: lldb_script,
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
				lldb_script = test_case[:lldb_script]
				ruby_script = test_case[:ruby_script]
				snapshot_file = test_case[:snapshot_file]
				
				# If there's a Ruby script, run it with LLDB
				if ruby_script
					result = run_ruby_with_lldb(ruby_script, lldb_script)
				else
					# Just run the LLDB script
					result = run_lldb_script(lldb_script)
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
			
			# Run a Ruby script under LLDB with an LLDB script
			def run_ruby_with_lldb(ruby_script, lldb_script)
				# Run LLDB in batch mode, loading ruby as target
				# The LLDB script is expected to set up breakpoints and run
				cmd = ["lldb", "--batch", "--source", lldb_script, "ruby", "--", ruby_script]
				
				stdout, status = Open3.capture2(*cmd)
				
				# Filter and normalize output
				filtered_output = filter_lldb_output(stdout)
				
				{output: filtered_output, raw_output: stdout, status: status}
			end
			
			# Run an LLDB script directly (no Ruby process)
			def run_lldb_script(lldb_script)
				# Run LLDB in batch mode with the script
				cmd = ["lldb", "--batch", "--source", lldb_script, "--source-quietly"]
				
				stdout, status = Open3.capture2(*cmd)
				
				# Filter and normalize output
				filtered_output = filter_lldb_output(stdout)
				
				{output: filtered_output, raw_output: stdout, status: status}
			end
			
			# Filter LLDB output to remove noise
			def filter_lldb_output(output)
				# Check if there are markers for extracting specific output
				if output.include?("===TOOLBOX-OUTPUT-START===")
					# Extract content between markers
					start_marker = "===TOOLBOX-OUTPUT-START==="
					end_marker = "===TOOLBOX-OUTPUT-END==="
					
					start_idx = output.index(start_marker)
					end_idx = output.index(end_marker)
					
					if start_idx && end_idx
						# Extract the content between markers (skip the newline after start marker)
						content = output[start_idx + start_marker.length...end_idx]
						
						# Filter lines
						lines = content.lines
						filtered = []
						lines.each do |line|
							# Skip LLDB prompts
							next if line.match?(/^\(lldb\)\s*$/)
							# Remove (lldb) prefix from command output lines
							line = line.sub(/^\(lldb\)\s+/, "")
							filtered << line unless line.strip.empty?
						end
						
						return filtered.join
					end
				end
				
				# Fallback: filter line by line
				lines = output.lines
				filtered = []
				
				lines.each do |line|
					# Skip LLDB startup/shutdown messages
					next if line.match?(/^\(lldb\) target create/)
					next if line.match?(/^Current executable set to/)
					next if line.match?(/^\(lldb\) settings set/)
					next if line.match?(/^\(lldb\) process launch/)
					next if line.match?(/^Process \d+ launched:/)
					next if line.match?(/^Process \d+ exited/)
					next if line.match?(/^\(lldb\) quit/)
					next if line.match?(/^Quitting LLDB will/)
					
					# Skip LLDB command prompts
					next if line.match?(/^\(lldb\) command script import/)
					next if line.match?(/^\(lldb\) rb-/)
					
					# Remove ANSI color codes
					line = line.gsub(/\e\[\d+m/, "")
					
					# Keep important output
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

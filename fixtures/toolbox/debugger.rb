# frozen_string_literal: true

module Toolbox
	module Debugger
		# Shared base module for debugger test fixtures
		# Provides common functionality for running tests with snapshots
		module Fixtures
			# Compute line-by-line diff between expected and actual output
			# @param expected [String] Expected output
			# @param actual [String] Actual output
			# @return [Array<Hash>] Array of diff entries with :line, :expected, :actual
			def compute_diff(expected, actual)
				expected_lines = expected.respond_to?(:lines) ? expected.lines : expected.split("\n")
				actual_lines = actual.respond_to?(:lines) ? actual.lines : actual.split("\n")
				
				max_lines = [expected_lines.length, actual_lines.length].max
				diff = []
				
				max_lines.times do |i|
					exp_line = expected_lines[i]
					act_line = actual_lines[i]
					
					# Normalize line endings for comparison
					exp = exp_line&.chomp
					act = act_line&.chomp
					
					if exp != act
						diff << {
							line: i + 1,
							expected: exp,
							actual: act
						}
					end
				end
				
				diff
			end
			
			# Run a test case with snapshot comparison
			# @param test_case [Hash] Test case configuration
			# @param update_snapshots [Boolean] If true, update snapshot files
			# @return [Hash] Result with :success?, :output, :expected, :match, :diff
			def run_test_case(test_case, update_snapshots: false)
				# Get the output from running the test
				# Subclass must implement this by overriding or ensuring result is set
				result = execute_test(test_case)
				
				return {success?: false, error: "Test execution failed"} unless result
				
				output = result[:output]
				snapshot_file = test_case[:snapshot_file]
				
				# Handle snapshot comparison
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
							raw_output: result[:raw_output] || output,
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
			
			# Execute the test - must be implemented by subclass
			# @param test_case [Hash] Test case configuration
			# @return [Hash] Result with :output and optionally :raw_output, :status
			def execute_test(test_case)
				raise NotImplementedError, "Subclass must implement execute_test"
			end
			
			# Normalize debugger output by extracting content between markers
			# and removing non-deterministic values
			# @param output [String] Raw output from debugger
			# @param debugger_prompts [Array<Regexp>] Debugger-specific prompt patterns to filter
			# @return [String] Normalized output
			def normalize_output(output, debugger_prompts: [])
				# Extract content between markers if present
				if output =~ /===TOOLBOX-OUTPUT-START===\n(.*?)\n===TOOLBOX-OUTPUT-END===/m
					content = $1
					
					# Apply all normalizations
					content = normalize_addresses(content)
					content = normalize_type_tags(content)
					content = normalize_strings(content)
					
					return content.strip + "\n"
				end
				
				# Fallback: filter and normalize line by line
				lines = output.split("\n")
				filtered = []
				
				lines.each do |line|
					# Skip debugger-specific prompts
					next if debugger_prompts.any?{|pattern| line.match?(pattern)}
					
					# Remove ANSI color codes
					line = line.gsub(/\e\[\d+m/, "")
					
					# Apply normalizations
					line = normalize_line(line)
					
					filtered << line unless line.strip.empty?
				end
				
				filtered.join("\n").strip + "\n"
			end
			
			# Normalize addresses in output
			# @param text [String] Text to normalize
			# @return [String] Normalized text
			def normalize_addresses(text)
				# Normalize type tags with addresses: <T_TYPE@0xABCD details> -> <T_TYPE@...>
				text = text.gsub(/<(T_\w+)@0x[0-9a-f]+([^>]*)>/, '<\1@...>')
				
				# Normalize C type pointers: <void *@0xABCD details> -> <void *@...>
				text = text.gsub(/<([A-Za-z_][\w\s*]+?)@0x[0-9a-f]+([^>]*)>/, '<\1@...>')
				
				# Normalize anonymous class references: #<Class:0xABCD> -> #<Class:0x...>
				text = text.gsub(/#<([A-Z][A-Za-z0-9_:]*):0x[0-9a-f]+>/, '#<\1:0x...>')
				
				# Normalize Ruby class instances: <ClassName:0xABCD> -> <ClassName:0x...>
				text = text.gsub(/<([A-Z][A-Za-z0-9_:]*):0x[0-9a-f]+>/, '<\1:0x...>')
				
				# Normalize hex addresses: 0x123ABC -> 0x...
				text = text.gsub(/\b0x[0-9a-f]+\b/i, "0x...")
				
				# Normalize plain hex in angle brackets: <0xABCD> -> <0x...>
				text = text.gsub(/<0x[0-9a-f]+>/i, "<0x...>")
				
				# Normalize process IDs: "Process 12345" -> "Process <PID>"
				text = text.gsub(/Process \d+ (launched|stopped|exited)/, 'Process <PID> \1')
				
				text
			end
			
			# Normalize type tags in output
			# @param text [String] Text to normalize
			# @return [String] Normalized text
			def normalize_type_tags(text)
				# Normalize plain numbers in angle brackets: <12345> -> <...>
				text = text.gsub(/<\d+>/, "<...>")
				
				text
			end
			
			# Normalize strings in output
			# @param text [String] Text to normalize
			# @return [String] Normalized text
			def normalize_strings(text)
				# Normalize string content (including escaped quotes)
				# (?:\\.|[^"]) matches either escaped character or non-quote
				text = text.gsub(/"((?:\\.|[^"])*)"/, '"..."')
				text = text.gsub(/'((?:\\.|[^'])*)'/, '"..."')
				
				text
			end
			
			# Normalize a single line of output
			# @param line [String] Line to normalize
			# @return [String] Normalized line
			def normalize_line(line)
				# Apply address normalizations
				line = normalize_addresses(line)
				
				# GDB-specific: Breakpoint lines
				if line.match?(/^Breakpoint \d+ at /)
					line = line.gsub(/^(Breakpoint \d+) at 0x[0-9a-f]+:/, '\1:')
				end
				
				# Normalize memory addresses in table/array/struct headers
				if line.match?(/(AR Table|ST Table|Heap Array|Embedded Array|Heap Struct|Embedded Struct) at (0x[0-9a-f]+|\d+)/)
					line = line.gsub(/ at (?:0x[0-9a-f]+|\d+)/, " at <address>")
				end
				
				# Normalize bignum length (varies by Ruby version)
				if line.match?(/Bignum \((embedded|heap), length \d+\)/)
					line = line.gsub(/(Bignum \((embedded|heap), length) \d+/, '\1 ...')
				end
				
				# Normalize file paths:
				root = File.expand_path("../..", __dir__)
				line.gsub!(root, "[...]")
				
				line
			end
		end
	end
end
# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

require "toolbox/lldb"
require "fileutils"

# Install LLDB extensions by adding command to ~/.lldbinit
# @parameter lldbinit [String] Optional path to .lldbinit (defaults to ~/.lldbinit)
def install(lldbinit: nil)
	lldbinit_path = lldbinit || File.join(Dir.home, ".lldbinit")
	init_py_path = Toolbox::LLDB.init_script_path
	command_line = "command script import #{init_py_path}"
	marker_comment = "# Ruby Toolbox LLDB Extensions"
	
	puts "Installing Ruby Toolbox LLDB extensions..."
	puts "  Extensions: #{File.dirname(init_py_path)}"
	puts "  Config: #{lldbinit_path}"
	
	# Read existing .lldbinit or create empty array
	lines = File.exist?(lldbinit_path) ? File.readlines(lldbinit_path) : []
	
	# Check if already installed (look for marker comment)
	marker_index = lines.index{|line| line.strip == marker_comment}
	
	if marker_index
		# Already installed - update the command line in case path changed
		command_index = marker_index + 1
		if command_index < lines.size && lines[command_index].strip.start_with?("command script import")
			old_command = lines[command_index].strip
			if old_command == command_line
				puts "\n✓ Already installed in #{lldbinit_path}"
				puts "  #{command_line}"
				return
			else
				# Path changed - update it
				lines[command_index] = "#{command_line}\n"
				File.write(lldbinit_path, lines.join)
				puts "\n✓ Updated installation in #{lldbinit_path}"
				puts "  Old: #{old_command}"
				puts "  New: #{command_line}"
				return
			end
		end
	end
	
	# Not installed - add it
	File.open(lldbinit_path, "a") do |f|
		f.puts unless lines.last&.strip&.empty?
		f.puts marker_comment
		f.puts command_line
	end
	
	puts "\n✓ Installation complete!"
	puts "\nAdded to #{lldbinit_path}:"
	puts "  #{command_line}"
	puts "\nExtensions will load automatically when you start LLDB."
end

# Uninstall LLDB extensions by removing command from ~/.lldbinit
# @parameter lldbinit [String] Optional path to .lldbinit (defaults to ~/.lldbinit)
def uninstall(lldbinit: nil)
	lldbinit_path = lldbinit || File.join(Dir.home, ".lldbinit")
	marker_comment = "# Ruby Toolbox LLDB Extensions"
	
	puts "Uninstalling Ruby Toolbox LLDB extensions..."
	
	unless File.exist?(lldbinit_path)
		puts "No ~/.lldbinit file found - nothing to uninstall."
		return
	end
	
	lines = File.readlines(lldbinit_path)
	marker_index = lines.index{|line| line.strip == marker_comment}
	
	unless marker_index
		puts "Extensions were not found in #{lldbinit_path}"
		return
	end
	
	# Remove the marker comment and the command line after it
	lines.delete_at(marker_index)  # Remove comment
	if marker_index < lines.size && lines[marker_index].strip.start_with?("command script import")
		removed_line = lines.delete_at(marker_index).strip  # Remove command line
		puts "  Removed: #{removed_line}"
	end
	
	# Clean up empty line before marker if it exists
	if marker_index > 0 && lines[marker_index - 1].strip.empty?
		lines.delete_at(marker_index - 1)
	end
	
	File.write(lldbinit_path, lines.join)
	puts "✓ Removed Ruby Toolbox LLDB extensions from #{lldbinit_path}"
end

# Show installation information
# @parameter lldbinit [String] Optional path to .lldbinit (defaults to ~/.lldbinit)
def info(lldbinit: nil)
	lldbinit_path = lldbinit || File.join(Dir.home, ".lldbinit")
	init_py_path = Toolbox::LLDB.init_script_path
	marker_comment = "# Ruby Toolbox LLDB Extensions"
	
	puts "Ruby Toolbox LLDB Extensions v#{Toolbox::VERSION}"
	puts "\nToolbox directory: #{Toolbox::LLDB.data_path}"
	puts "Init script: #{init_py_path}"
	puts "Note: Same init.py works for both GDB and LLDB"
	
	# Check installation status by looking for marker comment
	installed = false
	current_command = nil
	
	if File.exist?(lldbinit_path)
		lines = File.readlines(lldbinit_path)
		marker_index = lines.index{|line| line.strip == marker_comment}
		if marker_index
			installed = true
			command_index = marker_index + 1
			if command_index < lines.size
				current_command = lines[command_index].strip
			end
		end
	end
	
	puts "\nLLDB config: #{lldbinit_path}"
	if installed
		puts "Status: ✓ Installed"
		if current_command
			puts "  #{current_command}"
		end
	else
		puts "Status: ✗ Not installed"
		puts "\nRun: bake toolbox:lldb:install"
	end
end


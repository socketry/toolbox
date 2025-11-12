# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

require "ruby/gdb"
require "fileutils"

# Install GDB extensions by adding source line to ~/.gdbinit
# @parameter gdbinit [String] Optional path to .gdbinit (defaults to ~/.gdbinit)
def install(gdbinit: nil)
	gdbinit_path = gdbinit || File.join(Dir.home, ".gdbinit")
	init_py_path = Ruby::GDB.init_script_path
	source_line = "source #{init_py_path}"
	marker_comment = "# Ruby GDB Extensions (ruby-gdb gem)"
	
	puts "Installing Ruby GDB extensions..."
	puts "  Extensions: #{File.dirname(init_py_path)}"
	puts "  Config: #{gdbinit_path}"
	
	# Read existing .gdbinit or create empty array
	lines = File.exist?(gdbinit_path) ? File.readlines(gdbinit_path) : []
	
	# Check if already installed (look for marker comment)
	marker_index = lines.index{|line| line.strip == marker_comment}
	
	if marker_index
		# Already installed - update the source line in case path changed
		source_index = marker_index + 1
		if source_index < lines.size && lines[source_index].strip.start_with?("source")
			old_source = lines[source_index].strip
			if old_source == source_line
				puts "\n✓ Already installed in #{gdbinit_path}"
				puts "  #{source_line}"
				return
			else
				# Path changed - update it
				lines[source_index] = "#{source_line}\n"
				File.write(gdbinit_path, lines.join)
				puts "\n✓ Updated installation in #{gdbinit_path}"
				puts "  Old: #{old_source}"
				puts "  New: #{source_line}"
				return
			end
		end
	end
	
	# Not installed - add it
	File.open(gdbinit_path, "a") do |f|
		f.puts unless lines.last&.strip&.empty?
		f.puts marker_comment
		f.puts source_line
	end
	
	puts "\n✓ Installation complete!"
	puts "\nAdded to #{gdbinit_path}:"
	puts "  #{source_line}"
	puts "\nExtensions will load automatically when you start GDB."
end

# Uninstall GDB extensions by removing source line from ~/.gdbinit
# @parameter gdbinit [String] Optional path to .gdbinit (defaults to ~/.gdbinit)
def uninstall(gdbinit: nil)
	gdbinit_path = gdbinit || File.join(Dir.home, ".gdbinit")
	marker_comment = "# Ruby GDB Extensions (ruby-gdb gem)"
	
	puts "Uninstalling Ruby GDB extensions..."
	
	unless File.exist?(gdbinit_path)
		puts "No ~/.gdbinit file found - nothing to uninstall."
		return
	end
	
	lines = File.readlines(gdbinit_path)
	marker_index = lines.index{|line| line.strip == marker_comment}
	
	unless marker_index
		puts "Extensions were not found in #{gdbinit_path}"
		return
	end
	
	# Remove the marker comment and the source line after it
	lines.delete_at(marker_index)  # Remove comment
	if marker_index < lines.size && lines[marker_index].strip.start_with?("source")
		removed_line = lines.delete_at(marker_index).strip  # Remove source line
		puts "  Removed: #{removed_line}"
	end
	
	# Clean up empty line before marker if it exists
	if marker_index > 0 && lines[marker_index - 1].strip.empty?
		lines.delete_at(marker_index - 1)
	end
	
	File.write(gdbinit_path, lines.join)
	puts "✓ Removed Ruby GDB extensions from #{gdbinit_path}"
end

# Show installation information
# @parameter gdbinit [String] Optional path to .gdbinit (defaults to ~/.gdbinit)
def info(gdbinit: nil)
	gdbinit_path = gdbinit || File.join(Dir.home, ".gdbinit")
	init_py_path = Ruby::GDB.init_script_path
	marker_comment = "# Ruby GDB Extensions (ruby-gdb gem)"
	
	puts "Ruby GDB Extensions v#{Ruby::GDB::VERSION}"
	puts "\nGem data directory: #{Ruby::GDB.data_path}"
	puts "Init script: #{init_py_path}"
	
	# Check installation status by looking for marker comment
	installed = false
	current_source = nil
	
	if File.exist?(gdbinit_path)
		lines = File.readlines(gdbinit_path)
		marker_index = lines.index{|line| line.strip == marker_comment}
		if marker_index
			installed = true
			source_index = marker_index + 1
			if source_index < lines.size
				current_source = lines[source_index].strip
			end
		end
	end
	
	puts "\nGDB config: #{gdbinit_path}"
	if installed
		puts "Status: ✓ Installed"
		if current_source
			puts "  #{current_source}"
		end
	else
		puts "Status: ✗ Not installed"
		puts "\nRun: bake ruby:gdb:install"
	end
end

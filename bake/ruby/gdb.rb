# frozen_string_literal: true

# Released under the MIT License.
# Copyright, 2025, by Samuel Williams.

require "ruby/gdb"
require "fileutils"

# Install GDB Python extensions to XDG data directory or custom prefix
# @parameter prefix [String] Optional installation prefix (defaults to XDG_DATA_HOME)
def install(prefix: nil)
	install_path = Ruby::GDB.install_path(prefix: prefix)
	
	puts "Installing Ruby GDB extensions to: #{install_path}"
	
	# Create installation directory
	FileUtils.mkdir_p(install_path)
	
	# Copy Python scripts
	scripts = [
		Ruby::GDB.object_script_path,
		Ruby::GDB.fiber_script_path
	]
	
	scripts.each do |script|
		if File.exist?(script)
			dest = File.join(install_path, File.basename(script))
			puts "  Installing #{File.basename(script)}..."
			FileUtils.cp(script, dest)
		else
			warn "  Warning: #{script} not found"
		end
	end
	
	# Create a loader script that sources both extensions
	loader_path = File.join(install_path, "init.gdb")
	puts "  Creating loader script: #{File.basename(loader_path)}"
	
	File.write(loader_path, <<~GDB)
		# Ruby GDB Extensions Loader
		# This file loads Ruby debugging extensions for GDB
		
		python
		import sys
		import os
		
		# Add the Ruby GDB extensions directory to Python path
		ruby_gdb_dir = os.path.dirname(__file__)
		if ruby_gdb_dir not in sys.path:
		    sys.path.insert(0, ruby_gdb_dir)
		
		# Load Ruby object printing extensions
		exec(open(os.path.join(ruby_gdb_dir, 'object.py')).read())
		
		# Load Ruby fiber debugging extensions
		exec(open(os.path.join(ruby_gdb_dir, 'fiber.py')).read())
		
		print("Ruby GDB extensions loaded successfully!")
		print("Use 'help rb-' to see available commands.")
		end
	GDB
	
	puts "\nInstallation complete!"
	puts "\nTo use these extensions, add the following to your ~/.gdbinit:"
	puts "  source #{loader_path}"
	puts "\nOr load them manually in GDB with:"
	puts "  (gdb) source #{loader_path}"
end

# Uninstall GDB Python extensions
# @parameter prefix [String] Optional installation prefix (defaults to XDG_DATA_HOME)
def uninstall(prefix: nil)
	install_path = Ruby::GDB.install_path(prefix: prefix)
	
	if Dir.exist?(install_path)
		puts "Removing Ruby GDB extensions from: #{install_path}"
		FileUtils.rm_rf(install_path)
		puts "Uninstallation complete!"
	else
		puts "No installation found at: #{install_path}"
	end
end

# Show installation information
def info
	puts "Ruby GDB Extensions v#{Ruby::GDB::VERSION}"
	puts "\nData directory: #{Ruby::GDB.data_path}"
	puts "Default install path: #{Ruby::GDB.install_path}"
	puts "\nAvailable scripts:"
	puts "  - object.py (rb-object-print command)"
	puts "  - fiber.py (rb-scan-fibers, rb-fiber-bt, and more)"
end


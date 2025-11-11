# frozen_string_literal: true

require_relative "lib/ruby/gdb/version"

Gem::Specification.new do |spec|
	spec.name = "ruby-gdb"
	spec.version = Ruby::GDB::VERSION
	
	spec.summary = "Ruby debugging extensions for GDB"
	spec.authors = ["Samuel Williams"]
	spec.license = "MIT"
	
	spec.homepage = "https://github.com/socketry/ruby-gdb"
	
	spec.metadata = {
		"documentation_uri" => "https://socketry.github.io/ruby-gdb/",
		"source_code_uri" => "https://github.com/socketry/ruby-gdb",
	}
	
	spec.files = Dir["{data,lib}/**/*", "*.md", base: __dir__]
	
	spec.required_ruby_version = ">= 3.2"
end

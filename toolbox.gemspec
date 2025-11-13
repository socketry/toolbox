# frozen_string_literal: true

require_relative "lib/toolbox/version"

Gem::Specification.new do |spec|
	spec.name = "toolbox"
	spec.version = Toolbox::VERSION
	
	spec.summary = "Ruby debugging toolbox for GDB and LLDB"
	spec.authors = ["Samuel Williams"]
	spec.license = "MIT"
	
	spec.cert_chain  = ["release.cert"]
	spec.signing_key = File.expand_path("~/.gem/release.pem")
	
	spec.homepage = "https://github.com/socketry/toolbox"
	
	spec.metadata = {
		"documentation_uri" => "https://socketry.github.io/toolbox/",
		"source_code_uri" => "https://github.com/socketry/toolbox",
	}
	
	spec.files = Dir["{bake,context,data,lib}/**/*", "*.md", base: __dir__]
	
	spec.required_ruby_version = ">= 3.2"
end


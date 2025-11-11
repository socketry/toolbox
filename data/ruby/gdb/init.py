import gdb
import os
import sys

# Get the directory containing this file
ruby_gdb_dir = os.path.dirname(os.path.abspath(__file__))

# Add to Python path for imports
if ruby_gdb_dir not in sys.path:
	sys.path.insert(0, ruby_gdb_dir)

# Load object inspection extensions:
import object

# Load fiber debugging extensions:
import fiber

# Load stack inspection extensions:
import stack

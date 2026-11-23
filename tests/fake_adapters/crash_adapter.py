# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Test adapter: setup works, every fetch crashes without writing a result."""
import sys
if sys.argv[1] == "setup":
    print("0.1")
    sys.exit()
raise RuntimeError("browser crashed in /home/someone/secret")

# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Test adapter: starts a child process (like a browser) and never returns."""
import subprocess, sys, time
if sys.argv[1] == "setup":
    print("0.1")
    sys.exit()
subprocess.Popen(["sleep", "987654"])
time.sleep(987654)

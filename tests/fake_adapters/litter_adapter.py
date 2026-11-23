# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Test adapter: leaves a temporary folder behind, like a killed browser leaves its profile."""
import json, sys, tempfile

if sys.argv[1] == "setup":
    print("0.1")
    sys.exit()
left_behind = tempfile.mkdtemp(prefix="profile-")
json.dump({"status": 200, "html": left_behind, "clicked": False, "error": None}, open(sys.argv[4], "w"))

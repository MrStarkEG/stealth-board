# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Test adapter: fetch with urllib."""
import json, sys, urllib.error, urllib.request

if sys.argv[1] == "setup":
    print("1.2.3")
    sys.exit()
_, _, url, mode, outfile = sys.argv
try:
    with urllib.request.urlopen(url) as r:
        result = {"status": r.status, "html": r.read().decode(), "error": None}
except urllib.error.HTTPError as e:
    result = {"status": e.code, "html": e.read().decode(), "error": None}
json.dump(result, open(outfile, "w"))

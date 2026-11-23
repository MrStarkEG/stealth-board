"""Shared entry point for adapters.

An adapter is one standalone script. uv reads the dependency list at the top
of the script and runs it in its own environment, so tools never clash.

    uv run adapters/NAME_adapter.py setup
        Install what the tool needs (browsers). Print the tool version.
    uv run adapters/NAME_adapter.py fetch URL headless|headed|http OUTFILE
        Open URL once and write {"status", "html", "error"} to OUTFILE as JSON.
"""

import importlib.metadata
import json
import subprocess
import sys

# Browser adapters wait this long after the page loads, so a challenge page
# has time to finish and send the browser on to the real page.
SETTLE_MS = 8000
NAV_TIMEOUT_MS = 45000


def run(package, fetch, setup=()):
    """package: the PyPI name, for the version. fetch(url, headless) -> (status, html).
    setup: list of "python -m" argument lists to run once before the first fetch."""
    if sys.argv[1] == "setup":
        for args in setup:
            subprocess.run([sys.executable, "-m", *args], check=True, stdout=sys.stderr)
        print(importlib.metadata.version(package))
        return
    _, _, url, mode, outfile = sys.argv
    try:
        status, html = fetch(url, mode != "headed")
        result = {"status": status, "html": html, "error": None}
    except Exception as e:
        result = {"status": None, "html": "", "error": f"{type(e).__name__}: {e}"}
    with open(outfile, "w") as f:
        json.dump(result, f)

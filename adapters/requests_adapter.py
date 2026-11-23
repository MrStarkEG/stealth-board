# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["requests"]
# ///
"""Control: plain requests with default settings. This is what a beginner writes first.
If this passes a target, that target has no real protection."""

import requests

from _common import run_adapter


def fetch(url, headless):
    r = requests.get(url, timeout=30)
    return r.status_code, r.text


run_adapter("requests", fetch)

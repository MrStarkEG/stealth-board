# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Test adapter: when the page is a challenge and clicking is on, it "clicks"
by loading the page again with ?clicked=1."""
import json, os, sys, urllib.error, urllib.request

if sys.argv[1] == "setup":
    print("0.1")
    sys.exit()
_, _, url, mode, outfile = sys.argv


def get(u):
    try:
        with urllib.request.urlopen(u) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


status, html = get(url)
clicked = False
if "cf-turnstile" in html and os.environ["STEALTH_BOARD_CLICK"] == "1":
    status, html = get(url + "?clicked=1")
    clicked = True
json.dump({"status": status, "html": html, "clicked": clicked, "error": None}, open(outfile, "w"))

"""Shared entry point for adapters.

An adapter is one standalone script. uv reads the dependency list at the top
of the script and runs it in its own environment, so tools never clash.

    uv run adapters/NAME_adapter.py setup
        Install what the tool needs (browsers). Print the tool version.
    uv run adapters/NAME_adapter.py fetch URL headless|headed|http OUTFILE
        Open URL once and write {"status", "html", "clicked", "error"} to OUTFILE as JSON.

Clicking the challenge box: when a page shows a Cloudflare check box, the adapter
may click it once and wait again. "clicked" says what happened: true (clicked),
false (no box was found), null (the tool has its own solver and does not tell us).
The runner turns this off with STEALTH_BOARD_CLICK=0.
"""

import importlib.metadata
import json
import os
import subprocess
import sys
from pathlib import Path

# Browser adapters wait this long after the page loads, so a challenge page
# has time to finish and send the browser on to the real page.
SETTLE_MS = 8000
NAV_TIMEOUT_MS = 45000
CLICK = os.environ.get("STEALTH_BOARD_CLICK", "1") == "1"


def find_challenge_box(page):
    """Return the screen box whose left edge is the Cloudflare check box widget, or None."""
    # Chrome lists the widget frame with its Cloudflare URL.
    for frame in page.frames[1:]:
        if "challenges.cloudflare.com" in frame.url:
            try:
                box = frame.frame_element().bounding_box()
            except Exception:
                continue  # the frame went away while we looked
            if box and box["width"] >= 100 and box["height"] >= 50:  # skip hidden helper frames
                return box
    # Firefox hides that frame from us. The widget also puts a hidden input on the
    # page, and the element around that input starts where the widget starts.
    holder = page.locator('input[name="cf-turnstile-response"]').first.locator("xpath=..")
    try:
        box = holder.bounding_box(timeout=1000)
    except Exception:
        return None  # no widget on this page
    return box if box and box["height"] >= 50 else None


def settle(page):
    """For adapters with a Playwright-style page. Wait for the page to settle.
    If a Cloudflare check box is showing and clicking is on, click it once and
    wait again. Return True if it clicked.

    Cloudflare can still refuse a click that lands: the box shows "Verifying..."
    for a moment and then comes back empty. That try is saved as a challenge
    with clicked = true."""
    page.wait_for_timeout(SETTLE_MS)
    box = find_challenge_box(page) if CLICK else None
    if not box:
        return False
    # The check box is a square at the left of the widget, about 22px in.
    x, y = box["x"] + 22, box["y"] + box["height"] / 2
    page.mouse.move(x - 80, y + 50)
    page.mouse.move(x, y, steps=15)
    page.wait_for_timeout(300)
    page.mouse.click(x, y, delay=120)
    page.wait_for_timeout(SETTLE_MS)
    return True


def run(package, fetch, setup=()):
    """package: the PyPI name, for the version.
    fetch(url, headless) -> (status, html) or (status, html, clicked).
    setup: commands to run once before the first fetch, like ["playwright", "install", "chromium"].
    The first word is a command the package installs."""
    if sys.argv[1] == "setup":
        bin_dir = Path(sys.executable).parent
        for command, *args in setup:
            subprocess.run([bin_dir / command, *args], check=True, stdout=sys.stderr)
        print(importlib.metadata.version(package))
        return
    _, _, url, mode, outfile = sys.argv
    try:
        status, html, *clicked = fetch(url, mode != "headed")
        result = {"status": status, "html": html, "clicked": clicked[0] if clicked else False, "error": None}
    except Exception as e:
        result = {"status": None, "html": "", "clicked": False, "error": f"{type(e).__name__}: {e}"}
    with open(outfile, "w") as f:
        json.dump(result, f)

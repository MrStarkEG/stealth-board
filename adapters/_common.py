"""Shared code for adapters.

An adapter is one standalone script. uv reads the dependency list at the top
of the script and runs it in its own environment, so tools never clash.

    uv run adapters/NAME_adapter.py setup
        Install what the tool needs (browsers). Print the tool version.
    uv run adapters/NAME_adapter.py fetch URL MODE OUTFILE
        Open URL once and write {"status", "html", "clicked", "error"} to OUTFILE.

"clicked" is about the Cloudflare check box: true (the adapter clicked it),
false (no box, or clicking is off), null (the tool has its own solver and
does not say).
"""

import importlib.metadata
import json
import os
import subprocess
import sys
from pathlib import Path

SETTLE_MS = 8000  # time for a challenge page to finish and move on to the real page
NAV_TIMEOUT_MS = 45000
CLICK = os.environ.get("STEALTH_BOARD_CLICK", "1") == "1"

CHECKBOX_OFFSET_X = 22  # the check box is a square at the left edge of the widget
MIN_WIDGET_WIDTH = 100  # smaller Cloudflare frames are hidden helpers
MIN_WIDGET_HEIGHT = 50


def run_adapter(package, fetch, setup=()):
    """The entry point of every adapter.

    package: the PyPI name, used to read the version.
    fetch(url, headless): returns (status, html) or (status, html, clicked).
    setup: commands to run once, like ["playwright", "install", "chromium"].
    """
    if sys.argv[1] == "setup":
        install(package, setup)
    else:
        _, _, url, mode, outfile = sys.argv
        Path(outfile).write_text(json.dumps(fetch_safely(fetch, url, mode)))


def install(package, setup):
    bin_dir = Path(sys.executable).parent
    for command, *args in setup:
        subprocess.run([bin_dir / command, *args], check=True, stdout=sys.stderr)
    print(importlib.metadata.version(package))


def fetch_safely(fetch, url, mode):
    try:
        status, html, *clicked = fetch(url, mode != "headed")
    except Exception as error:
        return {"status": None, "html": "", "clicked": False, "error": f"{type(error).__name__}: {error}"}
    return {"status": status, "html": html, "clicked": clicked[0] if clicked else False, "error": None}


def wait_and_click(page):
    """For a Playwright-style page: wait, click the Cloudflare check box if there
    is one, and wait again. Return True if it clicked.

    Cloudflare can refuse a click that lands. The box then shows "Verifying..."
    for a moment and comes back empty.
    """
    page.wait_for_timeout(SETTLE_MS)
    if not CLICK:
        return False
    widget = find_challenge_widget(page)
    if widget is None:
        return False

    x = widget["x"] + CHECKBOX_OFFSET_X
    y = widget["y"] + widget["height"] / 2
    page.mouse.move(x - 80, y + 50)
    page.mouse.move(x, y, steps=15)
    page.wait_for_timeout(300)
    page.mouse.click(x, y, delay=120)
    page.wait_for_timeout(SETTLE_MS)
    return True


def find_challenge_widget(page):
    """Return the screen box of the Cloudflare check box widget, or None."""
    # Chrome lists the widget frame with its Cloudflare URL.
    for frame in page.frames[1:]:
        if "challenges.cloudflare.com" not in frame.url:
            continue
        try:
            box = frame.frame_element().bounding_box()
        except Exception:
            continue  # the frame went away while we looked
        if box and box["width"] >= MIN_WIDGET_WIDTH and box["height"] >= MIN_WIDGET_HEIGHT:
            return box

    # Firefox hides that frame. The widget also adds a hidden input, and the
    # element around that input starts where the widget starts.
    holder = page.locator('input[name="cf-turnstile-response"]').first.locator("xpath=..")
    try:
        box = holder.bounding_box(timeout=1000)
    except Exception:
        return None  # no widget on this page
    if box and box["height"] >= MIN_WIDGET_HEIGHT:
        return box
    return None

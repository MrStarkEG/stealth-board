# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["patchright"]
# ///
"""Patchright: a patched Playwright that hides the usual automation leaks.
Settings from its README ("Best Practice"): real Google Chrome, a persistent
profile, no fixed viewport, and no custom headers or user agent.
The profile is a new empty folder for every fetch."""

import shutil
import tempfile

from patchright.sync_api import sync_playwright

from _common import NAV_TIMEOUT_MS, run_adapter, wait_and_click


def fetch(url, headless):
    with sync_playwright() as p, tempfile.TemporaryDirectory() as profile:
        context = p.chromium.launch_persistent_context(profile, channel="chrome", headless=headless, no_viewport=True)
        page = context.pages[0] if context.pages else context.new_page()
        response = page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
        clicked = wait_and_click(page)
        html = page.content()
        context.close()
        return response.status if response else None, html, clicked


# Chrome needs root to install, so skip it when the machine already has it.
CHROME_SETUP = [] if shutil.which("google-chrome") else [["patchright", "install", "chrome"]]

run_adapter("patchright", fetch, setup=CHROME_SETUP)

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

from _common import NAV_TIMEOUT_MS, SETTLE_MS, run


def fetch(url, headless):
    with sync_playwright() as p, tempfile.TemporaryDirectory() as profile:
        context = p.chromium.launch_persistent_context(profile, channel="chrome", headless=headless, no_viewport=True)
        page = context.pages[0] if context.pages else context.new_page()
        response = page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
        page.wait_for_timeout(SETTLE_MS)
        html = page.content()
        context.close()
        return response.status if response else None, html


# Chrome needs root to install, so skip it when the machine already has it.
run("patchright", fetch, setup=[] if shutil.which("google-chrome") else [["patchright", "install", "chrome"]])

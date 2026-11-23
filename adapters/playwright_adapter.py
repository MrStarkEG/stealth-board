# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["playwright"]
# ///
"""Control: plain Playwright with its own Chromium and no stealth at all.
The stealth tools should beat this. If they do not, they add nothing."""

from playwright.sync_api import sync_playwright

from _common import NAV_TIMEOUT_MS, SETTLE_MS, run


def fetch(url, headless):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        response = page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
        page.wait_for_timeout(SETTLE_MS)
        html = page.content()
        browser.close()
        return response.status if response else None, html


run("playwright", fetch, setup=[["playwright", "install", "chromium"]])

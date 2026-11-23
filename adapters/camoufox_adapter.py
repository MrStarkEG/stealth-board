# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["camoufox[geoip]"]
# ///
"""Camoufox: a Firefox build that changes its fingerprint inside the browser itself.
Settings from its README: the default Camoufox() launch, which picks a
matching fingerprint on its own."""

from camoufox.sync_api import Camoufox

from _common import NAV_TIMEOUT_MS, run_adapter, wait_and_click


def fetch(url, headless):
    with Camoufox(headless=headless) as browser:
        page = browser.new_page()
        response = page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
        clicked = wait_and_click(page)
        return response.status if response else None, page.content(), clicked


run_adapter("camoufox", fetch, setup=[["camoufox", "fetch"]])

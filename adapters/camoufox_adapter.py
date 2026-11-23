# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["camoufox[geoip]"]
# ///
"""Camoufox: a Firefox build that changes its fingerprint inside the browser itself.
Settings from its README: the default Camoufox() launch, which picks a
matching fingerprint on its own."""

from camoufox.sync_api import Camoufox

from _common import NAV_TIMEOUT_MS, SETTLE_MS, run


def fetch(url, headless):
    with Camoufox(headless=headless) as browser:
        page = browser.new_page()
        response = page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
        page.wait_for_timeout(SETTLE_MS)
        return response.status if response else None, page.content()


run("camoufox", fetch, setup=[["camoufox", "fetch"]])

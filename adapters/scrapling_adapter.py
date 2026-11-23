# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["scrapling[fetchers]"]
# ///
"""Scrapling: a scraping framework. This tests its StealthyFetcher.
Settings from its README ("Advanced stealth mode"): solve_cloudflare=True.
That is its own solver for the Cloudflare box. It does not say if it clicked."""

from scrapling.fetchers import StealthyFetcher

from _common import CLICK, SETTLE_MS, run_adapter


def fetch(url, headless):
    page = StealthyFetcher.fetch(url, headless=headless, solve_cloudflare=CLICK, wait=SETTLE_MS)
    return page.status, page.html_content, None if CLICK else False


# "scrapling install" also runs a step that needs root, so download the browsers directly.
# StealthyFetcher drives Chromium through Patchright, which wants its own download.
BROWSER_SETUP = [["playwright", "install", "chromium"], ["patchright", "install", "chromium"]]

run_adapter("scrapling", fetch, setup=BROWSER_SETUP)

# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["scrapling[fetchers]"]
# ///
"""Scrapling: a scraping framework. This tests its StealthyFetcher.
Settings from its README ("Advanced stealth mode"): solve_cloudflare=True,
so it also tries to click through Cloudflare challenges by itself."""

from scrapling.fetchers import StealthyFetcher

from _common import SETTLE_MS, run


def fetch(url, headless):
    page = StealthyFetcher.fetch(url, headless=headless, solve_cloudflare=True, wait=SETTLE_MS)
    return page.status, page.html_content


# "scrapling install" also runs a step that needs root, so download the browsers directly.
# StealthyFetcher drives Chromium through Patchright, which wants its own download.
run("scrapling", fetch, setup=[["playwright", "install", "chromium"], ["patchright", "install", "chromium"]])

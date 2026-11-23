# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["zendriver"]
# ///
"""zendriver: an actively kept fork of nodriver. It also drives the installed
Chrome over the DevTools protocol. Settings from its README: the default
start(). It does not report the HTTP status."""

import asyncio

import zendriver

from _common import SETTLE_MS, run


def fetch(url, headless):
    async def go():
        browser = await zendriver.start(headless=headless)
        try:
            page = await browser.get(url)
            await page.sleep(SETTLE_MS / 1000)
            return None, await page.get_content()
        finally:
            await browser.stop()

    return asyncio.run(go())


run("zendriver", fetch)

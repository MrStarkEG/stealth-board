# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["zendriver"]
# ///
"""zendriver: an actively kept fork of nodriver. It also drives the installed
Chrome over the DevTools protocol. Settings from its README: the default
start(). It does not report the HTTP status.
For the challenge box it uses its own helper, verify_cf()."""

import asyncio

import zendriver

from _common import CLICK, SETTLE_MS, run_adapter


def fetch(url, headless):
    async def go():
        browser = await zendriver.start(headless=headless)
        try:
            page = await browser.get(url)
            await page.sleep(SETTLE_MS / 1000)
            clicked = False
            if CLICK:
                try:
                    await page.verify_cf(timeout=5)
                    clicked = True
                    await page.sleep(SETTLE_MS / 1000)
                except TimeoutError:
                    pass  # no check box on this page
            return None, await page.get_content(), clicked
        finally:
            await browser.stop()

    return asyncio.run(go())


run_adapter("zendriver", fetch)

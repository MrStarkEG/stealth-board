# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["nodriver"]
# ///
"""nodriver: drives the installed Chrome over the DevTools protocol, with no
WebDriver and no Playwright. Settings from its README: the default start(),
which uses a new temporary profile. It does not report the HTTP status."""

import nodriver

from _common import SETTLE_MS, run


def fetch(url, headless):
    async def go():
        browser = await nodriver.start(headless=headless)
        try:
            page = await browser.get(url)
            await page.sleep(SETTLE_MS / 1000)
            return None, await page.get_content()
        finally:
            browser.stop()

    return nodriver.loop().run_until_complete(go())


run("nodriver", fetch)

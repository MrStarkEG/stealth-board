# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["seleniumbase"]
# ///
"""SeleniumBase: this tests its "Pure CDP Mode" (sb_cdp), the stealth mode its
README recommends. It drives the installed Chrome and does not use WebDriver.
solve_captcha() is its own helper and does nothing when there is no captcha.
It does not report the HTTP status."""

from seleniumbase import sb_cdp

from _common import SETTLE_MS, run


def fetch(url, headless):
    sb = sb_cdp.Chrome(url, headless=headless)
    try:
        sb.sleep(SETTLE_MS / 1000 / 2)
        sb.solve_captcha()
        sb.sleep(SETTLE_MS / 1000 / 2)
        return None, sb.get_page_source()
    finally:
        sb.quit()


run("seleniumbase", fetch)

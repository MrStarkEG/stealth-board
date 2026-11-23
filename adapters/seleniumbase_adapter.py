# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["seleniumbase"]
# ///
"""SeleniumBase: this tests its "Pure CDP Mode" (sb_cdp), the stealth mode its
README recommends. It drives the installed Chrome and does not use WebDriver.
For the challenge box it uses its own helper, solve_captcha(), which does
nothing when there is no captcha and does not say if it clicked.
It does not report the HTTP status."""

from seleniumbase import sb_cdp

from _common import CLICK, SETTLE_MS, run_adapter


def fetch(url, headless):
    sb = sb_cdp.Chrome(url, headless=headless)
    try:
        sb.sleep(SETTLE_MS / 1000)
        if CLICK:
            sb.solve_captcha()
            sb.sleep(SETTLE_MS / 1000 / 2)
        return None, sb.get_page_source(), None if CLICK else False
    finally:
        sb.quit()


run_adapter("seleniumbase", fetch)

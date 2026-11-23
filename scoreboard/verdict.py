"""Decide if a fetched page is the real page or a block page."""

import re

# A challenge page asks the browser to prove something first (a check box, a
# puzzle, a wait). The site has not said no yet, but we did not get through.
CHALLENGES = [
    ("cloudflare challenge", r"Just a moment\.\.\.|cf-chl-|cf-turnstile|challenges\.cloudflare\.com"),
    ("datadome captcha", r"captcha-delivery\.com"),
    ("perimeterx captcha", r"px-captcha|Press &amp; Hold|Press & Hold"),
    ("kasada challenge", r"KPSDK"),
    ("captcha", r"g-recaptcha|h-captcha|hcaptcha\.com"),
]

# A block page is a plain no.
BLOCKS = [
    ("cloudflare block", r"Attention Required! \| Cloudflare|Sorry, you have been blocked"),
    ("akamai block", r"errors\.edgesuite\.net"),
    ("imperva block", r"_Incapsula_Resource"),
]


def judge(status, html, expect, reject=None):
    """Return (verdict, reason).

    pass       the expected text is there. A status of 200 is not enough,
               because block pages often return 200.
    challenge  the page is still showing a check or a captcha
    blocked    the site refused, or the page is something else

    The marker lists only choose between "challenge" and "blocked" and name
    the reason. Pass is decided by the expected text alone.
    """
    if reject and re.search(reject, html):
        return "blocked", "page says we are a bot"
    if re.search(expect, html):
        return "pass", ""
    for name, pattern in BLOCKS:
        if re.search(pattern, html):
            return "blocked", name
    for name, pattern in CHALLENGES:
        if re.search(pattern, html):
            return "challenge", name
    if status is not None and status >= 400:
        return "blocked", f"http {status}"
    return "blocked", "expected text missing"

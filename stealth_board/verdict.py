"""Decide if a fetched page is the real page, a challenge, or a block."""

import re

# A challenge page asks the browser to prove something first. The site has not
# said no yet, but we did not get through.
CHALLENGE_MARKERS = [
    ("cloudflare challenge", r"Just a moment\.\.\.|cf-chl-|cf-turnstile|challenges\.cloudflare\.com"),
    ("datadome captcha", r"captcha-delivery\.com"),
    ("perimeterx captcha", r"px-captcha|Press &amp; Hold|Press & Hold"),
    ("kasada challenge", r"KPSDK"),
    ("captcha", r"g-recaptcha|h-captcha|hcaptcha\.com"),
]

# A block page is a plain no.
BLOCK_MARKERS = [
    ("cloudflare block", r"Attention Required! \| Cloudflare|Sorry, you have been blocked"),
    ("akamai block", r"errors\.edgesuite\.net"),
    ("imperva block", r"_Incapsula_Resource"),
]


def judge_page(status, html, expect, reject=None):
    """Return (verdict, reason). The verdict is "pass", "challenge" or "blocked".

    Only the expect pattern decides a pass. A status of 200 is not enough,
    because block pages often return 200. The markers only choose between
    challenge and blocked, and name the reason.
    """
    if reject is not None and re.search(reject, html):
        return "blocked", "page says we are a bot"
    if re.search(expect, html):
        return "pass", ""
    block = _first_match(BLOCK_MARKERS, html)
    if block is not None:
        return "blocked", block
    challenge = _first_match(CHALLENGE_MARKERS, html)
    if challenge is not None:
        return "challenge", challenge
    if status is not None and status >= 400:
        return "blocked", f"http {status}"
    return "blocked", "expected text missing"


def _first_match(markers, html):
    for name, pattern in markers:
        if re.search(pattern, html):
            return name
    return None

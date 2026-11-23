"""Decide if a fetched page is the real page or a block page."""

import re

# Known block pages. Used only to name the reason when the expected text is missing.
MARKERS = [
    ("cloudflare challenge", r"Just a moment\.\.\.|cf-chl-|Attention Required! \| Cloudflare|cf-turnstile"),
    ("datadome captcha", r"captcha-delivery\.com"),
    ("perimeterx captcha", r"px-captcha|Press &amp; Hold|Press & Hold"),
    ("akamai block", r"errors\.edgesuite\.net|sec-if-cpt-container"),
    ("kasada challenge", r"KPSDK"),
    ("imperva block", r"_Incapsula_Resource"),
    ("captcha", r"g-recaptcha|h-captcha|hcaptcha\.com"),
]


def judge(status, html, expect, reject=None):
    """Return (verdict, reason). verdict is "pass" or "blocked".

    A pass needs the expected text. A status of 200 is not enough,
    because block pages often return 200.
    """
    if re.search(expect, html) and not (reject and re.search(reject, html)):
        return "pass", ""
    if reject and re.search(reject, html):
        return "blocked", "page says we are a bot"
    for name, pattern in MARKERS:
        if re.search(pattern, html):
            return "blocked", name
    if status is not None and status >= 400:
        return "blocked", f"http {status}"
    return "blocked", "expected text missing"


def demo():
    assert judge(200, "<h1>Welcome</h1>", "Welcome") == ("pass", "")
    assert judge(200, "<title>Just a moment...</title>", "Welcome") == ("blocked", "cloudflare challenge")
    assert judge(403, "nope", "Welcome") == ("blocked", "http 403")
    assert judge(200, "", "Welcome") == ("blocked", "expected text missing")
    assert judge(200, "Welcome, you are a bot", "Welcome", "you are a bot") == ("blocked", "page says we are a bot")
    # A real page that also embeds a captcha widget still passes.
    assert judge(200, "Welcome <div class=g-recaptcha>", "Welcome") == ("pass", "")
    print("ok")


if __name__ == "__main__":
    demo()

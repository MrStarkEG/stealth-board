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


def demo():
    assert judge(200, "<h1>Welcome</h1>", "Welcome") == ("pass", "")
    assert judge(200, "<title>Just a moment...</title>", "Welcome") == ("challenge", "cloudflare challenge")
    assert judge(403, "<title>Just a moment...</title>", "Welcome") == ("challenge", "cloudflare challenge")
    assert judge(403, "Sorry, you have been blocked <a href=challenges.cloudflare.com>", "Welcome") == ("blocked", "cloudflare block")
    assert judge(403, "nope", "Welcome") == ("blocked", "http 403")
    assert judge(200, "", "Welcome") == ("blocked", "expected text missing")
    assert judge(200, "Welcome, you are a bot", "Welcome", "you are a bot") == ("blocked", "page says we are a bot")
    # A real page that also embeds a captcha widget still passes.
    assert judge(200, "Welcome <div class=g-recaptcha>", "Welcome") == ("pass", "")
    print("ok")


if __name__ == "__main__":
    demo()

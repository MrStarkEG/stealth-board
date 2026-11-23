# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["curl_cffi"]
# ///
"""curl_cffi: an HTTP client that copies Chrome's TLS and HTTP/2 fingerprint.
It does not run JavaScript, so it cannot solve a challenge page.
Settings from its README: impersonate="chrome" follows the newest Chrome profile."""

import curl_cffi

from _common import run


def fetch(url, headless):
    r = curl_cffi.get(url, impersonate="chrome", timeout=30)
    return r.status_code, r.text


run("curl_cffi", fetch)

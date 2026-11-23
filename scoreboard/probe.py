"""Look at a website before you add it as a target.

    python -m scoreboard.probe https://www.example-shop.com/

It loads the page once with a plain HTTP client and prints what protection
it sees. It does not change any file.
"""

import argparse
import re
import urllib.error
import urllib.request

from scoreboard.verdict import judge

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"

# How each vendor shows up in a response. "headers" is matched against the raw
# header lines, "body" against the page. Add a line here when you meet a new vendor.
SIGNS = [
    ("Cloudflare", r"(?im)^server: cloudflare|^cf-ray:", r"Just a moment\.\.\.|challenges\.cloudflare\.com"),
    ("DataDome", r"(?im)^x-datadome|^set-cookie: datadome=", r"captcha-delivery\.com"),
    ("HUMAN (PerimeterX)", r"(?im)^set-cookie: _px|^x-px", r"px-captcha"),
    ("Akamai", r"(?im)^set-cookie: (_abck|bm_sz|ak_bmsc)=|^server: akamai", r"errors\.edgesuite\.net"),
    ("Kasada", r"(?im)^x-kpsdk", r"KPSDK"),
    ("Imperva", r"(?im)^set-cookie: (incap_ses|visid_incap)|^x-iinfo:", r"_Incapsula_Resource"),
    ("AWS WAF", r"(?im)^x-amzn-waf|^set-cookie: aws-waf-token", r"awswaf"),
]


def detect(headers, body):
    """Return [(vendor, where)] for every vendor seen. where is "headers", "page" or "headers and page"."""
    seen = []
    for vendor, in_headers, in_body in SIGNS:
        places = [name for name, pattern, text in (("headers", in_headers, headers), ("page", in_body, body)) if re.search(pattern, text)]
        if places:
            seen.append((vendor, " and ".join(places)))
    return seen


def get(url):
    """Return (status, raw header lines, body) for one plain GET."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(request, timeout=30) as r:
            return r.status, str(r.headers), r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, str(e.headers), e.read().decode(errors="replace")


def report(url, status, headers, body):
    """Return the lines to print."""
    title = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
    seen = detect(headers, body)
    verdict, reason = judge(status, body, r"\A(?!)")  # a pattern that never matches: we only want the reason
    lines = [
        f"url      {url}",
        f"status   {status}",
        f"title    {title.group(1).strip()[:80] if title else '(none)'}",
        f"size     {len(body)} characters",
        "vendor   " + (", ".join(f"{v} (seen in {w})" for v, w in seen) if seen else "none seen in this response"),
    ]
    if verdict == "challenge" or status >= 400:
        lines.append(f"plain client: stopped ({reason}). This page tells tools apart, so it can be a target.")
    else:
        lines.append("plain client: got a page. If this is the real page, the site does not block plain tools, and it is a weak target.")
    lines += [
        "",
        "Next: add a draft [[target]] to scoreboard.toml, then see which tools get in:",
        "  python -m scoreboard.run --target NEW_ID --tool playwright --tool patchright --tool camoufox --tries 1 --debug-dir debug",
    ]
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    args = ap.parse_args()
    print("\n".join(report(args.url, *get(args.url))))


if __name__ == "__main__":
    main()

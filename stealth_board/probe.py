"""Look at a website before you add it as a target.

    python -m stealth_board.probe https://www.example-shop.com/

It loads the page once with a plain HTTP client and prints what protection
it sees. It does not change any file.
"""

import argparse
import re
import urllib.error
import urllib.request

from stealth_board.verdict import judge_page

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
NEVER_MATCHES = r"\A(?!)"

# (vendor, pattern for the raw header lines, pattern for the page).
# Add a line when you meet a new vendor.
VENDOR_SIGNS = [
    ("Cloudflare", r"(?im)^server: cloudflare|^cf-ray:", r"Just a moment\.\.\.|challenges\.cloudflare\.com"),
    ("DataDome", r"(?im)^x-datadome|^set-cookie: datadome=", r"captcha-delivery\.com"),
    ("HUMAN (PerimeterX)", r"(?im)^set-cookie: _px|^x-px", r"px-captcha"),
    ("Akamai", r"(?im)^set-cookie: (_abck|bm_sz|ak_bmsc)=|^server: akamai", r"errors\.edgesuite\.net"),
    ("Kasada", r"(?im)^x-kpsdk", r"KPSDK"),
    ("Imperva", r"(?im)^set-cookie: (incap_ses|visid_incap)|^x-iinfo:", r"_Incapsula_Resource"),
    ("AWS WAF", r"(?im)^x-amzn-waf|^set-cookie: aws-waf-token", r"awswaf"),
]


def detect_vendors(headers, page):
    """Return (vendor, where) for every vendor seen in the response."""
    seen = []
    for vendor, header_pattern, page_pattern in VENDOR_SIGNS:
        places = []
        if re.search(header_pattern, headers):
            places.append("headers")
        if re.search(page_pattern, page):
            places.append("page")
        if places:
            seen.append((vendor, " and ".join(places)))
    return seen


def describe_vendors(vendors):
    if not vendors:
        return "none seen in this response"
    return ", ".join(f"{vendor} (seen in {where})" for vendor, where in vendors)


def fetch_plain(url):
    """Return (status, raw header lines, page) for one plain GET."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, str(response.headers), response.read().decode(errors="replace")
    except urllib.error.HTTPError as error:
        with error:
            return error.code, str(error.headers), error.read().decode(errors="replace")


def describe(url, status, headers, page):
    """Return the report as a list of lines."""
    title = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
    vendors = detect_vendors(headers, page)
    # The pattern never matches, so this only tells us how a failed page would be named.
    verdict, reason = judge_page(status, page, expect=NEVER_MATCHES)
    was_stopped = verdict == "challenge" or status >= 400

    lines = [
        f"url      {url}",
        f"status   {status}",
        f"title    {title.group(1).strip()[:80] if title else '(none)'}",
        f"size     {len(page)} characters",
        f"vendor   {describe_vendors(vendors)}",
    ]
    if was_stopped:
        lines.append(f"plain client: stopped ({reason}). This page tells tools apart, so it can be a target.")
    else:
        lines.append("plain client: got a page. If this is the real page, the site does not block plain tools, and it is a weak target.")
    lines += [
        "",
        "Next: add a draft [[target]] to board.toml, then see which tools get in:",
        "  python -m stealth_board.run --target NEW_ID --tool playwright --tool patchright --tool camoufox --tries 1 --debug-dir debug",
    ]
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url")
    args = parser.parse_args()
    print("\n".join(describe(args.url, *fetch_plain(args.url))))


if __name__ == "__main__":
    main()

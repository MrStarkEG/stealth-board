"""Check the verdict rules on sample pages.

Each file in tests/pages/ is a small copy of a page type we met on real sites.
When you add a marker to stealth_board/verdict.py, add a sample page and a line here.
"""

import unittest
from pathlib import Path

from stealth_board.verdict import judge_page

PAGES = Path(__file__).parent / "pages"
EXPECT = "Garden Tools"

# file, status, verdict, reason
CASES = [
    ("real-page.html", 200, "pass", ""),
    ("cloudflare-challenge.html", 403, "challenge", "cloudflare challenge"),
    ("cloudflare-block.html", 403, "blocked", "cloudflare block"),
    ("datadome-captcha.html", 403, "challenge", "datadome captcha"),
    ("perimeterx-captcha.html", 403, "challenge", "perimeterx captcha"),
    ("akamai-denied.html", 403, "blocked", "akamai block"),
    ("plain-403.html", 403, "blocked", "http 403"),
    ("empty-shell.html", 200, "blocked", "expected text missing"),
]


class VerdictTest(unittest.TestCase):
    def test_sample_pages(self):
        for name, status, verdict, reason in CASES:
            with self.subTest(page=name):
                self.assertEqual(judge_page(status, (PAGES / name).read_text(), EXPECT), (verdict, reason))

    def test_every_sample_page_has_a_case(self):
        self.assertEqual({p.name for p in PAGES.glob("*.html")}, {c[0] for c in CASES})

    def test_status_200_is_not_a_pass(self):
        # Block pages often come back with 200.
        self.assertEqual(judge_page(200, (PAGES / "cloudflare-challenge.html").read_text(), EXPECT)[0], "challenge")

    def test_real_page_with_a_captcha_widget_still_passes(self):
        html = (PAGES / "real-page.html").read_text() + '<div class="g-recaptcha"></div>'
        self.assertEqual(judge_page(200, html, EXPECT), ("pass", ""))

    def test_reject_beats_expect(self):
        html = "<h1>Garden Tools</h1><p>You are a bot!</p>"
        self.assertEqual(judge_page(200, html, EXPECT, "You are a bot"), ("blocked", "page says we are a bot"))


if __name__ == "__main__":
    unittest.main()

"""Check the 7 and 30 day pass rates on made-up history."""

import unittest

from scoreboard.build import build

CONFIG = {
    "tool": [
        {"name": "plain", "modes": ["http"], "control": True},
        {"name": "stealth", "modes": ["headless"]},
        {"name": "dead", "modes": ["headless", "headed"]},
    ],
    "target": [
        {"id": "open", "kind": "open"},
        {"id": "shop", "kind": "site"},
        {"id": "weak", "kind": "site"},
        {"id": "wall", "kind": "site"},
    ],
}


def record(date, tool, mode, verdicts, ip_type="datacenter"):
    """verdicts: {target: "pass pass blocked"}"""
    tries = {t: [{"verdict": v, "reason": "" if v == "pass" else "http 403"} for v in vs.split()] for t, vs in verdicts.items()}
    return {"date": date, "tool": tool, "version": "1.0", "setup": "ok", "setup_error": None, "ip_type": ip_type, "modes": {mode: tries}}


class BuildTest(unittest.TestCase):
    def setUp(self):
        records = []
        # stealth: passes shop every day for 30 days, then fails the last 2 days.
        for day in range(1, 31):
            ok = "pass pass" if day <= 28 else "blocked blocked"
            records.append(record(f"2026-06-{day:02}", "stealth", "headless", {"open": "pass", "shop": ok, "weak": "pass", "wall": "blocked"}))
            records.append(record(f"2026-06-{day:02}", "plain", "http", {"open": "pass", "shop": "blocked", "weak": "pass", "wall": "blocked"}))
        records.append(record("2026-05-20", "stealth", "headless", {"shop": "blocked"}))  # older than 30 days
        records.append(record("2026-06-30", "stealth", "headless", {"shop": "pass"}, ip_type="residential"))
        records.append({"date": "2026-06-30", "tool": "dead", "version": None, "setup": "broken", "setup_error": "no wheel", "ip_type": "datacenter", "modes": {}})
        self.data = build(records, CONFIG)
        self.board = self.data["boards"]["datacenter"]
        self.rows = {(r["tool"], r["mode"]): r for r in self.board["rows"]}

    def test_rates(self):
        shop = self.rows[("stealth", "headless")]["cells"]["shop"]
        # last 7 days = June 24..30: 5 good days and 2 bad days, 2 tries each
        self.assertEqual((shop["p7"], shop["n7"]), (10, 14))
        # last 30 days = June 1..30: 28 good days and 2 bad days. May 20 is out.
        self.assertEqual((shop["p30"], shop["n30"]), (56, 60))
        self.assertEqual(shop["reason"], "http 403")
        self.assertEqual((shop["blocked"], shop["challenge"], shop["error"], shop["clicks"]), (4, 0, 0, 0))

    def test_kinds_of_result(self):
        tries = [
            {"verdict": "pass", "reason": "", "clicked": True},
            {"verdict": "pass", "reason": "", "clicked": None},
            {"verdict": "challenge", "reason": "cloudflare challenge", "clicked": True},
            {"verdict": "error", "reason": "timeout after 90s", "clicked": False},
        ]
        rec = {"date": "2026-06-30", "tool": "stealth", "version": "1", "setup": "ok", "setup_error": None, "ip_type": "x", "modes": {"headless": {"shop": tries}}}
        cell = build([rec], CONFIG)["boards"]["x"]["rows"][0]["cells"]["shop"]
        self.assertEqual((cell["p7"], cell["n7"]), (2, 4))
        self.assertEqual((cell["clicks"], cell["challenge"], cell["blocked"], cell["error"]), (1, 1, 0, 1))

    def test_overall_score_skips_open_targets(self):
        row = self.rows[("stealth", "headless")]
        # shop 10/14 + weak 7/7 + wall 0/7; the open target is not counted
        self.assertEqual((row["p7"], row["n7"]), (17, 28))
        self.assertEqual(row["daily"][-1], round(1 / 4, 3))
        self.assertEqual(len(row["daily"]), 30)

    def test_flags(self):
        self.assertIn("plain tool opens", self.board["flags"]["weak"])
        self.assertIn("No tool opened", self.board["flags"]["wall"])
        self.assertNotIn("shop", self.board["flags"])
        self.assertNotIn("open", self.board["flags"])

    def test_broken_tool_is_one_row_at_the_bottom(self):
        self.assertEqual(self.rows[("dead", "headless")]["broken"], "no wheel")
        self.assertNotIn(("dead", "headed"), self.rows)
        self.assertEqual(self.board["rows"][-1]["tool"], "dead")

    def test_ip_types_are_separate(self):
        res = self.data["boards"]["residential"]["rows"]
        cell = next(r for r in res if r["tool"] == "stealth")["cells"]["shop"]
        self.assertEqual((cell["p7"], cell["n7"]), (1, 1))

    def test_no_results(self):
        self.assertEqual(build([], CONFIG)["boards"], {})


if __name__ == "__main__":
    unittest.main()

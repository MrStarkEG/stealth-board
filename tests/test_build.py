"""The dashboard numbers, checked on made-up history."""

import dataclasses
import unittest

from stealth_board.build import build_dashboard_data
from stealth_board.config import Config, Target, Tool


def target(target_id, kind="site"):
    return Target(id=target_id, name=target_id, kind=kind, vendor="x", url=f"https://{target_id}.example/", expect="x")


CONFIG = Config(
    tries=2,
    timeout=90,
    click=True,
    tools=(
        Tool(name="plain", modes=("http",), control=True),
        Tool(name="stealth", modes=("headless",)),
        Tool(name="dead", modes=("headless", "headed")),
    ),
    targets=(target("open", kind="open"), target("shop"), target("weak"), target("wall")),
)


def record(date, tool, mode, verdicts, ip_type="datacenter"):
    """verdicts: {target: "pass pass blocked"}"""
    tries = {
        target_id: [
            {"verdict": verdict, "reason": "" if verdict == "pass" else "http 403", "clicked": False}
            for verdict in words.split()
        ]
        for target_id, words in verdicts.items()
    }
    return {
        "date": date, "tool": tool, "version": "1.0", "setup": "ok", "setup_error": None,
        "ip_type": ip_type, "modes": {mode: tries},
    }


def broken_record(date, tool):
    return {
        "date": date, "tool": tool, "version": None, "setup": "broken", "setup_error": "no wheel",
        "ip_type": "datacenter", "modes": {},
    }


class BuildTest(unittest.TestCase):
    def setUp(self):
        records = []
        # stealth opens shop every day of June, then fails on the last 2 days.
        for day in range(1, 31):
            date = f"2026-06-{day:02}"
            shop = "pass pass" if day <= 28 else "blocked blocked"
            records.append(record(date, "stealth", "headless", {"open": "pass", "shop": shop, "weak": "pass", "wall": "blocked"}))
            records.append(record(date, "plain", "http", {"open": "pass", "shop": "blocked", "weak": "pass", "wall": "blocked"}))
        records.append(record("2026-05-20", "stealth", "headless", {"shop": "blocked"}))  # older than 30 days
        records.append(record("2026-06-30", "stealth", "headless", {"shop": "pass"}, ip_type="residential"))
        records.append(broken_record("2026-06-30", "dead"))

        self.data = build_dashboard_data(records, CONFIG)
        self.board = self.data["boards"]["datacenter"]
        self.rows = {(row["tool"], row["mode"]): row for row in self.board["rows"]}

    def test_cell_counts(self):
        shop = self.rows["stealth", "headless"]["cells"]["shop"]
        # 7 days = June 24..30: 5 good days and 2 bad days, 2 tries each.
        self.assertEqual((shop["passed_7d"], shop["tries_7d"]), (10, 14))
        # 30 days = June 1..30: 28 good days and 2 bad days. May 20 is out.
        self.assertEqual((shop["passed_30d"], shop["tries_30d"]), (56, 60))
        self.assertEqual(shop["last_failure"], "http 403")
        self.assertEqual((shop["blocked"], shop["challenge"], shop["error"], shop["after_click"]), (4, 0, 0, 0))

    def test_row_score_skips_open_targets(self):
        row = self.rows["stealth", "headless"]
        # shop 10/14 + weak 7/7 + wall 0/7. The open target is not counted.
        self.assertEqual((row["passed_7d"], row["tries_7d"]), (17, 28))
        self.assertEqual(len(row["daily"]), 30)
        self.assertEqual(row["daily"][-1], 0.25)

    def test_outcomes_and_clicks(self):
        tries = [
            {"verdict": "pass", "reason": "", "clicked": True},
            {"verdict": "pass", "reason": "", "clicked": None},
            {"verdict": "challenge", "reason": "cloudflare challenge", "clicked": True},
            {"verdict": "error", "reason": "timeout after 90s", "clicked": False},
        ]
        one_record = {
            "date": "2026-06-30", "tool": "stealth", "version": "1", "setup": "ok", "setup_error": None,
            "ip_type": "datacenter", "modes": {"headless": {"shop": tries}},
        }
        cell = build_dashboard_data([one_record], CONFIG)["boards"]["datacenter"]["rows"][0]["cells"]["shop"]
        self.assertEqual((cell["passed_7d"], cell["tries_7d"]), (2, 4))
        self.assertEqual((cell["after_click"], cell["challenge"], cell["blocked"], cell["error"]), (1, 1, 0, 1))
        self.assertEqual(cell["last_failure"], "timeout after 90s")

    def test_weak_targets_are_flagged(self):
        flags = self.board["flags"]
        self.assertIn("plain tool opens", flags["weak"])
        self.assertIn("No tool opened", flags["wall"])
        self.assertNotIn("shop", flags)
        self.assertNotIn("open", flags)

    def test_broken_tool_is_one_row_at_the_bottom(self):
        self.assertEqual(self.rows["dead", "headless"]["broken"], "no wheel")
        self.assertNotIn(("dead", "headed"), self.rows)
        self.assertEqual(self.board["rows"][-1]["tool"], "dead")

    def test_a_mode_that_never_ran_has_no_row(self):
        config = dataclasses.replace(CONFIG, tools=(Tool(name="stealth", modes=("headless", "headed")),))
        only_headless = [record("2026-06-30", "stealth", "headless", {"shop": "pass"})]
        rows = build_dashboard_data(only_headless, config)["boards"]["datacenter"]["rows"]
        self.assertEqual([row["mode"] for row in rows], ["headless"])

    def test_best_score_comes_first(self):
        self.assertEqual(self.board["rows"][0]["tool"], "stealth")

    def test_ip_types_are_separate(self):
        rows = self.data["boards"]["residential"]["rows"]
        cell = next(row for row in rows if row["tool"] == "stealth")["cells"]["shop"]
        self.assertEqual((cell["passed_7d"], cell["tries_7d"]), (1, 1))

    def test_no_results(self):
        data = build_dashboard_data([], CONFIG)
        self.assertEqual(data["boards"], {})
        self.assertEqual(len(data["targets"]), 4)


if __name__ == "__main__":
    unittest.main()

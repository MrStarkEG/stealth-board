"""Turn the saved results into site/data.json for the dashboard.

    python -m stealth_board.build
"""

import argparse
import dataclasses
import datetime
import json
from collections import defaultdict
from pathlib import Path

from stealth_board.config import load_config

WEEK_DAYS = 7
MONTH_DAYS = 30

CONTROL_OPENS_IT = "A plain tool opens this target, so it shows little."
NOTHING_OPENS_IT = "No tool opened this target in 7 days. The target or its check may need a look."


class History:
    """The tries of one IP type, looked up by tool, mode, target and day."""

    def __init__(self, records):
        self.tries = defaultdict(list)  # (tool, mode, target, day) -> tries
        self.latest_record = {}  # tool -> its newest record
        self.tool_modes = set()
        for record in sorted(records, key=lambda record: record["date"]):
            self.latest_record[record["tool"]] = record
            for mode, tries_by_target in record["modes"].items():
                self.tool_modes.add((record["tool"], mode))
                for target, tries in tries_by_target.items():
                    self.tries[record["tool"], mode, target, record["date"]] += tries

    def tries_on(self, tool, mode, target, days):
        return [one_try for day in days for one_try in self.tries[tool, mode, target, day]]


def build_dashboard_data(records, config):
    targets = [dataclasses.asdict(target) for target in config.targets]
    tools = [dataclasses.asdict(tool) for tool in config.tools]
    if not records:
        return {"generated": None, "targets": targets, "tools": tools, "boards": {}}

    newest_day = max(record["date"] for record in records)
    month = days_ending(newest_day, MONTH_DAYS)
    week = month[-WEEK_DAYS:]
    boards = {}
    for ip_type in sorted({record["ip_type"] for record in records}):
        history = History(r for r in records if r["ip_type"] == ip_type and r["date"] in month)
        boards[ip_type] = {
            "rows": build_rows(history, config, week, month),
            "flags": find_weak_targets(history, config, week),
        }
    return {"generated": newest_day, "targets": targets, "tools": tools, "boards": boards}


def days_ending(last_day, count):
    """The ISO dates of the count days that end with last_day, oldest first."""
    last = datetime.date.fromisoformat(last_day)
    return [(last - datetime.timedelta(days=back)).isoformat() for back in range(count - 1, -1, -1)]


def find_weak_targets(history, config, week):
    """Protected targets that prove little: a control opens them, or nothing does."""
    controls = {tool.name for tool in config.tools if tool.control}
    flags = {}
    for target in config.targets:
        if not target.is_scored:
            continue
        counts = {
            (tool, mode): count_passes(history.tries_on(tool, mode, target.id, week))
            for tool, mode in history.tool_modes
        }
        control_opens_it = any(
            total > 0 and passed * 2 >= total for (tool, _), (passed, total) in counts.items() if tool in controls
        )
        was_tested = any(total for _, total in counts.values())
        was_opened = any(passed for passed, _ in counts.values())
        if control_opens_it:
            flags[target.id] = CONTROL_OPENS_IT
        elif was_tested and not was_opened:
            flags[target.id] = NOTHING_OPENS_IT
    return flags


def build_rows(history, config, week, month):
    rows = []
    for tool in config.tools:
        if tool.name not in history.latest_record:
            continue
        latest = history.latest_record[tool.name]
        if latest["setup"] == "broken":
            rows.append(build_row(history, tool, tool.modes[0], latest, config, week, month))
        else:
            tested_modes = [mode for mode in tool.modes if (tool.name, mode) in history.tool_modes]
            rows += [build_row(history, tool, mode, latest, config, week, month) for mode in tested_modes]
    rows.sort(key=row_order)
    return rows


def build_row(history, tool, mode, latest, config, week, month):
    cells = {target.id: build_cell(history, tool.name, mode, target.id, week, month) for target in config.targets}
    scored = [cells[target.id] for target in config.targets if target.is_scored]
    scored_ids = [target.id for target in config.targets if target.is_scored]
    return {
        "tool": tool.name,
        "mode": mode,
        "control": tool.control,
        "version": latest["version"],
        "last_run": latest["date"],
        "broken": latest["setup_error"] if latest["setup"] == "broken" else None,
        "passed_7d": sum(cell["passed_7d"] for cell in scored),
        "tries_7d": sum(cell["tries_7d"] for cell in scored),
        "passed_30d": sum(cell["passed_30d"] for cell in scored),
        "tries_30d": sum(cell["tries_30d"] for cell in scored),
        "daily": [daily_score(history, tool.name, mode, scored_ids, day) for day in month],
        "cells": cells,
    }


def build_cell(history, tool, mode, target, week, month):
    week_tries = history.tries_on(tool, mode, target, week)
    month_tries = history.tries_on(tool, mode, target, month)
    passed_7d, tries_7d = count_passes(week_tries)
    passed_30d, tries_30d = count_passes(month_tries)
    failures = [one_try["reason"] for one_try in month_tries if one_try["verdict"] != "pass"]
    return {
        "passed_7d": passed_7d,
        "tries_7d": tries_7d,
        "passed_30d": passed_30d,
        "tries_30d": tries_30d,
        "last_failure": failures[-1] if failures else "",
        **count_outcomes(week_tries),
    }


def daily_score(history, tool, mode, target_ids, day):
    """The share of tries that passed on one day, or None when nothing ran."""
    tries = [one_try for target in target_ids for one_try in history.tries_on(tool, mode, target, [day])]
    passed, total = count_passes(tries)
    return round(passed / total, 3) if total else None


def count_passes(tries):
    return sum(one_try["verdict"] == "pass" for one_try in tries), len(tries)


def count_outcomes(tries):
    """How the tries ended, plus how many passes needed a click."""

    def count(verdict):
        return sum(one_try["verdict"] == verdict for one_try in tries)

    return {
        "after_click": sum(one_try["verdict"] == "pass" and one_try["clicked"] is True for one_try in tries),
        "challenge": count("challenge"),
        "blocked": count("blocked"),
        "error": count("error"),
    }


def row_order(row):
    """Best score first, broken tools last."""
    score = row["passed_7d"] / row["tries_7d"] if row["tries_7d"] else 0
    return (row["broken"] is not None, -score, row["tool"], row["mode"])


def load_records(results_dir):
    return [json.loads(path.read_text()) for path in sorted(Path(results_dir).glob("*/*.json"))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="board.toml")
    parser.add_argument("--adapters", default="adapters")
    parser.add_argument("--results", default="results")
    parser.add_argument("--out", default="site/data.json")
    args = parser.parse_args()

    config = load_config(args.config, args.adapters)
    data = build_dashboard_data(load_records(args.results), config)
    Path(args.out).write_text(json.dumps(data, separators=(",", ":")))
    print(f"wrote {args.out} for {data['generated']}")


if __name__ == "__main__":
    main()

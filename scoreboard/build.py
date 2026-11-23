"""Turn the saved results into site/data.json for the dashboard.

    python -m scoreboard.build
"""

import argparse
import datetime
import json
import tomllib
from collections import defaultdict
from pathlib import Path


def load(results_dir):
    return [json.loads(p.read_text()) for p in sorted(Path(results_dir).glob("*/*.json"))]


def rate(tries):
    """(passes, total) for a list of tries."""
    return sum(t["verdict"] == "pass" for t in tries), len(tries)


def build(records, config, today=None):
    """Return the dashboard data. today defaults to the newest date in the results."""
    if not records:
        return {"generated": None, "targets": config["target"], "tools": config["tool"], "boards": {}}
    today = today or max(r["date"] for r in records)
    day = datetime.date.fromisoformat(today)
    since7 = (day - datetime.timedelta(days=6)).isoformat()
    since30 = (day - datetime.timedelta(days=29)).isoformat()
    records = [r for r in records if since30 <= r["date"] <= today]
    controls = {t["name"] for t in config["tool"] if t.get("control")}
    open_targets = {t["id"] for t in config["target"] if t["kind"] == "open"}
    target_ids = [t["id"] for t in config["target"]]

    boards = {}
    for ip_type in sorted({r["ip_type"] for r in records}):
        # tries[(tool, mode)][target][date] = list of tries
        tries = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        latest = {}  # tool -> newest record
        for r in (r for r in records if r["ip_type"] == ip_type):
            if r["tool"] not in latest or r["date"] >= latest[r["tool"]]["date"]:
                latest[r["tool"]] = r
            for mode, by_target in r["modes"].items():
                for target, ts in by_target.items():
                    tries[(r["tool"], mode)][target][r["date"]] += ts

        def window(tool_mode, target, since):
            by_date = tries[tool_mode][target]
            return [t for d, ts in by_date.items() if d >= since for t in ts]

        # A protected target that a control opens, or that nothing opens, proves little.
        flags = {}
        for target in target_ids:
            if target in open_targets:
                continue
            passes = {tm: rate(window(tm, target, since7)) for tm in tries}
            control_pass = any(p * 2 >= n > 0 for (tool, _), (p, n) in passes.items() if tool in controls)
            tested = any(n for _, n in passes.values())
            if control_pass:
                flags[target] = "A plain tool opens this target, so it shows little."
            elif tested and not any(p for p, _ in passes.values()):
                flags[target] = "No tool opened this target in 7 days. The target or its check may need a look."

        scored = [t for t in target_ids if t not in open_targets]
        rows = []
        for tool in config["tool"]:
            last = latest.get(tool["name"])
            modes = tool["modes"] if last else []
            if last and last["setup"] == "broken":
                modes = modes[:1]
            for mode in modes:
                tm = (tool["name"], mode)
                cells = {}
                for target in target_ids:
                    p7, n7 = rate(window(tm, target, since7))
                    p30, n30 = rate(window(tm, target, since30))
                    by_date = tries[tm][target]
                    newest = by_date[max(by_date)] if by_date else []
                    reasons = [t["reason"] for t in newest if t["verdict"] != "pass"]
                    cells[target] = {"p7": p7, "n7": n7, "p30": p30, "n30": n30, "reason": reasons[-1] if reasons else ""}
                daily = []
                for back in range(29, -1, -1):
                    d = (day - datetime.timedelta(days=back)).isoformat()
                    p, n = rate([t for target in scored for t in tries[tm][target].get(d, [])])
                    daily.append(round(p / n, 3) if n else None)
                s7 = [sum(x) for x in zip(*[(cells[t]["p7"], cells[t]["n7"]) for t in scored])] if scored else [0, 0]
                s30 = [sum(x) for x in zip(*[(cells[t]["p30"], cells[t]["n30"]) for t in scored])] if scored else [0, 0]
                rows.append({
                    "tool": tool["name"], "mode": mode, "control": bool(tool.get("control")),
                    "version": last["version"], "last_run": last["date"],
                    "broken": last["setup_error"] if last["setup"] == "broken" else None,
                    "p7": s7[0], "n7": s7[1], "p30": s30[0], "n30": s30[1],
                    "cells": cells, "daily": daily,
                })
        rows.sort(key=lambda r: (r["broken"] is not None, -(r["p7"] / r["n7"] if r["n7"] else 0), r["tool"]))
        boards[ip_type] = {"rows": rows, "flags": flags}
    return {"generated": today, "targets": config["target"], "tools": config["tool"], "boards": boards}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default="scoreboard.toml")
    ap.add_argument("--results", default="results")
    ap.add_argument("--out", default="site/data.json")
    args = ap.parse_args()
    config = tomllib.loads(Path(args.config).read_text())
    data = build(load(args.results), config)
    Path(args.out).write_text(json.dumps(data, separators=(",", ":")))
    print(f"wrote {args.out} for {data['generated']}")


if __name__ == "__main__":
    main()

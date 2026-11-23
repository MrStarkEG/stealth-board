"""Check that board.toml is valid, before a run wastes an hour on a typo.

    python -m stealth_board.check
"""

import argparse
import re
import sys
import tomllib
from pathlib import Path

MODES = {"http", "headless", "headed"}
KINDS = {"open", "test", "site"}
TARGET_FIELDS = ("id", "name", "kind", "vendor", "url", "expect")


def problems(config, adapters_dir="adapters"):
    """Return a list of problems as plain sentences. Empty means the config is fine."""
    found = []
    for key, kind in (("tries", int), ("timeout", int), ("click", bool)):
        if type(config.get(key)) is not kind:
            found.append(f"'{key}' at the top must be a {kind.__name__}.")
    if type(config.get("tries")) is int and config["tries"] < 1:
        found.append("'tries' must be 1 or more.")

    names = [t.get("name") for t in config.get("tool", [])]
    if not names:
        found.append("There is no [[tool]].")
    for tool in config.get("tool", []):
        name = tool.get("name")
        if not name:
            found.append("A [[tool]] has no name.")
            continue
        if names.count(name) > 1:
            found.append(f"Tool '{name}' is listed more than once.")
        modes = tool.get("modes")
        if not modes or not set(modes) <= MODES:
            found.append(f"Tool '{name}': modes must be a list with some of {sorted(MODES)}.")
        if not (Path(adapters_dir) / f"{name}_adapter.py").exists():
            found.append(f"Tool '{name}': the file {adapters_dir}/{name}_adapter.py does not exist.")

    ids = [t.get("id") for t in config.get("target", [])]
    if not ids:
        found.append("There is no [[target]].")
    for target in config.get("target", []):
        tid = target.get("id")
        if not tid:
            found.append("A [[target]] has no id.")
            continue
        if ids.count(tid) > 1:
            found.append(f"Target '{tid}' is listed more than once.")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", tid):
            found.append(f"Target '{tid}': the id may only use small letters, digits and '-'.")
        missing = [f for f in TARGET_FIELDS if not target.get(f)]
        if missing:
            found.append(f"Target '{tid}': missing {', '.join(missing)}.")
        if target.get("kind") and target["kind"] not in KINDS:
            found.append(f"Target '{tid}': kind must be one of {sorted(KINDS)}.")
        if target.get("url") and not target["url"].startswith("https://"):
            found.append(f"Target '{tid}': the url must start with https://.")
        for field in ("expect", "reject"):
            if target.get(field):
                try:
                    re.compile(target[field])
                except re.error as e:
                    found.append(f"Target '{tid}': '{field}' is not a valid regular expression ({e}).")
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="board.toml")
    ap.add_argument("--adapters", default="adapters")
    args = ap.parse_args()
    config = tomllib.loads(Path(args.config).read_text())
    found = problems(config, args.adapters)
    for line in found:
        print("problem:", line)
    if found:
        sys.exit(1)
    print(f"{args.config} is fine: {len(config['tool'])} tools, {len(config['target'])} targets.")


if __name__ == "__main__":
    main()

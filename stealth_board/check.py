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
SETTINGS = {"tries": int, "timeout": int, "click": bool}
TOOL_FIELDS = {"name", "modes", "control"}
TARGET_REQUIRED = ("id", "name", "kind", "vendor", "url", "expect")
TARGET_FIELDS = {*TARGET_REQUIRED, "reject"}


def find_problems(raw, adapters_dir):
    """Return every problem in the raw config as a plain sentence. Empty means it is fine."""
    return [
        *_settings_problems(raw),
        *_tool_problems(raw, Path(adapters_dir)),
        *_target_problems(raw),
    ]


def _settings_problems(raw):
    problems = []
    for key, kind in SETTINGS.items():
        if key not in raw or type(raw[key]) is not kind:
            problems.append(f"'{key}' at the top must be a {kind.__name__}.")
        elif kind is int and raw[key] < 1:
            problems.append(f"'{key}' must be 1 or more.")
    return problems


def _tool_problems(raw, adapters_dir):
    if "tool" not in raw or not raw["tool"]:
        return ["There is no [[tool]]."]
    problems = []
    names = [tool["name"] for tool in raw["tool"] if "name" in tool]
    for tool in raw["tool"]:
        if "name" not in tool:
            problems.append("A [[tool]] has no name.")
            continue
        name = tool["name"]
        if names.count(name) > 1:
            problems.append(f"Tool '{name}' is listed more than once.")
        if "modes" not in tool or not tool["modes"] or not set(tool["modes"]) <= MODES:
            problems.append(f"Tool '{name}': modes must be a list with some of {sorted(MODES)}.")
        if not (adapters_dir / f"{name}_adapter.py").exists():
            problems.append(f"Tool '{name}': the file {adapters_dir.name}/{name}_adapter.py does not exist.")
        problems += _unknown_field_problems(f"Tool '{name}'", tool, TOOL_FIELDS)
    return problems


def _target_problems(raw):
    if "target" not in raw or not raw["target"]:
        return ["There is no [[target]]."]
    problems = []
    ids = [target["id"] for target in raw["target"] if "id" in target]
    for target in raw["target"]:
        if "id" not in target:
            problems.append("A [[target]] has no id.")
            continue
        label = f"Target '{target['id']}'"
        if ids.count(target["id"]) > 1:
            problems.append(f"{label} is listed more than once.")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", target["id"]):
            problems.append(f"{label}: the id may only use small letters, digits and '-'.")
        missing = [field for field in TARGET_REQUIRED if field not in target or not target[field]]
        if missing:
            problems.append(f"{label}: missing {', '.join(missing)}.")
        if "kind" in target and target["kind"] not in KINDS:
            problems.append(f"{label}: kind must be one of {sorted(KINDS)}.")
        if "url" in target and not target["url"].startswith("https://"):
            problems.append(f"{label}: the url must start with https://.")
        for field in ("expect", "reject"):
            if field in target and not _is_valid_pattern(target[field]):
                problems.append(f"{label}: '{field}' is not a valid regular expression.")
        problems += _unknown_field_problems(label, target, TARGET_FIELDS)
    return problems


def _unknown_field_problems(label, entry, known_fields):
    return [f"{label}: unknown field '{field}'." for field in entry if field not in known_fields]


def _is_valid_pattern(pattern):
    try:
        re.compile(pattern)
    except re.error:
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="board.toml")
    parser.add_argument("--adapters", default="adapters")
    args = parser.parse_args()

    raw = tomllib.loads(Path(args.config).read_text())
    problems = find_problems(raw, args.adapters)
    for problem in problems:
        print("problem:", problem)
    if problems:
        sys.exit(1)
    print(f"{args.config} is fine: {len(raw['tool'])} tools, {len(raw['target'])} targets.")


if __name__ == "__main__":
    main()

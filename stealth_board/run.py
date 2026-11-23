"""Run tools against targets and save the results as JSON.

    python -m stealth_board.run --runner vps --ip-type datacenter
    python -m stealth_board.run --tool patchright --target etsy --tries 1
"""

import argparse
import dataclasses
import datetime
import json
import os
import re
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from stealth_board.config import ConfigError, load_config
from stealth_board.process import run_command
from stealth_board.verdict import judge_page

SETUP_TIMEOUT_SECONDS = 900  # browser downloads can be slow
ERROR_MAX_LENGTH = 300

# How many tools run at the same time when --jobs is not given.
MEMORY_GB_PER_JOB = 4
MAX_AUTO_JOBS = 4


@dataclass(frozen=True)
class Page:
    """What one fetch brought back. error is set when the tool failed."""

    status: int | None
    html: str
    clicked: bool | None
    error: str | None


def run_tool(tool, config, adapters_dir, debug_dir=None):
    """Test one tool against every target and return its result record."""
    adapter = adapter_path(adapters_dir, tool.name)
    record = {"tool": tool.name, "version": None, "setup": "ok", "setup_error": None, "modes": {}}

    setup = run_command(["uv", "run", "--quiet", "--refresh", str(adapter), "setup"], SETUP_TIMEOUT_SECONDS)
    if setup.exit_code != 0:
        record["setup"] = "broken"
        record["setup_error"] = command_error(setup, SETUP_TIMEOUT_SECONDS)
        print(f"{tool.name:20} BROKEN   {record['setup_error']}", flush=True)
        return record
    record["version"] = setup.stdout.strip().splitlines()[-1]

    for mode in tool.modes:
        record["modes"][mode] = {
            target.id: [try_target(adapter, tool, mode, target, config, debug_dir) for _ in range(config.tries)]
            for target in config.targets
        }
    return record


def try_target(adapter, tool, mode, target, config, debug_dir):
    """Fetch one target once and return the saved form of that try."""
    started = time.monotonic()
    page = fetch_page(adapter, target.url, mode, config.timeout, config.click)
    elapsed_ms = round((time.monotonic() - started) * 1000)

    if debug_dir is not None:
        save_debug_page(debug_dir, tool, mode, target, page)
    if page.error is not None:
        verdict, reason = "error", page.error
    else:
        verdict, reason = judge_page(page.status, page.html, target.expect, target.reject)

    click_note = " (clicked)" if page.clicked else ""
    print(f"{tool.name:20} {mode:9} {target.id:28} {verdict:9} {reason}{click_note}", flush=True)
    return {"verdict": verdict, "reason": reason, "clicked": page.clicked, "status": page.status, "ms": elapsed_ms}


def fetch_page(adapter, url, mode, timeout, click):
    """Run the adapter once, in a throwaway folder that also holds the browser profile."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        result_file = Path(folder) / "result.json"
        env = os.environ | {"STEALTH_BOARD_CLICK": "1" if click else "0", "TMPDIR": folder}
        command = ["uv", "run", "--quiet", str(adapter), "fetch", url, mode, str(result_file)]
        finished = run_command(command, timeout, cwd=folder, env=env)
        if not result_file.exists():
            return Page(status=None, html="", clicked=False, error=command_error(finished, timeout))
        result = json.loads(result_file.read_text())
    shutil.rmtree(folder, ignore_errors=True)  # a dying browser may have written one more file

    error = result["error"]
    return Page(
        status=result["status"],
        html=result["html"],
        clicked=result["clicked"],
        error=shorten_error(error) if error is not None else None,
    )


def command_error(finished, timeout):
    if finished.timed_out:
        return f"timeout after {timeout}s"
    if finished.stderr.strip():
        return shorten_error(finished.stderr)
    return f"adapter exit code {finished.exit_code}"


def shorten_error(text):
    """Keep the last real line, without home paths. Results are public."""
    text = re.sub(r"/(home|Users)/[^/\s]+", "~", text.replace(str(Path.home()), "~"))
    # Some tools print a box of advice after the real error.
    lines = [line for line in text.strip().splitlines() if not line.startswith(("╔", "║", "╚"))]
    if not lines:
        return ""
    return re.sub(r"\s+", " ", lines[-1])[:ERROR_MAX_LENGTH]


def adapter_path(adapters_dir, tool_name):
    return (Path(adapters_dir) / f"{tool_name}_adapter.py").resolve()


def save_debug_page(debug_dir, tool, mode, target, page):
    debug_dir = Path(debug_dir)
    debug_dir.mkdir(parents=True, exist_ok=True)
    (debug_dir / f"{tool.name}-{mode}-{target.id}.html").write_text(page.html)


def pick_job_count(tool_count):
    """One job per MEMORY_GB_PER_JOB of free memory, so a small machine runs one tool at a time."""
    free_gb = free_memory_gb()
    if free_gb is None:
        return 1
    return max(1, min(tool_count, MAX_AUTO_JOBS, int(free_gb // MEMORY_GB_PER_JOB)))


def free_memory_gb():
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return None
    available_kb = int(re.search(r"MemAvailable:\s+(\d+)", meminfo.read_text()).group(1))
    return available_kb / 1024**2


def select(config, tool_names, target_ids, modes):
    """Narrow the config to what the command line asked for. None keeps everything."""
    tools = [tool for tool in config.tools if tool_names is None or tool.name in tool_names]
    if modes is not None:
        tools = [dataclasses.replace(tool, modes=tuple(m for m in tool.modes if m in modes)) for tool in tools]
    targets = [target for target in config.targets if target_ids is None or target.id in target_ids]
    return dataclasses.replace(config, tools=tuple(tools), targets=tuple(targets))


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="board.toml")
    parser.add_argument("--adapters", default="adapters")
    parser.add_argument("--out", default="results")
    parser.add_argument("--runner", default="local", help="a short public name for where this runs")
    parser.add_argument("--ip-type", default="residential", choices=["residential", "datacenter"])
    parser.add_argument("--tool", action="append", help="only this tool (repeatable)")
    parser.add_argument("--target", action="append", help="only this target id (repeatable)")
    parser.add_argument("--mode", action="append", help="only this mode (repeatable)")
    parser.add_argument("--tries", type=int, help="override tries from the config")
    parser.add_argument("--jobs", type=int, help="tools to run at the same time (default: from free memory)")
    parser.add_argument("--no-click", action="store_true", help="never click a challenge check box")
    parser.add_argument("--debug-dir", help="save the last fetched HTML of each case here")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        config = load_config(args.config, args.adapters)
    except ConfigError as error:
        raise SystemExit(str(error))

    config = select(config, args.tool, args.target, args.mode)
    if args.tries is not None:
        config = dataclasses.replace(config, tries=args.tries)
    if args.no_click:
        config = dataclasses.replace(config, click=False)

    date = datetime.datetime.now(datetime.UTC).date().isoformat()
    out_dir = Path(args.out) / date
    out_dir.mkdir(parents=True, exist_ok=True)

    def run_and_save(tool):
        record = run_tool(tool, config, args.adapters, args.debug_dir)
        record |= {"date": date, "runner": args.runner, "ip_type": args.ip_type, "click": config.click}
        (out_dir / f"{args.runner}__{tool.name}.json").write_text(json.dumps(record, indent=1) + "\n")

    jobs = args.jobs if args.jobs is not None else pick_job_count(len(config.tools))
    print(f"running {len(config.tools)} tools, {jobs} at a time", flush=True)
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(run_and_save, config.tools))


if __name__ == "__main__":
    main()

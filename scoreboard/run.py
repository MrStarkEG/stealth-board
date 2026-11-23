"""Run tools against targets and save the results as JSON.

    python -m scoreboard.run --runner local --ip-type residential
    python -m scoreboard.run --tool patchright --target cloudflare-demo --tries 1
"""

import argparse
import datetime
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
import tomllib
from pathlib import Path

from scoreboard.check import problems
from scoreboard.verdict import judge

SETUP_TIMEOUT = 900  # browser downloads can be slow


def processes():
    """{pid: (parent pid, session id)} for every live process. Linux only, empty elsewhere."""
    table = {}
    for stat in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = stat.read_text().rsplit(")", 1)[1].split()
        except OSError:
            continue  # the process ended while we looked
        if fields[0] != "Z":  # Z: already dead, only waiting to be collected
            table[int(stat.parent.name)] = (int(fields[1]), int(fields[3]))
    return table


def started_by(root):
    """Every live process that root started, directly or not, or that shares its session.

    One rule is not enough. Playwright starts browsers in a session of their own,
    so the session misses them and only the parent chain finds them. A child whose
    parent already exited has lost that chain, and only the session finds it."""
    table = processes()
    found = {pid for pid, (_, session) in table.items() if session == root or pid == root}
    grew = True
    while grew:
        more = {pid for pid, (parent, _) in table.items() if parent in found or parent == root} - found
        found |= more
        grew = bool(more)
    return found


def kill_all(root):
    """Kill everything root started and wait until it is gone. Waiting matters:
    a dying browser must not write into its profile folder while that folder
    is being deleted."""
    pids = started_by(root)
    for _ in range(50):
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        alive = processes()
        pids = {pid for pid in pids if pid in alive} | started_by(root)
        if not pids:
            break
        time.sleep(0.1)
    try:
        os.killpg(root, signal.SIGKILL)  # for systems without /proc
    except ProcessLookupError:
        pass


def call(cmd, timeout, cwd=None, env=None):
    """Run cmd in its own session. Return (returncode, stdout, stderr).
    returncode is None on timeout. Everything the command started is always
    killed at the end, so no browser is left running."""
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True, cwd=cwd, env=env) as p:
        try:
            out, err = p.communicate(timeout=timeout)
            return p.returncode, out, err
        except subprocess.TimeoutExpired:
            return None, "", f"timeout after {timeout}s"
        finally:
            kill_all(p.pid)


def scrub(text):
    """Short, one line, and no home path. Results are public."""
    text = re.sub(r"/(home|Users)/[^/\s]+", "~", text.replace(str(Path.home()), "~")).strip()
    # Some tools print a box of advice after the real error. Skip the box.
    lines = [line for line in text.splitlines() if not line.startswith(("╔", "║", "╚"))]
    last = lines[-1] if lines else ""
    return re.sub(r"\s+", " ", last)[:300]


def fetch_once(adapter, url, mode, timeout, debug_file, click=True):
    """One try. Return (status, html, clicked, error)."""
    # A killed browser can still be writing while the folder is removed. That must not stop the run.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        # TMPDIR points into the temporary folder, so browser profiles land there and
        # are deleted with it, also when the browser was killed.
        env = os.environ | {"SCOREBOARD_CLICK": "1" if click else "0", "TMPDIR": tmp}
        outfile = Path(tmp) / "out.json"
        # Run inside the temporary folder, so files a tool drops land there and not in the repo.
        code, _, err = call(["uv", "run", "--quiet", str(adapter), "fetch", url, mode, str(outfile)], timeout, cwd=tmp, env=env)
        if not outfile.exists():
            return None, "", False, scrub(err) if err.strip() else f"adapter exit code {code}"
        result = json.loads(outfile.read_text())
    shutil.rmtree(tmp, ignore_errors=True)  # a second sweep, in case a dying browser wrote one more file
    if debug_file:
        debug_file.parent.mkdir(parents=True, exist_ok=True)
        debug_file.write_text(result["html"])
    error = result["error"]
    return result["status"], result["html"], result["clicked"], scrub(error) if error else None


def run_tool(tool, targets, config, adapters_dir, debug_dir=None):
    """Return the result record for one tool."""
    # The "_adapter" suffix stops the script from hiding the package it imports.
    adapter = (Path(adapters_dir) / f"{tool['name']}_adapter.py").resolve()
    record = {"tool": tool["name"], "version": None, "setup": "ok", "setup_error": None, "modes": {}}
    code, out, err = call(["uv", "run", "--quiet", "--refresh", str(adapter), "setup"], SETUP_TIMEOUT)
    if code != 0:
        record["setup"] = "broken"
        record["setup_error"] = scrub(err)
        return record
    record["version"] = out.strip().splitlines()[-1]
    for mode in tool["modes"]:
        by_target = record["modes"][mode] = {}
        for target in targets:
            tries = by_target[target["id"]] = []
            for n in range(config["tries"]):
                debug_file = Path(debug_dir) / f"{tool['name']}-{mode}-{target['id']}.html" if debug_dir else None
                start = time.monotonic()
                status, html, clicked, error = fetch_once(adapter, target["url"], mode, config["timeout"], debug_file, config["click"])
                ms = round((time.monotonic() - start) * 1000)
                if error:
                    verdict, reason = "error", error
                else:
                    verdict, reason = judge(status, html, target["expect"], target.get("reject"))
                tries.append({"verdict": verdict, "reason": reason, "clicked": clicked, "status": status, "ms": ms})
                note = " (after click)" if clicked and verdict == "pass" else " (clicked)" if clicked else ""
                print(f"{tool['name']:20} {mode:9} {target['id']:28} {verdict:9} {reason}{note}", flush=True)
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="scoreboard.toml")
    ap.add_argument("--adapters", default="adapters")
    ap.add_argument("--out", default="results")
    ap.add_argument("--runner", default="local", help="a short public name for where this runs")
    ap.add_argument("--ip-type", default="residential", choices=["residential", "datacenter"])
    ap.add_argument("--tool", action="append", help="only this tool (repeatable)")
    ap.add_argument("--target", action="append", help="only this target id (repeatable)")
    ap.add_argument("--mode", action="append", help="only this mode (repeatable)")
    ap.add_argument("--tries", type=int, help="override tries from the config")
    ap.add_argument("--no-click", action="store_true", help="never click a challenge check box")
    ap.add_argument("--debug-dir", help="save the last fetched HTML of each case here")
    args = ap.parse_args()

    config = tomllib.loads(Path(args.config).read_text())
    found = problems(config, args.adapters)
    if found:
        raise SystemExit("The config has problems:\n  " + "\n  ".join(found))
    if args.tries:
        config["tries"] = args.tries
    if args.no_click:
        config["click"] = False
    tools = [t for t in config["tool"] if not args.tool or t["name"] in args.tool]
    if args.mode:
        tools = [t | {"modes": [m for m in t["modes"] if m in args.mode]} for t in tools]
    targets = [t for t in config["target"] if not args.target or t["id"] in args.target]
    date = datetime.datetime.now(datetime.UTC).date().isoformat()
    outdir = Path(args.out) / date
    outdir.mkdir(parents=True, exist_ok=True)
    for tool in tools:
        record = run_tool(tool, targets, config, args.adapters, args.debug_dir)
        record |= {"date": date, "runner": args.runner, "ip_type": args.ip_type, "click": config["click"]}
        (outdir / f"{args.runner}__{tool['name']}.json").write_text(json.dumps(record, indent=1) + "\n")
        if record["setup"] == "broken":
            print(f"{tool['name']:20} BROKEN   {record['setup_error']}", flush=True)


if __name__ == "__main__":
    main()

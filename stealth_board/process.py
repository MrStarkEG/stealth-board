"""Run a command and make sure nothing it started stays alive."""

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

KILL_WAIT_STEPS = 50
KILL_WAIT_STEP_SECONDS = 0.1


@dataclass(frozen=True)
class CommandResult:
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool


def run_command(command, timeout, cwd=None, env=None):
    """Run a command in its own session and kill everything it started afterwards."""
    with subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True, cwd=cwd, env=env
    ) as process:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            return CommandResult(process.returncode, stdout, stderr, timed_out=False)
        except subprocess.TimeoutExpired:
            return CommandResult(None, "", "", timed_out=True)
        finally:
            kill_process_tree(process.pid)


def kill_process_tree(root_pid):
    """Kill everything root_pid started, and wait until it is gone.

    The wait matters: a dying browser must not write into its profile folder
    while that folder is being deleted.
    """
    remaining = find_process_tree(root_pid)
    for _ in range(KILL_WAIT_STEPS):
        for pid in remaining:
            _kill(pid)
        alive = list_processes()
        remaining = {pid for pid in remaining if pid in alive} | find_process_tree(root_pid)
        if not remaining:
            break
        time.sleep(KILL_WAIT_STEP_SECONDS)
    _kill_group(root_pid)


def find_process_tree(root_pid):
    """Every live process that root_pid started, or that shares its session.

    Both rules are needed. Playwright starts browsers in a session of their own,
    so only the parent chain finds them. A child whose parent already exited has
    lost that chain, so only the session finds it.
    """
    processes = list_processes()
    tree = {pid for pid, (_, session) in processes.items() if pid == root_pid or session == root_pid}
    while True:
        children = {pid for pid, (parent, _) in processes.items() if parent == root_pid or parent in tree} - tree
        if not children:
            return tree
        tree |= children


def list_processes():
    """Map each live pid to (parent pid, session id). Empty on systems without /proc."""
    processes = {}
    for stat_file in Path("/proc").glob("[0-9]*/stat"):
        try:
            state, parent, _, session = stat_file.read_text().rsplit(")", 1)[1].split()[:4]
        except OSError:
            continue  # the process ended while we looked
        if state != "Z":  # a zombie is already dead
            processes[int(stat_file.parent.name)] = (int(parent), int(session))
    return processes


def _kill(pid):
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _kill_group(group_id):
    """The fallback for systems without /proc, where the tree is unknown."""
    try:
        os.killpg(group_id, signal.SIGKILL)
    except ProcessLookupError:
        pass

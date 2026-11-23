"""A private virtual screen for headed browsers."""

import contextlib
import os
import shutil
import subprocess

SCREEN = "1920x1080x24"


@contextlib.contextmanager
def headed_environment():
    """Yield the environment for headed fetches.

    With Xvfb installed, every caller gets a screen of its own, so tools that
    run side by side cannot click into each other's windows. Without Xvfb the
    browsers open on the real screen.
    """
    if shutil.which("Xvfb") is None:
        yield dict(os.environ)
        return

    # "-displayfd 1" lets Xvfb pick a free display number and print it.
    xvfb = subprocess.Popen(
        ["Xvfb", "-displayfd", "1", "-screen", "0", SCREEN, "-nolisten", "tcp"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
    )
    try:
        display_number = xvfb.stdout.readline().strip()
        environment = dict(os.environ, DISPLAY=f":{display_number}")
        # On a Wayland desktop, Chrome would still pick the real screen.
        environment.pop("WAYLAND_DISPLAY", None)
        yield environment
    finally:
        xvfb.terminate()
        xvfb.wait()
        xvfb.stdout.close()

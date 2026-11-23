"""A private virtual screen for headed browsers."""

import contextlib
import os
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path

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
    if shutil.which("xauth") is None:
        raise RuntimeError("Xvfb is installed but xauth is not. Install xauth, the virtual screen needs it.")

    # The screen only accepts clients that know the cookie in this private folder.
    with tempfile.TemporaryDirectory() as folder:
        auth_file = Path(folder) / "Xauthority"
        cookie = secrets.token_hex(16)
        # Xvfb picks its own display number below, and accepts the cookie under any name.
        add_cookie(auth_file, ":0", cookie)
        xvfb = subprocess.Popen(
            ["Xvfb", "-displayfd", "1", "-auth", str(auth_file), "-screen", "0", SCREEN, "-nolisten", "tcp"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        try:
            display = f":{xvfb.stdout.readline().strip()}"
            add_cookie(auth_file, display, cookie)
            environment = dict(os.environ, DISPLAY=display, XAUTHORITY=str(auth_file))
            # On a Wayland desktop, Chrome would still pick the real screen.
            environment.pop("WAYLAND_DISPLAY", None)
            yield environment
        finally:
            xvfb.terminate()
            xvfb.wait()
            xvfb.stdout.close()


def add_cookie(auth_file, display, cookie):
    subprocess.run(
        ["xauth", "-f", str(auth_file), "add", display, "MIT-MAGIC-COOKIE-1", cookie],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

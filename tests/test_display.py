"""The virtual screen for headed browsers."""

import os
import shutil
import subprocess
import unittest
from unittest import mock

from stealth_board.display import headed_environment


class DisplayTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which("Xvfb"), "needs Xvfb")
    def test_every_caller_gets_its_own_screen(self):
        with headed_environment() as first, headed_environment() as second:
            self.assertRegex(first["DISPLAY"], r"^:\d+$")
            self.assertNotEqual(first["DISPLAY"], second["DISPLAY"])
            self.assertNotIn("WAYLAND_DISPLAY", first)

    @unittest.skipUnless(shutil.which("Xvfb") and shutil.which("xdpyinfo"), "needs Xvfb and xdpyinfo")
    def test_the_screen_refuses_clients_without_the_cookie(self):
        with headed_environment() as environment:
            with_cookie = subprocess.run(["xdpyinfo"], env=environment, capture_output=True)
            without_cookie = subprocess.run(["xdpyinfo"], env=environment | {"XAUTHORITY": "/dev/null"}, capture_output=True)
        self.assertEqual(with_cookie.returncode, 0)
        self.assertNotEqual(without_cookie.returncode, 0)

    def test_without_xvfb_the_real_screen_is_used(self):
        with mock.patch("shutil.which", return_value=None):
            with headed_environment() as environment:
                self.assertEqual(environment, dict(os.environ))


if __name__ == "__main__":
    unittest.main()

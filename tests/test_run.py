"""End to end test of the runner against a local web server. Needs uv.

    python -m unittest discover tests
"""

import http.server
import subprocess
import threading
import time
import unittest
from pathlib import Path

from scoreboard.run import run_tool

FAKES = Path(__file__).parent / "fake_adapters"


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/hang":
            time.sleep(30)
            return
        status, body = {
            "/ok": (200, "<h1>Real products page</h1>"),
            "/block200": (200, "<title>Just a moment...</title>"),
            "/403": (403, "Forbidden"),
        }[self.path]
        self.send_response(status)
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *args):
        pass


class RunnerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.targets = [{"id": p.strip("/"), "url": base + p, "expect": "Real products"} for p in ("/ok", "/block200", "/403", "/hang")]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def run_fake(self, name, targets=None, timeout=20):
        tool = {"name": name, "modes": ["http"]}
        return run_tool(tool, targets or self.targets, {"tries": 1, "timeout": timeout}, FAKES)

    def test_verdicts(self):
        record = self.run_fake("plain", timeout=4)
        self.assertEqual(record["setup"], "ok")
        self.assertEqual(record["version"], "1.2.3")
        got = {tid: (tries[0]["verdict"], tries[0]["reason"]) for tid, tries in record["modes"]["http"].items()}
        self.assertEqual(got["ok"], ("pass", ""))
        self.assertEqual(got["block200"], ("blocked", "cloudflare challenge"))
        self.assertEqual(got["403"], ("blocked", "http 403"))
        self.assertEqual(got["hang"], ("error", "timeout after 4s"))

    def test_broken_setup_is_recorded(self):
        record = self.run_fake("broken_setup")
        self.assertEqual(record["setup"], "broken")
        self.assertIn("browser download failed", record["setup_error"])
        self.assertEqual(record["modes"], {})

    def test_crash_is_an_error_without_home_path(self):
        record = self.run_fake("crash", self.targets[:1])
        tries = record["modes"]["http"]["ok"]
        self.assertEqual(tries[0]["verdict"], "error")
        self.assertIn("browser crashed", tries[0]["reason"])
        self.assertNotIn("/home/", tries[0]["reason"])

    def test_timeout_kills_child_processes(self):
        record = self.run_fake("leaky", self.targets[:1], timeout=3)
        self.assertEqual(record["modes"]["http"]["ok"][0]["verdict"], "error")
        left = subprocess.run(["pgrep", "-f", "^sleep 987654"], capture_output=True, text=True).stdout
        self.assertEqual(left, "")


if __name__ == "__main__":
    unittest.main()

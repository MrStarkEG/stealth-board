"""The runner end to end, with fake adapters against a local web server. Needs uv.

    python -m unittest discover tests
"""

import http.server
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

from stealth_board import run
from stealth_board.config import Config, Target, Tool

FAKE_ADAPTERS = Path(__file__).parent / "fake_adapters"
REAL_PAGE = "<h1>Real products page</h1>"
CHALLENGE_PAGE = "<title>Just a moment...</title><div class=cf-turnstile></div>"

PAGES = {
    "/ok": (200, REAL_PAGE),
    "/block200": (200, "<title>Just a moment...</title>"),
    "/403": (403, "Forbidden"),
    "/challenge": (403, CHALLENGE_PAGE),
    "/challenge?clicked=1": (200, REAL_PAGE),
}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/hang":
            time.sleep(30)
            return
        status, body = PAGES[self.path]
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
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def run_fake(self, adapter, paths, timeout=20, click=True, expect="Real products", debug_dir=None):
        """Run one fake adapter against local pages. Return {path: first try}."""
        targets = tuple(
            Target(id=path.strip("/"), name=path, kind="site", vendor="test", url=self.base_url + path, expect=expect)
            for path in paths
        )
        tool = Tool(name=adapter, modes=("http",))
        config = Config(tries=1, timeout=timeout, click=click, tools=(tool,), targets=targets)
        record = run.run_tool(tool, config, FAKE_ADAPTERS, debug_dir)
        self.record = record
        if record["setup"] == "broken":
            return {}
        return {target_id: tries[0] for target_id, tries in record["modes"]["http"].items()}

    def test_verdicts(self):
        tries = self.run_fake("plain", ["/ok", "/block200", "/403", "/hang"], timeout=4)
        self.assertEqual(self.record["setup"], "ok")
        self.assertEqual(self.record["version"], "1.2.3")
        verdicts = {path: (one_try["verdict"], one_try["reason"]) for path, one_try in tries.items()}
        self.assertEqual(verdicts["ok"], ("pass", ""))
        self.assertEqual(verdicts["block200"], ("challenge", "cloudflare challenge"))
        self.assertEqual(verdicts["403"], ("blocked", "http 403"))
        self.assertEqual(verdicts["hang"], ("error", "timeout after 4s"))

    def test_click_moves_a_challenge_forward(self):
        clicked = self.run_fake("clicker", ["/challenge"])["challenge"]
        self.assertEqual((clicked["verdict"], clicked["clicked"]), ("pass", True))

        not_clicked = self.run_fake("clicker", ["/challenge"], click=False)["challenge"]
        self.assertEqual(not_clicked["verdict"], "challenge")
        self.assertEqual(not_clicked["reason"], "cloudflare challenge")
        self.assertFalse(not_clicked["clicked"])

    def test_broken_setup_is_recorded(self):
        self.run_fake("broken_setup", ["/ok"])
        self.assertEqual(self.record["setup"], "broken")
        self.assertIn("browser download failed", self.record["setup_error"])
        self.assertEqual(self.record["modes"], {})

    def test_crash_is_an_error_without_home_path(self):
        crashed = self.run_fake("crash", ["/ok"])["ok"]
        self.assertEqual(crashed["verdict"], "error")
        self.assertIn("browser crashed", crashed["reason"])
        self.assertNotIn("/home/", crashed["reason"])

    def test_temporary_files_of_a_tool_are_removed(self):
        debug_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, debug_dir)
        # The litter adapter returns the path of the folder it left behind as its page.
        littered = self.run_fake("litter", ["/ok"], expect="profile-", debug_dir=debug_dir)["ok"]
        self.assertEqual(littered["verdict"], "pass")
        left_behind = Path((debug_dir / "litter-http-ok.html").read_text())
        self.assertFalse(left_behind.exists())

    def test_timeout_kills_child_processes(self):
        hung = self.run_fake("leaky", ["/ok"], timeout=3)["ok"]
        self.assertEqual(hung["verdict"], "error")
        still_running = subprocess.run(["pgrep", "-f", "^sleep 987654"], capture_output=True, text=True).stdout
        self.assertEqual(still_running, "")


class SelectTest(unittest.TestCase):
    def setUp(self):
        shop = Target(id="shop", name="Shop", kind="site", vendor="x", url="https://shop.example/", expect="x")
        blog = Target(id="blog", name="Blog", kind="site", vendor="x", url="https://blog.example/", expect="x")
        browser = Tool(name="browser", modes=("headless", "headed"))
        client = Tool(name="client", modes=("http",))
        self.config = Config(tries=3, timeout=90, click=True, tools=(browser, client), targets=(shop, blog))

    def test_none_keeps_everything(self):
        self.assertEqual(run.select(self.config, None, None, None), self.config)

    def test_narrowing(self):
        chosen = run.select(self.config, ["browser"], ["blog"], ["headed"])
        self.assertEqual([tool.name for tool in chosen.tools], ["browser"])
        self.assertEqual(chosen.tools[0].modes, ("headed",))
        self.assertEqual([target.id for target in chosen.targets], ["blog"])


if __name__ == "__main__":
    unittest.main()

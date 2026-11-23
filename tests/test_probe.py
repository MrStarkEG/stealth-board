"""Check the website probe: vendor signs, and a full report from a local server."""

import http.server
import threading
import unittest

from stealth_board.probe import detect, get, report


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/protected":
            self.send_response(403)
            self.send_header("X-DataDome", "protected")
            self.end_headers()
            self.wfile.write(b'<title>shop</title><script src="https://ct.captcha-delivery.com/c.js"></script>')
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<title>Open Shop</title><h1>Welcome</h1>")

    def log_message(self, *args):
        pass


class ProbeTest(unittest.TestCase):
    def test_detect(self):
        cases = [
            ("Server: cloudflare\nCF-RAY: 1", "", [("Cloudflare", "headers")]),
            ("", "<title>Just a moment...</title>", [("Cloudflare", "page")]),
            ("X-DataDome: protected", "captcha-delivery.com", [("DataDome", "headers and page")]),
            ("Set-Cookie: _pxhd=abc", "", [("HUMAN (PerimeterX)", "headers")]),
            ("Set-Cookie: _abck=abc; Path=/", "", [("Akamai", "headers")]),
            ("x-kpsdk-ct: abc", "", [("Kasada", "headers")]),
            ("Set-Cookie: visid_incap_1=abc", "", [("Imperva", "headers")]),
            ("x-amzn-waf-action: challenge", "", [("AWS WAF", "headers")]),
            ("Server: nginx", "<h1>Hello</h1>", []),
        ]
        for headers, body, expected in cases:
            with self.subTest(headers=headers, body=body):
                self.assertEqual(detect(headers, body), expected)

    def test_report_from_a_local_server(self):
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_port}"

        protected = "\n".join(report(base + "/protected", *get(base + "/protected")))
        self.assertIn("status   403", protected)
        self.assertIn("DataDome (seen in headers and page)", protected)
        self.assertIn("it can be a target", protected)

        opened = "\n".join(report(base + "/", *get(base + "/")))
        self.assertIn("title    Open Shop", opened)
        self.assertIn("none seen", opened)
        self.assertIn("weak target", opened)


if __name__ == "__main__":
    unittest.main()

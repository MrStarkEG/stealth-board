"""Loading board.toml into Config."""

import tempfile
import unittest
from pathlib import Path

from stealth_board.config import ConfigError, load_config

ROOT = Path(__file__).parent.parent


class ConfigTest(unittest.TestCase):
    def test_the_real_config_loads(self):
        config = load_config(ROOT / "board.toml", ROOT / "adapters")
        requests = next(tool for tool in config.tools if tool.name == "requests")
        self.assertTrue(requests.control)
        self.assertEqual(requests.modes, ("http",))
        example = next(target for target in config.targets if target.id == "example")
        self.assertFalse(example.is_scored)
        self.assertIsNone(example.reject)

    def test_a_bad_config_names_its_problems(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml") as file:
            file.write("tries = 0\ntimeout = 90\nclick = true\n")
            file.flush()
            with self.assertRaises(ConfigError) as raised:
                load_config(file.name, ROOT / "adapters")
        message = str(raised.exception)
        self.assertIn("'tries' must be 1 or more", message)
        self.assertIn("There is no [[tool]]", message)


if __name__ == "__main__":
    unittest.main()

"""Check the config checker, and check the real config with it."""

import copy
import tomllib
import unittest
from pathlib import Path

from stealth_board.check import problems

ROOT = Path(__file__).parent.parent
GOOD = {
    "tries": 3, "timeout": 90, "click": True,
    "tool": [{"name": "requests", "modes": ["http"]}],
    "target": [{"id": "shop", "name": "Shop", "kind": "site", "vendor": "Cloudflare", "url": "https://shop.example/", "expect": "Garden"}],
}


def broken(change):
    config = copy.deepcopy(GOOD)
    change(config)
    return " ".join(problems(config, ROOT / "adapters"))


class CheckTest(unittest.TestCase):
    def test_the_real_config_is_fine(self):
        config = tomllib.loads((ROOT / "board.toml").read_text())
        self.assertEqual(problems(config, ROOT / "adapters"), [])

    def test_every_adapter_file_is_in_the_config(self):
        config = tomllib.loads((ROOT / "board.toml").read_text())
        files = {p.name.removesuffix("_adapter.py") for p in (ROOT / "adapters").glob("*_adapter.py")}
        self.assertEqual(files, {t["name"] for t in config["tool"]})

    def test_good_config(self):
        self.assertEqual(problems(GOOD, ROOT / "adapters"), [])

    def test_problems_are_found(self):
        cases = [
            (lambda c: c.update(tries=0), "'tries' must be 1 or more"),
            (lambda c: c.pop("click"), "'click' at the top must be a bool"),
            (lambda c: c["tool"][0].update(name="nosuchtool"), "nosuchtool_adapter.py does not exist"),
            (lambda c: c["tool"][0].update(modes=["window"]), "modes must be a list"),
            (lambda c: c["tool"].append(c["tool"][0]), "listed more than once"),
            (lambda c: c["target"][0].update(id="My Shop"), "may only use small letters"),
            (lambda c: c["target"][0].pop("vendor"), "missing vendor"),
            (lambda c: c["target"][0].update(kind="shop"), "kind must be one of"),
            (lambda c: c["target"][0].update(url="http://shop.example/"), "must start with https://"),
            (lambda c: c["target"][0].update(expect="(unclosed"), "not a valid regular expression"),
            (lambda c: c["target"].append(c["target"][0]), "listed more than once"),
            (lambda c: c.update(target=[]), "There is no [[target]]"),
        ]
        for change, message in cases:
            with self.subTest(message=message):
                self.assertIn(message, broken(change))


if __name__ == "__main__":
    unittest.main()

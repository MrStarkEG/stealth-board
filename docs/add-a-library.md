# Add a library

You add one file and three lines of config.

## 1. Write the adapter

Create `adapters/NAME_adapter.py`. The `_adapter` ending matters: a file called `NAME.py` would hide the package it imports.

```python
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["somelib"]
# ///
"""somelib: one line on what it is.
Settings from its README: say which ones you used and why."""

from somelib import Browser

from _common import NAV_TIMEOUT_MS, SETTLE_MS, run


def fetch(url, headless):
    browser = Browser(headless=headless)
    try:
        page = browser.open(url, timeout=NAV_TIMEOUT_MS)
        page.wait(SETTLE_MS)          # give a challenge page time to finish
        return page.status, page.html  # use None when the tool has no status
    finally:
        browser.close()


run("somelib", fetch, setup=[["somelib", "install"]])
```

Rules:

- `fetch(url, headless)` returns `(status, html)`. Raise an exception on failure, the runner saves it.
- For the click on a challenge box, return `(status, html, clicked)`. With a Playwright-style page, call `clicked = settle(page)` from `_common` in place of the wait. If the library has its own solver, use it only when `CLICK` from `_common` is true, and return `None` for clicked when the solver does not say what it did.
- `run(package, fetch, setup)`: `package` is the PyPI name, used to read the version. `setup` is a list of commands to run once, like downloading a browser. Leave it out when there is nothing to install.
- Use the settings the library's own README recommends, and write them in the docstring. The goal is a fair test of the library at its best.
- Do not pin a version. The scoreboard tests the newest release.
- Use a new empty profile for every fetch. Never point a tool at your own browser profile.
- Always close the browser, also on errors.

## 2. Add it to the config

In `board.toml`:

```toml
[[tool]]
name = "somelib"
modes = ["headless", "headed"]   # or ["http"] for an HTTP client
```

## 3. Try it

```sh
python3 -m stealth_board.run --tool somelib --target example --tries 1
python3 -m stealth_board.run --tool somelib --tries 1
```

The first command must pass. Run `python3 -m unittest discover tests` too: one test checks that every adapter file is listed in the config. `example` has no protection, so a failure there is a bug in the adapter.

Then open a pull request. The daily workflow reads the tool list from the config, so it needs no change.

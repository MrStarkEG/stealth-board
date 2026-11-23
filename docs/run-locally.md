# Run it locally

## What you need

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Google Chrome (patchright, nodriver, zendriver and seleniumbase drive the installed Chrome)
- On Linux, for headed mode with no visible windows: `sudo apt install xvfb`

The runner itself uses only the Python standard library. There is nothing to `pip install`.

## Commands

Run the tests. They use a local web server and fake adapters, so they need no browser:

```sh
python3 -m unittest discover tests
```

Run one small case:

```sh
python3 -m scoreboard.run --tool camoufox --target etsy --mode headless --tries 1
```

Run everything the way the daily run does. Results from a home connection are saved as "residential":

```sh
xvfb-run -a python3 -m scoreboard.run --runner home --ip-type residential
```

This takes a long time (9 tools, 12 targets, 3 tries, 2 modes). Use `--tool`, `--target`, `--mode` and `--tries` to make it smaller. Each one can be repeated.

Look at the page a tool got back:

```sh
python3 -m scoreboard.run --tool playwright --target zillow --tries 1 --debug-dir debug
# then open debug/playwright-headless-zillow.html
```

Build and view the dashboard:

```sh
python3 -m scoreboard.build
python3 -m http.server -d site 8000
```

## Common problems

**The first run is slow.** `setup` downloads a browser for the tool. Later runs reuse it.

**A tool shows BROKEN.** Its setup failed. Run the setup by hand to see the full error:

```sh
uv run adapters/NAME_adapter.py setup
```

**Headed mode opens windows on my screen.** Run it under `xvfb-run -a`, as shown above.

**Headed mode fails with "no display".** There is no screen to draw on. Use `xvfb-run -a`, or run headless only with `--mode headless --mode http`.

**Memory.** Every fetch starts a browser and closes it again, and tools run one after another, so only one browser is open at a time.

**My results differ from the dashboard.** That is expected. Your IP address, country and Chrome version are different.

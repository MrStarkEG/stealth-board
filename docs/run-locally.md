# Run it locally

## What you need

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Google Chrome (patchright, nodriver, zendriver and seleniumbase drive the installed Chrome)
- On Linux, for headed mode with no visible windows: `sudo apt install xvfb`

The runner itself uses only the Python standard library. There is nothing to `pip install`.

## Commands

Check the config and run the tests. They use a local web server and fake adapters, so they need no browser:

```sh
python3 -m stealth_board.check
python3 -m unittest discover tests
```

[testing.md](testing.md) explains what each test level covers.

Run one small case:

```sh
python3 -m stealth_board.run --tool camoufox --target etsy --mode headless --tries 1
```

Run everything the way the daily run does. Results from a home connection are saved as "residential":

```sh
xvfb-run -a python3 -m stealth_board.run --runner home --ip-type residential
```

On a Wayland desktop, Chrome may still open its windows on your real screen. Put `env -u WAYLAND_DISPLAY` in front of the command to stop that:

```sh
env -u WAYLAND_DISPLAY xvfb-run -a python3 -m stealth_board.run --runner home --ip-type residential
```

This takes one to three hours (9 tools, 12 targets, 3 tries, 2 modes). The runner tests several tools at the same time when there is enough free memory, one per 4 GB and at most 4. Set it yourself with `--jobs 2`, or use `--jobs 1` to run them one by one. Use `--tool`, `--target`, `--mode` and `--tries` to make it smaller. Each one can be repeated.

Where results go: one file per tool, day and runner name, `results/DATE/RUNNER__TOOL.json`. A new run with the same runner name on the same day replaces that file. Quick tries use the default name `local`, and git ignores those files. So do not use `--runner home` for a partial run, or it replaces the full results of that day.

Look at the page a tool got back:

```sh
python3 -m stealth_board.run --tool playwright --target zillow --tries 1 --debug-dir debug
# then open debug/playwright-headless-zillow.html
```

Build and view the dashboard:

```sh
python3 -m stealth_board.build
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

**Memory.** Every fetch starts a browser and closes it again. Each job has one browser open at a time, so `--jobs 1` means one browser in total.

**My results differ from the dashboard.** That is expected. Your IP address, country and Chrome version are different.

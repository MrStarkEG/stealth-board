# Testing

There are four levels. Each one is slower than the one before and closer to the real thing. Run them in this order.

| Level | Command | Needs | Time |
|---|---|---|---|
| 1. Config check | `python3 -m stealth_board.check` | nothing | under a second |
| 2. Tests | `python3 -m unittest discover tests` | uv | about 10 seconds |
| 3. Smoke run | `python3 -m stealth_board.run --target example --tries 1` | browsers, internet | a few minutes |
| 4. Full run | `xvfb-run -a python3 -m stealth_board.run` | browsers, internet | 1 to 3 hours |

Levels 1 and 2 also run on GitHub for every push and pull request (`.github/workflows/tests.yml`).

## 1. Config check

Reads `board.toml` and lists every problem in plain words: a missing field, a target id used twice, an `expect` pattern that is not a valid regular expression, a tool with no adapter file. The runner does the same check before it starts, so a typo cannot waste a long run.

## 2. Tests

They need no browser and no outside network. Everything runs against a small web server that the tests start on your own machine.

| File | What it proves |
|---|---|
| `tests/test_verdict.py` | Each sample page in `tests/pages/` gets the right result: pass, challenge or blocked, with the right reason. |
| `tests/test_check.py` | The real config is valid, every adapter file is listed in it, and the checker finds each kind of mistake. |
| `tests/test_config.py` | The real config loads, and a bad one is refused with its problems listed. |
| `tests/test_probe.py` | The website probe names the right vendor from headers and page text. |
| `tests/test_run.py` | The runner end to end, with fake adapters in `tests/fake_adapters/`: a real page, a block page with status 200, a 403, a page that hangs, a setup that fails, a crash, a click that opens a challenge, a browser that must not stay alive after a timeout, and temporary files that must not stay behind. Also the choice of how many tools run at the same time. |
| `tests/test_build.py` | The 7 and 30 day numbers on made-up history, the marks on weak targets, and broken tools. |

Run one file or one test:

```sh
python3 -m unittest tests.test_verdict
python3 -m unittest tests.test_run.RunnerTest.test_click_moves_a_challenge_forward
```

## 3. Smoke run

Starts every library once against a page with no protection. It proves that each library still installs, starts its browser and returns a page. If a library fails here, the problem is in its adapter or its newest release, not in any website.

```sh
python3 -m stealth_board.run --target example --tries 1 --mode http --mode headless
```

## 4. Full run

The same command the daily run uses. See [run-locally.md](run-locally.md). Use `--tool`, `--target`, `--mode` and `--tries` to run only a part of it.

## Test a new website before you add it

This is the path for every new target. It takes about ten minutes.

**Step 1. Look at the site.**

```sh
python3 -m stealth_board.probe https://www.example-shop.com/
```

```
status   403
title    example-shop.com
vendor   DataDome (seen in headers and page)
plain client: stopped (datadome captcha). This page tells tools apart, so it can be a target.
```

The probe loads the page once with a plain client and changes no file. If it says the site does not block plain tools, the site is a weak target and you can stop here.

**Step 2. Add a draft target** to `board.toml`. Guess the `expect` pattern for now. [add-a-target.md](add-a-target.md) explains each field.

**Step 3. Check the config.**

```sh
python3 -m stealth_board.check
```

**Step 4. See which tools get in, and save the pages.**

```sh
python3 -m stealth_board.run --target NEW_ID --tool playwright --tool patchright --tool camoufox --tries 1 --debug-dir debug
```

Open the files in `debug/`. Take the `expect` text from a page where a tool got in, and make sure the block page does not have it. Run the command again until the results match what you see in the saved pages.

**Step 5. Ask: is it a good target?** It is good when the control (`playwright`) is stopped and at least one stealth tool gets in. Keep the number of test loads small. Sites raise their guard when one address loads the same page many times, and that changes the result.

## When you meet a new kind of block page

The verdict rules know the block pages we have met so far. For a new one:

1. Add its marker to `CHALLENGE_MARKERS` or `BLOCK_MARKERS` in `stealth_board/verdict.py`. A challenge still asks for a check. A block is a plain no.
2. Save a small sample of the page in `tests/pages/`. Keep only the lines that matter, not the whole page.
3. Add one line for it to `CASES` in `tests/test_verdict.py`.

A test fails when a sample page has no case, so step 3 cannot be forgotten.

For a new protection vendor, also add one line to `VENDOR_SIGNS` in `stealth_board/probe.py` and one case to `tests/test_probe.py`.

## Checking the click on a challenge box

With `click = true` in the config, an adapter clicks a Cloudflare check box once and waits again. Each try saves `clicked`:

| clicked | Meaning |
|---|---|
| true | the adapter clicked the box |
| false | there was no box, or clicking was off |
| null | the tool used its own solver and does not say |

Read it together with the result:

| Result | clicked | What happened |
|---|---|---|
| pass | false | got in with no click |
| pass | true | the click moved it forward |
| challenge | true | the click landed, and the site showed the check again |
| challenge | false | a challenge with nothing to click, like a puzzle or a wait page |
| blocked | any | the site refused |

Compare a run with clicks and one without:

```sh
python3 -m stealth_board.run --target cloudflare-turnstile --tool patchright --tries 1
python3 -m stealth_board.run --target cloudflare-turnstile --tool patchright --tries 1 --no-click
```

Only the Cloudflare check box is clicked today. DataDome and HUMAN show puzzles that need more than a click, so those tries end as a challenge.

## The dashboard

The numbers are covered by `tests/test_build.py`. The page itself is checked by eye:

```sh
python3 -m stealth_board.build
python3 -m http.server -d site 8000
```

Look at it in light and dark mode and at phone width. The table scrolls sideways inside its box, and the page itself must not.

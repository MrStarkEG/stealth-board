# How it works

This page follows one test from start to end.

## 1. The config

[`board.toml`](../board.toml) lists the tools and the targets.

A tool has a name and its modes. A target has a URL and an `expect` pattern, which is text that only the real page has.

## 2. The adapter

Each tool has one script in `adapters/`, named `NAME_adapter.py`. All adapters do the same two jobs:

```sh
uv run adapters/NAME_adapter.py setup                       # install the browser, print the tool version
uv run adapters/NAME_adapter.py fetch URL MODE OUTFILE      # open URL once, write the page to OUTFILE
```

The top of each script lists its dependencies:

```python
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["patchright"]
# ///
```

`uv` reads this and runs the script in its own environment. This gives us two things:

- Tools never clash, even when two of them need different versions of the same package.
- No version is pinned, so every run uses the newest release. That is the point of the board.

## 3. The runner

`stealth_board/run.py` does this for each tool:

1. Run `setup`. If it fails, save the tool as **broken** and go on to the next tool.
2. For each mode, target and try, run `fetch` as a new process.
3. Kill everything the fetch started afterwards, so no browser stays behind. Temporary files, like the browser profile, go into a folder that is deleted after each fetch. A fetch that takes longer than `timeout` is killed and saved as an **error**.
4. Pass the page to the verdict rules.

Every fetch is a new process with a new empty browser profile. Nothing is shared between tries.

## 4. The verdict

`stealth_board/verdict.py` gives each try one of four results:

| Result | Meaning |
|---|---|
| pass | the `expect` pattern is in the page |
| challenge | the page still shows a check or a captcha |
| blocked | the site refused, or the page is something else |
| error | the tool crashed, or the fetch timed out |

For a failed try it also saves a reason, like "cloudflare challenge" or "http 403". Pass is decided by `expect` alone. The lists of known pages only choose between challenge and blocked.

### The click

Some challenge pages show a check box ("Verify you are human"). With `click = true` in the config, the adapter clicks that box once, waits, and reads the page again. Each try saves `clicked`, so the results can tell these apart:

- it passed with no click
- it passed after the click
- the click landed, and the site showed the check again

Adapters with a Playwright-style page share one helper for this (`wait_and_click` in `adapters/_common.py`). Tools with their own solver use that instead, and their adapter says so at the top.

## 5. The results

The runner writes one file per tool and day: `results/2026-11-21/vps__patchright.json`.

The file holds the tool version, the date, the runner name, the IP type (datacenter or residential), if clicking was on, and every try. It never holds an IP address, a host name or a page.

## 6. The dashboard

`stealth_board/build.py` reads all result files and writes `site/data.json` with the 7 and 30 day pass rates. `site/index.html` reads that file and draws the table.

The build also marks two kinds of weak targets:

- a control opens it, so it has no real protection
- no tool opened it for 7 days, so the target or its `expect` pattern may be out of date

## 7. Running tools side by side

Each tool is one job. Jobs run at the same time, as many as the free memory allows (one per 4 GB, at most 4), or as many as `--jobs` says. Inside a job, a tool opens one browser at a time, so two tries of the same tool never overlap. In headed mode each job has a virtual screen of its own.

## 8. The daily run

A cron job runs two commands once a day: the runner, then the build. A web server shows the `site/` folder. [deploy-on-a-server.md](deploy-on-a-server.md) has the details.

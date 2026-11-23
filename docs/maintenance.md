# Keeping it running

## What runs on its own

| Thing | How |
|---|---|
| New library releases | No version is pinned. Every run installs the newest release and saves its version. |
| A library that stops installing | Saved as "broken" and shown on the dashboard. The run goes on. |
| A library that hangs | Killed after `timeout` seconds, with its browser. Saved as an error. |
| New Chrome releases | The run installs the current stable Chrome. |
| The dashboard | Rebuilt and published after every run. |
| Weak targets | Marked on the dashboard (a control opens it, or nothing does). |

## What needs a person

**Targets go out of date.** This is the main job, a few minutes a month. Look at the "Targets to read with care" list on the dashboard and follow [add-a-target.md](add-a-target.md#when-a-target-goes-bad).

**A library changes its API.** The adapter then fails on every target, and the dashboard shows errors with the message. Read the library's README and fix its adapter, which is about 20 lines.

**GitHub Action versions.** `.github/workflows/daily.yml` uses major version tags (`actions/checkout@v7`). Raise them when GitHub announces that an old major version will stop working.

**The repo grows.** Each day adds about 10 small JSON files. That is a few megabytes a year. The dashboard only reads the last 30 days, so old folders in `results/` can be deleted at any time.

## Check that things still work after a change

```sh
python3 -m unittest discover tests
python3 -m scoreboard.run --target example --tries 1
python3 -m scoreboard.build
```

The first command tests the runner and the dashboard numbers with no network. The second starts every library once against an open page.

# Keeping it running

## What runs on its own

| Thing | How |
|---|---|
| New library releases | No version is pinned. Every run installs the newest release and saves its version. |
| A library that stops installing | Saved as "broken" and shown on the dashboard. The run goes on. |
| A library that hangs | Killed after `timeout` seconds, with its browser. Saved as an error. |
| New Chrome releases | The libraries use the Chrome on the machine, so keep it updated with the system. |
| The dashboard | Rebuilt and published after every run. |
| Weak targets | Marked on the dashboard (a control opens it, or nothing does). |

## What needs a person

**Targets go out of date.** This is the main job, a few minutes a month. Look at the "Targets to read with care" list on the dashboard and follow [add-a-target.md](add-a-target.md#when-a-target-goes-bad).

**A site shows a new kind of block page.** Its tries are then saved as "blocked, expected text missing", which is still correct but less clear. Add the page to the verdict rules as [testing.md](testing.md#when-you-meet-a-new-kind-of-block-page) shows.

**A library changes its API.** The adapter then fails on every target, and the dashboard shows errors with the message. Read the library's README and fix its adapter, which is about 20 lines.

**The repo grows.** Each day adds about 10 small JSON files. That is a few megabytes a year. The dashboard only reads the last 30 days, so old folders in `results/` can be deleted at any time.

## Check that things still work after a change

```sh
python3 -m stealth_board.check
python3 -m unittest discover tests
python3 -m stealth_board.run --target example --tries 1
```

The first two need no network. The third starts every library once against an open page. [testing.md](testing.md) explains each level.

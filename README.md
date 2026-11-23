# Stealth Board

Which open source scraping library still gets past bot protection today?

Stealth libraries break often. A new Chrome release or a new protection rule can stop one overnight, and nobody tells you. This project opens the same list of pages with every library once a day, using each library's newest release, and shows the results on one page.

- It runs on any Linux machine with one daily command. There are no proxies and no backend.
- The results are plain JSON files in this repo. There is no database.
- The dashboard is one static HTML page.

## What a result means

One **try** is one page load by one library. A try **passes** only when the real page content comes back. A status code of 200 is not enough, because block pages often return 200.

A try that fails is one of three kinds:

- **challenge**: the page kept showing a check or a captcha
- **blocked**: the site refused
- **error**: the library crashed or took too long

When a page shows a Cloudflare check box, the library clicks it once and waits again. The results say if a pass needed that click, and if the site refused the click.

Each run makes 3 tries per library, mode and target. The dashboard shows the pass rate over the last 7 and 30 days.

## What is tested

Libraries (the list lives in [`board.toml`](board.toml)):

| Library | What it is | Modes |
|---|---|---|
| requests | Control. Plain HTTP with no stealth | http |
| playwright | Control. Plain Playwright with no stealth | headless, headed |
| curl_cffi | HTTP client with Chrome's TLS fingerprint | http |
| patchright | Patched Playwright, driving real Chrome | headless, headed |
| camoufox | Firefox build that changes its fingerprint | headless, headed |
| nodriver | Drives Chrome over the DevTools protocol | headless, headed |
| zendriver | Kept-up fork of nodriver | headless, headed |
| scrapling | Scraping framework, its StealthyFetcher | headless, headed |
| seleniumbase | Its "Pure CDP Mode" | headless, headed |

**headless** means the browser has no window. **headed** means a real window on a virtual screen. Headed is harder to detect and uses more memory. Every library runs with the settings its own README recommends. Each adapter file says which settings and why.

Targets:

- one open page with no protection, as a sanity check
- two bot test pages that say if they see a robot
- nine pages behind Cloudflare, DataDome, HUMAN (PerimeterX) and Akamai

The two **controls** have no stealth at all. If a control opens a protected target, that target proves little, and the dashboard marks it.

## What this does not tell you

- Each test is one page load from one IP address with no proxy. It says nothing about thousands of requests.
- It loads one page. Logging in, clicking around, and other pages of the same site can be harder.
- Cloud servers have datacenter IPs, which protection systems trust the least. A home connection often does better. The dashboard keeps the two IP types apart.
- Sites change their protection, so a target can get easier or harder with no change in the library.

## Try it on your machine

You need Python 3.11 or newer, [uv](https://docs.astral.sh/uv/) and Google Chrome.

```sh
# one library, one target, one try, no window
python3 -m stealth_board.run --tool patchright --target cloudflare-practice --mode headless --tries 1

# build the dashboard data and open the page
python3 -m stealth_board.build
python3 -m http.server -d site 8000   # then open http://localhost:8000
```

The runner tests several libraries at the same time when the machine has the memory for it. `--jobs 1` runs them one by one.

The first run of a library downloads its browser, which can take a few minutes. More in [docs/run-locally.md](docs/run-locally.md).

## What is in this repo

```
board.toml                 the libraries, the targets and the run settings
adapters/                  one small script per library
stealth_board/run.py       runs the libraries against the targets, writes results/
stealth_board/verdict.py   decides pass, challenge or blocked
stealth_board/build.py     turns results/ into site/data.json
stealth_board/config.py    loads board.toml
stealth_board/check.py     checks that board.toml is valid
stealth_board/process.py   runs a command and kills everything it started
stealth_board/probe.py     looks at a new website before you add it
site/                      the dashboard: index.html, style.css, app.js
results/                   one folder per day, one JSON file per library
tests/                     tests against a local web server, with sample block pages
docs/                      the guides below
```

## Guides

- [How it works](docs/how-it-works.md): the full path from a URL to a number on the dashboard
- [Run it locally](docs/run-locally.md): setup, commands, and fixing common problems
- [Testing](docs/testing.md): the four test levels, testing a new website, and the click on a challenge box
- [Add a library](docs/add-a-library.md)
- [Add a target](docs/add-a-target.md)
- [Deploy it on a server](docs/deploy-on-a-server.md): the daily job, the dashboard, memory and speed
- [Keeping it running](docs/maintenance.md): what runs on its own and what needs a person

## Why this exists, and fair use

I built this to help the scraping community. People who collect public data need to know which open source tool still works today, and nobody publishes that in one place.

This is legal to do. The project only loads public pages, the same way a browser does, a few times a day, with no login. It keeps no page content, only "passed" or "blocked". It measures open source tools that anyone can already download. It does not ship a way to scrape any site.

Please keep it that way when you add targets: public pages only, a small number of loads, and no personal data. Laws and site terms differ between countries, so check the rules that apply to you before you run it on your own.

## License

MIT. See [LICENSE](LICENSE).

# Deploy it on a server

Any Linux server works. There is no database and no backend: a daily job writes JSON files, and a web server shows a folder of static files.

## 1. Install

```sh
sudo apt install xvfb
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install Google Chrome too. Four of the libraries drive the installed Chrome. Then clone this repo and check that it works:

```sh
python3 -m stealth_board.check
python3 -m unittest discover tests
python3 -m stealth_board.run --target example --tries 1 --mode http --mode headless
```

## 2. The daily job

Save this as `run-daily.sh` next to the repo and make it executable:

```sh
#!/bin/sh
set -e
cd /path/to/stealth-board
xvfb-run -a python3 -m stealth_board.run --runner vps --ip-type datacenter
python3 -m stealth_board.build
```

Use `--ip-type residential` when the server is on a home connection. Use a short public name for `--runner`. It becomes part of the result file names, so do not put a host name or anything private in it.

Run it every day with cron (`crontab -e`):

```
17 5 * * * /path/to/run-daily.sh >> /var/log/stealth-board.log 2>&1
```

## 3. Show the dashboard

The dashboard is the `site/` folder: `index.html`, `style.css`, `app.js` and the `data.json` that the build step writes. Point any web server at it. With nginx:

```
server {
    listen 80;
    server_name board.example.com;
    root /path/to/stealth-board/site;
}
```

Before the first run there is no `data.json`, and the page says "No results yet".

## Memory and speed

Each tool runs in its own job, and jobs run side by side. Inside one job, a tool opens one browser at a time.

By default the runner looks at the free memory and starts one job per 4 GB, with a limit of 4 jobs. So a server with 2 GB free runs one tool at a time, and one with 16 GB free runs four.

| Free memory | Jobs | A full run (9 tools) takes about |
|---|---|---|
| under 8 GB | 1 | 3 hours |
| 8 GB | 2 | 1.5 hours |
| 16 GB or more | 4 | under 1 hour |

Set it yourself with `--jobs`:

```sh
xvfb-run -a python3 -m stealth_board.run --jobs 2 --runner vps --ip-type datacenter
```

Do not go far above 4. More jobs means more page loads at the same moment from one IP address, and sites raise their guard when they see that. The results would then say more about the server than about the libraries.

## Keep the results

`results/` holds one folder per day. The dashboard reads the last 30 days. To keep the history safe, commit the folder to your own copy of the repo or back it up. Older folders can be deleted at any time.

## Results from a second place

A second machine can fill the other IP type tab. Run the same command there with another `--runner` name and `--ip-type`, and copy its `results/` files into the server's `results/` folder.

# Publish it on GitHub

This sets up the daily run and the public dashboard. It costs nothing for a public repo.

## Steps

1. Create a **public** repo on GitHub and push this project to it.
2. In the repo, open **Settings > Pages** and set **Source** to **GitHub Actions**.
3. Open **Settings > Actions > General**. Under **Workflow permissions** choose **Read and write permissions**, so the run can commit the result files.
4. Open the **Actions** tab, pick **Daily run**, and press **Run workflow** to start the first run by hand.
5. When it finishes, the dashboard is at `https://YOUR_NAME.github.io/REPO_NAME/`.

After that it runs by itself every day at 05:17 UTC.

## What the workflow does

- `list-tools` reads the tool names from `board.toml`.
- `test` runs one job per tool on a fresh Ubuntu machine, under a virtual screen. It installs Xvfb and Google Chrome itself.
- `publish` collects the result files, commits them to `results/`, builds `site/data.json` and publishes `site/`.

A tool that crashes only fails its own job. The publish job still runs.

## Good to know

- **Schedule delays.** GitHub may start a scheduled run late when it is busy.
- **Inactive repos.** GitHub turns off scheduled workflows in a public repo after 60 days with no activity. The daily commit of results counts as activity, so this does not happen while runs succeed.
- **IP type.** GitHub's machines have datacenter IPs. Results from there are saved as "datacenter".
- **GitHub's terms.** Read the Actions section of the [GitHub Terms for Additional Products and Features](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features) before you turn this on. It says Actions must not be used for "disrupting, gaining, or attempting to gain unauthorized access to, any service", must not put a load on GitHub out of proportion to the benefit, and on GitHub's own machines must relate to testing the software in the repo. This project loads a few public pages per day to test open source tools, with no login. Whether that fits is your call as the repo owner.

## Add results from a home connection

A second runner on a home connection fills the "Residential IP" tab. Run this on any machine, then commit the new files in `results/`:

```sh
xvfb-run -a python3 -m stealth_board.run --runner home --ip-type residential
git add results && git commit -m "Add residential results" && git push
```

Use a short public name for `--runner`. Do not put a host name or anything private in it, because it is part of the file name.

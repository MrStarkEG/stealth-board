# Everything the runner needs in one image: Chrome, a virtual screen and uv.
# Nothing is installed on the host. See docs/deploy-on-a-server.md.
FROM python:3.12-slim-bookworm

# The libgtk and libdbus lines are for Camoufox (Firefox). Chrome brings its own.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl git procps xauth xvfb \
        libasound2 libdbus-glib-1-2 libgtk-3-0 libxtst6 \
    && curl -fsSLo /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y --no-install-recommends /tmp/chrome.deb \
    && rm -rf /tmp/chrome.deb /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY . .

CMD ["python3", "-m", "stealth_board.run", "--runner", "vps", "--ip-type", "datacenter"]

# Scraper bridge — droplet HTTP service for “Run spider” from the UI

This folder contains a small **FastAPI** app (`main.py`) that:

- Runs `scrapy crawl <spider>` in the **background** and writes **`_bridge_crawl_logs/<spider>-<timestamp>.log`**
- Returns a **`message`** that includes the **full** `tail -f /absolute/path/...` command (copy-paste on the droplet), plus **`logTailCommand`** in JSON for the dashboard.

## Install (droplet)

```bash
cd /root/scrappingproxy/scraper-bridge   # or your path; copy files from this repo
python3 -m venv .venv-bridge && source .venv-bridge/bin/activate
pip install -r requirements.txt
```

Environment (systemd `EnvironmentFile` or unit):

- `SCRAPY_PROJECT_DIR` — default `/root/scrappingproxy`
- `SCRAPY_PYTHON` — default `$SCRAPY_PROJECT_DIR/.venv/bin/python`
- `SCRAPER_BRIDGE_SECRET` — optional; if set, the same value must be sent using one of:
  - **`X-Scraper-Bridge-Secret`** (preferred)
  - **`X-Bridge-Secret`**
  - **`Authorization: Bearer <secret>`**

Run manually:

```bash
uvicorn main:app --host 0.0.0.0 --port 8787
```

Point your systemd `scraper-bridge` unit at this venv + `uvicorn` (same as before).

## API (aliases for Vercel-style paths)

| Method | Path | Notes |
|--------|------|--------|
| GET | `/health` | No auth |
| GET | `/spiders` | `scrapy list` |
| GET | `/api/scraper/spiders` | Same |
| POST | `/crawl` | JSON body `{"spider":"mcdavid"}` |
| POST | `/api/scraper/crawl` | Same |

## Crawl response (green banner text source)

The UI should show **`message`** and/or **`logTailCommand`**:

```json
{
  "ok": true,
  "spider": "mcdavid",
  "message": "Spider started in background. stdout/stderr → _bridge_crawl_logs/mcdavid-….log On the droplet, stream this log with: tail -f '/root/scrappingproxy/_bridge_crawl_logs/mcdavid-….log' This does not use systemd scrapy-spider@… timers.",
  "logTailCommand": "tail -f '/root/scrappingproxy/_bridge_crawl_logs/mcdavid-….log'",
  "logFile": "/root/scrappingproxy/_bridge_crawl_logs/mcdavid-….log",
  "logFileRelative": "_bridge_crawl_logs/mcdavid-….log"
}
```

## After deploy

```bash
sudo systemctl restart scraper-bridge
```

If the dashboard still shows the old sentence only, update the React page to display **`message`** in full or **`logTailCommand`** in monospace with a copy button.

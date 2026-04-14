# InstantIntelProxyScraper

Production Scrapy project for RV inventory scraping, proxy support, and Supabase upsert.

## Repository structure

```
InstantIntelProxyScraper/
├── scrapy.cfg                 # Scrapy project entry (points at Rocmob)
├── requirements.txt           # Python deps (scrapy, supabase, pandas, requests, …)
├── .env.example               # Template for local / droplet env vars (copy to .env)
│
├── Rocmob/                    # Scrapy project package
│   ├── settings.py            # Global settings, proxy env, dotenv load
│   ├── middlewares.py         # ProxyMiddleware (+ optional spider middleware)
│   ├── rocmob_cfg.py          # Shared Supabase client (lazy init)
│   ├── pipelines.py           # Item pipelines
│   ├── items.py               # Scrapy item models
│   ├── rocmob_query.py        # SQL/query helpers (legacy paths)
│   ├── table_schema.py        # Table/schema reference
│   └── spiders/               # One module per dealer / spider
│       └── *.py               # Each file defines `name = "..."` for `scrapy crawl`
│
├── Hootprocess/               # Hoot CSV + transfer jobs (non-Scrapy)
│   ├── supabase_key.py        # Shared HOOT_SUPABASE_SECRET_KEY / service_role resolution
│   ├── hoot_import.py         # CSV → `hoot_inventory` upsert
│   ├── hoot_inventorydata.py  # RPC `run_inventory_from_hoot` → `inventorydata`
│   └── requirements.txt       # Standalone pip list; droplet also uses root requirements.txt
│
├── .github/workflows/
│   └── scrapy-production.yml  # CI: list spiders matrix, run with secrets
│
├── deploy/systemd/
│   ├── scrapy-spider@.service # Template unit: `scrapy crawl %i`
│   ├── scrapy-spider-*.timer  # Per-spider schedules (staggered UTC, see docs)
│   ├── hoot-import.service    # Oneshot: `hoot_import.py`
│   ├── hoot-import.timer      # Daily 04:15 UTC
│   ├── hoot-inventorydata.service  # Oneshot: `hoot_inventorydata.py` (RPC transfer)
│   └── hoot-inventorydata.timer    # Daily 05:30 UTC (after CSV import)
│
└── docs/
    ├── digitalocean-setup.md  # Droplet: venv, .env, systemd copy/enable
    └── debug.md               # journalctl, timers, env checks, stagger table
```

**Runtime flow (high level)**

1. Environment: `.env` or process env supplies `SUPABASE_*` and optional `PROXY_*`.
2. Scrapy loads `Rocmob/settings.py` → proxy middleware applies unless a spider sets `ENABLE_PROXY` false.
3. Each spider crawls targets and upserts via `Rocmob/rocmob_cfg.py` → Supabase.
4. **Hoot import**: `Hootprocess/hoot_import.py` upserts **`hoot_inventory`** from CSV feeds; **`Hootprocess/hoot_inventorydata.py`** calls RPC **`run_inventory_from_hoot`** to refresh **`inventorydata`** for a date. Both use **`HOOT_SUPABASE_SECRET_KEY`** when set, else **`SUPABASE_SERVICE_ROLE_KEY`**. Optional env for import: `HOOT_ACTIVE_PULL_ONLY`, `HOOT_INCLUDE_INACTIVE_CLIENTS`, `HOOT_CHUNK_SIZE`, `HOOT_HTTP_*`; for transfer: **`HOOT_TRANSFER_DATE`** (YYYY-MM-DD, default today). Timers: **`hoot-import.timer`** **04:15 UTC**, **`hoot-inventorydata.timer`** **05:30 UTC** (staggered after import).
5. **GitHub Actions**: install deps, `scrapy list` / `scrapy crawl` with repository secrets.
6. **Droplet**: same code + venv; copy `deploy/systemd` units and enable timers (see `docs/digitalocean-setup.md`). Enable **`hoot-import`** and **`hoot-inventorydata`** units if you use the Hoot pipeline on that host.

## Requirements

- Python 3.11+
- Dependencies from `requirements.txt`
- Supabase project credentials
- Optional proxy credentials (recommended for anti-bot protected targets)

## Environment Variables

Copy `.env.example` to `.env` for local runs:

```bash
cp .env.example .env
```

Required for data writes:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` (or `SUPABASE_KEY`, but service role is recommended) — used by Scrapy / `Rocmob`

Hoot pipeline (optional on hosts that run `hoot-import` / `hoot-inventorydata` timers):

- **`HOOT_SUPABASE_SECRET_KEY`** — preferred elevated key for `hoot_import.py` and `hoot_inventorydata.py` (Secret `sb_secret_...` or legacy `service_role` JWT). If empty, both fall back to `SUPABASE_SERVICE_ROLE_KEY`.
- **`HOOT_TRANSFER_DATE`** — optional `YYYY-MM-DD` for `hoot_inventorydata.py` (defaults to today).

Proxy settings:

- `ENABLE_PROXY` (`true`/`false`, default `true`)
- `PROXY_URL` (example: `http://brd.superproxy.io:33335/`)
- `PROXY_AUTH` (single credential: `username:password`)
- `PROXY_AUTH_LIST` (optional rotation list, comma-separated)

Runtime tuning:

- `SCRAPY_LOG_LEVEL`
- `SCRAPY_RETRY_TIMES`
- `SCRAPY_DOWNLOAD_TIMEOUT`

## Local Run

Install dependencies:

```bash
pip install -r requirements.txt
```

List spiders:

```bash
python -m scrapy list
```

Run one spider:

```bash
python -m scrapy crawl Livingston
```

## GitHub Actions

Workflow: `.github/workflows/scrapy-production.yml`

### Required repository secrets

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

### Optional proxy secrets

- `PROXY_URL`
- `PROXY_AUTH`
- `PROXY_AUTH_LIST`

### Manual run inputs

- `spider_names`: comma-separated spider names (blank = run all discovered spiders)
- `use_proxy`: toggle proxy per run (`true`/`false`)
- `fail_fast`: stop remaining matrix jobs after first failure

### Schedule

- Cron is optional in the workflow YAML. When enabled, a typical pattern is `0 */6 * * *` (every 6 hours). If the `schedule:` block is commented out, only manual **Run workflow** runs execute.

## DigitalOcean deployment

A complete setup guide is available in `docs/digitalocean-setup.md`.

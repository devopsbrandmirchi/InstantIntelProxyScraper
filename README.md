# InstantIntelProxyScraper

Production Scrapy project for RV inventory scraping, proxy support, and Supabase upsert.

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
- `SUPABASE_SERVICE_ROLE_KEY` (or `SUPABASE_KEY`, but service role is recommended)

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

- `0 */6 * * *` (every 6 hours)

## DigitalOcean deployment

A complete setup guide is available in `docs/digitalocean-setup.md`.

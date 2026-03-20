# EasyqScrapLive - Production Scrapy Setup

This repository is configured for production scraping with:

- Scrapy spiders in `Rocmob/spiders`
- Proxy-required execution (via environment/secrets)
- GitHub Actions workflow with per-spider parallel matrix jobs

## Requirements

- Python 3.11+
- Scrapy (installed through `requirements.txt`)
- Valid proxy credentials

## Proxy Configuration (Required)

The scraper reads proxy settings from environment variables:

- `ENABLE_PROXY` (`true`/`false`, default `true`)
- `PROXY_URL` (example: `http://zproxy.lum-superproxy.io:22225/`)
- `PROXY_AUTH` (single credential: `username:password`)
- `PROXY_AUTH_LIST` (optional rotation list, comma-separated)

If `PROXY_AUTH_LIST` is set, credentials rotate per request.

## Local Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run all spiders:

```bash
python run_spiders.py
```

Run selected spiders:

```bash
python run_spiders.py --spiders spider_one,spider_two
```

Run with timeout and fail-fast:

```bash
python run_spiders.py --spiders spider_one --timeout-seconds 1800 --fail-fast
```

## GitHub Actions (Production)

Workflow file:

- `.github/workflows/scrapy-production.yml`

### Add repository secrets

In GitHub repo settings -> Secrets and variables -> Actions, add:

- `PROXY_URL` (required)
- `PROXY_AUTH` (recommended if using one account)
- `PROXY_AUTH_LIST` (optional if rotating credentials)

### Manual run

Use **Run workflow** and optionally provide:

- `spider_names`: comma-separated spider names (example: `bamarv,alrvsales,fraserway`)
- `fail_fast`: stop matrix early when one spider fails

If you do not change `spider_names`, the fixed default list is used:

- `bamarv,alrvsales,fraserway`

### Scheduled run

The workflow is scheduled with cron:

- `0 */6 * * *` (every 6 hours)

## Notes

- Middleware supports `request.meta["skip_proxy"] = True` for requests that must bypass proxy.
- Keep credentials in GitHub Secrets only; do not hardcode proxy auth in code.

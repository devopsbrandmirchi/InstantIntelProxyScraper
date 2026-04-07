# Debug & operations cheat sheet

Quick reference for checking timers, logs, Scrapy runs, and environment on the DigitalOcean droplet (and similar Linux hosts).

---

## Scrapy (manual test)

From project directory with venv active:

```bash
cd /root/scrappingproxy
source .venv/bin/activate
#git pull origin main
python -m scrapy list
python -m scrapy crawl Livingston
python -m scrapy crawl Livingston -s LOG_LEVEL=INFO
```

Replace `Livingston` with any spider name from `scrapy list`.

---

## Environment & proxy (what Scrapy actually sees)

```bash
cd /root/scrappingproxy
source .venv/bin/activate
python - <<'PY'
from Rocmob import settings
print("ENABLE_PROXY:", settings.ENABLE_PROXY)
print("PROXY_URL:", settings.PROXY_URL)
print("HTTP_PROXY entries:", len(settings.HTTP_PROXY))
PY
```

- `.env` is loaded from project root when `python-dotenv` is installed and `Rocmob/settings.py` loads it.
- `systemd` units should use `EnvironmentFile=/root/scrappingproxy/.env` so vars exist without relying on shell.

---

## Per-spider proxy on/off

- **Global default:** `ENABLE_PROXY` in `.env` / environment.
- **Single spider off:** `custom_settings = {"ENABLE_PROXY": False}` in that spider (e.g. Livingston).
- **Single request off:** `meta={"skip_proxy": True}` on that `Request`.

---

## systemd timers — did the schedule run?

### List all scrapy-related timers (next / last)

```bash
systemctl list-timers --all | grep scrapy-spider
```

### One timer status (next trigger, last trigger)

```bash
systemctl status scrapy-spider-Livingston.timer
```

### Confirm timer is enabled

```bash
systemctl is-enabled scrapy-spider-Livingston.timer
```

### Inspect unit definitions

```bash
systemctl cat scrapy-spider-Livingston.timer
systemctl cat scrapy-spider@.service
```

### After changing `.timer` or `.service` files under `/etc/systemd/system/`

```bash
systemctl daemon-reload
systemctl restart scrapy-spider-Livingston.timer
```

---

## systemd — did the spider service run?

### Recent logs for one spider

```bash
journalctl -u scrapy-spider@Livingston.service --since "today" --no-pager
```

### Window around scheduled UTC time (adjust date)

```bash
journalctl -u scrapy-spider@Livingston.service \
  --since "2026-03-26 01:25 UTC" --until "2026-03-26 01:40 UTC" --no-pager
```

### Follow live

```bash
journalctl -u scrapy-spider@Livingston.service -f
```

### Many template instances (broad filter)

```bash
journalctl -u 'scrapy-spider@*.service' -n 300 --no-pager
```

---

## systemd — force one run now (debug)

```bash
systemctl start scrapy-spider@Livingston.service
journalctl -u scrapy-spider@Livingston.service -n 100 --no-pager
```

---

## Schedule format (this repo)

Timer files use **twice daily UTC** and are staggered by spider minute:

- `OnCalendar=*-*-* 01:MM:00 UTC`
- `OnCalendar=*-*-* 05:MM:00 UTC`

### Current stagger map

| Spider name | UTC runs |
|---|---|
| `Livingston` | `01:01`, `05:01` |
| `RazorbackCampers` | `01:03`, `05:03` |
| `WadesRvJO` | `01:05`, `05:05` |
| `campingworldareaFAR` | `01:07`, `05:07` |
| `campingworldareaLIT` | `01:09`, `05:09` |
| `campingworldareaLOW` | `01:11`, `05:11` |
| `campingworldareaSAR` | `01:13`, `05:13` |
| `claycooleyford` | `01:15`, `05:15` |
| `crabtreerv` | `01:17`, `05:17` |
| `funtownrvLR` | `01:19`, `05:19` |
| `mcdavid` | `01:21`, `05:21` |
| `moixrvhs` | `01:23`, `05:23` |
| `moixrvmo` | `01:25`, `05:25` |
| `moixrvsc` | `01:27`, `05:27` |
| `rockyridgerv` | `01:29`, `05:29` |
| `rohrmantoyota` | `01:31`, `05:31` |
| `rvcitybiz` | `01:33`, `05:33` |
| `rvcountry` | `01:35`, `05:35` |
| `skyriverrv` | `01:37`, `05:37` |
| `trailerhitchrv` | `01:39`, `05:39` |
| `wheelsrv` | `01:41`, `05:41` |
| `kokomoautomobiletoyota` | `01:43`, `05:43` |
| `kokomoautomobilehonda` | `01:45`, `05:45` |

Server clock should be UTC or you must interpret logs accordingly (`timedatectl`).

---

## Proxy errors (quick meaning)

| Symptom | Likely cause |
|--------|----------------|
| `407 ... ip_forbidden` | Proxy zone blocks client IP (e.g. GitHub runner); fix in provider dashboard or use allowed IP (droplet). |
| `407 ... Proxy Authentication Required` | Missing/wrong `PROXY_AUTH` or wrong `PROXY_URL` for that product. |
| `403` on target without proxy | Site blocks datacenter/direct IP; may need proxy or different headers. |

---

## GitHub Actions

- Manual runs: **Actions → workflow → Run workflow**.
- Toggle proxy per run: input `use_proxy` (if present in workflow).
- Cron: if commented out in workflow YAML, only manual runs run until re-enabled.

---

## Shared droplet with Docker

- Prefer `apt update` and **targeted** `apt install` only; defer full `apt upgrade` to a maintenance window.
- Scrapy uses an isolated `.venv` under the project folder; systemd runs do not start/stop Docker by themselves.
- Heavy parallel spiders can contend for CPU/RAM with containers — stagger timers if needed.

---

## Deploy files in repo

- `deploy/systemd/scrapy-spider@.service` — template service.
- `deploy/systemd/scrapy-spider-<SpiderName>.timer` — per-spider schedule.
- Copy to `/etc/systemd/system/` then `daemon-reload` and `enable --now` timers.

See also: `docs/digitalocean-setup.md`.

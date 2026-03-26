# DigitalOcean Droplet Setup

This guide installs and runs this Scrapy project on a DigitalOcean Ubuntu droplet.

## 1) Connect and prepare server

```bash
ssh root@YOUR_DROPLET_IP
apt update
apt install -y python3 python3-venv python3-pip git
```

If this droplet already runs other apps (for example Docker projects), avoid blanket `apt upgrade -y` during business hours. Use a maintenance window if you need full OS upgrades, because package upgrades can restart services.

## 2) Place project in your folder

If your folder is already created (`scrappingproxy`), use it:

```bash
cd /root/scrappingproxy
git clone https://github.com/<your-org-or-user>/InstantIntelProxyScraper.git .
```

If code already exists there, run:

```bash
cd /root/scrappingproxy
git pull
```

## 3) Create virtual environment and install deps

```bash
cd /root/scrappingproxy
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4) Configure environment

Create `.env` from example:

```bash
cd /root/scrappingproxy
cp .env.example .env
```

Edit `.env` and set:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ENABLE_PROXY=true` or `false`
- `PROXY_URL`
- `PROXY_AUTH` (or `PROXY_AUTH_LIST`)

## 5) Test commands

```bash
cd /root/scrappingproxy
source .venv/bin/activate
python -m scrapy list
python -m scrapy crawl Livingston
```

## 6) Run many spiders with systemd templates (recommended)

For 20+ spiders, use one reusable template service + one timer per spider.

Create a template service (or copy from `deploy/systemd/scrapy-spider@.service`):

```bash
cat > /etc/systemd/system/scrapy-spider@.service << 'EOF'
[Unit]
Description=Scrapy spider %i
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/root/scrappingproxy
EnvironmentFile=/root/scrappingproxy/.env
ExecStart=/root/scrappingproxy/.venv/bin/python -m scrapy crawl %i
User=root
Group=root
StandardOutput=journal
StandardError=journal
EOF
```

Create one timer per spider with its own schedule. For this repo, starter timer files are included in `deploy/systemd/` and set to run at `01:30 UTC` and `05:30 UTC`.

You can copy them directly:

```bash
cp /root/scrappingproxy/deploy/systemd/scrapy-spider@.service /etc/systemd/system/
cp /root/scrappingproxy/deploy/systemd/*.timer /etc/systemd/system/
```

Example timer structure:

```bash
cat > /etc/systemd/system/scrapy-spider-Livingston.timer << 'EOF'
[Unit]
Description=Run spider Livingston at 01:30 and 05:30 UTC

[Timer]
OnCalendar=*-*-* 01:30:00 UTC
OnCalendar=*-*-* 05:30:00 UTC
Unit=scrapy-spider@Livingston.service
Persistent=true

[Install]
WantedBy=timers.target
EOF
```

Reload and enable:

```bash
systemctl daemon-reload
systemctl enable --now scrapy-spider-Livingston.timer
systemctl enable --now scrapy-spider-mcdavid.timer
systemctl enable --now scrapy-spider-moixrvhs.timer
systemctl enable --now scrapy-spider-moixrvsc.timer
systemctl enable --now scrapy-spider-moixrvmo.timer
systemctl list-timers | grep scrapy-spider
```

Create additional timer files for your other spiders (`scrapy-spider-<SpiderName>.timer`) and set each schedule as needed.

## 7) Useful operations (debug + rerun)

Run one spider immediately (manual debug/rerun):

```bash
systemctl start scrapy-spider@Livingston.service
```

See last logs for one spider:

```bash
journalctl -u scrapy-spider@Livingston.service -n 200 --no-pager
```

Follow logs live for one spider:

```bash
journalctl -u scrapy-spider@Livingston.service -f
```

See all scrape service logs:

```bash
journalctl -u 'scrapy-spider@*.service' -n 300 --no-pager
```

## Notes

- If proxy returns `407 ... ip_forbidden`, your proxy account is blocking the droplet IP. Update proxy provider access settings or disable proxy.
- Keep `.env` out of git.
- Consider creating a non-root Linux user for long-term production hardening.

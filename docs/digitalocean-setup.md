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
- `SUPABASE_SERVICE_ROLE_KEY` (Scrapy / pipelines)
- `HOOT_SUPABASE_SECRET_KEY` (optional but recommended for `hoot-import.service` and `hoot-inventorydata.service`: Supabase **Secret** key `sb_secret_...` or legacy `service_role` JWT)
- `ENABLE_PROXY=true` or `false`
- `PROXY_URL` (use `http://brd.superproxy.io:44445/`; do not use legacy `zproxy.*` hosts or ports `22225` / `33335`)
- `PROXY_AUTH` (or `PROXY_AUTH_LIST`)

Allow outbound TCP to `brd.superproxy.io:44445` if the droplet firewall or `ufw` restricts egress. DigitalOcean allows all outbound traffic by default.

**Hoot timers (optional):** Copy `deploy/systemd/hoot-import.service`, `hoot-import.timer`, `hoot-inventorydata.service`, and `hoot-inventorydata.timer` to `/etc/systemd/system/`, then `systemctl daemon-reload` and `systemctl enable --now hoot-import.timer hoot-inventorydata.timer` (CSV import **04:15 UTC**, `inventorydata` transfer **05:30 UTC**).

## 5) Test commands

```bash
cd /root/scrappingproxy
source .venv/bin/activate
python -m scrapy list
python -m scrapy crawl Livingston
python -m scrapy crawl Livingston -s LOG_LEVEL=INFO
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

Create one timer per spider with its own schedule. For this repo, starter timer files are included in `deploy/systemd/` and are staggered across minutes between `01:01-01:45 UTC` and `05:01-05:45 UTC`.

You can copy them directly:

```bash
cp /root/scrappingproxy/deploy/systemd/scrapy-spider@.service /etc/systemd/system/
cp /root/scrappingproxy/deploy/systemd/*.timer /etc/systemd/system/
```

Example timer structure:

```bash
cat > /etc/systemd/system/scrapy-spider-Livingston.timer << 'EOF'
[Unit]
Description=Run spider Livingston at 01:01 and 05:01 UTC

[Timer]
OnCalendar=*-*-* 01:01:00 UTC
OnCalendar=*-*-* 05:01:00 UTC
Unit=scrapy-spider@Livingston.service
Persistent=true

[Install]
WantedBy=timers.target
EOF
```

Reload and enable **all** spider timers (one `.timer` file per spider in `deploy/systemd/`):

```bash
systemctl daemon-reload
for unit in /etc/systemd/system/scrapy-spider-*.timer; do
  [ -e "$unit" ] || continue
  systemctl enable --now "$(basename "$unit")"
done
systemctl list-timers | grep scrapy-spider
```

To enable only some spiders, run `systemctl enable --now scrapy-spider-<SpiderName>.timer` for each.

Create additional timer files for new spiders (`scrapy-spider-<SpiderName>.timer`) and set each schedule as needed.

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

## Bright Data port 44445 (required after deploy)

Bright Data retired ports `22225` / `33335` and legacy `zproxy.*` hostnames. After pulling this change, update live config — repo defaults do not override an existing `.env` or GitHub secret.

On the droplet:

```bash
cd /root/scrappingproxy
# Confirm current value (host/port only)
grep '^PROXY_URL=' .env
# Set the new endpoint; leave PROXY_AUTH unchanged
sed -i 's|^PROXY_URL=.*|PROXY_URL=http://brd.superproxy.io:44445/|' .env
grep '^PROXY_URL=' .env
```

Allow outbound TCP `44445` if the droplet firewall or `ufw` restricts egress, then test:

```bash
set -a && source /root/scrappingproxy/.env && set +a
curl --proxy "$PROXY_URL" --proxy-user "$PROXY_AUTH" "https://geo.brdtest.com/mygeo.json"
```

If a Bright Data CA is installed under `/usr/local/share/ca-certificates/`, replace it with `brightdata_root_ca_44445.crt` from [brightdata_proxy_ca.zip](https://brightdata.com/static/brightdata_proxy_ca.zip) and run `sudo update-ca-certificates`.

GitHub Actions uses `secrets.PROXY_URL`. After merge, set that secret to `http://brd.superproxy.io:44445/`:

```bash
gh secret set PROXY_URL --body 'http://brd.superproxy.io:44445/'
```

## Journald size cap

Spider stdout goes to journald. Cap it so logs do not fill the disk. This limit applies to **the whole droplet**, including other apps.

On the production host this is already set (`/etc/systemd/journald.conf.d/size.conf`): `SystemMaxUse=1G`, `MaxRetentionSec=14day`. See `docs/debug.md` for check/vacuum commands.

## Notes

- If proxy returns `407 ... ip_forbidden`, your proxy account is blocking the droplet IP. Update proxy provider access settings or disable proxy.
- Keep `.env` out of git.
- Consider creating a non-root Linux user for long-term production hardening.

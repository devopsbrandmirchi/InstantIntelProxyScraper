# DigitalOcean Droplet Setup

This guide installs and runs this Scrapy project on a DigitalOcean Ubuntu droplet.

## 1) Connect and prepare server

```bash
ssh root@YOUR_DROPLET_IP
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip git
```

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

## 6) Run with systemd (recommended)

Create service file:

```bash
cat > /etc/systemd/system/livingston-scrapy.service << 'EOF'
[Unit]
Description=Livingston Scrapy Spider
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/root/scrappingproxy
EnvironmentFile=/root/scrappingproxy/.env
ExecStart=/root/scrappingproxy/.venv/bin/python -m scrapy crawl Livingston
User=root
Group=root
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

Create timer (example: every 6 hours):

```bash
cat > /etc/systemd/system/livingston-scrapy.timer << 'EOF'
[Unit]
Description=Run Livingston spider every 6 hours

[Timer]
OnBootSec=5min
OnUnitActiveSec=6h
Persistent=true

[Install]
WantedBy=timers.target
EOF
```

Enable and start timer:

```bash
systemctl daemon-reload
systemctl enable --now livingston-scrapy.timer
systemctl list-timers | grep livingston
```

## 7) Useful operations

Run once immediately:

```bash
systemctl start livingston-scrapy.service
```

See logs:

```bash
journalctl -u livingston-scrapy.service -n 200 --no-pager
```

Follow logs live:

```bash
journalctl -u livingston-scrapy.service -f
```

## Notes

- If proxy returns `407 ... ip_forbidden`, your proxy account is blocking the droplet IP. Update proxy provider access settings or disable proxy.
- Keep `.env` out of git.

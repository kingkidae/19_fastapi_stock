#!/bin/bash
# EC2 user-data: runs once on first boot. Installs the app and the auto-deploy timer.
# Launch: aws ec2 run-instances ... --user-data file://deploy/setup.sh
set -euxo pipefail
exec > >(tee /var/log/stock-setup.log) 2>&1
export HOME=/root

apt-get update -y
apt-get install -y git curl
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin UV_NO_MODIFY_PATH=1 sh

# code stays root-owned; the app user can read it but not modify it
useradd --system --no-create-home --shell /usr/sbin/nologin app
git clone https://github.com/kingkidae/19_fastapi_stock.git /opt/app

cat > /etc/systemd/system/stock.service <<'EOF'
[Unit]
Description=FastAPI stock dashboard
After=network-online.target
Wants=network-online.target

[Service]
User=app
WorkingDirectory=/opt/app
ExecStart=/opt/app/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 80
AmbientCapabilities=CAP_NET_BIND_SERVICE
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/stock-update.service <<'EOF'
[Unit]
Description=Deploy new commits from GitHub
After=network-online.target

[Service]
Type=oneshot
Environment=HOME=/root
ExecStart=/bin/bash /opt/app/deploy/update.sh
EOF

cat > /etc/systemd/system/stock-update.timer <<'EOF'
[Unit]
Description=Check GitHub for new commits every minute

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable stock
bash /opt/app/deploy/update.sh   # first deploy: uv sync + start
systemctl enable --now stock-update.timer
echo "STOCK SETUP DONE"

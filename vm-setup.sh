#!/usr/bin/env bash
# Atosu StreamPipes — one-shot VM bootstrap (Ubuntu 22.04 ARM64, Oracle Always Free A1).
# Run as: curl-or-paste this on a fresh VM. Installs Docker, clones the repo,
# builds the Atosu-branded image, starts the stack, installs pipeline elements.
#
# Usage:
#   REPO=https://<TOKEN>@github.com/mrvivekjagtap-wq/streampipes-demo.git ./vm-setup.sh
#   (or make the repo public and use the plain https URL)
set -euo pipefail
REPO="${REPO:-https://github.com/mrvivekjagtap-wq/streampipes-demo.git}"
DIR="${DIR:-$HOME/streampipes-demo}"

echo "==> Installing Docker"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER" || true
  sudo systemctl enable --now docker
fi

echo "==> Opening host firewall for port 80 (Oracle images ship a restrictive iptables)"
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT || true
sudo netfilter-persistent save 2>/dev/null || sudo bash -c 'iptables-save > /etc/iptables/rules.v4' 2>/dev/null || true

echo "==> Cloning $REPO"
[ -d "$DIR/.git" ] || sudo -u "$USER" git clone "$REPO" "$DIR"
cd "$DIR"

echo "==> Building + starting the Atosu StreamPipes stack"
sudo docker compose up -d --build

echo "==> Installing bundled pipeline elements (waits for backend, ~2-3 min)"
sudo BASE=http://localhost:80 bash ./install-extensions.sh || true

IP=$(curl -s ifconfig.me || echo YOUR_VM_IP)
cat <<EOF

==================================================================
  Atosu StreamPipes is up.
  Open:  http://$IP/      (once the OCI Security List allows port 80)
  Login: admin@streampipes.apache.org / admin  <-- CHANGE THIS
==================================================================
EOF

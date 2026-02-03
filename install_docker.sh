#!/usr/bin/env bash
set -euo pipefail

if command -v docker >/dev/null 2>&1; then
  echo "Docker already installed."
  exit 0
fi

if ! command -v apt >/dev/null 2>&1; then
  echo "ERROR: apt not found. This script supports Ubuntu/Debian only."
  exit 1
fi

echo "==> Installing Docker + Compose (Ubuntu/Debian)"
sudo apt update
sudo apt install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

arch="$(dpkg --print-architecture)"
codename="$(. /etc/os-release && echo "$VERSION_CODENAME")"
echo "deb [arch=${arch} signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${codename} stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

if id -nG "$USER" | grep -qw docker; then
  :
else
  sudo usermod -aG docker "$USER" || true
  echo "==> Added $USER to docker group. Re-login may be required."
fi

echo "==> Docker installed"

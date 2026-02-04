#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-$(pwd)}"
BRANCH="${BRANCH:-main}"
ENV_FILE="$REPO_DIR/.env"
ENV_EXAMPLE="$REPO_DIR/.env.example"

usage() {
  cat <<USAGE
Usage:
  ./deploy.sh [GROWW_API_KEY] [GROWW_API_SECRET]

Options via env:
  REPO_DIR=/path/to/repo
  BRANCH=main

Behavior:
  - pulls latest from origin/main
  - copies .env.example -> .env if missing
  - installs Docker if missing
  - prompts for GROWW_API_KEY and GROWW_API_SECRET if not provided
  - builds with --no-cache and restarts docker compose
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

cd "$REPO_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "==> Docker not found. Installing Docker + Compose (Ubuntu)..."
  if ! command -v apt >/dev/null 2>&1; then
    echo "ERROR: apt not found. Install Docker manually for your OS."
    exit 1
  fi

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
    : # already in docker group
  else
    sudo usermod -aG docker "$USER" || true
    echo "==> Added $USER to docker group. Re-login may be required."
  fi
fi

echo "==> Fetching latest code ($BRANCH)"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git fetch origin "$BRANCH"
  git checkout "$BRANCH"
  git pull --ff-only origin "$BRANCH"
else
  echo "ERROR: $REPO_DIR is not a git repository"
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "$ENV_EXAMPLE" ]]; then
    echo "==> Creating .env from .env.example"
    cp "$ENV_EXAMPLE" "$ENV_FILE"
  else
    echo "ERROR: .env.example not found"
    exit 1
  fi
fi

EXISTING_GROWW_KEY=""
EXISTING_GROWW_SECRET=""
if [[ -f "$ENV_FILE" ]]; then
  read -r EXISTING_GROWW_KEY EXISTING_GROWW_SECRET < <(python3 - <<'PY'
import os
from pathlib import Path

env_path = Path(os.environ["ENV_FILE"])
key = ""
secret = ""
for line in env_path.read_text().splitlines():
    if line.startswith("GROWW_API_KEY="):
        key = line.split("=", 1)[1].strip().strip('"').strip("'")
    elif line.startswith("GROWW_API_SECRET="):
        secret = line.split("=", 1)[1].strip().strip('"').strip("'")
print(f"{key} {secret}")
PY
)
fi

GROWW_KEY_INPUT="${1:-${GROWW_API_KEY:-${EXISTING_GROWW_KEY:-}}}"
GROWW_SECRET_INPUT="${2:-${GROWW_API_SECRET:-${EXISTING_GROWW_SECRET:-}}}"
if [[ -z "$GROWW_KEY_INPUT" ]]; then
  echo "==> Enter GROWW_API_KEY (input hidden):"
  read -r -s GROWW_KEY_INPUT
  echo
fi
if [[ -z "$GROWW_SECRET_INPUT" ]]; then
  echo "==> Enter GROWW_API_SECRET (input hidden):"
  read -r -s GROWW_SECRET_INPUT
  echo
fi

export GROWW_KEY_INPUT
export GROWW_SECRET_INPUT
export ENV_FILE
python3 - <<'PY'
from pathlib import Path
import os

env_path = Path(os.environ["ENV_FILE"])
key = os.environ.get("GROWW_KEY_INPUT") or ""
secret = os.environ.get("GROWW_SECRET_INPUT") or ""

lines = env_path.read_text().splitlines()
updated_key = False
updated_secret = False
out = []
for line in lines:
    if line.startswith("GROWW_API_KEY="):
        out.append(f"GROWW_API_KEY={key}")
        updated_key = True
    elif line.startswith("GROWW_API_SECRET="):
        out.append(f"GROWW_API_SECRET={secret}")
        updated_secret = True
    else:
        out.append(line)
if not updated_key:
    out.append(f"GROWW_API_KEY={key}")
if not updated_secret:
    out.append(f"GROWW_API_SECRET={secret}")

env_path.write_text("\n".join(out) + "\n")
PY

export GROWW_API_KEY="$GROWW_KEY_INPUT"
export GROWW_API_SECRET="$GROWW_SECRET_INPUT"

echo "==> Building and deploying (no cache)"
docker compose build --no-cache
docker compose up -d

echo "==> Done"

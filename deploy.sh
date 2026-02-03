#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-$(pwd)}"
BRANCH="${BRANCH:-main}"
ENV_FILE="$REPO_DIR/.env"
ENV_EXAMPLE="$REPO_DIR/.env.example"

usage() {
  cat <<USAGE
Usage:
  ./deploy.sh [GROWW_API_KEY]

Options via env:
  REPO_DIR=/path/to/repo
  BRANCH=main

Behavior:
  - pulls latest from origin/main
  - copies .env.example -> .env if missing
  - prompts for GROWW_API_KEY if not provided
  - builds with --no-cache and restarts docker compose
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

cd "$REPO_DIR"

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

GROWW_KEY_INPUT="${1:-${GROWW_API_KEY:-}}"
if [[ -z "$GROWW_KEY_INPUT" ]]; then
  echo "==> Enter GROWW_API_KEY (input hidden):"
  read -r -s GROWW_KEY_INPUT
  echo
fi

export GROWW_KEY_INPUT
export ENV_FILE
python3 - <<'PY'
from pathlib import Path
import os

env_path = Path(os.environ["ENV_FILE"])
key = os.environ.get("GROWW_KEY_INPUT") or ""

lines = env_path.read_text().splitlines()
updated = False
out = []
for line in lines:
    if line.startswith("GROWW_API_KEY="):
        out.append(f"GROWW_API_KEY={key}")
        updated = True
    else:
        out.append(line)
if not updated:
    out.append(f"GROWW_API_KEY={key}")

env_path.write_text("\n".join(out) + "\n")
PY

export GROWW_API_KEY="$GROWW_KEY_INPUT"

echo "==> Building and deploying (no cache)"
docker compose build --no-cache
docker compose up -d

echo "==> Done"

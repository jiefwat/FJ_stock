#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
DEPLOY_HOST=${DEPLOY_HOST:?set DEPLOY_HOST to the public server host}
DEPLOY_USER=${DEPLOY_USER:-admin}
SSH_KEY=${SSH_KEY:-}
REMOTE="${DEPLOY_USER}@${DEPLOY_HOST}"
SSH=(ssh -o BatchMode=yes)
RSYNC=(rsync -a --delete)

if [[ -n "$SSH_KEY" ]]; then
  SSH+=(-i "$SSH_KEY")
  RSYNC+=(-e "ssh -i $SSH_KEY -o BatchMode=yes")
else
  RSYNC+=(-e "ssh -o BatchMode=yes")
fi

RELEASE_ID="$(date +%Y%m%d-%H%M%S)-$(git -C "$ROOT" rev-parse --short HEAD)"
RELEASE_DIR="/opt/aster-market/releases/$RELEASE_ID"
ARCHIVE="$ROOT/.run/$RELEASE_ID.tar.gz"

mkdir -p "$ROOT/.run"
pnpm --dir "$ROOT/frontend" build

COPYFILE_DISABLE=1 tar \
  --format ustar \
  --exclude='.git' \
  --exclude='.run' \
  --exclude='.superpowers' \
  --exclude='backend/.venv' \
  --exclude='**/.mypy_cache' \
  --exclude='**/.pytest_cache' \
  --exclude='**/.ruff_cache' \
  --exclude='**/__pycache__' \
  --exclude='frontend/node_modules' \
  --exclude='data' \
  --exclude='*.tsbuildinfo' \
  -czf "$ARCHIVE" \
  -C "$ROOT" .

"${SSH[@]}" "$REMOTE" "mkdir -p /opt/aster-market/releases /opt/aster-market/data /tmp/aster-market-deploy"
"${RSYNC[@]}" "$ARCHIVE" "$REMOTE:/tmp/aster-market-deploy/$RELEASE_ID.tar.gz"
"${SSH[@]}" "$REMOTE" "rm -rf '$RELEASE_DIR.tmp' && mkdir -p '$RELEASE_DIR.tmp'"
"${SSH[@]}" "$REMOTE" "tar -xzf '/tmp/aster-market-deploy/$RELEASE_ID.tar.gz' -C '$RELEASE_DIR.tmp'"
"${SSH[@]}" "$REMOTE" "python3 -m venv '$RELEASE_DIR.tmp/.venv'"
"${SSH[@]}" "$REMOTE" "'$RELEASE_DIR.tmp/.venv/bin/python' -m pip install --upgrade pip"
"${SSH[@]}" "$REMOTE" "'$RELEASE_DIR.tmp/.venv/bin/python' -m pip install 'fastapi>=0.115,<1' 'httpx>=0.27,<1' 'pydantic-settings>=2.6,<3' 'uvicorn[standard]>=0.32,<1'"
"${SSH[@]}" "$REMOTE" "rm -rf '$RELEASE_DIR' && mv '$RELEASE_DIR.tmp' '$RELEASE_DIR'"
"${SSH[@]}" "$REMOTE" "ln -sfn \"$RELEASE_DIR\" /opt/aster-market/current"
"${SSH[@]}" "$REMOTE" "sudo cp '$RELEASE_DIR/deploy/stock-ts.service' /etc/systemd/system/stock-ts.service"
"${SSH[@]}" "$REMOTE" "sudo systemctl daemon-reload"
"${SSH[@]}" "$REMOTE" "sudo systemctl restart stock-ts.service"
"${SSH[@]}" "$REMOTE" "curl -fsS http://127.0.0.1:8501/healthz"

echo "Deployed $RELEASE_ID to $DEPLOY_HOST"

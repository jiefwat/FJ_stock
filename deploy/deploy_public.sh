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

GIT_SUFFIX=""
if [[ -n "$(git -C "$ROOT" status --porcelain)" ]]; then
  GIT_SUFFIX="-dirty"
fi
RELEASE_ID="$(date +%Y%m%d-%H%M%S)-$(git -C "$ROOT" rev-parse --short HEAD)$GIT_SUFFIX"
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
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='data' \
  --exclude='*.tsbuildinfo' \
  -czf "$ARCHIVE" \
  -C "$ROOT" .

"${SSH[@]}" "$REMOTE" "mkdir -p /opt/aster-market/releases /opt/aster-market/data /tmp/aster-market-deploy"
if [[ -f "$ROOT/.env" ]]; then
  SAFE_ENV="$ROOT/.run/$RELEASE_ID.env"
  python3 - "$ROOT/.env" "$SAFE_ENV" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
target = Path(sys.argv[2])
lines = source.read_text(encoding="utf-8").splitlines()
safe_lines = [
    line
    for line in lines
    if not line.strip().startswith("MARKETDESK_DATA_DIR=")
]
target.write_text("\n".join(safe_lines) + ("\n" if safe_lines else ""), encoding="utf-8")
PY
  "${RSYNC[@]}" "$SAFE_ENV" "$REMOTE:/tmp/aster-market-deploy/$RELEASE_ID.env"
  "${SSH[@]}" "$REMOTE" "python3 - '/opt/aster-market/.env' '/tmp/aster-market-deploy/$RELEASE_ID.env' <<'PY'
from pathlib import Path
import sys

target = Path(sys.argv[1])
incoming = Path(sys.argv[2])

def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip()
    return values

merged = read_env(target)
merged.update(read_env(incoming))
order = list(read_env(target)) + [key for key in read_env(incoming) if key not in read_env(target)]
if not order:
    order = sorted(merged)
target.write_text('\\n'.join(f'{key}={merged[key]}' for key in order if key in merged) + '\\n', encoding='utf-8')
PY"
  "${SSH[@]}" "$REMOTE" "chmod 600 /opt/aster-market/.env"
fi
"${RSYNC[@]}" "$ARCHIVE" "$REMOTE:/tmp/aster-market-deploy/$RELEASE_ID.tar.gz"
"${SSH[@]}" "$REMOTE" "rm -rf '$RELEASE_DIR.tmp' && mkdir -p '$RELEASE_DIR.tmp'"
"${SSH[@]}" "$REMOTE" "tar -xzf '/tmp/aster-market-deploy/$RELEASE_ID.tar.gz' -C '$RELEASE_DIR.tmp'"
# Keep recent hashed chunks available so tabs opened before a release can still lazy-load routes.
"${SSH[@]}" "$REMOTE" "for assets in /opt/aster-market/releases/*/frontend/dist/assets; do if [[ \"\$assets\" != '$RELEASE_DIR.tmp/frontend/dist/assets' && -d \"\$assets\" ]]; then cp -a --update=none \"\$assets/.\" '$RELEASE_DIR.tmp/frontend/dist/assets/'; fi; done; find '$RELEASE_DIR.tmp/frontend/dist/assets' -type f -mtime +14 -delete"
"${SSH[@]}" "$REMOTE" "python3 -m venv '$RELEASE_DIR.tmp/.venv'"
"${SSH[@]}" "$REMOTE" "'$RELEASE_DIR.tmp/.venv/bin/python' -m pip install --upgrade pip"
"${SSH[@]}" "$REMOTE" "'$RELEASE_DIR.tmp/.venv/bin/python' -m pip install 'fastapi>=0.115,<1' 'httpx>=0.27,<1' 'pydantic-settings>=2.6,<3' 'uvicorn[standard]>=0.32,<1'"
"${SSH[@]}" "$REMOTE" "rm -rf '$RELEASE_DIR' && mv '$RELEASE_DIR.tmp' '$RELEASE_DIR'"
"${SSH[@]}" "$REMOTE" "ln -sfn \"$RELEASE_DIR\" /opt/aster-market/current"
"${SSH[@]}" "$REMOTE" "sudo cp '$RELEASE_DIR/deploy/stock-ts.service' /etc/systemd/system/stock-ts.service"
"${SSH[@]}" "$REMOTE" "sudo cp '$RELEASE_DIR/deploy/stock-ts-morning-email.service' /etc/systemd/system/stock-ts-morning-email.service"
"${SSH[@]}" "$REMOTE" "sudo cp '$RELEASE_DIR/deploy/stock-ts-morning-email.timer' /etc/systemd/system/stock-ts-morning-email.timer"
"${SSH[@]}" "$REMOTE" "sudo systemctl daemon-reload"
"${SSH[@]}" "$REMOTE" "sudo systemctl restart stock-ts.service"
"${SSH[@]}" "$REMOTE" "sudo systemctl enable --now stock-ts-morning-email.timer"
"${SSH[@]}" "$REMOTE" "curl -fsS http://127.0.0.1:8501/healthz"

echo "Deployed $RELEASE_ID to $DEPLOY_HOST"

#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
uv sync --project "$ROOT/backend"
pnpm --dir "$ROOT/frontend" install --frozen-lockfile
echo "Setup complete. Run: make start"

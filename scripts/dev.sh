#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cleanup() { jobs -pr | xargs -r kill 2>/dev/null || true; }
trap cleanup EXIT INT TERM
uv run --project "$ROOT/backend" uvicorn marketdesk.api:app --host 127.0.0.1 --port 8000 --reload &
pnpm --dir "$ROOT/frontend" dev &
wait

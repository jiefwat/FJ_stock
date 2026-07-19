#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
echo "[1/7] Backend lint"
cd "$ROOT/backend" && uv run ruff check src tests
echo "[2/7] Backend types"
uv run mypy src
echo "[3/7] Backend tests"
uv run pytest -q
echo "[4/7] Frontend types"
cd "$ROOT/frontend" && pnpm typecheck
echo "[5/7] Frontend tests"
pnpm test --run
echo "[6/7] Frontend production build"
pnpm build
echo "[7/7] Live data quality"
cd "$ROOT" && uv run --project backend python scripts/check_live_data.py
echo "All verification gates passed."

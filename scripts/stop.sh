#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PID_FILE="$ROOT/.run/marketdesk.pid"
if [[ ! -f "$PID_FILE" ]]; then echo "Market Desk is not running."; exit 0; fi
PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then kill "$PID"; fi
rm -f "$PID_FILE" "$ROOT/.run/marketdesk.port"
echo "Market Desk stopped."

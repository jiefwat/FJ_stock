#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PREFERRED_PORT=${PORT:-8765}
RUN_DIR="$ROOT/.run"
PID_FILE="$RUN_DIR/marketdesk.pid"
LOG_FILE="$RUN_DIR/marketdesk.log"
PORT_FILE="$RUN_DIR/marketdesk.port"
mkdir -p "$RUN_DIR" "$ROOT/data"

if [[ -f "$PID_FILE" ]]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    kill "$OLD_PID"
    for _ in {1..20}; do kill -0 "$OLD_PID" 2>/dev/null || break; sleep 0.1; done
  fi
fi

PORT=$(python3 - "$PREFERRED_PORT" <<'PY'
import socket
import sys

preferred = int(sys.argv[1])
for port in range(preferred, preferred + 30):
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            continue
        print(port)
        break
else:
    raise SystemExit("no free local port found")
PY
)

pnpm --dir "$ROOT/frontend" build >/dev/null
cd "$ROOT"
UVICORN_BIN="$ROOT/backend/.venv/bin/uvicorn"
if [[ ! -x "$UVICORN_BIN" ]]; then
  uv run --project backend python -c "import uvicorn" >/dev/null
  UVICORN_BIN="$ROOT/backend/.venv/bin/uvicorn"
fi
nohup "$UVICORN_BIN" marketdesk.api:app --host 127.0.0.1 --port "$PORT" >"$LOG_FILE" 2>&1 &
PID=$!
echo "$PID" > "$PID_FILE"
echo "$PORT" > "$PORT_FILE"

for _ in {1..60}; do
  if curl -fsS "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then
    echo "Market Desk is running: http://127.0.0.1:$PORT"
    echo "Log: $LOG_FILE"
    exit 0
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    tail -40 "$LOG_FILE" >&2
    exit 1
  fi
  sleep 0.25
done
echo "Startup timed out. See $LOG_FILE" >&2
exit 1

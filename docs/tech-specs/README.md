# Technical Rules

- Python 3.11+ with strict Pydantic contracts, Ruff, mypy, and pytest.
- React and TypeScript with Vitest and a production Vite build.
- Every new behavior starts with a failing test.
- Secrets come only from environment variables.
- Market timestamps, coverage, source, and freshness stay visible through every layer.
- Public browser routes are a desktop workbench only: the HTML head omits
  device-scaling metadata, and the UI has no drawer, bottom bar, or
  narrow-screen CSS.

## Runtime Contract

- Backend package: `marketdesk`
- Public app: `marketdesk.api:app`
- API prefix: `/api/v1/*`
- Local default port: `8765`
- Production proxy port: `8501`
- Persistent data directory: `MARKETDESK_DATA_DIR`

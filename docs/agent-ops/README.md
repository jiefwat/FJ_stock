# Agent Operations

Default read order: `AGENTS.md` -> `docs/superpowers/README.md` -> active requirement.
Do not scan historical requirements by default.

## Local

```bash
make setup
make start
make stop
```

`make start` builds the React frontend, starts FastAPI on `127.0.0.1`, and writes
the selected port to `.run/marketdesk.port`.

## Verify

```bash
make verify
```

The gate runs backend lint, backend mypy, backend tests, frontend typecheck,
frontend tests, frontend production build, and live public-data quality checks.

## Public Deploy

Production keeps the existing public proxy port: the app binds
`127.0.0.1:8501` through `stock-ts.service`.

```bash
DEPLOY_HOST=<public-host> \
SSH_KEY=~/.ssh/stockts_aliyun_deploy \
deploy/deploy_public.sh
```

The script builds frontend assets locally, uploads a release archive, creates a
remote Python venv, installs backend runtime dependencies, switches
`/opt/aster-market/current` atomically, and restarts only `stock-ts.service`.
Runtime SQLite data stays under `/opt/aster-market/data`.

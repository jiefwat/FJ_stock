.PHONY: setup dev start stop test lint verify

setup:
	./scripts/setup.sh

dev:
	./scripts/dev.sh

start:
	./scripts/start.sh

stop:
	./scripts/stop.sh

test:
	cd backend && uv run pytest -q
	cd frontend && pnpm test --run

lint:
	cd backend && uv run ruff check src tests && uv run mypy src
	cd frontend && pnpm typecheck

verify:
	./scripts/verify.sh

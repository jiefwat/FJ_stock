# Architecture

The React frontend calls only the local FastAPI API. FastAPI orchestrates no-key public providers, normalization, deterministic analysis, SQLite snapshots, and local watchlist state. Provider failures must return stale cached data or an explicit unavailable state; they must never silently become zeros.

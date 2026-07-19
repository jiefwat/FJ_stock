# Agent Guide

Read `docs/superpowers/README.md`, then the active requirement listed there. Keep provider access behind `backend/src/marketdesk/providers/`, deterministic analysis under `analysis/`, and browser code dependent only on `/api/v1/*`.

Required before completion: `make verify`. Never commit `.env`, runtime databases, provider payload caches, or generated frontend artifacts.

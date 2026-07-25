# Application Authentication Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent unauthenticated visitors from seeing or requesting any Market Desk business content while preserving the existing authenticated application layout.

**Architecture:** Add one backend middleware for the entire `/api/v1/*` boundary and split the frontend root into a session gate, standalone authentication page, and authenticated shell. The shell is mounted only after `/auth/me` validates the stored token.

**Tech Stack:** FastAPI, Starlette middleware, React 19, TanStack Query, TypeScript, Vitest, Testing Library, CSS.

---

## File Map

- `backend/src/marketdesk/api.py`: application-wide API authentication middleware.
- `backend/tests/test_api.py`: anonymous and authenticated route-boundary regressions.
- `frontend/src/app/App.tsx`: root session gate, standalone auth page, and authenticated account menu.
- `frontend/src/app/App.test.tsx`: authentication-page, session restore, login, and request-boundary regressions.
- `frontend/src/app/styles.css`: standalone authentication page layout.
- `docs/superpowers/market-intelligence-workbench/TODO.md`: accepted application-auth boundary.
- `docs/superpowers/market-intelligence-workbench/test.md`: local and production evidence.

### Task 1: Protect Every Business API

- [ ] Add a failing backend test that expects HTTP 401 from representative market, stock, opportunity, refresh, data, and personal endpoints without a bearer token while registration and login remain callable.
- [ ] Run `cd backend && uv run pytest -q tests/test_api.py -k application_routes_require_authentication` and confirm the public market endpoint causes the expected failure.
- [ ] Add an `/api/v1/*` middleware that exempts only `OPTIONS`, registration, and login, validates bearer sessions, and returns a JSON HTTP 401 before endpoint execution.
- [ ] Run `cd backend && uv run pytest -q tests/test_api.py` and update only test setup that intentionally exercises authenticated business routes.

### Task 2: Mount the Application Only After Authentication

- [ ] Rewrite the App regression first: without a token, assert the standalone `登录 Market Desk` form is visible, `主导航` and `市场状态` are absent, and no market API was requested.
- [ ] Run `cd frontend && pnpm test --run src/app/App.test.tsx` and confirm the current shell makes the test fail.
- [ ] Extract a root session gate in `App.tsx`. Render authentication during anonymous/invalid sessions and mount `Shell` only for a validated user. Keep authentication mutations at the gate and pass the user/logout callback into the existing account menu.
- [ ] Add valid-session and logout regressions. Verify business calls include the bearer token and logout immediately returns to the standalone authentication page.
- [ ] Run `cd frontend && pnpm test --run src/app/App.test.tsx` and then all frontend tests.

### Task 3: Finish, Verify, and Release

- [ ] Add responsive standalone-auth styles without changing authenticated business-page selectors or layout.
- [ ] Update the active TODO and test evidence, then run `git diff --check` and `make verify`.
- [ ] In a real browser, verify anonymous desktop and 390px pages show only authentication and make no business API request; verify a real login mounts the shell.
- [ ] Commit and push the implementation, deploy with `deploy/deploy_public.sh`, then repeat health, anonymous API, login, service, release-link, and persistent-data checks on production.

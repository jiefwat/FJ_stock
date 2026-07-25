# Application Authentication Gate Design

Date: 2026-07-25
Status: Approved under delegated product authority

## 1. Decision

Market Desk becomes a private application. An unauthenticated visitor may access only the static application entry point, health check, registration endpoint, and login endpoint. Market summaries, full-market quotes, events, opportunities, stock dossiers, data status, refresh, holdings, watchlists, preferences, and saved views all require a valid bearer token.

## 2. Frontend Boundary

The root application resolves the stored session before mounting business routes. With no token it renders a standalone authentication page containing the product identity, a login/register form, and a short privacy explanation. It must not render the sidebar, top bar, navigation, market data, or any feature page.

With a stored token, the root requests `/api/v1/auth/me`. A valid response mounts the existing shell without changing its business-page layout. An invalid or expired token is removed and returns the visitor to the authentication page. Login or registration stores the new token and mounts the shell. Logout clears the token and query cache before returning to the authentication page.

The standalone authentication page is responsive at 390px and 1440px. Authentication fields remain labelled, errors use `role=alert`, and the loading state does not expose application content.

## 3. Backend Boundary

A single HTTP middleware protects `/api/v1/*` before endpoint execution. The only anonymous API exceptions are:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`

`GET /healthz` and frontend assets remain public so the service and login page can load. CORS preflight requests remain available. Every other `/api/v1/*` request without a valid bearer token returns HTTP 401 and does not invoke providers or analysis services.

## 4. Data Flow

1. The browser loads static HTML and JavaScript.
2. The root reads the local access token.
3. No token: render only the authentication page and make no market request.
4. Token: call `/api/v1/auth/me`.
5. Valid session: mount the existing application shell and allow feature queries.
6. Invalid session or logout: clear local auth state and all cached query data, then render the authentication page.

## 5. Acceptance

- Anonymous `/api/v1/market`, `/today`, `/equities`, `/opportunities`, `/stocks/*`, `/search`, `/data-status`, `/refresh`, and all personal endpoints return HTTP 401.
- Registration and login remain anonymously callable.
- With no token, the page shows a standalone login/register form and no main navigation or market conclusion.
- With a valid token, the existing main shell renders and sends bearer-authenticated business requests.
- An invalid stored token returns to the authentication page without briefly rendering business content.
- Logout removes the shell and cached business data immediately.
- Desktop and 390px login pages have no horizontal overflow.
- `make verify` and a real-browser production smoke test pass.

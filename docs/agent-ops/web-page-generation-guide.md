# Web Page Generation Guide for Agents

Use this guide when an agent needs to create, redesign, or publish a web page for this project or for the `jiewat-kaka-fj.com` domain family.

## Default Context

- Brand: `Jiewat Kaka FJ`
- Primary domain: `jiewat-kaka-fj.com`
- Recommended project URL: `stock.jiewat-kaka-fj.com`
- Current app: `StockTS`, a Python web app for A-share research and review.
- Safety posture: public pages should default to read-only unless the owner explicitly asks for private/admin functionality.

## Recommended Site Structure

Use one domain with multiple clear entry points instead of buying a new domain for each project.

```text
jiewat-kaka-fj.com        -> home page / navigation hub
stock.jiewat-kaka-fj.com  -> StockTS web app
docs.jiewat-kaka-fj.com   -> documentation or tutorials
api.jiewat-kaka-fj.com    -> future API service, if needed
demo.jiewat-kaka-fj.com   -> experiments and demos
```

Prefer subdomains for independent apps. Prefer paths for sections inside the same app.

```text
Good independent apps:
stock.jiewat-kaka-fj.com
docs.jiewat-kaka-fj.com

Good same-app paths:
jiewat-kaka-fj.com/stock
jiewat-kaka-fj.com/reports
```

## Design Direction

Avoid generic SaaS templates. The page should feel like a focused research workstation, not a default landing page.

- Use a strong visual thesis in the hero: market desk, command console, research board, evidence timeline, or portfolio cockpit.
- Use the existing brand name `Jiewat Kaka FJ`, but keep the technical package name `stock_ts` unchanged.
- Prefer calm financial colors: ink blue, steel gray, warm paper, brass, restrained green/red for market state.
- Avoid purple-on-white default AI styling.
- Use purposeful typography. Do not default to Inter, Roboto, Arial, or system stacks unless preserving an existing design system.
- Make structure meaningful: modules, sessions, trade dates, evidence, watchlists, and risk states should drive layout labels.
- Use motion sparingly: one load/reveal sequence or one meaningful state transition is better than many small generic animations.
- Make mobile usable, not just smaller.

## Content Rules

Financial pages must be careful and specific.

- Always include a disclaimer: research only, not investment advice.
- Do not promise certain returns, tomorrow's gains, or risk-free trades.
- Use language like "observation score", "scenario", "trigger", "invalid line", and "risk boundary".
- Make data freshness visible: provider, trade date, source, and whether data is sample/fallback.
- Empty and error states must tell users exactly what to do next.

## Public Safety Rules

When publishing pages for other people to use:

- Do not expose `.env`, tokens, webhook URLs, email passwords, or private holdings.
- Default to `STOCK_TS_PUBLIC_READONLY=1`.
- Do not allow public users to edit holdings, save settings, or send notifications unless auth is added first.
- Keep the Python service bound to `127.0.0.1` behind Nginx when deploying on a server.
- Put HTTPS in front of any public page.
- If the server is in mainland China, confirm ICP filing requirements before public launch.

## StockTS Runtime

Local run:

```bash
PYTHONPATH=src python3 -m stock_ts.web
```

Public read-only run behind Nginx:

```bash
HOST=127.0.0.1 \
PORT=8501 \
STOCK_TS_PUBLIC_READONLY=1 \
PYTHONPATH=src \
python3 -m stock_ts.web
```

Personal writable run behind Nginx:

```bash
HOST=127.0.0.1 \
PORT=8501 \
STOCK_TS_PUBLIC_READONLY=0 \
PYTHONPATH=src \
python3 -m stock_ts.web
```

Use writable mode only for the owner-operated site, because holdings, settings, and notification test forms can write server-side state.

Docker run:

```bash
docker build -t jiewat-kaka-fj .
docker run --rm -p 8501:8501 jiewat-kaka-fj
```

## DNS Pattern

For `stock.jiewat-kaka-fj.com`, add this DNS record in Aliyun DNS:

```text
Type: A
Host: stock
Value: <server public IP>
TTL: default
```

For the root domain:

```text
Type: A
Host: @
Value: <server public IP>
TTL: default
```

For `www`:

```text
Type: CNAME
Host: www
Value: jiewat-kaka-fj.com
TTL: default
```

## Nginx Pattern

Use this for a StockTS subdomain:

```nginx
server {
    listen 80;
    server_name stock.jiewat-kaka-fj.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Then enable HTTPS with the server's certificate workflow, for example:

```bash
sudo certbot --nginx -d stock.jiewat-kaka-fj.com
```

## Agent Workflow

Before changing a page, an agent should:

1. Read `AGENTS.md`.
2. Read `docs/agent-ops/README.md`.
3. Read this file.
4. Inspect the current page implementation and tests.
5. Preserve existing project conventions unless the user asks for a redesign.
6. Add or update tests when changing behavior, routing, safety gates, or rendered copy.
7. Run relevant verification before claiming completion.

## Quality Checklist

Before handing off a generated page:

- The page has a clear single job.
- The visual direction is specific to the product, not generic.
- Desktop and mobile layouts both work.
- Keyboard focus states are visible.
- Reduced-motion users are respected if animation is added.
- Public mode cannot mutate private data.
- Secrets are never printed, embedded, or committed.
- The disclaimer is visible on financial research pages.
- The domain/subdomain choice is documented.
- Deployment variables are listed.
- Verification commands and results are reported.

## Copy-Paste Prompt for Another Agent

```text
You are working on a Jiewat Kaka FJ web page.

Read:
- AGENTS.md
- docs/agent-ops/README.md
- docs/agent-ops/web-page-generation-guide.md

Use jiewat-kaka-fj.com as the primary domain family. Prefer subdomains for independent apps, especially stock.jiewat-kaka-fj.com for StockTS.

For public pages, default to read-only behavior and do not expose secrets, webhook URLs, private holdings, or editable admin settings.

Design direction: distinctive research workstation, calm financial palette, meaningful data structure, strong but restrained visual identity. Avoid generic AI SaaS styling.

If changing StockTS, keep the Python package and command names as stock_ts / stock-ts. Keep financial disclaimers and data quality indicators visible.

Before completion, run relevant lint/tests or explain why they were not run.
```

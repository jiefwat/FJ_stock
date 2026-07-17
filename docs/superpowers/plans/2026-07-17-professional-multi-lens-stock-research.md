# Professional Multi-Lens Stock Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the four generic research methods with task-specific professional lenses and add a supplier-neutral, user-triggered deep stock research module backed by the existing official data capabilities.

**Architecture:** Add a deterministic research-method contract between normalized evidence and the product result, then reuse the existing safe external adapter for a focused stock-deep-research service. Keep local analysis primary, expose no provider metadata, reject incompatible snapshots, and render the new module inside the native stock workspace.

**Tech Stack:** Python 3.11+, dataclasses, stdlib HTTP server, pytest, server-rendered HTML, vanilla JavaScript and CSS.

---

### Task 1: Professional research method contract

**Files:**
- Create: `src/stock_ts/research_method.py`
- Create: `tests/test_research_method.py`
- Modify: `src/stock_ts/research_engine.py`
- Modify: `src/stock_ts/research_fallback.py`

- [ ] **Step 1: Write failing contract tests**

Add tests proving that market, portfolio, stock and opportunity expose different dimension keys and comparison bases; missing dimensions return `unknown` without a score; stock includes support, counter-evidence, expectation gap and invalidation; opportunity requires theme, company, price and risk gates.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
PYTHONPATH=src python -m pytest -q tests/test_research_method.py
```

Expected: import or assertion failures because the method contract does not exist.

- [ ] **Step 3: Implement the method contract**

Create immutable `ResearchMethodDimension` and `ResearchMethod` models, `RESEARCH_METHODS`, `method_for(module)`, and `build_method_section(module, ready_keys, missing_keys)`. Dimension output must use `ready`, `partial`, or `unknown`; `unknown` emits `score=None` and a recovery instruction.

- [ ] **Step 4: Attach the method section**

Add the method section to local and external `ResearchWorkspaceResult` objects without changing supplier-neutral serialization. Keep each module's section order distinct.

- [ ] **Step 5: Run focused tests and verify GREEN**

```bash
PYTHONPATH=src python -m pytest -q \
  tests/test_research_method.py tests/test_research_fallback.py tests/test_research_engine.py
```

### Task 2: Expand evidence dimensions and professional queries

**Files:**
- Modify: `src/stock_ts/iwencai.py`
- Modify: `src/stock_ts/research_evidence.py`
- Modify: `src/stock_ts/research_engine.py`
- Modify: `tests/test_iwencai.py`
- Modify: `tests/test_research_evidence.py`
- Modify: `tests/test_research_engine.py`

- [ ] **Step 1: Write failing capability tests**

Require `basicinfo`, `management`, and `news` in the stock bundle. Require normalization for company identity, shareholder-count change, controlling shareholder, pledge ratio and dated news. Require prompts to ask for multi-period change, peer comparison and expectation revisions instead of only current values.

- [ ] **Step 2: Verify RED**

```bash
PYTHONPATH=src python -m pytest -q \
  tests/test_iwencai.py tests/test_research_evidence.py tests/test_research_engine.py
```

- [ ] **Step 3: Implement official capability mapping and schemas**

Add `hithink-basicinfo-query`; extend stock capabilities to eleven official fact domains; add `CapabilitySchema` entries for basic information and governance; keep unknown fields excluded from the public contract.

- [ ] **Step 4: Upgrade prompts**

Finance asks for three-year/four-quarter trend and cash-profit matching; industry asks for peer percentile; consensus asks for three-month estimate revisions and dispersion; market asks for 5/20/60-day structure; management asks for shareholder-count, pledge and controller changes; events/news/report queries request dates and material changes.

- [ ] **Step 5: Verify GREEN**

Run the same three test files and confirm no provider brand or internal metadata enters public JSON.

### Task 3: Stock deep research service and API

**Files:**
- Create: `src/stock_ts/stock_deep_research.py`
- Create: `tests/test_stock_deep_research.py`
- Modify: `src/stock_ts/web.py`
- Modify: `tests/test_web_research_workspace_api.py`
- Modify: `tests/test_web_auth.py`

- [ ] **Step 1: Write failing service tests**

Define the wished-for API:

```python
result = StockDeepResearchService(client_factory=factory).research(
    code="600519",
    name="贵州茅台",
    focus="all",
    question="",
    refresh=False,
)
```

Assert six product groups, partial success, five-minute cache, custom-question single-capability routing, no holdings context, no provider metadata, and product-language errors.

- [ ] **Step 2: Verify RED**

```bash
PYTHONPATH=src python -m pytest -q tests/test_stock_deep_research.py
```

- [ ] **Step 3: Implement the service**

Add `DeepResearchGroup`, `StockDeepResearchResult`, focus allowlist, grouping rules, request construction and TTL cache. Reuse `IwencaiSkillClient`, `SKILLS` and normalized evidence; do not accept ability IDs or gateway URLs from callers.

- [ ] **Step 4: Write failing HTTP tests**

Require authenticated `POST /api/research/stock/deep`, JSON content type, 16 KiB request cap, rate limiting, supplier-neutral success payload and sanitized failure payload. Anonymous requests return 401.

- [ ] **Step 5: Implement the endpoint and verify GREEN**

Run:

```bash
PYTHONPATH=src python -m pytest -q \
  tests/test_stock_deep_research.py \
  tests/test_web_research_workspace_api.py \
  tests/test_web_auth.py
```

### Task 4: Native stock deep-research interaction

**Files:**
- Modify: `src/stock_ts/webapp/engine_workspace.py`
- Modify: `src/stock_ts/webapp/styles.py`
- Modify: `tests/test_web_native_research_workspaces.py`
- Modify: `tests/test_web_design_guide_shell.py`

- [ ] **Step 1: Write failing HTML/JS/CSS tests**

Require a compact `data-stock-deep-research` module after the stock switcher, six understandable group labels, `运行深度研究`, focus chips, a custom question form, loading/partial/cached/error states, folded evidence, no automatic request on bootstrap, no provider terms, keyboard focus and desktop-safe layout.

- [ ] **Step 2: Verify RED**

```bash
PYTHONPATH=src python -m pytest -q \
  tests/test_web_native_research_workspaces.py \
  tests/test_web_design_guide_shell.py
```

- [ ] **Step 3: Implement markup and interaction**

Render the idle module in the stock workspace. On explicit click, call `/api/research/stock/deep`, update six status cells, show added facts/support/conflicts/gaps, and keep complete evidence folded. Focus chips call one allowed focus; custom questions retain the current stock only.

- [ ] **Step 4: Implement restrained desktop styling**

Use the existing ink/copper research-terminal palette, 12px minimum utility text, a six-column status rail at 1440/1680, two columns below 1100px, visible focus and reduced motion. Do not introduce another hero card or duplicate the primary verdict.

- [ ] **Step 5: Verify GREEN**

Run the two UI contract files and inspect rendered HTML for supplier neutrality.

### Task 5: Snapshot compatibility, deep links and error language

**Files:**
- Modify: `src/stock_ts/research_snapshots.py`
- Modify: `src/stock_ts/web.py`
- Modify: `src/stock_ts/webapp/engine_workspace.py`
- Modify: `tests/test_research_snapshots.py`
- Modify: `tests/test_web_research_workspace_api.py`
- Modify: `tests/test_web_native_research_workspaces.py`

- [ ] **Step 1: Write failing regression tests**

Require `research_contract_version` on new snapshots; reject old-version snapshots as current; preserve query strings and `#stock`/`#opportunity` after canonical navigation; map missing-stock and JSON errors to product language; never expose filesystem paths or raw exceptions in the new module.

- [ ] **Step 2: Verify RED**

Run the three regression files and confirm failures match the observed browser defects.

- [ ] **Step 3: Implement version and routing gates**

Add one contract version constant used by save/load and workspace validation. Old snapshots remain available only through stale/history delivery. Preserve the requested module across redirects and bootstrap from stock/theme query parameters when a fragment is unavailable.

- [ ] **Step 4: Sanitize errors**

Convert known `ValueError` and upstream failures to stable product error codes and recovery copy before rendering.

- [ ] **Step 5: Verify GREEN**

Run snapshot, API and native-workspace tests plus `git diff --check`.

### Task 6: Verification and deployment

**Files:**
- Modify: this plan only for final delivery evidence.

- [ ] **Step 1: Run lint and professional gate**

```bash
make lint
PYTHONPATH=src python -m pytest -q \
  tests/test_research_method.py \
  tests/test_iwencai.py \
  tests/test_research_evidence.py \
  tests/test_research_engine.py \
  tests/test_research_fallback.py \
  tests/test_stock_deep_research.py \
  tests/test_research_snapshots.py \
  tests/test_web_research_workspace_api.py \
  tests/test_web_native_research_workspaces.py \
  tests/test_web_design_guide_shell.py \
  tests/test_web_auth.py
```

- [ ] **Step 2: Run repository-wide tests and report the exact baseline**

```bash
PATH=/Users/fangjie/Documents/StockTs/.venv/bin:$PATH \
PYTEST_ADDOPTS='-q --tb=short' make test
```

Do not claim full green if legacy/native or missing-fixture failures remain.

- [ ] **Step 3: Browser acceptance**

At 1440x900 and 1680x1050 verify login, market, portfolio, stock, opportunity, deep-research idle/run/partial/error, theme-to-stock links, refresh persistence, no horizontal overflow and no console errors.

- [ ] **Step 4: Commit, push and deploy**

Push `codex/research-data-depth-v2`; deploy via Git bundle to `/opt/stock-ts`; restart only `stock-ts.service`; do not run the complete market-data pipeline.

- [ ] **Step 5: Refresh research snapshots and verify production**

Run only the research snapshot job after the data pipeline is confirmed `ok`, then verify the new contract version, supplier-neutral deep endpoint, service/timers, `/healthz`, login redirect and current market/opportunity semantics.

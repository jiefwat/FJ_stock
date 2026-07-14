# StockTS Native Research Workspaces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the four local-analysis workspaces with lazy, supplier-neutral research workspaces powered only by fixed server-side iWencai capability bundles.

**Architecture:** A new `ResearchWorkspaceService` owns bundle selection, sanitized query construction, concurrent calls, fact normalization, honest partial-failure semantics, and short-lived caching. The root web page becomes a lightweight research shell; browser JavaScript calls one supplier-neutral endpoint and renders a shared result schema without exposing provider metadata.

**Tech Stack:** Python 3.11 stdlib, dataclasses, `ThreadPoolExecutor`, existing iWencai HTTP adapter, stdlib HTML/JavaScript renderer, pytest, BeautifulSoup.

---

### Task 1: Define The Research Engine Contract

**Files:**
- Create: `tests/test_research_engine.py`
- Create: `src/stock_ts/research_engine.py`

- [ ] **Step 1: Write failing bundle and privacy tests**

```python
def test_each_workspace_has_a_fixed_capability_bundle() -> None:
    assert workspace_capabilities("market") == ("index", "macro", "sector_selector", "news")
    assert workspace_capabilities("portfolio") == ("event", "announcement", "consensus", "market")
    assert workspace_capabilities("stock") == ("finance", "business", "consensus", "event")
    assert workspace_capabilities("opportunity") == ("sector_selector", "astock_selector", "event", "news")

def test_portfolio_queries_never_include_private_position_fields() -> None:
    context = ResearchContext(
        holdings=(ResearchTarget(code="600519", name="贵州茅台"),),
    )
    queries = build_workspace_queries("portfolio", context)
    text = " ".join(item.query for item in queries)
    assert "1000" not in text
    assert "成本" not in text
    assert "权重" not in text
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_research_engine.py -q
```

Expected: import failure because `stock_ts.research_engine` does not exist.

- [ ] **Step 3: Implement the domain types and fixed bundles**

Define immutable `ResearchTarget`, `ResearchContext`, `CapabilityRequest`, `ResearchFinding`, `ResearchDetail`, and `ResearchWorkspaceResult` dataclasses. Add an allowlisted `WORKSPACE_CAPABILITIES` mapping and reject unknown modules.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run the same pytest command. Expected: all contract and privacy tests pass.

### Task 2: Execute, Normalize, And Cache Capability Bundles

**Files:**
- Modify: `tests/test_research_engine.py`
- Modify: `src/stock_ts/research_engine.py`

- [ ] **Step 1: Write failing complete, partial, and cache tests**

```python
def test_service_returns_supplier_neutral_partial_result() -> None:
    client = FakeClient(results={"finance": {"datas": [{"收入": "增长"}]}}, failures={"event"})
    result = ResearchWorkspaceService(client_factory=lambda: client).research(
        "stock", ResearchContext(code="600519", name="贵州茅台")
    )
    payload = result.to_public_dict()
    assert payload["status"] == "partial"
    assert payload["findings"]
    assert "event" not in json.dumps(payload)
    assert "问财" not in json.dumps(payload, ensure_ascii=False)

def test_service_reuses_unexpired_result() -> None:
    service = ResearchWorkspaceService(client_factory=lambda: FakeClient())
    first = service.research("market", ResearchContext())
    second = service.research("market", ResearchContext())
    assert second is first
```

- [ ] **Step 2: Run the tests and verify RED**

Expected: service and public serialization are missing.

- [ ] **Step 3: Implement concurrent execution and normalization**

Run a maximum of four requests concurrently. Convert at most three rows per capability and at most four fields per row to product findings. Return `complete`, `partial`, `empty`, or `unavailable`; never derive a strong buy/sell claim from row count. Cache complete and partial results for 300 seconds using a sanitized context key.

- [ ] **Step 4: Run tests and verify GREEN**

Run `tests/test_research_engine.py`. Expected: complete, partial, empty, privacy, cache, and supplier-neutral serialization tests pass.

### Task 3: Add The Supplier-Neutral Workspace Endpoint

**Files:**
- Create: `tests/test_web_research_workspace_api.py`
- Modify: `src/stock_ts/web.py`

- [ ] **Step 1: Write failing payload and endpoint tests**

```python
def test_parse_workspace_payload_rejects_provider_control_fields() -> None:
    payload = json.dumps({"module": "stock", "skill": "anything", "context": {"code": "600519"}}).encode()
    parsed = _parse_research_workspace_payload(payload)
    assert set(parsed) == {"module", "context", "refresh"}

def test_public_response_has_no_provider_metadata() -> None:
    payload = _request_workspace("stock", {"code": "600519", "name": "贵州茅台"})
    serialized = json.dumps(payload, ensure_ascii=False)
    for forbidden in ("问财", "iWencai", "同花顺", "skill_id", "trace_id", "openapi"):
        assert forbidden not in serialized
```

- [ ] **Step 2: Run the tests and verify RED**

Expected: parser and `/api/research/workspace` do not exist.

- [ ] **Step 3: Implement parsing and handler routing**

Accept only `module`, bounded supplier-neutral `context`, and `refresh`. Reuse the current login gate, per-user/IP limiter, 16 KiB request cap, JSON content-type check, and safe JSON headers. Convert configuration and gateway errors to generic product messages without provider names.

- [ ] **Step 4: Run API and legacy security tests**

```bash
PYTHONPATH=src .venv/bin/python -m pytest \
  tests/test_web_research_workspace_api.py \
  tests/test_web_iwencai_research.py tests/test_iwencai.py -q
```

Expected: new endpoint tests and existing credential/timeout/size protections pass.

### Task 4: Replace The Root Page With Four Lazy Workspaces

**Files:**
- Create: `tests/test_web_native_research_workspaces.py`
- Create: `src/stock_ts/webapp/engine_workspace.py`
- Modify: `src/stock_ts/webapp/__init__.py`
- Modify: `src/stock_ts/webapp/shell.py`
- Modify: `src/stock_ts/webapp/styles.py`
- Modify: `src/stock_ts/web.py`

- [ ] **Step 1: Write failing page contract tests**

```python
def test_root_page_renders_four_lazy_workspaces_without_local_provider_calls() -> None:
    provider = ExplodingProvider()
    html = render_page(provider=provider, stock_code="600519")
    assert html.count('data-engine-workspace="') == 4
    assert "当前判断" in html

def test_visible_page_copy_is_supplier_neutral() -> None:
    html = render_page(stock_code="600519")
    for forbidden in ("问财", "iWencai", "同花顺", "Skill", "外部证据"):
        assert forbidden not in html
```

- [ ] **Step 2: Run the tests and verify RED**

Expected: the old root page invokes its local provider and renders the previous analysis workspaces.

- [ ] **Step 3: Implement the shared workspace renderer**

Render the module title, generic service status, context controls, judgment band, verdict/action/risk slots, three findings, one closed detail drawer, and retry action. Use `data-*` hooks rather than supplier names.

- [ ] **Step 4: Implement lazy client behavior**

On initial route activation, call `/api/research/workspace` once for that module. Cache the browser result per context, support explicit refresh, render with `textContent`, and keep failure localized. Do not render chats, provider labels, ability names, trace ids, or raw HTML from responses.

- [ ] **Step 5: Bypass the old four-module analysis pipeline**

Make `render_page` build the research shell from the selected stock and privacy-safe holdings targets before creating any market provider or running `build_daily_report`. Keep authentication and account controls available; old analysis functions remain in the branch only as unused rollback code.

- [ ] **Step 6: Run focused page tests and verify GREEN**

```bash
PYTHONPATH=src .venv/bin/python -m pytest \
  tests/test_web_native_research_workspaces.py \
  tests/test_web_research_workspace_api.py tests/test_web_auth.py -q
```

Expected: the root is lazy, supplier-neutral, provider-independent, and authenticated API behavior remains intact.

### Task 5: Visual, Security, And Regression Verification

**Files:**
- Modify: `docs/architecture/README.md`
- Modify: `docs/tech-specs/README.md`
- Modify: `docs/superpowers/iwencai-native-workspaces/TODO.md`
- Create: `docs/superpowers/iwencai-native-workspaces/test.md`
- Create: `docs/superpowers/iwencai-native-workspaces/review.md`

- [ ] **Step 1: Run focused and full verification**

```bash
PYTHONPATH=src .venv/bin/python -m pytest \
  tests/test_research_engine.py \
  tests/test_web_research_workspace_api.py \
  tests/test_web_native_research_workspaces.py \
  tests/test_iwencai.py tests/test_web_iwencai_research.py -q
make lint
PYTHONPATH=src .venv/bin/python -m pytest -q
git diff --check
```

Expected: focused suite and lint pass. Record any intentionally obsolete old-workspace assertions separately; do not describe the full suite as clean unless it exits zero.

- [ ] **Step 2: Inspect desktop and mobile pages**

Start the app on an unused local port. Inspect all four routes at `1280x900` and `390x844`. Verify one verdict/action/risk hierarchy, no horizontal overflow, visible keyboard focus, reduced motion, localized failures, and no supplier wording in visible text or the browser console.

- [ ] **Step 3: Verify the real API without exposing credentials**

Run one authenticated request per module using server-side environment configuration. Record only status, duration, finding count, and missing-section count. Never print request headers, API key, raw trace id, private holding fields, or full upstream response.

- [ ] **Step 4: Update docs and commit**

Document the new runtime boundary, mark completed TODO items, record exact commands/results, run `git status --short`, and commit only this branch's files with a Chinese Conventional Commit message.


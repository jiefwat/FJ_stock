# Always-Visible Research UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep all four research workspaces populated with auditable content when the external research service is unavailable.

**Architecture:** Add a focused local adapter that converts existing TDX snapshot, stock, portfolio, sector, and candidate domain reports into the existing `ResearchWorkspaceResult` product contract. `deliver_research` keeps live and global snapshot precedence, then calls the adapter as a final evidence path. The Web handler injects the authenticated holdings path internally, while the browser and public JSON remain privacy-safe.

**Tech Stack:** Python 3.12, dataclasses, existing StockTs workflows/providers, stdlib HTTP server, pytest, Ruff, safe DOM JavaScript.

---

## File Structure

- Create `src/stock_ts/research_fallback.py`: build supplier-neutral local product results for market, portfolio, stock, and opportunity.
- Modify `src/stock_ts/research_delivery.py`: invoke local fallback after live/global snapshot failure without changing successful precedence.
- Modify `src/stock_ts/research_engine.py`: expose optional `data_label` and `fallback_reason` in the public result contract.
- Modify `src/stock_ts/web.py`: construct the local adapter, inject the authenticated holdings path internally, and return fallback results as HTTP 200.
- Modify `src/stock_ts/webapp/engine_workspace.py`: render delivery state, date, fallback reason, and preserve the previous result when refresh fails.
- Modify `src/stock_ts/webapp/styles.py`: style live/snapshot/local/history states on desktop and mobile.
- Create `tests/test_research_fallback.py`: unit tests for local stock, portfolio, market, and opportunity results.
- Modify `tests/test_research_snapshots.py`: delivery precedence and unavailable-to-local fallback tests.
- Modify `tests/test_web_research_workspace_api.py`: authenticated holdings-path injection and quota-error fallback tests.
- Modify `tests/test_web_native_research_workspaces.py`: DOM contract for fallback state and refresh preservation.
- Update `docs/superpowers/always-visible-research-ui/TODO.md` and add `test.md`, `review.md`, and `handoff.md` after verification.

### Task 1: Local stock fallback contract

**Files:**
- Create: `src/stock_ts/research_fallback.py`
- Modify: `src/stock_ts/research_engine.py`
- Create: `tests/test_research_fallback.py`

- [ ] **Step 1: Write the failing stock fallback test**

```python
from dataclasses import replace

from stock_ts.models import NewsItem
from stock_ts.providers.sample import SampleDataProvider


class LocalFixtureProvider(SampleDataProvider):
    def fetch_stock(self, code: str):
        raw = super().fetch_stock(code)
        return replace(
            raw,
            fundamental_metrics={"roe": 12.4, "revenue_yoy": 8.6, "net_profit_yoy": -3.2},
            valuation={"pe_ttm": raw.pe_ttm, "pb": 2.4},
            fund_flow_detail={"main_net_inflow": raw.fund_flow},
            news_items=[
                NewsItem(
                    date="2026-07-15",
                    source="公开新闻",
                    title="公司披露经营进展",
                    summary="收入保持增长，利润仍待修复。",
                )
            ],
            announcements=[
                {"title": "2026年半年度业绩预告", "date": "2026-07-15"}
            ],
        )


def test_local_stock_fallback_keeps_available_dimensions_and_marks_gaps() -> None:
    result = build_local_research(
        "stock",
        ResearchContext(code="603278", name="大业股份"),
        provider=LocalFixtureProvider(),
    )

    payload = result.to_public_dict()
    assert payload["status"] == "partial"
    assert payload["delivery"] == "local_fallback"
    assert payload["data_label"] == "本地证据"
    assert payload["verdict"]
    assert len(payload["findings"]) >= 2
    assert len(payload["module_items"]) == 8
    assert {item["label"] for item in payload["module_items"]} >= {
        "财务质量",
        "行情资金",
        "公告事项",
    }
    assert "机构预期" in payload["missing_sections"]
```

- [ ] **Step 2: Run the test and verify RED**

Run: `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m pytest tests/test_research_fallback.py::test_local_stock_fallback_keeps_available_dimensions_and_marks_gaps -q`

Expected: FAIL because `stock_ts.research_fallback` does not exist.

- [ ] **Step 3: Implement the minimal stock adapter**

Add `data_label: str = ""` and `fallback_reason: str = ""` to
`ResearchWorkspaceResult`, and serialize both fields in `to_public_dict()`.

Create `build_local_research(module, context, provider, holdings_path=None)` and a stock builder that:

```python
raw = provider.fetch_stock(context.code)
report = analyze_stock(raw)
items = (
    _stock_item("财务质量", _fundamental_summary(raw), bool(raw.fundamental_metrics)),
    _stock_item("经营结构", "经营结构需要实时研究补充。", False),
    _stock_item("机构预期", "机构预期需要实时研究补充。", False),
    _stock_item("事件风险", _event_summary(raw), bool(raw.news_items or raw.announcements)),
    _stock_item("行情资金", _market_summary(report, raw), True),
    _stock_item("行业位置", _industry_summary(provider, raw.code), bool(_industry_name(provider, raw.code))),
    _stock_item("公告事项", _announcement_summary(raw), bool(raw.announcements)),
    _stock_item("研报观点", "研报观点需要实时研究补充。", False),
)
```

Return `ResearchWorkspaceResult` with `delivery="local_fallback"`, `status="partial"`, non-empty verdict/action/risk/findings, eight module items, actual `as_of`, and explicit missing sections.

- [ ] **Step 4: Run the stock fallback test and verify GREEN**

Run: `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m pytest tests/test_research_fallback.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/stock_ts/research_fallback.py src/stock_ts/research_engine.py tests/test_research_fallback.py
git commit -m "feat: add local stock research fallback"
```

### Task 2: Portfolio, market, and opportunity fallback content

**Files:**
- Modify: `src/stock_ts/research_fallback.py`
- Modify: `tests/test_research_fallback.py`

- [ ] **Step 1: Write failing portfolio and global fallback tests**

```python
def test_local_portfolio_fallback_shows_all_positions_and_theme_sections(tmp_path) -> None:
    holdings = tmp_path / "holdings.csv"
    holdings.write_text(
        "code,name,shares,cost_price,sector,note\n"
        "600519,贵州茅台,10,1500,白酒,核心\n"
        "000001,平安银行,100,12,银行,观察\n"
        "300750,宁德时代,20,200,新能源车,观察\n",
        encoding="utf-8",
    )
    result = build_local_research(
        "portfolio",
        ResearchContext(
            holdings=(
                ResearchTarget(code="600519", name="贵州茅台"),
                ResearchTarget(code="000001", name="平安银行"),
                ResearchTarget(code="300750", name="宁德时代"),
            )
        ),
        provider=LocalFixtureProvider(),
        holdings_path=holdings,
    )
    payload = result.to_public_dict()
    assert payload["subject_count"] == 3
    assert len(payload["module_items"]) == 3
    assert {section["key"] for section in payload["module_sections"]} == {
        "portfolio-themes",
        "portfolio-divergence",
    }
    assert len(payload["findings"]) <= 3


def test_local_global_fallback_returns_market_and_opportunity_content() -> None:
    market = build_local_research("market", ResearchContext(), provider=LocalFixtureProvider())
    opportunity = build_local_research(
        "opportunity", ResearchContext(), provider=LocalFixtureProvider()
    )
    assert market.module_sections
    assert opportunity.module_sections
    assert market.module_items
    assert opportunity.module_items
```

- [ ] **Step 2: Run tests and verify RED**

Run: `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m pytest tests/test_research_fallback.py -q`

Expected: FAIL because only stock fallback exists.

- [ ] **Step 3: Implement portfolio and global adapters**

Use existing workflows:

```python
market = build_market_report(provider)
sectors = build_sector_report(provider, market=market)
portfolio = build_portfolio_report(
    provider,
    holdings_path=holdings_path,
    market=market,
    allow_empty=True,
)
candidates = build_candidate_report(
    provider,
    market=market,
    sectors=sectors,
    limit=10,
)
```

Map portfolio positions to `ResearchModuleItem`, sector weights to `portfolio-themes`, multi-member sectors to `portfolio-divergence`, market breadth to `market-breadth`, sectors to theme sections, and candidates to `opportunity-candidates`. Never put shares, cost, weight, notes, or holdings paths in `ResearchFact` or public summaries.

- [ ] **Step 4: Run fallback tests and verify GREEN**

Run: `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m pytest tests/test_research_fallback.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/stock_ts/research_fallback.py tests/test_research_fallback.py
git commit -m "feat: add portfolio and market fallback content"
```

### Task 3: Delivery and authenticated Web integration

**Files:**
- Modify: `src/stock_ts/research_delivery.py`
- Modify: `src/stock_ts/web.py`
- Modify: `tests/test_research_snapshots.py`
- Modify: `tests/test_web_research_workspace_api.py`

- [ ] **Step 1: Write failing delivery tests**

```python
def test_non_global_unavailable_result_uses_local_fallback(tmp_path) -> None:
    calls = []

    def fallback(module, context):
        calls.append((module, context))
        return ResearchWorkspaceResult(
            ok=True,
            status="partial",
            module="stock",
            generated_at=NOW.isoformat(),
            verdict="本地结论",
            action="条件观察",
            primary_risk="部分维度待补",
            delivery="local_fallback",
        )

    delivered = deliver_research(
        FakeService(_result(ok=False, status="unavailable")),
        ResearchSnapshotStore(tmp_path),
        "stock",
        ResearchContext(code="603278"),
        fallback=fallback,
    )
    assert delivered["delivery"] == "local_fallback"
    assert len(calls) == 1


def test_live_success_never_calls_local_fallback(tmp_path) -> None:
    def fallback(*_args):
        raise AssertionError("live success must not call fallback")

    delivered = deliver_research(
        FakeService(_result(ok=True, status="complete")),
        ResearchSnapshotStore(tmp_path),
        "stock",
        ResearchContext(code="603278"),
        fallback=fallback,
    )
    assert delivered["delivery"] == "live"
```

- [ ] **Step 2: Run tests and verify RED**

Run: `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m pytest tests/test_research_snapshots.py tests/test_web_research_workspace_api.py -q`

Expected: FAIL because `deliver_research` has no fallback callback and the handler does not inject a holdings path.

- [ ] **Step 3: Implement delivery precedence and internal holdings injection**

Extend delivery with:

```python
Fallback = Callable[[str, ResearchContext], ResearchWorkspaceResult]

def _local_payload(fallback: Fallback | None, module: str, context: ResearchContext):
    if fallback is None:
        return None
    result = fallback(module, context)
    payload = result.to_public_dict()
    payload["delivery"] = "local_fallback"
    payload["stale"] = False
    return payload
```

Use it after live exception or non-OK result, but only after global stale-snapshot lookup. In `_handle_research_workspace_post`, add the trusted value after parsing:

```python
payload["holdings_path"] = _effective_holdings_path(user)
```

In `_research_workspace_response`, construct `create_provider(WEB_DATA_PROVIDER)` and call `build_local_research` through a closure that receives the trusted holdings path. Browser-provided `holdings_path` remains ignored.

- [ ] **Step 4: Run integration tests and verify GREEN**

Run: `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m pytest tests/test_research_snapshots.py tests/test_web_research_workspace_api.py -q`

Expected: PASS, including missing configuration, gateway failure, and authenticated private-path cases.

- [ ] **Step 5: Commit**

```bash
git add src/stock_ts/research_delivery.py src/stock_ts/web.py tests/test_research_snapshots.py tests/test_web_research_workspace_api.py
git commit -m "feat: deliver local evidence when live research fails"
```

### Task 4: Always-visible UI state and refresh preservation

**Files:**
- Modify: `src/stock_ts/webapp/engine_workspace.py`
- Modify: `src/stock_ts/webapp/styles.py`
- Modify: `tests/test_web_native_research_workspaces.py`

- [ ] **Step 1: Write failing DOM contract tests**

```python
def test_engine_renders_local_fallback_state_and_reason() -> None:
    result = _run_engine_dom_scenario(LOCAL_FALLBACK_SCENARIO)
    assert result["delivery"] == "本地证据"
    assert result["reason"] == "实时研究暂不可用，已使用本地证据。"
    assert result["findings"] == 3
    assert result["items"] > 0


def test_refresh_error_preserves_previous_content() -> None:
    result = _run_engine_dom_scenario(REFRESH_ERROR_SCENARIO)
    assert result["verdict"] == "刷新前结论"
    assert result["live"] == "刷新失败，已保留现有内容"
```

- [ ] **Step 2: Run tests and verify RED**

Run: `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m pytest tests/test_web_native_research_workspaces.py -q`

Expected: FAIL because `local_fallback`, `data_label`, `fallback_reason`, and refresh preservation are not rendered.

- [ ] **Step 3: Implement the UI state**

Add delivery labels and fallback text rendering:

```javascript
const deliveryLabels = {
  live: '实时研究',
  snapshot: '当日快照',
  stale_snapshot: '历史参考',
  local_fallback: '本地证据',
  unavailable: '数据缺失'
};
delivery.textContent = payload.data_label || deliveryLabels[payload.delivery] || '实时研究';
workspace.dataset.engineDelivery = payload.delivery || 'live';
```

Add a dedicated `[data-engine-fallback-reason]` line below the header. In the fetch catch block, if `engineCache` has an existing result, re-render it and only set the live state to `刷新失败，已保留现有内容`; only render the unavailable payload on initial load with no cached content.

Add CSS for `data-engine-delivery="live|snapshot|local_fallback|stale_snapshot"`, mobile wrapping, visible focus, and reduced motion. Keep root width equal to viewport.

- [ ] **Step 4: Run UI tests and verify GREEN**

Run: `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m pytest tests/test_web_native_research_workspaces.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/stock_ts/webapp/engine_workspace.py src/stock_ts/webapp/styles.py tests/test_web_native_research_workspaces.py
git commit -m "feat: keep research workspaces populated during fallback"
```

### Task 5: Verification, documentation, and public deployment

**Files:**
- Modify: `docs/superpowers/always-visible-research-ui/TODO.md`
- Create: `docs/superpowers/always-visible-research-ui/test.md`
- Create: `docs/superpowers/always-visible-research-ui/review.md`
- Create: `docs/superpowers/always-visible-research-ui/handoff.md`

- [ ] **Step 1: Run focused Python 3.12 verification**

Run:

```bash
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m pytest -q \
  tests/test_research_fallback.py \
  tests/test_research_snapshots.py \
  tests/test_research_engine.py \
  tests/test_web_research_workspace_api.py \
  tests/test_web_native_research_workspaces.py \
  tests/test_auth.py tests/test_web_auth.py
```

Expected: all selected tests pass.

- [ ] **Step 2: Run lint, legacy rollback, and full baseline**

Run:

```bash
PATH=/Users/fangjie/Documents/StockTs/.venv/bin:$PATH make lint
STOCK_TS_WEB_VERSION=legacy /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m pytest -q \
  $(find tests -maxdepth 1 -name 'test_web_*.py' ! -name 'test_web_native_research_workspaces.py' -print)
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m pytest -q
git diff --check
```

Expected: lint and legacy rollback pass; full baseline has no failures absent from the recorded `653 passed / 141 failed` native-vs-legacy baseline.

- [ ] **Step 3: Verify the real exhausted-quota path locally**

Start the service with the configured key and confirm all four `/api/research/workspace` calls return HTTP 200. Market and opportunity may use snapshots; portfolio and stock must return `delivery=local_fallback`, non-empty verdict, findings, and module items without exposing credentials or supplier terms.

- [ ] **Step 4: Verify desktop and mobile UI**

At 1280x900 and 390x844 verify four-module navigation, quick stock search, candidate-to-stock drilldown, result shortcuts, evidence disclosure, refresh preservation, no horizontal overflow, and no console warning/error.

- [ ] **Step 5: Write test/review/handoff evidence and commit**

```bash
git add docs/superpowers/always-visible-research-ui
git commit -m "docs: record always-visible research verification"
```

- [ ] **Step 6: Fast-forward main, push, and deploy**

Fast-forward local `main` only after all gates pass, push `origin/main`, transfer the verified commit to `/opt/stock-ts`, preserve `.env`, `.secrets`, `data`, `reports`, authentication, and holdings, then restart only `stock-ts.service`.

- [ ] **Step 7: Verify public production**

Confirm local, GitHub, and server hashes match; `stock-ts.service`, `stock-ts-daily-research.timer`, and `stock-ts-daily-analysis.timer` are active; `/healthz` is 200; root redirects to login; authenticated four-module calls return content; no public response exposes credentials or supplier terms.

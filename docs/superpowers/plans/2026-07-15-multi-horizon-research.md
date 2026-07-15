# Multi-Horizon Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make StockTs block conclusions on stale or incomplete stock data, rank opportunities from reproducible multi-day evidence, and add a separate multi-day continuation list to the daily market workspace.

**Architecture:** Add a pure `continuation.py` domain module that computes multi-horizon profiles and stages from daily bars. `research_fallback.py` consumes those results for stock, market, portfolio, and opportunity product contracts; `web.py` validates the new snapshot contract; the existing DOM renderer receives dedicated section renderers without changing navigation or authentication. The K-line refresh script records stale results after comparing returned bars with the snapshot market date.

**Tech Stack:** Python 3.12, dataclasses, pytest, stdlib HTTP/DOM templates, Ruff, systemd deployment.

---

## File Map

- Create `src/stock_ts/continuation.py`: pure multi-horizon calculations, stage classification, score and candidate ordering.
- Create `tests/test_continuation.py`: deterministic profile, stale, pulse, overheat and ranking tests.
- Modify `src/stock_ts/research_fallback.py`: data gate, stock sections, continuation market section, multi-day opportunity facts and portfolio facts.
- Modify `tests/test_research_fallback.py`: stock data gate, market continuation and opportunity fact contracts.
- Modify `src/stock_ts/web.py`: reject old snapshots missing continuation contracts.
- Modify `tests/test_web_research_workspace_api.py`: snapshot rebuild tests for the new contract.
- Modify `src/stock_ts/webapp/engine_workspace.py`: render data-gate and continuation sections as compact lists.
- Modify `tests/test_web_native_research_workspaces.py`: renderer and no-brand assertions.
- Modify `scripts/refresh_a_share_kline.py`: mark returned bars stale when they lag the snapshot market date.
- Modify `tests/test_a_share_kline_refresh.py`: stale summary and reliable-price behavior.
- Update `docs/superpowers/specs/2026-07-15-multi-horizon-research-design.md`: only if implementation reveals a contract correction.

### Task 1: Pure multi-horizon profile and continuation stages

**Files:**
- Create: `src/stock_ts/continuation.py`
- Create: `tests/test_continuation.py`

- [ ] **Step 1: Write failing profile and stage tests**

Add fixtures that build 25 reliable `DailyBar` values and assert:

```python
profile = build_multi_horizon_profile(
    bars,
    market_trade_date="2026-07-15",
    price_reliable=True,
)
assert profile.return_5d == pytest.approx(expected_5d)
assert profile.up_days_5d == 4
assert profile.volume_ratio_5d_to_20d > 0
assert assess_continuation(profile).stage == "延续观察"
```

Add separate tests for:

```python
assert assess_continuation(pulse_profile).stage == "脉冲待验证"
assert assess_continuation(overheated_profile).stage == "过热回避"
assert assess_continuation(stale_profile).stage == "剔除"
assert assess_continuation(short_profile).stage == "剔除"
missing_flow = assess_continuation(steady_profile, fund_flow=None)
positive_flow = assess_continuation(steady_profile, fund_flow=2.0)
assert positive_flow.score > missing_flow.score
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `pytest -q tests/test_continuation.py`

Expected: collection fails because `stock_ts.continuation` does not exist.

- [ ] **Step 3: Implement the pure domain module**

Define immutable types with the listed fields. Expose exactly these two public call contracts:

```python
@dataclass(frozen=True)
class MultiHorizonProfile:
    as_of: str
    bar_count: int
    latest_return: float
    return_3d: float | None
    return_5d: float | None
    return_10d: float | None
    return_20d: float | None
    up_days_5d: int
    up_days_10d: int
    volume_ratio_5d_to_20d: float | None
    drawdown_10d: float | None
    distance_to_20d_high: float | None
    distance_to_ma20: float | None
    ma_alignment: str
    stale_days: int
    price_reliable: bool

@dataclass(frozen=True)
class ContinuationAssessment:
    score: int
    stage: str
    confidence: str
    support: str
    counter_evidence: str
    confirmation: str
    invalidation: str

build_multi_horizon_profile(
    bars: list[DailyBar], *, market_trade_date: str = "", price_reliable: bool = True
) -> MultiHorizonProfile

assess_continuation(
    profile: MultiHorizonProfile, *, theme_confirmed: bool = False,
    fund_flow: float | None = None, evidence_count: int = 0
) -> ContinuationAssessment
```

Keep all thresholds as named module constants. 资金流缺失必须贡献零分，不能按中性资金获得默认正分。Apply stale, insufficient-bar, pulse and overheat gates before positive stages.

- [ ] **Step 4: Run tests and confirm GREEN**

Run: `pytest -q tests/test_continuation.py`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/stock_ts/continuation.py tests/test_continuation.py
git commit -m "feat: add multi-horizon continuation model"
```

### Task 2: Correct stock data gates and compact missing evidence

**Files:**
- Modify: `src/stock_ts/research_fallback.py`
- Modify: `tests/test_research_fallback.py`

- [ ] **Step 1: Write failing stock-gate tests**

Create a fixture provider with market date `2026-07-15` and a stock ending `2026-07-14`, with only bars populated. Assert:

```python
result = build_local_research("stock", context, provider=provider)
assert result.decision_label == "数据不足"
assert "谨慎进攻" not in result.verdict
assert [section.key for section in result.module_sections[:2]] == [
    "stock-data-gate",
    "stock-multi-horizon",
]
assert sum(item.status == "missing" for item in result.module_items) == 1
assert result.module_items[-1].label == "关键缺口"
```

Add a fresh, sufficiently covered fixture that preserves a conditional non-blocked conclusion.

- [ ] **Step 2: Run the tests and confirm RED**

Run: `pytest -q tests/test_research_fallback.py -k 'stock and (gate or missing or multi_horizon)'`

Expected: failures show the old `谨慎进攻` result and seven missing cards.

- [ ] **Step 3: Implement stock gate integration**

In `_build_stock_research`, fetch the market date defensively and create the profile before the existing evidence matrix. Collapse missing dimensions with:

```python
missing_labels = tuple(item.label for item in raw_dimension_items if item.status != "ready")
module_items = tuple(item for item in raw_dimension_items if item.status == "ready") + (
    _missing_evidence_item(missing_labels),
)
```

Add `stock-data-gate` and `stock-multi-horizon` sections. Override verdict, action and label when stale or fewer than four dimensions are ready:

```python
if blocked:
    decision_label = "数据不足"
    verdict = f"{report.name}数据不足：{gate_reason}，暂停形成方向性判断。"
    action = "等待行情日期与关键研究证据补齐后再判断。"
```

Keep the eight analytic evidence cards only in `stock-evidence`; product-level `module_items` must contain ready evidence plus one missing summary.

- [ ] **Step 4: Run stock tests and confirm GREEN**

Run: `pytest -q tests/test_research_fallback.py -k 'stock'`

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/stock_ts/research_fallback.py tests/test_research_fallback.py
git commit -m "fix: gate stock conclusions on data readiness"
```

### Task 3: Multi-day opportunities and daily-market continuation list

**Files:**
- Modify: `src/stock_ts/research_fallback.py`
- Modify: `tests/test_research_fallback.py`

- [ ] **Step 1: Write failing opportunity and market tests**

Build three candidates: steady 10-day rise, one-day spike after four weak days, and stale data. Assert:

```python
opportunity = build_local_research("opportunity", ResearchContext(), provider=provider)
items = opportunity_section(opportunity, "opportunity-candidates").items
assert items[0].name == "稳步上行"
assert {fact.label for fact in items[0].facts} >= {
    "阶段判断", "持续性评分", "5日表现", "10日表现", "20日表现",
    "上涨天数", "最大回撤", "入选原因", "确认条件", "失效条件",
}
assert next(item for item in items if item.name == "单日脉冲").facts[0].value == "脉冲待验证"
assert all(item.name != "陈旧行情" for item in items)
```

For market, assert `market-continuation` and `market-movers` both exist and use different ordering logic.

- [ ] **Step 2: Run the tests and confirm RED**

Run: `pytest -q tests/test_research_fallback.py -k 'continuation or multi_day or pulse'`

Expected: missing section and missing facts failures.

- [ ] **Step 3: Implement candidate assessments and ordering**

Add helpers in `research_fallback.py` that convert each raw candidate to a profile and assessment using the market trade date. Sort by:

```python
(
    stage_priority[assessment.stage],
    -assessment.score,
    -(profile.return_10d or -999.0),
    profile.drawdown_10d or 999.0,
    candidate.code,
)
```

Exclude stale, unreliable, insufficient and overheated candidates from the default opportunity list. Permit pulse and rebound candidates only after continuation and breakout candidates. Populate all fixed multi-day facts.

Add a `market-continuation` section containing only `延续观察` and `突破待确认`, capped at eight items. Keep `_market_mover_candidates` unchanged as a separate one-day abnormal monitor.

- [ ] **Step 4: Reuse multi-day facts in portfolio items**

Build a profile for each portfolio position's stock bars when available and append stage, 5-day, 10-day and 20-day facts to the existing action/reason/confirmation/invalidation facts. If bars cannot be loaded, retain the existing position action without inventing a stage.

- [ ] **Step 5: Run tests and confirm GREEN**

Run: `pytest -q tests/test_continuation.py tests/test_research_fallback.py`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/stock_ts/research_fallback.py tests/test_research_fallback.py
git commit -m "feat: rank opportunities by multi-day continuation"
```

### Task 4: Snapshot contract and safe workspace rendering

**Files:**
- Modify: `src/stock_ts/web.py`
- Modify: `src/stock_ts/webapp/engine_workspace.py`
- Modify: `tests/test_web_research_workspace_api.py`
- Modify: `tests/test_web_native_research_workspaces.py`

- [ ] **Step 1: Write failing snapshot and renderer tests**

Assert old market snapshots without `market-continuation` rebuild locally. Assert old opportunity facts without `阶段判断`, `5日表现`, `10日表现`, `20日表现` rebuild locally.

Assert the engine script routes:

```python
assert "section.key === 'stock-data-gate'" in script
assert "section.key === 'stock-multi-horizon'" in script
assert "section.key === 'market-continuation'" in script
```

Keep the existing no-brand and `textContent` assertions.

- [ ] **Step 2: Run the tests and confirm RED**

Run: `pytest -q tests/test_web_research_workspace_api.py tests/test_web_native_research_workspaces.py -k 'snapshot or continuation or data_gate or renderer'`

Expected: old snapshots are accepted and the new section branches are absent.

- [ ] **Step 3: Tighten snapshot compatibility**

Require:

```python
required_sections = {
    "market": {"market-pulse", "market-continuation", "market-movers"},
    "opportunity": {"opportunity-candidates"},
}
```

Require multi-day opportunity facts and continuation facts before accepting snapshots.

- [ ] **Step 4: Add compact DOM renderers**

Render stock gate as a compact status strip and multi-horizon/continuation items as list rows. Use `engineNode`, `.textContent`, `replaceChildren` and existing link builders; do not interpolate response HTML.

- [ ] **Step 5: Run tests and confirm GREEN**

Run: `pytest -q tests/test_web_research_workspace_api.py tests/test_web_native_research_workspaces.py`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/stock_ts/web.py src/stock_ts/webapp/engine_workspace.py tests/test_web_research_workspace_api.py tests/test_web_native_research_workspaces.py
git commit -m "feat: render multi-horizon research workspaces"
```

### Task 5: Make K-line refresh status date-aware

**Files:**
- Modify: `scripts/refresh_a_share_kline.py`
- Modify: `tests/test_a_share_kline_refresh.py`

- [ ] **Step 1: Write a failing stale-refresh test**

Use a snapshot with market trade date `2026-07-15` and a fake Tushare response ending `2026-07-14`. Assert:

```python
summary = refresh_a_share_kline_snapshot(
    snapshot_path,
    holdings_path=None,
    codes=["300725"],
    tushare_client=fake_client,
)
assert summary["status"] == "stale"
assert summary["stale_count"] == 1
assert summary["stale_codes"] == ["300725"]
assert snapshot["stocks"]["300725"]["price_reliable"] is False
```

Add a same-date response that remains `ok` and reliable.

- [ ] **Step 2: Run the test and confirm RED**

Run: `pytest -q tests/test_a_share_kline_refresh.py -k 'stale or market_date'`

Expected: summary remains `ok` and price stays reliable.

- [ ] **Step 3: Implement date-aware refresh summary**

Compare each returned last bar date with `payload["market"]["trade_date"]`. Merge bars for historical use, but write `price_reliable=false` for stale results. Add `stale_count`, `stale_codes` and per-code reason. Status precedence is `failed`, `partial`, `stale`, then `ok`; mixed current and stale updates are `partial`.

- [ ] **Step 4: Run tests and confirm GREEN**

Run: `pytest -q tests/test_a_share_kline_refresh.py`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/refresh_a_share_kline.py tests/test_a_share_kline_refresh.py
git commit -m "fix: mark stale K-line refresh results"
```

### Task 6: Integrated verification and public deployment

This task completes local verification and 公网 deployment without adding a new service or timer.

**Files:**
- Create: `docs/research/multi-horizon-research-test-report.md`

- [ ] **Step 1: Run focused verification**

Run:

```bash
pytest -q \
  tests/test_continuation.py \
  tests/test_a_share_kline_refresh.py \
  tests/test_research_fallback.py \
  tests/test_web_native_research_workspaces.py \
  tests/test_web_research_workspace_api.py \
  tests/test_web_auth.py \
  tests/test_systemd_timer_contract.py
python -m py_compile \
  src/stock_ts/continuation.py \
  src/stock_ts/research_fallback.py \
  src/stock_ts/web.py \
  src/stock_ts/webapp/engine_workspace.py \
  scripts/refresh_a_share_kline.py
make lint
```

Expected: focused tests, compile and lint pass.

- [ ] **Step 2: Run full baseline comparison**

Run: `make test`

Expected: no failures beyond the recorded legacy-page/missing-fixture baseline. Record exact passed and failed counts.

- [ ] **Step 3: Browser verification**

Run the local server with temporary authenticated user data. Verify 1440px and 390px:

- `300725` shows `数据不足`, a stale gate, multi-horizon facts and one compact missing-evidence card.
- Market has separate continuation and mover sections.
- Opportunity ranks a steady multi-day fixture above a one-day pulse and exposes fixed facts.
- Portfolio edit/delete and stock drill-down still work.
- No horizontal overflow, console error, provider branding or internal fields.

- [ ] **Step 4: Commit the test report**

```bash
git add docs/research/*test-report.md
git commit -m "test: document multi-horizon research verification"
```

- [ ] **Step 5: Deploy with the existing bundle workflow**

Create and verify a Git bundle for `codex/research-data-depth-v2`, upload with the explicit deploy identity, fetch to `FETCH_HEAD`, fast-forward `/opt/stock-ts`, compile changed production files, and restart only `stock-ts.service`. Preserve `.env`, auth DB, holdings, reports, snapshots, Nginx and all existing timers.

- [ ] **Step 6: Public authenticated smoke test**

Verify:

- `/healthz = 200 / ok`, `/ = 303 -> /login`, `/login = 200`.
- Authenticated stock `300725` has a blocked data gate and no aggressive label.
- Market response has `market-continuation` before `market-movers`.
- Opportunity response has one candidate section and multi-day facts.
- Portfolio controls and stock links remain present.
- No provider branding, trace, gateway, key or private holding fields.
- `stock-ts.service` and the three existing timers are active; no new service or timer exists.

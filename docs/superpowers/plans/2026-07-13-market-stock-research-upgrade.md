# Market and Stock Research Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the daily-market workspace into an auditable market-regime console and the stock workspace into a professional investment memo with scenario analysis and evidence gating.

**Architecture:** Add pure research-domain modules under `stock_ts.research`, then pass their immutable results into focused workspace renderers under `stock_ts.webapp`. Keep `web.py` as the compatibility orchestration layer so the existing request flow and unrelated workspaces remain stable.

**Tech Stack:** Python 3.11 dataclasses, standard-library HTML rendering, pytest, ruff, existing StockTS provider and report models.

---

## File Map

- Create `src/stock_ts/research/__init__.py`: public exports for research-domain contracts.
- Create `src/stock_ts/research/evidence.py`: evidence status, source/date audit and reusable quality gates.
- Create `src/stock_ts/research/market_regime.py`: deterministic market-state assessment and three scenarios.
- Create `src/stock_ts/research/stock_memo.py`: business, quality, valuation, expectation-gap and scenario memo.
- Create `src/stock_ts/webapp/market_workspace.py`: semantic HTML for the market-regime console.
- Create `src/stock_ts/webapp/stock_workspace.py`: semantic HTML for the stock research memo.
- Modify `src/stock_ts/web.py`: construct the new research models and delegate only the two affected workspaces.
- Modify `src/stock_ts/webapp/styles.py`: add the market-state strip, thesis board, scenario grid and evidence audit styles.
- Create `tests/test_market_regime.py`: domain tests for market classification, evidence and stale-data gating.
- Create `tests/test_stock_research_memo.py`: domain tests for financial/valuation constraints and scenario output.
- Create `tests/test_web_market_research_workspace.py`: market workspace hierarchy and degraded-state tests.
- Create `tests/test_web_stock_research_workspace.py`: stock memo hierarchy, missing-data language and holding context tests.

## Increment One: Daily Market Regime Console

### Task 1: Create the evidence audit contract

**Files:**
- Create: `src/stock_ts/research/__init__.py`
- Create: `src/stock_ts/research/evidence.py`
- Test: `tests/test_research_evidence.py`

- [ ] **Step 1: Write the failing evidence tests**

```python
from stock_ts.research.evidence import EvidenceItem, EvidenceStatus, audit_status


def test_audit_status_blocks_stale_price_data() -> None:
    items = [
        EvidenceItem("行情", "tdx", "2026-07-10", EvidenceStatus.STALE, "交易日落后"),
        EvidenceItem("财务", "tushare", "2026-03-31", EvidenceStatus.COMPLETE, "季报"),
    ]
    assert audit_status(items, required={"行情"}) == EvidenceStatus.BLOCKED


def test_audit_status_degrades_when_optional_block_is_missing() -> None:
    items = [
        EvidenceItem("行情", "tdx", "2026-07-11", EvidenceStatus.COMPLETE, "日线"),
        EvidenceItem("估值", "", "", EvidenceStatus.MISSING, "缺历史分位"),
    ]
    assert audit_status(items, required={"行情"}) == EvidenceStatus.DEGRADED
```

- [ ] **Step 2: Run the tests and verify the import fails**

Run: `PYTHONPATH=src pytest -q tests/test_research_evidence.py`

Expected: FAIL with `ModuleNotFoundError: No module named 'stock_ts.research'`.

- [ ] **Step 3: Implement the immutable evidence contract**

```python
# src/stock_ts/research/evidence.py
from dataclasses import dataclass
from enum import StrEnum


class EvidenceStatus(StrEnum):
    COMPLETE = "complete"
    DEGRADED = "degraded"
    MISSING = "missing"
    STALE = "stale"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class EvidenceItem:
    block: str
    source: str
    as_of: str
    status: EvidenceStatus
    detail: str


def audit_status(items: list[EvidenceItem], *, required: set[str]) -> EvidenceStatus:
    by_block = {item.block: item for item in items}
    if any(
        block not in by_block
        or by_block[block].status in {EvidenceStatus.MISSING, EvidenceStatus.STALE, EvidenceStatus.BLOCKED}
        for block in required
    ):
        return EvidenceStatus.BLOCKED
    if any(item.status != EvidenceStatus.COMPLETE for item in items):
        return EvidenceStatus.DEGRADED
    return EvidenceStatus.COMPLETE
```

Export these names from `src/stock_ts/research/__init__.py`.

- [ ] **Step 4: Run the focused tests**

Run: `PYTHONPATH=src pytest -q tests/test_research_evidence.py`

Expected: `2 passed`.

- [ ] **Step 5: Commit the contract**

```bash
git add src/stock_ts/research tests/test_research_evidence.py
git commit -m "feat: add auditable research evidence contract"
```

### Task 2: Build the market regime model

**Files:**
- Create: `src/stock_ts/research/market_regime.py`
- Test: `tests/test_market_regime.py`

- [ ] **Step 1: Write failing regime and stale-gate tests**

```python
from stock_ts.models import IndexQuote, MarketSnapshot
from stock_ts.research.evidence import EvidenceStatus
from stock_ts.research.market_regime import assess_market_regime


def market(*, heat: int, advancing: int, declining: int, limit_down: int) -> MarketSnapshot:
    return MarketSnapshot(
        trade_date="2026-07-13",
        heat_score=heat,
        breadth_ratio=advancing / max(declining, 1),
        summary="test",
        regime="震荡",
        indices=[IndexQuote("000001", "上证指数", 3500, 1.1, 5000)],
        top_sectors=[("机器人", 3.2)],
        dimensions=[], opportunities=[], risks=[], tomorrow_watch=[],
        limit_up_count=70, limit_down_count=limit_down,
        advancing_count=advancing, declining_count=declining,
    )


def test_assessment_identifies_attack_regime_with_counter_evidence() -> None:
    result = assess_market_regime(market(heat=76, advancing=3900, declining=1100, limit_down=4))
    assert result.stage == "进攻"
    assert result.risk_budget == "70%-85%"
    assert len(result.supporting_evidence) >= 2
    assert result.counter_evidence
    assert result.invalidate_condition


def test_assessment_blocks_when_quote_is_stale() -> None:
    result = assess_market_regime(
        market(heat=76, advancing=3900, declining=1100, limit_down=4),
        quote_status=EvidenceStatus.STALE,
    )
    assert result.stage == "数据暂停"
    assert result.risk_budget == "0%"
```

- [ ] **Step 2: Run tests and confirm the missing implementation**

Run: `PYTHONPATH=src pytest -q tests/test_market_regime.py`

Expected: FAIL importing `assess_market_regime`.

- [ ] **Step 3: Implement deterministic contracts and classification**

Define `MarketRegimeDimension`, `MarketScenario` and `MarketRegimeAssessment` as frozen dataclasses. Implement `assess_market_regime(market, *, quote_status=EvidenceStatus.COMPLETE)` with these explicit thresholds:

```python
if quote_status in {EvidenceStatus.STALE, EvidenceStatus.BLOCKED}:
    stage, budget = "数据暂停", "0%"
elif market.heat_score >= 70 and market.breadth_ratio >= 1.5 and market.limit_down_count < 10:
    stage, budget = "进攻", "70%-85%"
elif market.heat_score >= 55 and market.breadth_ratio >= 0.9:
    stage, budget = "轮动", "50%-70%"
elif market.limit_down_count >= 30 or market.breadth_ratio < 0.55:
    stage, budget = "风险释放", "10%-30%"
elif market.heat_score < 45:
    stage, budget = "防守", "20%-40%"
else:
    stage, budget = "震荡", "40%-60%"
```

Create five dimensions named `趋势`, `宽度`, `流动性`, `风格`, `情绪`. When the current `MarketSnapshot` cannot support a cross-period claim, mark the dimension `degraded` and say `仅有当日截面`. Always generate bullish/base/bearish scenarios with explicit trigger and invalidation text.

- [ ] **Step 4: Run model tests and lint the new module**

Run: `PYTHONPATH=src pytest -q tests/test_market_regime.py tests/test_research_evidence.py && ruff check src/stock_ts/research tests/test_market_regime.py tests/test_research_evidence.py`

Expected: all tests pass and ruff exits 0.

- [ ] **Step 5: Commit market research model**

```bash
git add src/stock_ts/research/market_regime.py src/stock_ts/research/__init__.py tests/test_market_regime.py
git commit -m "feat: add deterministic market regime assessment"
```

### Task 3: Render the market research workspace

**Files:**
- Create: `src/stock_ts/webapp/market_workspace.py`
- Create: `tests/test_web_market_research_workspace.py`
- Modify: `src/stock_ts/web.py:6497`
- Modify: `src/stock_ts/webapp/styles.py`

- [ ] **Step 1: Write failing semantic-layout tests**

```python
from stock_ts.webapp.market_workspace import render_market_workspace


def test_market_workspace_orders_decision_before_evidence(attack_assessment) -> None:
    html = render_market_workspace(attack_assessment)
    assert 'data-market-stage="进攻"' in html
    assert html.index("市场状态") < html.index("趋势与宽度")
    assert html.index("最大风险") < html.index("三情景推演")
    assert "市场风险预算" in html
    assert "买卖指导" not in html


def test_market_workspace_exposes_snapshot_limitations(degraded_assessment) -> None:
    html = render_market_workspace(degraded_assessment)
    assert "仅有当日截面" in html
    assert "持续增强" not in html
```

Build fixtures in the same test file with explicit `MarketRegimeAssessment` objects; do not call providers.

- [ ] **Step 2: Run tests and verify the renderer is missing**

Run: `PYTHONPATH=src pytest -q tests/test_web_market_research_workspace.py`

Expected: FAIL importing `render_market_workspace`.

- [ ] **Step 3: Implement the pure renderer**

Implement `render_market_workspace(assessment, *, distribution_html="", sectors_html="", events_html="", refresh_html="")`. Escape all model text with `html.escape`. Use semantic sections and stable test hooks:

```html
<section class="market-research-workspace" data-market-stage="...">
  <header class="market-state-strip">...</header>
  <section aria-labelledby="market-thesis-title">...</section>
  <section aria-labelledby="market-structure-title">...</section>
  <section aria-labelledby="market-scenarios-title">...</section>
  <details class="evidence-audit">...</details>
</section>
```

- [ ] **Step 4: Delegate from the existing market function**

In `_render_compact_market_module`, build the assessment from `market`, pass the existing distribution, sector, wide-move and event fragments into the new renderer, and retain the current function signature. Do not alter portfolio, opportunity or account rendering.

- [ ] **Step 5: Add focused styles**

Add CSS variables and rules for `.market-state-strip`, `.market-thesis-board`, `.market-dimension-grid`, `.research-scenario-grid` and `.evidence-audit`. At `max-width: 680px`, force a single column and order the risk card before secondary evidence. Respect `prefers-reduced-motion`.

- [ ] **Step 6: Run focused and existing market tests**

Run: `PYTHONPATH=src pytest -q tests/test_web_market_research_workspace.py tests/test_web_module_decisions.py tests/test_web_design_guide_shell.py tests/test_web_layout.py`

Expected: all pass. If old assertions require removed labels such as `买卖指导`, update only assertions that conflict with the approved design; retain navigation and data-quality assertions.

- [ ] **Step 7: Commit the market workspace**

```bash
git add src/stock_ts/web.py src/stock_ts/webapp/market_workspace.py src/stock_ts/webapp/styles.py tests/test_web_market_research_workspace.py tests/test_web_module_decisions.py tests/test_web_design_guide_shell.py
git commit -m "feat: reshape daily market as regime console"
```

## Increment Two: Stock Investment Memo

### Task 4: Build the stock research memo model

**Files:**
- Create: `src/stock_ts/research/stock_memo.py`
- Create: `tests/test_stock_research_memo.py`

- [ ] **Step 1: Write failing completeness and valuation-language tests**

```python
from stock_ts.models import DailyBar, StockRawData
from stock_ts.research.stock_memo import build_stock_research_memo


def raw_stock(**changes) -> StockRawData:
    values = dict(
        code="600000", name="示例银行",
        bars=[DailyBar("2026-07-11", 10, 10.5, 9.8, 10.2, 1000)],
        pe_ttm=6.5,
        valuation={"pb": 0.7, "source": "tushare", "date": "2026-07-11"},
        fundamental_metrics={}, announcements=[], data_sources=["tdx", "tushare"],
    )
    values.update(changes)
    return StockRawData(**values)


def test_memo_does_not_call_absolute_multiples_undervalued() -> None:
    memo = build_stock_research_memo(raw_stock())
    assert memo.verdict.status == "技术性观察"
    assert "低估" not in memo.valuation.conclusion
    assert "缺少历史分位或行业对比" in memo.valuation.limitations


def test_memo_uses_financial_quality_when_fields_are_complete() -> None:
    memo = build_stock_research_memo(raw_stock(fundamental_metrics={
        "date": "2026-03-31", "revenue_yoy": 18.0, "net_profit_yoy": 24.0,
        "roe": 16.0, "gross_margin": 32.0, "debt_to_assets": 42.0,
        "ocf_to_profit": 1.2, "source": "tushare.fina_indicator",
    }))
    assert "盈利增速高于收入增速" in memo.quality.conclusion
    assert any(item.block == "经营质量" for item in memo.evidence)
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `PYTHONPATH=src pytest -q tests/test_stock_research_memo.py`

Expected: FAIL importing `build_stock_research_memo`.

- [ ] **Step 3: Implement focused memo dataclasses**

Define frozen dataclasses `ResearchSection`, `ResearchScenario`, `ResearchVerdict` and `StockResearchMemo`. Keep conclusions factual and separate `facts`, `limitations`, and `next_checks`.

`build_stock_research_memo(raw, *, holding=None, technical=None, event_radar=None)` must:

- label the result `技术性观察` when two of fundamentals, comparative valuation and announcements are missing;
- describe PE/PB as absolute multiples without high/low language unless `pe_percentile` or `industry_pe_median` exists;
- use `revenue_yoy`, `net_profit_yoy`, `roe`, `gross_margin`, `debt_to_assets`, and `ocf_to_profit` only when present;
- create bull/base/bear scenarios with `premises`, `signals`, and `invalidation`;
- expose `strongest_evidence`, `strongest_counter_evidence`, `core_conflict`, and `next_review`;
- create an `EvidenceItem` for行情, 经营质量, 估值, 资金, 新闻公告 and 组合上下文.

- [ ] **Step 4: Add explicit negative tests**

Add tests proving that one financial period never emits `趋势改善`, title-only announcement scanning contains `未代替原文复核`, and no holding never emits `成本优势` or `减仓`.

- [ ] **Step 5: Run model tests and lint**

Run: `PYTHONPATH=src pytest -q tests/test_stock_research_memo.py tests/test_research_evidence.py && ruff check src/stock_ts/research tests/test_stock_research_memo.py`

Expected: all pass and ruff exits 0.

- [ ] **Step 6: Commit stock memo model**

```bash
git add src/stock_ts/research/stock_memo.py src/stock_ts/research/__init__.py tests/test_stock_research_memo.py
git commit -m "feat: add auditable stock investment memo"
```

### Task 5: Render the stock research workspace

**Files:**
- Create: `src/stock_ts/webapp/stock_workspace.py`
- Create: `tests/test_web_stock_research_workspace.py`
- Modify: `src/stock_ts/web.py:9632`
- Modify: `src/stock_ts/webapp/styles.py`

- [ ] **Step 1: Write failing hierarchy and safety-copy tests**

```python
from stock_ts.webapp.stock_workspace import render_stock_workspace


def test_stock_workspace_leads_with_thesis_not_score(complete_memo) -> None:
    html = render_stock_workspace(complete_memo)
    assert html.index("研究结论") < html.index("六类证据")
    assert html.index("核心矛盾") < html.index("交易计划")
    assert "机会评分" not in html
    assert "乐观情景" in html and "基准情景" in html and "悲观情景" in html


def test_stock_workspace_shows_missing_blocks_without_false_confidence(degraded_memo) -> None:
    html = render_stock_workspace(degraded_memo)
    assert "技术性观察" in html
    assert "缺少历史分位或行业对比" in html
    assert "投资逻辑成立" not in html
    assert "低估" not in html
```

- [ ] **Step 2: Run tests and verify renderer import failure**

Run: `PYTHONPATH=src pytest -q tests/test_web_stock_research_workspace.py`

Expected: FAIL importing `render_stock_workspace`.

- [ ] **Step 3: Implement the pure stock renderer**

Implement `render_stock_workspace(memo, *, identity_html="", technical_html="", trade_plan_html="", agent_debate_html="", refresh_html="")` with this stable semantic order:

```html
<section class="stock-research-workspace" data-research-status="...">
  <header class="stock-identity-strip">...</header>
  <section class="stock-thesis-board">...</section>
  <section class="investment-memo-grid">...</section>
  <section class="research-scenario-grid">...</section>
  <section class="stock-evidence-grid">...</section>
  <section class="research-actions">...</section>
  <section class="trade-plan-section">...</section>
  <details class="evidence-audit">...</details>
  <details class="agent-debate">...</details>
</section>
```

Escape all model text. Scores may appear inside evidence cards but not in the title, identity strip or thesis board.

- [ ] **Step 4: Delegate from `_render_compact_stock_module`**

Build the memo from `stock_raw`, the matching portfolio position, `technical`, and `event_radar`. Reuse the existing trade-plan and TradingAgents renderers as collapsed supporting sections. Preserve the existing function signature and search form.

- [ ] **Step 5: Add stock memo styles**

Add `.stock-thesis-board`, `.thesis-conflict`, `.investment-memo-grid`, `.research-scenario-card`, `.stock-evidence-grid`, `.evidence-status` and mobile ordering rules. Use typography and spacing from the current terminal skin; do not introduce a new site-wide theme.

- [ ] **Step 6: Run stock and context regression tests**

Run: `PYTHONPATH=src pytest -q tests/test_web_stock_research_workspace.py tests/test_agentic_stock_method.py tests/test_professional_research.py tests/test_latest_stock_method_unified.py tests/test_web_module_decisions.py tests/test_web_data_accuracy.py`

Expected: all pass. Update only assertions invalidated by the approved hierarchy; keep provider dates, data gaps, holding cost and source-context assertions.

- [ ] **Step 7: Commit stock workspace**

```bash
git add src/stock_ts/web.py src/stock_ts/webapp/stock_workspace.py src/stock_ts/webapp/styles.py tests/test_web_stock_research_workspace.py tests/test_web_module_decisions.py tests/test_web_data_accuracy.py
git commit -m "feat: turn stock analysis into investment memo"
```

### Task 6: Integrate, document and verify the complete upgrade

**Files:**
- Modify: `docs/architecture/README.md`
- Modify: `docs/product/module-daily-market-design.md`
- Modify: `docs/product/module-stock-analysis-design.md`
- Create: `docs/agent-ops/test-reports/2026-07-13-market-stock-research-upgrade.md`

- [ ] **Step 1: Update architecture boundaries**

Document `stock_ts.research.evidence`, `market_regime`, `stock_memo` and both workspace renderers. State that research-domain modules return structured models and never HTML.

- [ ] **Step 2: Align product specifications with shipped behavior**

Update the two product docs to list the new semantic regions, three evidence states, scenario requirements, and the rule that scores cannot replace evidence. Keep any still-unimplemented data sources marked as gaps.

- [ ] **Step 3: Run the focused suite**

Run:

```bash
PYTHONPATH=src pytest -q \
  tests/test_research_evidence.py \
  tests/test_market_regime.py \
  tests/test_stock_research_memo.py \
  tests/test_web_market_research_workspace.py \
  tests/test_web_stock_research_workspace.py \
  tests/test_web_module_decisions.py \
  tests/test_web_data_accuracy.py \
  tests/test_web_layout.py
```

Expected: all pass.

- [ ] **Step 4: Run repository quality checks**

Run: `make lint && make test`

Expected: both commands exit 0. Record exact counts, duration and any warnings in the test report.

- [ ] **Step 5: Run three local Web smoke cases**

Start with `PYTHONPATH=src python3 -m stock_ts.web`. Verify with a complete TDX snapshot, a fixture with missing fundamentals, and a stale quote fixture. Record route, status, visible research state and screenshot/manual observations. Do not claim public deployment verification.

- [ ] **Step 6: Write the Markdown verification report**

Use the structure from `docs/agent-ops/local-full-test-flow.md`: environment, git state, commands, results, known warnings, browser smoke evidence and residual risks.

- [ ] **Step 7: Commit docs and verification evidence**

```bash
git add docs/architecture/README.md docs/product/module-daily-market-design.md \
  docs/product/module-stock-analysis-design.md docs/agent-ops/test-reports/2026-07-13-market-stock-research-upgrade.md
git commit -m "docs: record professional research upgrade verification"
```

## Execution Notes

- The current checkout contains pre-existing uncommitted changes. Before implementation, create an isolated worktree from commit `37e4436` or explicitly reconcile the existing diff; never reset or absorb unrelated files.
- Capture baseline failures for the focused suites before changing code so pre-existing failures remain distinguishable from regressions.
- If current dirty changes are required behavior, port them deliberately into the isolated branch as reviewed patches rather than copying the entire working tree.
- Do not use subagents unless the user explicitly authorizes delegation; inline execution is the default for this request.

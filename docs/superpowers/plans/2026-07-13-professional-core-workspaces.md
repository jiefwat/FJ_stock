# Professional Core Workspaces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a gate-first market-to-portfolio-to-opportunity decision chain that suppresses price-dependent actions and rankings when data is stale.

**Architecture:** Keep `MarketRegimeAssessment` as the market authority. Add module-specific immutable portfolio and opportunity dossiers under `stock_ts.research`, render them in focused `webapp` modules, and leave `web.py` responsible only for orchestration and compatibility. Both downstream dossiers receive `EvidenceStatus` explicitly and may tighten, never relax, the market risk gate.

**Tech Stack:** Python 3.9+, frozen dataclasses, existing StockTs analysis models, standard-library HTML escaping, pytest, Ruff, existing CSS terminal skin.

---

### Task 1: Define The Opportunity Dossier Contract

**Files:**

- Create: `src/stock_ts/research/opportunity_dossier_models.py`
- Create: `src/stock_ts/research/opportunity_dossier.py`
- Modify: `src/stock_ts/research/__init__.py`
- Test: `tests/test_opportunity_dossier.py`

- [ ] **Step 1: Write the failing stale-gate and state tests**

Create fixtures with one reliable high-score candidate, one ST candidate, one candidate with unreliable prices, and a `MarketRegimeAssessment`. Assert:

```python
def test_stale_quote_blocks_all_opportunity_candidates() -> None:
    dossier = build_opportunity_dossier(
        pool,
        market=market,
        quote_status=EvidenceStatus.STALE,
        candidate_universe=raw_candidates,
        metadata={"universe_size": "5200"},
    )

    assert dossier.gate.state == "数据暂停"
    assert dossier.gate.eligible_count == 0
    assert all(item.state == "待补数据" for item in dossier.candidates)


def test_candidate_states_are_mutually_exclusive() -> None:
    dossier = build_opportunity_dossier(
        pool,
        market=market,
        quote_status=EvidenceStatus.COMPLETE,
        candidate_universe=raw_candidates,
        metadata={"universe_size": "5200"},
    )

    assert {item.code: item.state for item in dossier.candidates} == {
        "600001": "可验证",
        "600002": "风险排除",
        "600003": "待补数据",
    }
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_opportunity_dossier.py
```

Expected: collection fails because `opportunity_dossier` and its models do not exist.

- [ ] **Step 3: Add immutable opportunity models**

Define:

```python
@dataclass(frozen=True)
class OpportunityGate:
    state: str
    action: str
    risk_budget: str
    data_status: str
    scanned_count: int | None
    evidence_ready_count: int
    eligible_count: int
    thesis: str
    next_step: str


@dataclass(frozen=True)
class FunnelStage:
    name: str
    count: int
    status: str
    note: str


@dataclass(frozen=True)
class CandidateDecision:
    code: str
    name: str
    sector: str
    state: str
    strategy: str
    evidence: tuple[str, ...]
    counter_evidence: tuple[str, ...]
    data_date: str
    data_status: EvidenceStatus
    next_verification: str
    exclusion_reason: str


@dataclass(frozen=True)
class OpportunityRisk:
    category: str
    severity: str
    evidence: str
    consequence: str


@dataclass(frozen=True)
class OpportunityDossier:
    gate: OpportunityGate
    funnel: tuple[FunnelStage, ...]
    candidates: tuple[CandidateDecision, ...]
    risks: tuple[OpportunityRisk, ...]
    source_notes: tuple[str, ...]
```

- [ ] **Step 4: Implement deterministic candidate classification**

Implement `build_opportunity_dossier(...)` with these rules:

```python
blocked = quote_status in {EvidenceStatus.STALE, EvidenceStatus.BLOCKED}
blocked = blocked or market.stage == "数据暂停"

if blocked or not pool.price_reliable or not item.price_reliable:
    state = "待补数据"
elif _has_explicit_exclusion(item):
    state = "风险排除"
elif item.score >= 70 and item.sector not in {"", "未识别主题"}:
    state = "可验证"
else:
    state = "只观察"
```

`_has_explicit_exclusion` only matches explicit blocking evidence such as ST/delist, investigation, major litigation, limit-down, missing liquidity, or unreliable data. Generic volatility and chase-risk text remains counter-evidence rather than excluding every candidate.

Sort fresh candidates by state priority (`可验证`, `只观察`, `风险排除`, `待补数据`) and then by existing score. Preserve input order when the gate is blocked so the UI cannot imply a current ranking.

- [ ] **Step 5: Run tests and verify GREEN**

Run the Task 1 test command. Expected: all tests pass.

- [ ] **Step 6: Commit the opportunity domain contract**

```bash
git add src/stock_ts/research/opportunity_dossier_models.py src/stock_ts/research/opportunity_dossier.py src/stock_ts/research/__init__.py tests/test_opportunity_dossier.py
git commit -m '[机会研究] 建立候选漏斗证据契约'
```

### Task 2: Render And Integrate The Opportunity Research Funnel

**Files:**

- Create: `src/stock_ts/webapp/opportunity_workspace.py`
- Modify: `src/stock_ts/web.py:4714`
- Modify: `src/stock_ts/webapp/styles.py`
- Create: `tests/test_web_opportunity_dossier.py`
- Modify: legacy opportunity UI tests that assert `推荐股票` or buy-language headings

- [ ] **Step 1: Write failing renderer tests**

Assert one primary verdict, funnel order, explicit counter-evidence, and the absence of recommendation language:

```python
def test_opportunity_workspace_is_gate_first_and_not_buy_first() -> None:
    html = render_opportunity_workspace(_dossier())

    assert html.count('data-primary-opportunity-verdict="true"') == 1
    assert html.index("机会总闸门") < html.index("研究候选")
    assert "支持证据" in html
    assert "最大反证" in html
    assert "推荐买入" not in html
    assert "推荐股票" not in html


def test_stale_web_page_has_no_ranked_candidate_surface() -> None:
    html = render_page(...stale fixture...)

    assert "数据暂停" in html
    assert "可验证 0" in html
    assert "待补数据" in html
    assert "推荐买入" not in html
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_web_opportunity_dossier.py
```

Expected: import failure for the missing renderer.

- [ ] **Step 3: Implement the opportunity renderer**

Render, in order:

1. `data-primary-opportunity-verdict="true"` gate panel.
2. Five funnel stage cells.
3. Candidate cards grouped by `可验证`, `只观察`, `风险排除`, `待补数据`.
4. Risk exclusion register.
5. Source and filter ledger.

Every candidate card contains strategy, supporting evidence, maximum counter-evidence, data status/date, next verification, and an `进入个股分析` link. Escape every provider-derived value.

- [ ] **Step 4: Replace legacy opportunity composition in Web**

In `_render_hot_opportunity_module`:

- retain `candidate_universe_metadata`;
- call `assess_market_regime(...)` using `quality.quote_status`;
- build the dossier once;
- render the new workspace once;
- remove the primary use of `_render_opportunity_buy_sell_guidance` and the recommendation table;
- keep compatible helper functions only if other callers/tests still use them.

Rename primary copy from `推荐股票/推荐买入` to `研究候选/进入个股分析`.

- [ ] **Step 5: Add the funnel visual system**

Add `.opportunity-dossier`, `.opportunity-gate-brief`, `.opportunity-funnel-rail`, `.candidate-decision-card`, and `.opportunity-risk-register` styles. Use the established navy/amber/paper tokens. Add 760px one-column and reduced-motion rules.

- [ ] **Step 6: Migrate old UI assertions and run focused tests**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q \
  tests/test_opportunity_dossier.py \
  tests/test_web_opportunity_dossier.py \
  tests/test_web_professional_modules.py \
  tests/test_web_module_decisions.py \
  tests/test_web_data_accuracy.py \
  tests/test_web_layout.py
```

Expected: no new failure beyond the documented stale-opportunity baseline assertion until its expected copy is migrated to the new gate contract.

- [ ] **Step 7: Commit the opportunity workspace**

```bash
git add src/stock_ts/webapp/opportunity_workspace.py src/stock_ts/web.py src/stock_ts/webapp/styles.py tests
git commit -m '[机会研究] 重构风险优先候选漏斗'
```

### Task 3: Define The Portfolio Dossier Contract

**Files:**

- Create: `src/stock_ts/research/portfolio_dossier_models.py`
- Create: `src/stock_ts/research/portfolio_dossier.py`
- Modify: `src/stock_ts/research/__init__.py`
- Create: `tests/test_portfolio_dossier.py`

- [ ] **Step 1: Write failing portfolio queue and stale tests**

```python
def test_portfolio_queue_prioritizes_risk_before_hold() -> None:
    dossier = build_portfolio_dossier(
        portfolio,
        advice,
        market=market_assessment,
        quote_status=EvidenceStatus.COMPLETE,
    )

    assert dossier.queue[0].state == "必须处理"
    assert dossier.queue[0].code == "600001"


def test_stale_quote_suppresses_numeric_portfolio_actions() -> None:
    dossier = build_portfolio_dossier(
        portfolio,
        advice,
        market=stale_market,
        quote_status=EvidenceStatus.STALE,
    )

    assert dossier.verdict.state == "数据暂停"
    assert all(item.state == "待补数据" for item in dossier.queue)
    assert all(item.target_range == "待刷新" for item in dossier.boundaries)
    assert all(item.invalidation == "待刷新" for item in dossier.boundaries)
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_portfolio_dossier.py
```

Expected: collection fails because the portfolio dossier modules do not exist.

- [ ] **Step 3: Add immutable portfolio models**

Define `PortfolioVerdict`, `PortfolioMetric`, `PortfolioQueueItem`, `PortfolioExposure`, `PortfolioBoundary`, and `PortfolioDossier`. Store all rendered text as explicit fields; keep weights and values numeric only where the renderer needs formatting.

- [ ] **Step 4: Implement deterministic portfolio classification**

Map existing `PositionAdvice.action`, risk level, trend, concentration, and quote status:

```python
if blocked or position.latest_price <= 0:
    state = "待补数据"
elif advice.action in {"降仓", "锁定利润"} or position.risk_level == "高":
    state = "必须处理"
elif advice.action == "持有观察" or position.weight >= 0.25:
    state = "重点观察"
else:
    state = "可继续持有"
```

Sort by state priority, then concentration and absolute loss. On stale data, keep cost/weight audit facts but set price-dependent action, target range, reduce trigger, and invalidation to `待刷新`.

- [ ] **Step 5: Run tests and verify GREEN**

Run the Task 3 test command. Expected: all tests pass.

- [ ] **Step 6: Commit the portfolio domain contract**

```bash
git add src/stock_ts/research/portfolio_dossier_models.py src/stock_ts/research/portfolio_dossier.py src/stock_ts/research/__init__.py tests/test_portfolio_dossier.py
git commit -m '[组合研究] 建立组合处置档案契约'
```

### Task 4: Render And Integrate The Portfolio Treatment Console

**Files:**

- Create: `src/stock_ts/webapp/portfolio_workspace.py`
- Modify: `src/stock_ts/web.py:8563`
- Modify: `src/stock_ts/webapp/styles.py`
- Create: `tests/test_web_portfolio_dossier.py`
- Modify: legacy portfolio tests that assert the old three-bucket summary

- [ ] **Step 1: Write failing renderer and Web integration tests**

```python
def test_portfolio_workspace_leads_with_one_committee_verdict() -> None:
    html = render_portfolio_workspace(_dossier())

    assert html.count('data-primary-portfolio-verdict="true"') == 1
    assert html.index("组合风控结论") < html.index("处置队列")
    assert html.index("处置队列") < html.index("持仓证据")
    assert "禁止动作" in html


def test_stale_portfolio_page_does_not_publish_old_price_actions() -> None:
    html = render_page(...stale fixture...)
    portfolio_html = _module_html(html, "portfolio")

    assert "数据暂停" in portfolio_html
    assert "价格动作待刷新" in portfolio_html
    assert "目标仓位" not in portfolio_html.split("持仓证据", 1)[0]
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_web_portfolio_dossier.py
```

Expected: import failure for the missing renderer.

- [ ] **Step 3: Implement the portfolio renderer**

Render one verdict, five risk metrics, ordered queue cards, exposure register, execution boundaries, and a supporting-evidence slot. Use `data-primary-portfolio-verdict="true"` and escape all position/account text.

- [ ] **Step 4: Pass quote quality into portfolio orchestration**

Add `quality: DataQualityView | None` to `_render_compact_portfolio_module`, pass it from `render_page`, build `MarketRegimeAssessment`, build one portfolio dossier, and render it once. Keep the edit form outside the dossier so account/write authorization remains unchanged.

Move the current detailed position table into the supporting-evidence slot. Remove the old primary `看好/建议轻仓/继续观察` buckets and generic buy/sell guidance.

- [ ] **Step 5: Add portfolio dossier responsive styles**

Add `.portfolio-dossier`, `.portfolio-verdict-brief`, `.portfolio-metric-strip`, `.portfolio-treatment-queue`, `.portfolio-exposure-register`, and `.portfolio-boundary-grid`. At 760px stack cards; keep edit forms and tables inside their own overflow containers.

- [ ] **Step 6: Run portfolio focused tests**

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q \
  tests/test_portfolio_dossier.py \
  tests/test_web_portfolio_dossier.py \
  tests/test_web_portfolio_interaction.py \
  tests/test_web_module_decisions.py \
  tests/test_web_compact_mode.py
```

Expected: all portfolio tests pass after migrating obsolete UI-copy assertions.

- [ ] **Step 7: Commit the portfolio workspace**

```bash
git add src/stock_ts/webapp/portfolio_workspace.py src/stock_ts/web.py src/stock_ts/webapp/styles.py tests
git commit -m '[组合研究] 重构风险优先处置工作台'
```

### Task 5: Tighten The Market Decision Rail

**Files:**

- Modify: `src/stock_ts/webapp/market_workspace.py`
- Modify: `src/stock_ts/webapp/styles.py`
- Modify: `tests/test_market_regime.py`
- Modify: `tests/test_web_market_research_workspace.py`

- [ ] **Step 1: Write failing market rail tests**

Assert the market workspace has exactly one primary verdict and five ordered steps: current regime, risk-on confirmation, position budget, downgrade trigger, reassessment.

- [ ] **Step 2: Run tests and verify RED**

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_web_market_research_workspace.py
```

Expected: failure because the current renderer has no five-step market rail.

- [ ] **Step 3: Add the rail without a second market conclusion**

Derive rail copy only from `MarketRegimeAssessment` fields. For `数据暂停`, every step must use pause/refresh language and contain no old market trigger number. Keep dimensions, scenarios, and raw market statistics as supporting evidence.

- [ ] **Step 4: Add matching rail styles and run tests**

Reuse the stock dossier rail geometry with market-specific class names so selector changes cannot affect the stock module. Run market, stock dossier, and responsive tests.

- [ ] **Step 5: Commit the market refinement**

```bash
git add src/stock_ts/webapp/market_workspace.py src/stock_ts/webapp/styles.py tests/test_market_regime.py tests/test_web_market_research_workspace.py
git commit -m '[大盘研究] 收口市场风险决策轨道'
```

### Task 6: Complete Cross-Module Verification And Documentation

**Files:**

- Modify: `docs/product/module-daily-market-design.md`
- Modify: `docs/product/module-portfolio-design.md`
- Modify: `docs/product/module-market-opportunities-design.md`
- Modify: `docs/superpowers/professional-core-workspaces/TODO.md`
- Modify: `docs/superpowers/professional-core-workspaces/test.md`
- Modify: `docs/superpowers/professional-core-workspaces/review.md`
- Modify: `docs/superpowers/professional-core-workspaces/handoff.md`

- [ ] **Step 1: Run focused suites**

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q \
  tests/test_opportunity_dossier.py tests/test_web_opportunity_dossier.py \
  tests/test_portfolio_dossier.py tests/test_web_portfolio_dossier.py \
  tests/test_market_regime.py tests/test_web_market_research_workspace.py \
  tests/test_stock_dossier.py tests/test_web_stock_dossier.py
```

- [ ] **Step 2: Run Python 3.9 compatibility**

```bash
PYTHONPATH=src /Users/fangjie/opt/anaconda3/bin/python3.9 -m pytest -q \
  tests/test_opportunity_dossier.py tests/test_portfolio_dossier.py
```

- [ ] **Step 3: Run Ruff and full pytest**

```bash
ruff check src tests
PYTHONPATH=src .venv/bin/python -m pytest -q --tb=short
```

Expected: Ruff passes. Compare pytest with the documented six-failure baseline and investigate every new failure.

- [ ] **Step 4: Run real-snapshot HTTP and browser smoke**

Start authentication-disabled Web on a temporary port. Verify:

- market, portfolio, opportunity, and stock each have one primary verdict;
- stale market risk budget and opportunity eligible count are zero;
- stale portfolio primary surface contains no target/stop price action;
- opportunity primary surface contains no recommendation/buy language;
- desktop 1440px and mobile 390px have no document-level horizontal overflow;
- stop the temporary server and confirm the port is released.

- [ ] **Step 5: Perform AI Review**

Review `main..HEAD` for stale-data bypass, hidden ranking, cost/weight arithmetic, state ordering, XSS escaping, account isolation, and responsive overflow. Fix P0/P1 findings and rerun focused/full verification.

- [ ] **Step 6: Update evidence documents**

Record exact counts, known baseline failures, review findings, screenshots, and deployment boundaries in the requirement directory and product specs.

- [ ] **Step 7: Commit quality evidence**

```bash
git add docs src tests
git commit -m '[核心工作台] 完成三模块质量闭环'
```

- [ ] **Step 8: Merge, push, and deploy**

Fast-forward `main`, push `origin/main`, create a new `/opt/stock-ts/.deploy_backups/` rollback package, deploy tracked source without modifying `.env`, `.secrets`, snapshots, holdings, reports, Nginx, timers, or DSA, restart `stock-ts.service`, and verify local/GitHub/server commit equality plus public login/auth routes.

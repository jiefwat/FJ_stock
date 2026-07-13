# Professional Stock Dossier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the duplicated and shallow stock-analysis surface with one deterministic, auditable professional dossier that converts financial, valuation, technical, capital, event, and portfolio evidence into bounded action guidance.

**Architecture:** Add focused typed models, diagnostic calculations, and decision orchestration under `stock_ts.research`; keep `web.py` limited to collecting existing inputs. Render a single investment-committee workspace with a decision rail, risk register, diagnostics, scenarios, and a collapsed evidence ledger. Preserve the existing `StockResearchMemo` for compatibility, but stop using it as a second primary conclusion in the Web workspace.

**Tech Stack:** Python 3.9+, frozen dataclasses, standard-library statistics/math/HTML escaping, existing StockTs Web renderer and CSS, pytest, Ruff.

---

## File Map

Create:

- `src/stock_ts/research/stock_dossier_models.py`: immutable public dossier contracts only.
- `src/stock_ts/research/stock_diagnostics.py`: deterministic financial, valuation, technical, capital, and event calculations.
- `src/stock_ts/research/stock_dossier.py`: evidence grade, risk synthesis, verdict, position guidance, scenarios, and orchestration.
- `tests/test_stock_dossier.py`: domain and decision-rule tests.
- `tests/test_web_stock_dossier.py`: renderer and Web integration tests.
- `docs/superpowers/professional-stock-dossier/README.md`: requirement goal, scope, non-goals, acceptance.
- `docs/superpowers/professional-stock-dossier/TODO.md`: task status.
- `docs/superpowers/professional-stock-dossier/plan.md`: pointer to this implementation plan.
- `docs/superpowers/professional-stock-dossier/test.md`: verification evidence.
- `docs/superpowers/professional-stock-dossier/review.md`: review findings and decision.
- `docs/superpowers/professional-stock-dossier/handoff.md`: current state and deployment evidence.

Modify:

- `docs/superpowers/README.md`: register the active requirement.
- `src/stock_ts/research/__init__.py`: export dossier contracts and builder.
- `src/stock_ts/webapp/stock_workspace.py`: render the dossier as the only primary stock decision.
- `src/stock_ts/webapp/styles.py`: add the decision-rail and risk-register visual rules.
- `src/stock_ts/web.py`: build the dossier and remove duplicated primary legacy conclusions.
- `tests/test_web_stock_research_workspace.py`: retain memo compatibility tests while moving workspace expectations to the dossier.
- `docs/product/module-stock-analysis-design.md`: record the implemented contract after verification.

Do not modify providers or production snapshot data in this phase. All new conclusions must be derived from fields already present in `StockRawData` and existing typed supporting models.

---

### Task 1: Register The Active Requirement

**Files:**

- Modify: `docs/superpowers/README.md`
- Create: `docs/superpowers/professional-stock-dossier/README.md`
- Create: `docs/superpowers/professional-stock-dossier/TODO.md`
- Create: `docs/superpowers/professional-stock-dossier/plan.md`
- Create: `docs/superpowers/professional-stock-dossier/test.md`
- Create: `docs/superpowers/professional-stock-dossier/review.md`
- Create: `docs/superpowers/professional-stock-dossier/handoff.md`

- [ ] **Step 1: Add the active-index entry**

Add exactly this entry under `## 活跃需求`:

```markdown
- `professional-stock-dossier/`：统一专业个股研究档案与条件化操作指引
```

- [ ] **Step 2: Create the requirement README**

```markdown
# Professional Stock Dossier

## 目标

把个股分析从重复的指标摘要升级为单一、可审计、可执行的专业研究档案。

## 范围

- 财务、估值、技术、资金、事件和持仓诊断。
- 单一研究立场、决策轨道、风险登记表和条件化仓位建议。
- 桌面与移动端个股工作区。

## 不做事项

- 不接券商下单。
- 不生成无依据目标价或上涨概率。
- 不使用 LLM 替代确定性证据规则。

## 验收

- 真实 `603278` 快照显示亏损、负 PE 失效、PB 口径冲突、高质押风险和多周期价格结构。
- 页面只有一个主结论，且每个动作都有触发、降级和失效条件。
```

- [ ] **Step 3: Create TODO, plan, test, review, and handoff skeletons**

`TODO.md` starts with every task in this plan unchecked. `plan.md` links to `../plans/2026-07-13-professional-stock-dossier.md`. `test.md`, `review.md`, and `handoff.md` contain headings and `Status: pending` only; they do not claim evidence before verification.

- [ ] **Step 4: Validate and commit the requirement assets**

Run:

```bash
git diff --check
rg -n "professional-stock-dossier" docs/superpowers/README.md docs/superpowers/professional-stock-dossier
```

Expected: no whitespace errors and all requirement links resolve.

Commit:

```bash
git add docs/superpowers/README.md docs/superpowers/professional-stock-dossier
git commit -m "[个股研究] 登记专业个股档案需求"
```

---

### Task 2: Add Dossier Contracts And Evidence Grade

**Files:**

- Create: `src/stock_ts/research/stock_dossier_models.py`
- Create: `src/stock_ts/research/stock_dossier.py`
- Create: `tests/test_stock_dossier.py`
- Modify: `src/stock_ts/research/__init__.py`

- [ ] **Step 1: Write failing evidence-grade tests**

Create reusable fixtures with 80 deterministic daily bars and add:

```python
def test_complete_score_measures_evidence_not_upside() -> None:
    dossier = build_professional_stock_dossier(
        _raw_stock(financial=True, events=True),
        technical=_technical(),
        event_radar=_event_radar(),
        input_quality=ResearchInputQuality(quote_status=EvidenceStatus.COMPLETE),
    )

    assert dossier.verdict.evidence_grade in {"A", "B"}
    assert dossier.verdict.confidence >= 70
    assert "上涨概率" not in dossier.verdict.thesis


def test_stale_quote_forces_grade_d_and_zero_confidence() -> None:
    dossier = build_professional_stock_dossier(
        _raw_stock(financial=True, events=True),
        technical=_technical(),
        event_radar=_event_radar(),
        input_quality=ResearchInputQuality(
            quote_status=EvidenceStatus.STALE,
            blockers=("行情日期落后",),
        ),
    )

    assert dossier.verdict.stance == "数据暂停"
    assert dossier.verdict.evidence_grade == "D"
    assert dossier.verdict.confidence == 0
    assert dossier.position.position_cap == "0%"
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_stock_dossier.py
```

Expected: collection fails because `stock_ts.research.stock_dossier` does not exist.

- [ ] **Step 3: Add immutable dossier contracts**

Define in `stock_dossier_models.py`:

```python
@dataclass(frozen=True)
class DossierVerdict:
    stance: str
    action: str
    evidence_grade: str
    confidence: int
    horizon: str
    thesis: str
    strongest_evidence: str
    strongest_counter_evidence: str
    next_review: str


@dataclass(frozen=True)
class DecisionStep:
    label: str
    state: str
    condition: str
    consequence: str


@dataclass(frozen=True)
class DiagnosticBlock:
    name: str
    status: str
    conclusion: str
    facts: tuple[str, ...]
    risks: tuple[str, ...]
    limitation: str


@dataclass(frozen=True)
class RiskItem:
    severity: str
    category: str
    evidence: str
    consequence: str
    monitor: str


@dataclass(frozen=True)
class PositionGuidance:
    audience: str
    current_action: str
    position_cap: str
    risk_budget: str
    entry_trigger: str
    add_trigger: str
    reduce_trigger: str
    invalidation: str
    prohibited_action: str


@dataclass(frozen=True)
class DossierScenario:
    name: str
    premise: str
    confirmation: str
    action: str
    invalidation: str
    evidence_source: str


@dataclass(frozen=True)
class ProfessionalStockDossier:
    code: str
    name: str
    trade_date: str
    latest_close: float
    verdict: DossierVerdict
    decision_steps: tuple[DecisionStep, ...]
    diagnostics: tuple[DiagnosticBlock, ...]
    risks: tuple[RiskItem, ...]
    position: PositionGuidance
    scenarios: tuple[DossierScenario, ...]
    evidence: tuple[EvidenceItem, ...]
```

- [ ] **Step 4: Implement the minimal builder and fixed completeness score**

Use the exact weights from the design. The builder returns Grade D and confidence 0 before evaluating any other rule when quote status is stale or blocked. Do not infer attractiveness from confidence.

Use this public signature throughout later tasks:

```python
def build_professional_stock_dossier(
    raw: StockRawData,
    *,
    technical: TechnicalProfile,
    event_radar: EventRadar,
    holding: Holding | None = None,
    input_quality: ResearchInputQuality | None = None,
    sector_context: str = "",
    market_context: str = "",
) -> ProfessionalStockDossier:
    ...
```

- [ ] **Step 5: Run focused tests and lint**

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_stock_dossier.py
.venv/bin/ruff check src/stock_ts/research tests/test_stock_dossier.py
```

Expected: evidence-grade tests pass and Ruff reports no errors.

- [ ] **Step 6: Commit**

```bash
git add src/stock_ts/research/stock_dossier_models.py src/stock_ts/research/stock_dossier.py src/stock_ts/research/__init__.py tests/test_stock_dossier.py
git commit -m "[个股研究] 建立专业档案证据契约"
```

---

### Task 3: Implement Financial And Valuation Diagnostics

**Files:**

- Create: `src/stock_ts/research/stock_diagnostics.py`
- Modify: `src/stock_ts/research/stock_dossier.py`
- Modify: `tests/test_stock_dossier.py`

- [ ] **Step 1: Write failing financial snapshot tests**

```python
def test_absolute_financial_snapshot_is_not_reported_missing() -> None:
    raw = _raw_stock(
        fundamental_metrics={
            "eps": -0.07,
            "net_asset_per_share": 5.665,
            "operating_revenue": 1_136_418.25,
            "operating_profit": -27_039.40,
            "net_profit": -24_557.60,
            "operating_cash_flow": 29_811.00,
            "source": "tdx.profile.finance",
            "date": "2026-05-18",
        }
    )

    dossier = _build(raw)
    financial = _diagnostic(dossier, "财务质量")

    assert financial.status == "degraded"
    assert "亏损" in financial.conclusion
    assert "经营现金流为正" in financial.conclusion
    assert "财务数据缺失" not in financial.conclusion


def test_negative_pe_is_not_a_valuation_anchor() -> None:
    dossier = _build(_raw_stock(pe_ttm=-79.96, fundamental_metrics={"net_profit": -10.0}))
    valuation = _diagnostic(dossier, "估值")

    assert "PE 失去解释力" in valuation.conclusion
    assert "低估" not in valuation.conclusion


def test_reported_pb_conflict_is_exposed() -> None:
    dossier = _build(
        _raw_stock(
            close=10.05,
            valuation={"pb": 0.177},
            fundamental_metrics={"net_asset_per_share": 5.665},
        )
    )
    valuation = _diagnostic(dossier, "估值")

    assert valuation.status == "degraded"
    assert "来源 PB 0.18x" in valuation.conclusion
    assert "价格/每股净资产反算 1.77x" in valuation.conclusion
    assert "口径冲突" in valuation.risks
```

- [ ] **Step 2: Run tests and verify RED**

Expected: financial diagnostic is absent or still reports the block as missing.

- [ ] **Step 3: Implement financial calculations**

Add `build_financial_diagnostic(raw)` and derive only compatible-unit ratios. Use explicit branches for negative profit plus positive operating cash flow. Keep snapshot state separate from multi-period trend state.

- [ ] **Step 4: Implement valuation validation**

Add `build_valuation_diagnostic(raw)`. Reject negative PE as an anchor, derive PB from close/BPS, and mark a greater-than-30% source conflict as degraded. Preserve the existing 20-observation percentile requirement.

- [ ] **Step 5: Run tests and commit**

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_stock_dossier.py
.venv/bin/ruff check src/stock_ts/research tests/test_stock_dossier.py
git add src/stock_ts/research/stock_diagnostics.py src/stock_ts/research/stock_dossier.py tests/test_stock_dossier.py
git commit -m "[个股研究] 补齐财务与估值诊断"
```

---

### Task 4: Implement Multi-Horizon Technical And Capital Diagnostics

**Files:**

- Modify: `src/stock_ts/research/stock_diagnostics.py`
- Modify: `src/stock_ts/research/stock_dossier.py`
- Modify: `tests/test_stock_dossier.py`

- [ ] **Step 1: Write failing regime tests**

```python
def test_one_day_rebound_after_twenty_day_damage_is_not_reversal() -> None:
    raw = _raw_from_closes(_declining_closes(79) + [10.05])
    dossier = _build(raw)
    technical = _diagnostic(dossier, "技术结构")

    assert "反弹尝试" in technical.conclusion
    assert "趋势反转" not in technical.conclusion
    assert any("20日" in fact for fact in technical.facts)
    assert any("60日高点" in fact for fact in technical.facts)


def test_turnover_proxy_is_not_called_main_fund_flow() -> None:
    dossier = _build(
        _raw_stock(
            fund_flow=None,
            fund_flow_detail={
                "source": "tdx.quote.turnover",
                "amount_yuan": 306_457_952,
                "turnover_rate": 8.84,
            },
        )
    )
    capital = _diagnostic(dossier, "资金与交易")

    assert "成交活跃" in capital.conclusion
    assert "主力净流入" not in capital.conclusion
    assert "单日" in capital.limitation
```

- [ ] **Step 2: Run tests and verify RED**

Expected: no multi-horizon classification or source-safe capital conclusion exists.

- [ ] **Step 3: Implement returns, drawdown, volatility, and regime**

Calculate 5/20/60-session returns only when enough closes exist. Calculate 60-session drawdown and 20-session annualized realized volatility. Apply the ordered regime rules from the design so `breakdown risk` and `rebound attempt` take precedence over generic range text.

- [ ] **Step 4: Implement source-safe capital diagnostics**

Only use `main_net_inflow` wording when the source is a true money-flow provider. For `tdx.quote.turnover` and derived K-line signals, use `成交活跃度`, `量价承接`, and `分歧` wording.

- [ ] **Step 5: Run tests and commit**

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_stock_dossier.py
.venv/bin/ruff check src/stock_ts/research tests/test_stock_dossier.py
git add src/stock_ts/research/stock_diagnostics.py src/stock_ts/research/stock_dossier.py tests/test_stock_dossier.py
git commit -m "[个股研究] 增加多周期技术与资金诊断"
```

---

### Task 5: Implement Event Risk, Verdict, And Position Guidance

**Files:**

- Modify: `src/stock_ts/research/stock_diagnostics.py`
- Modify: `src/stock_ts/research/stock_dossier.py`
- Modify: `tests/test_stock_dossier.py`

- [ ] **Step 1: Write failing event and action tests**

```python
def test_high_pledge_and_loss_constrain_non_holder_to_zero_position() -> None:
    raw = _raw_stock(
        fundamental_metrics={"net_profit": -24_557.6},
        news_items=[
            NewsItem(
                date="2026-05-25",
                source="fixture",
                title="控股股东累计质押占其持股65.72%",
                summary="",
                sentiment="negative",
            )
        ],
    )
    dossier = _build(raw, holding=None)

    assert dossier.verdict.stance == "风险规避"
    assert dossier.position.position_cap == "0%"
    assert any(item.severity == "high" and item.category == "股权质押" for item in dossier.risks)
    assert "追反弹" in dossier.position.prohibited_action


def test_holder_guidance_uses_cost_without_calling_cost_bullish() -> None:
    dossier = _build(
        _raw_stock(close=9.5),
        holding=Holding("603278", "大业股份", 1000, 11.0, "高端装备"),
    )

    assert dossier.position.audience == "已持仓"
    assert "成本 11.00" in dossier.position.current_action
    assert "成本优势" not in dossier.verdict.thesis
    assert dossier.position.reduce_trigger
    assert dossier.position.invalidation
```

- [ ] **Step 2: Run tests and verify RED**

Expected: pledge percentage is not parsed and stance does not constrain the position cap.

- [ ] **Step 3: Implement event classification and risk register**

Scan announcement/news title plus summary. Extract pledge percentages with a bounded regex, link the extracted percentage to its source text, and classify reduction, pledge, guarantee, financial assistance, litigation, regulation, loss warning, and neutral operating updates.

- [ ] **Step 4: Implement ordered stance rules**

Apply in this order:

```text
stale/block -> 数据暂停
critical risk -> 风险规避
high event risk + loss/weak technical -> 风险规避
holding exists -> 持仓管理
grade C or weak technical -> 等待修复
grade A/B + explicit upgrade trigger -> 条件观察
```

- [ ] **Step 5: Implement five decision steps and separate position guidance**

Return exactly current, upgrade, add confirmation, downgrade, and invalidation steps. Non-holder caps are 0% while blocked/high combined risk and at most 5% only after Grade A/B triggers. Holder guidance includes cost and P/L but never treats cost as business evidence.

- [ ] **Step 6: Run tests and commit**

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_stock_dossier.py
.venv/bin/ruff check src/stock_ts/research tests/test_stock_dossier.py
git add src/stock_ts/research/stock_diagnostics.py src/stock_ts/research/stock_dossier.py tests/test_stock_dossier.py
git commit -m "[个股研究] 收敛事件风险与仓位指引"
```

---

### Task 6: Make Scenarios And Evidence Stock-Specific

**Files:**

- Modify: `src/stock_ts/research/stock_dossier.py`
- Modify: `tests/test_stock_dossier.py`

- [ ] **Step 1: Write failing scenario tests**

```python
def test_scenarios_reference_actual_stock_evidence() -> None:
    dossier = _build(_loss_making_high_pledge_raw())
    text = " ".join(
        f"{item.premise} {item.confirmation} {item.action} {item.invalidation}"
        for item in dossier.scenarios
    )

    assert [item.name for item in dossier.scenarios] == ["改善", "基准", "恶化"]
    assert "亏损" in text
    assert "质押" in text
    assert "20日" in text or "MA20" in text
    assert "盈利质量改善，事件无新增风险" not in text
```

- [ ] **Step 2: Run tests and verify RED**

Expected: scenarios are missing or generic.

- [ ] **Step 3: Build scenarios from the strongest diagnostics and risks**

Each scenario must cite at least one stock-specific fact and one observable confirmation or invalidation. Do not add numeric probability or target price.

- [ ] **Step 4: Build an evidence ledger**

Map every diagnostic to source, date, status, and limitation. Preserve missing and conflicting evidence rather than filtering it out.

- [ ] **Step 5: Run tests and commit**

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_stock_dossier.py
git add src/stock_ts/research/stock_dossier.py tests/test_stock_dossier.py
git commit -m "[个股研究] 生成个股化情景与证据账本"
```

---

### Task 7: Render The Investment-Committee Workspace

**Files:**

- Modify: `src/stock_ts/webapp/stock_workspace.py`
- Create: `tests/test_web_stock_dossier.py`
- Modify: `tests/test_web_stock_research_workspace.py`

- [ ] **Step 1: Write failing renderer tests**

```python
def test_workspace_leads_with_one_decision_and_five_step_rail() -> None:
    html = render_stock_workspace(_dossier())

    assert html.index("投委会结论") < html.index("诊断底稿")
    assert html.count('data-primary-stock-verdict="true"') == 1
    assert html.count('class="decision-rail-step') == 5
    assert "当前状态" in html
    assert "转强触发" in html
    assert "加仓确认" in html
    assert "降级触发" in html
    assert "失效退出" in html


def test_workspace_places_risk_before_scenarios_and_labels_confidence() -> None:
    html = render_stock_workspace(_dossier())

    assert html.index("风险登记表") < html.index("三种情景")
    assert "证据完整度" in html
    assert "上涨概率" not in html
    assert "仓位上限" in html
    assert "禁止动作" in html
```

- [ ] **Step 2: Run tests and verify RED**

Expected: current renderer accepts `StockResearchMemo` and lacks the decision-rail markup.

- [ ] **Step 3: Replace the primary renderer contract**

Render `ProfessionalStockDossier` with these functions:

```python
render_stock_workspace(...)
_render_decision_brief(...)
_render_decision_rail(...)
_render_position_guidance(...)
_render_risk_register(...)
_render_diagnostics(...)
_render_scenarios(...)
_render_evidence_ledger(...)
```

Escape all dynamic strings. Use `<details>` for raw evidence. Keep identity, refresh, and supporting legacy evidence as optional injected HTML slots.

- [ ] **Step 4: Update memo renderer tests**

Keep `build_stock_research_memo` unit tests. Move Web workspace expectations to `test_web_stock_dossier.py`; do not delete safety assertions for stale quotes or missing evidence.

- [ ] **Step 5: Run tests and commit**

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_web_stock_dossier.py tests/test_web_stock_research_workspace.py
.venv/bin/ruff check src/stock_ts/webapp tests/test_web_stock_dossier.py tests/test_web_stock_research_workspace.py
git add src/stock_ts/webapp/stock_workspace.py tests/test_web_stock_dossier.py tests/test_web_stock_research_workspace.py
git commit -m "[个股研究] 重构投委会式个股工作区"
```

---

### Task 8: Integrate One Dossier Into Web Orchestration

**Files:**

- Modify: `src/stock_ts/web.py:9663`
- Modify: `tests/test_web_stock_dossier.py`
- Modify: `tests/test_web_module_decisions.py`

- [ ] **Step 1: Write failing integration tests**

```python
def test_real_stock_orchestration_builds_one_dossier() -> None:
    source = inspect.getsource(web._render_compact_stock_module)

    assert "build_professional_stock_dossier" in source
    assert source.count("render_stock_workspace(") == 1
    assert "legacy_trade_plan =" not in source


def test_stock_page_has_no_duplicate_primary_trade_conclusion() -> None:
    stock_html = _workspace(_sample_html(stock_code="603278"), "stock")

    assert stock_html.count('data-primary-stock-verdict="true"') == 1
    assert stock_html.count("投委会结论") == 1
    assert "多角色分析方法" not in stock_html.split("诊断底稿", 1)[0]
```

- [ ] **Step 2: Run tests and verify RED**

Expected: `web.py` still builds `StockResearchMemo` plus `legacy_trade_plan`.

- [ ] **Step 3: Build the dossier from existing typed inputs**

In `_render_compact_stock_module`, find the current holding, construct `ResearchInputQuality`, pass `stock_raw`, `technical`, `event_radar`, holding, sector context, and quality to `build_professional_stock_dossier`, then render it once.

- [ ] **Step 4: Remove duplicated primary output**

Delete the `legacy_trade_plan` top-level composition. Preserve useful deep tables only in the renderer's supporting-evidence slot. Ensure no second action, score-led conclusion, or generic multi-role block appears before the evidence drawer.

- [ ] **Step 5: Run integration tests and commit**

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_web_stock_dossier.py tests/test_web_module_decisions.py tests/test_web_data_accuracy.py
.venv/bin/ruff check src/stock_ts/web.py tests/test_web_stock_dossier.py tests/test_web_module_decisions.py
git add src/stock_ts/web.py tests/test_web_stock_dossier.py tests/test_web_module_decisions.py
git commit -m "[个股研究] 统一网页个股决策链"
```

---

### Task 9: Add The Decision-Rail Visual System

**Files:**

- Modify: `src/stock_ts/webapp/styles.py`
- Modify: `tests/test_web_stock_dossier.py`

- [ ] **Step 1: Add failing semantic-style tests**

```python
def test_dossier_styles_define_desktop_mobile_and_reduced_motion() -> None:
    from stock_ts.webapp.styles import CSS

    assert ".stock-dossier-grid" in CSS
    assert ".decision-rail-step" in CSS
    assert ".risk-register" in CSS
    assert "font-variant-numeric:tabular-nums" in CSS
    assert "@media (max-width: 760px)" in CSS
    assert "prefers-reduced-motion" in CSS
```

- [ ] **Step 2: Run tests and verify RED**

Expected: new dossier selectors do not exist.

- [ ] **Step 3: Implement the visual tokens and layout**

Reuse the existing StockTs variables. Add:

```css
.stock-dossier-grid { display:grid; grid-template-columns:minmax(0,1.25fr) minmax(300px,.75fr); gap:16px; }
.decision-rail { position:relative; display:grid; gap:0; }
.decision-rail-step { display:grid; grid-template-columns:112px 1fr; gap:14px; padding:14px 0; border-bottom:1px solid var(--line); }
.decision-rail-step strong, .dossier-price { font-variant-numeric:tabular-nums; }
.risk-register { display:grid; gap:10px; }
```

Use one restrained reveal animation for the decision rail, disable it under reduced motion, and collapse the grid to one column at 760px. Do not introduce a new font or unrelated color theme.

- [ ] **Step 4: Run tests and commit**

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_web_stock_dossier.py tests/test_web_design_guide_shell.py
.venv/bin/ruff check src tests
git add src/stock_ts/webapp/styles.py tests/test_web_stock_dossier.py
git commit -m "[个股研究] 完善决策轨道响应式视觉"
```

---

### Task 10: Verify The Real Snapshot And Close Quality Gates

**Files:**

- Modify: `docs/product/module-stock-analysis-design.md`
- Modify: `docs/superpowers/professional-stock-dossier/TODO.md`
- Modify: `docs/superpowers/professional-stock-dossier/test.md`
- Modify: `docs/superpowers/professional-stock-dossier/review.md`
- Modify: `docs/superpowers/professional-stock-dossier/handoff.md`

- [ ] **Step 1: Run the focused suite**

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q \
  tests/test_stock_dossier.py \
  tests/test_web_stock_dossier.py \
  tests/test_stock_research_memo.py \
  tests/test_web_stock_research_workspace.py \
  tests/test_web_module_decisions.py \
  tests/test_web_data_accuracy.py
```

Expected: all focused dossier and stock-workspace tests pass.

- [ ] **Step 2: Run the real `603278` smoke test**

Build the page from `data/imports/tdx_snapshots.json` and assert all of these phrases or equivalent typed fields:

```text
亏损
PE 失去解释力
来源 PB 0.18x
反算 1.77x
口径冲突
股权质押
65.72%
20日
60日高点
仓位上限
禁止动作
```

The smoke test must not mutate the snapshot.

- [ ] **Step 3: Run full lint and full tests**

```bash
make lint
PYTHONPATH=src .venv/bin/python -m pytest -q
```

Expected: Ruff passes. Compare full pytest results with the documented six-failure baseline and investigate any new failure before proceeding.

- [ ] **Step 4: Run a local HTTP and responsive smoke**

Start the app on a temporary port with authentication disabled and the real snapshot. Verify HTTP 200, the dossier markers, desktop layout, mobile stacking, keyboard focus, and no horizontal overflow. Stop the temporary process and confirm the port is released.

- [ ] **Step 5: Perform AI Review**

Review `main..HEAD` for:

- false precision or unsupported financial claims;
- negative-PE and PB-conflict handling;
- source-safe capital wording;
- stale-data and high-event-risk overrides;
- duplicated verdicts;
- private data leakage;
- desktop/mobile regressions;
- missing tests.

Write findings and decision to `review.md`. Resolve every P0/P1 finding before release.

- [ ] **Step 6: Update requirement evidence**

Write exact commands, counts, HTTP evidence, real-snapshot evidence, review outcome, known baseline failures, and deployment status into `test.md` and `handoff.md`. Check completed TODO items only after evidence exists.

- [ ] **Step 7: Commit the quality record**

```bash
git add docs/product/module-stock-analysis-design.md docs/superpowers/professional-stock-dossier
git commit -m "[个股研究] 记录专业档案验证结果"
```

- [ ] **Step 8: Merge, push, deploy, and verify**

After the branch is reviewed:

1. fast-forward or merge it into `main` in the clean integration worktree;
2. push `origin/main` only after explicit repository verification;
3. create a server-side rollback archive;
4. align tracked server source to the exact `main` commit while preserving `.env`, `.secrets`, data, accounts, holdings, reports, Nginx, services, and timers;
5. restart `stock-ts.service`;
6. verify server HEAD, tracked cleanliness, source hashes, service health, public 303 authentication redirect, login 200/title, and dossier markers through an authenticated or temporary protected smoke path.

Record the final commit, backup path, PID transition, source hashes, and public verification in `handoff.md` without committing secrets.

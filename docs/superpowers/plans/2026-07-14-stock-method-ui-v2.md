# Stock Method UI V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a stock-research decision chain that connects a falsifiable thesis, weighted evidence, valuation and expectation gaps, scenarios, price conditions, and position actions in one concise responsive page.

**Architecture:** Extend `ProfessionalStockDossier` with immutable thesis and evidence-assessment contracts, and keep all inference in `research/stock_dossier.py`. `webapp/stock_workspace.py` remains a pure renderer; the legacy raw analysis stays inside one closed evidence ledger. Existing freshness gates, holding isolation, providers, and server configuration remain unchanged.

**Tech Stack:** Python 3.11 dataclasses, deterministic research rules, server-rendered HTML, CSS, pytest, ruff.

---

## File Map

- Modify `src/stock_ts/research/stock_dossier_models.py`: define thesis and weighted-evidence contracts.
- Modify `src/stock_ts/research/stock_dossier.py`: build the thesis, causal chain, evidence directions, and research-linked actions.
- Modify `src/stock_ts/research/__init__.py`: export the new public model types.
- Modify `src/stock_ts/webapp/stock_workspace.py`: render the four-block first screen and evidence-first body.
- Modify `src/stock_ts/webapp/styles.py`: add the thesis spine, evidence matrix, and responsive layout.
- Modify `src/stock_ts/web.py`: remove duplicated method narration from the raw evidence drawer.
- Modify `tests/test_stock_dossier.py`: specify research-method behavior.
- Modify `tests/test_web_stock_dossier.py`: specify page order, density, and semantics.
- Modify the directly affected Web contract tests: replace old section-name assertions with the V2 decision-chain contract.
- Update `docs/superpowers/stock-method-ui-v2/TODO.md`, `test.md`, and `handoff.md`: record completion and fresh evidence.

### Task 1: Define the research-thesis contracts

**Files:**
- Modify: `src/stock_ts/research/stock_dossier_models.py`
- Modify: `src/stock_ts/research/__init__.py`
- Test: `tests/test_stock_dossier.py`

- [ ] **Step 1: Write the failing contract test**

```python
def test_dossier_exposes_falsifiable_thesis_and_weighted_evidence() -> None:
    dossier = _build(_raw_stock(financial=True, events=True))

    assert dossier.thesis.headline
    assert dossier.thesis.core_conflict
    assert len(dossier.thesis.causal_chain) == 3
    assert dossier.thesis.expectation_gap
    assert dossier.thesis.valuation_fit
    assert dossier.thesis.key_unknown
    assert dossier.thesis.falsifier
    assert [item.dimension for item in dossier.weighted_evidence] == [
        "盈利质量", "估值与预期差", "事件与治理", "行业位置", "资金与价格"
    ]
    assert all(item.direction in {"支持", "中性", "反证", "未知"} for item in dossier.weighted_evidence)
```

- [ ] **Step 2: Run the test and verify RED**

Run: `.venv/bin/pytest tests/test_stock_dossier.py::test_dossier_exposes_falsifiable_thesis_and_weighted_evidence -q`

Expected: FAIL because `ProfessionalStockDossier` has no `thesis` field.

- [ ] **Step 3: Add immutable contracts and dossier fields**

```python
@dataclass(frozen=True)
class ThesisFramework:
    headline: str
    core_conflict: str
    causal_chain: tuple[str, str, str]
    expectation_gap: str
    valuation_fit: str
    catalyst_window: str
    key_unknown: str
    falsifier: str


@dataclass(frozen=True)
class WeightedEvidence:
    dimension: str
    importance: str
    direction: str
    fact: str
    inference: str
    unknown: str
```

Add `thesis: ThesisFramework` and `weighted_evidence: tuple[WeightedEvidence, ...]` to `ProfessionalStockDossier`, then export both types from `research/__init__.py`.

- [ ] **Step 4: Add temporary minimal construction and verify GREEN**

Construct all required fields in `build_professional_stock_dossier` with honest degraded values such as `"待建立研究假设"` and `"未知"`; do not infer behavior yet.

Run: `.venv/bin/pytest tests/test_stock_dossier.py::test_dossier_exposes_falsifiable_thesis_and_weighted_evidence -q`

Expected: PASS.

- [ ] **Step 5: Commit the model contract**

```bash
git add src/stock_ts/research/stock_dossier_models.py src/stock_ts/research/__init__.py src/stock_ts/research/stock_dossier.py tests/test_stock_dossier.py
git commit -m "[个股研究] 建立研究假设与证据权重契约"
```

### Task 2: Generate a stock-specific thesis and evidence weights

**Files:**
- Modify: `src/stock_ts/research/stock_dossier.py`
- Test: `tests/test_stock_dossier.py`

- [ ] **Step 1: Write failing loss-making and missing-data tests**

```python
def test_loss_making_stock_links_profit_repair_event_risk_and_price_confirmation() -> None:
    dossier = _build(_raw_stock(
        pe_ttm=-79.96,
        fundamental_metrics={"net_profit": -24557.6, "operating_cash_flow": 29811.0},
        news_items=[NewsItem("2026-05-25", "fixture", "控股股东累计质押占其持股65.72%", "风险")],
    ))

    assert "盈利" in dossier.thesis.core_conflict
    assert "质押" in " ".join(dossier.thesis.causal_chain)
    assert "PE" in dossier.thesis.valuation_fit
    assert "不可量化" in dossier.thesis.expectation_gap
    assert next(item for item in dossier.weighted_evidence if item.dimension == "盈利质量").direction == "反证"
    assert next(item for item in dossier.weighted_evidence if item.dimension == "事件与治理").direction == "反证"


def test_missing_fundamentals_stay_unknown_instead_of_becoming_technical_support() -> None:
    dossier = _build(_raw_stock(financial=False, events=False))

    earnings = next(item for item in dossier.weighted_evidence if item.dimension == "盈利质量")
    assert earnings.direction == "未知"
    assert "补" in earnings.unknown
    assert "技术" not in dossier.thesis.headline or "待验证" in dossier.thesis.headline
```

- [ ] **Step 2: Run both tests and verify RED**

Run: `.venv/bin/pytest tests/test_stock_dossier.py -k "loss_making_stock_links or missing_fundamentals_stay" -q`

Expected: FAIL because the temporary contract does not use stock-specific evidence.

- [ ] **Step 3: Implement deterministic thesis builders**

Add focused private functions with these signatures:

```python
def _thesis_framework(
    raw: StockRawData,
    *,
    financial: DiagnosticBlock,
    valuation: DiagnosticBlock,
    technical: DiagnosticBlock,
    capital: DiagnosticBlock,
    risks: tuple[RiskItem, ...],
    sector_context: str,
    paused: bool,
    resistance: float,
    invalid_line: float,
) -> ThesisFramework: ...


def _weighted_evidence(
    *,
    financial: DiagnosticBlock,
    valuation: DiagnosticBlock,
    event: DiagnosticBlock,
    capital: DiagnosticBlock,
    technical: DiagnosticBlock,
    risks: tuple[RiskItem, ...],
    sector_context: str,
) -> tuple[WeightedEvidence, ...]: ...
```

Rules:

- Financial missing -> `未知`; loss or explicit financial risk -> `反证`; evidence of multi-period improvement with cash support -> `支持`; otherwise `中性`.
- Valuation conflict, invalid PE, or no comparison -> `未知` or `反证`; comparable valuation without quality support remains `中性`.
- Critical or high event -> `反证`; no usable event data -> `未知`; otherwise `中性`.
- Sector text missing -> `未知`; because the input is not yet structured ranking, non-empty context remains `中性`, never automatic support.
- Price/capital can support execution timing but the inference must explicitly state that they do not prove company quality.
- With no consensus forecast fields, expectation gap always says it is not quantifiable and names the next evidence needed.

- [ ] **Step 4: Run the full dossier tests and verify GREEN**

Run: `.venv/bin/pytest tests/test_stock_dossier.py -q`

Expected: all dossier tests pass.

- [ ] **Step 5: Commit the research rules**

```bash
git add src/stock_ts/research/stock_dossier.py tests/test_stock_dossier.py
git commit -m "[个股研究] 形成可证伪研究假设与证据权重"
```

### Task 3: Link research conditions to position actions

**Files:**
- Modify: `src/stock_ts/research/stock_dossier.py`
- Test: `tests/test_stock_dossier.py`

- [ ] **Step 1: Write failing action-boundary tests**

```python
def test_entry_requires_research_and_price_confirmation() -> None:
    dossier = _build(_raw_stock(financial=True, events=True))
    assert "经营" in dossier.position.entry_trigger or "事件" in dossier.position.entry_trigger
    assert "10.80" in dossier.position.entry_trigger
    assert "9.40" in dossier.position.invalidation
    assert any(word in dossier.position.invalidation for word in ("盈利", "事件", "论点"))


def test_loss_and_high_event_risk_cannot_be_overridden_by_breakout() -> None:
    dossier = _build(_raw_stock(
        fundamental_metrics={"net_profit": -10.0},
        news_items=[NewsItem("2026-07-10", "fixture", "收到立案调查通知", "监管立案")],
    ))
    assert dossier.position.position_cap == "0%"
    assert "风险" in dossier.position.entry_trigger or "暂停" in dossier.position.entry_trigger
    assert "站稳 10.80" not in dossier.position.entry_trigger.split("；")[0]
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `.venv/bin/pytest tests/test_stock_dossier.py -k "entry_requires_research or cannot_be_overridden" -q`

Expected: FAIL because the current entry trigger is price-only.

- [ ] **Step 3: Pass thesis confirmation and falsifier into action generation**

Change `_position_guidance` and `_decision_steps` to receive the built `ThesisFramework` and risk state. Generate five conditions in this order:

```python
(
    DecisionStep("当前判断", "current", stance, action),
    DecisionStep("研究转强", "upgrade", research_confirmation, "允许进入价格确认"),
    DecisionStep("价格确认", "confirm", f"站稳 {technical.resistance:.2f} 且量能确认", "才允许增加风险"),
    DecisionStep("降级条件", "downgrade", downgrade_condition, "降低观察或持仓等级"),
    DecisionStep("论点失效", "invalid", thesis.falsifier, "终止当前研究假设"),
)
```

For critical/high risk plus loss, keep position cap at zero and make risk repair the first prerequisite. For stale data, retain the existing zero-confidence and no-old-price behavior exactly.

- [ ] **Step 4: Verify dossier and stale-gate tests**

Run: `.venv/bin/pytest tests/test_stock_dossier.py -q`

Expected: all pass, including stale quote tests.

- [ ] **Step 5: Commit the action linkage**

```bash
git add src/stock_ts/research/stock_dossier.py tests/test_stock_dossier.py
git commit -m "[个股研究] 贯通研究确认与仓位动作"
```

### Task 4: Rebuild the stock page around the decision chain

**Files:**
- Modify: `src/stock_ts/webapp/stock_workspace.py`
- Modify: `src/stock_ts/web.py`
- Test: `tests/test_web_stock_dossier.py`
- Test: `tests/test_web_module_decisions.py`
- Test: `tests/test_agentic_stock_method.py`
- Test: `tests/test_web_layout.py`
- Test: `tests/test_web_professional_modules.py`
- Test: `tests/test_web_compact_mode.py`

- [ ] **Step 1: Replace old layout assertions with a failing V2 contract**

```python
def test_workspace_reads_as_thesis_conditions_execution_evidence_and_scenarios() -> None:
    html = render_stock_workspace(_dossier())
    labels = ["投资判断", "核心矛盾", "决策条件", "执行边界", "论点链", "关键证据", "风险反证", "三情景", "证据账本"]
    assert all(label in html for label in labels)
    assert [html.index(label) for label in labels] == sorted(html.index(label) for label in labels)
    assert "诊断底稿" not in html.split("证据账本", 1)[0]
    assert "多角色分析方法" not in html
    assert html.count('data-primary-stock-verdict="true"') == 1
```

Update `_dossier()` with explicit `ThesisFramework` and `WeightedEvidence` fixtures. Remove assertions that require the old names `五步决策轨道`, `仓位与执行边界`, and `三种情景`; retain checks for all trigger, risk, evidence-ledger, and no-upside-probability semantics.

- [ ] **Step 2: Run the page contract test and verify RED**

Run: `.venv/bin/pytest tests/test_web_stock_dossier.py::test_workspace_reads_as_thesis_conditions_execution_evidence_and_scenarios -q`

Expected: FAIL because the V2 headings and thesis spine are absent.

- [ ] **Step 3: Implement the pure HTML renderer**

Render sections in this exact order:

```python
identity -> investment_judgement -> identity_html -> decision_conditions
-> execution_boundary -> thesis_spine -> weighted_evidence
-> top_three_risks -> three_scenarios -> closed_evidence_ledger
```

The investment judgment contains `headline`, `core_conflict`, grade, confidence, horizon, and next review. The thesis spine renders the three `causal_chain` items. Each evidence row renders importance, direction, fact, inference, and unknown. Move full diagnostic cards into the closed ledger. Keep the prohibited action visible in the execution boundary.

In `web.py`, remove `_render_stock_method_chain(...)` from `_render_stock_simple_analysis_content`; preserve raw dimension rows, data-block status, source, and quality warning in the evidence ledger.

- [ ] **Step 4: Run directly affected Web tests and make them GREEN**

Run:

```bash
.venv/bin/pytest \
  tests/test_web_stock_dossier.py \
  tests/test_web_module_decisions.py \
  tests/test_agentic_stock_method.py \
  tests/test_web_layout.py \
  tests/test_web_professional_modules.py \
  tests/test_web_compact_mode.py -q
```

Expected: all selected tests pass; no primary conclusion is duplicated.

- [ ] **Step 5: Commit the page structure**

```bash
git add src/stock_ts/webapp/stock_workspace.py src/stock_ts/web.py tests/test_web_stock_dossier.py tests/test_web_module_decisions.py tests/test_agentic_stock_method.py tests/test_web_layout.py tests/test_web_professional_modules.py tests/test_web_compact_mode.py
git commit -m "[界面设计] 重排个股研究决策链"
```

### Task 5: Add the thesis-spine visual system and responsive behavior

**Files:**
- Modify: `src/stock_ts/webapp/styles.py`
- Test: `tests/test_web_stock_dossier.py`

- [ ] **Step 1: Write the failing style contract**

```python
def test_v2_styles_define_thesis_spine_evidence_directions_and_mobile_stack() -> None:
    assert ".thesis-spine" in CSS
    assert ".weighted-evidence-row" in CSS
    assert '[data-direction="反证"]' in CSS
    assert '[data-direction="未知"]' in CSS
    mobile = CSS.split("@media (max-width: 760px)", 1)[1]
    assert ".thesis-spine" in mobile
    assert "grid-template-columns:1fr" in mobile
    assert "prefers-reduced-motion" in CSS
```

- [ ] **Step 2: Run the style test and verify RED**

Run: `.venv/bin/pytest tests/test_web_stock_dossier.py::test_v2_styles_define_thesis_spine_evidence_directions_and_mobile_stack -q`

Expected: FAIL because the new selectors are absent.

- [ ] **Step 3: Implement the page-specific visual system**

Use existing tokens only: deep blue judgment board, gold condition markers, green support, red counter-evidence, and muted unknown states. The thesis spine is a three-column directional track on desktop and a one-column vertical track below 760px. Evidence rows use a stable label column and flexible content column; at mobile width all content stacks without fixed widths. Add visible `:focus-visible` to the evidence summary and keep `prefers-reduced-motion` disabling the reveal animation.

- [ ] **Step 4: Run the stock page tests and verify GREEN**

Run: `.venv/bin/pytest tests/test_web_stock_dossier.py -q`

Expected: all pass.

- [ ] **Step 5: Commit the responsive UI**

```bash
git add src/stock_ts/webapp/styles.py tests/test_web_stock_dossier.py
git commit -m "[界面设计] 建立个股论点脊柱与证据矩阵"
```

### Task 6: Verify, review, and record the delivery state

**Files:**
- Modify: `docs/superpowers/stock-method-ui-v2/TODO.md`
- Modify: `docs/superpowers/stock-method-ui-v2/test.md`
- Modify: `docs/superpowers/stock-method-ui-v2/handoff.md`

- [ ] **Step 1: Run focused research and Web verification**

```bash
.venv/bin/pytest tests/test_stock_dossier.py tests/test_web_stock_dossier.py -q
.venv/bin/pytest tests/test_web_*.py -q
```

Expected: zero failures.

- [ ] **Step 2: Run lint and the full repository suite**

```bash
make lint
.venv/bin/pytest -q
```

Expected: lint passes. Record the exact pytest count; if the known `tests/test_daily_pipeline.py` baseline failures remain, verify that no new failure belongs to this change and record them without calling the full suite green.

- [ ] **Step 3: Start the local app and inspect real output**

```bash
PYTHONPATH=src .venv/bin/python -m stock_ts.web
```

Open `http://127.0.0.1:8501/?code=603278&provider=tdx-snapshot#stock`. Check desktop and 390px mobile widths, first-screen order, closed evidence ledger, keyboard focus, and horizontal overflow. Capture screenshots outside the repository if needed.

- [ ] **Step 4: Perform code review and fix findings under TDD**

Review the diff for stale-gate regression, overclaiming, evidence-direction errors, HTML escaping, duplicated conclusions, mobile overflow, and unrelated data/config changes. For each behavior bug, add a failing regression test before the fix.

- [ ] **Step 5: Update requirement evidence**

Record exact commands, counts, browser routes, known failures, changed files, and remaining deployment status in `test.md` and `handoff.md`. Mark only completed TODO items.

- [ ] **Step 6: Commit the verified delivery record**

```bash
git add docs/superpowers/stock-method-ui-v2
git commit -m "[交付验收] 完成个股研究决策链验收"
```

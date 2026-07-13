# Data Readiness Command Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the flat data-center status table into a deterministic recovery command center that explains what is blocked, what to restore first, which modules are affected, and how to verify recovery.

**Architecture:** Add a focused dossier model and builder under `stock_ts.research`, then render it through a dedicated `webapp` module. `web.py` remains responsible for collecting existing `DataCenterRow` values and the existing refresh form; the new builder performs deterministic presentation orchestration without provider calls.

**Tech Stack:** Python 3.9+, frozen dataclasses, structural typing with `Protocol`, server-rendered HTML, CSS grid, native `details/summary`, pytest, Ruff, in-app browser smoke.

---

### Task 1: Establish The Data Readiness Dossier Contract

**Files:**
- Create: `src/stock_ts/research/data_center_dossier_models.py`
- Create: `src/stock_ts/research/data_center_dossier.py`
- Create: `tests/test_data_center_dossier.py`

- [ ] **Step 1: Write blocked-state and preservation tests**

Define a local row fixture with the same public fields as `DataCenterRow`, then assert:

```python
dossier = build_data_center_dossier(
    status="影响分析",
    updated_at="2026-07-11 11:32:33 北京时间",
    rows=rows,
)

assert dossier.gate.state == "影响分析"
assert dossier.gate.action == "停止强结论，按恢复顺序补齐数据"
assert dossier.gate.blocked_count == 2
assert [item.category for item in dossier.recovery_steps] == ["K线行情", "新闻舆情", "全链路校验"]
assert len(dossier.ledger) == len(rows)
```

Add separate tests for warning-only, all-ready, and empty input. The empty input must return a blocked gate and one recovery step explaining `数据域清单为空`.

- [ ] **Step 2: Run the tests and confirm RED**

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q tests/test_data_center_dossier.py
```

Expected: collection fails because the dossier modules do not exist.

- [ ] **Step 3: Implement immutable models**

Create frozen dataclasses:

```python
@dataclass(frozen=True)
class DataReadinessGate:
    state: str
    action: str
    thesis: str
    blocked_count: int
    warning_count: int
    ready_count: int
    total_count: int
    next_step: str

@dataclass(frozen=True)
class DataRecoveryStep:
    priority: int
    category: str
    status: str
    severity: str
    issue: str
    consequence: str
    verification: str

@dataclass(frozen=True)
class DataImpactLane:
    key: str
    label: str
    status: str
    affected_domains: tuple[str, ...]
    guidance: str

@dataclass(frozen=True)
class DataLedgerEntry:
    category: str
    channel: str
    status: str
    latest_at: str
    coverage: str
    missing: str
    impact: str
    level: str

@dataclass(frozen=True)
class DataCenterDossier:
    gate: DataReadinessGate
    recovery_steps: tuple[DataRecoveryStep, ...]
    impacts: tuple[DataImpactLane, ...]
    ledger: tuple[DataLedgerEntry, ...]
    updated_at: str
```

- [ ] **Step 4: Implement the builder**

Use a `Protocol` for incoming row fields, copy every row into the ledger, sort only recovery steps by explicit category rank plus severity and original index, and derive four impact lanes from constant domain mappings. Do not calculate a numeric quality score.

- [ ] **Step 5: Run tests and confirm GREEN**

Run the Task 1 command. Expected: all dossier tests pass.

- [ ] **Step 6: Commit the contract**

```bash
git add src/stock_ts/research/data_center_dossier_models.py src/stock_ts/research/data_center_dossier.py tests/test_data_center_dossier.py
git commit -m '[数据中台] 建立数据恢复档案契约'
```

### Task 2: Render The Recovery Command Center

**Files:**
- Create: `src/stock_ts/webapp/data_center_workspace.py`
- Create: `tests/test_web_data_center_workspace.py`
- Modify: `src/stock_ts/web.py`
- Modify: `tests/test_web_module_decisions.py`

- [ ] **Step 1: Write gate-first rendering tests**

Build a dossier with blocked, warning, and ready rows and assert:

```python
html = render_data_center_workspace(dossier, refresh_html="<form>refresh</form>")

assert html.count('data-primary-data-verdict="true"') == 1
assert html.index("数据就绪闸门") < html.index("恢复运行轨道")
assert html.index("恢复运行轨道") < html.index("模块影响面")
assert "停止强结论，按恢复顺序补齐数据" in html
assert "01" in html and "全链路校验" in html
assert "每日大盘" in html and "我的持仓" in html
assert '<details class="data-source-ledger"' in html
assert "查看 3 个数据域的完整来源账本" in html
assert "<form>refresh</form>" in html
```

Add an escaping test using channel `<script>alert(1)</script>` and missing text `<b>缺口</b>`.

- [ ] **Step 2: Run rendering tests and confirm RED**

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q tests/test_web_data_center_workspace.py
```

Expected: collection fails because the renderer does not exist.

- [ ] **Step 3: Implement the dedicated renderer**

Render, in order:

1. `.data-readiness-brief[data-primary-data-verdict="true"]`;
2. `.data-operations-grid` containing `.data-recovery-rail` and `.data-impact-grid`;
3. default-closed `details.data-source-ledger` with every ledger entry.

Use `html.escape` for every dossier string. The renderer accepts already-rendered trusted `refresh_html` only for the existing refresh form.

- [ ] **Step 4: Delegate from `web.py`**

Import the builder and renderer, replace `_render_data_center_panel` internals with:

```python
dossier = build_data_center_dossier(
    status=data_center.status,
    updated_at=data_center.updated_at,
    rows=data_center.rows,
)
return render_data_center_workspace(
    dossier,
    refresh_html=_render_module_refresh_tools(...),
)
```

Remove the obsolete `_simple_data_center_*` helpers. Keep `_render_data_center_summary` and the existing `DataCenterRow` calculations unchanged.

- [ ] **Step 5: Update legacy expectations**

Replace the old `test_global_data_center_is_simple_status_list` expectation with an action-first contract. It must allow source-channel and coverage details only inside the collapsed ledger and continue to reject credentials or automatic repair claims.

- [ ] **Step 6: Run focused tests and confirm GREEN**

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q \
  tests/test_web_data_center_workspace.py \
  tests/test_web_module_decisions.py \
  tests/test_web_layout.py \
  tests/test_web_data_accuracy.py
```

Expected: zero failures.

- [ ] **Step 7: Commit the workspace**

```bash
git add src/stock_ts/web.py src/stock_ts/webapp/data_center_workspace.py tests/test_web_data_center_workspace.py tests/test_web_module_decisions.py
git commit -m '[数据中台] 构建影响优先恢复指挥台'
```

### Task 3: Add The Operations-Rail Visual System

**Files:**
- Modify: `src/stock_ts/webapp/styles.py`
- Modify: `tests/test_web_design_guide_shell.py`

- [ ] **Step 1: Write CSS contract tests**

Assert the stylesheet contains:

```python
for selector in [
    ".data-readiness-brief",
    ".data-recovery-rail",
    ".data-recovery-step::before",
    ".data-impact-grid",
    ".data-source-ledger",
    ".data-ledger-card",
]:
    assert selector in CSS

mobile = CSS.split("@media (max-width:680px)")[-1]
assert ".data-operations-grid" in mobile
assert "grid-template-columns:1fr" in mobile.replace(" ", "")
```

- [ ] **Step 2: Run the CSS test and confirm RED**

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q tests/test_web_design_guide_shell.py
```

Expected: failure because the command-center selectors do not exist.

- [ ] **Step 3: Implement desktop styling**

Use a restrained navy gate, one wine-red blocked edge, a numbered vertical recovery rail, four compact impact lanes, and an ivory source ledger. Keep focus-visible treatment on the ledger summary.

- [ ] **Step 4: Implement mobile styling**

At `max-width:680px`, make the gate, metrics, operations grid, and impact lanes single-column. Hide the desktop ledger table header and render each ledger entry as a stacked card without horizontal overflow.

- [ ] **Step 5: Run style and Web regressions**

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q \
  tests/test_web_design_guide_shell.py \
  tests/test_web_data_center_workspace.py \
  tests/test_web_module_decisions.py \
  tests/test_web_compact_mode.py
```

Expected: zero failures.

- [ ] **Step 6: Commit the visual system**

```bash
git add src/stock_ts/webapp/styles.py tests/test_web_design_guide_shell.py
git commit -m '[界面设计] 建立数据恢复运行轨道'
```

### Task 4: Verify, Review, Integrate, And Deploy

**Files:**
- Modify: `docs/product/stock-analysis-agent-design-guide.md`
- Modify: `docs/superpowers/data-readiness-command-center/TODO.md`
- Modify: `docs/superpowers/data-readiness-command-center/test.md`
- Modify: `docs/superpowers/data-readiness-command-center/review.md`

- [ ] **Step 1: Perform responsive browser smoke**

At `1440x1000` and `390x844`, verify no horizontal overflow, one primary data verdict, default-closed source ledger, complete ledger count, readable recovery steps, and an active-module heading inside the mobile first screen.

- [ ] **Step 2: Run static and focused verification**

```bash
make lint
git diff --check
/Users/fangjie/Documents/StockTs/.venv/bin/python -m compileall -q src/stock_ts
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q \
  tests/test_data_center_dossier.py \
  tests/test_web_data_center_workspace.py \
  tests/test_web_design_guide_shell.py \
  tests/test_web_module_decisions.py \
  tests/test_web_layout.py \
  tests/test_web_data_accuracy.py
```

Expected: static checks and focused tests pass.

- [ ] **Step 3: Run Python 3.9 and full suite**

```bash
PYTHONPATH=src /Users/fangjie/opt/anaconda3/bin/python3.9 -m pytest -q \
  tests/test_data_center_dossier.py tests/test_web_data_center_workspace.py
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q
```

Expected: contract tests pass; full suite has no failure outside the five known daily-pipeline baseline failures.

- [ ] **Step 4: Review and record evidence**

Use `ai-review` against `main`, record findings and residual risks in `review.md`, and write exact command outputs and viewport measurements to `test.md`.

- [ ] **Step 5: Commit evidence**

```bash
git add docs/product/stock-analysis-agent-design-guide.md docs/superpowers/data-readiness-command-center docs/superpowers/README.md
git commit -m '[交付验收] 完成数据恢复指挥台验收'
```

- [ ] **Step 6: Fast-forward and deploy**

Fast-forward local `main`, push GitHub `main`, deploy by Git bundle to `/opt/stock-ts`, compile/import-check, restart only `stock-ts.service`, and verify local/public health plus `stock-ts-signal-desk.service` and Nginx remain active.

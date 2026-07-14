# StockTS Three-Second Essence V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the market, portfolio, stock, and opportunity workspaces understandable in three seconds by showing only one verdict, one action, one primary risk, and no more than three focus items before a single closed evidence drawer.

**Architecture:** Keep all research models, rankings, stale-data gates, authentication, and iWencai routing unchanged. Restructure only the five HTML renderers and add a small shared CSS layer so each workspace has a decision-first surface and one audit drawer containing the current professional detail.

**Tech Stack:** Python 3.11, stdlib HTML rendering, pytest, BeautifulSoup, existing CSS string renderer, local HTTP and responsive browser verification.

---

### Task 1: Lock The Three-Second Contract

**Files:**
- Create: `tests/test_web_three_second_essence.py`
- Modify: `tests/test_web_iwencai_four_workspaces.py`

- [ ] **Step 1: Write failing full-page density tests**

```python
def test_four_workspaces_have_one_primary_verdict_and_one_closed_detail_drawer() -> None:
    soup = BeautifulSoup(_sample_html(), "html.parser")
    selectors = {
        "market": ("[data-primary-market-verdict]", "details.market-evidence"),
        "portfolio": ("[data-primary-portfolio-verdict]", "details.portfolio-evidence"),
        "stock": ("[data-primary-stock-verdict]", "details.stock-evidence"),
        "opportunity": ("[data-primary-opportunity-verdict]", "details.opportunity-evidence"),
    }
    for key, (verdict_selector, detail_selector) in selectors.items():
        pane = soup.select_one(f'.workspace-pane[data-workspace="{key}"]')
        assert pane is not None
        assert len(pane.select(verdict_selector)) == 1
        details = pane.select(detail_selector)
        assert len(details) == 1
        assert "open" not in details[0].attrs
```

- [ ] **Step 2: Write failing renderer caps and hidden-detail tests**

```python
def test_stock_front_surface_has_at_most_three_core_facts() -> None:
    soup = BeautifulSoup(_stock_html(), "html.parser")
    assert len(soup.select("[data-core-stock-fact]")) <= 3
    drawer = soup.select_one("details.stock-evidence")
    assert drawer is not None
    assert drawer.select(".decision-rail, .dossier-diagnostic-grid, .dossier-scenario-grid")

def test_market_process_modules_are_inside_closed_detail() -> None:
    soup = BeautifulSoup(_market_html(), "html.parser")
    drawer = soup.select_one("details.market-evidence")
    assert drawer is not None
    for selector in (".market-decision-rail", ".research-scenario-grid", ".market-dimension-grid"):
        assert drawer.select_one(selector) is not None
```

- [ ] **Step 3: Write failing iWencai disclosure test**

```python
def test_iwencai_console_is_closed_until_requested() -> None:
    html = render_iwencai_research_console(module="stock", status="configured")
    soup = BeautifulSoup(html, "html.parser")
    drawer = soup.select_one("details.iwencai-research-disclosure")
    assert drawer is not None
    assert "open" not in drawer.attrs
    assert "问财核查 · 按需展开" in drawer.get_text(" ", strip=True)
    assert drawer.select_one("form[data-iwencai-form]") is not None
```

- [ ] **Step 4: Run the tests and verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest \
  tests/test_web_three_second_essence.py \
  tests/test_web_iwencai_four_workspaces.py -q
```

Expected: failures because the current market process, stock diagnostics, and iWencai controls are visible before a drawer is opened.

### Task 2: Collapse iWencai Into One Optional Row

**Files:**
- Modify: `src/stock_ts/webapp/research_console.py`
- Modify: `src/stock_ts/webapp/styles.py`
- Test: `tests/test_web_iwencai_four_workspaces.py`
- Test: `tests/test_web_three_second_essence.py`

- [ ] **Step 1: Wrap the existing console in a closed details element**

```python
console_html = f"""
  <section class="iwencai-research-console" data-iwencai-research="true"
    data-iwencai-module="{escape(module)}" data-stock-code="{escape(code, quote=True)}"
    data-stock-name="{escape(name, quote=True)}" data-sector="{escape(sector, quote=True)}"
    data-local-as-of="{escape(local_as_of, quote=True)}"
    data-config-status="{escape(status, quote=True)}">
    <div class="iwencai-question-rail">{suggestions}</div>
    <form class="{form_class}" data-iwencai-form>
      {context_select}
      <textarea id="{question_id}" name="question" maxlength="200"
        rows="2" required data-iwencai-input{disabled}></textarea>
      <button type="submit" data-iwencai-submit{disabled}>核查问财</button>
    </form>
    <p class="iwencai-console-state" data-iwencai-state>{state_message}</p>
    <div class="iwencai-research-result" data-iwencai-result hidden
      aria-live="polite"></div>
  </section>"""
return f"""
  <details class="iwencai-research-disclosure" data-iwencai-disclosure>
    <summary><span>问财核查 · 按需展开</span>
      <strong class="iwencai-connection {status_class}">{status_label}</strong></summary>
    {console_html}
  </details>"""
```

- [ ] **Step 2: Preserve all API hooks and status behavior**

Keep `data-iwencai-research`, `data-iwencai-module`, `data-iwencai-form`, `data-iwencai-input`, `data-iwencai-submit`, `data-iwencai-state`, and `data-iwencai-result` unchanged so existing JavaScript, authentication, and degradation behavior continue to work.

- [ ] **Step 3: Run iWencai tests and verify GREEN**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest \
  tests/test_web_iwencai_four_workspaces.py \
  tests/test_iwencai.py tests/test_web_iwencai_api.py -q
```

Expected: all selected tests pass with the controls still present inside a default-closed disclosure.

### Task 3: Reduce Market And Portfolio To Decisions

**Files:**
- Modify: `src/stock_ts/webapp/market_workspace.py`
- Modify: `src/stock_ts/webapp/portfolio_workspace.py`
- Test: `tests/test_web_three_second_essence.py`
- Test: `tests/test_web_market_research_workspace.py`
- Test: `tests/test_web_portfolio_dossier.py`

- [ ] **Step 1: Keep only the market verdict, action, and primary risk visible**

Use `assessment.thesis` as the single large verdict. Derive the visible action from the already computed risk budget without changing the model:

```python
market_action = (
    "暂停新增风险，先恢复行情数据。"
    if assessment.stage == "数据暂停"
    else f"按{assessment.risk_budget}执行；只在支持证据继续成立时增加风险。"
)
```

Move the decision rail, scenarios, dimensions, distribution, sectors, events, intraday/close panels, full evidence table, supporting HTML, and iWencai disclosure inside the single `details.market-evidence` block.

- [ ] **Step 2: Keep only the top three portfolio decisions visible**

Render `dossier.queue[:3]` as the visible queue. Each card keeps name, action/state, reason, and invalidation; remove visible priority numbers and cost-context narration. Move metrics, exposures, remaining queue items, boundaries, supporting evidence, and iWencai into `details.portfolio-evidence`.

- [ ] **Step 3: Run market and portfolio tests and verify GREEN**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest \
  tests/test_web_three_second_essence.py \
  tests/test_web_market_research_workspace.py \
  tests/test_web_portfolio_dossier.py \
  tests/test_web_essence_mode.py -q
```

Expected: the visible surface is capped while all professional content remains queryable in one closed details element.

### Task 4: Reduce Stock And Opportunity To Decisions

**Files:**
- Modify: `src/stock_ts/webapp/stock_workspace.py`
- Modify: `src/stock_ts/webapp/opportunity_workspace.py`
- Test: `tests/test_web_three_second_essence.py`
- Test: `tests/test_web_stock_dossier.py`
- Test: `tests/test_web_opportunity_dossier.py`

- [ ] **Step 1: Build the professional dossier's three visible facts**

Render at most two highest-weight `dossier.weighted_evidence` facts plus one counter-evidence/risk item, each marked with `data-core-stock-fact`. Keep the verdict stance/action and `position.invalidation` visible. Move identity detail, decision rail, position matrix, thesis spine, remaining weighted evidence, all diagnostics, full risks, scenarios, tables, supporting HTML, and iWencai into one `details.stock-evidence`.

- [ ] **Step 2: Give the memo fallback the same visible contract**

Keep status, next review/action, strongest evidence, strongest counter-evidence, and the primary invalidation from the first scenario. Move memo sections, scenarios, full evidence, trade plan, technical detail, debate, and iWencai into the same closed stock drawer.

- [ ] **Step 3: Keep only three opportunity candidate cards visible**

Keep `dossier.candidates[:3]`. Each visible card keeps one support fact, one counter fact, and `next_verification`. Move the funnel, gate metrics, risk register, remaining candidates, source/audit ledger, supporting HTML, and iWencai into `details.opportunity-evidence`.

- [ ] **Step 4: Run stock and opportunity tests and verify GREEN**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest \
  tests/test_web_three_second_essence.py \
  tests/test_web_stock_dossier.py \
  tests/test_web_stock_research_workspace.py \
  tests/test_web_opportunity_dossier.py -q
```

Expected: the primary facts and candidate caps pass, stale-data wording remains conditional, and the full audit trail stays present inside the drawer.

### Task 5: Establish The Decision-Note Visual Hierarchy

**Files:**
- Modify: `src/stock_ts/webapp/styles.py`
- Test: `tests/test_web_three_second_essence.py`

- [ ] **Step 1: Add shared three-second layout classes**

Add `.essence-verdict`, `.essence-action-risk`, `.essence-focus-list`, `.essence-detail`, and `.iwencai-research-disclosure` rules using the existing palette. Use one memorable element: a narrow left-edge decision signal whose color follows state. Keep all other surfaces quiet, flat, and low-contrast.

- [ ] **Step 2: Add mobile and accessibility contracts**

At `max-width: 760px`, stack action and risk, remove multi-column minimum widths, keep cards within `min-width: 0`, and preserve a 44px disclosure target. Keep `:focus-visible` and `prefers-reduced-motion` rules.

- [ ] **Step 3: Run web regression and lint**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_web_*.py -q
make lint
git diff --check
```

Expected: no new web or lint failures.

### Task 6: Verify, Document, Push, And Deploy

**Files:**
- Modify: `docs/superpowers/three-second-essence/TODO.md`
- Create: `docs/superpowers/three-second-essence/test.md`
- Create: `docs/superpowers/three-second-essence/review.md`
- Create: `docs/superpowers/three-second-essence/handoff.md`

- [ ] **Step 1: Run focused and full test suites**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest \
  tests/test_web_three_second_essence.py \
  tests/test_web_essence_mode.py \
  tests/test_web_compact_mode.py \
  tests/test_web_market_research_workspace.py \
  tests/test_web_portfolio_dossier.py \
  tests/test_web_stock_dossier.py \
  tests/test_web_opportunity_dossier.py \
  tests/test_web_iwencai_four_workspaces.py -q
PYTHONPATH=src .venv/bin/python -m pytest -q
```

Expected: focused suite passes. Record any unchanged full-suite baseline failures separately; do not claim a clean full suite unless it exits zero.

- [ ] **Step 2: Inspect real desktop and mobile pages**

Start the app on an unused local port. Inspect market, portfolio, stock, and opportunity at `1280x900` and `390x844`; verify the first viewport shows verdict/action/risk, all details are closed, `document.documentElement.scrollWidth <= window.innerWidth`, and the browser console has no errors.

- [ ] **Step 3: Review the diff and write evidence**

Check every spec acceptance criterion, record exact test outputs and screenshots in `test.md`, record safety/privacy review in `review.md`, update all TODO checkboxes, and run `git diff --check` plus `git status --short`.

- [ ] **Step 4: Commit and push main**

```bash
git add docs/superpowers src/stock_ts/webapp tests
git commit -m "[界面优化] 四工作台收敛为三秒精华版"
git push origin main
```

- [ ] **Step 5: Deploy the verified Git commit**

Back up `/opt/stock-ts`, preserve `.env`, `.secrets`, `data`, `reports`, authentication and holdings data, fast-forward the server checkout to the pushed `main`, restart only `stock-ts.service`, and verify the main service, Signal Desk, and Nginx stay active.

- [ ] **Step 6: Verify public parity**

Confirm local `main`, `origin/main`, and server `main` have the same commit hash. Verify the public health route, authenticated page boundary, and anonymous iWencai rejection without printing or exposing any credentials.

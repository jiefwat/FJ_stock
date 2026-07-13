# Market Session Playbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the daily-market workspace into pre-market, intraday, and close-review phases with a collapsed intraday evidence dossier.

**Architecture:** Keep `MarketRegimeAssessment` and every existing evidence renderer unchanged. Extend `render_market_workspace` with explicit intraday-detail and close-review slots, then change `web.py` composition so high-value signals stay visible while detailed movers, sector lists, and events use native disclosure.

**Tech Stack:** Python 3.9+, server-rendered HTML, CSS grid, native `details/summary`, pytest, Ruff, in-app browser smoke.

---

### Task 1: Establish The Three-Session HTML Contract

**Files:**
- Modify: `tests/test_web_market_research_workspace.py`
- Modify: `src/stock_ts/webapp/market_workspace.py`
- Modify: `src/stock_ts/web.py`
- Modify: `tests/test_web_module_decisions.py`

- [ ] Write a failing renderer test asserting exactly three `.market-session-phase` sections in `盘前框架 -> 盘中验证 -> 收盘复核` order, a default-closed `.market-intraday-ledger`, and complete injected detail/close content.
- [ ] Run `PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q tests/test_web_market_research_workspace.py` and confirm failure because phase markup does not exist.
- [ ] Add `intraday_detail_html` and `close_html` keyword parameters to `render_market_workspace`.
- [ ] Render thesis, decision rail, and scenarios inside phase 01; trend/distribution and mainline inside phase 02; detailed intraday HTML in native disclosure; close HTML and evidence audit inside phase 03.
- [ ] In `_render_compact_market_module`, pass heatmap/mainline as `sectors_html`, movers/Top5/events as `intraday_detail_html`, and diagnosis/guidance as `close_html`.
- [ ] Update module tests to prove all legacy evidence remains in the market HTML and the intraday detail is after its disclosure summary.
- [ ] Run focused market tests and commit with `[大盘研究] 建立三段式市场剧本`.

### Task 2: Build The Market Session Ruler And Verify

**Files:**
- Modify: `tests/test_web_design_guide_shell.py`
- Modify: `src/stock_ts/webapp/styles.py`
- Modify: `docs/product/stock-analysis-agent-design-guide.md`
- Modify: `docs/superpowers/market-session-playbook/TODO.md`
- Modify: `docs/superpowers/market-session-playbook/test.md`
- Modify: `docs/superpowers/market-session-playbook/review.md`

- [ ] Write a failing CSS contract test for `.market-session-ruler`, `.market-session-phase`, `.market-intraday-ledger`, focus-visible treatment, and mobile single-column rules.
- [ ] Run the CSS test and confirm RED.
- [ ] Add a horizontal three-phase ruler, quiet phase surfaces, and an ivory intraday ledger using existing tokens.
- [ ] At `max-width:680px`, stack the ruler and phase headers, keep disclosure readable, and prevent horizontal overflow.
- [ ] Run browser smoke at `1440x1000` and `390x844`, checking one primary verdict, three phases, closed intraday ledger, preserved evidence, and no overflow.
- [ ] Run Ruff, compileall, focused tests, Python 3.9 contracts, and full pytest; report the known daily-pipeline baseline separately.
- [ ] Use `ai-review`, update product/test/review/TODO evidence, and commit with `[交付验收] 完成三段式市场剧本验收`.
- [ ] Fast-forward `main`, push, deploy by Git bundle, restart only `stock-ts.service`, and verify local/public health plus Signal Desk and Nginx.

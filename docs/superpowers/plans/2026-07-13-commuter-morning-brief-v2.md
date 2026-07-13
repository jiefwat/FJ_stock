# Commuter Morning Brief V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 15-stock morning email with a 30-second action-first brief that remains safe under stale or degraded data.

**Architecture:** Keep `latest.md`, `latest_decisions.json`, `pipeline.status`, per-user holdings, and the delivery pipeline unchanged. Change only `build_morning_report` composition and add small deterministic helpers that cap holdings, candidates, discipline, and workspace links.

**Tech Stack:** Python 3.9+, Markdown email transport, existing notification renderer, pytest, Ruff, systemd dry-run.

---

### Task 1: Establish The 30-Second Content Contract

**Files:**
- Modify: `tests/test_email_report_simplification.py`
- Modify: `tests/test_send_morning_report.py`
- Modify: `scripts/send_morning_report.py`

- [ ] Add a production-like failing test that renders at least five holdings and ten candidates, then asserts:
  - the first heading is `## 30秒结论`;
  - `## 投资建议 15只票` and `## 今日市场机会` are absent;
  - `## 先处理持仓`, `## 今日只看3只`, `## 三条纪律`, and `## 到公司再看` are present in order;
  - candidate action lines are capped at three and holding action lines at four;
  - the supplied `site_url` appears in market, portfolio, opportunity, and data links;
  - non-empty line count is at most 28 and total content is at most 1,100 characters for the fixture.
- [ ] Run:

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q \
  tests/test_email_report_simplification.py \
  tests/test_send_morning_report.py
```

Expected: fail because the current report still renders `投资建议 15只票`, exposes up to 15 candidates, and has no 30-second or web-review sections.

- [ ] Refactor `build_morning_report` to compose these arrays:

```python
quick_lines = _commuter_decision_brief(
    conclusion=conclusion,
    market=market,
    portfolio_actions=portfolio_actions,
    opportunity_actions=opportunity_actions,
    pipeline=pipeline,
)[:4]
holding_lines = _subway_holding_lines(portfolio_actions, portfolio)[:4]
candidate_lines = opportunity_actions[:3]
discipline_lines = _commuter_discipline_lines(
    execution_guard=execution_guard,
    data_lines=data_lines,
)
review_lines = _commuter_review_links(site_url, trade_date)
```

- [ ] Add `_commuter_discipline_lines` that returns exactly three concise bullets: the current execution guard, a fixed no-chase/no-average-down/no-trigger-no-trade rule, and the first actionable data or announcement exception when present.
- [ ] Add `_commuter_review_links` using the normalized supplied `site_url` and Markdown links to `#market`, `#portfolio`, `#opportunity`, and `#data-center`, followed by the research-only trade-date notice.
- [ ] Change the email composition to the five design-contract headings and remove the duplicated market-opportunity summary plus the 15-stock block.
- [ ] Run the focused tests and confirm they pass.
- [ ] Commit with `[晨报内容] 建立三十秒通勤简报`.

### Task 2: Preserve Safety, Personalization, And Delivery

**Files:**
- Modify: `tests/test_send_morning_report.py`
- Modify: `tests/test_user_morning_reports.py`
- Modify: `docs/superpowers/commuter-morning-brief-v2/TODO.md`
- Modify: `docs/superpowers/commuter-morning-brief-v2/test.md`
- Modify: `docs/superpowers/commuter-morning-brief-v2/review.md`

- [ ] Update existing heading assertions from the retired five-section contract to the new five-section contract; do not weaken assertions for stock names, judgment, action, invalidation, stale guard, deduplication, per-user holdings path, or dry-run dispatch.
- [ ] Add a failing stale-data test asserting `先别按今天盘面执行` appears inside `30秒结论` and before any holding or candidate.
- [ ] Pass the first `_execution_guard_lines` item into `_commuter_decision_brief` and render it as the first quick-read bullet. Do not alter `_execution_guard_lines` rules.
- [ ] Run:

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q \
  tests/test_send_morning_report.py \
  tests/test_email_report_simplification.py \
  tests/test_user_morning_reports.py
make lint
/Users/fangjie/Documents/StockTs/.venv/bin/python -m compileall -q scripts/send_morning_report.py
git diff --check
```

- [ ] Render the freshly generated server artifacts without sending mail:

```bash
PYTHONPATH=src .venv/bin/python scripts/send_morning_report.py \
  --daily-dir reports/daily \
  --html-dir reports/html \
  --announcement-dir reports/announcements \
  --holdings-path data/portfolio/holdings.csv \
  --channels email \
  --style digest \
  --dry-run
```

Verify no real delivery occurs, the content has at most three candidates, the stale guard matches the current pipeline, and operational errors or credentials are absent.

- [ ] Use `ai-review`, update TODO/test/review evidence, and commit with `[交付验收] 完成通勤版晨报验收`.
- [ ] Fast-forward `main`, push, deploy by Git bundle, run the server dry-run again, and verify the morning-email timer, StockTS, Signal Desk, Nginx, and public health remain active.

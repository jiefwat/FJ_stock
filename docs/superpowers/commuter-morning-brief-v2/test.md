# Test Evidence

Status: verified locally and with server production artifacts

Date: 2026-07-13

## TDD Evidence

The new production-like density test first failed because the legacy report rendered `昨天大盘总结`, `今日市场机会`, and `投资建议 15只票`. After the composition change it passed with the five-section 30-second contract.

## Focused Regression

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q \
  tests/test_send_morning_report.py \
  tests/test_email_report_simplification.py \
  tests/test_user_morning_reports.py
```

Result: `29 passed in 0.31s`.

## Static Verification

```bash
make lint
/Users/fangjie/Documents/StockTs/.venv/bin/python -m compileall -q scripts/send_morning_report.py
git diff --check
```

Result: Ruff reported `All checks passed!`; compileall and diff check exited `0`.

## Full Suite

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q
```

Result: `556 passed, 5 failed, 10 warnings in 18.22s`.

The five failures are the unchanged `tests/test_daily_pipeline.py` baseline failures. This branch does not modify the daily pipeline or its tests, and no failure appeared in the morning-report, notification, or per-user delivery paths.

## Server Artifact Dry-Run

The candidate script was uploaded to `/tmp` and rendered against the freshly refreshed server artifacts without replacing the production script. The actual dispatch command used `--dry-run`, so no email was sent.

Production-artifact result:

- body length: `1050` characters, down from `1929`;
- non-empty lines: `23`, down from `41`;
- maximum line length: `111` characters;
- ordered headings: `30秒结论`, `先处理持仓`, `今日只看3只`, `三条纪律`, `到公司再看`;
- candidate lines: `3`, down from `15`;
- legacy 15-stock heading absent;
- market/data workspace links and research disclaimer present;
- dispatch dry-run exited `0`.

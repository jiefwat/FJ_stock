# Test Evidence

Status: accepted with five unchanged daily-pipeline baseline failures

Date: 2026-07-13

## Static Verification

```bash
make lint
/Users/fangjie/Documents/StockTs/.venv/bin/python -m compileall -q src/stock_ts
git diff --check
```

Result: Ruff reported `All checks passed!`; compileall and diff check exited `0`.

## Focused Regression

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q \
  tests/test_data_center_dossier.py \
  tests/test_web_data_center_workspace.py \
  tests/test_web_design_guide_shell.py \
  tests/test_web_module_decisions.py \
  tests/test_web_layout.py \
  tests/test_web_data_accuracy.py
```

Result: `128 passed in 2.46s`.

## Python 3.9 Contract Regression

```bash
PYTHONPATH=src /Users/fangjie/opt/anaconda3/bin/python3.9 -m pytest -q \
  tests/test_data_center_dossier.py \
  tests/test_web_data_center_workspace.py
```

Result: `9 passed in 0.10s`.

## Full Suite

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q
```

Result: `552 passed, 5 failed, 10 warnings in 18.96s`.

The five failures are the unchanged `tests/test_daily_pipeline.py` baseline failures. This branch does not modify the daily-pipeline implementation or tests, and no failure appeared outside that known baseline.

## Responsive Browser Smoke

Local preview: `http://127.0.0.1:18654`

Desktop `1440x1000`:

- document width `1425`, no horizontal overflow;
- one primary data verdict;
- readiness gate height `218px`;
- seven recovery steps in source-restoration order;
- four downstream impact lanes;
- nine source-ledger rows preserved;
- source ledger default closed.

Mobile `390x844`:

- document width `375`, no horizontal overflow;
- active data-center title begins at `569px`, inside the first viewport;
- one primary data verdict, seven recovery steps, and four impact lanes remain present;
- source ledger default closed and expands through native `details/summary`;
- expanded ledger uses block cards (`303px` first-card width) instead of a horizontal table;
- all nine ledger rows remain in the DOM.

Visual inspection also found and corrected one operations-order defect: full-chain validation originally appeared before repairable sources. The final order restores market/K-line and other upstream evidence first, then uses full-chain validation as the acceptance check.

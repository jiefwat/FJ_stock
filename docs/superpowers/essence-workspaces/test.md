# Essence Workspaces Test Evidence

## TDD Evidence

The new essence-mode contract initially failed in nine expected places:

- narration and decorative labels remained;
- unified evidence drawers did not exist;
- portfolio and opportunity front rows exceeded three records;
- data-center English eyebrows remained;
- essence CSS contracts did not exist.

After implementation, the focused suite passed:

```text
30 passed in 0.64s
```

## Web Regression

Command:

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest tests/test_web_*.py -q
```

Result:

```text
214 passed in 9.53s
```

Lint command:

```bash
make lint
```

Result:

```text
All checks passed!
```

## Full Regression

Command:

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q
```

Result:

```text
559 passed, 5 failed, 10 warnings in 18.90s
```

All five failures are the pre-existing `tests/test_daily_pipeline.py` baseline reproduced before this change. The failing test names and failure mode are unchanged; each expects `DailyPipelineResult.ok is True` and receives `False`.

## Browser Acceptance

Local URL: `http://127.0.0.1:8514/?provider=sample&code=600519`

Desktop viewport: `1440x1000`. Mobile viewport: `390x844` with a `375px` layout viewport.

| Workspace | Before visible text | After visible text | After desktop height |
| --- | ---: | ---: | ---: |
| Daily market | 4,209 | 865 | 1,432px |
| Portfolio | 5,389 | 662 | 1,197px |
| Stock | 4,988 | 1,324 | 1,882px |
| Opportunities | 11,533 | 869 | 1,238px |
| Data center | 4,585 | 694 | 840px |

Mobile acceptance:

- all five workspace hashes activated the intended workspace;
- `scrollWidth == clientWidth == 375` for every workspace;
- all primary evidence ledgers were closed by default;
- the stock committee verdict appears before the secondary stock input panel;
- the repeated global data-center summary was removed;
- browser console reported no errors.

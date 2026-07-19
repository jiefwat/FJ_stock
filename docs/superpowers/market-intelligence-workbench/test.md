# Verification Report

Date: 2026-07-19
Branch: `codex/analyst-workflow-v2`
Local verification URL: `http://127.0.0.1:8765`

## Automated Gates

`make verify` passed the complete operator gate:

| Gate | Result |
| --- | --- |
| Ruff | Passed, no findings |
| mypy strict | Passed, 14 source files |
| Backend pytest | Passed, 28 tests |
| Frontend TypeScript | Passed |
| Frontend Vitest | Passed, 5 tests across 4 files |
| Vite production build | Passed, 1,650 modules transformed |
| Live data | Passed: 5,527 equities, 100.0% core-field coverage, 6 indices, 49 sectors |

Focused TDD checks run during V2 implementation:

```text
pnpm test --run src/features/stocks/StockLabPage.test.tsx
uv run pytest -q tests/test_analysis.py -k 'presets_are_distinct or risk_off_penalty'
uv run pytest -q tests/test_analysis.py -k 'multiple_visible_factors or high_volatility'
```

The focused tests were observed failing for the intended missing behavior before implementation, then passed after the corresponding implementation.

## Browser Workflow

The production build was served by FastAPI and tested in a real browser.

| Scenario | Result |
| --- | --- |
| Today route | Displayed market temperature 5, defensive regime, 25% research-risk reference, 70% evidence coverage, and linked next actions |
| Market route | Displayed real breadth, index, and sector evidence with weights; expanded 12 sectors to all 49 on demand |
| Trend strategy | Scanned 5,527 stocks; 151 passed; top result `星网锐捷` showed base 95, context penalty 15, final 80, and 50% evidence coverage |
| Unsupported strategies | Capital and sector strategies showed explicit unavailable explanations and rendered no fabricated candidate cards; sector-name-only input is regression-tested as insufficient without strength evidence |
| Oversold strategy | Returned a distinct candidate set headed by `特变电工`; copy identifies it as a daily observation proxy |
| Stock Lab | Loaded `SH.600519`, 180 bars, close/MA5/MA20/MA60, seven score factors, and 70% evidence coverage |
| Add to watchlist | Accepted an edited thesis and invalidation, then showed both `观察中 · 编辑记录` and a persistent success confirmation |
| Watchlist persistence | Updated status, thesis, and invalidation; showed `已保存` and linked back to the dossier |
| Data Center | Displayed observation/fetch timestamps, delayed freshness, 100% coverage, and a successful manual-refresh timestamp |
| Desktop layout | Passed at 1,280 CSS pixels with no horizontal overflow |
| Desktop workflow | Today, Opportunities, Stock Lab, and Watchlist passed at 1440 x 900, 1536 x 900, and 1920 x 1080 with no horizontal overflow |
| Browser logs | No warning or error entries after the complete workflow |

## Data Assertions

- The market observation timestamp was `2026-07-17 15:00:00`, the latest completed A-share session before the weekend test date.
- Sina supplied the 5,527-stock universe and 49 industry snapshots.
- Tencent supplied the six required core indices and stock history.
- Missing sector capital flow is presented as unavailable, never as a fabricated zero.
- Market factors expose the evidence counts used by the deterministic score; unavailable factors are excluded and available weights are renormalized.
- The defensive regime applies a visible 15-point penalty to opportunity scores; cautious mode applies 8 points.
- Stock stance starts at 50 and is reproducible from the displayed factor impacts rather than one moving-average threshold.

## Residual Risks

- Public market endpoints and their terms can change without notice; production or commercial use still needs a licensing review.
- Previous-market-day selection handles weekends but does not yet use an official exchange holiday calendar.
- iWenCai enrichment was not exercised because `IWENCAI_API_KEY` is not configured.
- Stock-level sector mapping and capital-flow coverage are not available in the current normalized universe; dependent strategies stop with an explicit reason.
- Oversold observation is a single-day proxy, not confirmation of a multi-day reversal.
- FastAPI TestClient emits one third-party Starlette/httpx deprecation warning; it does not affect runtime behavior.

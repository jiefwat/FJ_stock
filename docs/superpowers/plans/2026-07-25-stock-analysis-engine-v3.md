# Stock Analysis Engine V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a modular multi-factor stock-analysis engine with honest historical validation and volatility-aware risk guidance while preserving the existing Stock Lab layout.

**Architecture:** Pure indicator formulas live in a new dependency-free `analysis/indicators.py` module. `analysis/stock.py` converts those values into API models, visible factors, validation, and prose; the frontend only adds a compact validation panel and continues to render existing ledgers and grids.

**Tech Stack:** Python 3.12, Pydantic, pytest, FastAPI, React 19, TypeScript, TanStack Query, Vitest, Testing Library, CSS.

---

## File Map

- Create `backend/src/marketdesk/analysis/indicators.py`: pure EMA, MACD, ATR, Bollinger, and drawdown calculations.
- Create `backend/tests/test_indicators.py`: formula, warm-up, and invalid-input regression tests.
- Modify `backend/src/marketdesk/models.py`: expanded technical summary and historical validation contract.
- Modify `backend/src/marketdesk/analysis/stock.py`: orchestration, score factors, confluence, validation, and ATR risk guidance.
- Modify `backend/tests/test_analysis.py`: behavior tests for factors, validation, confluence, and risk language.
- Modify `backend/tests/test_api.py`: response-contract coverage for the new dossier fields.
- Modify `frontend/src/features/stocks/StockLabPage.tsx`: typed compact validation panel without section reordering.
- Modify `frontend/src/features/stocks/StockLabPage.test.tsx`: validation panel and content-order regression coverage.
- Modify `frontend/src/app/styles.css`: styles scoped to the compact validation panel.
- Modify `docs/superpowers/market-intelligence-workbench/TODO.md`: completed V3 capability marker.
- Modify `docs/superpowers/market-intelligence-workbench/test.md`: verification and public smoke evidence.

### Task 1: Pure Indicator Engine

**Files:**
- Create: `backend/tests/test_indicators.py`
- Create: `backend/src/marketdesk/analysis/indicators.py`

- [ ] **Step 1: Write failing formula and warm-up tests**

```python
from datetime import date, timedelta

import pytest

from marketdesk.analysis.indicators import (
    average_true_range,
    bollinger_bands,
    ema_series,
    macd_series,
    maximum_drawdown,
)
from marketdesk.models import Bar


def test_ema_series_seeds_with_sma_and_then_recurses() -> None:
    assert ema_series([1, 2, 3, 4], 3) == [None, None, 2.0, 3.0]


def test_macd_requires_a_warmed_signal_line() -> None:
    line, signal, histogram = macd_series([float(value) for value in range(1, 41)])
    assert line[-1] is not None
    assert signal[-1] is not None
    assert histogram[-1] == pytest.approx(line[-1] - signal[-1])


def test_atr_uses_true_range_and_requires_previous_close() -> None:
    start = date(2026, 1, 1)
    bars = [Bar(date=start + timedelta(days=i), open=10, high=12, low=9, close=11, volume=1, amount=1) for i in range(15)]
    assert average_true_range(bars, 14) == pytest.approx(3.0)


def test_bollinger_and_drawdown_handle_flat_and_zero_values() -> None:
    assert bollinger_bands([10.0] * 20) == (10.0, 10.0, 0.5)
    assert maximum_drawdown([100, 120, 90], 3) == pytest.approx(25.0)
    assert maximum_drawdown([0, 1, 2], 3) is None
```

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend && uv run pytest -q tests/test_indicators.py`

Expected: collection fails because `marketdesk.analysis.indicators` does not exist.

- [ ] **Step 3: Implement minimal pure calculations**

```python
def ema_series(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if period <= 0 or len(values) < period:
        return result
    current = sum(values[:period]) / period
    result[period - 1] = current
    alpha = 2 / (period + 1)
    for index in range(period, len(values)):
        current = (values[index] - current) * alpha + current
        result[index] = current
    return result


def macd_series(values: list[float], fast: int = 12, slow: int = 26, signal_period: int = 9) -> tuple[list[float | None], list[float | None], list[float | None]]:
    fast_line = ema_series(values, fast)
    slow_line = ema_series(values, slow)
    macd: list[float | None] = [
        fast_value - slow_value
        if fast_value is not None and slow_value is not None
        else None
        for fast_value, slow_value in zip(fast_line, slow_line, strict=True)
    ]
    indexes = [index for index, value in enumerate(macd) if value is not None]
    compact = [macd[index] for index in indexes]
    compact_signal = ema_series([float(value) for value in compact if value is not None], signal_period)
    signal: list[float | None] = [None] * len(values)
    for index, value in zip(indexes, compact_signal, strict=True):
        signal[index] = value
    histogram = [
        value - signal_value
        if value is not None and signal_value is not None
        else None
        for value, signal_value in zip(macd, signal, strict=True)
    ]
    return macd, signal, histogram


def average_true_range(bars: list[Bar], period: int = 14) -> float | None:
    if period <= 0 or len(bars) < period + 1:
        return None
    true_ranges = [
        max(
            bar.high - bar.low,
            abs(bar.high - bars[index - 1].close),
            abs(bar.low - bars[index - 1].close),
        )
        for index, bar in enumerate(bars[1:], start=1)
    ]
    current = sum(true_ranges[:period]) / period
    for value in true_ranges[period:]:
        current = (current * (period - 1) + value) / period
    return current


def bollinger_bands(values: list[float], period: int = 20, deviations: float = 2) -> tuple[float | None, float | None, float | None]:
    if period <= 0 or len(values) < period:
        return None, None, None
    sample = values[-period:]
    mean = sum(sample) / period
    standard_deviation = (sum((value - mean) ** 2 for value in sample) / period) ** 0.5
    upper = mean + deviations * standard_deviation
    lower = mean - deviations * standard_deviation
    position = 0.5 if upper == lower else (sample[-1] - lower) / (upper - lower)
    return upper, lower, position


def maximum_drawdown(values: list[float], window: int = 60) -> float | None:
    if window <= 0 or len(values) < window:
        return None
    sample = values[-window:]
    if any(value <= 0 for value in sample):
        return None
    peak = sample[0]
    drawdown = 0.0
    for value in sample[1:]:
        peak = max(peak, value)
        drawdown = max(drawdown, (peak - value) / peak * 100)
    return drawdown
```

The implementation must validate positive periods, return unavailable values for short history, and return `None` rather than divide by a non-positive peak or close.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `cd backend && uv run pytest -q tests/test_indicators.py`

Expected: all indicator tests pass.

- [ ] **Step 5: Commit the indicator boundary**

```bash
git add backend/src/marketdesk/analysis/indicators.py backend/tests/test_indicators.py
git commit -m '[分析内核] 增加纯技术指标引擎'
```

### Task 2: Expanded Dossier, Factors, Confluence, And Validation

**Files:**
- Modify: `backend/src/marketdesk/models.py`
- Modify: `backend/src/marketdesk/analysis/stock.py`
- Modify: `backend/tests/test_analysis.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing stock behavior tests**

```python
def test_stock_analysis_adds_independent_momentum_and_risk_factors() -> None:
    result = analyse_stock(equity(pe=22), trending_bars(140))
    assert result.technical is not None
    assert result.technical.macd_histogram is not None
    assert result.technical.atr_pct is not None
    assert result.technical.bollinger_position is not None
    assert result.technical.max_drawdown60 is not None
    assert {factor.key for factor in result.score_factors} >= {
        "macd_momentum", "atr_risk", "bollinger_position", "drawdown_risk"
    }
    assert any(item.key == "signal_confluence" for item in result.analysis_dimensions)


def test_historical_validation_is_descriptive_and_does_not_change_live_score() -> None:
    bars = trending_bars(160)
    result = analyse_stock(equity(pe=22), bars)
    expected_score = round(max(0, min(100, 50 + sum(item.impact for item in result.score_factors))), 2)
    assert result.stance_score == expected_score
    assert result.signal_validation.horizon_days == 20
    assert result.signal_validation.sample_count >= 3
    assert "不直接计入实时评分" in result.signal_validation.summary


def test_short_history_returns_unavailable_validation() -> None:
    result = analyse_stock(equity(), trending_bars(30))
    assert result.signal_validation.available is False
    assert result.signal_validation.sample_count == 0
```

Add an API assertion that `/api/v1/stocks/{symbol}` returns `signal_validation`, `technical.macd_histogram`, and `technical.atr_pct`.

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend && uv run pytest -q tests/test_analysis.py -k 'independent_momentum or historical_validation or unavailable_validation'`

Expected: fail because the model and fields do not exist.

- [ ] **Step 3: Add exact response contracts**

```python
class TechnicalSummary(StrictModel):
    ma5: float | None
    ma20: float | None
    ma60: float | None
    ema12: float | None
    ema26: float | None
    macd: float | None
    macd_signal: float | None
    macd_histogram: float | None
    rsi14: float | None
    volatility20: float | None
    atr14: float | None
    atr_pct: float | None
    bollinger_upper: float | None
    bollinger_lower: float | None
    bollinger_position: float | None
    max_drawdown60: float | None
    support: float | None
    resistance: float | None


class StockSignalValidation(StrictModel):
    available: bool
    horizon_days: int = 20
    sample_count: int = Field(ge=0)
    positive_rate: float | None = Field(default=None, ge=0, le=1)
    average_return: float | None = None
    worst_return: float | None = None
    summary: str
```

Add `signal_validation: StockSignalValidation` to `StockDossier`.

- [ ] **Step 4: Build the technical snapshot and visible factors**

Use the pure indicator functions and add factors with these deterministic impacts:

```python
# MACD: +6 positive histogram, -6 negative histogram.
# ATR percentage: +3 at <=2%, 0 at <=3%, -4 at <=5%, -8 above 5%.
# Bollinger position: +3 from 0.35 through 0.80, -6 above 1, -3 below 0.
# 60-day drawdown: +2 at <=8%, 0 at <=15%, -4 at <=25%, -8 above 25%.
```

Create a `signal_confluence` dimension from available positive/negative trend, momentum, and risk factors. Its summary must state the counts and whether signals agree or conflict; it must not add another score factor.

- [ ] **Step 5: Add leak-resistant rolling validation**

For every historical index with warmed MA20, MA5, and MACD signal plus a complete 20-bar forward window, select a signal only when close > MA20, MA5 > MA20, and MACD histogram > 0. Calculate the forward return from that index to index + 20. Require three samples; label overlapping samples and keep this object outside `score_factors`.

- [ ] **Step 6: Run backend tests and verify GREEN**

Run: `cd backend && uv run pytest -q tests/test_indicators.py tests/test_analysis.py tests/test_api.py`

Expected: all focused backend tests pass.

- [ ] **Step 7: Commit the expanded analysis contract**

```bash
git add backend/src/marketdesk/models.py backend/src/marketdesk/analysis/stock.py backend/tests/test_analysis.py backend/tests/test_api.py
git commit -m '[个股分析] 增加多因子信号与历史验证'
```

### Task 3: Volatility-aware Risk Guidance

**Files:**
- Modify: `backend/src/marketdesk/analysis/stock.py`
- Modify: `backend/tests/test_analysis.py`

- [ ] **Step 1: Write failing ATR guidance tests**

```python
def test_atr_changes_stop_and_caps_position_for_high_volatility() -> None:
    result = analyse_stock(equity(price=100, pe=22), volatile_bars(140))
    assert result.technical and result.technical.atr_pct and result.technical.atr_pct > 5
    assert "ATR" in result.investment_advice.stop_loss
    assert "5%" in result.investment_advice.position_hint
    assert "ATR" in next(item for item in result.analysis_dimensions if item.key == "risk_controls").summary


def test_atr_target_is_used_when_resistance_is_not_above_price() -> None:
    result = analyse_stock(equity(price=120, pe=22), flat_then_breakout_bars())
    assert "ATR" in result.investment_advice.take_profit
```

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend && uv run pytest -q tests/test_analysis.py -k 'atr_changes_stop or atr_target'`

Expected: fail because advice still uses structural support/resistance only.

- [ ] **Step 3: Add separate structural and volatility anchors**

Use `latest_close - 2 * atr14` as the volatility risk line and `latest_close + 3 * atr14` as a review target when resistance is missing or not above the latest close. Keep structural support in the text. Cap suggested trial size at 5% when `atr_pct > 5`, at 10% when `atr_pct > 3`, and never increase a position recommendation when stance or evidence is weak.

- [ ] **Step 4: Run analysis tests and verify GREEN**

Run: `cd backend && uv run pytest -q tests/test_analysis.py`

Expected: all analysis tests pass.

- [ ] **Step 5: Commit the risk guidance**

```bash
git add backend/src/marketdesk/analysis/stock.py backend/tests/test_analysis.py
git commit -m '[风险分析] 增加 ATR 动态仓位与止损纪律'
```

### Task 4: Compact Existing-layout UI Integration

**Files:**
- Modify: `frontend/src/features/stocks/StockLabPage.tsx`
- Modify: `frontend/src/features/stocks/StockLabPage.test.tsx`
- Modify: `frontend/src/app/styles.css`

- [ ] **Step 1: Write a failing panel and order test**

Extend the dossier fixture with:

```typescript
signal_validation: {
  available: true,
  horizon_days: 20,
  sample_count: 18,
  positive_rate: 0.67,
  average_return: 3.2,
  worst_return: -6.4,
  summary: "历史滚动样本仅作描述，不直接计入实时评分。",
},
```

Then assert:

```typescript
const validation = within(await screen.findByLabelText("历史信号验证"));
expect(validation.getByText("18 个样本")).toBeInTheDocument();
expect(validation.getByText("67%")).toBeInTheDocument();
expect(validation.getByText(/不直接计入实时评分/)).toBeInTheDocument();
expect(forecast.compareDocumentPosition(validationElement) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
expect(validationElement.compareDocumentPosition(comparison) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
```

- [ ] **Step 2: Run the test and verify RED**

Run: `cd frontend && pnpm test --run src/features/stocks/StockLabPage.test.tsx`

Expected: fail because the validation panel does not exist.

- [ ] **Step 3: Add typed compact panel**

Define `SignalValidation`, add it to `Dossier`, and render `SignalValidationPanel` immediately after `TrendForecastPanel`. Show unavailable state, sample count, positive rate, average return, worst return, and the descriptive-only boundary. Use existing `panel`, typography, and responsive grid patterns.

- [ ] **Step 4: Add scoped responsive styles**

Use `.signal-validation-panel`, `.signal-validation-metrics`, and existing color variables. Do not change shell widths, navigation, route order, or global section spacing.

- [ ] **Step 5: Run frontend checks and verify GREEN**

Run: `cd frontend && pnpm test --run src/features/stocks/StockLabPage.test.tsx && pnpm typecheck && pnpm build`

Expected: Stock Lab tests, type checking, and production build pass.

- [ ] **Step 6: Commit the UI integration**

```bash
git add frontend/src/features/stocks/StockLabPage.tsx frontend/src/features/stocks/StockLabPage.test.tsx frontend/src/app/styles.css
git commit -m '[个股研究] 展示历史信号验证证据'
```

### Task 5: Verification, Review, Deployment, And Public Acceptance

**Files:**
- Modify: `docs/superpowers/market-intelligence-workbench/TODO.md`
- Modify: `docs/superpowers/market-intelligence-workbench/test.md`
- Modify only implementation files required by review findings.

- [ ] **Step 1: Run the full repository gate**

Run: `make verify`

Expected: backend lint, backend types, backend tests, frontend types, frontend tests, production build, and live-data quality all pass.

- [ ] **Step 2: Review the complete diff**

Run: `git diff release-2026-07-25...HEAD --check` and inspect `git diff release-2026-07-25...HEAD`.

Confirm indicator availability, formula boundaries, score visibility, no look-ahead use, API compatibility, mobile behavior, and no provider access outside `providers/`.

- [ ] **Step 3: Run local production browser acceptance**

Open Stock Lab against the production build and verify:

1. existing page section order is unchanged except the compact validation panel after trend forecast;
2. new technical values and score factors render;
3. unavailable validation is honest for short history;
4. desktop and 390px mobile widths have no horizontal overflow.

- [ ] **Step 4: Record evidence and rerun the final gate**

Update TODO and test evidence with actual counts, run `git diff --check`, and run `make verify` again after documentation changes.

- [ ] **Step 5: Commit, push, and deploy**

```bash
git add docs/superpowers/market-intelligence-workbench/TODO.md docs/superpowers/market-intelligence-workbench/test.md
git commit -m '[发布记录] 完成分析内核 V3 验收'
git push origin codex/user-accounts-personalization
DEPLOY_HOST="$DEPLOY_HOST" ./deploy/deploy_public.sh
```

- [ ] **Step 6: Verify production**

Check `/healthz`, one public stock dossier response, the production release symlink and service state, and the Stock Lab page in a real browser. Confirm anonymous personal-data endpoints still return 401 and no account database was replaced.

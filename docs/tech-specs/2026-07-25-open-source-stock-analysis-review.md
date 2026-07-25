# Open-source Stock Analysis Review

Date: 2026-07-25

## Purpose

Identify proven analysis patterns that can improve Market Desk's deterministic stock research without changing the product into an automated trading system or adding a heavy machine-learning dependency.

Repository popularity figures are a point-in-time GitHub API snapshot from 2026-07-25. Stars indicate community attention, not investment validity.

## Primary-source findings

### Microsoft Qlib

- Repository: [microsoft/qlib](https://github.com/microsoft/qlib), 46,615 stars, MIT license at review time.
- Qlib describes a complete research chain covering data processing, model training, backtesting, alpha research, risk modeling, portfolio optimization, execution, and online serving.
- Its evaluation module reports annualized return, information ratio, and maximum drawdown rather than presenting a raw signal as sufficient evidence.
- Market Desk takeaway: add a small, explicit historical validation result beside the live signal. Keep it descriptive and separate from the live score because the available history is short and rolling samples overlap.
- Sources: [Qlib README](https://github.com/microsoft/qlib/blob/main/README.md), [Qlib evaluation source](https://github.com/microsoft/qlib/blob/main/qlib/contrib/evaluate.py).

### vn.py

- Repository: [vnpy/vnpy](https://github.com/vnpy/vnpy), 43,854 stars, MIT license at review time.
- `ArrayManager` keeps time-series storage and indicator calculation behind one boundary and exposes SMA, EMA, ATR, RSI, MACD, ADX, and Bollinger calculations.
- Market Desk takeaway: move indicator math out of the large stock narrative module into a pure, dependency-free indicator module. This makes formulas independently testable and prevents UI language from owning quantitative calculations.
- Source: [vn.py ArrayManager](https://github.com/vnpy/vnpy/blob/master/vnpy/trader/utility.py).

### Backtrader

- Repository: [mementum/backtrader](https://github.com/mementum/backtrader), 22,560 stars, GPL-3.0 license at review time.
- Its indicator package includes ATR, Bollinger, MACD, directional movement, RSI, moving averages, and other composable indicators.
- Market Desk takeaway: use several independent indicator families instead of adding more variations of the same moving-average signal. No Backtrader code is copied because its GPL license is not compatible with an unexamined direct reuse path here.
- Source: [Backtrader indicators directory](https://github.com/mementum/backtrader/tree/master/backtrader/indicators).

### QuantConnect LEAN

- Repository: [QuantConnect/Lean](https://github.com/QuantConnect/Lean), 20,764 stars, Apache-2.0 license at review time.
- LEAN defines ATR from true range and uses risk models as a separate layer from signal generation. Its trailing-stop model measures drawdown from the best unrealized value rather than treating the entry signal as permanent.
- Market Desk takeaway: use ATR as a volatility-normalized risk unit, keep risk controls separate from trend scoring, and make the stop/position guidance adapt to volatility.
- Sources: [LEAN ATR](https://github.com/QuantConnect/Lean/blob/master/Indicators/AverageTrueRange.cs), [LEAN trailing-stop risk model](https://github.com/QuantConnect/Lean/blob/master/Algorithm.Framework/Risk/TrailingStopRiskManagementModel.py).

### FinRL

- Repository: [AI4Finance-Foundation/FinRL](https://github.com/AI4Finance-Foundation/FinRL), 15,801 stars, MIT license at review time.
- FinRL documents a train-test-trade pipeline and compares results with baselines instead of evaluating a model only on its training period.
- Market Desk takeaway: do not add reinforcement learning now. The current data and product contract are better served by deterministic signals plus honest validation boundaries.
- Source: [FinRL README](https://github.com/AI4Finance-Foundation/FinRL/blob/master/README.md).

## Selected direction

1. Extract pure indicator calculations into `backend/src/marketdesk/analysis/indicators.py`.
2. Add MACD momentum, ATR percentage, Bollinger position, and 60-day maximum drawdown to the technical summary.
3. Add independent score factors for momentum confirmation, volatility-normalized risk, price extension, and drawdown risk.
4. Add a signal-confluence dimension that explicitly calls out agreement or conflict across trend, momentum, and risk factors.
5. Add a rolling 20-day historical validation that never changes the live score and clearly labels small or overlapping samples.
6. Use ATR to improve stop and position guidance while retaining structural support and resistance.

## Rejected for this iteration

- Machine-learning price prediction: insufficient governed training data and too easy to present false precision.
- Automated order execution: outside the research-only product boundary.
- Full portfolio optimizer: useful later, but it needs stable covariance history and user-level risk constraints first.
- Large indicator catalogue: more indicators can duplicate the same underlying price signal and inflate confidence.

# Stock Analysis Engine V3 Design

Date: 2026-07-25
Status: Approved under delegated product authority
Rollback baseline: `release-2026-07-25`

## 1. Decision

Upgrade the deterministic stock-analysis core without changing the Market Desk navigation or overall Stock Lab layout. The implementation will add four indicator families, an explicit signal-confluence view, a small historical validation, and volatility-aware risk guidance.

The preferred approach is a bounded deterministic engine rather than either of the alternatives below:

- **Add only more prose:** low implementation risk, but the conclusions remain driven by the same limited factors.
- **Introduce ML price prediction:** potentially richer, but the current data history, feature governance, and validation pipeline cannot support honest production claims.
- **Selected — modular deterministic factors plus validation:** materially improves analysis depth while every number remains reproducible and testable.

## 2. Architecture

Create `backend/src/marketdesk/analysis/indicators.py` as a pure calculation boundary. It accepts existing `Bar` or numeric series inputs and returns numbers only. It must not import providers, stores, API code, or presentation text.

`analysis/stock.py` remains the orchestration and explanation layer. It will:

1. build a technical snapshot from bars;
2. translate technical values into visible score factors;
3. calculate signal confluence and historical validation;
4. generate risk guidance and narrative from those results.

Provider access remains under `backend/src/marketdesk/providers/`. Browser code continues to use only `/api/v1/*`.

## 3. Indicators

The technical snapshot gains:

- EMA12 and EMA26;
- MACD line, signal line, and histogram using 12/26/9 exponential averages;
- ATR14 and ATR as a percentage of closing price using Wilder smoothing;
- 20-day Bollinger upper/lower bands and normalized band position;
- 60-day maximum peak-to-trough drawdown.

Unavailable values stay `null`; they are never replaced with a neutral score. At least 35 bars are required for a fully warmed MACD signal, 20 for Bollinger values, 15 for ATR14, and 60 for maximum drawdown.

## 4. Scoring And Confluence

The live score keeps the existing visible additive contract so old consumers remain compatible. Four new factors are added:

- `macd_momentum`: confirms or contradicts the moving-average trend;
- `atr_risk`: penalizes high volatility measured relative to price;
- `bollinger_position`: penalizes extreme upper-band extension and identifies controlled positioning;
- `drawdown_risk`: penalizes a deep 60-day peak-to-trough decline.

A new `signal_confluence` analysis dimension groups factors into trend, momentum, and risk families. It reports positive and negative counts, identifies conflicts, and lowers its own confidence when the families disagree. It does not double-count a separate score adjustment.

## 5. Historical Validation

`StockSignalValidation` evaluates the current deterministic technical setup against prior points in the same bar history:

- signal: close above MA20, MA5 above MA20, and MACD histogram positive;
- forward horizon: 20 trading bars;
- outputs: sample count, positive-return rate, average forward return, worst forward return, availability, and a readable summary;
- minimum: three historical signal samples with a complete forward window.

The validation is explicitly descriptive. Samples may overlap, valuation and point-in-time fundamentals are not available, and the result does not alter the live stance score or forecast confidence.

## 6. Risk Guidance

Risk control uses two separate anchors:

- structural anchor: recent support/resistance;
- volatility anchor: two ATR below the latest close for risk, three ATR above it for a review target when structural resistance is not usable.

Position language becomes volatility-aware. High ATR percentage reduces the suggested trial size; low ATR does not override weak evidence, poor risk/reward, or missing data.

## 7. UI Contract

Stock Lab keeps its current section order, typography, navigation, and responsive structure.

- New technical values appear in the existing technical metric grid.
- Signal confluence appears as one additional card in the existing analysis-dimension grid.
- Historical validation appears as a compact panel near the trend forecast and comparisons.
- The evidence ledger receives the four new factors through its existing list renderer.

No new top-level route, navigation item, or full-width layout system is introduced.

## 8. Error And Missing-data Behaviour

- Short history returns unavailable indicators and a readable validation-unavailable state.
- Zero or invalid close values do not cause division errors.
- Historical validation never fabricates samples and never treats no signal as a failed signal.
- Risk guidance falls back to structural support/resistance when ATR is unavailable.
- The existing insufficient-history dossier remains valid and returns an unavailable validation object.

## 9. Acceptance

- Indicator formulas have focused unit tests, including warm-up and zero-price cases.
- A rising series produces positive MACD/confluence evidence; a volatile drawdown series produces visible ATR/drawdown risk evidence.
- Historical validation uses only data available at each historical point and never changes `stance_score`.
- ATR changes stop and position guidance without removing the research-only disclaimer.
- Existing Stock Lab content order and mobile/desktop layout remain intact.
- Backend API tests, frontend tests, types, build, live-data quality, and `make verify` pass.
- Production deployment is followed by public health and authenticated/anonymous smoke checks.

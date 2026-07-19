# Analyst Workflow V2 Design

Date: 2026-07-19
Status: Approved under delegated product authority

## 1. Decision

Keep the existing editorial market-desk identity, but rebuild the interaction around a five-step analyst loop:

1. Read the market regime and the evidence behind it.
2. Select a strategy that has enough data to run.
3. Understand why each candidate passed and what could invalidate it.
4. Review a stock through balanced technical evidence rather than one threshold.
5. Save an editable thesis and return to it on a review schedule.

The application must prefer an explicit unavailable state over a strategy that silently returns generic results. Scores are research-priority signals, never trading instructions.

## 2. Interaction Direction

The current warm-paper and deep-green visual system remains. The V2 signature is an evidence ledger: each conclusion is paired with a compact line showing the available evidence, missing evidence, and any market-context penalty.

- **Today** becomes a decision briefing. Confidence is formatted without a price-change sign, the risk budget is labelled as a research reference, top market factors are visible, and every next action is a link.
- **Market** shows factor evidence and weights, limits the initial sector list to the most relevant twelve, and offers an explicit path into opportunity research.
- **Opportunities** displays strategy rules before results. Unsupported strategies show why they cannot run. Candidate cards show score composition, market penalty, missing evidence, and risk flags.
- **Stock Lab** shows price plus MA5/20/60 overlays, a scored evidence ledger, balanced bull and bear cases, and evidence coverage. Adding to the watchlist opens an editable thesis form and detects an existing item.
- **Watchlist** is a research journal: stock names link back to Stock Lab, thesis and invalidation are editable, save state is visible, and the latest update time is shown.
- **Data Center** distinguishes observation time from fetch time, displays freshness, coverage and errors, and confirms the result of a manual refresh.

## 3. Deterministic Analysis

### 3.1 Opportunity Strategies

All strategies retain the hard exclusions for ST/delisting risk, invalid price, low liquidity, and small market capitalisation.

- `trend`: requires a daily return from 0.5% through 7%, at least CNY 300 million turnover, and rejects limit-up chasing.
- `sector_improving`: requires stock-level sector membership and sector-strength evidence. If the live universe lacks that mapping, the entire strategy is unavailable with an explicit reason.
- `capital_confirmed`: requires capital-flow coverage. If no eligible stocks have capital-flow data, the strategy is unavailable.
- `oversold_rebound`: is presented as "oversold observation" and requires a daily return from -7% through -1%, positive PE below 50, and at least CNY 100 million turnover. The UI states that this is a daily proxy, not a multi-day reversal confirmation.

Risk-off and cautious regimes apply deterministic context penalties to the final score. The API returns strategy availability, readable rules, base score, context penalty, final score, risk flags, and evidence coverage.

### 3.2 Stock Stance

Stock stance starts at 50 and applies visible impacts for:

- close versus MA20;
- MA5 versus MA20;
- MA20 versus MA60;
- RSI zone;
- 20-day annualised volatility;
- valuation sanity;
- single-day chase risk.

Every impact becomes a displayed evidence item. Missing sector, capital flow, and announcement/research evidence reduce evidence coverage and appear explicitly. The final stance uses the same displayed impacts, so it is reproducible from the page.

## 4. API And State

Provider access remains isolated under `backend/src/marketdesk/providers/`; no browser code calls providers directly. Deterministic rules remain under `backend/src/marketdesk/analysis/`.

The opportunity response gains strategy metadata and score context. The stock dossier gains evidence coverage and score factors. Existing watchlist CRUD remains compatible; the frontend queries the watchlist to detect existing symbols and edits thesis/invalidation through the existing PATCH API.

No new credentials or external provider dependency are required.

## 5. Error And Missing-data Behaviour

- Unsupported strategies render a bounded explanation and a recommended available alternative.
- Missing score factors are never assigned a neutral value.
- Refresh failure retains the previous snapshot and displays the returned error.
- Saving a watchlist note preserves the typed draft on failure and shows a retryable message.
- Existing watchlist membership is visible before the user clicks an action.

## 6. Acceptance

- The four strategy controls produce distinct results or an explicit unavailable state.
- In a risk-off market, context penalties are visible and a raw high score cannot masquerade as an unqualified recommendation.
- Stock stance is not determined solely by close versus MA20.
- The stock chart visibly includes close, MA5, MA20, and MA60.
- A user can edit thesis and invalidation before adding, then edit them again from Watchlist.
- Existing watched stocks display "In watchlist" without requiring another POST.
- Data refresh shows pending, success, or failure feedback and both observation/fetch timestamps.
- The Today -> Opportunities -> Stock Lab -> Watchlist path has no dead end.
- Desktop 1440 x 900, 1536 x 900, and 1920 x 1080 views have no horizontal overflow.
- `make verify` passes, followed by a real-browser workflow against the production build.

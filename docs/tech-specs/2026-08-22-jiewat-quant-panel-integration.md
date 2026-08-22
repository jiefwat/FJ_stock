# Jiewat Quant Panel Integration Research

Date: 2026-08-22
Reference revision: `6a30ec47b7358acfeabdabcc2dd170155113983d`

## Product finding

The useful part of `jiewat-quant-panel` is its shared market-structure workflow, not its Tailwind presentation or TickFlow dependency. Its dashboard, screener, limit ladder, concept analysis, and industry analysis all start from one normalized market snapshot and progressively narrow the question from market state to group strength to a stock-level decision.

StockTS already has the deeper final-decision surface: confidence, evidence coverage, market context, candidate review, and Stock Lab. The integration therefore keeps StockTS as the decision system and adds the missing structure views as upstream research tools.

## Capability map

| Reference capability | Required evidence | StockTS source | Support | StockTS interaction |
| --- | --- | --- | --- | --- |
| Market sentiment | full-market change, indices, liquidity, capital flow | normalized Sina/Tencent/Eastmoney snapshot | supported | decision banner, breadth distribution, market pulse and leaders |
| Strategy pool | current quotes, valuation, flow and optional K-line history | opportunity presets and monitored K-line cache | supported | strategy cards select one detailed candidate queue |
| Entry/exit reasons | strategy rules and deterministic checks | opportunity validation, invalidation and dimensions | supported | visible entry signal, exit condition, hit count and confidence |
| Limit ladder | daily limit state and recent closes | current snapshot plus provider K-lines | derived | level columns, limit-down switch, industry distribution and Stock Lab handoff |
| One-word board | open/high/low/close at the limit price | daily K-line | derived when current daily bar exists | explicit one-word marker; otherwise unavailable rather than guessed |
| Concepts | concept board catalog and constituents | Eastmoney concept boards behind provider adapter | supported | ranked groups, search/sort, leader and constituent drill-down |
| Industries | industry board catalog and constituents | Eastmoney industry boards behind provider adapter | supported | ranked groups, breadth/capital/leader analysis and drill-down |
| Rotation history | multiple historical group snapshots | not currently persisted by StockTS | unavailable in this release | show current cross-section only and state that time-series rotation is pending |
| Sealed-order amount | order-book depth | not in the normalized provider contract | unavailable | do not render a fabricated sealed-order value |

## Reference logic retained

- Dashboard: breadth, distribution, market temperature, turnover, capital confirmation, strongest/weakest groups, and high-activity stocks.
- Strategy system: a registry-like card layer with an active strategy, parameters expressed as readable rules, hit counts, ranking score, entry evidence, and exit/invalidation evidence.
- Limit ladder: exchange-aware limit thresholds, consecutive daily limit verification, level grouping, limit-up/limit-down mode, and one-word-board detection.
- Concept and industry analysis: merge board membership with the current quote snapshot, then calculate average return, breadth, turnover, capital flow, leader score, risk score, and evidence coverage.
- Drill-down: every strategy/group/ladder row can open the same Stock Lab final gate.

## StockTS-specific design decisions

1. Provider access remains in `providers/`; browser code never calls Eastmoney or TickFlow.
2. All scoring and aggregation is deterministic under `analysis/`.
3. Concept and industry are separate provider queries instead of relabeling one board list.
4. Strategy cards reuse the existing opportunity algorithms and monitoring contract instead of importing 18 strategies whose evidence StockTS cannot support.
5. Confidence means evidence coverage and calculation reliability, never probability of a price increase.
6. The existing warm-paper and deep-green visual language remains; only the information architecture and interactions are adopted.

## Interface seams

- `MarketProvider.fetch_market_groups(kind)` is the adapter seam for concept and industry catalogs.
- `analyse_market_dashboard(snapshot)` owns dashboard aggregation.
- `build_strategy_board(snapshot)` owns lightweight cross-strategy summaries.
- `build_limit_ladder(snapshot, history_by_symbol, mode)` owns limit-state derivation.
- `analyse_market_groups(groups, constituents_by_code, kind)` owns group scoring.
- `/api/v1/market-structure/*` is the browser interface for the new modules.

These interfaces keep provider volatility shallow and put reusable market logic behind a small, deep module.

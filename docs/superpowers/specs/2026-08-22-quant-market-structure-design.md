# Quant Market Structure Workbench Design

Date: 2026-08-22

## Goal

Adopt the market dashboard, strategy-pool, limit-ladder, concept, and industry workflows from `jiewat-quant-panel` while preserving StockTS data ownership, confidence semantics, decision-first handoffs, and established visual system.

## Architecture

The provider module gains one bounded market-group adapter. A deterministic `market_structure` analysis module turns normalized quotes, bars, and board membership into four strict response contracts. `MarketService` provides caching and isolated degradation. React consumes only `/api/v1/*` and uses Stock Lab as the final decision gate.

## Pages

- **大盘**: retain the direct action banner, then add a compact dashboard with breadth distribution, liquidity/capital pulse, market extremes, sector leadership, and shortcuts into the three structure modules.
- **候选策略**: lead with a strategy library. Selecting a card updates the existing detailed candidate queue; each card states its category, trigger, exit condition, hit count, and evidence state.
- **连板梯队**: switch between limit-up and limit-down, scan level columns, filter by industry, and open a stock dossier. Daily bars verify the streak and one-word state.
- **概念分析 / 行业分析**: search and sort a group rank, select one group, inspect breadth/capital/leader evidence, then drill into constituents and Stock Lab.

## Human factors

- The first screen answers “what state is the market in?” and “where should I inspect next?”
- Color never carries meaning alone; every state has a label and numeric evidence.
- Dense ranks use stable columns and progressive disclosure, while mobile becomes a card sequence.
- Confidence is always accompanied by evidence coverage or a missing-data explanation.
- Unsupported rotation history and sealed-order data are named as unavailable.

## Acceptance

- Market dashboard calculations are deterministic and bounded.
- Strategy cards map to real StockTS presets and select distinct results.
- Limit thresholds account for ST, ChiNext/STAR, Beijing, and standard A-share boards.
- Concept and industry use different provider catalogs and expose independent failure states.
- All stock references include confidence/evidence coverage and link to Stock Lab.
- Desktop and 390px layouts have no document-level horizontal overflow.
- `make verify` passes before commit and deployment.

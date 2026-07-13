# Market Session Playbook Design

Date: 2026-07-13
Branch: `codex/market-session-playbook`
Status: approved by the user's standing instruction to continue autonomously

## Goal

Turn the long daily-market research page into a three-session playbook without removing evidence, changing market-regime rules, or generating stock actions from the market page.

## Observed Problem

The live market workspace contains more than 9,000 characters, 16 headings, six tables, and 33 articles. The primary verdict is professional, but trend, breadth, mainline, movers, sector Top5, diagnosis, scenarios, events, and guidance all share one long reading stream.

The user cannot quickly answer:

1. What is decided before the market opens?
2. What must be verified during trading?
3. What evidence closes or invalidates the thesis after the session?

## Chosen Direction

Use a chronological market-session playbook.

- A spacing-only refresh is rejected because it preserves the long undifferentiated stream.
- Collapsing every statistic is rejected because intraday verification would become invisible.
- The selected design keeps the decision contract and reorganizes evidence by when it is used.

## Information Architecture

### Phase 01: 盘前框架

- market state and risk budget;
- primary thesis and maximum counter-risk;
- five-step risk-governance rail;
- three scenarios and their invalidation conditions.

### Phase 02: 盘中验证

Always visible:

- trend and breadth dimensions;
- market distribution;
- sector heatmap and mainline introduction.

Default-collapsed intraday dossier:

- wide movers;
- strong/weak sector Top5;
- event and sentiment detail.

### Phase 03: 收盘复核

- professional market diagnosis;
- market-level action discipline and risk limits;
- evidence audit.

## Component Boundary

`render_market_workspace` receives already-rendered content in four explicit slots:

- `distribution_html`;
- `sectors_html` for the always-visible mainline surface;
- `intraday_detail_html` for the collapsed dossier;
- `close_html` for diagnosis and action discipline.

`web.py` remains responsible for composing existing renderers. The market workspace only controls sequence and disclosure; it does not recalculate conclusions.

## Visual Direction

The signature is a market-session ruler with three meaningful time phases. It uses the existing navy, research gold, wine-red, green, and ivory tokens.

```text
01 盘前框架  ->  02 盘中验证  ->  03 收盘复核
```

The ruler is structural, not decorative: each marker corresponds to a different decision responsibility. Supporting cards remain quiet and document-like.

## Responsive Behavior

- Desktop: session ruler stays horizontal; phase content uses existing grids.
- Mobile: ruler becomes a three-row sequence; phase sections become one column.
- Intraday dossier and evidence audit use native `details/summary` with visible keyboard focus.
- No content or stock link is removed from the HTML.
- No horizontal overflow at `390px`.

## Safety

- Stale state continues to pause every decision-rail step.
- Market page continues to set only total risk budget, never individual-stock buy/sell conclusions.
- Collapsed content remains available for audit and search.
- Reduced-motion behavior remains unchanged.

## Acceptance Criteria

- Exactly three session phases appear in chronological order.
- Primary thesis and five-step rail remain before intraday evidence.
- Trend, distribution, heatmap, and mainline remain always visible.
- Wide movers, sector Top5, and event detail move into a default-closed intraday dossier.
- Professional diagnosis and market action discipline appear in close review.
- Existing stale gates, market evidence, and source-audit tests remain valid.
- Desktop and mobile have no horizontal overflow.

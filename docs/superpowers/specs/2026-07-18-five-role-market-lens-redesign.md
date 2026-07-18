# StockTS Five-Role Market Lens Redesign

## Review Participants

This specification records the independent review and adversarial synthesis of five roles:

1. A-share stock analyst.
2. Financial software UI/UX designer.
3. Stock data engineer.
4. Stock analysis strategist.
5. Daily desktop investor and paying user.

## Shared Verdict

The previous release changed typography, color, radius, and CSS ordering but retained the same report-shaped DOM. The user therefore saw a skin change rather than a software redesign. The next release must change source order, first-screen composition, and initial-data delivery while preserving the analysis and snapshot kernel.

## Role Tensions And Decisions

### Analyst Versus Designer

The analyst requires conclusion, action, invalidation, and three reasons in the first screen. The designer requires fewer bordered surfaces and a distinct 12-column desktop composition. The decision is one integrated decision board: thesis and reasons occupy eight columns; action and invalidation occupy four.

### Strategist Versus Compression

The strategist rejects one semantic template for all modules. Shared components are allowed, but semantics remain distinct:

- Market is an observable fact ledger with rule inference clearly separated.
- Portfolio is a risk-treatment queue ordered by hard triggers, thesis failure, concentration, confirmation, then daily P/L.
- Stock is a thesis-and-falsification surface with strongest support, strongest counter-evidence, and next validation.
- Opportunity is a conditional forecast with horizon, reason, confirmation, invalidation, tradability, and frozen feedback.

### Data Engineer Versus Instant UI

Market and unfiltered opportunity already have validated scheduled snapshots. Their core verdict, action, risk, time, coverage, and up to three findings must render into server HTML so the first paint does not say "waiting". The bootstrap JSON and existing JavaScript renderer remain the authority for complex sections and idempotent hydration. Stock and portfolio remain user/context scoped and must not share global caches.

### Paying User Versus Research Tooling

The user does not want to see how the system researches before seeing what changed. Deep research becomes a closed secondary disclosure labelled in user language. The first screen must answer in ten seconds: what happened, what to do, and what invalidates the view.

## Desktop Information Architecture

```text
+---- 184px rail ----+----------------------- 60px security command -----------------------+
| brand              | active module | stock search | target | data time | state | refresh |
| market             +---------------------------------------------------------------------+
| portfolio          | decision board: thesis + 3 reasons (8) | action + invalidation (4) |
| stock              +---------------------------------------------------------------------+
| opportunity        | module-owned primary facts / treatment queue / forecast list        |
| data center        | secondary evidence, complete lists, research disclosure             |
| account at bottom  |                                                                     |
+--------------------+---------------------------------------------------------------------+
```

## Required Structural Changes

- Move global stock search into the command bar; keep the sidebar limited to navigation and a bottom account surface.
- Keep exactly one visible module identity, target, evidence time, delivery state, and refresh control.
- Place the key findings inside the decision board source DOM, not below unrelated sections.
- Move stock deep research after the decision board and primary analysis in source DOM; render it as a closed disclosure.
- Retain current `data-engine-*` hooks, API payloads, hash/query routing, cache keys, snapshot gates, and refresh-failure preservation.
- Server-render core fields from a validated `initial_payload`; retain the escaped bootstrap JSON for complex hydration.
- Remove visual dependence on CSS `order` for stock decision priority.

## Visual Direction

- Market Lens: calm 184px ocean rail, white command bar, mist canvas, and one dark ocean decision surface.
- Normal-width Chinese typography; monospace only for market data, codes, dates, and percentages.
- 8-10px structural corners rather than universal pill cards.
- A segmented evidence scale on the decision surface, driven by real ready/total coverage.
- Copper marks active actions; A-share red/green appear only with explicit directional text.
- Dense primary tables use 44px rows and sticky headers; evidence and research remain visually secondary.

## Safety Boundaries

Do not modify snapshot compatibility checks, latest-pipeline coverage checks, workspace API contracts, external enrichment decisions, prediction immutability, portfolio privacy boundaries, scheduled jobs, or analysis scoring. Do not expose provider names, capability identifiers, traces, gateways, credentials, or absolute holdings paths.

## Acceptance

- At 1440x900, target appears by y=160, conclusion by y=260, and action, invalidation, and three reasons are fully visible by y=620.
- The first screen contains no expanded deep-research controls and no full-width four-cell research-protocol strip.
- Module name and evidence time each appear once visually.
- Valid market/opportunity snapshots render core content in the initial HTML without corresponding waiting copy.
- Stock deep research follows decision and primary analysis in source order and is closed by default.
- The sidebar is at most 184px and the command bar at most 60px.
- The new screenshot differs structurally: decision board areas, command search, and research disclosure change position and area, not only color.
- The native product is desktop-only: no mobile dock, phone breakpoint contract, or mobile search fallback ships.
- Existing native workspace, API, snapshot, navigation, and privacy contracts pass at 1440x900 and 1680x1050.

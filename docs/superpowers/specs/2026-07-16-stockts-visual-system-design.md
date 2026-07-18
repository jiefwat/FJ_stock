# StockTS Modern Decision Cockpit Design

## Goal

Keep every native research workspace, route, interaction, API contract, scheduled snapshot, and analysis result intact while making StockTS feel like a modern desktop investment product rather than an HTML research report.

## Product Thesis

The first screen must answer three questions in order: what is the judgment, what should the user do, and what could invalidate it. Research tools and supporting evidence follow the decision instead of competing with it.

## Visual Direction

- Modern decision cockpit: cool mist background, white decision surfaces, deep ocean navigation, restrained copper emphasis, and China-market red/green only where direction is explicit.
- Normal-width Chinese typography: `Avenir Next`, `HarmonyOS Sans SC`, `MiSans`, and `PingFang SC` for headings and body copy. Monospace is limited to prices, percentages, codes, dates, and compact status data.
- Soft structure: 12-14px primary card corners, subtle borders, controlled shadows, and no global grid texture.
- Decision-first hierarchy: one strong judgment surface, smaller action and risk surfaces, quiet evidence sections, and compact controls.
- Desktop application frame: fixed navigation and session bar, independently scrolling active workspace, and no page-level overflow at desktop widths.

## App Frame

- Use a 204px deep-ocean sidebar with reduced visual weight, quieter account/search cards, and a rounded active navigation item.
- Keep the research-session bar fixed at 56px and limit it to current module, research target, data status, evidence time, and refresh.
- Keep workspace content centered at a maximum width of 1420px with 24-44px desktop gutters.
- Use subtle atmospheric background gradients only; do not use repeating grid or ruled-paper textures.
- Preserve the existing hash routes, keyboard shortcuts, module switch behavior, forms, and mobile dock.

## Stock First-Screen Order

The stock workspace presents content in this visual order without changing its data or interaction contracts:

1. Stock title and service state.
2. Compact research context.
3. Stock switcher and market-screening entry.
4. Core judgment.
5. Today action and maximum risk within the judgment surface.
6. Judgment shortcuts and key findings.
7. Six-lens deep research as a secondary evidence tool.
8. Full lists, supplemental analysis, evidence disclosure, and manual refresh.

The deep-research tool remains fully functional but no longer occupies the first decision viewport.

## Component Language

- Primary surfaces use 14px corners; compact controls use 9-11px corners.
- Buttons use a consistent 40px control height, sentence-case labels, visible focus, and a single deep-ocean primary treatment.
- Inputs use a quiet white surface with a clear focus ring and no heavy inset styling.
- Tables and long lists remain dense, but row separation comes from spacing and weak rules rather than boxed cells.
- Hover motion is limited to a 1px lift on actionable cards and is disabled under reduced motion.
- Empty, stale, partial, and unavailable states retain their current wording and behavior.

## Responsive Contract

- 1440x900 and 1680x1050 are the primary design targets.
- Desktop keeps the sidebar and session bar visible while only the active workspace scrolls.
- Tablet collapses dense grids without hiding actions or evidence status.
- At 390x844, document scrolling returns, the mobile dock remains usable, controls retain 44px touch targets, and no horizontal overflow is introduced.

## Accessibility And Privacy

- Keyboard focus uses a visible copper ring.
- Red and green never carry meaning without text or labels.
- Tabular numerals remain enabled for market data.
- No external fonts, CDN assets, provider logos, capability IDs, traces, gateway names, or credentials are exposed.

## Acceptance

- A final `StockTS modern decision cockpit skin` layer is the visual authority.
- The final layer uses normal-width heading and body font stacks and excludes condensed display fonts.
- The final body background has no repeating grid texture.
- Primary cards use at least 12px radii with restrained shadows and weak borders.
- In the stock workspace, `.engine-judgment` is ordered before `.stock-deep-research`.
- The fixed desktop app frame, 1420px content boundary, active-workspace scrolling, and 390px mobile document-scrolling contract remain intact.
- Existing module HTML, API, snapshot, research, and routing tests remain unchanged and pass.
- Browser verification at 1440x900, 1680x1050, and 390x844 shows no clipped navigation, hidden primary action, sticky overlap, or horizontal overflow.

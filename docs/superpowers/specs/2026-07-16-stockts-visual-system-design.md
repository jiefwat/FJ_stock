# StockTS Visual System Design

## Goal

Keep the current native research workspaces and all data behavior intact while making the product feel like a modern institutional research terminal instead of a layered dashboard template.

## Direction

- Editorial research desk: ink, warm paper, graphite, restrained copper, and China-market red/green.
- Dense but legible: compact navigation and tables, stronger whitespace around conclusions, and tabular numerals for all market data.
- Clear hierarchy: judgment is the primary surface; action, risk, evidence, and detail become progressively quieter.
- Low ornament: 4-8px structural corners, thin rules, almost no decorative gradients, and shadows reserved for the primary decision surface.
- Local-first typography: Avenir Next / IBM Plex Sans for editorial headings, HarmonyOS Sans SC / MiSans / Source Han Sans SC for Chinese text, and IBM Plex Mono for data.

## Scope

- Restyle the native app shell, sidebar, navigation, workspace header, decision spine, research sections, lists, tables, buttons, disclosures, and mobile dock.
- Preserve every existing route, form, data attribute, interaction, workspace module, loading state, and API contract.
- Do not add external font or asset dependencies.
- Do not expose provider branding or infrastructure identifiers.

## Responsive Contract

- Desktop: 214px research navigation and a content canvas up to 1580px.
- Tablet: keep the decision hierarchy while allowing grids to collapse naturally.
- Mobile: retain the current top controls and bottom module dock, use one-column evidence cards, preserve 44px touch targets, and prevent horizontal overflow.

## Accessibility Contract

- Visible keyboard focus using the copper accent.
- Red/green never carry meaning without text or labels.
- Tabular numerals improve scanning and comparison.
- All reveal motion is disabled under `prefers-reduced-motion`.

## Acceptance

- Visual-contract tests assert the font stacks, numeric typography, restrained geometry, decision spine, desktop width, mobile breakpoint, and reduced-motion support.
- Existing workspace HTML and research/API tests remain unchanged.
- Desktop and mobile screenshots show no clipped navigation, overflowing tables, or hidden primary actions.

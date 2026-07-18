# StockTS Visual System Design

## Goal

Keep the current native research workspaces and all data behavior intact while making the product feel like a modern institutional research terminal instead of a layered dashboard template.

## Direction

- Editorial research desk: ink, warm paper, graphite, restrained copper, and China-market red/green.
- Dense but legible: compact navigation and tables, stronger whitespace around conclusions, and tabular numerals for all market data.
- Clear hierarchy: judgment is the primary surface; action, risk, evidence, and detail become progressively quieter.
- Low ornament: 4-8px structural corners, thin rules, almost no decorative gradients, and shadows reserved for the primary decision surface.
- Local-first typography: Avenir Next / IBM Plex Sans for editorial headings, HarmonyOS Sans SC / MiSans / Source Han Sans SC for Chinese text, and IBM Plex Mono for data.

## Desktop App Frame

- Treat the product as a running research application, not a document: the sidebar and a 58px research-session bar remain fixed while only the active workspace scrolls.
- The session bar always answers four questions without duplicating analysis content: current module, research target, delivery state, and evidence time.
- Keep module navigation in the left rail, module-owned actions inside each workspace, and expose one session-level `刷新当前判断` control that delegates to the active module action.
- Scope each `.workspace-pane` to the available viewport. Switching modules replaces the active workspace in place and resets only that workspace scroll position.
- Use one thin copper status scale on the session bar as the visual signature. Avoid more gradients, floating cards, oversized hero typography, or decorative dashboard chrome.
- Keep the existing hash routes, forms, API payloads, research results, keyboard shortcuts, mobile dock, and provider-neutral language unchanged.

## Scope

- Restyle the native app shell, sidebar, navigation, workspace header, decision spine, research sections, lists, tables, buttons, disclosures, and mobile dock.
- Preserve every existing route, form, data attribute, interaction, workspace module, loading state, and API contract.
- Do not add external font or asset dependencies.
- Do not expose provider branding or infrastructure identifiers.

## Responsive Contract

- Desktop: 214px research navigation, a fixed research-session bar, and an independently scrolling content canvas up to 1420px.
- Tablet: keep the decision hierarchy while allowing grids to collapse naturally.
- Mobile: return to document scrolling, retain the current top controls and bottom module dock, use one-column evidence cards, preserve 44px touch targets, and prevent horizontal overflow.

## Accessibility Contract

- Visible keyboard focus using the copper accent.
- Red/green never carry meaning without text or labels.
- Tabular numerals improve scanning and comparison.
- All reveal motion is disabled under `prefers-reduced-motion`.

## Acceptance

- Visual-contract tests assert the font stacks, numeric typography, restrained geometry, decision spine, desktop app viewport, session bar, 1420px content width, mobile scroll reset, and reduced-motion support.
- Existing workspace HTML and research/API tests remain unchanged.
- At 1440x900 and 1680x1050, the sidebar and session bar remain visible while the active pane scrolls without page-level overflow.
- Desktop and mobile screenshots show no clipped navigation, overflowing tables, hidden primary actions, or sticky elements covering content.

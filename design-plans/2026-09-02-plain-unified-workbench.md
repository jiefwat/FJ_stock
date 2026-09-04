# Plain Unified Research Workbench

Written against: e868aff2a3a3865636450691b32750ed96afbf63 plus the preserved uncommitted application work

## Evidence chain

- Surface: authenticated React workbench under `frontend/src/app/App.tsx`, covering the route-stage consumers for Decisions, Market, Opportunities, Review, Stock Lab, Ask, Holdings, Limit Ladder, Concepts, and Industries.
- Problem: the user reports that differently sized cards across the current interface make the visual rationale unreadable. The loaded cascade confirms the contradiction: `frontend/src/main.tsx` imports `styles.css` and then a 5,162-line `coherence.css` containing successive card, editorial, spatial, and alignment passes that redefine the same route surfaces at multiple breakpoints.
- Design evidence: `docs/superpowers/specs/2026-07-19-market-intelligence-workbench-design.md` requires a calm, readable analyst workbench; `docs/superpowers/specs/2026-08-22-quant-market-structure-design.md` requires stable dense ranks, progressive disclosure, and preserved confidence/market semantics. The user's selected direction is explicitly plain and unified.
- Owner: `frontend/src/app/coherence.css`, imported after the legacy feature stylesheet by `frontend/src/main.tsx`; shared page framing is owned by `frontend/src/components/WorkbenchPageHeader.tsx`.
- Scope and affected surfaces: all authenticated routes rendered inside `.route-stage`, the shell/navigation around them, shared filters, tables, lists, disclosures, loading/error/empty states, and responsive behavior at phone, tablet, and desktop widths.
- Uncertainty: feature markup is intentionally heterogeneous, so the visual contract must normalize existing owners without changing data, route, or disclosure behavior.

## Design decision

Replace the accumulated override history with one final visual contract based on three levels only: a borderless page canvas; a ruled section with one shared heading treatment; and flat rows/cells inside that section. Reserve a tinted panel for one primary conclusion or an actual warning. Use one 8px control radius, one 10px section radius, no decorative shadows, and no nested card elevation. Preserve red-up/green-down, confidence, missing-evidence, and degraded-state semantics.

## Reuse

- `WorkbenchPageHeader` and `PageTaskRail` remain the shared page framing owners.
- Existing `.panel`, `.panel-title`, table/list, disclosure, semantic state, and route-specific classes remain the markup owners; the new cascade gives them one consistent presentation.
- Exemplar: the Stock Lab editorial direction already accepted in the active requirement, where typography, whitespace, and hairlines replace nested surfaces.

## Changes

1. `frontend/src/app/coherence.css`
   - Change: replace layered historical overrides with one compact token and component contract for shell, page framing, sections, rows, controls, semantic states, and responsive layouts.
   - Preserve: existing feature grids where they express useful comparison, all semantic data colors, sticky navigation behavior, and progressive disclosures.
   - Verify: every route uses the same page edge, section edge, title rhythm, control radius, row divider, and selected state; nested modules no longer create independent shadows or competing radii.
2. `frontend/src/components/WorkbenchPageHeader.tsx` and current route consumers
   - Change: retain the single heading and page-path system; adjust markup only if a route cannot conform through the shared contract.
   - Preserve: active-step observation, focus movement, reduced-motion behavior, and deep-link opening.
   - Verify: one page title and one compact path per route, with no duplicate visual header.
3. `frontend/src/**/*.test.tsx`
   - Change: update only assertions invalidated by a deliberate presentation or wording change; add a cross-route contract check if source tests do not already cover the shared frame.
   - Preserve: all behavioral, authentication, analysis, and data-state assertions.
   - Verify: interaction tests continue to pass without weakening functional coverage.

## Scope

- Inherit: every current and future page rendered within `.route-stage` receives the shared tokens and section contract.
- Verify: authentication, command search, desktop sidebar, mobile bottom navigation and More menu, all ten authenticated routes, empty/loading/error states, and 320px/390px/768px/1024px/1440px widths.
- Exclude: provider logic, deterministic analysis, API contracts, persistence, financial calculations, email behavior, and the content hierarchy already encoded in feature components.

## Validation

- Product: a user can move from page title to primary conclusion to evidence without interpreting card size as undocumented importance.
- Interface: inspect all authenticated routes at 1440px and 390px; exercise navigation, strategy selection, stock selection, disclosures, group selection, and mobile More; verify no horizontal overflow or origin-owned console errors.
- System: confirm `coherence.css` is the only final appearance layer and contains no successive named redesign passes or conflicting radius/shadow systems.
- Repository: `make verify` -> backend lint/types/tests, frontend types/tests/build, and live-data gate all pass.

## Stop conditions

- Stop if a current uncommitted functional change must be reverted, if a route requires changing data semantics to fit the design, or if the shared contract hides unavailable/confidence information.

## Design documentation

- After acceptance and validation: record the three-level surface contract and route-matrix evidence in `docs/superpowers/market-intelligence-workbench/review.md` and `test.md`.

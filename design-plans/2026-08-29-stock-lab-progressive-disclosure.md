# Stock Lab Single-Decision Progressive Disclosure

Written against: `e868aff2a3a3865636450691b32750ed96afbf63`

## Evidence chain

- Surface: `frontend/src/features/stocks/StockLabPage.tsx`, route `/stocks?symbol=<symbol>` after a stock has loaded.
- Problem: the loaded page still presents several parallel first-layer choices. `StockFocusBoard` shows verdict, discipline, operation conditions, price disclosure, why, risk, trend, a sector action, and an ask action; the page then repeats evidence and ask destinations in `stock-section-directory`, while `PageTaskRail` provides a second directory for the same destinations. The user's reported outcome is that the page remains content-heavy and its directory is unclear even after the card styling was flattened.
- Design evidence: `docs/superpowers/specs/2026-08-16-stock-financial-news-intelligence-design.md` requires compact conclusion phrases and folds detailed periods and news; `frontend/src/features/stocks/StockLabPage.tsx` already owns a single-open-panel state for evidence, questions, and detail; `frontend/src/components/WorkbenchPageHeader.tsx` already owns section navigation and opens a target disclosure before scrolling to it.
- Owner: `StockLabPage`, `StockFocusBoard`, `StockDecisionDrivers`, `PageTaskRail`, and the Stock Lab editorial rules in `frontend/src/app/coherence.css`.
- Scope and affected surfaces: the loaded Stock Lab page on desktop, tablet, and mobile; empty stock selection, API contracts, scoring, account boundaries, and other workbench routes are unchanged.
- Uncertainty: browser inspection of the loopback URL was blocked by the browser URL policy. Source, test, and direct user evidence establish the duplicate hierarchy, but visual spacing must be accepted at 1440px, 768px, and 390px during implementation.

## Design decision

Make the loaded page expose one decision before one directory. The first layer contains stock identity, the verdict, any blocking condition, position discipline, and the existing collapsed operation conditions. `PageTaskRail` becomes the only visible page directory. Evidence, price, questions, and professional detail remain available, but only inside the three existing mutually exclusive disclosure groups. Remove duplicate summary strips and duplicate ask actions rather than restyling them again.

## Reuse

- Existing `PageTaskRail` active-section and open-before-scroll behavior.
- Existing `openPanel` / `openDeepSection` state in `StockLabPage`.
- Existing `StockDecisionDrivers`, `StockAskRouter`, `StockDeepDossier`, `stock-condition-disclosure`, and `stock-price-disclosure` compositions.
- Existing `--ink`, `--muted`, `--line`, `--accent`, `--surface`, `--radius-control`, and responsive device-mode rules in `frontend/src/app/coherence.css`.
- Exemplar: the current single-open-panel directory composition at the end of `frontend/src/features/stocks/StockLabPage.tsx`.

No new visual primitive is required.

## Changes

1. `frontend/src/features/stocks/StockLabPage.tsx`
   - Change: reduce `StockFocusBoard` to identity, verdict, evidence-quality metadata, blocking condition, position discipline, and the existing collapsed operation conditions. Remove `stock-brief-strip`, `stock-focus-actions`, and `stock-mobile-decision-actions`. Preserve the sector destination as a quiet inline link beside the sector label; keep ask entry only in `StockAskRouter`.
   - Preserve: action wording, confidence and coverage caveat, blocker priority, entry/stop/take-profit content, source context, and stock identity.
   - Verify: before opening a directory item, the loaded page has one ask destination, no visible `为什么 / 风险 / 趋势` summary strip, and no duplicate desktop/mobile action group.
2. `frontend/src/features/stocks/StockLabPage.tsx`
   - Change: move `stock-price-disclosure` from `StockFocusBoard` into `StockDecisionDrivers`, after the four compact company/message/price/change summaries. It stays collapsed and only exists while the evidence group is open; history-unavailable copy and lazy `StockTrend` loading remain unchanged.
   - Preserve: financial and news availability states, external news links, trend data, chart lazy loading, and the no-price-history fallback.
   - Verify: choosing `依据` opens one group containing the compact drivers and a closed price-chart row; choosing `追问` or `明细` closes it.
3. `frontend/src/features/stocks/StockLabPage.tsx` and `frontend/src/components/WorkbenchPageHeader.tsx`
   - Change: keep `PageTaskRail` as the sole visible directory and remove the redundant `进一步查看 / 一次只展开当前需要的一层 / 依据 · 追问 · 明细` header. Retain the semantic `stock-section-directory` wrapper and its three disclosure owners.
   - Preserve: the four `结论 / 依据 / 追问 / 明细` destinations, active-section tracking, keyboard focus after navigation, reduced-motion behavior, deep-link opening, and one-open-panel behavior.
   - Verify: there is one visible directory label, every rail destination lands on the matching section, and a deep link to company evidence or scoring opens the required parent and child disclosure.
4. `frontend/src/app/coherence.css`
   - Change: update the final Stock Lab editorial block for the smaller decision composition, inline sector link, evidence-contained price disclosure, and headerless directory. Remove touched selectors that only serve the deleted summary strip or duplicate action groups, and reconcile touched Stock Lab overrides so each retained presentation has one final owner in `coherence.css`.
   - Preserve: typography-led presentation, neutral sheet background, line-based grouping, focus styles, risk emphasis, 44px mobile targets, and reduced-motion handling.
   - Verify: no large filled card returns; desktop uses whitespace and rules for hierarchy, tablet remains single-column where required, and 390px has no horizontal scroll or clipped controls.
5. `frontend/src/features/stocks/StockLabPage.test.tsx` and `frontend/src/components/WorkbenchPageHeader.test.tsx`
   - Change: replace assertions for the redundant directory header and duplicate focus actions with regressions for one visible directory, one ask entry, evidence-contained price disclosure, one-open-panel behavior, and deep-link opening.
   - Preserve: stock switching, search keyboard behavior, source context, unavailable states, evidence lazy loading, and decision correctness coverage.
   - Verify: focused Vitest tests fail on the current duplicate hierarchy and pass after the composition change.

## Scope

- Inherit: all loaded A-share, Hong Kong, and US stock analyses that render `StockLabPage`.
- Verify: blocked, conditional, and eligible decisions; price history available and unavailable; financial/news unavailable; direct deep links; desktop, tablet, and 390px mobile.
- Exclude: backend analysis changes, scoring changes, provider access, email reminders, global sidebar redesign, empty stock selection, Ask page redesign, and unrelated legacy CSS cleanup.

## Validation

- Product: open a stock, understand the action and discipline without expanding anything, then use the single page path to inspect evidence, ask a question, and open professional detail; each transition exposes only one secondary group.
- Interface: verify `/stocks?symbol=SH.600519` in blocked and non-blocked fixtures at 1440px, 768px, and 390px; check long Chinese text, missing price history, missing financial/news data, focus return, deep links, and reduced motion.
- System: confirm all moved content reuses the existing data and disclosure owners, no second ask/navigation pattern is introduced, and browser code still depends only on `/api/v1/*`.
- Repository: `pnpm --dir frontend test --run src/features/stocks/StockLabPage.test.tsx src/components/WorkbenchPageHeader.test.tsx && make verify` -> focused tests and the complete repository gate pass.

## Stop conditions

- Stop if moving the chart into `StockDecisionDrivers` changes data-fetch timing, if a deep link cannot open the correct parent disclosure through the existing state model, or if removing duplicate actions leaves the sector or ask destination unreachable at any supported viewport.

## Design documentation

- After acceptance and validation: record the single-decision-first hierarchy, removal of duplicate action/navigation surfaces, responsive acceptance, and verification results in `docs/superpowers/market-intelligence-workbench/TODO.md` and `docs/superpowers/market-intelligence-workbench/test.md`.

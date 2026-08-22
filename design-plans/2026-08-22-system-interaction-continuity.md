# System Interaction Continuity

Written against: `c2ca0020153dae5d198f385e5ff3fb71dcb095af`

## Evidence chain

- Surface: `frontend/src/features/ask/AskStockPage.tsx`, route `/ask`
- Problem: Financial-Skill `llm_answer` responses discard the matched stock identity, intent, observation time, and stock-specific follow-up route even when the API supplies them.
- Design evidence: `docs/superpowers/specs/2026-07-25-ask-stock-workbench-design.md` requires a result header with matched stock, answer intent, market observation time, and source.
- Owner: `AskResult` and the assistant-message follow-up area in `frontend/src/features/ask/AskStockPage.tsx`.
- Scope and affected surfaces: named `llm_answer` rendering and its follow-up actions; stockless general answers remain compact.
- Uncertainty: none; the normalized response already carries all required fields.

- Surface: `frontend/src/features/decisions/DecisionCenterPage.tsx`, route `/decisions`
- Problem: filter controls precede actionable events, delaying the page's primary task and contradicting its decision-first hierarchy.
- Design evidence: `docs/superpowers/specs/2026-08-16-decision-change-center-design.md` says the page leads with what needs attention today and separates user actions from system monitoring.
- Owner: `DecisionCenterPage` section composition.
- Scope and affected surfaces: section order only; filters, empty states, event cards, and mutations are preserved.
- Uncertainty: none.

- Surface: `frontend/src/app/App.tsx`, global refresh action
- Problem: successful refresh feedback says only `数据已同步`, so users cannot tell whether the action covered the whole system or when the resulting snapshot completed.
- Design evidence: `docs/superpowers/specs/2026-07-19-market-intelligence-workbench-design.md` requires every refresh action to show scope, completion, and resulting data time.
- Owner: app-shell refresh mutation and API response typing.
- Scope and affected surfaces: global refresh success notice; failure wording and retained workspace state stay unchanged.
- Uncertainty: none; `/api/v1/refresh` already returns snapshot metadata.

## Design decision

Make context persist across each user action. A named financial-Skill answer receives the same identity header and stock follow-ups as deterministic stock analysis; the Decision Center presents actionable events before configuration controls; and global refresh confirmation states both its all-site scope and the returned completion time. Reuse existing components and visual language so the changes repair hierarchy and feedback without creating parallel patterns.

## Reuse

- Existing `ask-result-head`, intent labels, confidence display, evidence link, and follow-up prompt composition.
- Existing `decision-event-section actionable`, filter panel, and monitoring section.
- Existing `Meta`, refresh notice, and date formatting utilities.
- Exemplar: `frontend/src/features/ask/AskStockPage.tsx` stock-analysis result header.

No new visual primitive is required.

## Changes

1. `frontend/src/features/ask/AskStockPage.tsx`
   - Change: render the stock result header for `llm_answer` when both symbol and name are present, including intent, source, confidence, observation time, and the Stock Lab evidence link; enable existing stock follow-up prompts for that response.
   - Preserve: concise answer-first layout, expandable detail, and compact rendering for truly stockless answers.
   - Verify: a Ningde Times financial-Skill fixture displays `宁德时代`, `SZ.300750`, `风险核对`, observation time, source/confidence, follow-ups, and a Stock Lab link for that symbol.
2. `frontend/src/features/decisions/DecisionCenterPage.tsx`
   - Change: move the actionable event section before the reminder-filter panel.
   - Preserve: filtering behavior, monitoring order, unread actions, retries, and empty state.
   - Verify: DOM order places `需要处理` before `提醒筛选`, with monitoring after both.
3. `frontend/src/lib/api.ts` and `frontend/src/app/App.tsx`
   - Change: type the refresh response and use its `meta.fetched_at` to show `全站数据已同步 · 更新于 <time>`.
   - Preserve: pending state, disabled action, error feedback, and data retention on failure.
   - Verify: refresh feedback contains scope, completion, and returned refresh time.
4. Focused tests and active requirement evidence
   - Change: add regressions for all three behaviors and record acceptance evidence in the active requirement files.
   - Preserve: existing fixtures and unrelated acceptance coverage.
   - Verify: focused Vitest suite and repository verification pass.

## Scope

- Inherit: all named financial-Skill stock answers, all Decision Center event feeds, and the global refresh action.
- Verify: deterministic stock answers, stockless Skill answers, empty decision feeds, monitoring-only feeds, and refresh errors.
- Exclude: backend response changes, provider changes, new scoring logic, navigation redesign, and unrelated page styling.

## Validation

- Product: ask about a non-Moutai stock through the financial Skill, review today's actionable decision changes, and trigger a global refresh; each flow must retain identity, priority, and completion context.
- Interface: test named and stockless Skill answers, actionable and monitoring event combinations, successful and failed refreshes, and existing responsive boundaries.
- System: confirm reuse of the existing stock header/follow-ups, decision sections, and shell notice rather than new parallel components.
- Repository: `PATH=/Applications/Cursor.app/Contents/Resources/app/resources/helpers:$PATH make verify` -> all backend, frontend, build, and live-data gates pass.

## Stop conditions

- Stop if the refresh endpoint no longer returns `meta.fetched_at`, named Skill answers do not carry a stable symbol/name contract, or section reordering exposes a filter-state ownership conflict.

## Design documentation

- After acceptance and validation: record the three interaction-continuity regressions and verification evidence in `docs/superpowers/market-intelligence-workbench/TODO.md`, `test.md`, and `review.md`.

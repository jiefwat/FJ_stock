# StockTS Essence Workspaces Design

Status: approved by the user's standing instruction to proceed autonomously.

## Goal

Turn the five core workspaces into concise decision surfaces. A reader should understand the current conclusion, required action, largest risk, and data state without reading explanatory narration.

## Problem Evidence

The sample page currently renders the following density before this change:

| Workspace | Visible characters | Headings | Paragraphs | Details |
| --- | ---: | ---: | ---: | ---: |
| Daily market | 4,209 | 18 | 50 | 2 |
| Portfolio | 5,389 | 6 | 47 | 4 |
| Stock | 4,988 | 15 | 21 | 2 |
| Opportunities | 11,533 | 5 | 100 | 3 |
| Data center | 4,585 | 4 | 26 | 1 |

The main failure is not font size. The renderers repeat module descriptions, workflow explanations, English eyebrows, methodology packaging, and the same conclusion across several cards.

## Selected Approach

Use renderer-level simplification with progressive evidence disclosure.

- Keep the primary verdict, current action, invalidation or risk boundary, key numbers, refresh control, and evidence status visible.
- Remove module descriptions, background copy, method narration, decorative English labels, and repeated subtitles from the generated HTML.
- Keep raw tables, source ledgers, and lower-priority evidence in native `details` elements that are closed by default.
- Limit front-row records and place overflow records behind a single disclosure control.
- Use CSS only to tighten hierarchy and spacing. CSS must not hide narration that still exists in the HTML.

Rejected alternatives:

1. Smaller type and spacing only: the reading burden remains unchanged.
2. Hide everything with CSS: inaccessible content and tests still retain the unwanted narration.
3. Collapse every module: the first screen would lose the risk and evidence needed for a safe decision.

## Content Contract

Every core workspace uses the same four-layer contract:

1. Verdict: one state and one sentence.
2. Action: the next allowed action or explicit pause.
3. Risk: no more than three front-row risks, invalidations, or blockers.
4. Evidence: compact key metrics plus one closed evidence ledger.

The following content is non-negotiable:

- stale-data hard gates and paused actions;
- conditional actions, position limits, and invalidation rules;
- source, date, confidence, and missing-data status;
- financial disclaimer and no-guaranteed-return language;
- the boundary that the market page sets total risk budget but does not create stock trades.

## Workspace Decisions

### Daily Market

- Keep one market state strip and one primary market verdict.
- Replace the duplicate session ruler plus narrated session headings with three compact phase labels.
- Keep the risk-budget decision rail but remove its methodology heading and descriptive paragraph.
- Show scenario triggers and actions; remove prose explaining what scenarios are.
- Keep trend/width and the strongest market direction visible.
- Move distribution detail, intraday movers, event tables, full sector lists, and audit rows into one closed `Market evidence` drawer.
- Remove the page-level module description.

### Portfolio

- Keep the portfolio verdict, market risk budget, primary risk, and next review.
- Reduce the metric strip to values without explanatory footnotes.
- Keep the first three treatment actions visible; move the rest to overflow.
- Keep only the highest-severity exposure visible; move the complete exposure and boundary ledger into one closed `Portfolio evidence` drawer.
- Remove English eyebrows and the narration under the holdings boundary title.
- Keep editing controls available after the decision surface.

### Stock

- Keep identity, price, trade date, refresh, one committee verdict, strongest evidence, strongest counter-evidence, and confidence.
- Replace the five full-width decision cards with a compact trigger strip.
- Keep current action, position cap, entry trigger, reduce trigger, invalidation, and prohibited action visible.
- Show at most three highest-priority risks before scenarios.
- Keep compact diagnostic conclusions; move facts, limitations, raw technical panels, role debate, and the evidence table into one closed `Research evidence` drawer.
- Remove English eyebrows, method-chain copy, repeated analysis-entry narration, and repeated page subtitle.

### Opportunities

- Keep the opportunity gate, risk budget, scanned count, evidence-ready count, and eligible count.
- Replace the five narrated funnel cards with a compact count strip.
- Show three candidates on the front row; each card keeps state, strategy, one support item, one counter item, data date, and the stock-analysis link.
- Keep up to three exclusions or market risks visible.
- Move remaining candidates, source notes, and legacy supporting panels into one closed `Screening evidence` drawer.
- Remove the page-level explanation and all `research funnel` narration.

### Data Center

- Keep the data gate, blocked/warning/ready counts, next recovery action, and refresh control.
- Show at most three recovery steps; each step keeps issue and verification, while repeated business-consequence narration is removed from the front row.
- Replace verbose downstream impact cards with compact status rows.
- Keep the complete source ledger closed by default.
- Remove the page subtitle, English eyebrows, and explanations of recovery order or downstream impact.

## Shell And Visual Direction

The visual direction is a quiet execution blotter: warm paper background, dark navy navigation, muted gold action accent, red only for blocked risk, and green only for verified readiness. Existing brand colors remain; the redesign spends its visual emphasis on a single signature element: the primary verdict band at the top of every workspace.

- Remove sidebar narration and module-description paragraphs.
- Preserve current typography and application navigation to avoid an unrelated rebrand.
- Tighten vertical rhythm around section boundaries and use rules, not decorative cards, for secondary structure.
- Keep visible keyboard focus and `prefers-reduced-motion` behavior.
- At 390px width, primary verdict, action, and risk must appear before any evidence drawer.

## Testing

Renderer tests must fail first and then prove:

- prohibited narration and decorative labels are absent from generated HTML;
- every workspace still has exactly one primary verdict;
- stale states still pause actions;
- required risk, invalidation, refresh, source, and evidence controls remain;
- front-row limits are enforced while overflow evidence remains reachable;
- desktop and mobile CSS retain responsive, focus, and reduced-motion contracts.

Browser acceptance uses `1440x1000` and `390x844` viewports. It checks that each workspace opens at the top, the primary verdict is readable without scrolling past narration, drawers are closed by default, and no horizontal overflow appears.

## Acceptance Targets

- No `.module-desc` or decorative English eyebrow is rendered in the five core workspaces.
- Each core workspace has one primary verdict and no more than four visible top-level content groups before its evidence drawer.
- Opportunity front row contains at most three candidates; portfolio front row contains at most three treatment items.
- Raw evidence and all retained records remain accessible through a default-closed `details` element.
- Existing safety-gate, professional-dossier, routing, authentication, and refresh tests continue to pass, except documented pre-existing baseline failures.
- The change does not modify providers, analysis algorithms, holdings data, reports, timers, credentials, or external service configuration.

# Research Terminal Density V2 Design

Date: 2026-07-13  
Branch: `codex/research-terminal-density-v2`  
Status: approved by the user's standing instruction to proceed autonomously

## 1. Goal

Improve both content presentation and visual design without changing the existing market, portfolio, opportunity, or stock decision contracts.

The release must solve two observed problems:

1. On a 390px viewport, global data status and navigation consume most of the first screen before the active module appears.
2. Portfolio and opportunity pages render every record as an equally prominent card, so users cannot distinguish the research front row from the full audit trail.

## 2. Chosen Direction

Use a hierarchy-and-density redesign rather than a cosmetic reskin or a multi-window trading terminal.

- A cosmetic reskin is rejected because it leaves the excessive first-screen height and long card streams unchanged.
- A multi-window terminal is rejected because it introduces unnecessary state and resembles an order-entry product.
- The selected direction keeps the existing server-rendered HTML and deterministic research models, then adds a compact global research tape and progressive disclosure inside dense modules.

## 3. Information Architecture

The reading order remains:

```text
global action gate
  -> active workspace verdict
  -> research front row
  -> risk and boundary evidence
  -> complete audit trail
```

No downstream module may create a second market authority or bypass stale/blocked rules.

### 3.1 Global Research Tape

Replace the six equal freshness cards with one semantic tape:

- primary: action gate and its reason;
- core: data status and trading date;
- secondary: quote date, evidence coverage, and provider;
- route: direct link to the data center.

The primary item is visually dominant. Secondary items remain visible on desktop and are hidden on mobile, where the data-center route provides the full audit surface.

### 3.2 Portfolio Front Row

- Render the first five queue items in the always-visible treatment queue.
- Keep remaining queue items inside an explicit `查看其余 N 项处置` disclosure.
- Render the first four position boundaries in the always-visible boundary grid.
- Keep remaining boundaries inside `查看其余 N 项边界`.
- Preserve the model order so risk-priority ordering remains authoritative.
- Preserve every holding and boundary in the HTML; this is progressive disclosure, not truncation.

### 3.3 Opportunity Front Row

- Render the first six candidate dossiers as the always-visible research front row.
- Keep remaining candidates inside `查看其余 N 只候选`.
- Preserve every candidate and its evidence, counter-evidence, data status, and link.
- Keep the risk register adjacent and sticky only on wide desktop layouts.

## 4. Visual System

The current navy, aged-gold, and ivory identity remains. The redesign reduces repeated large cards and spends visual emphasis on one signature component: the Research Tape.

### 4.1 Tokens

| Role | Token |
| --- | --- |
| Deep navy | `#10283d` |
| Ink | `#101923` |
| Research gold | `#bd8b33` |
| Risk red | `#b94336` |
| Verified green | `#247153` |
| Ivory surface | `#fffdf8` |
| Canvas | `#ece8dc` |

Typography roles:

- display: `Avenir Next Condensed`, then existing Chinese fallbacks;
- body: `PingFang SC` / `Hiragino Sans GB`;
- data and labels: `SFMono-Regular` / `JetBrains Mono`.

### 4.2 Desktop Wireframe

```text
┌ sidebar ─────┬──────────────── research tape ─────────────────────┐
│ brand/search │ ACTION GATE │ DATA STATE │ DATE │ EVIDENCE │ SOURCE│
│ navigation   ├─────────────────────────────────────────────────────┤
│              │ module header                                      │
│              │ primary verdict                                    │
│              │ front-row research          │ risk register        │
│              │ [expand remaining records]  │                      │
│              │ boundaries / evidence ledger                       │
└──────────────┴─────────────────────────────────────────────────────┘
```

### 4.3 Mobile Wireframe

```text
┌ brand ───────────────────────┐
│ [stock code________] [analyze]│
│ market | portfolio | stock | …│
├ ACTION GATE ──────────────────┤
│ data state      trading date │
│ data details ->               │
├ active module title ──────────┤
│ primary verdict               │
│ front-row records             │
│ view remaining N              │
└───────────────────────────────┘
```

## 5. Responsive Behavior

At `max-width: 680px`:

- collapse quick stock search into one row;
- hide the brand subtitle and sidebar note;
- reduce business-navigation item width;
- show only action gate, data state, trading date, and the data-center route in the research tape;
- make the tape and all front-row grids single-column;
- keep the document free of horizontal overflow.

At `min-width: 921px`:

- keep opportunity risk register sticky within its workspace;
- keep the research tape on one row when space permits;
- use two-column candidate and boundary grids.

## 6. Interaction And Accessibility

- Native `details/summary` elements provide disclosure without new client state.
- Summary copy includes the hidden record count.
- Existing hash navigation, account permissions, refresh forms, and candidate links remain unchanged.
- New links and summaries receive visible `:focus-visible` treatment.
- Motion is limited to the existing page reveal and disabled by `prefers-reduced-motion`.

## 7. Data And Error Behavior

- Renderers receive existing immutable dossiers and do not fetch or recalculate data.
- Empty queues, candidates, exposures, and boundaries retain directed empty states.
- Stale/blocked behavior remains authoritative: no active ranking, current price action, old target range, or numeric stop may reappear.
- Progressive disclosure must never change record counts or link context.

## 8. Testing

Add regression tests for:

- one research tape with primary/core/secondary roles and a data-center route;
- mobile CSS hiding secondary tape fields and compacting search/navigation;
- portfolio front-row and overflow counts while preserving every queue and boundary record;
- opportunity front-row and overflow counts while preserving every candidate link;
- unchanged one-primary-verdict rules and stale safety gates;
- desktop/mobile browser smoke with no horizontal overflow.

Run focused Web suites, Python 3.9 contract tests, ruff, compileall, and full pytest with the five known daily-pipeline baseline failures reported separately.

## 9. Non-Goals

- No new data source, broker connection, automatic order, or calibrated price forecast.
- No SPA framework or client-side store.
- No redesign of account isolation, server configuration, DSA, notification delivery, or the daily pipeline.
- No removal of audit evidence or research records.

## 10. Acceptance Criteria

- At 390px, the active workspace title or primary verdict begins materially earlier than the current version and the page has no horizontal overflow.
- The global action gate is more prominent than provider or evidence-channel metadata.
- Portfolio shows five queue items and four boundaries before disclosure when more records exist.
- Opportunity shows six candidates before disclosure when more records exist.
- Expanding disclosures reveals all original records and links.
- Desktop retains adjacent risk context and a coherent research-document visual hierarchy.
- Existing stale/blocked, authorization, routing, and refresh tests continue to pass.

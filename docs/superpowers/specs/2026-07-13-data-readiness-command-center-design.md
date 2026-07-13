# Data Readiness Command Center Design

Date: 2026-07-13
Branch: `codex/data-readiness-command-center`
Status: approved by the user's standing instruction to continue autonomously

## 1. Problem

The current data center is visually tidy but operationally shallow. It shows one summary row, a flat status table, and at most three alerts. When stale data blocks the entire research terminal, the page does not answer four questions:

1. Which data domain should be restored first?
2. Which research modules are affected by each failure?
3. What evidence proves that a data domain has recovered?
4. Where can the complete source, coverage, and missing-field record be audited?

The live page currently contains only 649 characters, one table, and no explicit recovery sequence, while the market and opportunity modules contain thousands of characters of downstream analysis. This makes the upstream data failure harder to act on than the downstream research it invalidates.

## 2. Options Considered

### Option A: Restyle The Existing Table

Add stronger colors, icons, and status chips to the current four-column table.

- Advantage: minimal code change.
- Rejected: it does not create recovery priority, downstream impact, or verification guidance.

### Option B: Add More Technical Columns

Expose channel, coverage, missing fields, and update timestamps in one wide table.

- Advantage: complete audit detail is always visible.
- Rejected: desktop becomes dense and mobile becomes a horizontal-scrolling operations table.

### Option C: Recovery Command Center

Create an action-first data dossier with a readiness gate, ordered restoration runbook, downstream impact matrix, and collapsed source ledger.

- Advantage: tells the user what to do while preserving complete audit detail.
- Selected: it matches the product's action-gate research language and keeps the page useful on mobile.

## 3. Product Thesis

The data center has one job: restore trustworthy research as quickly and audibly as possible.

Its reading order is:

```text
data readiness gate
  -> ordered recovery runbook
  -> downstream module impact
  -> complete source ledger
```

The page does not fetch data, run jobs automatically, or override stale/blocked rules. It converts existing data-quality rows into a deterministic operations dossier.

## 4. Domain Model

Create a dedicated dossier boundary under `stock_ts.research`.

### 4.1 DataReadinessGate

- state: `影响分析`, `需复核`, or `正常`;
- action: the allowed research behavior;
- thesis: why the gate has this state;
- blocked_count, warning_count, ready_count, total_count;
- next_step: the first recovery or maintenance action.

### 4.2 DataRecoveryStep

- priority: stable numeric recovery order;
- category and current status;
- severity: blocked or warn;
- issue: stale, missing, or degraded evidence;
- consequence: the existing business impact text;
- verification: the date/update evidence to check after refresh.

Recovery order is meaningful and therefore may use numbered steps:

1. market and K-line inputs;
2. candidate universe and fund-flow inputs;
3. news and event context;
4. announcements and fundamentals;
5. full-chain validation as the final acceptance check.

Within the same rank, blocked rows precede warnings and existing row order remains stable. Full-chain validation is never presented as a repairable source; it closes the runbook after upstream inputs are restored.

### 4.3 DataImpactLane

The dossier maps existing data domains to four downstream research modules:

| Module | Required domains |
| --- | --- |
| Daily market | market, K-line, news, full-chain |
| Portfolio | market, K-line, fund flow, fundamentals, full-chain |
| Stock | K-line, technical, fund flow, news, announcements, fundamentals, full-chain |
| Opportunities | market, K-line, candidate universe, fund flow, news, full-chain |

Each lane is blocked when any required domain is blocked, degraded when none is blocked but one is warning, and ready otherwise. The lane lists the affected domains instead of inventing a new score.

### 4.4 DataLedgerEntry

Every original row is preserved with category, channel, status, date/update evidence, coverage, missing fields, impact, and level. The ledger is presentation-complete but default-collapsed.

## 5. Page Structure

### 5.1 Readiness Gate

A dark navy operational brief opens the workspace. In blocked state it uses one wine-red edge, not an all-red surface.

It shows:

- current data state;
- allowed research action;
- one-sentence thesis;
- blocked, warning, ready, and total counts;
- the unique next step;
- the existing manual refresh control.

### 5.2 Recovery Runbook

Only blocked and warning domains appear in the runbook. Each step shows the real category, issue, consequence, and verification evidence. If no domain needs recovery, the section becomes a directed ready state rather than disappearing.

### 5.3 Module Impact Matrix

Four compact lanes show whether market, portfolio, stock, and opportunity research are blocked, degraded, or ready. The matrix explains why the global gate propagates to downstream modules.

### 5.4 Source Ledger

Native `details/summary` preserves the complete source audit without consuming the first screen. The summary includes the total domain count. The ledger uses cards on mobile instead of forcing a wide table.

## 6. Visual Direction

The subject is a research data operations room, not a generic admin dashboard.

### Tokens

- command navy: `#10283d`;
- command ink: `#101923`;
- recovery gold: `#bd8b33`;
- blocked wine: `#7d342f`;
- ready green: `#247153`;
- paper: `#fffdf8`;
- canvas: `#ece8dc`.

### Signature

The ordered restoration rail is the one new visual signature. A thin vertical line connects meaningful numbered recovery steps. Other surfaces stay flat, quiet, and document-like.

### Typography

- display: existing `Avenir Next Condensed` role;
- body: existing Chinese sans-serif role;
- source, dates, statuses, and step numbers: existing mono role.

## 7. Responsive Behavior

At desktop widths:

- readiness gate uses a verdict column and a wider thesis column;
- recovery runbook and impact matrix form a two-column operations grid;
- source ledger uses a compact six-column table.

At `max-width: 680px`:

- gate, metrics, recovery runbook, and impact lanes become one column;
- manual refresh remains visible;
- source entries render as stacked audit cards;
- no raw channel or missing-field string can cause horizontal overflow.

## 8. Safety And Error Behavior

- The dossier is deterministic and never calls a provider.
- Existing status, missing-field, freshness, and impact calculations remain authoritative.
- Empty rows produce a blocked gate with an explicit `数据域清单为空` recovery step.
- Raw source labels are escaped by the renderer.
- No credential, URL secret, internal address, or automatic write action is introduced.
- The existing refresh form remains the only mutation entry.

## 9. Testing

Add focused tests for:

- blocked, warning, ready, and empty dossier states;
- stable recovery priority and preservation of every ledger row;
- impact-lane propagation without invented scores;
- gate-first HTML order and one primary verdict;
- complete source ledger with default-closed disclosure;
- escaped channel and missing-field text;
- mobile CSS without horizontal table dependence;
- existing stale and optional-context rules.

Run focused Web tests, Python 3.9 contracts, Ruff, compileall, full pytest with known daily-pipeline failures reported separately, and browser smoke at `1440x1000` and `390x844`.

## 10. Non-Goals

- No scheduler, retry engine, or background worker.
- No new external provider or data credential.
- No automatic repair button that claims success without evidence.
- No change to market, portfolio, stock, or opportunity decision rules.
- No change to authentication, DSA, Signal Desk, Nginx, or systemd timers.

## 11. Acceptance Criteria

- The first screen explains the data gate, allowed action, counts, and unique next step.
- Blocked/warning domains appear in deterministic recovery order.
- All four business modules expose downstream impact and named blockers.
- Every original data row remains available in the source ledger.
- Source ledger is closed by default and keyboard accessible.
- At 390px the page has no horizontal overflow and recovery steps remain readable.
- Existing stale/blocked behavior remains unchanged across other modules.

# Professional Stock Workbench V2 Design

## 1. Background

The production baseline is commit `d8747819fcd00091b86648c594bc9984db3dd447`.
It already provides authentication, four research workspaces, a server-side research
adapter, account-isolated holdings, data-quality gates, and a production deployment.

The rejected iteration changed the page's operating logic and made the application
harder to use. This design therefore treats the current routes, login flow, account
flow, holdings operations, and workspace navigation as compatibility contracts.

The goal is not to add another research console. The goal is to make StockTS a
professional daily decision workstation whose statistics are reproducible, whose
conclusions show evidence and counter-evidence, and whose external enrichment remains
an invisible server-side implementation detail.

## 2. Product Goal

StockTS should help an owner answer five questions quickly and safely:

1. What state is the market in today?
2. Is risk expanding or contracting beneath the index?
3. Which sectors have breadth, persistence, and evidence rather than one-stock noise?
4. What is the strongest evidence for and against a stock?
5. What condition would strengthen, invalidate, or postpone the current conclusion?

Success means the answer is useful even when external enrichment is unavailable.
External data may improve coverage and confidence, but it must never become a page
dependency or the sole source of a trading conclusion.

## 3. Scope Guard

### In scope

- Improve desktop and mobile information hierarchy without changing workspace routes.
- Add deterministic market statistics derived from existing snapshots and candidate
  data.
- Upgrade stock analysis into an evidence matrix with confidence and hard risk gates.
- Fuse normalized server-side research evidence into statistics and analysis when it
  is available.
- Keep all public copy and API fields provider-neutral.
- Add tests that protect login, navigation, holdings, data freshness, privacy, and
  degraded operation.

### Out of scope

- No automatic trading, order entry, brokerage connection, or return promise.
- No replacement of authentication, account storage, holdings forms, or hash routing.
- No user-facing provider logo, provider name, skill list, trace id, API key, or
  external-research entry point.
- No new systemd timer. Optional enrichment runs inside the existing daily pipeline or
  on the existing authenticated research endpoint.
- No migration or deletion of `.env`, user accounts, holdings, snapshots, reports, or
  notification settings.

## 4. Chosen Approach

Use progressive evidence fusion.

The existing local provider and analysis chain remains the primary deterministic
source. The existing server-side research adapter is a secondary evidence source. A
normalization boundary converts both into provider-neutral domain objects before any
page or product API sees them.

```text
Local snapshot / provider data
  -> deterministic market statistics and stock evidence matrix
  -> evidence fusion and confidence downgrade
  -> existing workspace view model
  -> existing authenticated page shell

Optional server-side research capabilities
  -> strict allowlist and privacy filter
  -> normalized evidence only
  -> evidence fusion (never direct page rendering)
```

The page never calls a vendor-specific endpoint. Missing, late, malformed, or
rate-limited enrichment is recorded as a coverage gap and the local result remains
usable.

## 5. Market Statistics

Add a focused domain module for reproducible market calculations. The statistics must
use raw counts and candidate observations, not narrative inference.

### Core metrics

| Metric | Definition | Purpose |
| --- | --- | --- |
| Advance ratio | advancing / max(advancing + declining + unchanged, 1) | Measures market participation |
| Breadth ratio | advancing / max(declining, 1) | Separates index strength from broad strength |
| Limit balance | limit-up count - 2 x limit-down count | Applies a larger penalty to hard downside risk |
| Extreme spread | count above +3% - count below -3% | Measures short-term payoff asymmetry |
| Strong-move breadth | count above +6% by theme and total | Detects genuine expansion versus isolated spikes |
| Weak-move breadth | count below -6% by theme and total | Detects concentrated damage and risk propagation |
| Sector participation | themes with at least two confirming stocks / themes observed | Rejects single-stock themes |
| Evidence coverage | ready required blocks / required blocks | Caps confidence when data is incomplete |

### Market regime

The market regime is determined by explicit thresholds and hard gates:

- `risk_off`: stale core data, limit-down stress, or broad negative extreme spread.
- `defensive`: breadth ratio below 0.8 or evidence coverage below 60%.
- `balanced`: mixed breadth and sector rotation without broad confirmation.
- `constructive`: breadth ratio at least 1.3, positive extreme spread, and at least two
  confirmed themes.
- `risk_on`: constructive conditions plus strong evidence coverage and no hard risk
  gate.

The regime determines a risk budget, not a buy signal. The UI must display the formula
inputs, freshness, and the reason for any confidence downgrade.

### Market UI

Keep the existing `#market` workspace. The first viewport becomes a compact market
pulse board:

```text
Market regime and risk budget            Data time / coverage
----------------------------------------------------------------------
Advance ratio | Breadth | Limit balance | +3/-3 spread | +6/-6 spread
----------------------------------------------------------------------
Strong themes with participation         Primary risk and invalidation
```

Detailed heat maps, movers, news, and evidence remain below the fold. Repeated summary
cards are removed. Desktop uses the available content width; mobile becomes one column
without horizontal scrolling.

## 6. Stock Analysis Method

Keep the existing eight professional dimensions but make every dimension auditable.

1. Technical trend
2. Price-volume structure
3. Fund behavior
4. Valuation and fundamentals
5. News and events
6. Statistical position
7. Risk constraints
8. Execution plan

Each dimension returns:

- `score`: 0-100, produced only from explicit inputs.
- `supporting_evidence`: up to three dated facts.
- `counter_evidence`: up to three dated facts.
- `coverage`: ready, partial, stale, or missing.
- `confidence`: high, medium, low, or blocked.
- `strengthen_condition`: a measurable condition that would improve the view.
- `invalidation_condition`: a measurable condition that would invalidate it.

### Composite decision

The composite score uses fixed weights, but hard gates override the score:

- Stale quote or K-line data blocks price-triggered actions.
- A material negative event prevents an aggressive verdict until reviewed.
- Missing fundamentals prevents a high-confidence valuation conclusion.
- Missing fund-flow data lowers confidence but may use price-volume evidence as a
  clearly labelled proxy.
- User cost and position size affect risk handling, never the evidence that a stock is
  attractive.

The final output is a condition-based decision record:

```text
verdict -> current action -> strongest support -> strongest counter-evidence
        -> strengthen condition -> invalidation condition -> confidence
```

The page keeps the existing `#stock` route, stock search, and holdings context. It does
not add a chat box or external-research drawer.

## 7. Invisible Research Enrichment

Reuse the existing safe research client and allowlisted capabilities.

### Market enrichment

- Index structure
- Market breadth
- Hot-stock distribution
- Sector selection
- Macro and market events

### Stock enrichment

- Financial quality
- Business structure
- Institutional expectations
- Event risk
- Industry position
- Announcements and reports

Only code, name, sector, and bounded research questions may leave the service. Holdings
quantity, cost, weight, account identity, notes, cookies, and session data must never be
sent upstream.

Normalized evidence can raise coverage or add a dated supporting/counter fact. It
cannot directly set a verdict, action, target position, stop loss, or opportunity rank.
The public response and HTML must reject provider names, capability ids, trace ids,
gateway fields, and secrets.

## 8. Visual Direction

The visual thesis is a calm A-share decision desk, not a dashboard template.

- Ink: `#10263A`
- Paper: `#F4F7F8`
- Surface: `#FFFFFF`
- Brass: `#B4853A`
- Confirmed: `#0E6A5C`
- Risk: `#B64A3C`

Typography keeps the existing offline-safe Chinese family and monospaced market data.
The signature element is the market pulse rail: a single horizontal band that encodes
participation, stress, coverage, and the current risk budget. Decorative cards and
large empty gutters are removed.

The page must support:

- 1440 px and 1280 px desktop widths using the available canvas.
- 390 x 844 mobile without horizontal overflow.
- Visible keyboard focus.
- Reduced motion.
- Red/green meaning accompanied by text or symbols.

## 9. Error Handling and Freshness

- Core data stale: block price-specific action and show the stale timestamp.
- External enrichment unavailable: keep local analysis, mark the missing evidence, and
  lower confidence.
- Individual capability failure: preserve other capability results.
- Invalid dynamic fields: discard them at normalization; never render raw payloads.
- No candidate or sector coverage: show an actionable empty state, not sample data.
- API and page errors must not contain keys, endpoint paths, trace ids, or stack traces.

## 10. Testing Strategy

### Characterization protection

- Login, logout, registration, account isolation, and holdings write paths.
- Workspace hashes and sidebar navigation.
- Existing data freshness and public read-only safety gates.
- Existing production health endpoint.

### New unit tests

- Every market metric, zero-denominator behavior, thresholds, and hard gates.
- Sector participation rejects a single-stock theme.
- Stock evidence matrix keeps support and counter-evidence separate.
- Hard risk gates override a high composite score.
- External evidence changes coverage but cannot directly set an action.
- Provider terms and internal metadata cannot enter public dictionaries or HTML.

### Integration and browser tests

- Local-only analysis works without an API key.
- Optional enrichment failure does not break market or stock pages.
- Authenticated market and stock pages render the new decision surfaces.
- 1440 px, 1280 px, and 390 px layouts have no horizontal overflow.
- Core forms, links, and hash navigation remain functional.

## 11. Deployment and Rollback

Deploy only the isolated branch after focused tests, full lint, local browser checks, and
a tracked-file review.

Before deployment:

1. Back up the current production source and record the current commit.
2. Preserve `.env`, user databases, holdings, snapshots, reports, Nginx, and all existing
   timers.
3. Do not create or modify a timer for this feature.

After deployment:

1. Restart only `stock-ts.service`.
2. Verify `/healthz`, root redirect, login, authenticated market, authenticated stock,
   account management, and one read-only analysis request.
3. Verify all existing timers remain active.
4. Roll back to `d8747819` immediately if login, navigation, holdings, or either core
   workspace regresses.

## 12. Acceptance Criteria

- The implementation is based on `d8747819` in an isolated worktree.
- Login, accounts, holdings, routes, and workspace navigation retain their behavior.
- Market statistics are deterministic, tested, dated, and visible with their coverage.
- Stock conclusions show support, counter-evidence, confidence, triggers, and
  invalidation.
- The application remains useful with all optional research capabilities disabled.
- No provider logo, provider name, skill list, external-research entry point, trace id,
  gateway field, or secret appears in the page or public API.
- Desktop uses the available width and mobile has no horizontal overflow.
- No new timer or deployment path is introduced.
- Public health, authentication, market, stock, and account smoke checks pass after
  deployment.

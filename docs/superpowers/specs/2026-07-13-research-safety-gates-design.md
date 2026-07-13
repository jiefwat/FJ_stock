# Research Safety Gates Design

**Date:** 2026-07-13  
**Scope:** Phase 1 of the StockTs system upgrade  
**Status:** Approved for implementation under the user's autonomous-improvement direction

## 1. Purpose

The market and stock workspaces now present structured research, but three defects can still make a weak or stale input look more authoritative than it is:

1. Extreme downside risk can be classified as `轮动` because the rotation rule runs before the risk-release rule.
2. The stock memo does not receive a typed quote-freshness status, so stale K-line data can still produce a non-zero-confidence research verdict.
3. Metadata-only dictionaries, invalid comparison values, and empty event payloads can count as complete research blocks.

This phase adds a small, typed safety boundary between data-quality assessment and research conclusions. It does not redesign the data platform, add new providers, or change the visual hierarchy.

## 2. Design Principles

- Safety conditions override opportunity conditions.
- A stale or blocked price input cannot produce an actionable market or stock conclusion.
- Evidence completeness is determined by usable values, not container truthiness.
- Research modules consume typed status; they do not infer safety from Chinese warning text.
- Existing date and pipeline-freshness checks remain the source of truth. This phase translates their result into `EvidenceStatus` instead of adding another trading-calendar algorithm.
- Missing optional evidence degrades a conclusion; missing or stale required quote evidence blocks it.

## 3. Options Considered

### Option A: Reorder conditions and add warning-string checks

This is the smallest patch: move the risk-release branch above rotation, then match more warning substrings in `web.py` for the stock page. It is rejected because safety would remain coupled to display copy and future wording changes could silently disable the gate.

### Option B: Shared typed research gate

Reuse `EvidenceStatus` and add a compact immutable input-quality contract. The Web orchestration layer maps its existing data-quality result into that contract and both research models consume the same status semantics. This option is selected because it fixes the confirmed defects without broad platform work.

### Option C: Replace the entire data-quality architecture

Move all freshness, completeness, source lineage, and pipeline health checks into a new domain service. This is a useful long-term direction but is rejected for Phase 1 because it would mix a safety fix with a large migration of `web.py`, `data_chain.py`, providers, and reports.

## 4. Domain Contract

Add an immutable contract in `stock_ts.research.evidence`:

```python
@dataclass(frozen=True)
class ResearchInputQuality:
    quote_status: EvidenceStatus = EvidenceStatus.COMPLETE
    fundamental_coverage: float = 0.0
    valuation_comparable: bool = False
    event_status: EvidenceStatus = EvidenceStatus.MISSING
    blockers: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
```

The contract is intentionally small:

- `quote_status` is the hard gate used by market and stock research.
- `fundamental_coverage` is the fraction of six recognized quality metrics with valid numeric values.
- `valuation_comparable` is true only when a valid numeric historical percentile exists, or when both absolute PE and a valid industry median exist.
- `event_status` is based on usable titled announcements or news items.
- `blockers` and `limitations` preserve audit text without making research logic parse that text.

Helper functions may construct this contract from `StockRawData`, but Web freshness remains derived from the existing data-quality checks.

## 5. Market Gate

### 5.1 Hard freshness gate

`assess_market_regime` continues to accept `quote_status`. `STALE` and `BLOCKED` produce:

- stage: `数据暂停`
- risk budget: `0%`
- confidence: `0`
- a visible blocker and refresh condition

### 5.2 Risk-first classification

Classification order becomes:

1. data pause
2. risk release
3. attack
4. rotation
5. defense
6. range-bound

`limit_down_count >= 30` or `breadth_ratio < 0.55` therefore overrides high heat and nominal breadth. The existing attack requirement that limit-down count is below 10 remains.

### 5.3 Contradiction penalty

Confidence must reflect conflicting market signals as well as missing dimensions. At minimum:

- a risk-release condition combined with heat at or above 55 incurs a confidence penalty;
- an attack/rotation candidate with elevated limit-down count incurs a confidence penalty;
- confidence remains deterministic and bounded from 0 to 100.

The exact penalty is a transparent rule, not a statistical claim.

## 6. Stock Gate

`build_stock_research_memo` accepts a `ResearchInputQuality` argument with a safe backward-compatible default derived from the input data.

### 6.1 Hard freshness gate

When `quote_status` is `STALE` or `BLOCKED`, the verdict is:

- status: `数据暂停`
- confidence: `0`
- strongest counter-evidence: quote blocker or stale-data limitation
- next review: refresh the latest trade-date quote before reassessment

The memo may still render known facts for audit, but scenarios and surrounding copy must not imply that the current price setup is actionable.

### 6.2 Fundamental coverage

Only these valid numeric fields count toward fundamental coverage:

- `revenue_yoy`
- `net_profit_yoy`
- `roe`
- `gross_margin`
- `debt_to_assets`
- `ocf_to_profit`

Keys such as `source`, `date`, `industry`, and `business_summary` are metadata/context and do not count. A block with zero recognized numeric metrics is `MISSING`; a partial block is `DEGRADED`.

### 6.3 Comparable valuation

Comparable valuation is available only when:

- `pe_percentile` is numeric and within 0 to 100; or
- PE is numeric and positive, and `industry_pe_median` is numeric and positive.

Absolute PE/PB/PS can still be displayed, but they do not elevate the research status by themselves.

### 6.4 Usable events

Events count only when at least one announcement or news item has a non-empty title after trimming. Empty mappings, blank titles, and malformed values do not elevate status or confidence.

### 6.5 Verdict ceiling

Among fundamentals, comparable valuation, and usable events, if two or more are unavailable, the highest status is `技术性观察`. Complete valid inputs retain the existing `条件研究` behavior.

## 7. Web Integration

`web.py` remains orchestration only:

1. Run the existing `_assess_data_quality` flow.
2. Convert the existing freshness result into a typed `EvidenceStatus` once.
3. Pass that status to `assess_market_regime` and `build_stock_research_memo`.
4. Stop deriving research safety by matching warning sentences.

The migration should use an explicit field or helper at the `DataQualityView` boundary. Display warnings remain for users, but their wording is no longer a control-flow API.

## 8. Compatibility

- Existing callers that omit the new stock quality argument continue to work through input-derived defaults.
- Existing HTML renderers consume the same market and stock memo types.
- No provider schema, account data, report artifact, notification route, or deployment configuration changes.
- Existing complete-data fixtures continue to produce `条件研究`.

## 9. Tests and Acceptance Criteria

Required regression tests:

1. Heat 60, breadth 1.0, and 80 limit-down stocks produce `风险释放`, never `轮动`.
2. Conflicting high-heat/high-risk inputs have lower confidence than an internally consistent regime input.
3. A stale stock quote produces `数据暂停` with confidence 0.
4. `{source, date}`-only fundamentals have zero metric coverage and do not improve status or confidence.
5. Invalid valuation comparison values do not count as comparable evidence.
6. Empty or blank-title event payloads do not count as event evidence.
7. Existing valid financial, valuation, and announcement inputs remain `条件研究`.
8. Web orchestration passes the same typed freshness status into market and stock research.
9. Focused research/Web tests pass; full-suite results are compared with the recorded baseline before deployment.

## 10. Deployment Boundary

Deployment is an incremental source patch to the existing StockTs service. Before restart:

- validate the patch with `git apply --check` on the server;
- back up the affected `src/stock_ts` files;
- run targeted compile/import checks and a temporary preview service;
- restart only `stock-ts.service`;
- verify the public site with authenticated or public `GET` as currently configured.

Do not replace `.env`, account holdings, reports, Nginx configuration, timers, DSA files, or unrelated server changes. The rollback unit is the backed-up affected source files plus a service restart.

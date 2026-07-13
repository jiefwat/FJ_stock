# Research Safety Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent stale quotes, extreme downside risk, and metadata-only evidence from producing authoritative market or stock research conclusions.

**Architecture:** Extend the existing `stock_ts.research.evidence` contract with deterministic input-quality helpers, then make market and stock research consume the typed result. `web.py` translates its existing freshness checks into `EvidenceStatus` once and passes the same typed boundary to both research models; renderers remain unchanged.

**Tech Stack:** Python 3.11 frozen dataclasses, existing StockTs domain models, pytest, ruff, standard-library Web application.

---

## File Map

- Modify `src/stock_ts/research/evidence.py`: add the immutable research-input quality contract and pure validation helpers.
- Modify `src/stock_ts/research/market_regime.py`: prioritize risk release and penalize contradictory signals.
- Modify `src/stock_ts/research/stock_memo.py`: consume typed quality, block stale quotes, and base verdict/evidence on usable values.
- Modify `src/stock_ts/web.py`: expose a typed quote status on `DataQualityView` and pass it to both research models.
- Modify `tests/test_research_evidence.py`: verify fundamental, valuation, and event validation.
- Modify `tests/test_market_regime.py`: lock risk-first classification and contradiction penalties.
- Modify `tests/test_stock_research_memo.py`: lock stale-data and metadata-only degradation behavior.
- Modify `tests/test_web_data_accuracy.py`: verify freshness assessment produces a typed research gate.
- Modify `tests/test_web_market_research_workspace.py`: verify market integration uses the typed gate without warning-string matching.
- Modify `tests/test_web_stock_research_workspace.py`: verify stock memo rendering preserves `数据暂停`.
- Create `docs/research/research-safety-gates-test-report.md`: record focused, full-suite, local-smoke, and deployment verification.

## Task 1: Add the typed input-quality contract

**Files:**
- Modify: `src/stock_ts/research/evidence.py`
- Modify: `tests/test_research_evidence.py`

- [ ] **Step 1: Write failing tests for usable evidence**

Add tests that import `ResearchInputQuality`, `fundamental_metric_coverage`, `has_comparable_valuation`, and `has_usable_events` and assert:

```python
def test_metadata_only_fundamentals_have_zero_coverage() -> None:
    assert fundamental_metric_coverage(
        {"source": "tushare", "date": "2026-03-31", "industry": "银行"}
    ) == 0.0


def test_fundamental_coverage_counts_only_numeric_quality_metrics() -> None:
    coverage = fundamental_metric_coverage(
        {"revenue_yoy": 12.0, "roe": "8.5", "gross_margin": "invalid"}
    )
    assert coverage == 2 / 6


def test_comparable_valuation_requires_valid_numeric_reference() -> None:
    assert has_comparable_valuation({"pe_percentile": 20}) is True
    assert has_comparable_valuation({"pe_percentile": 120}) is False
    assert has_comparable_valuation(
        {"pe_ttm": 12, "industry_pe_median": 15}
    ) is True
    assert has_comparable_valuation({"industry_pe_median": "invalid"}) is False


def test_events_require_a_non_blank_title() -> None:
    assert has_usable_events([{"title": "  "}], []) is False
    assert has_usable_events([{"title": "季度经营公告"}], []) is True
```

- [ ] **Step 2: Run the new tests and confirm they fail for missing imports**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_research_evidence.py
```

Expected: FAIL because the new contract and helpers are not defined.

- [ ] **Step 3: Implement pure validation helpers**

Add the contract and helpers to `evidence.py`:

```python
FUNDAMENTAL_QUALITY_FIELDS = (
    "revenue_yoy",
    "net_profit_yoy",
    "roe",
    "gross_margin",
    "debt_to_assets",
    "ocf_to_profit",
)


@dataclass(frozen=True)
class ResearchInputQuality:
    quote_status: EvidenceStatus = EvidenceStatus.COMPLETE
    fundamental_coverage: float = 0.0
    valuation_comparable: bool = False
    event_status: EvidenceStatus = EvidenceStatus.MISSING
    blockers: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


def _finite_number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def fundamental_metric_coverage(metrics: Mapping[str, object]) -> float:
    available = sum(_finite_number(metrics.get(key)) is not None for key in FUNDAMENTAL_QUALITY_FIELDS)
    return available / len(FUNDAMENTAL_QUALITY_FIELDS)


def has_comparable_valuation(valuation: Mapping[str, object], *, pe_ttm: object = None) -> bool:
    percentile = _finite_number(valuation.get("pe_percentile"))
    if percentile is not None and 0 <= percentile <= 100:
        return True
    pe = _finite_number(pe_ttm if pe_ttm is not None else valuation.get("pe_ttm"))
    median = _finite_number(valuation.get("industry_pe_median"))
    return pe is not None and pe > 0 and median is not None and median > 0


def has_usable_events(announcements: Iterable[Mapping[str, object]], news_items: Iterable[object]) -> bool:
    announcement_titles = (str(item.get("title") or "").strip() for item in announcements)
    news_titles = (str(getattr(item, "title", "") or "").strip() for item in news_items)
    return any((*announcement_titles, *news_titles))
```

Import `math`, `Iterable`, and `Mapping` from the standard library as required.

- [ ] **Step 4: Run focused tests and lint**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_research_evidence.py
.venv/bin/ruff check src/stock_ts/research/evidence.py tests/test_research_evidence.py
```

Expected: all evidence tests pass and ruff exits 0.

- [ ] **Step 5: Commit the evidence contract**

```bash
git add src/stock_ts/research/evidence.py tests/test_research_evidence.py
git commit -m "feat: add typed research input quality"
```

## Task 2: Make market classification risk-first

**Files:**
- Modify: `src/stock_ts/research/market_regime.py`
- Modify: `tests/test_market_regime.py`

- [ ] **Step 1: Write failing risk-priority tests**

```python
def test_extreme_limit_down_risk_overrides_rotation() -> None:
    result = assess_market_regime(
        _market(heat=60, advancing=2500, declining=2500, limit_down=80)
    )
    assert result.stage == "风险释放"
    assert result.risk_budget == "10%-30%"


def test_contradictory_high_heat_risk_release_reduces_confidence() -> None:
    conflicted = assess_market_regime(
        _market(heat=60, advancing=2500, declining=2500, limit_down=80)
    )
    consistent = assess_market_regime(
        _market(heat=40, advancing=1000, declining=3000, limit_down=80)
    )
    assert conflicted.confidence < consistent.confidence
```

- [ ] **Step 2: Run the tests and confirm the rotation-priority failure**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_market_regime.py
```

Expected: the extreme-limit-down case reports `轮动` instead of `风险释放`.

- [ ] **Step 3: Reorder classification and add a bounded contradiction penalty**

Move the risk-release condition before attack and rotation:

```python
def _classify(market: MarketSnapshot) -> tuple[str, str]:
    if market.limit_down_count >= 30 or market.breadth_ratio < 0.55:
        return "风险释放", "10%-30%"
    if market.heat_score >= 70 and market.breadth_ratio >= 1.5 and market.limit_down_count < 10:
        return "进攻", "70%-85%"
    if market.heat_score >= 55 and market.breadth_ratio >= 0.9:
        return "轮动", "50%-70%"
    if market.heat_score < 45:
        return "防守", "20%-40%"
    return "震荡", "40%-60%"
```

Add a pure `_contradiction_penalty(market, stage)` and use it in confidence calculation:

```python
def _contradiction_penalty(market: MarketSnapshot, stage: str) -> int:
    penalty = 0
    if stage == "风险释放" and market.heat_score >= 55:
        penalty += 12
    if stage in {"进攻", "轮动"} and market.limit_down_count >= 20:
        penalty += 10
    return penalty


confidence = max(0, min(100, 82 - degraded_count * 4 - _contradiction_penalty(market, stage)))
```

- [ ] **Step 4: Run focused tests and lint**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_market_regime.py tests/test_web_market_research_workspace.py
.venv/bin/ruff check src/stock_ts/research/market_regime.py tests/test_market_regime.py
```

Expected: all selected tests pass and ruff exits 0.

- [ ] **Step 5: Commit the market safety rules**

```bash
git add src/stock_ts/research/market_regime.py tests/test_market_regime.py
git commit -m "fix: prioritize market downside risk"
```

## Task 3: Gate stock verdicts with usable evidence

**Files:**
- Modify: `src/stock_ts/research/stock_memo.py`
- Modify: `tests/test_stock_research_memo.py`
- Modify: `tests/test_web_stock_research_workspace.py`

- [ ] **Step 1: Write failing stock-gate tests**

Add tests for stale quotes, metadata-only fundamentals, invalid comparisons, and blank events:

```python
def test_stale_quote_pauses_stock_research() -> None:
    memo = build_stock_research_memo(
        _raw_stock(),
        input_quality=ResearchInputQuality(quote_status=EvidenceStatus.STALE),
    )
    assert memo.verdict.status == "数据暂停"
    assert memo.verdict.confidence == 0


def test_metadata_only_fundamentals_do_not_improve_verdict() -> None:
    memo = build_stock_research_memo(
        _raw_stock(
            fundamental_metrics={"source": "tushare", "date": "2026-03-31"},
            valuation={"pe_percentile": 20},
            announcements=[{"title": "  "}],
        )
    )
    assert memo.verdict.status == "技术性观察"
    quality = next(item for item in memo.evidence if item.block == "经营质量")
    events = next(item for item in memo.evidence if item.block == "新闻公告")
    assert quality.status == EvidenceStatus.MISSING
    assert events.status == EvidenceStatus.MISSING


def test_valid_complete_inputs_remain_conditional_research() -> None:
    memo = build_stock_research_memo(
        _raw_stock(
            fundamental_metrics={
                "revenue_yoy": 18.0,
                "net_profit_yoy": 24.0,
                "roe": 16.0,
                "gross_margin": 32.0,
                "debt_to_assets": 42.0,
                "ocf_to_profit": 1.2,
                "source": "tushare.fina_indicator",
                "date": "2026-03-31",
            },
            valuation={
                "pe_percentile": 25,
                "source": "tushare",
                "date": "2026-07-11",
            },
            announcements=[{"title": "季度经营公告"}],
        )
    )
    assert memo.verdict.status == "条件研究"
    assert memo.verdict.confidence > 0
```

In the renderer test, build a stale memo and assert the HTML contains `数据暂停` and does not contain an affirmative action claim.

- [ ] **Step 2: Run stock tests and confirm the false-confidence failures**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_stock_research_memo.py tests/test_web_stock_research_workspace.py
```

Expected: stale status is unsupported and metadata-only evidence is counted as available.

- [ ] **Step 3: Derive or accept input quality and use it consistently**

Update the public function:

```python
def build_stock_research_memo(
    raw: StockRawData,
    *,
    holding: Holding | None = None,
    technical: Any | None = None,
    event_radar: Any | None = None,
    input_quality: ResearchInputQuality | None = None,
) -> StockResearchMemo:
    quality_gate = input_quality or ResearchInputQuality(
        fundamental_coverage=fundamental_metric_coverage(raw.fundamental_metrics),
        valuation_comparable=has_comparable_valuation(raw.valuation, pe_ttm=raw.pe_ttm),
        event_status=(
            EvidenceStatus.DEGRADED
            if has_usable_events(raw.announcements, raw.news_items)
            else EvidenceStatus.MISSING
        ),
    )
```

Pass `quality_gate` to `_verdict` and `_evidence_items`. In `_verdict`, return the hard-gate verdict before normal completeness scoring:

```python
if quality_gate.quote_status in {EvidenceStatus.STALE, EvidenceStatus.BLOCKED}:
    blocker = quality_gate.blockers[0] if quality_gate.blockers else "行情时效未通过"
    return ResearchVerdict(
        status="数据暂停",
        confidence=0,
        core_conflict="行情时效未通过，当前价格与研究证据不在同一有效时点。",
        strongest_evidence="保留已有事实用于审计，不形成当前交易判断。",
        strongest_counter_evidence=blocker,
        next_review="刷新最近交易日行情后重新评估。",
    )
```

For normal verdicts, derive the three availability booleans from `quality_gate` rather than raw mapping/list truthiness. Set the evidence statuses from the same contract so verdict and audit cannot disagree.

- [ ] **Step 4: Run focused tests and lint**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_research_evidence.py tests/test_stock_research_memo.py tests/test_web_stock_research_workspace.py
.venv/bin/ruff check src/stock_ts/research tests/test_research_evidence.py tests/test_stock_research_memo.py tests/test_web_stock_research_workspace.py
```

Expected: all selected tests pass and ruff exits 0.

- [ ] **Step 5: Commit the stock research gate**

```bash
git add src/stock_ts/research tests/test_stock_research_memo.py tests/test_web_stock_research_workspace.py
git commit -m "fix: gate stock research on usable evidence"
```

## Task 4: Pass typed freshness through Web orchestration

**Files:**
- Modify: `src/stock_ts/web.py`
- Modify: `tests/test_web_data_accuracy.py`
- Modify: `tests/test_web_market_research_workspace.py`
- Modify: `tests/test_web_stock_research_workspace.py`

- [ ] **Step 1: Write failing typed-integration tests**

Freeze time with `STOCK_TS_NOW`, call `_assess_data_quality` with old non-sample dates, and assert:

```python
assert quality.quote_status == EvidenceStatus.STALE
```

Add a fresh-date case that asserts `EvidenceStatus.COMPLETE`. Add an integration assertion that the market and stock workspace orchestration source no longer contains the warning-substring control flow (`"数据已滞后" in warning`).

- [ ] **Step 2: Run the Web tests and confirm `quote_status` is absent**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_web_data_accuracy.py tests/test_web_market_research_workspace.py tests/test_web_stock_research_workspace.py
```

Expected: FAIL because `DataQualityView` has no `quote_status` field and the market workspace still parses warning text.

- [ ] **Step 3: Add and propagate the typed status**

Add `quote_status: EvidenceStatus` to `DataQualityView`. In `_assess_data_quality`, retain separate lists before combining them:

```python
quote_freshness_warnings = _trade_date_freshness_warnings(...)
quote_freshness_warnings.extend(_kline_freshness_warnings(...))
pipeline_freshness_warnings = _pipeline_freshness_warnings()
freshness_warnings = [*quote_freshness_warnings, *pipeline_freshness_warnings]
quote_status = (
    EvidenceStatus.STALE
    if quote_freshness_warnings or pipeline_freshness_warnings
    else EvidenceStatus.COMPLETE
)
```

Return `quote_status` in `DataQualityView`. Replace market warning-string matching with:

```python
assessment = assess_market_regime(market, quote_status=quality.quote_status if quality else EvidenceStatus.COMPLETE)
```

Pass an explicit stock contract:

```python
input_quality = ResearchInputQuality(
    quote_status=quality.quote_status,
    fundamental_coverage=fundamental_metric_coverage(stock_raw.fundamental_metrics),
    valuation_comparable=has_comparable_valuation(stock_raw.valuation, pe_ttm=stock_raw.pe_ttm),
    event_status=(
        EvidenceStatus.DEGRADED
        if has_usable_events(stock_raw.announcements, stock_raw.news_items)
        else EvidenceStatus.MISSING
    ),
    blockers=tuple(quality.warnings) if quality.quote_status != EvidenceStatus.COMPLETE else (),
)
memo = build_stock_research_memo(..., input_quality=input_quality)
```

Import the contract and helpers from `stock_ts.research.evidence`.

- [ ] **Step 4: Run the Web-focused regression set and lint**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q \
  tests/test_web_data_accuracy.py \
  tests/test_web_market_research_workspace.py \
  tests/test_web_stock_research_workspace.py \
  tests/test_market_regime.py \
  tests/test_stock_research_memo.py
.venv/bin/ruff check src/stock_ts/web.py src/stock_ts/research tests/test_web_data_accuracy.py
```

Expected: all selected tests pass and ruff exits 0.

- [ ] **Step 5: Commit Web integration**

```bash
git add src/stock_ts/web.py tests/test_web_data_accuracy.py tests/test_web_market_research_workspace.py tests/test_web_stock_research_workspace.py
git commit -m "fix: propagate typed research freshness gates"
```

## Task 5: Verify, document, and deploy the phase

**Files:**
- Create: `docs/research/research-safety-gates-test-report.md`

- [ ] **Step 1: Run the full local quality chain**

Run:

```bash
make lint
PYTHONPATH=src .venv/bin/pytest -q
```

Expected: lint passes. Compare any full-suite failures with the recorded pre-change baseline; no new failure is acceptable.

- [ ] **Step 2: Run a local Web smoke test**

Start the app on an unused local port with the project virtual environment, request the root page with `GET`, and verify the response contains the StockTs shell and the research workspaces. Stop the temporary process after verification.

- [ ] **Step 3: Write the verification report**

Record in `docs/research/research-safety-gates-test-report.md`:

- branch and commit tested;
- focused test commands and counts;
- lint result;
- full-suite count and baseline comparison;
- local HTTP status and visible gate checks;
- known pre-existing failures with exact test names;
- deployment backup path, service status, public GET status, and rollback command.

- [ ] **Step 4: Commit the local verification report**

```bash
git add docs/research/research-safety-gates-test-report.md
git commit -m "docs: record research safety gate verification"
```

- [ ] **Step 5: Deploy an incremental patch with rollback**

Create a patch containing only Phase 1 source files. On the server:

1. run `git apply --check` against `/opt/stock-ts`;
2. archive affected source files under `/opt/stock-ts/.deploy_backups/` with a timestamp;
3. apply the patch without replacing `.env`, data, reports, accounts, Nginx, timers, or DSA;
4. compile only explicit Python source paths, excluding AppleDouble `._*.py` files;
5. launch a temporary preview on port `18501` and verify it by `GET`;
6. restart `stock-ts.service` and confirm it is active;
7. verify `https://stock.jiewat-kaka-fj.com/` by `GET` and check the response contains the current research workspaces.

If any post-deploy check fails, restore the archived source files and restart `stock-ts.service` before reporting the failure.

- [ ] **Step 6: Update the report with live evidence and commit**

Add the exact backup path, service state, public HTTP status, and response marker to the report, then run:

```bash
git add docs/research/research-safety-gates-test-report.md
git commit -m "docs: record research safety gate deployment"
```

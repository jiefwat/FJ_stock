# Usable Research Decisions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert dynamic research responses into capability-specific evidence and concise, stock-specific decisions that are genuinely useful in all four workspaces.

**Architecture:** Add a focused evidence-normalization module between the upstream adapter and `ResearchWorkspaceService`. The engine continues to own queries, concurrency, caching, and module synthesis, while the new module owns field classification, formatting, semantic quality gates, and row deduplication. The existing supplier-neutral API remains stable; the web renderer adds evidence completeness and stronger visual hierarchy without exposing implementation details.

**Tech Stack:** Python 3.11 dataclasses and mappings, pytest, server-rendered HTML, vanilla JavaScript, CSS.

---

### Task 1: Capability-Specific Evidence Normalization

**Files:**
- Create: `src/stock_ts/research_evidence.py`
- Create: `tests/test_research_evidence.py`

- [ ] **Step 1: Write failing tests for identity exclusion and capability evidence**

```python
from stock_ts.research_evidence import normalize_capability_rows


def test_finance_skips_identity_and_keeps_financial_periods() -> None:
    raw = {
        "datas": [{
            "股票代码": "603278",
            "股票简称": "大业股份",
            "最新价": 8.61,
            "涨跌幅": "1.06%",
            "营业收入[2025]": 5_100_000_000,
            "营业收入[2024]": 4_700_000_000,
            "归母净利润[2025]": 162_000_000,
            "经营现金流[2025]": 91_000_000,
            "净资产收益率ROE[2025]": "7.8%",
        }]
    }

    rows = normalize_capability_rows("finance", raw)

    labels = [fact.label for fact in rows[0]]
    assert "股票代码" not in labels
    assert "股票简称" not in labels
    assert "最新价" not in labels
    assert labels[:2] == ["营业收入[2025]", "营业收入[2024]"]
    assert rows[0][0].value == "51.00 亿"


def test_identity_only_consensus_is_semantically_empty() -> None:
    raw = {"datas": [{"股票代码": "603278", "股票简称": "大业股份", "最新价": 8.61}]}

    assert normalize_capability_rows("consensus", raw) == ()
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `pytest -q tests/test_research_evidence.py`

Expected: collection fails because `stock_ts.research_evidence` does not exist.

- [ ] **Step 3: Implement schemas, field classification, and deterministic formatting**

```python
@dataclass(frozen=True)
class CapabilitySchema:
    include_groups: tuple[tuple[str, ...], ...]
    excluded: tuple[str, ...] = ()
    minimum_facts: int = 1
    allow_quotes: bool = False


CAPABILITY_SCHEMAS = {
    "finance": CapabilitySchema((("营业收入", "营收"), ("归母净利润", "净利润"), ("经营现金流",), ("roe", "净资产收益率"), ("毛利率",), ("负债",))),
    "business": CapabilitySchema((("主营", "产品"), ("业务范围",), ("竞争", "同行"), ("客户",), ("供应商",), ("市场地位",))),
    "consensus": CapabilitySchema((("预测", "一致预期"), ("评级",), ("目标价",), ("上调", "下修"))),
    "event": CapabilitySchema((("业绩预", "业绩快报"), ("同比",), ("解禁",), ("质押",), ("监管",), ("诉讼",), ("增持", "减持"), ("公告",))),
}


def normalize_capability_rows(
    capability: str,
    raw: Mapping[str, object],
    *,
    max_rows: int = 3,
    max_facts: int = 6,
) -> tuple[tuple[ResearchFact, ...], ...]:
    rows = _raw_rows(raw)
    schema = CAPABILITY_SCHEMAS[capability]
    normalized = []
    seen = set()
    for row in rows:
        facts = _extract_ranked_facts(schema, row)[:max_facts]
        fingerprint = tuple((fact.label, fact.value) for fact in facts)
        if len(facts) >= schema.minimum_facts and fingerprint not in seen:
            normalized.append(tuple(facts))
            seen.add(fingerprint)
        if len(normalized) == max_rows:
            break
    return tuple(normalized)
```

Implementation requirements:

- Keep `ResearchFact` in `research_engine.py` for the public protocol; import it lazily inside `normalize_capability_rows` to avoid a circular top-level import.
- Define schemas for all capabilities used by the four workspaces: `index`, `macro`, `sector_selector`, `news`, `event`, `announcement`, `consensus`, `market`, `finance`, `business`, and `astock_selector`.
- Exclude internal metadata and identity fields before ranking.
- Format explicit monetary fields in yuan as `亿` or `万`, preserve percent strings, normalize eight-digit dates, and cap long values.

- [ ] **Step 4: Run evidence tests and verify GREEN**

Run: `pytest -q tests/test_research_evidence.py`

Expected: all evidence normalization tests pass.

- [ ] **Step 5: Commit the evidence layer**

```bash
git add src/stock_ts/research_evidence.py tests/test_research_evidence.py
git commit -m "feat(研究证据): 增加能力级字段提取与质量门禁"
```

### Task 2: Engine Quality Gates, Deduplication, and Specific Decisions

**Files:**
- Modify: `src/stock_ts/research_engine.py`
- Modify: `tests/test_research_engine.py`

- [ ] **Step 1: Write failing engine tests for semantic emptiness and specific findings**

```python
def test_identity_only_capability_is_reported_missing() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(results={
            "consensus": {"datas": [{"股票代码": "603278", "股票简称": "大业股份", "最新价": 8.61}]},
        })
    )

    result = service.research("stock", ResearchContext(code="603278", name="大业股份"))

    consensus = next(item for item in result.details if item.section == "机构预期")
    assert consensus.status == "insufficient"
    assert "大业股份 · 机构预期" in result.missing_sections


def test_stock_findings_use_distinct_research_evidence() -> None:
    service = ResearchWorkspaceService(
        client_factory=lambda: FakeClient(results=stock_research_fixture())
    )

    result = service.research("stock", ResearchContext(code="603278", name="大业股份"))

    serialized = json.dumps(result.to_public_dict(), ensure_ascii=False)
    assert "营业收入" in serialized
    assert "主营产品" in serialized
    assert "2027" in serialized
    assert len({item.summary for item in result.findings}) == len(result.findings)
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `pytest -q tests/test_research_engine.py -k "identity_only or distinct_research"`

Expected: identity-only consensus is currently `ready`, and useful fields are absent because the first four source fields are selected.

- [ ] **Step 3: Route every capability through the evidence layer**

```python
def _execute_capability(client: Any, request: CapabilityRequest) -> _CapabilityOutcome:
    raw = client.query(SKILLS[request.capability], request.query)
    rows = normalize_capability_rows(request.capability, raw)
    return _CapabilityOutcome(
        request=request,
        rows=rows,
        insufficient=bool(_raw_rows(raw)) and not rows,
    )
```

Extend `_CapabilityOutcome` with `insufficient: bool = False`. Render detail status as `ready`, `insufficient`, `failed`, or `missing`. Count only `rows` as successful, while all other statuses enter `missing_sections`.

- [ ] **Step 4: Add capability-specific summaries and stable deduplication**

```python
def _finding_summary(outcome: _CapabilityOutcome, row: tuple[ResearchFact, ...]) -> str:
    capability = outcome.request.capability
    if capability == "finance":
        return _finance_summary(row)
    if capability == "consensus":
        return _consensus_summary(row)
    if capability == "event":
        return _event_summary(row)
    return "；".join(f"{fact.label}：{fact.value}" for fact in row[:2])


def _deduplicate_findings(findings: Iterable[ResearchFinding]) -> tuple[ResearchFinding, ...]:
    unique = []
    seen = set()
    for finding in findings:
        fingerprint = tuple((fact.label, fact.value) for fact in finding.facts)
        if fingerprint and fingerprint not in seen:
            unique.append(finding)
            seen.add(fingerprint)
    return tuple(unique)
```

Use concise titles such as `财务方向`, `经营与竞争`, `机构预期`, and `最新事件`. Build verdicts from the highest-priority valid findings; if only one period exists, state that the trend is unconfirmed.

- [ ] **Step 5: Run engine and security-focused tests and verify GREEN**

Run: `pytest -q tests/test_research_engine.py tests/test_web_research_workspace_api.py tests/test_iwencai.py`

Expected: all focused tests pass, including supplier neutrality and metadata redaction.

- [ ] **Step 6: Commit engine synthesis**

```bash
git add src/stock_ts/research_engine.py tests/test_research_engine.py
git commit -m "feat(研究决策): 用语义证据生成专业结论"
```

### Task 3: Real-Query Calibration for Market and Opportunity

**Files:**
- Modify: `src/stock_ts/research_engine.py`
- Modify: `tests/test_research_engine.py`
- Create: `docs/superpowers/usable-research-decisions/test.md`

- [ ] **Step 1: Write failing query contract tests**

```python
def test_market_queries_use_explicit_index_and_sector_shapes() -> None:
    requests = build_workspace_queries("market", ResearchContext())
    query_by_capability = {item.capability: item.query for item in requests}
    assert "上证指数" in query_by_capability["index"]
    assert "创业板指" in query_by_capability["index"]
    assert "前5" in query_by_capability["sector_selector"]
    assert "排序" in query_by_capability["sector_selector"]


def test_opportunity_selector_query_contains_parseable_conditions() -> None:
    requests = build_workspace_queries("opportunity", ResearchContext(sector="机器人"))
    query_by_capability = {item.capability: item.query for item in requests}
    assert "机器人概念" in query_by_capability["sector_selector"]
    assert "净利润同比增长" in query_by_capability["astock_selector"]
    assert "成交额" in query_by_capability["astock_selector"]
    assert "前10" in query_by_capability["astock_selector"]
```

- [ ] **Step 2: Run query tests and verify RED**

Run: `pytest -q tests/test_research_engine.py -k "explicit_index or parseable_conditions"`

Expected: current broad natural-language prompts do not contain deterministic symbols, fields, or result limits.

- [ ] **Step 3: Replace broad selector prompts with calibrated expressions**

```python
("market", "index"): "上证指数、深证成指、创业板指 最新点位 涨跌幅 成交额",
("market", "sector_selector"): "行业板块 按成交额和热度排序 前5",
("opportunity", "sector_selector"): "{sector}概念板块 按成交额和热度排序 前5",
("opportunity", "astock_selector"): "{sector} A股 净利润同比增长 成交额大于5亿 按成交额排序 前10",
```

Build opportunity selector queries in a dedicated helper so the sector prefix is inserted once and `A股` does not become an invalid theme name.

- [ ] **Step 4: Run the real calibration script without printing secrets**

Run a local Python command that loads `/Users/fangjie/Documents/StockTs/.env`, calls only the fixed capability allowlist, and prints capability name, row count, and returned field names. Do not print request headers, environment values, or the API key.

Expected: record the actual row count and semantic field coverage for each market and opportunity capability. Zero-row capabilities remain explicit missing sections.

- [ ] **Step 5: Document the real-call evidence and run focused tests**

Write `docs/superpowers/usable-research-decisions/test.md` with timestamp, target, capability row counts, field categories, and redaction checks.

Run: `pytest -q tests/test_research_engine.py tests/test_iwencai_four_workspaces.py`

Expected: all query and route contract tests pass.

- [ ] **Step 6: Commit query calibration**

```bash
git add src/stock_ts/research_engine.py tests/test_research_engine.py docs/superpowers/usable-research-decisions/test.md
git commit -m "fix(研究查询): 校准市场与机会筛选条件"
```

### Task 4: Evidence-First Workspace UI

**Files:**
- Modify: `src/stock_ts/webapp/engine_workspace.py`
- Modify: `src/stock_ts/webapp/styles.py`
- Modify: `tests/test_web_native_research_workspaces.py`

- [ ] **Step 1: Write failing UI structure tests**

```python
def test_engine_workspace_exposes_evidence_completeness() -> None:
    html = render_engine_workspace("stock", status="configured")
    assert "data-engine-coverage" in html
    assert "已确认维度" in html


def test_finding_cards_have_rank_and_evidence_role() -> None:
    script = engine_app_script()
    assert "engine-finding-rank" in script
    assert "engine-evidence-tag" in script
    assert "item.title" in script
```

- [ ] **Step 2: Run UI tests and verify RED**

Run: `pytest -q tests/test_web_native_research_workspaces.py -k "coverage or rank"`

Expected: the current workspace has no evidence completeness element or ranked finding metadata.

- [ ] **Step 3: Render coverage and ranked findings without duplicating content**

```javascript
const ready = details.filter((detail) => detail.status === 'ready').length;
const coverage = workspace.querySelector('[data-engine-coverage]');
if (coverage) coverage.textContent = `已确认维度 ${ready}/${details.length}`;

function renderEngineFinding(item, index = 0) {
  const card = engineNode('article', 'engine-finding-card');
  const meta = engineNode('div', 'engine-finding-meta');
  meta.append(
    engineNode('span', 'engine-finding-rank', String(index + 1).padStart(2, '0')),
    engineNode('span', 'engine-evidence-tag', item.target || '研究证据')
  );
  card.append(meta, engineNode('strong', '', item.title || '关键变化'));
  if (item.summary) card.append(engineNode('p', '', item.summary));
  return card;
}
```

Pass the finding index from both the front-page and detail render loops. Treat `insufficient` as `证据不足` and `failed` as `获取失败` in the detail status label.

- [ ] **Step 4: Refine CSS for two-speed reading and mobile density**

Add a compact coverage badge, numbered finding metadata, stronger numeric values, quieter labels, and a single-column mobile layout. Keep the existing ink/paper/signal/risk palette and reduced-motion behavior. Do not add decorative gradients or extra background copy.

- [ ] **Step 5: Run UI and API tests and verify GREEN**

Run: `pytest -q tests/test_web_native_research_workspaces.py tests/test_web_research_workspace_api.py tests/test_research_engine.py`

Expected: all UI contract and product API tests pass.

- [ ] **Step 6: Commit the UI refinement**

```bash
git add src/stock_ts/webapp/engine_workspace.py src/stock_ts/webapp/styles.py tests/test_web_native_research_workspaces.py
git commit -m "feat(研究界面): 强化证据层级与首屏可读性"
```

### Task 5: Real-Data and Regression Verification

**Files:**
- Modify: `docs/superpowers/iwencai-native-workspaces/test.md`
- Modify: `docs/superpowers/iwencai-native-workspaces/review.md`
- Modify: `docs/TODO.md`

- [ ] **Step 1: Run focused regression tests**

Run:

```bash
pytest -q tests/test_research_evidence.py tests/test_research_engine.py tests/test_web_native_research_workspaces.py tests/test_web_research_workspace_api.py tests/test_iwencai.py tests/test_iwencai_four_workspaces.py
```

Expected: all focused research, API, UI, and security tests pass.

- [ ] **Step 2: Run lint and diff validation**

Run:

```bash
make lint
git diff --check
```

Expected: both commands exit with status 0.

- [ ] **Step 3: Verify real stock and four-module responses**

Call the local product API with `refresh=true` for stock `603278` and all four modules. Verify:

- finance, business, consensus, and event cards contain domain evidence rather than repeated identity/quote fields;
- identity-only capabilities appear in `missing_sections`;
- findings have unique fact fingerprints;
- no public response contains `问财`, `iWencai`, `同花顺`, `Skill`, internal ids, trace, headers, or secrets.

- [ ] **Step 4: Inspect desktop and mobile pages**

Open `http://127.0.0.1:8765/` at 1280px and 390px, visit all four workspaces, and verify no horizontal overflow, no duplicated card title/summary, readable coverage status, and correct incomplete-state labels.

- [ ] **Step 5: Run the full default and legacy suites**

Run:

```bash
pytest -q
STOCK_TS_WEB_VERSION=legacy pytest -q
```

Expected: compare results with the recorded baseline of default `540 passed / 141 failed` and legacy `670 passed / 5 failed`; document exact new counts and separate known obsolete-page or date-freshness failures from regressions.

- [ ] **Step 6: Update verification records and commit**

Record exact commands, test counts, real capability status, desktop/mobile results, and remaining gaps in the three documentation files.

```bash
git add docs/superpowers/iwencai-native-workspaces/test.md docs/superpowers/iwencai-native-workspaces/review.md docs/TODO.md
git commit -m "docs(研究决策): 记录可用性验证结果"
```


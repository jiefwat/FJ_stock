# Theme-First Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把四个研究模块升级为结论与主题优先的工作台，补齐真实市场宽度、热门股、持仓主题分化和人话结论。

**Architecture:** 在现有供应商中性结果协议上增加 `ResearchModuleSection` 和 `decision_label`；用两个逻辑能力复用 A 股筛选服务分别获取市场宽度和热门股。研究引擎负责合成主题、分布和分化，前端只渲染结构化分区，不在浏览器推导金融结论。

**Tech Stack:** Python 3.9+、dataclasses、stdlib、原生 JavaScript/CSS、pytest、systemd 快照链

---

## 文件职责

- `src/stock_ts/iwencai.py`：登记市场宽度和热门股两个逻辑能力，仍映射官方 A 股筛选接口。
- `src/stock_ts/research_evidence.py`：宽度、热门股、主题字段的语义门禁。
- `src/stock_ts/research_engine.py`：能力查询、决策标签、模块分区、主题聚合和分化结论。
- `src/stock_ts/webapp/engine_workspace.py`：分区 DOM、安全文本渲染和页面顺序。
- `src/stock_ts/webapp/styles.py`：主题雷达、分布条、分化卡和响应式布局。
- `tests/test_research_evidence.py`：新增能力字段归一化。
- `tests/test_research_engine.py`：四模块分析结构和人话结论。
- `tests/test_web_native_research_workspaces.py`：主题优先 DOM、无 `innerHTML` 和移动布局。
- `docs/superpowers/theme-first-research/`：测试、审查和交付记录。

### Task 1: 扩展主题优先产品协议和真实大盘能力

**Files:**
- Modify: `tests/test_research_engine.py`
- Modify: `tests/test_research_evidence.py`
- Modify: `src/stock_ts/iwencai.py`
- Modify: `src/stock_ts/research_evidence.py`
- Modify: `src/stock_ts/research_engine.py`

- [ ] **Step 1: 写产品协议和证据门禁失败测试**

```python
def test_workspace_result_exposes_decision_label_and_sections() -> None:
    result = ResearchWorkspaceResult(
        ok=True,
        status="complete",
        module="market",
        generated_at="2026-07-15T09:30:00+08:00",
        verdict="指数修复，但短周期仍有分化。",
        action="关注主线持续性。",
        primary_risk="修复未扩散。",
        decision_label="修复中",
        module_sections=(
            ResearchModuleSection(
                key="market-themes",
                title="当前主题",
                conclusion="制造与创新药靠前。",
            ),
        ),
    )
    payload = result.to_public_dict()
    assert payload["decision_label"] == "修复中"
    assert payload["module_sections"][0]["key"] == "market-themes"


def test_breadth_and_hot_stock_rows_keep_required_fields() -> None:
    breadth = normalize_capability_rows("breadth", {"datas": [{
        "指数简称": "同花顺全A(沪深京)",
        "上涨家数[20260715]": 3681,
        "下跌家数[20260715]": 1771,
        "平盘家数[20260715]": 71,
        "涨停家数[20260715]": 63,
        "跌停家数[20260715]": 16,
    }]})
    hot = normalize_capability_rows("hot_stock", {"datas": [{
        "股票代码": "002384.SZ",
        "股票简称": "东山精密",
        "涨跌幅[20260715]": 2.68,
        "成交额[20260715]": 29_117_831_192,
        "所属概念": ["CPO", "PCB概念"],
    }]})
    assert {fact.label for fact in breadth[0]} >= {"上涨家数[20260715]", "下跌家数[20260715]"}
    assert any(fact.label == "所属概念" for fact in hot[0])
```

- [ ] **Step 2: 运行测试确认协议和 schema 缺失**

Run: `pytest -q tests/test_research_engine.py tests/test_research_evidence.py -k 'decision_label_and_sections or breadth_and_hot_stock'`

Expected: FAIL，缺少 `ResearchModuleSection`、`breadth` 和 `hot_stock`。

- [ ] **Step 3: 实现最小协议和逻辑能力**

在 `iwencai.py` 中增加两个使用 `hithink-astock-selector` 的不同逻辑对象；在证据层增加宽度家数和热门股主题字段 schema。在 `research_engine.py` 增加：

```python
@dataclass(frozen=True)
class ResearchModuleSection:
    key: str
    title: str
    conclusion: str
    tone: str = "neutral"
    items: tuple[ResearchModuleItem, ...] = ()

    def to_public_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "title": self.title,
            "conclusion": self.conclusion,
            "tone": self.tone,
            "items": [item.to_public_dict() for item in self.items],
        }
```

`ResearchWorkspaceResult` 增加 `decision_label` 和 `module_sections` 默认值，并在公开协议中序列化。

- [ ] **Step 4: 运行协议测试**

Run: `pytest -q tests/test_research_engine.py tests/test_research_evidence.py -k 'decision_label_and_sections or breadth_and_hot_stock'`

Expected: PASS。

- [ ] **Step 5: 提交协议**

```bash
git add src/stock_ts/iwencai.py src/stock_ts/research_evidence.py src/stock_ts/research_engine.py tests/test_research_engine.py tests/test_research_evidence.py
git commit -m '[主题研究] 增加市场宽度与分区协议'
```

### Task 2: 合成四模块结论、主题和分化

**Files:**
- Modify: `tests/test_research_engine.py`
- Modify: `src/stock_ts/research_engine.py`

- [ ] **Step 1: 写四模块失败测试**

测试必须覆盖：

```python
def test_market_builds_theme_breadth_and_hot_stock_sections() -> None:
    payload = service_with_theme_fixture().research("market", ResearchContext()).to_public_dict()
    assert [item["key"] for item in payload["module_sections"]] == [
        "market-themes", "market-breadth", "market-hot"
    ]
    assert payload["decision_label"] == "修复中"


def test_portfolio_groups_holdings_by_theme_and_explains_divergence() -> None:
    payload = portfolio_theme_service().research("portfolio", context).to_public_dict()
    themes = next(item for item in payload["module_sections"] if item["key"] == "portfolio-themes")
    divergence = next(item for item in payload["module_sections"] if item["key"] == "portfolio-divergence")
    assert themes["items"][0]["name"] == "半导体"
    assert "相对强" in divergence["items"][0]["summary"]
    assert "相对弱" in divergence["items"][0]["summary"]


def test_stock_verdict_is_plain_language_status_reason_and_next_step() -> None:
    result = negative_stock_service().research("stock", ResearchContext(code="603278", name="大业股份"))
    assert result.decision_label == "基本面承压"
    assert "先等" in result.verdict


def test_opportunity_sections_put_themes_before_candidates() -> None:
    result = opportunity_theme_service().research("opportunity", ResearchContext())
    assert [section.key for section in result.module_sections][:2] == [
        "opportunity-themes", "opportunity-candidates"
    ]
    assert result.decision_label == "有主线"
```

- [ ] **Step 2: 运行测试确认旧引擎只有通用列表**

Run: `pytest -q tests/test_research_engine.py -k 'builds_theme_breadth or groups_holdings_by_theme or plain_language_status or sections_put_themes'`

Expected: FAIL。

- [ ] **Step 3: 扩展能力包和查询**

- market：`index / breadth / sector_selector / hot_stock / macro / news`。
- portfolio：每只持仓 `event / consensus / market / industry`。
- stock：保持八维。
- opportunity：保持行业、候选、事件、新闻，但候选查询增加所属概念和行业字段。

宽度取 1 行，主题取 5 行，热门股和候选取 10 行。持仓仍限制 20 只、并发 8。

- [ ] **Step 4: 实现模块分区和人话结论**

增加 `_build_module_sections()`、`_market_decision()`、`_portfolio_decision()`、`_stock_decision()`、`_opportunity_decision()`。所有结论只使用已归一化事实；缺数据返回“待确认”，不补推测。

- [ ] **Step 5: 运行研究引擎测试和真实烟测**

Run: `pytest -q tests/test_research_engine.py tests/test_research_evidence.py`

Expected: PASS。随后用本机 `.env` 仅输出四模块 `decision_label`、section keys、覆盖数和 item 数量。

- [ ] **Step 6: 提交分析合成**

```bash
git add src/stock_ts/research_engine.py tests/test_research_engine.py
git commit -m '[主题研究] 合成四模块主题结论与分化'
```

### Task 3: 重做主题优先页面层级

**Files:**
- Modify: `tests/test_web_native_research_workspaces.py`
- Modify: `src/stock_ts/webapp/engine_workspace.py`
- Modify: `src/stock_ts/webapp/styles.py`

- [ ] **Step 1: 写 DOM 与响应式失败测试**

```python
def test_workspace_places_decision_and_sections_before_findings() -> None:
    html = render_engine_workspace("market", status="configured")
    assert html.index("data-engine-decision-label") < html.index("data-engine-sections")
    assert html.index("data-engine-sections") < html.index("data-engine-target=\"findings\"")


def test_engine_script_renders_sections_with_safe_dom_only() -> None:
    script = engine_app_script()
    assert "renderEngineSections" in script
    assert "payload.module_sections" in script
    assert "market-breadth" in script
    assert ".innerHTML" not in script
```

CSS 测试要求主题带可横向滚动、宽度条有真实比例、390px 根布局单列且页面不依赖固定宽度。

- [ ] **Step 2: 运行页面测试确认结构不存在**

Run: `pytest -q tests/test_web_native_research_workspaces.py -k 'decision_and_sections or renders_sections'`

Expected: FAIL。

- [ ] **Step 3: 实现安全分区渲染**

在判断区增加 `data-engine-decision-label`。新增 `data-engine-sections`，根据 section key 渲染：

- themes：横向主题雷达卡。
- breadth：上涨/下跌/平盘/涨停/跌停的比例条与家数。
- hot/candidates：股票卡，显示主题、依据和失效条件。
- divergence：主题内强弱对照卡。

所有节点使用 `engineNode()` 和 `textContent`。

- [ ] **Step 4: 实现视觉层级**

延续现有颜色变量；主题带使用低饱和青绿和琥珀状态，分布条只在涨跌语义上使用红绿。桌面 3 列，移动单列；主题带允许自身横向滚动，页面根节点不得溢出。

- [ ] **Step 5: 运行页面与专项回归**

Run: `pytest -q tests/test_web_native_research_workspaces.py tests/test_web_research_workspace_api.py`

Expected: PASS。

- [ ] **Step 6: 提交页面**

```bash
git add src/stock_ts/webapp/engine_workspace.py src/stock_ts/webapp/styles.py tests/test_web_native_research_workspaces.py
git commit -m '[主题研究] 重排四页主题优先界面'
```

### Task 4: 刷新、验收、审查与部署

**Files:**
- Modify: `docs/superpowers/theme-first-research/TODO.md`
- Create: `docs/superpowers/theme-first-research/test.md`
- Create: `docs/superpowers/theme-first-research/review.md`
- Create: `docs/superpowers/theme-first-research/handoff.md`

- [ ] **Step 1: 刷新真实快照并验证四模块**

Run: `PYTHONPATH=src python scripts/run_daily_research.py --output-dir reports/research --refresh`

验证大盘包含三个 section，机会包含两个 section；持仓覆盖 11/11；个股八维和人话结论均可用。

- [ ] **Step 2: 浏览器验收**

在 1280x900 和 390x844 验证四页：主题先于证据、宽度家数真实、持仓分化可读、个股结论为人话、机会先主题后候选、无横向溢出和控制台错误。

- [ ] **Step 3: 自动化与基线对照**

Run:

```bash
pytest -q tests/test_research_engine.py tests/test_research_evidence.py \
  tests/test_research_snapshots.py tests/test_daily_research.py \
  tests/test_web_native_research_workspaces.py tests/test_web_research_workspace_api.py \
  tests/test_iwencai.py tests/test_iwencai_four_workspaces.py
make lint
git diff --check
```

全量 `pytest -q --tb=no` 与 `main` 失败集比较，禁止新增失败。

- [ ] **Step 4: AI Review 和文档**

使用 `$ai-review` 检查金融语义、隐私、供应商隔离、快照兼容、并发和测试缺口；修复全部 P0/P1/P2。写入 test、review、handoff，并完成 TODO。

- [ ] **Step 5: 合并与部署**

提交最终文档，快进 `main`，推送 GitHub；通过 Git bundle 快进 `/opt/stock-ts`，重启 Web，手动运行每日任务，并确认 timer 继续 active。

- [ ] **Step 6: 公网验收**

登录后四模块真实请求均返回 200；大盘 section keys、持仓 11/11、个股 decision_label、机会主题与候选数量符合预期；本地/GitHub/服务器 `main` 哈希一致。

# Complete Research System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把四个研究工作台升级为包含大盘趋势、全量持仓、八维个股研究、每日机会快照和公网自动任务的完整系统。

**Architecture:** 扩展现有 `ResearchWorkspaceResult`，用供应商中性的 `module_items` 承载模块专属全量列表；新增原子 JSON 快照仓库与 delivery service，使大盘/机会秒开快照、刷新实时运行、失败回退最后成功结果。独立每日脚本和 systemd timer 只生成全局大盘与机会，不持久化用户持仓。

**Tech Stack:** Python 3.9+、dataclasses、stdlib JSON/Path、原生 JavaScript/CSS、pytest、systemd

---

## 文件职责

- `src/stock_ts/research_engine.py`：能力包、全量覆盖、模块条目和产品协议。
- `src/stock_ts/research_evidence.py`：行业与研报语义门禁、能力行数上限。
- `src/stock_ts/research_snapshots.py`：原子快照读写、新鲜度和过期回退。
- `src/stock_ts/research_delivery.py`：统一快照优先、实时刷新和失败降级策略。
- `src/stock_ts/web.py`：解析最多 20 只持仓并调用 delivery service。
- `src/stock_ts/webapp/engine_workspace.py`：渲染趋势、持仓、八维和机会清单。
- `src/stock_ts/webapp/styles.py`：模块专属清单和移动端样式。
- `scripts/run_daily_research.py`：生成大盘与机会 latest/归档/status。
- `deploy/systemd/stock-ts-daily-research.service`：每日研究 oneshot。
- `deploy/systemd/stock-ts-daily-research.timer`：07:20、12:10、18:30 定时。
- `tests/test_research_engine.py`：产品协议、持仓上限、八维与候选数量。
- `tests/test_research_snapshots.py`：原子快照、新鲜度和 delivery 回退。
- `tests/test_daily_research.py`：每日脚本与状态文件。
- `tests/test_web_native_research_workspaces.py`：模块专属页面与安全 DOM。

### Task 1: 扩展研究产品协议

**Files:**
- Modify: `tests/test_research_engine.py`
- Modify: `src/stock_ts/research_engine.py`

- [ ] **Step 1: 写失败测试**

增加 `ResearchModuleItem`、coverage 和产品字段契约测试：

```python
def test_workspace_result_exposes_complete_product_contract() -> None:
    result = ResearchWorkspaceResult(
        ok=True,
        status="complete",
        module="market",
        generated_at="2026-07-15T07:20:00+08:00",
        verdict="趋势偏强",
        action="保持风险预算",
        primary_risk="成交缩量",
        subject_count=3,
        coverage_ready=3,
        coverage_total=4,
        module_items=(
            ResearchModuleItem(
                kind="index",
                code="000001.SH",
                name="上证指数",
                label="短中期趋势",
                summary="5日上行，20日待确认",
                risk="跌破20日趋势则失效",
            ),
        ),
    )

    payload = result.to_public_dict()

    assert payload["subject_count"] == 3
    assert payload["coverage"] == {"ready": 3, "total": 4}
    assert payload["delivery"] == "live"
    assert payload["module_items"][0]["kind"] == "index"
```

- [ ] **Step 2: 运行测试确认缺少产品字段**

Run: `pytest -q tests/test_research_engine.py -k complete_product_contract`

Expected: FAIL，缺少 `ResearchModuleItem` 或构造参数。

- [ ] **Step 3: 实现兼容协议**

新增不可变数据类：

```python
@dataclass(frozen=True)
class ResearchModuleItem:
    kind: str
    code: str = ""
    name: str = ""
    label: str = ""
    summary: str = ""
    risk: str = ""
    status: str = "ready"
    facts: tuple[ResearchFact, ...] = ()

    def to_public_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "code": self.code,
            "name": self.name,
            "label": self.label,
            "summary": self.summary,
            "risk": self.risk,
            "status": self.status,
            "facts": [fact.to_public_dict() for fact in self.facts],
        }
```

给 `ResearchWorkspaceResult` 增加带默认值的 `subject_count`、`coverage_ready`、`coverage_total`、`delivery="live"`、`as_of` 和 `module_items`，保持旧调用方兼容。

- [ ] **Step 4: 运行研究引擎测试**

Run: `pytest -q tests/test_research_engine.py`

Expected: PASS。

- [ ] **Step 5: 提交协议**

```bash
git add src/stock_ts/research_engine.py tests/test_research_engine.py
git commit -m "feat(完整系统): 扩展研究产品协议"
```

### Task 2: 补齐大盘、全持仓、八维个股和候选列表

**Files:**
- Modify: `tests/test_research_engine.py`
- Modify: `tests/test_research_evidence.py`
- Modify: `tests/test_web_native_research_workspaces.py`
- Modify: `src/stock_ts/research_engine.py`
- Modify: `src/stock_ts/research_evidence.py`
- Modify: `src/stock_ts/web.py`

- [ ] **Step 1: 写失败测试**

覆盖四项行为：

```python
def test_portfolio_builds_three_capabilities_for_all_twenty_holdings() -> None:
    holdings = tuple(ResearchTarget(code=f"600{index:03d}", name=f"持仓{index}") for index in range(25))
    requests = build_workspace_queries("portfolio", ResearchContext(holdings=holdings))
    assert len(requests) == 20 * 3
    assert {request.capability for request in requests} == {"event", "consensus", "market"}


def test_stock_research_uses_eight_dimensions() -> None:
    requests = build_workspace_queries("stock", ResearchContext(code="603278", name="大业股份"))
    assert [request.capability for request in requests] == [
        "finance", "business", "consensus", "event",
        "market", "industry", "announcement", "report",
    ]


def test_opportunity_keeps_ten_candidate_rows() -> None:
    rows = [
        {"股票代码": f"60{index:04d}", "股票简称": f"候选{index}", "净利润同比增长率": f"{index + 10}%"}
        for index in range(10)
    ]
    client = FakeClient(results={"astock_selector": {"datas": rows}})
    result = ResearchWorkspaceService(client_factory=lambda: client).research(
        "opportunity", ResearchContext(), refresh=True
    )
    assert len([item for item in result.module_items if item.kind == "candidate"]) == 10


def test_web_portfolio_context_keeps_twenty_names_and_codes_only(tmp_path) -> None:
    # 写 21 行持仓后渲染页面。
    assert len(context["holdings"]) == 20
    assert set(context["holdings"][0]) == {"code", "name"}
```

- [ ] **Step 2: 运行测试确认旧上限与旧维度失败**

Run: `pytest -q tests/test_research_engine.py tests/test_research_evidence.py tests/test_web_native_research_workspaces.py -k 'twenty_holdings or eight_dimensions or ten_candidate_rows or keeps_twenty'`

Expected: FAIL，旧代码只取 3 只、4 个股维度和 3 行候选。

- [ ] **Step 3: 实现能力包与语义门禁**

修改能力包：

```python
WORKSPACE_CAPABILITIES = {
    "market": ("index", "macro", "sector_selector", "news"),
    "portfolio": ("event", "consensus", "market"),
    "stock": (
        "finance", "business", "consensus", "event",
        "market", "industry", "announcement", "report",
    ),
    "opportunity": ("sector_selector", "astock_selector", "event", "news"),
}
```

持仓取 `context.holdings[:20]`，执行器并发上限改为 8。`normalize_capability_rows()` 由调用方传入能力行数：候选 10、板块 5、新闻/公告/研报 5，其余 3。新增 `industry` 与 `report` schema，行业接受行业名称/排名/估值/同行，研报接受标题/摘要/发布日期/目标价/评级。

大盘指数查询增加 5 日、20 日涨跌和均线字段。Web 持仓上下文上限同步为 20。
新闻、公告和研报在进入首屏发现前解析发布日期；超过 30 天的条目保留在完整依据，但不能参与 verdict、primary_risk 或前三条发现。

- [ ] **Step 4: 生成模块条目**

实现 `_build_module_items(module, outcomes)`：

- `market`：指数 outcome 的前三行。
- `portfolio`：每个 target 一项，风险优先选择 event，其次 consensus、market。
- `stock`：八个 detail 各一项。
- `opportunity`：候选 outcome 的前十行，缺代码或名称的行丢弃，统一风险为“板块退潮、成交萎缩或业绩证据转弱时移出清单”。

coverage 使用 ready outcome 数量；subject_count 分别为指数数、持仓数、1 和候选数。个股至少 6/8 ready 才为 complete。

- [ ] **Step 5: 运行相关测试与真实四模块烟测**

Run: `pytest -q tests/test_research_engine.py tests/test_research_evidence.py tests/test_web_native_research_workspaces.py`

Expected: PASS。随后用本机 `.env` 运行四模块，只打印 status、coverage、subject_count 和 module_items 数量。

- [ ] **Step 6: 提交研究深度**

```bash
git add src/stock_ts/research_engine.py src/stock_ts/research_evidence.py src/stock_ts/web.py tests/test_research_engine.py tests/test_research_evidence.py tests/test_web_native_research_workspaces.py
git commit -m "feat(完整系统): 补齐四模块全量研究"
```

### Task 3: 实现每日快照与 delivery service

**Files:**
- Create: `src/stock_ts/research_snapshots.py`
- Create: `src/stock_ts/research_delivery.py`
- Create: `tests/test_research_snapshots.py`
- Modify: `src/stock_ts/web.py`
- Modify: `tests/test_web_research_workspace_api.py`

- [ ] **Step 1: 写快照失败测试**

```python
def test_snapshot_store_writes_latest_and_date_archive_atomically(tmp_path) -> None:
    store = ResearchSnapshotStore(tmp_path, clock=lambda: fixed_now)
    store.save("opportunity", payload)
    assert json.loads((tmp_path / "opportunity/latest.json").read_text()) == payload
    assert (tmp_path / "opportunity/2026-07-15.json").exists()
    assert not list(tmp_path.rglob("*.tmp"))


def test_delivery_prefers_fresh_snapshot_without_live_call(tmp_path) -> None:
    store.save("market", payload)
    delivered = deliver_research(exploding_service, store, "market", context, refresh=False)
    assert delivered["delivery"] == "snapshot"


def test_delivery_falls_back_to_stale_snapshot_after_live_failure(tmp_path) -> None:
    store.save("market", old_payload)
    delivered = deliver_research(unavailable_service, store, "market", context, refresh=False)
    assert delivered["delivery"] == "stale_snapshot"
    assert delivered["stale"] is True
```

- [ ] **Step 2: 运行测试确认模块不存在**

Run: `pytest -q tests/test_research_snapshots.py`

Expected: collection FAIL，缺少 `stock_ts.research_snapshots`。

- [ ] **Step 3: 实现原子快照仓库**

`ResearchSnapshotStore.save(module, payload)` 只允许 `market/opportunity`，使用 `NamedTemporaryFile` 或同目录 `.tmp` 后 `Path.replace()`。`load(module, max_age_hours=18, allow_stale=False)` 返回包含 payload、age 和 stale 的 `SnapshotRead`。

- [ ] **Step 4: 实现 delivery service 并接入 Web**

`deliver_research()` 规则：

1. 非刷新且存在新鲜快照：直接返回，`delivery=snapshot`。
2. 否则运行实时服务。
3. 实时成功：大盘/机会保存快照并返回 `delivery=live`。
4. 实时全部失败且存在旧快照：返回 `delivery=stale_snapshot`、`stale=true`。
5. 持仓和个股始终实时，不读取共享快照。

Web 通过 `STOCK_TS_RESEARCH_SNAPSHOT_DIR`，默认 `reports/research`，调用 delivery service。

- [ ] **Step 5: 运行快照与 API 测试**

Run: `pytest -q tests/test_research_snapshots.py tests/test_web_research_workspace_api.py`

Expected: PASS。

- [ ] **Step 6: 提交快照链**

```bash
git add src/stock_ts/research_snapshots.py src/stock_ts/research_delivery.py src/stock_ts/web.py tests/test_research_snapshots.py tests/test_web_research_workspace_api.py
git commit -m "feat(完整系统): 增加研究快照与降级链"
```

### Task 4: 实现每日研究脚本与 systemd timer

**Files:**
- Create: `scripts/run_daily_research.py`
- Create: `deploy/systemd/stock-ts-daily-research.service`
- Create: `deploy/systemd/stock-ts-daily-research.timer`
- Create: `tests/test_daily_research.py`
- Modify: `scripts/README.md`

- [ ] **Step 1: 写每日任务失败测试**

```python
def test_daily_research_writes_market_opportunity_and_status(tmp_path) -> None:
    result = run_daily_research(output_dir=tmp_path, service=fake_service, now=fixed_now)
    assert result.ok is True
    assert (tmp_path / "market/latest.json").exists()
    assert (tmp_path / "opportunity/latest.json").exists()
    status = json.loads((tmp_path / "daily.status.json").read_text())
    assert status["modules"] == {"market": "complete", "opportunity": "complete"}
```

同时断言 timer 包含 `07:20:00`、`12:10:00`、`18:30:00`、`Persistent=true`。

- [ ] **Step 2: 运行测试确认脚本缺失**

Run: `pytest -q tests/test_daily_research.py`

Expected: collection FAIL，缺少 `scripts.run_daily_research`。

- [ ] **Step 3: 实现脚本**

脚本提供 `DailyResearchResult`、`run_daily_research()` 和 CLI。依次强制刷新 market/opportunity，成功结果交给 `ResearchSnapshotStore`，最终原子写 `daily.status.json`。两模块全部失败时 exit 2，部分成功 exit 0 但 status 为 partial。

- [ ] **Step 4: 实现并记录 systemd 单元**

service 使用 `/opt/stock-ts/.venv/bin/python scripts/run_daily_research.py --output-dir reports/research --refresh`；timer 定义三个 OnCalendar、`Persistent=true`、`AccuracySec=5m`。在 `scripts/README.md` 写安装、手动运行和状态检查命令。

- [ ] **Step 5: 运行脚本测试与本机真实任务**

Run: `pytest -q tests/test_daily_research.py`

Expected: PASS。随后用本机忽略提交的 `.env` 运行真实脚本，验证两个 latest、两个日期归档和 status，不打印凭证。

- [ ] **Step 6: 提交自动任务**

```bash
git add scripts/run_daily_research.py deploy/systemd/stock-ts-daily-research.service deploy/systemd/stock-ts-daily-research.timer tests/test_daily_research.py scripts/README.md
git commit -m "feat(完整系统): 增加每日研究自动任务"
```

### Task 5: 展示模块专属完整清单

**Files:**
- Modify: `tests/test_web_native_research_workspaces.py`
- Modify: `src/stock_ts/webapp/engine_workspace.py`
- Modify: `src/stock_ts/webapp/styles.py`

- [ ] **Step 1: 写页面失败测试**

```python
def test_workspace_exposes_module_specific_list_and_delivery_state() -> None:
    html = render_engine_workspace("market", status="configured")
    assert "data-engine-module-items" in html
    assert "data-engine-delivery" in html


def test_engine_script_renders_module_items_without_inner_html() -> None:
    script = engine_app_script()
    assert "renderEngineModuleItems" in script
    assert "payload.module_items" in script
    assert "encodeURIComponent" in script
    assert ".innerHTML" not in script
```

CSS 测试要求 `.engine-module-item-grid`、移动单列和 stale 状态。

- [ ] **Step 2: 运行页面测试确认结构缺失**

Run: `pytest -q tests/test_web_native_research_workspaces.py -k 'module_specific or module_items or delivery_state'`

Expected: FAIL。

- [ ] **Step 3: 实现模块清单 DOM**

关键发现后增加模块清单容器。JS 根据 module：

- market 标题“指数趋势”，最多 3 卡。
- portfolio 标题“全部持仓”，显示 `已分析 N/N`。
- stock 标题“八维覆盖”，显示 8 个维度状态。
- opportunity 标题“今日机会”，显示 5–10 候选，并用 `/?code=<编码>#stock` 进入个股页。

delivery badge 显示“实时”“今日快照”“历史快照”，历史快照使用琥珀警示。全部节点使用 `engineNode()` 和 `textContent`。

- [ ] **Step 4: 实现克制的响应式样式**

桌面 market/stock 使用 3–4 列，portfolio/opportunity 使用 2 列；760px 以下全部单列。卡片复用墨蓝、纸白、绿/琥珀/红状态体系，不增加装饰性背景模块。

- [ ] **Step 5: 运行页面专项与 lint**

Run: `pytest -q tests/test_web_native_research_workspaces.py && make lint`

Expected: PASS / clean。

- [ ] **Step 6: 提交页面**

```bash
git add src/stock_ts/webapp/engine_workspace.py src/stock_ts/webapp/styles.py tests/test_web_native_research_workspaces.py
git commit -m "feat(完整系统): 展示四模块完整研究清单"
```

### Task 6: 质量门禁、部署与公网验收

**Files:**
- Modify: `docs/superpowers/complete-research-system/TODO.md`
- Create: `docs/superpowers/complete-research-system/test.md`
- Create: `docs/superpowers/complete-research-system/review.md`
- Create: `docs/superpowers/complete-research-system/handoff.md`

- [ ] **Step 1: 运行专项与真实数据验证**

Run:

```bash
pytest -q tests/test_research_engine.py tests/test_research_evidence.py \
  tests/test_research_snapshots.py tests/test_daily_research.py \
  tests/test_web_native_research_workspaces.py tests/test_web_research_workspace_api.py \
  tests/test_iwencai.py tests/test_iwencai_four_workspaces.py
make lint
git diff --check
```

Expected: 全部 PASS。真实四模块输出满足 3 个指数、11/11 持仓、个股至少 6/8、机会至少 5 只。

- [ ] **Step 2: 浏览器验证**

在 1280x900 和 390x844 验证四页清单、快照状态、刷新、个股跳转、无横向溢出、控制台无错误。

- [ ] **Step 3: AI Review 与 findings 修复**

按 Python/AI review 规则审查当前分支相对 `main` 的安全、协议、快照、并发、隐私和测试缺口。所有 P0/P1/P2 findings 必须修复并重新运行 Step 1。

- [ ] **Step 4: 更新需求证据并提交**

在 TODO 勾选完成项；test 记录测试、真实数据和浏览器证据；review 记录 findings；handoff 记录部署和回滚边界。

- [ ] **Step 5: 合并推送并部署**

快进本地 `main` 并推送 `origin/main`。服务器 `/opt/stock-ts` 用 git bundle 快进，保留 `.env`、`.secrets`、`data`、`reports`，安装依赖并重启 `stock-ts.service`。

安装并启用：

```bash
sudo cp deploy/systemd/stock-ts-daily-research.service /etc/systemd/system/
sudo cp deploy/systemd/stock-ts-daily-research.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now stock-ts-daily-research.timer
sudo systemctl start stock-ts-daily-research.service
```

- [ ] **Step 6: 公网最终验收**

确认本地 `main`、GitHub `main`、服务器 `main` 哈希一致；`stock-ts.service` 和新 timer active；登录态四模块 HTTP 200；服务器真实每日任务生成快照；公网 `/healthz` 和 `/login` 为 200。

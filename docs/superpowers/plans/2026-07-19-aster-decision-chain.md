# Aster Market Decision Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把四个并列模块重构为“市场环境 -> 参与许可 -> 主线判定 -> 个股验证 -> 持仓检查”的连续桌面研判工作流。

**Architecture:** 在 `analysis.py` 新增纯函数 `build_decision_brief()`，只组合已有市场分析与主题机会，不改变原始快照模型；`presenter.py` 将决策简报加入供应商中立 view。UI 使用一个全局研判链承接四个工作区，首页只展示结论、证据、主线梯队和下一触发条件，完整八主题仍留在主线扫描工作区。

**Tech Stack:** Python 3.11 标准库、不可变 dataclass、原生 HTML/CSS/JavaScript、Pytest、Ruff。

---

## 文件边界

- Modify: `src/aster_market/analysis.py`：新增参与许可和主线状态的确定性组合逻辑。
- Modify: `src/aster_market/presenter.py`：将 `decision_brief` 注入页面 view。
- Modify: `src/aster_market/ui.py`：渲染全局研判链、今日结论、主线梯队和新导航名称。
- Modify: `src/aster_market/ui_modules.py`：把机会、个股和持仓工作区改为递进语义，并携带全局结论。
- Modify: `src/aster_market/assets/app.css`：实现研判链、结论工作面和主线梯队。
- Modify: `src/aster_market/assets/modules.css`：统一三个下游工作区的分析上下文与层级。
- Modify: `tests/test_analysis.py`：覆盖确认主线、候选主线、逆势异动和无主线。
- Modify: `tests/test_presenter.py`：覆盖 view 决策简报合同。
- Modify: `tests/test_ui.py`：覆盖新信息架构、资源版本和桌面边界。
- Create: `docs/superpowers/aster-decision-chain/test.md`：记录自动化、浏览器、数据和公网验收。
- Create: `docs/superpowers/aster-decision-chain/review.md`：记录最终 diff 审查。
- Modify: `docs/TODO.md`、`docs/architecture/README.md`、`docs/tech-specs/README.md`：同步产品和分析规则。

### Task 1: 参与许可与主线判定

**Files:**
- Modify: `tests/test_analysis.py`
- Modify: `src/aster_market/analysis.py`

- [ ] **Step 1: 写四种决策简报失败测试**

在 `tests/test_analysis.py` 导入 `build_decision_brief`，使用 `dataclasses.replace` 构造市场状态：

```python
def test_decision_brief_downgrades_strength_in_contracting_market() -> None:
    snapshot = replace(_snapshot(), advancing=400, declining=4600, limit_down=80)
    brief = build_decision_brief(snapshot)
    assert brief["permission"]["label"] == "防守等待"
    assert brief["mainline"]["status"] == "countertrend"
    assert brief["mainline"]["label"] == "逆势异动"
    assert "尚未形成可确认主线" in brief["summary"]


def test_decision_brief_confirms_mainline_in_expansion() -> None:
    snapshot = replace(_snapshot(), advancing=3400, declining=1600, limit_down=6)
    brief = build_decision_brief(snapshot)
    assert brief["permission"]["label"] == "主动跟踪"
    assert brief["mainline"]["status"] == "confirmed"
    assert brief["mainline"]["theme"] == "机器人"


def test_decision_brief_keeps_rotation_as_candidate() -> None:
    brief = build_decision_brief(_snapshot())
    assert brief["permission"]["label"] == "结构确认"
    assert brief["mainline"]["status"] == "candidate"


def test_decision_brief_handles_empty_sectors() -> None:
    brief = build_decision_brief(replace(_snapshot(), sectors=(), candidates=()))
    assert brief["mainline"]["status"] == "none"
    assert brief["mainline"]["theme"] is None
```

- [ ] **Step 2: 运行测试并确认 RED**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_analysis.py -k decision_brief`

Expected: FAIL，因为 `build_decision_brief` 尚不存在。

- [ ] **Step 3: 实现最小决策逻辑**

在 `src/aster_market/analysis.py` 中复用 `build_market_analysis()` 和 `build_opportunities()`：

```python
def build_decision_brief(snapshot: MarketSnapshot) -> dict[str, object]:
    market = build_market_analysis(snapshot)
    opportunities = build_opportunities(snapshot)
    if market["regime"] == "扩张" and market["risk_level"] == "可控":
        permission = {"label": "主动跟踪", "tone": "constructive", "reason": "市场扩张且风险可控"}
    elif market["regime"] == "收缩" or market["risk_level"] == "升高":
        permission = {"label": "防守等待", "tone": "defensive", "reason": f"市场{market['regime']}且风险{market['risk_level']}"}
    else:
        permission = {"label": "结构确认", "tone": "selective", "reason": "市场轮动，等待强度扩散"}
```

第一主题不存在时返回 `status=none`；防守许可统一返回 `countertrend`；主动许可且第一主题阶段为扩散返回 `confirmed`；结构确认且第一主题为扩散或加速返回 `candidate`；其他情况返回 `divergent`。生成 `headline`、`summary`、`next_trigger` 和五步 `chain`。

- [ ] **Step 4: 运行分析测试并提交**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_analysis.py`

Expected: 全部通过。

Commit: `[研判引擎] 建立市场许可与主线判定`

### Task 2: 页面数据合同

**Files:**
- Modify: `tests/test_presenter.py`
- Modify: `src/aster_market/presenter.py`
- Modify: `tests/test_web.py`

- [ ] **Step 1: 写 view 与 API 合同失败测试**

```python
def test_build_view_exposes_decision_chain() -> None:
    view = build_view(_snapshot())
    assert view["decision_brief"]["permission"]["label"] == "结构确认"
    assert [step["key"] for step in view["decision_brief"]["chain"]] == [
        "environment", "permission", "mainline", "validation", "trigger"
    ]
```

在 `tests/test_web.py::test_health_and_snapshot_are_public_no_store_endpoints` 中增加：

```python
assert payload["decision_brief"]["mainline"]["theme"] == "机器人"
```

- [ ] **Step 2: 运行测试并确认 RED**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_presenter.py tests/test_web.py`

Expected: FAIL，因为 view 尚无 `decision_brief`。

- [ ] **Step 3: 接入 Presenter**

在 `presenter.py` 导入 `build_decision_brief`，在 `build_view()` 返回对象中加入：

```python
"decision_brief": build_decision_brief(snapshot),
```

- [ ] **Step 4: 运行合同测试并提交**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_presenter.py tests/test_web.py`

Expected: 全部通过。

Commit: `[页面数据] 接入今日研判链合同`

### Task 3: 连续研判工作台

**Files:**
- Modify: `tests/test_ui.py`
- Modify: `src/aster_market/ui.py`
- Modify: `src/aster_market/ui_modules.py`
- Modify: `src/aster_market/assets/app.css`
- Modify: `src/aster_market/assets/modules.css`

- [ ] **Step 1: 写新信息架构失败测试**

```python
def test_ui_exposes_analyst_decision_chain() -> None:
    html = render_app(_sample_view())
    css = asset_text("app.css")
    assert 'data-decision-chain' in html
    assert 'data-decision-status="candidate"' in html
    assert "今日研判" in html
    assert "主线扫描" in html
    assert "个股验证" in html
    assert "持仓检查" in html
    assert "参与许可" in html
    assert "主线梯队" in html
    assert ".decision-chain" in css
    assert ".thesis-stage" in css
    assert "decision-v1" in html
```

增加收缩市场测试，断言 `逆势异动` 与 `尚未形成可确认主线` 出现在 HTML，且不出现“确认主线：人工智能”。

- [ ] **Step 2: 运行 UI 测试并确认 RED**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_ui.py -k 'decision_chain or contracting'`

Expected: FAIL，新结构尚不存在。

- [ ] **Step 3: 重排 HTML**

在 `ui.py` 新增 `_render_decision_chain(view)`、`_render_thesis_stage(view)`、`_render_mainline_ladder(view)`。全局研判链放在命令带后、四个 deck 前；市场 deck 首屏顺序固定为今日结论、四维证据、主线梯队、下一触发条件。首页候选只显示第一主题映射股票，不再展示全市场涨幅前 18 名。

导航文案改为 `今日研判 / 主线扫描 / 个股验证 / 持仓检查`。所有资源版本统一为 `decision-v1`。

- [ ] **Step 4: 实现 CSS 研判链**

`.decision-chain` 使用五列连续轨道；当前防守状态使用信号橙，确认状态使用市场绿。`.thesis-stage` 使用 0.9fr / 1.1fr 双列：左侧只放结论，右侧放四条证据，不再使用大幅地平线作为主角。`.mainline-ladder` 使用语义表格行，不使用独立圆角卡片。

保持 `html`、`body`、`.analysis-deck` 的 `min-width: 1180px`，不得新增 viewport meta 或 `@media (max-width: ...)`。

- [ ] **Step 5: 运行 UI 与语法测试并提交**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_ui.py && node --check src/aster_market/assets/app.js && node --check src/aster_market/assets/portfolio.js`

Expected: 全部通过。

Commit: `[研判界面] 重构连续分析工作台`

### Task 4: 浏览器、文档与发布

**Files:**
- Create: `docs/superpowers/aster-decision-chain/test.md`
- Create: `docs/superpowers/aster-decision-chain/review.md`
- Modify: `docs/TODO.md`
- Modify: `docs/architecture/README.md`
- Modify: `docs/tech-specs/README.md`

- [ ] **Step 1: 全量本地验证**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q && ruff check src tests && python3 -m compileall -q src && node --check src/aster_market/assets/app.js && node --check src/aster_market/assets/portfolio.js && git diff --check`

Expected: 全部通过。

- [ ] **Step 2: 真实浏览器验收**

用测试快照和生产只读 view 分别验证：今日研判首屏形成一句完整结论；收缩市场显示防守等待与逆势异动；四模块按 `1` 至 `4` 递进；主线候选进入个股；搜索、持仓保存/编辑/删除保持；1280、1536、1920 无横向溢出；控制台无错误。

- [ ] **Step 3: 更新文档与审查记录**

`test.md` 记录自动化、浏览器和生产数据证据；`review.md` 记录 findings、假设、残余风险和发布决定。架构文档增加 `decision_brief` 数据流，技术规格写入参与许可和主线判定规则，TODO 增加今日研判链完成项。

- [ ] **Step 4: 提交并推送**

Commit: `[质量验收] 完成今日研判链验证`

Run: `git push origin main`

Expected: 本地 `main` 与 `origin/main` 指向同一提交，远端仅保留 `main`。

- [ ] **Step 5: 原子部署与公网验证**

创建 `/opt/aster-market/releases/<timestamp>-<short-hash>`，上传 `git archive HEAD`，原子切换 `/opt/aster-market/current`，只重启 `stock-ts.service`。预热后验证首页、`/api/snapshot`、大盘、机会和真实个股接口；确认 `decision_brief`、四工作区、实时快照链接、三个服务 active、`NRestarts=0` 和 warning=0。验收通过后删除旧 release，只保留当前 release。

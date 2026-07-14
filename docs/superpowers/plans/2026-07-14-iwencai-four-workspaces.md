# 问财四大工作台集成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在每日大盘、我的持仓、个股分析和热点机会中提供模块化问财外部核查，同时保持本地结论优先和持仓隐私边界。

**Architecture:** 扩展 `iwencai.py` 为模块技能路由器，保留单一登录态 endpoint；抽出共享研究坞渲染器，四个 workspace 只提供最小上下文和插入位置。浏览器发送嵌套 `context`，服务端白名单化为扁平字段后构造查询，外部结果继续压缩为最多 5 条证据。

**Tech Stack:** Python 3.11、stdlib HTTP server、HTML/CSS/原生 JavaScript、pytest、ruff

---

### Task 1: 扩展模块技能目录与路由

**Files:**
- Modify: `src/stock_ts/iwencai.py`
- Create: `tests/test_iwencai_four_workspaces.py`

- [ ] **Step 1: 写模块路由失败测试**

```python
import pytest

from stock_ts.iwencai import route_module_research_skill


@pytest.mark.parametrize(
    ("module", "question", "skill_id"),
    [
        ("market", "三大指数当前结构", "hithink-zhishu-query"),
        ("market", "近期宏观变量", "hithink-macro-query"),
        ("market", "筛选当前主线板块", "hithink-sector-selector"),
        ("opportunity", "筛选盈利改善的A股", "hithink-astock-selector"),
        ("opportunity", "机器人板块持续性", "hithink-sector-selector"),
        ("portfolio", "这只持仓是否有业绩风险", "hithink-event-query"),
        ("stock", "净利润质量", "hithink-finance-query"),
    ],
)
def test_route_module_research_skill(module: str, question: str, skill_id: str) -> None:
    assert route_module_research_skill(module, question).skill_id == skill_id
```

- [ ] **Step 2: 运行测试并确认因函数或技能缺失而失败**

Run: `PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest tests/test_iwencai_four_workspaces.py -q`

Expected: FAIL，提示 `route_module_research_skill` 不存在。

- [ ] **Step 3: 实现 4 个技能和模块白名单路由**

在 `SKILLS` 增加：

```python
"index": IwencaiSkill("hithink-zhishu-query", "指数结构"),
"macro": IwencaiSkill("hithink-macro-query", "宏观变量"),
"sector_selector": IwencaiSkill("hithink-sector-selector", "板块筛选"),
"astock_selector": IwencaiSkill("hithink-astock-selector", "A股筛选"),
```

实现 `MODULE_ROUTING_RULES` 和：

```python
def route_module_research_skill(module: str, question: str) -> IwencaiSkill:
    if module == "stock":
        return route_stock_research_skill(question)
    rules, fallback = MODULE_ROUTING_RULES[module]
    normalized = question.strip().lower()
    for skill_key, keywords in rules:
        if any(keyword in normalized for keyword in keywords):
            return SKILLS[skill_key]
    return SKILLS[fallback]
```

未知模块抛出 `ValueError("不支持的研究模块。")`，各模块不能路由到白名单外技能。

- [ ] **Step 4: 增加查询上下文和通用响应测试**

覆盖：market 查询不带股票、portfolio 查询只含名称/代码/问题、opportunity 查询含板块或候选、响应返回 `module` 和 `context_label`，且不出现 `shares/cost_price/weight`。

- [ ] **Step 5: 实现 `build_module_research_query` 与 `build_module_research_response`**

保留 `build_stock_research_response` 作为兼容包装；通用响应继续复用行压缩、trace 尾号、来源和免责声明。

- [ ] **Step 6: 运行模块与原问财测试**

Run: `PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest tests/test_iwencai.py tests/test_iwencai_four_workspaces.py -q`

Expected: PASS。

- [ ] **Step 7: 提交**

```bash
git add src/stock_ts/iwencai.py tests/test_iwencai_four_workspaces.py
git commit -m '[问财研究] 扩展四工作台技能路由'
```

### Task 2: 泛化同源研究 endpoint

**Files:**
- Modify: `src/stock_ts/web.py`
- Modify: `tests/test_web_iwencai_research.py`

- [ ] **Step 1: 写模块 payload 与隐私失败测试**

```python
def test_parse_market_and_portfolio_research_payloads() -> None:
    market = _parse_iwencai_research_payload(
        json.dumps({"module": "market", "question": "三大指数结构", "context": {"local_as_of": "2026-07-14"}}).encode()
    )
    portfolio = _parse_iwencai_research_payload(
        json.dumps({
            "module": "portfolio",
            "question": "公告风险",
            "context": {"code": "600519", "name": "贵州茅台", "shares": "100", "cost_price": "1500"},
        }, ensure_ascii=False).encode()
    )
    assert market["module"] == "market"
    assert portfolio == {
        "module": "portfolio", "code": "600519", "name": "贵州茅台",
        "sector": "", "question": "公告风险", "local_as_of": "",
    }
```

同时覆盖未知模块、portfolio 缺股票、opportunity 缺板块/候选、旧扁平 stock payload 兼容。

- [ ] **Step 2: 运行 endpoint 测试确认失败**

Run: `PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest tests/test_web_iwencai_research.py -q`

Expected: FAIL，现有解析器没有 `module/context`。

- [ ] **Step 3: 最小实现嵌套上下文解析和模块调用**

`_parse_iwencai_research_payload` 只读取 `module/code/name/sector/question/local_as_of`；旧扁平字段作为 fallback。把 `_ask_iwencai_stock_research` 泛化为模块路由，但保留函数名供现有测试和调用兼容。

- [ ] **Step 4: 增加 endpoint 结构化返回测试**

对 market 和 opportunity 请求 monkeypatch 服务函数，断言 HTTP 200、模块字段透传、登录与限流仍生效；断言原始请求中的持仓私密字段不会进入捕获 payload。

- [ ] **Step 5: 运行 endpoint 与鉴权测试**

Run: `PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest tests/test_web_iwencai_research.py tests/test_web_auth.py -q`

Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add src/stock_ts/web.py tests/test_web_iwencai_research.py
git commit -m '[问财研究] 泛化四模块研究接口'
```

### Task 3: 抽出共享研究坞

**Files:**
- Create: `src/stock_ts/webapp/research_console.py`
- Modify: `src/stock_ts/webapp/stock_workspace.py`
- Modify: `src/stock_ts/webapp/__init__.py`
- Create: `tests/test_web_iwencai_four_workspaces.py`

- [ ] **Step 1: 写共享渲染器失败测试**

测试四个模块各有 4 个快捷问题、正确的 `data-iwencai-module`、配置状态、唯一 textarea id；portfolio 和 opportunity 的 `<option>` 只含代码/名称/板块，不含成本、股数或权重。

- [ ] **Step 2: 运行测试确认模块不存在**

Run: `PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest tests/test_web_iwencai_four_workspaces.py -q`

Expected: FAIL，无法导入 `research_console`。

- [ ] **Step 3: 创建共享配置和渲染器**

实现不可变 `ResearchContextOption`，四套 `MODULE_PRESETS`，以及：

```python
def render_iwencai_research_console(
    *, module: str, status: str, code: str = "", name: str = "",
    sector: str = "", local_as_of: str = "",
    context_options: tuple[ResearchContextOption, ...] = (),
) -> str:
    ...
```

HTML 使用 `data-iwencai-module`、`data-stock-code/name`、`data-sector`、`data-local-as-of`；上下文 `<option>` 使用 escaped `data-*`，不序列化整个对象。

- [ ] **Step 4: 个股页切换到共享渲染器**

删除 `stock_workspace.py` 内部 `_render_iwencai_research_console`，保持现有位置和文案契约。

- [ ] **Step 5: 运行共享渲染与原个股 UI 测试**

Run: `PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest tests/test_web_iwencai_four_workspaces.py tests/test_web_stock_research_workspace.py -q`

Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add src/stock_ts/webapp/research_console.py src/stock_ts/webapp/stock_workspace.py src/stock_ts/webapp/__init__.py tests/test_web_iwencai_four_workspaces.py
git commit -m '[界面组件] 抽出问财共享研究坞'
```

### Task 4: 接入大盘、持仓与机会工作台

**Files:**
- Modify: `src/stock_ts/webapp/market_workspace.py`
- Modify: `src/stock_ts/webapp/portfolio_workspace.py`
- Modify: `src/stock_ts/webapp/opportunity_workspace.py`
- Modify: `src/stock_ts/web.py`
- Modify: `tests/test_web_iwencai_four_workspaces.py`

- [ ] **Step 1: 写四页位置与上下文失败测试**

断言：market 研究坞位于五步轨道后、三情景前；portfolio 位于处置队列后、持仓证据前；stock 维持关键证据后；opportunity 位于证据漏斗后、研究候选前。完整页面四个 workspace 各有且只有一个 `data-iwencai-research`。

- [ ] **Step 2: 运行测试确认只有个股页存在研究坞**

Run: `PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest tests/test_web_iwencai_four_workspaces.py -q`

Expected: FAIL，market/portfolio/opportunity 缺入口。

- [ ] **Step 3: 为三个 workspace 增加 `iwencai_status` 参数**

market 直接渲染无选择器研究坞；portfolio 从 `dossier.queue` 构造名称/代码选项；opportunity 从 `dossier.candidates` 构造候选选项并增加去重板块选项。只从领域对象读取允许字段。

- [ ] **Step 4: 在 `web.py` 四个渲染调用中传入安全状态**

使用 `_iwencai_research_ui_status()`，不把 Key 或配置值传入 renderer。

- [ ] **Step 5: 运行四页、机会和持仓回归**

Run: `PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest tests/test_web_iwencai_four_workspaces.py tests/test_web_module_decisions.py tests/test_web_opportunity_dossier.py tests/test_web_portfolio_interaction.py -q`

Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add src/stock_ts/webapp/market_workspace.py src/stock_ts/webapp/portfolio_workspace.py src/stock_ts/webapp/opportunity_workspace.py src/stock_ts/web.py tests/test_web_iwencai_four_workspaces.py
git commit -m '[界面集成] 接入四工作台外部核查'
```

### Task 5: 泛化交互脚本与响应式样式

**Files:**
- Modify: `src/stock_ts/webapp/shell.py`
- Modify: `src/stock_ts/webapp/styles.py`
- Modify: `tests/test_web_iwencai_four_workspaces.py`
- Modify: `tests/test_web_stock_research_workspace.py`

- [ ] **Step 1: 写浏览器 payload 与安全渲染失败测试**

断言脚本读取 `data-iwencai-module` 和选中 option 的 `dataset`，发送嵌套 `context`；仍使用 `textContent`/DOM node，不使用 `innerHTML` 渲染外部结果。断言选择器、四模块窄屏和 reduced-motion CSS 存在。

- [ ] **Step 2: 运行测试确认旧脚本只发送个股扁平字段**

Run: `PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest tests/test_web_iwencai_four_workspaces.py tests/test_web_stock_research_workspace.py -q`

Expected: FAIL，缺少 module/context selector 逻辑。

- [ ] **Step 3: 最小泛化提交与上下文同步**

表单提交时从固定 `data-*` 或选中 option 读取 `code/name/sector/local_as_of`，构造 `{module, question, context}`；切换上下文时不自动请求。结果标题显示技能与 `context_label`。

- [ ] **Step 4: 收紧 CSS**

保持现有配色、字体和证据卡；新增 `.iwencai-context-select`，桌面端与输入同一操作带，390px 下单列。研究坞不增加渐变、头像、气泡或背景插画。

- [ ] **Step 5: 运行交互、布局与紧凑模式测试**

Run: `PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest tests/test_web_iwencai_four_workspaces.py tests/test_web_stock_research_workspace.py tests/test_web_layout.py tests/test_web_compact_mode.py -q`

Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add src/stock_ts/webapp/shell.py src/stock_ts/webapp/styles.py tests/test_web_iwencai_four_workspaces.py tests/test_web_stock_research_workspace.py
git commit -m '[交互体验] 统一四模块问财核查交互'
```

### Task 6: 验证、审查与部署

**Files:**
- Modify: `docs/superpowers/iwencai-four-workspaces/TODO.md`
- Create: `docs/superpowers/iwencai-four-workspaces/test.md`
- Create: `docs/superpowers/iwencai-four-workspaces/review.md`
- Create: `docs/superpowers/iwencai-four-workspaces/handoff.md`

- [ ] **Step 1: 运行专项和 lint**

```bash
make lint
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest \
  tests/test_iwencai.py tests/test_iwencai_four_workspaces.py \
  tests/test_web_iwencai_research.py tests/test_web_iwencai_four_workspaces.py \
  tests/test_web_stock_research_workspace.py tests/test_web_auth.py -q
```

- [ ] **Step 2: 运行全量测试并区分既有基线**

Run: `PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q`

Expected: 新增测试通过；若仍有 `tests/test_daily_pipeline.py` 的 5 个既有失败，按用例名记录，不写成全量通过。

- [ ] **Step 3: 本地浏览器检查**

启动本地服务，登录后检查 1280px 和 390px：四个研究坞位置、上下文选择、加载/错误/结果状态、无横向溢出；匿名模式保持禁用。

- [ ] **Step 4: 代码审查**

重点检查模块白名单、旧 payload 兼容、持仓隐私、动态字段 DOM 安全、限流共享和 stale 闸门边界；把 findings 与残余风险写入 `review.md`。

- [ ] **Step 5: 提交验收记录**

```bash
git add docs/superpowers/iwencai-four-workspaces
git commit -m '[交付验收] 完成问财四工作台验收'
```

- [ ] **Step 6: 推送与服务器部署**

推送 `main`，创建 `/opt/stock-ts/.deploy_backups/iwencai-four-workspaces-<timestamp>/source-before.tar.gz`，使用 Git bundle `--ff-only` 快进服务器；不覆盖 `.env`、持仓、快照、报告和认证数据。编译改动 Python 文件并重启 `stock-ts.service`。

- [ ] **Step 7: 生产真实技能验收**

登录态分别调用 market、portfolio、stock、opportunity，确认技能 ID、HTTP 200、事实数量和 `secret_leak=false`；匿名请求仍为 HTTP 401，公网 `/healthz` 为 200。

- [ ] **Step 8: 三端一致性**

确认本地 `main`、GitHub `main`、服务器 `/opt/stock-ts` HEAD 一致且 tracked worktree 干净，更新 `TODO.md`、`test.md` 和 `handoff.md` 后提交最终部署记录。

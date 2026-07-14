# Research Action Dock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为四个原生研究工作台增加同步状态导航、移动端底部行动坞、结果直达动作和键盘操作，使用户更快找到风险与证据。

**Architecture:** 保持现有服务端协议和按需请求不变；`shell.py` 输出可被研究状态增强的桌面导航，`engine_workspace.py` 统一输出核心工作台、移动行动坞和客户端交互，`styles.py` 只追加研究行动坞样式。所有动态内容继续用 DOM 文本节点渲染，桌面与移动导航共享 `data-workspace` 和模块状态源。

**Tech Stack:** Python 3.11、服务端 HTML 字符串、原生 JavaScript、CSS、pytest、BeautifulSoup

---

## 文件职责

- `src/stock_ts/webapp/shell.py`：为四个核心桌面导航项输出状态钩子和初始无障碍状态。
- `src/stock_ts/webapp/engine_workspace.py`：输出模块行动轨、稳定跳转目标、移动行动坞，并实现状态同步、跳转、快捷键和详情关闭交互。
- `src/stock_ts/webapp/__init__.py`：导出移动行动坞渲染函数。
- `src/stock_ts/web.py`：只在原生研究页面装配移动行动坞。
- `src/stock_ts/webapp/styles.py`：定义状态点、行动轨、底部行动坞、焦点与响应式样式。
- `tests/test_web_native_research_workspaces.py`：覆盖 HTML 契约、交互脚本、安全边界和移动 CSS。
- `docs/superpowers/iwencai-native-workspaces/test.md`：记录本次专项、全量和浏览器验证。

### Task 1: 固定导航与直达动作 HTML 契约

**Files:**
- Modify: `tests/test_web_native_research_workspaces.py`
- Modify: `src/stock_ts/webapp/shell.py`
- Modify: `src/stock_ts/webapp/engine_workspace.py`
- Modify: `src/stock_ts/webapp/__init__.py`
- Modify: `src/stock_ts/web.py`

- [ ] **Step 1: 写失败测试**

增加测试，要求每个工作台恰好包含三个 `data-engine-jump` 动作及 `risk/findings/evidence` 目标；页面恰好包含一个移动行动坞和四个核心按钮；桌面与移动核心按钮都具有 `data-engine-nav-state="idle"`，非核心按钮没有状态钩子。

```python
def test_each_workspace_exposes_three_result_shortcuts() -> None:
    soup = BeautifulSoup(render_page(stock_code="600519"), "html.parser")
    for module in ("market", "portfolio", "stock", "opportunity"):
        workspace = soup.select_one(f'[data-engine-workspace="{module}"]')
        assert [node["data-engine-jump"] for node in workspace.select("[data-engine-jump]")] == [
            "risk", "findings", "evidence"
        ]
        for target in ("risk", "findings", "evidence"):
            assert workspace.select_one(f'[data-engine-target="{target}"]') is not None


def test_native_page_has_four_item_mobile_research_dock() -> None:
    soup = BeautifulSoup(render_page(stock_code="600519"), "html.parser")
    docks = soup.select('[data-engine-mobile-dock]')
    assert len(docks) == 1
    buttons = docks[0].select('[data-engine-mobile-nav][data-workspace]')
    assert [button["data-workspace"] for button in buttons] == [
        "market", "portfolio", "stock", "opportunity"
    ]
    assert all(button["data-engine-nav-state"] == "idle" for button in buttons)
```

- [ ] **Step 2: 运行测试并确认因缺少行动坞失败**

Run: `pytest -q tests/test_web_native_research_workspaces.py -k 'shortcuts or mobile_research_dock or navigation_state'`

Expected: FAIL，失败原因是找不到 `data-engine-jump`、`data-engine-mobile-dock` 或 `data-engine-nav-state`。

- [ ] **Step 3: 实现最小 HTML 结构**

在 `render_engine_workspace()` 中给风险卡、发现标题和 `details` 增加稳定目标与 `tabindex="-1"`，在判断卡后输出：

```html
<nav class="engine-action-rail" aria-label="结果直达">
  <button type="button" data-engine-jump="risk">先看风险</button>
  <button type="button" data-engine-jump="findings">看三条发现</button>
  <button type="button" data-engine-jump="evidence">展开完整依据</button>
</nav>
```

新增 `render_engine_mobile_dock()`，只循环 `market/portfolio/stock/opportunity`，每个按钮输出 `data-engine-mobile-nav`、`data-workspace`、`data-engine-nav-state="idle"` 和屏幕阅读器状态。`render_sidebar()` 只为这四个核心项增加同样状态钩子。通过 `webapp/__init__.py` 导出，并在 `_render_native_research_page()` 的壳内装配一次。

- [ ] **Step 4: 运行专项测试**

Run: `pytest -q tests/test_web_native_research_workspaces.py`

Expected: PASS。

- [ ] **Step 5: 提交 HTML 契约**

```bash
git add tests/test_web_native_research_workspaces.py src/stock_ts/webapp/shell.py src/stock_ts/webapp/engine_workspace.py src/stock_ts/webapp/__init__.py src/stock_ts/web.py
git commit -m "feat(研究工作台): 增加行动导航结构"
```

### Task 2: 实现状态同步、跳转与快捷键

**Files:**
- Modify: `tests/test_web_native_research_workspaces.py`
- Modify: `src/stock_ts/webapp/engine_workspace.py`

- [ ] **Step 1: 写失败测试**

增加脚本契约测试，覆盖状态同步、`aria-current`、输入保护、数字键和 `R`、详情展开滚动及 `Escape` 关闭。

```python
def test_engine_script_coordinates_navigation_and_shortcuts() -> None:
    script = engine_app_script()
    for fragment in (
        "setEngineNavigationState",
        "data-engine-nav-state",
        "aria-current",
        "isContentEditable",
        "event.key.toLowerCase() === 'r'",
        "engineKeyboardModules",
        "data-engine-jump",
        "scrollIntoView",
        "event.key === 'Escape'",
    ):
        assert fragment in script
```

- [ ] **Step 2: 运行测试并确认因脚本能力缺失而失败**

Run: `pytest -q tests/test_web_native_research_workspaces.py::test_engine_script_coordinates_navigation_and_shortcuts`

Expected: FAIL，首个缺失项为 `setEngineNavigationState`。

- [ ] **Step 3: 实现状态与交互**

在 `engine_app_script()` 中实现：

```javascript
const engineKeyboardModules = ['market', 'portfolio', 'stock', 'opportunity'];

function setEngineNavigationState(module, state) {
  document.querySelectorAll(`[data-workspace="${module}"][data-engine-nav-state]`).forEach((item) => {
    item.dataset.engineNavState = state;
    const label = item.querySelector('[data-engine-nav-status]');
    if (label) label.textContent = engineStateLabels[state] || engineStateLabels.idle;
  });
}
```

请求开始设置 `loading`；持仓模块实时文案改为“正在逐只核对，可能需要几秒”，其余模块显示“正在生成判断…”。渲染结果时把 `complete` 映射为完成，`partial/empty` 映射为待补证据，其他错误映射为不可用。切换模块时同步所有导航的 `active` 与 `aria-current`。点击 `data-engine-jump` 时定位当前工作台内的目标、调用 `scrollIntoView()` 并只在该用户动作中聚焦；依据目标先打开 `details`。键盘监听对输入、选择、文本域和 `isContentEditable` 提前返回；`1-4` 切换模块，`R` 刷新当前核心模块，`Escape` 关闭活动页详情并将焦点还给摘要。

- [ ] **Step 4: 运行专项测试**

Run: `pytest -q tests/test_web_native_research_workspaces.py`

Expected: PASS。

- [ ] **Step 5: 提交交互逻辑**

```bash
git add tests/test_web_native_research_workspaces.py src/stock_ts/webapp/engine_workspace.py
git commit -m "feat(研究工作台): 同步状态与快捷交互"
```

### Task 3: 完成研究行动坞视觉与移动适配

**Files:**
- Modify: `tests/test_web_native_research_workspaces.py`
- Modify: `src/stock_ts/webapp/styles.py`

- [ ] **Step 1: 写失败测试**

增加 CSS 契约测试，要求底部行动坞默认隐藏、760px 以下固定显示、使用安全区、按钮不低于 44px，并要求状态点覆盖五态和 reduced-motion。

```python
def test_mobile_research_dock_is_fixed_safe_and_touchable() -> None:
    assert ".engine-mobile-dock" in CSS
    assert "env(safe-area-inset-bottom)" in CSS
    assert "position:fixed" in CSS.replace(" ", "")
    assert "min-height:44px" in CSS.replace(" ", "")
    for state in ("idle", "loading", "complete", "partial", "unavailable"):
        assert f'[data-engine-nav-state="{state}"]' in CSS
```

- [ ] **Step 2: 运行测试并确认因 CSS 缺失失败**

Run: `pytest -q tests/test_web_native_research_workspaces.py::test_mobile_research_dock_is_fixed_safe_and_touchable`

Expected: FAIL，失败原因是缺少 `.engine-mobile-dock`。

- [ ] **Step 3: 实现最小视觉系统**

在原生研究工作台样式区追加：默认隐藏移动坞；状态点用灰、蓝、绿、琥珀、红五态；`loading` 仅状态点脉冲；行动轨为低噪声纸白按钮；跳转目标保留明确焦点环。760px 以下固定行动坞、四等分、44px 触控高度和安全区，并给 `.engine-workspace-root` 增加对应底部留白。`prefers-reduced-motion` 下关闭状态脉冲和顺滑滚动。

- [ ] **Step 4: 运行专项测试与静态检查**

Run: `pytest -q tests/test_web_native_research_workspaces.py && make lint`

Expected: 测试全部 PASS，lint clean。

- [ ] **Step 5: 提交样式**

```bash
git add tests/test_web_native_research_workspaces.py src/stock_ts/webapp/styles.py
git commit -m "style(研究工作台): 完成移动行动坞"
```

### Task 4: 浏览器验证与交付记录

**Files:**
- Modify: `docs/superpowers/iwencai-native-workspaces/test.md`

- [ ] **Step 1: 启动当前工作树服务**

Run: `set -a; source /Users/fangjie/Documents/StockTs/.env; set +a; PYTHONPATH=src HOST=127.0.0.1 PORT=8765 python3 -m stock_ts.web`

Expected: 服务监听 `http://127.0.0.1:8765/`，日志和页面不输出凭证。

- [ ] **Step 2: 验证桌面和移动端**

在 1280px 验证侧栏状态、行动轨、详情跳转、`1-4` 和 `R`；在 390px 验证底部行动坞固定、四项完整、无水平溢出、页面末尾不被遮挡。检查控制台无错误。

- [ ] **Step 3: 运行最终验证**

Run: `pytest -q tests/test_web_native_research_workspaces.py tests/test_research_engine.py tests/test_research_evidence.py && make lint`

Expected: 专项测试全部 PASS，lint clean。

- [ ] **Step 4: 更新验证记录**

在 `docs/superpowers/iwencai-native-workspaces/test.md` 追加本次命令、通过数量、桌面/移动视口、交互检查和已知全量基线，不覆盖既有记录。

- [ ] **Step 5: 提交验证记录**

```bash
git add docs/superpowers/iwencai-native-workspaces/test.md
git commit -m "docs(研究工作台): 记录行动坞验证结果"
```

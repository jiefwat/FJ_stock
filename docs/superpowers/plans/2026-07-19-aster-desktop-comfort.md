# Aster Market Desktop Comfort Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Aster Market 调整为首屏更紧凑、文字更易读、模块切换和股票查询更顺滑的桌面投研工作台，并消除生产快照重复解析造成的 3–10 秒等待。

**Architecture:** 新建独立的线程安全快照缓存，以目标文件指纹自动失效，HTTP handler 只消费缓存状态；浏览器仍是无框架原生 JavaScript，但增加请求取消、会话缓存、滚动位置和快捷键。HTML 数据契约、只读 API、localStorage 持仓和桌面最小宽度保持不变。

**Tech Stack:** Python 3.11 标准库、`ThreadingHTTPServer`、不可变 dataclass、原生 HTML/CSS/JavaScript、Pytest、Ruff。

---

## 文件边界

- Create: `src/aster_market/snapshot_cache.py`：只负责快照文件指纹、线程锁、解析结果和 presenter view 缓存。
- Modify: `src/aster_market/web.py`：每个 server/handler 使用一个缓存实例，不再直接重复调用 `load_snapshot`。
- Modify: `src/aster_market/ui.py`：压缩命令带与大盘首屏，加入快捷键提示、状态提示容器和新资源版本。
- Modify: `src/aster_market/ui_modules.py`：压缩三个模块标题区，增加结构化股票加载骨架和操作反馈锚点。
- Modify: `src/aster_market/assets/app.css`：收紧大盘首屏与命令带，提高正文和数据字号。
- Modify: `src/aster_market/assets/modules.css`：收紧机会、股票、持仓工作面并补齐交互状态。
- Modify: `src/aster_market/assets/app.js`：模块滚动位置、快捷键、请求取消、搜索/个股缓存、toast 和刷新状态。
- Modify: `src/aster_market/assets/portfolio.js`：复用公开股票缓存并提供本机保存/删除/清空反馈。
- Create: `tests/test_snapshot_cache.py`：缓存命中、原子替换、缺失恢复和线程安全。
- Modify: `tests/test_web.py`、`tests/test_ui.py`：缓存接线、结构、资源和桌面交互契约。
- Create: `docs/superpowers/aster-desktop-comfort/test.md`：本地、浏览器、性能和公网验收记录。

### Task 1: 快照指纹缓存

**Files:**
- Create: `src/aster_market/snapshot_cache.py`
- Create: `tests/test_snapshot_cache.py`

- [ ] **Step 1: 写缓存命中失败测试**

```python
def test_unchanged_snapshot_is_parsed_once(tmp_path, monkeypatch):
    path = tmp_path / "snapshot.json"
    path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    calls = 0
    real_loader = snapshot_cache.load_snapshot

    def counting_loader(candidate):
        nonlocal calls
        calls += 1
        return real_loader(candidate)

    monkeypatch.setattr(snapshot_cache, "load_snapshot", counting_loader)
    cache = SnapshotCache()
    assert cache.get(path).view["status"] == "ready"
    assert cache.get(path).view["status"] == "ready"
    assert calls == 1
```

- [ ] **Step 2: 运行测试并确认 RED**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_snapshot_cache.py`

Expected: FAIL，因为 `aster_market.snapshot_cache` 尚不存在。

- [ ] **Step 3: 实现最小线程安全缓存**

```python
@dataclass(frozen=True)
class CachedSnapshot:
    fingerprint: tuple[int, int, int] | None
    result: SnapshotResult
    view: dict[str, Any]


class SnapshotCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: CachedSnapshot | None = None

    def get(self, path: Path) -> CachedSnapshot:
        fingerprint = _fingerprint(path)
        with self._lock:
            if self._state is not None and self._state.fingerprint == fingerprint:
                return self._state
            result = load_snapshot(path)
            view = (
                build_view(result.snapshot)
                if result.snapshot is not None
                else {"status": result.status, "message": result.message}
            )
            self._state = CachedSnapshot(fingerprint, result, view)
            return self._state
```

- [ ] **Step 4: 补原子替换与并发测试**

原子替换测试先读取交易日 A，再用 `replacement.replace(path)` 写入交易日 B，断言第二次 `get()` 返回 B。并发测试用 `ThreadPoolExecutor(max_workers=8)` 同时调用 `get()`，断言计数 loader 只执行一次。

- [ ] **Step 5: 运行测试并提交**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_snapshot_cache.py`

Expected: PASS。

Commit: `[性能优化] 缓存运行时行情快照`

### Task 2: HTTP 服务接入缓存

**Files:**
- Modify: `src/aster_market/web.py:22-183`
- Modify: `tests/test_web.py`

- [ ] **Step 1: 写 HTTP 缓存失效测试**

```python
def test_server_reloads_snapshot_after_atomic_replacement(tmp_path):
    path = tmp_path / "snapshot.json"
    path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    with running_server(path) as base_url:
        first = json.loads(_get(f"{base_url}/api/snapshot")[2])
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["market"]["trade_date"] = "2026-07-19"
        replacement = path.with_suffix(".staging")
        replacement.write_text(json.dumps(payload), encoding="utf-8")
        replacement.replace(path)
        second = json.loads(_get(f"{base_url}/api/snapshot")[2])
    assert first["trade_date"] == "2026-07-18"
    assert second["trade_date"] == "2026-07-19"
```

- [ ] **Step 2: 运行测试并确认 RED**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_web.py::test_server_reloads_snapshot_after_atomic_replacement`

Expected: 新测试存在但 handler 尚未使用缓存合同。

- [ ] **Step 3: handler 使用闭包缓存**

```python
def create_handler(snapshot_path=None, snapshot_cache=None):
    cache = snapshot_cache or SnapshotCache()

    class AsterRequestHandler(BaseHTTPRequestHandler):
        def _snapshot_state(self):
            return cache.get(self._snapshot_path())
```

`/` 与 `/api/snapshot` 使用 `state.view`；其余分析 API 使用 `state.result.snapshot`。删除 `_view_for()` 和 handler 内直接 `load_snapshot()`。

- [ ] **Step 4: 运行 Web 契约测试并提交**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_web.py tests/test_snapshot_cache.py`

Expected: PASS，404、503、`no-store` 和原子更新均保持。

Commit: `[服务性能] 接入指纹快照缓存`

### Task 3: 紧凑桌面工作面

**Files:**
- Modify: `src/aster_market/ui.py:292-342`
- Modify: `src/aster_market/ui_modules.py`
- Modify: `src/aster_market/assets/app.css`
- Modify: `src/aster_market/assets/modules.css`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: 写视觉结构失败测试**

```python
def test_ui_exposes_comfort_workbench_contract():
    html = render_app(_sample_view())
    css = asset_text("modules.css") + asset_text("app.css")
    assert 'data-keyboard-hint="1-4"' in html
    assert "data-toast" in html
    assert "stock-loading-skeleton" in html
    assert "min-height: 112px" in css
    assert "font-size: 12px" in css
```

- [ ] **Step 2: 运行测试并确认 RED**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_ui.py::test_ui_exposes_comfort_workbench_contract`

Expected: FAIL，新的工作台结构尚不存在。

- [ ] **Step 3: 调整 HTML 结构**

命令带显示短时间、快捷键提示和单一 toast 容器；股票 loading 改为三段骨架。资源版本统一提升为 `comfort-v3`，防止公网继续使用旧 CSS/JS。

- [ ] **Step 4: 调整 CSS**

命令带约 64px；模块 heading 约 112px；机会正文和证据说明至少 11–12px；股票图表与空状态降低高度；持仓表单和汇总首屏可见。保持 `min-width: 1180px`，不得新增 viewport meta 或 `@media (max-width: ...)`。

- [ ] **Step 5: 运行 UI 测试并提交**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_ui.py`

Expected: PASS。

Commit: `[界面体验] 收紧桌面分析工作面`

### Task 4: 丝滑交互状态

**Files:**
- Modify: `src/aster_market/assets/app.js`
- Modify: `src/aster_market/assets/portfolio.js`
- Modify: `src/aster_market/assets/modules.css`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: 写资源契约失败测试**

```python
def test_interaction_assets_include_smooth_workbench_controls():
    app = asset_text("app.js")
    portfolio = asset_text("portfolio.js")
    assert "AbortController" in app
    assert "moduleScrollPositions" in app
    assert 'event.key === "/"' in app
    assert "AsterStockCache" in app
    assert "aster:toast" in app
    assert "AsterStockCache" in portfolio
```

- [ ] **Step 2: 运行测试并确认 RED**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_ui.py::test_interaction_assets_include_smooth_workbench_controls`

Expected: FAIL，交互控制尚未实现。

- [ ] **Step 3: 实现模块和键盘交互**

保存离开模块时的 `window.scrollY`，切换后恢复目标模块位置；`1–4` 切换模块，`/` 聚焦全局搜索，输入控件内不拦截按键。模块切换只执行 180ms 入场动画，不强制平滑滚顶。

- [ ] **Step 4: 实现请求取消与会话缓存**

搜索使用一个 `AbortController` 和 220ms 共享防抖；被取消的请求静默结束。`window.AsterStockCache = new Map()` 存储个股 Promise，股票分析和持仓共同复用；搜索结果按 query 缓存。

- [ ] **Step 5: 实现反馈与 reduced motion**

统一监听 `aster:toast`，显示 1.8 秒提示。刷新按钮先显示“读取中”；持仓保存、编辑、删除和清空派发明确反馈。CSS 对 `prefers-reduced-motion: reduce` 关闭位移和骨架扫光。

- [ ] **Step 6: 运行资源与语法测试并提交**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_ui.py && node --check src/aster_market/assets/app.js && node --check src/aster_market/assets/portfolio.js`

Expected: PASS。

Commit: `[交互体验] 完善快捷操作与加载反馈`

### Task 5: 浏览器、性能与公网验收

**Files:**
- Create: `docs/superpowers/aster-desktop-comfort/test.md`
- Modify: `docs/TODO.md`

- [ ] **Step 1: 全量本地验证**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q && ruff check src tests && python3 -m compileall -q src`

Expected: 全部通过。

- [ ] **Step 2: 本地真实浏览器验收**

用测试快照启动本地服务，逐项验证：四模块按钮、`1–4`、`/`、机会到个股、快速连续搜索、加入持仓、保存/编辑/删除、刷新按钮、控制台无错误。检查 1280、1536、1920 三档桌面无横向溢出。

- [ ] **Step 3: 提交并推送**

Commit: `[质量验收] 记录桌面舒适度验证`

Push: `git push origin main`

- [ ] **Step 4: 原子部署**

创建 `/opt/aster-market/releases/<timestamp>-<short-hash>`，上传 `git archive HEAD`，原子切换 `/opt/aster-market/current`，只重启 `stock-ts.service`。保留快照链接，不修改 Nginx、Signal Desk 或行情刷新任务。

- [ ] **Step 5: 公网性能与服务验证**

先请求一次预热，再连续请求首页、市场分析、机会和个股接口；断言首字节均小于 250ms。确认公网四模块可交互，`stock-ts.service`、`stock-ts-signal-desk.service`、Nginx 均为 active，主服务 `NRestarts=0`。

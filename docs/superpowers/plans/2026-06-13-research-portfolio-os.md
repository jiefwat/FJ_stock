# Research Portfolio OS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 StockTS Web 入口重构为研究 + 组合一体化操作系统，并保证交互、结构和测试都稳定可用。

**Architecture:** 保留既有分析引擎与 workflow 编排，新增 `webapp` 装配层和工作区渲染层，将 `web.py` 从巨型模板文件收缩为入口与请求处理器。交互上以工作区而非模块堆叠为中心，统一表单与跳转协议。

**Tech Stack:** Python 3.9+, 标准库 `http.server`, pytest, ruff, 现有 StockTS workflow / analysis / report 模块。

---

### Task 1: 建立 WebApp 装配骨架

**Files:**
- Create: `src/stock_ts/webapp/__init__.py`
- Create: `src/stock_ts/webapp/view_models.py`
- Create: `src/stock_ts/webapp/composition.py`
- Modify: `src/stock_ts/web.py`
- Test: `tests/test_web_app_shell.py`

- [ ] 建立页面上下文 dataclass，承载 workspace、焦点标的、候选焦点、notice 与分析结果。
- [ ] 将 `render_page` 的数据组装逻辑迁移到 `composition.py`。
- [ ] 让 `web.py` 调用新的装配入口，而不是直接承担所有渲染细节。
- [ ] 运行目标测试并确认页面仍能渲染主要入口。

### Task 2: 重做产品壳与导航协议

**Files:**
- Create: `src/stock_ts/webapp/shell.py`
- Modify: `src/stock_ts/web.py`
- Test: `tests/test_web_layout.py`
- Test: `tests/test_web_user_comfort.py`

- [ ] 在新壳层中实现 workspace 导航、顶部研究会话条、统一脚本与样式承载。
- [ ] 将原“模块切换”语义升级为“工作区切换”语义，保留必要子模块锚点。
- [ ] 统一按钮行为契约：切 workspace、切上下文、提交表单三类。
- [ ] 更新测试，确认工作区标签、默认入口与跳转脚本可见。

### Task 3: 重组研究中枢

**Files:**
- Create: `src/stock_ts/webapp/workspaces.py`
- Modify: `src/stock_ts/web.py`
- Test: `tests/test_web_professional_modules.py`
- Test: `tests/test_workflows_cache_web.py`

- [ ] 将市场、板块、候选、个股、公告、技术、交易计划收束进“研究中枢”。
- [ ] 将候选焦点与个股工作台之间的切换做成清晰链路。
- [ ] 移除“像报告章节一样平铺”的主视图组织方式。
- [ ] 增加研究中枢相关断言，确保关键入口仍可见。

### Task 4: 重组组合中枢

**Files:**
- Create: `src/stock_ts/webapp/forms.py`
- Modify: `src/stock_ts/web.py`
- Test: `tests/test_web_portfolio_interaction.py`

- [ ] 将持仓列表、编辑区、调仓建议、风险预算整合为单一组合中枢视图。
- [ ] 把新增 / 编辑 / 删除 / 结束编辑统一走明确的 workspace 跳转。
- [ ] 为删除按钮增加客户端确认提示。
- [ ] 更新测试验证动作按钮、跳转目标和编辑态文案。

### Task 5: 收束执行中枢与归档系统

**Files:**
- Modify: `src/stock_ts/web.py`
- Test: `tests/test_web_professional.py`
- Test: `tests/test_web_data_sources.py`

- [ ] 将今日动作、交易计划、盘中清单收束到执行中枢。
- [ ] 将日报、数据质量、系统状态收束到归档与系统区。
- [ ] 保留专业化文案与多源数据矩阵，但降低它们对主流程的干扰。
- [ ] 更新测试断言，确保执行 / 系统相关信息仍存在。

### Task 6: 全量验收与启动

**Files:**
- Modify: `docs/superpowers/daily-analysis-workbench/test.md`

- [ ] 运行 `make lint`。
- [ ] 运行 `make test`。
- [ ] 运行 Web GET / 持仓交互冒烟验证。
- [ ] 回写测试证据到 `docs/superpowers/daily-analysis-workbench/test.md`。
- [ ] 启动 `PYTHONPATH=src python3 -m stock_ts.web` 并确认 `127.0.0.1:8501` 可访问。

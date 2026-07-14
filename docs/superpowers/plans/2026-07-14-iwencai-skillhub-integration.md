# 问财 SkillHub 研究集成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在个股页提供服务端安全代理的问财研究追问，并完成测试、合并和公网部署。

**Architecture:** `iwencai.py` 隔离外部契约与路由，`web.py` 暴露同源 JSON endpoint，`stock_workspace.py` 与 `shell.py` 负责精简交互。外部结果只作为证据，不改变本地研究模型。

**Tech Stack:** Python 标准库 `urllib`、`http.server`、服务端 HTML、原生 JavaScript、pytest、ruff、systemd、Nginx。

---

### Task 1: 外部技能客户端与路由

**Files:**
- Create: `src/stock_ts/iwencai.py`
- Create: `tests/test_iwencai.py`

- [ ] 先写路由、缺 Key、请求头、成功响应、超时和错误脱敏测试。
- [ ] 运行 `PYTHONPATH=src .venv311/bin/pytest tests/test_iwencai.py -q`，确认因模块缺失而失败。
- [ ] 实现 `IwencaiSkillClient`、`route_stock_research_skill`、`compress_iwencai_result` 和安全配置摘要。
- [ ] 重跑专项测试，确认通过。

### Task 2: JSON endpoint 与安全边界

**Files:**
- Modify: `src/stock_ts/web.py`
- Create: `tests/test_web_iwencai_research.py`

- [ ] 先写 endpoint 的登录边界、JSON 校验、长度限制、无 Key 降级、成功返回和 Key 不泄露测试。
- [ ] 运行 endpoint 专项测试并确认预期失败。
- [ ] 实现 `POST /api/iwencai/research`、16 KiB 请求限制和进程内限流。
- [ ] 重跑 endpoint 与 Web auth 测试。

### Task 3: 个股研究调度台

**Files:**
- Modify: `src/stock_ts/webapp/stock_workspace.py`
- Modify: `src/stock_ts/webapp/shell.py`
- Modify: `src/stock_ts/webapp/styles.py`
- Modify: `tests/test_web_stock_research_workspace.py`

- [ ] 先写页面结构、快捷问题、状态、无旁白和移动端 CSS 测试。
- [ ] 运行页面专项测试并确认预期失败。
- [ ] 在关键证据之后渲染研究调度台，添加 fetch、加载、结果和错误状态。
- [ ] 增加窄屏、键盘焦点和 reduced-motion 样式，重跑页面测试。

### Task 4: 文档与验证

**Files:**
- Modify: `docs/architecture/README.md`
- Modify: `docs/tech-specs/README.md`
- Modify: `docs/superpowers/iwencai-skillhub-integration/TODO.md`
- Modify: `docs/superpowers/iwencai-skillhub-integration/test.md`
- Modify: `docs/superpowers/iwencai-skillhub-integration/review.md`
- Modify: `docs/superpowers/iwencai-skillhub-integration/handoff.md`

- [ ] 记录官方契约、环境变量、安全边界和真实测试结果。
- [ ] 运行专项、Web 回归、`make lint` 与 `make test`。
- [ ] 启动本地服务，用桌面和 390px 检查个股页。

### Task 5: 合并与公网部署

**Files:**
- Modify: `main` branch history and server checkout only; preserve server `.env`, data, reports and service configuration.

- [ ] 审查 diff 和 Key 泄露风险，提交功能分支。
- [ ] 合并到 `main` 并推送 `origin/main`。
- [ ] 备份 `/opt/stock-ts` 源码，拉取 `main`，保留运行数据和凭证。
- [ ] 在服务器配置现有 `IWENCAI_API_KEY`（若存在）；若缺失，保持明确降级，不伪造真实调用。
- [ ] 重启 `stock-ts.service`，验证服务、`/healthz`、公网个股页和 endpoint 安全响应。

# 完整股票研究系统测试记录

## 专项自动化

- 命令：`pytest -q tests/test_research_engine.py tests/test_research_evidence.py tests/test_research_snapshots.py tests/test_daily_research.py tests/test_web_native_research_workspaces.py tests/test_web_research_workspace_api.py tests/test_iwencai.py tests/test_iwencai_four_workspaces.py`
- 结果：135 项通过；覆盖产品协议、四模块能力、快照降级、并发原子写、每日任务、登录边界、供应商中性输出和响应式页面。
- 静态检查：`make lint` 与 `git diff --check` 通过。

## 真实数据

- 大盘：3 个指数趋势项，覆盖 3/4；过期事件不进入首屏。
- 持仓：当前 11 只全部分析，页面显示 `已分析 11/11`。
- 个股：大业股份 8 个维度，7/8 可用；财务、经营、预期、事件、行情、行业、公告和研报标签可区分。
- 机会：10 只候选，每只包含代码、名称、依据、失效条件和个股研究入口。
- 每日任务：生成 `market/latest.json`、`opportunity/latest.json`、日期归档和 `daily.status.json`。

## 浏览器

- 桌面：1280x900，四模块可切换，无横向溢出。
- 移动：390x844，底部行动坞可切换，四模块卡片单列，无横向溢出。
- 控制台：未发现 error、warn 或 warning。

## 全量基线

- 当前分支全量：600 通过、141 失败。
- `main` 同环境基线：565 通过、152 失败。
- 差异：当前分支没有新增失败，并修复 11 个既有失败；剩余失败集中在 legacy 页面契约和旧日报流水线，与本次原生四模块专项无新增回归关系。

## 公网验证

- `stock-ts.service`：`active/running`，`/healthz` 返回 200。
- 登录边界：`/login` 返回 200，未登录根路径返回 303 到登录页。
- 登录后真实接口：大盘 3 项、持仓 11/11、个股 7/8、机会 10 项，四个请求均返回 200。
- `stock-ts-daily-research.timer`：`active/waiting`、`enabled`，下一次执行为北京时间 07:20。
- 每日任务：最近一次 `Result=success`，大盘与机会快照均已在服务器生成。
- 版本：本地、GitHub 和服务器 `main` 在最终文档提交后核对一致。

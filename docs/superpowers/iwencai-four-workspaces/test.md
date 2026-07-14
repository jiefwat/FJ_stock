# Test Record

## 自动化验证

| 验证 | 结果 | 覆盖 |
|---|---|---|
| `make lint` | 通过 | 全仓 Python 与测试静态检查 |
| `pytest tests/test_iwencai.py tests/test_iwencai_four_workspaces.py tests/test_web_iwencai_research.py tests/test_web_iwencai_four_workspaces.py tests/test_web_stock_research_workspace.py tests/test_web_auth.py -q` | `99 passed` | 14 个技能、模块白名单、payload、隐私、鉴权、限流、四页 UI、脚本与安全渲染 |
| `pytest -q` | `643 passed, 5 failed, 10 warnings` | 全仓；5 个失败均为既有日报流水线基线 |

## TDD 证据

- 模块技能路由测试先因 `route_module_research_skill` 不存在而失败，再实现 4 个新增技能和模块白名单。
- 通用 payload 测试先因旧解析器要求股票代码而失败，再实现 `module + context` 和旧 stock payload 兼容。
- 共享研究坞测试先因模块不存在而失败，再抽出统一 renderer。
- 四页位置测试先证明只有个股页有研究坞，再接入大盘、持仓和机会。
- 浏览器 payload 和 CSS 测试先证明缺少模块上下文与选择器样式，再泛化脚本和响应式布局。
- 页面检查发现机会下拉选项过多后，测试先复现 28 个选项，再限制为 5 个板块、8 只候选和 1 个占位项。
- 空持仓/空候选测试先证明控件仍可点击，再改为禁用并提示下一步。

## 真实技能验证

2026-07-14 使用服务器配置执行官方 OpenAPI 调用：

| 技能 | 结果 | 返回 |
|---|---|---:|
| `hithink-zhishu-query` | 成功 | 3 条 |
| `hithink-macro-query` | 成功 | 1 条 |
| `hithink-sector-selector` | 成功 | 1 条 |
| `hithink-astock-selector` | 成功 | 10 条 |

四次调用均为 `secret_leak=false`。

## 页面检查

- 1280px：四个 workspace 各有且只有一个研究坞；大盘宽 956px，持仓和机会宽 994px；无横向溢出。
- 390px：页面宽 390px、研究坞宽 340px、控件宽 310px、表单单列；无横向溢出。
- 机会选择器最终为 14 项：占位 1、板块最多 5、候选最多 8。
- 浏览器控制台无 error、warn 或 warning。
- 大盘位于五步风险轨道后；持仓位于处置队列后；个股维持关键证据后；机会位于证据漏斗后。

## 已知基线失败

以下 `tests/test_daily_pipeline.py` 用例与本需求开始前一致，本轮未修改其实现或测试：

- `test_daily_pipeline_runs_refresh_enrich_announcements_and_report`
- `test_daily_pipeline_continues_when_external_enrichment_times_out`
- `test_daily_pipeline_continues_when_a_share_kline_hits_rate_limit`
- `test_daily_pipeline_enriches_holdings_with_news_before_broad_candidate_chunks`
- `test_daily_pipeline_writes_data_chain_artifact_and_degrades_on_skipped_steps`

## 生产部署验证

- 运行代码提交：`ca286f55ef3772a58b7a045d8203f22c9165c910`。
- 回滚包：`/opt/stock-ts/.deploy_backups/iwencai-four-workspaces-20260714-164557/source-before.tar.gz`。
- 服务器编译检查通过，`stock-ts.service` 重启后为 `active`，本机 `/healthz` 返回 `ok`。

生产登录态四模块调用：

| 模块 | HTTP | 状态 | 技能 | 事实数 | Key 回显 |
|---|---:|---|---|---:|---|
| market | 200 | complete | `hithink-zhishu-query` | 3 | false |
| portfolio | 200 | complete | `announcement-search` | 5 | false |
| stock | 200 | complete | `hithink-finance-query` | 1 | false |
| opportunity | 200 | complete | `hithink-astock-selector` | 5 | false |

公网验证：

- `https://stock.jiewat-kaka-fj.com/healthz` 返回 HTTP 200 和 `ok`。
- 根路径返回 HTTP 303，并跳转 `/login?next=%2F`。
- 匿名研究请求返回 HTTP 401、`login_required`。
- 公网登录态 market 请求返回 HTTP 200、`complete`、3 条事实，技能为 `hithink-zhishu-query`，Key 回显为 false。

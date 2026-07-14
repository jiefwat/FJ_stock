# Test Record

## 已完成

| 验证 | 结果 | 覆盖 |
|---|---|---|
| `python3 -m pytest tests/test_iwencai.py tests/test_web_iwencai_research.py tests/test_web_stock_research_workspace.py tests/test_web_auth.py -q` | `69 passed` | 技能路由、双 endpoint、浮点成功状态、全路径脱敏、鉴权、限流、UI |
| `make lint` | 通过 | 全仓 Python 与测试静态检查 |
| `make test` | `613 passed, 5 failed, 10 warnings` | 全仓；5 个失败均为既有日报流水线基线 |
| 1280px 浏览器 | 通过 | 调度台位于证据之后、风险之前；未配置状态与布局正确 |
| 390px 浏览器 | 通过 | 宽度 340px、文档宽度 390px，无横向溢出；输入与按钮单列 |
| 无 Key 交互 | 通过 | 显示服务器配置提示，同时明确本地分析仍可用 |
| 服务器源码与进程 | 通过 | `/opt/stock-ts` 位于 `main`，部署提交 `98787b57d43d125626331b60d7d63491432eef96`；tracked worktree 干净，主服务、Signal Desk 和 Nginx 均为 `active` |
| 服务器本机健康检查 | 通过 | `http://127.0.0.1:8501/healthz` 返回 `ok` |
| 公网健康检查 | 通过 | `https://stock.jiewat-kaka-fj.com/healthz` 返回 HTTP 200 和 `ok` |
| 公网登录保护 | 通过 | 根路径返回 HTTP 303，并跳转 `/login?next=%2F` |
| 公网匿名研究请求 | 通过 | `POST /api/iwencai/research` 返回 HTTP 401、`login_required`，响应中无 Key |
| 回滚包 | 通过 | `/opt/stock-ts/.deploy_backups/iwencai-20260714-153500-a6a1f05/source-a6a1f05.tar.gz` 存在 |
| 真实问财网关 | 通过 | 财务质量请求路由到 `hithink-finance-query`，返回 `complete`、1 条结构化事实和 trace 尾号，响应中无 Key |
| 生产登录态端到端 | 通过 | 本机生产服务登录返回 HTTP 303，携带会话请求 `/api/iwencai/research` 返回 HTTP 200、`complete` 和 1 条事实 |
| 网关兼容修复部署 | 通过 | 运行提交 `c72f70d176f8a489e220878356ae1540a5ae9d48`；回滚包位于 `/opt/stock-ts/.deploy_backups/iwencai-status-fix-20260714-155431/source-before.tar.gz` |

## 真实联调发现与修复

- 问财 `query2data` 的成功响应使用浮点数 `status_code=0.0`；原客户端只接受字符串 `0` / `200`，会误判为业务错误。
- 已用失败测试复现，再统一按数值语义兼容 `0` / `200` 的整数、浮点数和字符串形式；专项测试由 68 增至 69 个。
- 服务器 `.env` 权限为 `600`，systemd 通过只包含文件路径的 drop-in 注入环境；主进程确认存在变量，但验证过程不输出变量值。

## 部署边界

- 功能代码、鉴权、安全降级、页面和真实问财调用均已部署到公网。
- 问财调用失败时，StockTs 本地个股分析、数据闸门和其他页面仍不受影响。
- 本轮没有提交、上传或输出任何真实 Key，也没有向问财发送持仓、成本、Cookie 或账号信息。

## 已知基线失败

以下 `tests/test_daily_pipeline.py` 用例与上一版基线一致，本轮未修改其实现或测试：

- `test_daily_pipeline_runs_refresh_enrich_announcements_and_report`
- `test_daily_pipeline_continues_when_external_enrichment_times_out`
- `test_daily_pipeline_continues_when_a_share_kline_hits_rate_limit`
- `test_daily_pipeline_enriches_holdings_with_news_before_broad_candidate_chunks`
- `test_daily_pipeline_writes_data_chain_artifact_and_degrades_on_skipped_steps`

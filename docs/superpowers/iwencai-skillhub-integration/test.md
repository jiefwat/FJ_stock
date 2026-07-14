# Test Record

## 已完成

| 验证 | 结果 | 覆盖 |
|---|---|---|
| `python3 -m pytest tests/test_iwencai.py tests/test_web_iwencai_research.py tests/test_web_stock_research_workspace.py tests/test_web_auth.py -q` | `68 passed` | 技能路由、双 endpoint、全路径脱敏、鉴权、限流、UI |
| `make lint` | 通过 | 全仓 Python 与测试静态检查 |
| `make test` | `612 passed, 5 failed, 11 warnings` | 全仓；5 个失败均为既有日报流水线基线 |
| 1280px 浏览器 | 通过 | 调度台位于证据之后、风险之前；未配置状态与布局正确 |
| 390px 浏览器 | 通过 | 宽度 340px、文档宽度 390px，无横向溢出；输入与按钮单列 |
| 无 Key 交互 | 通过 | 显示服务器配置提示，同时明确本地分析仍可用 |

## 待完成

- 服务器环境、服务状态和公网真实页面。
- 若服务器存在 `IWENCAI_API_KEY`，执行一次不回显密钥的真实问财查询。

## 已知基线失败

以下 `tests/test_daily_pipeline.py` 用例与上一版基线一致，本轮未修改其实现或测试：

- `test_daily_pipeline_runs_refresh_enrich_announcements_and_report`
- `test_daily_pipeline_continues_when_external_enrichment_times_out`
- `test_daily_pipeline_continues_when_a_share_kline_hits_rate_limit`
- `test_daily_pipeline_enriches_holdings_with_news_before_broad_candidate_chunks`
- `test_daily_pipeline_writes_data_chain_artifact_and_degrades_on_skipped_steps`

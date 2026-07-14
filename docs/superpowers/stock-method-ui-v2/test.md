# Test Evidence

## 自动验证

| 命令 | 结果 | 覆盖 |
| --- | --- | --- |
| `/Users/fangjie/Documents/StockTs/.venv/bin/ruff check src tests` | 通过 | Python 与测试静态检查 |
| `PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest tests/test_stock_dossier.py tests/test_web_stock_dossier.py -q` | `33 passed` | 研究模型、stale 闸门、HTML 与响应式契约 |
| `PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest tests/test_web_*.py tests/test_trade_plan.py tests/test_professional_research.py -q` | `223 passed` | 全部 Web、交易计划与专业研究回归 |
| `PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q` | `571 passed, 5 failed, 10 warnings` | 全仓；5 个失败均为既有 `tests/test_daily_pipeline.py` 基线失败 |

全量失败仍是以下既有 case，均未涉及本轮文件：

- `test_daily_pipeline_runs_refresh_enrich_announcements_and_report`
- `test_daily_pipeline_continues_when_external_enrichment_times_out`
- `test_daily_pipeline_continues_when_a_share_kline_hits_rate_limit`
- `test_daily_pipeline_enriches_holdings_with_news_before_broad_candidate_chunks`
- `test_daily_pipeline_writes_data_chain_artifact_and_degrades_on_skipped_steps`

## 浏览器验证

- 本地地址：`http://127.0.0.1:8517/?code=603278&provider=tdx-snapshot#stock`
- 1280px：无横向溢出；投资判断、决策/执行、论点链、证据、风险和情景顺序正确。
- 390px：无横向溢出；证据账本默认关闭；投资判断顶部从约 `710px` 提前到 `486px`。
- 真实 `603278` stale 数据：页面暂停行动、置信度为 0、仓位/风险预算为 0，旧价格不进入情景与可见资金价格结论。

## 未覆盖

- 未使用生产服务器浏览器验证本分支，因为本轮尚未合并或部署。
- 未验证真实 fresh 行情下的手机截图；规则与 sample/Web 契约已覆盖 fresh 分支。

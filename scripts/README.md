# scripts

放置可重复执行的本地脚本、迁移脚本或运维辅助脚本。脚本应优先支持 dry-run 或明确说明副作用。

## 自动日报

完整盘后流水线入口：

```bash
PYTHONPATH=src python3 scripts/run_daily_pipeline.py \
  --snapshot data/imports/tdx_snapshots.json \
  --holdings data/portfolio/holdings.csv \
  --provider tdx-snapshot \
  --candidate-limit 300 \
  --enrich-limit 50 \
  --announcement-limit 5 \
  --output-dir reports/daily \
  --html-dir reports/html \
  --announcement-dir reports/announcements
```

它会依次执行：

- TDX 全市场快照刷新。
- TDX 候选前排 K 线/主题补强。
- Tushare A 股日线强制刷新：把持仓和全市场候选池的 A 股 K 线写回快照，港股等非 A 股会跳过并记录原因；遇到 Tushare 频率限制会限速重试，已有股票更新成功时记录为 `partial` 可用状态，不把整条流水线判死。
- 多源外部补强：估值、资金流、个股新闻和市场新闻；默认每只股票取 3 条新闻、市场取 20 条新闻。该步骤失败不覆盖 Tushare 日线。可通过 `STOCK_TS_INTELLIGENCE_URLS` 或 `--intelligence-url` 追加 NewsNow/RSS-bridge JSON 情报源，单源失败只写入状态不阻断日报。
- 持仓/候选公告事件摘要。
- 每日 Markdown/HTML 报告生成。

单独导入 MCP 新闻/事件：

```bash
PYTHONPATH=src python3 scripts/import_mcp_market_intelligence.py \
  --snapshot data/imports/tdx_snapshots.json \
  --source longbridge.mcp \
  /tmp/longbridge_news.json /tmp/longbridge_events.json
```

该脚本接收 Longbridge MCP 的 `_news`、`_top_movers`、`_market_temperature`、`_finance_calendar` JSON 输出，也兼容通用新闻 JSON；导入后写入 `market_news` 和 `mcp_market_news_refresh`，Web 数据中台会展示采集渠道、更新时间和缺口预警。MCP 是会话工具，项目运行时只读取落地后的快照，不在打开页面时调用 MCP。

单独刷新 A 股日线：

```bash
PYTHONPATH=src python3 scripts/refresh_a_share_kline.py \
  --snapshot data/imports/tdx_snapshots.json \
  --holdings data/portfolio/holdings.csv \
  --candidate-limit 300 \
  --bar-count 120 \
  --sleep 1.3 \
  --retry-rate-limit 1
```

该脚本只调用 Tushare `daily` 日线接口，不抓新闻、资金或估值，避免慢接口影响 K 线准确性。返回摘要中的 `status=partial` 表示部分股票被限频或失败，但已更新的 K 线仍可被日报和页面使用。

单独生成日报入口：

```bash
PYTHONPATH=src python3 scripts/run_daily_analysis.py \
  --provider tdx-snapshot \
  --holdings data/portfolio/holdings.csv \
  --candidate-limit 20 \
  --output-dir reports/daily \
  --html-dir reports/html
```

输出：

- `reports/daily/latest.md`
- `reports/daily/YYYY-MM-DD.md`
- `reports/daily/latest_decisions.json`
- `reports/daily/YYYY-MM-DD_decisions.json`
- `reports/daily/latest.status`
- `reports/daily/pipeline.status`
- `reports/daily/data_chain_status.json`
- `reports/html/latest.html`
- `reports/html/YYYY-MM-DD.html`
- `reports/announcements/latest.md`

流水线会在报告生成后校验“采集 -> 校验 -> 大盘/持仓/个股/机会消费”的全链路：

- `pipeline.status` 的 `status=ok` 表示关键链路可用。
- `status=degraded` 表示报告已生成但存在跳过、部分失败或上下文缺口，Web 数据中台必须预警。
- `status=failed` 表示存在阻断节点，例如关键行情/K 线缺失或刷新/报告步骤失败。
- `data_chain_status.json` 保存每个模块的结构化状态，供 Web 底部“专业数据中台”展示。

失败时返回非 0，并把错误写入 `reports/daily/latest.status` 或 `pipeline.status`，Web 会读取这个状态提示。

## 服务器刷新时间

`stock-ts-daily-analysis.timer` 使用交易研究检查点刷新数据：

- 00:00：盘后/夜间归档，补齐前一交易日 K 线、资金、公告和新闻。
- 06:00：早间预刷新，供盘前查看数据中台状态。
- 09:00：开盘前刷新候选池、市场新闻和持仓数据。
- 12:30：午间复核，更新上午盘面后的候选和异动。
- 14:00：尾盘前复核，供收盘前人工决策。

模板位于 `deploy/systemd/stock-ts-daily-analysis.service` 和 `deploy/systemd/stock-ts-daily-analysis.timer`，上线后需复制到 `/etc/systemd/system/`，再执行 `systemctl daemon-reload && systemctl restart stock-ts-daily-analysis.timer`。
注意：`--python` 指项目运行环境；TDX 桥接会自动选择能 `import eltdx` 的 Python（优先项目环境，再尝试 `python3.11` / `python3.12` / `python3`），必要时可用 `--tdx-bridge-python` 显式指定。
## 早间邮件

每天早上发送昨晚生成好的最新日报，不重新拉行情。邮件会优先读取 `reports/daily/latest_decisions.json`，输出红黄绿交易清单、今日交易限制、自动任务提醒和压缩版机会；JSON 缺失时再降级解析 Markdown。如果最新日报包含个股“决策摘要”，持仓建议会直接使用最终判断、核心矛盾、今日动作、禁忌、转强和离场条件，不再只提示去网页查看；当新闻、资金或 K 线补强不完整时，会在邮件里标注对应判断不可信。

```bash
PYTHONPATH=src python3 scripts/send_morning_report.py \
  --daily-dir reports/daily \
  --html-dir reports/html \
  --announcement-dir reports/announcements \
  --channels email \
  --style digest
```

依赖 `.env` 中的 `EMAIL_SENDER`、`EMAIL_PASSWORD` 和 `EMAIL_RECEIVERS`。缺少邮箱授权码时只能 dry-run，不能真实发送。

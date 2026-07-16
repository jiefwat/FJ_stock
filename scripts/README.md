# scripts

放置可重复执行的本地脚本、迁移脚本或运维辅助脚本。脚本应优先支持 dry-run 或明确说明副作用。

## 自动日报

完整盘后流水线入口：

```bash
PYTHONPATH=src python3 scripts/run_daily_pipeline.py \
  --snapshot data/imports/tdx_snapshots.json \
  --holdings data/portfolio/holdings.csv \
  --provider tdx-snapshot \
  --candidate-limit 500 \
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
  --candidate-limit 500 \
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

`stock-ts-daily-analysis.timer` 使用固定刷新点：

- 07:00：晨间刷新，补齐上一完整交易日 K 线、资金、公告和新闻。
- 09:00：开盘前刷新候选池、市场新闻和持仓数据。
- 13:00：午间后复核，更新上午盘面后的候选和异动。
- 15:00：收盘阶段刷新，更新指数、市场宽度、主题和候选风险。

盘中行情日期可以是当天，但 Tushare 日线在 15:30 前只要求到上一完整交易日，
避免把正常的上一收盘 K 线误判为过期。页面始终使用最后一次完整研究快照；研究
快照若早于最新成功的 `pipeline.status`，会立即回退到最新本地事实，不展示半成品。
法定休市日优先使用 Tushare 交易日历，不只按周末推算。主流水线为正式快照加
跨进程互斥锁，并在 run-specific staging 中完成刷新、补强、报告和数据链验收；
成功后才发布正式快照、日报与 HTML，失败任务保留上一套完整产物。发布版本写入
`snapshot_version`，研究快照和页面必须与该版本一致。A 股日线子任务的超时会随
候选数量扩展，500 只候选按最多 2000 秒执行，避免正常节流刷新在 20 分钟被误杀。

模板位于 `deploy/systemd/stock-ts-daily-analysis.service` 和 `deploy/systemd/stock-ts-daily-analysis.timer`，上线后需复制到 `/etc/systemd/system/`，再执行 `systemctl daemon-reload && systemctl restart stock-ts-daily-analysis.timer`。公网开放账号注册时，把 `deploy/systemd/stock-ts-auth-open.conf` 放到 `/etc/systemd/system/stock-ts.service.d/auth.conf`，真实管理员密码和 session secret 仍只放服务器环境或 `.env`。

### 每日研究快照

大盘趋势和每日机会使用独立轻量任务，消费最近一次已完成的全量行情流水线：

```bash
PYTHONPATH=src python scripts/run_daily_research.py --output-dir reports/research --refresh
```

任务写入 `reports/research/market/`、`reports/research/opportunity/` 和
`reports/research/daily.status.json`。systemd 模板为
`deploy/systemd/stock-ts-daily-research.service` 与
`deploy/systemd/stock-ts-daily-research.timer`，每天 07:30、09:30、13:30、15:30
运行。研究任务先用本地行情建立事实底座，再融合外部研究证据；外部证据不完整时
不能覆盖本地大盘事实。主流水线发布成功后会立即运行一次研究任务，独立 timer 只作
恢复补跑；如果运行期间正式快照版本变化，旧研究任务不得覆盖新版本。
注意：`--python` 指项目运行环境；TDX 桥接会自动选择能 `import eltdx` 的 Python（优先项目环境，再尝试 `python3.11` / `python3.12` / `python3`），必要时可用 `--tdx-bridge-python` 显式指定。
## 早间邮件

每天早上发送昨晚生成好的最新日报，不重新拉行情。邮件会优先读取 `reports/daily/latest_decisions.json`，输出红黄绿交易清单、今日交易限制、自动任务提醒和压缩版机会；JSON 缺失时再降级解析 Markdown。如果最新日报包含个股“决策摘要”，持仓建议会直接使用最终判断、核心矛盾、今日动作、禁忌、转强和离场条件，不再只提示去网页查看；当新闻、资金或 K 线补强不完整时，会在邮件里标注对应判断不可信。

```bash
PYTHONPATH=src python3 scripts/send_morning_report.py \
  --daily-dir reports/daily \
  --html-dir reports/html \
  --announcement-dir reports/announcements \
  --holdings-path data/auth/users/1/holdings.csv \
  --channels email \
  --email-receivers user@example.com \
  --style digest
```

依赖 `.env` 中的 `EMAIL_SENDER` 和 `EMAIL_PASSWORD`。单账号发送可用 `--email-receivers` 覆盖接收人；账号管理页会把每个用户的接收邮箱、启用状态和发送时间保存到 `data/auth/users/<user_id>/morning_email.json`。定时模板位于 `deploy/systemd/stock-ts-morning-email.service` 和 `deploy/systemd/stock-ts-morning-email.timer`，默认每 15 分钟检查一次，到达用户配置时间后当天只发送一次。

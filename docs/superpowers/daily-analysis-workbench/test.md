# Daily Analysis Workbench Test Evidence

## 验证时间

- 2026-06-12
- 验证目录：`/tmp/stockts-verify-20260612233042`

## 已运行命令

```bash
make lint
make test
PYTHONPATH=src python3 -m stock_ts.cli doctor --provider sample
PYTHONPATH=src python3 -m stock_ts.cli market --provider sample --output /tmp/stockts-verify-20260612233042/04-market.md
PYTHONPATH=src python3 -m stock_ts.cli stock 600519 --provider sample --output /tmp/stockts-verify-20260612233042/05-stock.md
PYTHONPATH=src python3 -m stock_ts.cli sectors --provider sample --output /tmp/stockts-verify-20260612233042/06-sectors.md
PYTHONPATH=src python3 -m stock_ts.cli candidates --provider sample --limit 20 --output /tmp/stockts-verify-20260612233042/07-candidates.md
PYTHONPATH=src python3 -m stock_ts.cli portfolio --provider sample --holdings data/portfolio/holdings.csv --output /tmp/stockts-verify-20260612233042/08-portfolio.md
PYTHONPATH=src python3 -m stock_ts.cli daily --provider sample --holdings data/portfolio/holdings.csv --news data/imports/news.csv --candidate-limit 20 --cache-dir /tmp/stockts-verify-20260612233042/cache --refresh --output /tmp/stockts-verify-20260612233042/09-daily.md
PYTHONPATH=src python3 -m stock_ts.cli import-prices data/imports/sample_prices.csv --code 688001 --name 示例科技 --output /tmp/stockts-verify-20260612233042/12-import-prices.md
PYTHONPATH=src python3 -m stock_ts.cli news data/imports/news.csv --output /tmp/stockts-verify-20260612233042/13-news.md
PYTHONPATH=src python3 -m stock_ts.cli send-daily --provider sample --holdings data/portfolio/holdings.csv --news data/imports/news.csv --channels email,wechat --dry-run --output /tmp/stockts-verify-20260612233042/14-send-report.md
```

## 结果

- `make lint`：通过。
- `make test`：37 个测试全部通过。
- `doctor`：sample 主流程 OK；AKShare/Tushare 依赖已安装；邮件和企业微信渠道未配置。
- sample 大盘、个股、板块、候选池、持仓、完整日报：均能生成 Markdown 报告。
- 日报缓存：刷新后生成 `/tmp/stockts-verify-20260612233042/cache/reports/daily-sample-2026-06-05.json`；再次构建命中缓存。
- 本地行情导入：`sample_prices.csv` 能生成 `示例科技（688001）` 个股分析。
- 新闻舆情导入：`news.csv` 能生成舆情摘要，并能嵌入完整日报。
- `send-daily --dry-run`：邮件和企业微信均返回 OK dry-run，不产生真实外发。
- 缺少持仓文件：CLI 按预期失败并输出 `Holdings file not found`。
- Web 页面：本地 HTTP 返回包含今日总览、大盘、板块、持仓、候选池、个股、完整日报、系统状态；错误页能展示排查建议。
- Dashboard：`import stock_ts.dashboard` 通过。

## 外部能力验证

- `akshare stock 600519`：真实数据源个股分析通过，生成 `/tmp/stockts-verify-20260612233042/19-akshare-stock.md`。
- `akshare market`：失败，外部接口 `stock_zh_a_spot_em` 连接被远端关闭，错误为 `RemoteDisconnected`。
- `akshare sectors` / `akshare candidates`：失败，当前先依赖 `fetch_market()`，因此同样被 AKShare spot 接口连接问题阻断；此外 AKShare provider 还没有真实板块和候选池实现。

## 残余风险

- 邮件和企业微信只验证了 dry-run、缺配置失败路径和消息分发逻辑；没有真实发送，因为当前 `.env` 未配置真实渠道密钥。
- Browser 插件访问 `localhost:8501` / `127.0.0.1:8501` 被客户端拦截为 `ERR_BLOCKED_BY_CLIENT`，已用 `curl` 对实际 HTTP 页面与错误页完成验证。
- AKShare 个股真实数据可用；大盘、板块、候选池还需要对外部接口失败做降级或换源。
- Tushare 依赖已安装且 token 状态为 configured，但项目当前还没有 Tushare provider。

## 2026-06-12 P0 优化补测

新增覆盖：

```bash
pytest tests/test_transactions_akshare_provider.py -q
PYTHONPATH=src python3 -m stock_ts.cli portfolio --provider sample --transactions data/portfolio/transactions.csv
PYTHONPATH=src python3 -m stock_ts.cli daily --provider sample --transactions data/portfolio/transactions.csv --news data/imports/news.csv
PYTHONPATH=src python3 -m stock_ts.cli market --provider akshare
```

验证点：

- 交易流水 CSV 可以按移动加权成本生成当前持仓。
- `portfolio`、`daily`、`send-daily` 支持 `--transactions`，与原 `--holdings` 快照输入并存。
- AKShare 全市场 spot 接口失败时，`fetch_market()` 降级为指数可用，不再直接抛出连接异常。

仍未覆盖：

- 手续费、印花税暂未纳入持仓成本。
- 交易流水暂不计算已实现盈亏、现金余额、分红和组合净值曲线。
- AKShare 真实板块和候选池仍未实现，需要下一阶段补真实 `fetch_sectors()` 与 `fetch_candidate_universe()`。

## 2026-06-12 AKShare 能力增强补测

新增覆盖：

```bash
pytest tests/test_akshare_news_enhancements.py -q
PYTHONPATH=src python3 -m stock_ts.cli sectors --provider akshare
PYTHONPATH=src python3 -m stock_ts.cli candidates --provider akshare --limit 20
PYTHONPATH=src python3 -m stock_ts.cli fetch-news 600519 --provider akshare
```

验证点：

- AKShare 行业板块接口可转换为 `SectorRawData`。
- AKShare 候选池优先使用全市场 spot；spot 失败时回退到行业板块成份。
- AKShare 东方财富个股新闻可转换为 `NewsItem` 并渲染新闻舆情摘要。

仍未覆盖：

- 新闻抓取当前为 AKShare 个股新闻，不包含通用 RSS、公告全文解析和搜索引擎抓取。
- 候选池使用 spot 或板块成份的当日截面构造轻量 K 线，后续应接入真实历史 K 线缓存以提高评分质量。

## 2026-06-13 深度分析与 HTML 结论页补测

新增覆盖：

```bash
PYTHONPATH=src pytest tests/test_deep_analysis.py tests/test_deep_cli_html.py -q
make lint
make test
PYTHONPATH=src python3 -m stock_ts.cli stock-deep 600519 --provider sample --output /tmp/stockts-deep-verify-20260613000901/stock-deep-600519.md --html /tmp/stockts-deep-verify-20260613000901/html/stock-deep-600519.html
PYTHONPATH=src python3 -m stock_ts.cli batch 600519,000001,300750 --provider sample --output /tmp/stockts-deep-verify-20260613000901/batch.md --html /tmp/stockts-deep-verify-20260613000901/html/batch.html
PYTHONPATH=src python3 -m stock_ts.cli daily-deep --provider sample --transactions data/portfolio/transactions.csv --news data/imports/news.csv --candidate-limit 5 --output /tmp/stockts-deep-verify-20260613000901/daily-deep.md --html /tmp/stockts-deep-verify-20260613000901/html/daily-deep.html
PYTHONPATH=src python3 -m stock_ts.cli stock-deep 600519 --provider akshare --output /tmp/stockts-deep-akshare-20260613001021/stock-deep-akshare.md --html /tmp/stockts-deep-akshare-20260613001021/html/stock-deep-akshare.html
```

验证点：

- `stock-deep` 输出单股多角度深度分析，包含未来上涨潜力观察分、多头观点、空头观点、裁判结论、风险与失效条件。
- `batch` 支持多个股票统一深度分析和观察优先级排序，保持“只作为观察优先级，不代表确定上涨、买入建议或收益承诺”的安全措辞。
- `daily-deep` 汇总每日大盘情况、板块情况、持仓分析、新闻舆情、候选池和多轮对抗摘要。
- HTML 输出均为单文件，包含结构化卡片和 `debate-card`，不依赖外部 CDN 或 `<script src>`。
- AKShare 个股历史接口断连时，`fetch_stock()` 已降级到 sample 个股数据，`stock-deep --provider akshare` 不再崩溃。

仍未覆盖：

- 当前多轮对抗为确定性规则引擎，尚未接入外部 LLM；后续接 AI 时需要固定 Prompt、结构化输出契约和回放测试。
- 行业映射仍是轻量推断，真实投研需要接入稳定行业分类和历史行业强弱缓存。

## 2026-06-13 GitHub 优秀项目能力参考补测

参考方向：

- OpenBB / BatesStocks 类项目的 watchlist、研究工作台、标签和提醒流。
- Qlib / Zipline 类项目的研究验证、回测指标、买入持有对照和风险度量。
- TradingAgents 类项目的多角色结论已经在上一阶段落为确定性多轮对抗。

新增覆盖：

```bash
PYTHONPATH=src pytest tests/test_watchlist_backtest.py -q
PYTHONPATH=src python3 -m stock_ts.cli watchlist data/watchlists/sample.yaml --provider sample --output /tmp/stockts-rich-verify-20260613001910/watchlist.md
PYTHONPATH=src python3 -m stock_ts.cli backtest data/imports/sample_prices.csv --code 688001 --name 示例科技 --fast 2 --slow 4 --output /tmp/stockts-rich-verify-20260613001910/backtest.md
```

验证点：

- `watchlist` 能读取轻量 YAML-like 自选股清单，保留标签、研究假设、价格/评分提醒，并复用深度分析输出批量深度排序。
- `backtest` 能对本地行情 CSV 做 MA 均线轻量回测，输出策略收益、买入持有收益、最大回撤、交易次数、胜率、持仓暴露和交易明细。
- 两个新增能力均保持离线 sample/CSV 可用，不依赖真实行情接口。
- 所有输出保留“不构成投资建议”免责声明。

仍未覆盖：

- 回测当前不含手续费、滑点、停牌、涨跌停无法成交、真实成交时点和组合级资金曲线。
- 自选股提醒当前只在报告中展示，尚未接入邮件/企业微信外发。

## 2026-06-13 可选大模型增强补测

新增覆盖：

```bash
PYTHONPATH=src pytest tests/test_llm_insight.py -q
PYTHONPATH=src python3 -m stock_ts.cli ai-insight 600519 --provider sample
```

验证点：

- 默认不需要大模型 Key；无 `STOCK_TS_LLM_API_KEY` / `DASHSCOPE_API_KEY` 时，`ai-insight` 输出“AI 增强未启用”并保留规则结论。
- 配置层支持 `STOCK_TS_LLM_PROVIDER`、`STOCK_TS_LLM_BASE_URL`、`STOCK_TS_LLM_MODEL`、`STOCK_TS_LLM_API_KEY`、`DASHSCOPE_API_KEY`。
- `safe_summary()` 和 doctor 只显示 configured/missing，不输出真实 Key。
- LLM 输出保留“不构成投资建议”，并要求基于结构化数据、风险和失效条件生成。

安全说明：

- 不把真实 Key 写入仓库、README、测试、报告或命令参数。
- 如果 Key 曾经出现在聊天或日志中，建议在平台作废并重新生成，只放入本机 `.env`。

## 2026-06-13 深度分析模块边界重构补测

重构目标：

- 将 `deep_analysis.py` 中的数据结构、规则分析和 Markdown 渲染拆开，避免单文件继续膨胀。
- 保留旧公共导入路径，避免已有调用方从 `stock_ts.deep_analysis` 导入渲染函数时破坏兼容性。
- 抽出 `output.py` 统一 CLI 写文件逻辑。
- 深度报告渲染对空 `debate_rounds` 做防御性兜底。

新增/调整模块：

- `src/stock_ts/deep_models.py`：深度分析领域模型。
- `src/stock_ts/deep_report.py`：深度分析 Markdown 渲染。
- `src/stock_ts/output.py`：文本输出工具。
- `src/stock_ts/deep_analysis.py`：保留规则分析，并 re-export 旧渲染函数。

验证命令：

```bash
PYTHONPATH=src pytest tests/test_refactor_contracts.py -q
make lint
make test
```

验证点：

- 旧路径 `from stock_ts.deep_analysis import render_deep_stock_markdown` 仍然可用。
- 新路径 `from stock_ts.deep_report import render_deep_stock_markdown` 与旧路径输出一致。
- CLI 输出工具能自动创建父目录并写入 UTF-8 文本。
- 空 `debate_rounds` 不再导致每日深度报告渲染崩溃。

## 2026-06-13 全量功能验收与启动前补测

验收目录：`/tmp/stockts-full-verify-20260613214944`

本轮目标：

- 按当前 CLI 能力清单逐项执行一次，确认核心命令都能正常返回。
- 补做 Web 页面与持仓交互链路冒烟，确认启动后首页、`provider=auto` 页面和 `/holdings` 写入流程可用。
- 在最终启动前重新执行 `make lint` 与 `make test`，确保没有带着未验证修改交付。

已运行命令：

```bash
make lint
make test
PYTHONPATH=src python3 -m stock_ts.cli doctor --provider sample
PYTHONPATH=src python3 -m stock_ts.cli market --provider sample --output /tmp/stockts-full-verify-20260613214944/market-sample.md
PYTHONPATH=src python3 -m stock_ts.cli stock 600519 --provider sample --output /tmp/stockts-full-verify-20260613214944/stock-sample.md
PYTHONPATH=src python3 -m stock_ts.cli stock 600519 --provider auto --output /tmp/stockts-full-verify-20260613214944/stock-auto.md
PYTHONPATH=src python3 -m stock_ts.cli stock-deep 600519 --provider sample --output /tmp/stockts-full-verify-20260613214944/stock-deep.md --html /tmp/stockts-full-verify-20260613214944/html/stock-deep.html
PYTHONPATH=src python3 -m stock_ts.cli research 600519 --provider sample --output /tmp/stockts-full-verify-20260613214944/research.md
PYTHONPATH=src python3 -m stock_ts.cli ai-insight 600519 --provider sample --output /tmp/stockts-full-verify-20260613214944/ai-insight.md
PYTHONPATH=src python3 -m stock_ts.cli batch 600519,000001,300750 --provider sample --output /tmp/stockts-full-verify-20260613214944/batch.md --html /tmp/stockts-full-verify-20260613214944/html/batch.html
PYTHONPATH=src python3 -m stock_ts.cli sectors --provider sample --output /tmp/stockts-full-verify-20260613214944/sectors.md
PYTHONPATH=src python3 -m stock_ts.cli candidates --provider sample --limit 20 --output /tmp/stockts-full-verify-20260613214944/candidates.md
PYTHONPATH=src python3 -m stock_ts.cli portfolio --provider sample --holdings data/portfolio/holdings.csv --output /tmp/stockts-full-verify-20260613214944/portfolio-sample.md
PYTHONPATH=src python3 -m stock_ts.cli daily --provider sample --holdings data/portfolio/holdings.csv --news data/imports/news.csv --candidate-limit 20 --cache-dir /tmp/stockts-full-verify-20260613214944/cache --refresh --output /tmp/stockts-full-verify-20260613214944/daily-sample.md
PYTHONPATH=src python3 -m stock_ts.cli daily-deep --provider sample --transactions data/portfolio/transactions.csv --news data/imports/news.csv --candidate-limit 5 --output /tmp/stockts-full-verify-20260613214944/daily-deep.md --html /tmp/stockts-full-verify-20260613214944/html/daily-deep.html
PYTHONPATH=src python3 -m stock_ts.cli import-prices data/imports/sample_prices.csv --code 688001 --name 示例科技 --output /tmp/stockts-full-verify-20260613214944/import-prices.md
PYTHONPATH=src python3 -m stock_ts.cli news data/imports/news.csv --output /tmp/stockts-full-verify-20260613214944/news.md
PYTHONPATH=src python3 -m stock_ts.cli watchlist data/watchlists/sample.yaml --provider sample --output /tmp/stockts-full-verify-20260613214944/watchlist.md
PYTHONPATH=src python3 -m stock_ts.cli backtest data/imports/sample_prices.csv --code 688001 --name 示例科技 --fast 2 --slow 4 --output /tmp/stockts-full-verify-20260613214944/backtest.md
PYTHONPATH=src python3 -m stock_ts.cli fetch-news 600519 --provider akshare --limit 5 --output /tmp/stockts-full-verify-20260613214944/fetch-news.md
PYTHONPATH=src python3 -m stock_ts.cli announcements 600519 --limit 5 --output /tmp/stockts-full-verify-20260613214944/announcements.md
PYTHONPATH=src python3 -m stock_ts.cli send-daily --provider sample --holdings data/portfolio/holdings.csv --news data/imports/news.csv --channels email,wechat --dry-run --output /tmp/stockts-full-verify-20260613214944/send-daily.md
make lint
make test
```

Web 冒烟：

```bash
PYTHONPATH=src python3 -m stock_ts.web
curl http://127.0.0.1:8501/
curl 'http://127.0.0.1:8501/?code=600519&provider=auto&holdings=data%2Fportfolio%2Fholdings.csv#module-overview'
POST /holdings upsert (temp csv)
POST /holdings delete (temp csv)
```

结果：

- `make lint` 通过。
- `make test` 通过，当前为 `102 passed`。
- 当前 CLI 帮助里的核心子命令全部实际执行过一轮：`market`、`stock`、`stock-deep`、`research`、`ai-insight`、`batch`、`import-prices`、`news`、`fetch-news`、`announcements`、`sectors`、`candidates`、`doctor`、`portfolio`、`daily`、`daily-deep`、`send-daily`、`watchlist`、`backtest`。
- `stock --provider auto` 可执行；腾讯实时源若握手超时会自动降级到 sample，不阻断命令返回。
- `ai-insight` 在未配置真实 Key 的情况下仍能输出可读结果，保持安全降级。
- `fetch-news` 与 `announcements` 本轮均返回成功并生成 Markdown 文件。
- 首页 `http://127.0.0.1:8501/` 和 `provider=auto` 页面均返回 `200`。
- `/holdings` 的新增、删除链路可用；临时文件 `/tmp/stockts-web-verify-20260613/holdings-upsert-only.csv` 已验证会写入 `601318,中国平安,200,45.6,保险,web smoke`，删除链路也已验证可移除临时持仓。
- `provider=auto` 首次打开仍明显慢于 sample，但在腾讯源短时缓存生效后，重复访问速度明显改善，未出现错误页。

残余风险：

- `provider=auto/tencent` 依赖外部接口质量，首次访问仍可能因 SSL 握手或读超时变慢；当前策略是短时缓存 + sample 降级，优先保证“可用”而非“每次都是真实秒级响应”。
- 邮件和企业微信仍只验证了 `--dry-run` 路径；当前本地未配置真实发送凭证，因此未做真实外发。
- Browser 插件本轮仍不稳定，HTTP 可用性通过本地服务返回与持仓表单写入脚本验证，而不是通过浏览器自动化完成。

## 2026-06-13 Research + Portfolio OS 产品化重构补测

设计与计划文档：

- `docs/superpowers/specs/2026-06-13-research-portfolio-os-design.md`
- `docs/superpowers/plans/2026-06-13-research-portfolio-os.md`

本轮重构重点：

- 新增 `src/stock_ts/webapp/` 装配层，把页面壳、工作区分组、跳转协议和样式从 `web.py` 中拆分出去。
- Web 从“模块逐个切换”升级为“工作区切换”：`今日总控`、`研究中枢`、`组合中枢`、`执行中枢`、`归档与系统`。
- 保留既有分析引擎和模块内容，但把它们重组到真实工作流里。
- 所有关键按钮必须属于明确的工作区跳转或提交动作，不再出现“点完不知道去哪”的弱行为。
- 持仓删除增加确认提示；客户端断开连接时服务端不再抛出未处理异常日志。

新增验证：

```bash
ruff check src tests
pytest tests/test_web_app_shell.py tests/test_web_portfolio_interaction.py tests/test_web_layout.py tests/test_web_user_comfort.py tests/test_workflows_cache_web.py -q
make lint
make test
```

验证点：

- 页面 HTML 中存在新的工作区结构：`workspace-home`、`workspace-research`、`workspace-portfolio`、`workspace-execution`、`workspace-archive`。
- 研究会话工具条默认回到研究工作区。
- 候选、个股、持仓相关按钮使用明确的 hash 路由返回目标工作区。
- 个股、候选、持仓核心测试全部通过，且不破坏既有 100+ 测试资产。
- 全量测试通过后，当前测试总数升级为 `103 passed`。

结果：

- `make lint`：通过。
- `make test`：通过，`103 passed`。
- `tests/test_web_app_shell.py`、`tests/test_web_portfolio_interaction.py`、`tests/test_web_layout.py`、`tests/test_web_user_comfort.py`、`tests/test_workflows_cache_web.py`：通过。
- 产品入口文案与结构已经切换为“研究 + 组合操作系统”语义，而非长 HTML 模块页语义。

残余风险：

- 页面结构虽然已经产品化，但底层 `web.py` 里仍保留部分旧渲染函数，后续还可以继续把工作区渲染器进一步拆到 `webapp/` 子模块里。
- `provider=auto/tencent` 的首次请求耗时仍取决于外部接口质量；当前通过短时缓存和 sample 降级保障稳定可用。

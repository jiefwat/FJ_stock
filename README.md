# StockTS A股分析软件

StockTS 是按 `yqn-dev-skills` Python standard 治理结构初始化的 A 股研究分析项目，目标是提供每日大盘分析、个股分析、自选股复盘和后续 AI/量化扩展的统一工程骨架。

> 免责声明：本项目只做研究、复盘和风险提示，不构成投资建议，不提供自动交易能力。

公开站点品牌名暂定为 **Jiewat Kaka FJ**，推荐域名为 `jiewat-kaka-fj.com`。代码包名和命令仍保持 `stock_ts` / `stock-ts`，方便继续按现有工程约定开发。

## 当前能力

- 每日大盘分析：指数趋势、市场广度、短线情绪、资金流、板块强度、风险状态、明日观察。
- 每日板块情况：板块热度榜、市场主线、持续性、资金活跃、轮动状态、板块风险。
- 明日强势候选观察池：基于趋势、量价、板块、资金和风险扣分排序，按资金抱团、市场热度、超跌反弹、强势突破和风险排查拆分策略入口。
- 每日持仓分析：总市值、浮动盈亏、当日盈亏、组合健康度、行业暴露、集中度、市场主线匹配、操作检查清单。
- 组合整体建议：页面和 `portfolio` 命令会明确告诉你持仓文件在哪里添加，并按第一大持仓、行业暴露、趋势、盈亏和市场热度给出总体动作、目标现金仓位、每只股票目标仓位、调整金额、止损和止盈观察。
- 个股分析：短期趋势、涨跌幅、量能变化、资金流、估值观察、风险等级、跟踪点。
- 深度个股分析：参考 TradingAgents 的多角色思路，增加价格趋势、量能、市场、板块、新闻、风险、持仓影响等多角度评分，以及多头/空头/裁判三轮对抗结论。
- 批量个股分析：支持多个股票统一打分排序，输出观察优先级、失效条件和对比结论。
- 每日深度复盘：把大盘、板块、候选池、持仓、新闻舆情和重点个股对抗摘要汇总成一份可落地日报。
- HTML 结论页：`stock-deep`、`batch`、`daily-deep` 均可输出单文件 HTML，无 CDN 依赖，适合本地打开或后续外发。
- 自选股研究工作台：参考 OpenBB / BatesStocks 类项目的 watchlist 工作流，支持沉淀研究假设、标签、价格/评分提醒，并生成批量深度排序。
- 轻量回测：参考 Qlib / Zipline 的研究验证思想，支持本地行情 CSV 的 MA 均线策略 sanity check，输出收益、买入持有对照、最大回撤、胜率和交易明细。
- 可选 AI 增强研报：默认不需要大模型 Key；配置 OpenAI-compatible / 千问 DashScope Key 后，可用 `ai-insight` 在规则分析基础上追加 AI 研报。
- 本地行情导入：支持 `date,open,high,low,close,volume` CSV 直接生成个股分析。
- 新闻舆情导入：支持本地新闻 CSV，按正面/负面/中性汇总并嵌入每日复盘。
- 公告/财报事件：支持从 CNInfo/巨潮抓取上市公司公告，识别减持、监管、诉讼、担保/质押、亏损、退市/ST、重大事项等标题风险标签。
- 专业单股研究包：新增 `research` 命令与 Web 模块，把多角度深度分析、盘口技术结构、支撑/压力/失效线、量能比、公告事件雷达和复核动作合并成一份可执行研究草稿。
- 明确操作计划：Web 和 `research` 命令输出当前动作、目标仓位、买入/加仓触发、止损/减仓触发、止盈计划、禁止动作和盘中执行清单，避免只给空泛描述。
- 数据源适配：内置 `sample` 保证离线可运行；新增无额外依赖的 `tencent/auto` 行情源用于拉取较新的 A 股个股/指数日线；保留 `akshare` 作为板块、候选池和新闻增强源；新增 `iTick` 可选报价/K线补强；新增 `tdx-snapshot`，支持把 TDX MCP/通达信服务导出的 quote/K 线快照纳入本地分析。
- 数据质量追踪：Web 页面会展示请求源、实际 Provider、个股行情日期、大盘交易日，并对样例数据、疑似降级、行情过期和名称未解析做显著告警。
- 输出形态：CLI 输出 Markdown；轻量 Web 投研工作台；可写入报告文件；可通过邮件/企业微信/飞书发送；预留 Streamlit 本地 Dashboard。
- 专业 Web 工作台：新增专业投研框架、大盘情景推演/风险闸门、板块主线确认矩阵、组合风险预算/持仓处理剧本、候选池评分方法/分层和能力覆盖矩阵，避免只停留在简单汇总。
- UI 研究指挥舱：Web 首页新增 Command Deck，将研究偏向、观察分、市场热度、技术红线、候选首位、证据链时间轴、下一步动作、风险红线和数据可信度集中展示，进入各模块前先形成全局判断。
- 应用式 Web 壳：左侧导航现在是模块切换按钮，不再是长 HTML 锚点报告；顶部提供股票、数据源、持仓文件的应用工具栏和“一键分析”入口。
- 用户工作台：总览页新增“我今天先看什么”和“用户工作流入口”，可直接跳到持仓处理、个股执行计划、候选池和数据质量，不需要在页面里找功能。
- 开源项目优秀点融合：参考 `daily_stock_analysis` 的决策仪表盘/多源数据完整性/操作清单，参考 `TradingAgents` 的分析师-研究员-交易员-风控-组合经理分工，参考 `stock-analysis` 的组合与可视化分析思路；当前已落地为 AI 决策仪表盘、策略透镜矩阵、研究团队分工、数据块完整性、观察点位和交易纪律。
- 工程治理：`AGENTS.md`、`docs/superpowers/`、`docs/architecture/`、`tests/`、`Makefile`。

## 快速开始

```bash
# 运行体检
PYTHONPATH=src python3 -m stock_ts.cli doctor --provider sample

# 离线样例大盘报告
PYTHONPATH=src python3 -m stock_ts.cli market --provider sample

# 离线样例个股报告
PYTHONPATH=src python3 -m stock_ts.cli stock 600519 --provider sample

# 使用腾讯行情源做真实个股深度分析，支持代码或内置中文名映射
PYTHONPATH=src python3 -m stock_ts.cli stock-deep 大业股份 --provider tencent

# 专业单股研究包：深度结论 + 技术结构 + CNInfo 公告事件雷达
PYTHONPATH=src python3 -m stock_ts.cli research 大业股份 --provider auto --announcements 5 --output reports/research-603278.md

# 单个股票深度分析：Markdown + HTML 结论页
PYTHONPATH=src python3 -m stock_ts.cli stock-deep 600519 --provider sample --output reports/stock-deep-600519.md --html reports/html/stock-deep-600519.html

# 可选 AI 增强研报：无 Key 时安全降级；有 Key 时调用配置的大模型
PYTHONPATH=src python3 -m stock_ts.cli ai-insight 600519 --provider sample --output reports/ai-insight-600519.md

# 多个股票批量深度对比
PYTHONPATH=src python3 -m stock_ts.cli batch 600519,000001,300750 --provider sample --output reports/batch-sample.md --html reports/html/batch-sample.html

# 自选股研究工作台：研究假设 + 标签 + 提醒检查 + 深度排序
PYTHONPATH=src python3 -m stock_ts.cli watchlist data/watchlists/sample.yaml --provider sample --output reports/watchlist-sample.md

# 导入本地行情 CSV 并分析
PYTHONPATH=src python3 -m stock_ts.cli import-prices data/imports/sample_prices.csv --code 688001 --name 示例科技

# 对本地行情 CSV 做轻量均线回测
PYTHONPATH=src python3 -m stock_ts.cli backtest data/imports/sample_prices.csv --code 688001 --name 示例科技 --fast 2 --slow 4 --output reports/backtest-688001.md

# 导入新闻/舆情 CSV 并生成摘要
PYTHONPATH=src python3 -m stock_ts.cli news data/imports/news.csv

# 从 AKShare/东方财富抓取个股新闻并生成摘要
PYTHONPATH=src python3 -m stock_ts.cli fetch-news 600519 --provider akshare

# 从 CNInfo/巨潮抓取公告并识别风险事件
PYTHONPATH=src python3 -m stock_ts.cli announcements 603278 --limit 10

# 每日板块情况
PYTHONPATH=src python3 -m stock_ts.cli sectors --provider sample

# 明日强势候选观察池 Top 20
PYTHONPATH=src python3 -m stock_ts.cli candidates --provider sample --limit 20

# 每日持仓分析
PYTHONPATH=src python3 -m stock_ts.cli portfolio --provider sample --holdings data/portfolio/holdings.csv

# 用真实行情源分析当前持仓，并输出具体组合建议
PYTHONPATH=src python3 -m stock_ts.cli portfolio --provider auto --holdings data/portfolio/holdings.csv --output reports/portfolio-current-auto.md

# 用交易流水自动生成当前持仓后分析
PYTHONPATH=src python3 -m stock_ts.cli portfolio --provider sample --transactions data/portfolio/transactions.csv

# 完整每日复盘
PYTHONPATH=src python3 -m stock_ts.cli daily --provider sample --holdings data/portfolio/holdings.csv --candidate-limit 20 --cache-dir data/cache --refresh --output reports/daily/sample-full.md

# 带新闻舆情的完整日报
PYTHONPATH=src python3 -m stock_ts.cli daily --provider sample --holdings data/portfolio/holdings.csv --news data/imports/news.csv

# 用交易流水 + 新闻舆情生成完整日报
PYTHONPATH=src python3 -m stock_ts.cli daily --provider sample --transactions data/portfolio/transactions.csv --news data/imports/news.csv

# 每日深度复盘：大盘 + 板块 + 持仓 + 舆情 + 多轮对抗摘要 + HTML
PYTHONPATH=src python3 -m stock_ts.cli daily-deep --provider sample --transactions data/portfolio/transactions.csv --news data/imports/news.csv --candidate-limit 20 --output reports/daily-deep-sample.md --html reports/html/daily-deep-sample.html

# 刷新 TDX 全市场智能选股快照：扫描全市场行情，预筛 300 只候选写入 tdx_snapshots.json
PYTHONPATH=src python3 scripts/refresh_tdx_snapshot.py --output data/imports/tdx_snapshots.json --candidate-limit 300 --quote-only --timeout 60

# 对已有候选快照做前排深度补强：补真实日线与主题，不重新扫描全市场
PYTHONPATH=src python3 scripts/refresh_tdx_snapshot.py --output data/imports/tdx_snapshots.json --enrich-existing --enrich-limit 30 --bar-count 20 --timeout 30

# 用 AKShare 补强 K 线、估值、资金流、个股新闻和市场新闻，写回本地快照
PYTHONPATH=src python3 scripts/enrich_tdx_snapshot.py --snapshot data/imports/tdx_snapshots.json --codes 688362,600519 --bar-count 120 --news-limit 5 --market-news-limit 20
# 如已配置 ITICK_API_KEY，脚本会优先用 iTick 补 K 线/最新报价，再用 AKShare/Tushare 补估值、资金和新闻

# 发送日报。先用 dry-run 验证渠道，再去掉 --dry-run 真发
PYTHONPATH=src python3 -m stock_ts.cli send-daily --provider sample --holdings data/portfolio/holdings.csv --channels email,wechat,feishu --style digest --dry-run

# 使用 .env 里配置的默认日报通道和样式
PYTHONPATH=src python3 -m stock_ts.cli send-daily --provider sample --holdings data/portfolio/holdings.csv --dry-run

# 单渠道测试发送
PYTHONPATH=src python3 -m stock_ts.cli test-notify --channel feishu --style digest --dry-run --subject "StockTS 通知测试" --content "测试消息"

# 输出到文件
PYTHONPATH=src python3 -m stock_ts.cli market --provider sample --output reports/market.md
PYTHONPATH=src python3 -m stock_ts.cli stock 600519 --provider sample --output reports/600519.md
```

也可以使用 Makefile：

```bash
make market
make stock
make test
make run
```

## 配置与缓存

- `.env` 支持 `STOCK_TS_PROVIDER`、`STOCK_TS_HOLDINGS_PATH`、`STOCK_TS_CACHE_DIR`、`TUSHARE_TOKEN`、`ITICK_API_KEY`。
- `TUSHARE_TOKEN` 和 `ITICK_API_KEY` 只在本地 `.env` 使用，页面和 doctor 只显示 configured/missing。
- 邮件发送使用 `EMAIL_SENDER`、`EMAIL_PASSWORD`、`EMAIL_RECEIVERS`；企业微信使用 `WECHAT_WEBHOOK_URL`；飞书使用 `FEISHU_WEBHOOK_URL`。
- `NOTIFICATION_REPORT_CHANNELS` 控制默认日报通道，`NOTIFICATION_REPORT_STYLE` 控制默认消息样式（`auto/full/digest/action`）。
- 大模型增强使用 `STOCK_TS_LLM_API_KEY` 或 `DASHSCOPE_API_KEY`；默认兼容千问 DashScope OpenAI-compatible endpoint：`https://dashscope.aliyuncs.com/compatible-mode/v1`，默认模型 `qwen-plus`。
- 真实 Key 只能放本地 `.env`，不要写入 README、测试、代码、命令历史或提交记录；`doctor` 只显示 configured/missing。
- `send-daily --dry-run` 和 Web 设置页的“发送测试消息 / 发送今日复盘”都支持 dry-run，适合先验证配置状态与消息格式。
- `daily --cache-dir data/cache` 会缓存完整日报 Markdown；加 `--refresh` 可强制刷新。
- `scripts/refresh_tdx_snapshot.py --quote-only` 会先扫描全市场 A 股行情，再把预筛候选写入本地 TDX 快照；这是智能选股的全市场入口。
- `scripts/refresh_tdx_snapshot.py --enrich-existing` 会在现有候选快照上补前排真实日线与主题，并写入 `enriched_count` / `enrichment_status`，页面只把已补强部分标成深度数据。
- `scripts/enrich_tdx_snapshot.py` 会用 iTick/Tushare/AKShare 把日线 K 线、最新报价、PE/PB/市值、主力资金流、个股新闻和市场新闻写回本地快照；Web 只读快照，不在打开页面时等待外部接口。
- Web 智能选股会优先使用 TDX 快照里的全市场预筛候选做策略分层；页面展示的是候选池和策略命中，不把它说成确定买点。
- `JsonCacheStore` 是当前最小缓存层，后续可升级 SQLite/Parquet。

## 本地导入格式

行情 CSV：

```csv
date,open,high,low,close,volume
2026-06-05,11.3,11.8,11.1,11.6,2200
```

新闻/舆情 CSV：

```csv
date,source,title,summary,url,sentiment
2026-06-05,示例财经,半导体景气改善,订单增长和国产替代推进,https://example.com/a,positive
```

`sentiment` 支持 `positive`、`negative`、`neutral`，也支持 `利好`、`利空`、`中性`。

交易流水 CSV：

```csv
date,code,name,side,shares,price,fee,tax,sector,note
2026-06-01,600519,贵州茅台,buy,100,1500,5,0,白酒,建仓
2026-06-03,600519,贵州茅台,sell,20,1700,2,1,白酒,减仓
```

`side` 支持 `buy/sell`，也支持 `买入/卖出`。使用 `--transactions` 时会按移动加权成本生成当前持仓；当前版本暂不把手续费、印花税纳入成本计算。

持仓添加位置：

- 默认持仓文件：`data/portfolio/holdings.csv`
- 默认交易流水：`data/portfolio/transactions.csv`
- Web 可通过 URL 参数切换：`?holdings=data/portfolio/holdings.csv`
- 持仓 CSV 表头必须是：`code,name,shares,cost_price,sector,note`

自选股 YAML-like 文件：

```yaml
stocks:
  - code: 600519
    name: 贵州茅台
    sector: 白酒
    tags: 核心资产,消费
    thesis: 消费龙头样例，观察板块弱势时是否跑输市场
    alert_price_below: 1500
    alert_score_below: 60
```

当前解析器为轻量 YAML-like 格式，不依赖 PyYAML；适合先沉淀自选池、标签、研究假设和提醒条件。提醒只用于复盘检查，不代表自动交易。

## 使用真实数据源

当前推荐优先用 `tencent` 或 `auto` 做个股/指数行情验证；它不需要安装额外依赖，适合避免 AKShare 东财接口临时断连导致的样例回退：

```bash
PYTHONPATH=src python3 -m stock_ts.cli stock 大业股份 --provider tencent
PYTHONPATH=src python3 -m stock_ts.cli stock-deep 603278 --provider tencent
PYTHONPATH=src python3 -m stock_ts.cli daily --provider auto --holdings data/portfolio/holdings.csv
```

`tencent` 当前提供指数与个股日线；板块与候选池暂时沿用 sample 结构兜底，因此页面会在数据质量模块显示实际来源和风险提示。

Web 工作台固定读取 TDX MCP 快照。使用 Codex 里的 TDX MCP 或其他通达信服务时，先把查询结果整理为本地快照文件；缺少 `market`、`sectors` 或 `candidate_universe` 时页面会直接提示补数据，不再回退到 sample：

```json
{
  "market": {
    "trade_date": "2026-06-18",
    "indices": [
      {"code": "000001", "name": "上证指数", "close": 3280.12, "pct_chg": 0.62, "amount": 5123.4}
    ],
    "advancing": 3210,
    "declining": 1450,
    "limit_up": 63,
    "limit_down": 7,
    "top_sectors": [["机器人", 2.8]]
  },
  "sectors": [
    {"name": "机器人", "pct_chg": 2.8, "advancing_ratio": 0.72, "amount_change": 16.4, "limit_up_count": 9}
  ],
  "candidate_universe": {
    "items": [
      {
        "code": "603278",
        "name": "大业股份",
        "sector": "机器人",
        "bars": [
          {"date": "2026-06-18", "open": 12.10, "high": 12.90, "low": 12.00, "close": 12.80, "volume": 510000}
        ]
      }
    ]
  },
  "stocks": {
    "603278": {
      "name": "大业股份",
      "bars": [
        {"date": "2026-06-12", "open": 12.18, "high": 12.36, "low": 11.62, "close": 11.83, "volume": 349275}
      ],
      "fund_flow": -0.43,
      "pe_ttm": 42.0
    }
  }
}
```

默认路径为 `data/imports/tdx_snapshots.json`，也可用 `STOCK_TS_TDX_SNAPSHOT_PATH` 指定，然后运行：

```bash
PYTHONPATH=src python3 -m stock_ts.cli stock-deep 603278 --provider tdx-snapshot
```

已接入 AKShare 适配层，安装数据依赖后可尝试：

```bash
python3 -m pip install -e '.[data]'
PYTHONPATH=src python3 -m stock_ts.cli market --provider akshare
PYTHONPATH=src python3 -m stock_ts.cli stock 600519 --provider akshare
PYTHONPATH=src python3 -m stock_ts.cli sectors --provider akshare
PYTHONPATH=src python3 -m stock_ts.cli candidates --provider akshare --limit 20
PYTHONPATH=src python3 -m stock_ts.cli fetch-news 600519 --provider akshare
```

AKShare 大盘会优先读取全市场实时行情来计算涨跌家数；如果外部 spot 接口临时失败，会降级为指数行情，避免整份报告失败。行业板块使用 AKShare 行业板块接口；候选池优先用全市场 spot，失败时回退到行业板块成份；个股历史行情接口断连或返回空数据时，会回退到 sample 个股数据并在 stderr 输出 warning。真实数据源仍需考虑接口变更、限频、交易日、复权口径和字段缺失；后续可继续增加 pytdx 或本地行情缓存；iTick 当前仅作为需要 `ITICK_API_KEY` 的报价/K线备用源，不替代新闻、估值、基本面和资金流。

## 轻量 Web 页面

无需安装 Streamlit，直接用 Python 标准库启动：

```bash
PYTHONPATH=src python3 -m stock_ts.web
# 或使用项目约定入口
make run
```

浏览器打开 `http://127.0.0.1:8501`。当前页面以 **Jiewat Kaka FJ** 展示，是侧边栏式投研工作台，包含 A股大盘、板块分析、涨停板、跌停板、智能选股、个股分析、持仓分析、每日复盘报告和消息渠道。页面默认使用 `provider=auto`；支持 `?provider=tencent&code=大业股份&holdings=data/portfolio/holdings.csv` 参数；数据源或持仓文件失败时会显示可读错误页。

部署平台通常会注入 `PORT`，可用环境变量覆盖监听地址：

```bash
HOST=0.0.0.0 PORT=8501 PYTHONPATH=src python3 -m stock_ts.web
```

公开给别人访问时建议开启只读模式，避免外部用户修改持仓、保存配置或触发消息发送：

```bash
STOCK_TS_PUBLIC_READONLY=1 HOST=0.0.0.0 PORT=8501 PYTHONPATH=src python3 -m stock_ts.web
```

个人自用网站可以关闭只读模式，页面会显示添加/编辑/删除持仓、保存配置和消息测试入口：

```bash
STOCK_TS_PUBLIC_READONLY=0 HOST=127.0.0.1 PORT=8501 PYTHONPATH=src python3 -m stock_ts.web
```

关闭只读后，页面会直接写入服务器上的 `data/portfolio/holdings.csv`。如果是个人自用或后续准备开放给别人，建议同时开启账号体系：

```bash
STOCK_TS_AUTH_ENABLED=1
STOCK_TS_ADMIN_USERNAME=your-email@example.com
STOCK_TS_ADMIN_PASSWORD=<strong-password>
STOCK_TS_SESSION_SECRET=<random-long-secret>
STOCK_TS_AUTH_DB_PATH=data/auth/users.sqlite3
STOCK_TS_ALLOW_REGISTRATION=1
```

账号体系当前提供一个 owner 管理员、登录页、注册入口、签名会话 Cookie、退出登录和设置页账号状态。`STOCK_TS_ALLOW_REGISTRATION=1` 时，新用户可在登录页自助注册，注册后立即获得访问权限。密码使用 PBKDF2 哈希保存在 SQLite，不会在页面或配置状态里明文展示。后续开放给更多人时，可在同一个 `users` 表上继续扩展角色、邀请审核和每人独立持仓。

## 公网发布

推荐先注册 `jiewat-kaka-fj.com`，再把域名解析到部署平台提供的地址。项目已提供最小 Docker 镜像，默认以只读 Demo 方式运行：

```bash
docker build -t jiewat-kaka-fj .
docker run --rm -p 8501:8501 jiewat-kaka-fj
```

部署到 Render / Railway / Fly.io 这类平台时，使用 Dockerfile 构建即可。DNS 侧通常按平台提示添加一条 `CNAME` 或 `A` 记录；解析生效后，把 HTTPS 和自定义域名绑定到 `jiewat-kaka-fj.com`。

公网给别人访问时不要注入真实 `TUSHARE_TOKEN`、`ITICK_API_KEY`、`EMAIL_PASSWORD`、`WECHAT_WEBHOOK_URL`、`FEISHU_WEBHOOK_URL`、`STOCK_TS_LLM_API_KEY` 或个人持仓文件，除非已经开启账号体系并确认访问边界。个人自用且不对外分享时，可设置 `STOCK_TS_PUBLIC_READONLY=0` 开启持仓写入；如果后续分享给别人，优先开启 `STOCK_TS_AUTH_ENABLED=1`，再考虑多用户数据隔离。

## 项目结构

```text
AGENTS.md                         # Codex/Agent 冷启动入口
README.md                         # 项目入口说明
Makefile                          # 常用命令
pyproject.toml                    # Python 包与可选依赖
src/stock_ts/
  announcements.py                # CNInfo/巨潮公告抓取、事件摘要和风险标签
  analysis.py                     # 大盘/个股分析规则
  deep_models.py                  # 深度分析领域模型
  deep_analysis.py                # 多角度深度分析、批量对比、多轮对抗
  deep_report.py                  # 深度分析 Markdown 渲染
  research_playbook.py            # 决策仪表盘、策略透镜、研究团队和数据块完整性
  professional_research.py        # 单股专业研究附录：技术结构、公告事件雷达、复核动作
  llm.py                          # 可选 OpenAI-compatible 大模型增强层
  output.py                       # CLI/Web 共用文本输出工具
  watchlist.py                    # 自选股研究工作台、标签和提醒检查
  backtest.py                     # 轻量均线回测与风险指标
  html_report.py                  # 单文件 HTML 结论页渲染
  symbols.py                      # 股票名称/代码轻量解析
  workflows.py                    # CLI/Web 共用服务编排层
  cache.py                        # 轻量 JSON 缓存工具
  cli.py                          # 命令行入口
  web.py                          # 轻量本地页面，无需额外依赖
  dashboard.py                    # 可选 Streamlit Dashboard
  portfolio.py                    # 持仓 CSV 读取
  indicators.py                   # 基础技术指标
  models.py                       # 领域数据模型
  providers/                      # 数据源适配层
  report.py                       # Markdown 报告渲染
tests/                            # pytest 回归测试
docs/
  architecture/README.md          # 架构说明
  superpowers/                    # yqn-dev-skills 需求治理资产
  tech-specs/README.md            # 技术规范入口
```

## 路线图

1. 接入真实板块和全市场股票池数据，校准候选观察池评分。
2. 在现有 JSON 缓存基础上接入稳定数据缓存：SQLite/Parquet，按交易日增量刷新。
3. Tushare 实测：用真实交易日数据校准字段、行业、财务和资金流口径。
4. 增强个股：K 线图、财务指标、公告摘要、真实行业映射和历史评分回放。
5. 增加自选股：watchlist 批量分析、每日复盘报告、风险异动提醒。
6. 增加 AI 研报助手：固定 Prompt 契约、可回放样例、人工复核门禁。

# `a-stock-data` / `global-stock-data` 能力与 StockTs 集成调研

Date: 2026-07-28

## 结论先行

1. **港美股数据可以通过 `global-stock-data` 所列接口获取，但它不是数据仓库或可安装 SDK。** 两个仓库的交付物都是单个 `SKILL.md`：Markdown 中内嵌可复制执行的 Python 函数；仓库没有数据文件、Python 包、自动更新任务、测试目录或 GitHub Actions。应把它们视为“接口目录 + 参考实现”，不能直接挂进 StockTs 作为稳定依赖。[A 股仓库固定快照](https://github.com/simonlin1212/a-stock-data/tree/281fc69a0b733ffc6458fe2cf9f1ea56804aa886)；[港美股仓库固定快照](https://github.com/simonlin1212/global-stock-data/tree/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef)
2. **最值得先落地的是港美股报价/K 线的 provider 适配，以及美股 SEC 官方数据。** 港美报价可用腾讯/新浪/东财互备；美股 K 线可用新浪 + Yahoo，港股 K 线在该仓库中只有 Yahoo；SEC Filing、XBRL、全市场横截面是美股最有差异化、且仓库标为可商用的能力。[港美股数据源优先级](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L2171-L2197)
3. **如果 StockTs 是公开或商业产品，不能因为代码是 Apache-2.0 就默认可以使用或再分发接口数据。** `global-stock-data` 将 SEC/Treasury/CFTC 标为 S 级，将 FINRA 标为 B 级，将 CBOE/Nasdaq/Yahoo/东财/新浪/腾讯标为 C 级，并明确 CBOE 需授权、Yahoo 仅限个人使用、HKEX CCASS 自动抓取已被排除。该分级来自仓库作者对条款的整理，本报告不构成法律意见。[合规分级与硬规则](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L104-L140)
4. **不要复制仓库内的技术指标和分析结论。** StockTs 已有确定性 `analysis/` 层；外部仓库只应负责取数和规范化。`global-stock-data` 的 MA/MACD/RSI/KDJ/布林带属于参考实现，不应成为第二套计算口径。[港美股技术指标层](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L770-L798)
5. **建议分阶段接入，不做“一次性全市场全能力导入”。** 第一阶段仅做按标的只读查询与有限缓存；第二阶段接 SEC；第三阶段才评估全市场列表、资金流、期权、新闻等高风险或高成本能力。

## 调研基线与证据边界

- `a-stock-data`：`main` 提交 [`281fc69a0b733ffc6458fe2cf9f1ea56804aa886`](https://github.com/simonlin1212/a-stock-data/commit/281fc69a0b733ffc6458fe2cf9f1ea56804aa886)，提交时间 2026-07-26，`SKILL.md` 版本 3.5.1。[版本元数据](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/SKILL.md#L1-L14)
- `global-stock-data`：`main` 提交 [`c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef`](https://github.com/simonlin1212/global-stock-data/commit/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef)，提交时间 2026-07-26，`SKILL.md` 版本 2.0.3。[版本元数据](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L1-L20)
- 本次实际克隆并检查了固定提交下的 README、`SKILL.md`、CHANGELOG、LICENSE 和完整文件树；没有调用第三方行情端点做长期完整性/准确性回测。因此，下文的覆盖数量和历史跨度均标为“仓库声明”或“函数参数允许”，不是 StockTs 已验证的 SLA。
- 两个固定快照都只有 README/CHANGELOG/LICENSE/`SKILL.md`、赞助配置与图片资产；没有 `pyproject.toml`、`requirements.txt`、模块目录、测试目录、数据目录或 `.github/workflows/`。[A 股文件树](https://github.com/simonlin1212/a-stock-data/tree/281fc69a0b733ffc6458fe2cf9f1ea56804aa886)；[港美股文件树](https://github.com/simonlin1212/global-stock-data/tree/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef)

2026-07-28 的小范围验活结果与上述边界一致：腾讯 `qt.gtimg.cn` 一次请求可同时返回 `usAAPL` 与 `hk00700`，并带 USD/HKD；Yahoo chart 的 `0700.HK`、`5d` 返回 OHLCV；SEC submissions 的 `CIK0000320193` 返回 Apple。相反，东财 push2 的 AAPL 单股请求本次出现 `Empty reply`，东财 `np-weblist` 本次返回 HTTP 567，而东财 reportapi 行业研报正常。这不是可用率统计，但直接说明同一供应商不同域名、不同端点也可能呈现不同故障面，生产适配必须逐端点隔离状态、保留缓存并允许主备切换。对应接口定义见 [腾讯港美报价](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L429-L595)、[Yahoo K 线](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L725-L765)、[SEC submissions](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L1549-L1595) 和 [东财行业研报](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/SKILL.md#L747-L798)。

## 项目形态、目录与文件格式

| 项目 | 仓库交付物 | 运行时返回 | 本地持久化 | 更新方式 |
| --- | --- | --- | --- | --- |
| `a-stock-data` | 一份约 3,000 行的自包含 `SKILL.md`；依赖 `mootdx`、`requests`、`pandas`、`stockstats` | 大部分函数返回 `dict` / `list[dict]` / `pandas.DataFrame`；原始协议含 TCP 二进制、JSON/JSONP、GBK 分隔文本 | 可下载研报 PDF 到 `./reports`；北向资金会写 `~/.tradingagents/cache/northbound_daily.csv` | 用户更新 `SKILL.md` 或跟随 tag；运行时按需直连上游，无后台 ETL |
| `global-stock-data` | 一份约 2,200 行的自包含 `SKILL.md`；仅依赖 `requests` | 统一示例主要返回内存中的 `dict` / `list[dict]`；原始协议含 JSON、GBK 分隔文本、FINRA pipe 文本、Treasury CSV | 只有 Yahoo session/crumb 与 SEC ticker-CIK 映射的进程内缓存，无数据文件 | 用户更新 `SKILL.md` 或跟随 tag；运行时按需直连上游，无后台 ETL |

证据：A 股安装依赖见 [README 快速开始](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/README.md#L59-L77)，PDF 下载写盘见 [`download_pdf`](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/SKILL.md#L683-L724)，北向 CSV 缓存见 [`_northbound_cache_path`](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/SKILL.md#L1017-L1089)；港美股安装依赖见 [README 快速开始](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/README_zh.md#L80-L98)，内存 crumb 见 [`get_yahoo_session`](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L213-L251)，内存 CIK 映射见 [`ticker_to_cik`](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L1759-L1788)。

这意味着所谓“数据更新”有两层：

- **仓库代码更新**是维护者手工提交、打 tag、更新 CHANGELOG；没有 CI 定时探测接口。
- **市场数据更新**是调用函数时临时请求上游；仓库自身不镜像市场数据，也不提供增量同步、水位线、校验和、历史补数或 schema version。

## `a-stock-data` 能力

### 数据覆盖

仓库声明覆盖 A 股主板、中小板、科创板、ST，并在路由规则中包含沪深北、指数和 ETF；10 层、44 个端点、15 个源。[覆盖声明](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/SKILL.md#L12-L18) [市场前缀规则](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/SKILL.md#L368-L402)

| 层 | 标的/频率 | 主要字段与历史跨度 | 对 StockTs 的价值 |
| --- | --- | --- | --- |
| 行情/K 线 | A 股、指数、ETF；1/5/15/30/60 分、日/周/月/季/年 | OHLC、成交量/额；46 字段报价含五档；逐笔成交；通达信 K 线不复权 | 本地已有新浪 + 腾讯日线，可借鉴通达信盘口/分钟线与腾讯路由修复，但不宜为了它引入冲突依赖 |
| 估值/基本面 | 个股、指数、ETF；实时或季度 | 腾讯 PE/PB/市值/换手/涨跌停；通达信 37 字段季报与 F10；新浪三表 | 可补充财报与 F10，但上游条款、字段稳定性需另审 |
| 研报/一致预期 | 个股与行业；查询区间示例 2000-01-01 至 2030-01-01，最多默认 5×100 条 | 标题、机构、评级、三年 EPS 预测、PDF；同花顺一致预期；iwencai NL 检索 | 可作为研究证据增强，不能进入确定性评分，PDF 需单独治理版权与缓存 |
| 信号/资金 | 盘中分钟、日级 120 日、今日/5日/10日、未来 90 日 | 题材、板块归属、资金流、龙虎榜、解禁、行业/概念/地域资金、两融、大宗、股东户数、分红 | 可补齐 StockTs 当前缺失证据，但大多依赖东财，需低频且可降级 |
| 新闻/公告 | 7×24 快讯、个股新闻、沪深北公告 | 标题、摘要、时间、PDF/链接 | 可进入事件雷达；必须保存来源、发布时间、抓取时间 |
| 打板/ETF 期权/舆情 | 当日池、各月 ETF 期权、热榜/互动易 | 连板、封单、炸板、希腊字母/IV、问答、热度 | 属 A 股扩展，不是本次港美股优先项 |

完整字段清单见 [README 行情至资金层](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/README.md#L81-L126) 和 [基础数据至舆情层](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/README.md#L128-L179)。K 线周期、字段和不复权限制见 [mootdx 行情层](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/SKILL.md#L469-L505)。

### 数据来源与降级

- 首选通达信 TCP 与腾讯行情；低风险源含新浪、巨潮、同花顺；东财只用于独有能力。[优先级原则](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/SKILL.md#L167-L184)
- 仓库为行情、K 线、龙虎榜、资金流、公告、财务、新闻、评级和北向等列出独立备源；打板、期权、舆情仍无独立备源。[备用源表](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/SKILL.md#L2841-L2859)
- 对 StockTs 最有直接价值的不是复制全部函数，而是吸收其**显式市场前缀、真实取数验活、主备源分离、错误不可静默为空**的经验。CHANGELOG 记录过 ETF/指数误路由导致返回错标的、TCP 握手成功但取数为空等问题。[v3.4.1 修复记录](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/CHANGELOG.md#L50-L68)

### 失败与限流风险

- 仓库给出的东财社区阈值是 >5 QPS、单 IP 并发 ≥10、1 分钟 ≥200、5 分钟 ≥300 会显著提高封禁风险；一次未限速的 10 线程、45,000+ 请求案例造成 `push2/push2his` IP 级封禁 20+ 小时。[东财阈值与事故](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/SKILL.md#L186-L208)
- `em_get()` 以 1 秒最小间隔、随机抖动、session 复用和 429/5xx 重试缓解风险；403 不重试。[请求 helper](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/SKILL.md#L404-L448)
- 腾讯也不是无限容量：仓库事故记录称连续 5,000+ 次 K 线请求后可能返空，降速后恢复。[限流案例](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/SKILL.md#L198-L206)
- 通达信依赖 `mootdx` 已停更、可能与现代 `httpx` 依赖冲突，TCP 7709 在海外不稳定；这与 StockTs 当前 `httpx` 栈存在现实集成成本。[mootdx 风险](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/README.md#L265-L277)
- 北向数据存在上游断供与披露变化：深股通分钟值仅供参考，历史从本地 CSV 开始累积，不是完整历史库。[北向限制](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/SKILL.md#L1017-L1025)
- 仓库更新快且频繁修复静默截断、市场路由、字段变更等问题，说明前端接口 schema 不稳定，必须做 fixture 合同测试和数据质量门槛。[v3.5.1 修复记录](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/CHANGELOG.md#L3-L31)

## `global-stock-data` 能力

### 港股与美股核心覆盖

仓库声明 13 层、30+ 端点、11 个源。Layer 1–5 同时覆盖港美股；CBOE 期权、FINRA、SEC 事件/横截面明确仅美股。[架构与市场范围](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L24-L76)

| 能力 | 美股 | 港股 | 频率/跨度 | 关键字段 | 主要限制 |
| --- | --- | --- | --- | --- | --- |
| 实时报价 | 新浪、腾讯、东财 | 腾讯、 新浪、东财 | 上游实时/延时快照 | OHLC、昨收、成交量/额、涨跌幅、PE/PB、市值、52 周高低、币种；腾讯美股 71 字段、港股 78 字段 | “实时”延迟未形成 SLA；GBK 分隔字段按下标解析，schema 易漂移 |
| K 线 | 新浪主、Yahoo 备 | Yahoo 唯一 | 新浪美股仓库声明可回溯至 1984；Yahoo 参数支持 5m/15m/1h/日/周/月，range 到 `max` | 日期、OHLCV | Yahoo 个人使用限制；港股无独立备源；示例未返回成交额 |
| 技术指标 | 是 | 是 | 基于取得的 K 线 | MA/EMA、MACD、RSI、KDJ、布林带 | 应由 StockTs 本地 `analysis/` 统一计算 |
| 财报/关键指标 | 东财、Yahoo、SEC | 东财、Yahoo | 东财默认最近 4 期；Yahoo 年/季；SEC 函数每指标示例截最近 20 条 | 三表、49/75 项指标、PE/PB/EV、利润率、ROE/ROA、目标价、分析师、机构持仓；SEC 503 个 GAAP 指标（仓库实测口径） | 港股无官方 S 级源；Yahoo/东财为 C 级 |
| 资金流 | 东财 | 东财 | 默认 100 个交易日 | 主力/超大/大/中/小单净额及主力占比 | 非官方算法口径，依赖东财单源 |
| 期权 | CBOE 主、Yahoo 备 | 无 | 当前延时全链；支持 0DTE 与 N 日内筛选 | bid/ask、volume/OI、IV、delta/gamma/vega/theta/rho、spot | CBOE 需事先授权；Yahoo 无完整 Greeks；不适用于实盘 |
| SEC Filing/XBRL | 是 | 否 | submissions 最近 50 条；全文检索 2001 至今；companyfacts 每指标示例最近 20 条 | 10-K/10-Q/8-K/Form 4/13F/144、正文检索、结构化财务 | 必须真实 UA，≤10 req/s；统一 helper 设 8 req/s |
| 全市场列表/筛选 | NASDAQ/NYSE/ETF | 港股 | 分页快照；仓库样本为美股 5,925+、港股 18,000+ | 代码、名称、价、涨幅、量额、振幅、高低开收 | 依赖东财；不宜全量高频轮询 |
| 做空 | FINRA Reg SHO | 无 | 每日；函数可拼任意日期，默认回退近 7 个工作日 | short、short-exempt、total、ratio；仓库样本覆盖 12,112 只 | short volume 不是 short interest；商用条款需确认 |
| 宏观/日历 | Treasury、CFTC、Nasdaq | 间接相关 | 美债按年每日；COT 最新 N 条；财报日历按日 | 1M–30Y 收益率、COT、财报时点/EPS 预期 | Nasdaq 条款未核实 |
| 搜索/新闻 | 东财/Yahoo/SEC | 东财/Yahoo | 按需 | 中英文代码映射、新闻标题/发布者/时间、ticker-CIK | Yahoo/东财 C 级；新闻无独立备源 |

主要字段证据：美股报价见 [`us_stock_quote_sina/tencent`](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L429-L513)，港股报价见 [`hk_stock_quote_tencent/sina`](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L516-L595)，K 线参数与跨度见 [Layer 2](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L685-L765)，基本面见 [东财与 Yahoo](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L986-L1124)，资金流见 [Layer 5](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L1271-L1312)。

差异化能力证据：CBOE 期权见 [Layer 6.1](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L1317-L1378)，SEC XBRL 见 [Layer 7.2](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L1598-L1663)，全市场列表见 [Layer 8.4](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L1791-L1852)，FINRA 见 [Layer 9](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L1857-L1940)，SEC 事件/全文检索见 [Layer 10](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L1944-L2025)，横截面见 [Layer 11](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L2029-L2124)，宏观见 [Layer 12](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L2128-L2167)。

### 港股可用边界

港股当前可通过这个仓库获得：

- 腾讯/新浪/东财的报价与估值快照；
- Yahoo 日/周/月/分钟 K 线；
- 东财/Yahoo 财报、关键指标、分析师预期和机构持仓；
- 东财日级资金流、搜索、全市场列表；
- Yahoo 新闻。

港股当前**不能**从这个仓库获得：CBOE/Yahoo 港股期权、SEC/FINRA 数据、CCASS 自动抓取。仓库明确称港股 K 线只有 Yahoo、港股期权不覆盖，并删除了违反 HKEX 条款的 CCASS 抓取代码。[港股 K 线限制](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L760-L765) [港股期权限制](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L1489-L1503) [HKEX 排除理由](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L130-L140)

因此：**个人/内部研究场景可以较快接入；公开商业产品没有一条来自该仓库、同时兼具港股 K 线与明确可商用授权的路径。** 这不是技术问题，而是数据许可缺口。

### 失败、限流与实现风险

- 官方源 helper 为 SEC 设 8 QPS、FINRA/CBOE 4 QPS、Nasdaq 2 QPS，并区分“确实无数据”与网络/配置/限流故障；这是可借鉴的错误语义。[统一 HTTP 出口](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L279-L408)
- SEC 必须使用包含真实联系信息的 User-Agent；否则会被判定为未声明自动化工具。[SEC 要求](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L109-L114)
- **统一 helper 只明确覆盖新增的 Layer 9–12。** 旧的港美报价、Yahoo、东财以及旧 SEC Layer 7 多数仍直接 `requests.get`，没有共享的重试、速率预算和熔断；接入 StockTs 时必须重写到现有 async client/受控 provider，不能原样复制。[helper 覆盖范围](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L279-L282) [东财直连示例](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L254-L274) [旧 SEC 直连示例](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L1549-L1615)
- Yahoo 的 cookie/crumb 会过期；中国网络访问 Yahoo/SEC 可能不稳定；港股 K 线无备源。[FAQ](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/README_zh.md#L211-L223)
- Yahoo K 线示例用本机 `datetime.fromtimestamp()` 格式化时间并丢失时区，跨部署时区可能造成盘中时间或交易日偏移；StockTs 必须按交易所时区规范化。[Yahoo K 线时间处理](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L725-L756)
- 腾讯返回是按位置解析的 GBK 文本；仓库在 2026-07-26 才修复两个报价函数此前“每次调用必崩”的字段下标问题。任何复制都必须配真实载荷 fixture、字段数守卫、名称/代码回验。[v2.0.2 修复记录](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/CHANGELOG.md#L36-L65)
- 全市场列表中的价、高低开收被注明是“原始值，需按小数位缩放”，但函数返回没有携带缩放位 `f59`；不应直接作为标准化价格使用。[全市场列表字段](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L1835-L1852)
- SEC Frames 的 instant/duration 周期差异也在最新版本才修复；横截面还存在不同公司使用不同 XBRL 标签、需合并口径的问题。[v2.0.3 修复](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/CHANGELOG.md#L3-L25) [XBRL 口径提醒](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L2120-L2124)

## 许可证与使用限制

### 仓库代码

两个仓库都是 Apache License 2.0。若直接复制代码并分发修改版本，需要附许可证、标注修改、保留版权/归属声明；代码按“AS IS”提供，适用性风险由使用者承担。[A 股 LICENSE](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/LICENSE#L89-L151) [港美股 LICENSE](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/LICENSE#L89-L151)

### 上游市场数据

Apache-2.0 只覆盖仓库作者的代码/文档，不替代上游数据许可。`global-stock-data` 自己也明确“只分发代码，不分发市场数据”，商用只建议 S 级源。[README 声明](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/README_zh.md#L29-L37)

建议按以下策略治理：

| 来源 | 仓库分级 | StockTs 建议 |
| --- | --- | --- |
| SEC EDGAR | S | 可作为美股基本面/事件首批来源；配置真实 UA，严格限速，保留来源 URL |
| US Treasury / CFTC | S（但仓库说明未逐条核验两站条款） | 可做宏观研究；正式商用前由项目自行复核最新条款 |
| FINRA | B | 仅内部研究试验；商用前确认许可，不对外再分发原始文件 |
| CBOE | C | 未获许可前不接生产，不缓存或对外展示全链数据 |
| Nasdaq | C | 条款未核实，暂缓生产接入 |
| Yahoo / 东财 / 新浪 / 腾讯 | C | 仅个人/内部研究开关；公开商业部署前换持牌源或取得授权 |
| HKEX CCASS | 排除 | 不实现自动抓取；只走授权渠道 |

## 与 StockTs 的契合点和缺口

### 已契合

- StockTs 已把 provider 访问隔离在 `backend/src/marketdesk/providers/`，由 `MarketProvider` 协议向 service 提供行情、指数、板块、K 线与研究证据；这是放置港美适配器的正确边界。[本地 provider 协议](../../backend/src/marketdesk/services.py#L44-L53)
- `DatasetMeta` 已有 `source`、`observed_at`、`fetched_at`、`freshness`、`coverage`、`errors`，可承载港美多源取数与失败降级。[本地数据元信息](../../backend/src/marketdesk/models.py#L19-L32)
- service 已在刷新失败时读取最近快照并标为 stale，适合外部源不稳定场景。[本地 stale fallback](../../backend/src/marketdesk/services.py#L64-L104)
- 本地已有新浪、腾讯、东财接口和重试框架；A 股仓库验证了相同上游的若干字段与降级策略，可复用设计经验而非复制运行时。[本地 PublicMarketProvider](../../backend/src/marketdesk/providers/public_market.py#L46-L99)

### A 股侧可先吸收的能力

即使暂不做港美股，`a-stock-data` 也能补上 StockTs 已经明确暴露为“缺失证据”的部分。建议按以下顺序评估，而不是替换现有的新浪全市场、腾讯 K 线或本地技术指标：

1. **公告 + 研报证据**：用巨潮公告、东财个股/行业研报补充 `StockDossier.research_evidence`。当前分析会在缺少这些数据时明确标记“公告与研报增强数据”，因此这是与现有产品契约最直接的增量；原始证据应保留标题、机构/发布方、发布日期和 URL，不能只传无来源文本。[本地缺失证据处理](../../backend/src/marketdesk/analysis/stock.py#L195-L211)
2. **事件雷达备源**：把财联社电报作为当前东财快讯的独立故障面备源，统一去重、分类和来源展示；不改变 `analysis/events.py` 的确定性分类边界。[外部财联社端点](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/SKILL.md#L1890-L1933)
3. **板块资金与个股板块映射**：用于提高现有“板块位置/资金态度”的覆盖度，但要低频缓存，不能在每次打开个股时重新抓全市场。[外部板块资金流](https://github.com/simonlin1212/a-stock-data/blob/281fc69a0b733ffc6458fe2cf9f1ea56804aa886/SKILL.md#L1439-L1539)
4. **解禁、两融、大宗和股东户数**：作为风险/筹码证据单独展示，先不进入当前评分；这些口径和更新时间不同，不能压成一个笼统的“资金面分数”。

不建议接入 `mootdx` 只为重复现有日线能力，也不建议采用外部技术指标、打板信号和估值结论；前者会引入依赖与 TCP 运维成本，后两者会制造第二套分析口径。

### 必须先解决的模型缺口

1. `EquityQuote` 没有 `market`、`exchange`、`currency`、报价时间、延时类型；港美同名代码、不同币种和跨时区数据不能安全混入 A 股快照。[本地 EquityQuote](../../backend/src/marketdesk/models.py#L43-L57)
2. 当前全市场筛选的 exchange 只允许 `all/sh/sz/bj`，且本地符号解析按 6 位 A 股代码构造；不能直接容纳 `AAPL`、`NASDAQ`、`HK.00700`。[本地筛选契约](../../backend/src/marketdesk/models.py#L79-L105) [本地代码路由](../../backend/src/marketdesk/providers/public_market.py#L184-L191)
3. StockTs 的 `Bar.amount` 是必填 `float`，而 `global-stock-data` 的新浪/Yahoo K 线只有 OHLCV。不能用 0 冒充有效成交额；应将金额改为可空或定义单独的市场历史契约，并让覆盖度反映缺失。[本地 Bar](../../backend/src/marketdesk/models.py#L277-L285) [外部 K 线返回](https://github.com/simonlin1212/global-stock-data/blob/c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef/SKILL.md#L693-L732)
4. 当前 `_market_observed_at` 固定上海时区和 A 股交易时段；美股需 `America/New_York`、港股需 `Asia/Hong_Kong`，并处理夏令时、各自节假日与延时数据。[本地观察时间](../../backend/src/marketdesk/providers/public_market.py#L30-L43)
5. 当前技术分析可以复用同一 `Bar` 口径，但前提是先完成复权、币种、交易日和缺失字段规范化。外部仓库的纯 Python指标不应绕过这些契约。
6. 当前机会筛选包含 ST/退市判断、A 股涨跌幅区间、以人民币“亿元”为单位的流动性阈值；港美股必须使用独立的市场规则和本币阈值，不能共用同一个 `rank_candidates` 入口参数默认值。[本地机会规则](../../backend/src/marketdesk/analysis/opportunities.py#L61-L90)
7. 当前持仓市值、总市值、盈亏和目标仓位直接按数值相加，没有币种、汇率时间点、港股每手股数或美股碎股语义。第一阶段只能按币种分桶展示持仓，禁止在没有 FX 快照时给出跨币种组合总值和调仓股数。[本地持仓计算](../../backend/src/marketdesk/analysis/holding.py#L10-L48)
8. 当前问股只从问题中提取六位数字代码，用户偏好默认标的是 `SH.600519`；要支持 `AAPL`、`00700`、中文/英文别名，需显式市场消歧并迁移偏好契约。[本地问股解析](../../backend/src/marketdesk/analysis/ask_stock.py#L37-L57) [本地默认偏好](../../backend/src/marketdesk/models.py#L534-L539)
9. 当前 `MarketService` 只有一个内存快照和一个 `MarketSnapshot.meta`，市场分析也默认把所有股票放进同一涨跌广度。CN/HK/US 必须分开快照、交易时段、指数集合和市场 regime，不能把三个市场合并后计算一个分数。[本地市场服务](../../backend/src/marketdesk/services.py#L57-L106)

## 完整能力集成矩阵

处置含义：`现在` 是现有 A 股产品可直接形成增量；`下一步` 依赖基础契约或新页面；`以后` 需要证明价值或稳定性；`拒绝` 表示不应进入 StockTs 运行时。评分策略中，“直接”仅表示允许进入确定性计算，并不表示照搬上游结论；“间接”表示只改变覆盖度、风险提示或市场上下文；“展示”表示不计分。

### `a-stock-data` 到 StockTs

| 能力组 | 主要来源 | 规范化对象 | 页面 / 模块 | 建议 API | 刷新 / 缓存 | 评分策略 | 许可 | 处置 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A 股报价、日线 | mootdx、腾讯、百度 | `QuoteSnapshot`、`BarSeries` | 大盘、个股 | 保留现有 `/market`、`/stocks/{symbol}` | 现有 2 小时全量；个股按需 | 直接，使用本地公式 | C / 条款待核 | 拒绝重复接入；只借鉴字段校准 |
| 五档盘口、逐笔、分钟线 | mootdx、腾讯备源 | `OrderBookSnapshot`、`TradeTick`、`BarSeries` | 个股“盘中结构” | `/api/v1/instruments/{id}/microstructure` | 页面激活时 5–15 秒；不长期保存逐笔 | 展示 | 条款待核 | 以后；不为此单独引入 mootdx |
| 个股/行业研报、PDF | 东财 reportapi | `ResearchDocument`、`ConsensusForecast` | 个股、问股 | `/api/v1/instruments/{id}/research` | 元数据 6 小时；PDF 不默认缓存 | 间接；补证据覆盖，不改技术分 | C，正文版权另审 | 现在先接元数据，PDF 以后 |
| 同花顺一致预期、iwencai | 同花顺、iwencai | `ConsensusForecast`、`ScreenResult` | 个股、问股 | 复用 `/ask-stock`，新增 `/research` | 日级；查询按需 | 展示；预测值不直接加分 | C / Key | 保留现有 iwencai；一致预期下一步 |
| 热点题材、概念归属 | 同花顺、东财 | `ThemeSignal`、`InstrumentTheme` | 今日、大盘、个股 | `/api/v1/markets/CN/themes` | 5–15 分钟 | 间接市场上下文 | C | 下一步 |
| 北向资金 | 同花顺、本地累积 | `CrossBorderFlow` | 大盘、数据 | `/api/v1/markets/CN/flows/northbound` | 盘中 5 分钟、收盘固化 | 展示；披露变化时不可用 | C，且历史不完整 | 以后 |
| 个股分钟/120 日资金流 | 东财 push2/push2his | `CapitalFlowSeries` | 个股、持仓 | `/api/v1/instruments/{id}/positioning` | 分钟数据 1–5 分钟；日级 6 小时 | 间接；不把供应商算法当事实分 | C | 下一步，默认可选增强 |
| 板块排名与今日/5日/10日资金 | 东财 push2 | `SectorFlowSnapshot` | 今日、大盘、机会 | `/api/v1/markets/CN/sectors/flows` | 5–15 分钟 | 间接；可作为策略可用性条件 | C | 现在，优先补当前板块缺口 |
| 龙虎榜、全市场龙虎榜 | 东财、交易所备源 | `TradingAnomaly` | 今日、大盘、个股 | `/api/v1/markets/CN/anomalies`、`/instruments/{id}/events` | 收盘后日级 | 展示；席位净买不直接加分 | 混合，官方优先 | 下一步 |
| 解禁日历 | 东财 | `CorporateEvent` | 个股、持仓、跟踪 | `/api/v1/instruments/{id}/events?type=lockup` | 日级，未来 90 日 | 间接风险提示 | C | 下一步 |
| 两融、大宗、股东户数、分红 | 东财 datacenter | `MarginSnapshot`、`BlockTrade`、`OwnershipSnapshot`、`DividendEvent` | 个股、持仓 | `/api/v1/instruments/{id}/positioning`、`/events` | 两融日级；大宗日级；股东季度；分红日级 | 展示，触发风险提示 | C | 下一步；分对象保留口径 |
| 个股新闻、财联社电报、全球资讯 | 东财、财联社 | `RawMarketEvent` | 今日、大盘、问股 | 复用 `/market-events` | 1–5 分钟，去重缓存 | 间接；只进入本地事件分类 | C | 现在，把财联社作为独立备源 |
| 季报快照、F10、个股资料、三表 | mootdx、东财、新浪 | `FundamentalSnapshot`、`StatementSeries`、`CompanyProfile` | 个股、问股 | `/api/v1/instruments/{id}/fundamentals` | 公司资料 7 日；财报日级检查、季度固化 | 间接；先展示和覆盖度 | C / 条款待核 | 下一步；不依赖外部结论 |
| 巨潮公告、F10 公告摘要 | 巨潮、mootdx | `FilingDocument` | 个股、问股、持仓、跟踪 | `/api/v1/instruments/{id}/filings` | 15–30 分钟；元数据长期保留 | 间接风险与催化证据 | 条款需项目复核 | 现在，优先级最高 |
| 涨停/炸板/跌停/昨日涨停池 | 东财、同花顺 | `MarketMicrostructure` | 今日、大盘 | `/api/v1/markets/CN/microstructure` | 交易时段 1–5 分钟 | 间接，仅 A 股环境 | C | 以后；不进入个股买卖分 |
| ETF 期权 T 型报价、Greeks、IV | 新浪 | `DerivativeChainSnapshot` | 独立“衍生品”页 | `/api/v1/derivatives/{underlying}` | 页面激活时 15–60 秒 | 展示 | C / 条款待核 | 以后，许可明确后 |
| 互动易、热榜、人气榜、概念命中 | 巨潮、同花顺、东财 | `InvestorQAndA`、`AttentionSignal` | 个股、大盘 | `/api/v1/instruments/{id}/sentiment` | 问答 1 小时；热榜 10 分钟 | 展示，明确为注意力而非基本面 | C | 以后 |
| 外部估值公式、完整调研流程 | 本地示例代码 | 无 | 无 | 无 | 无 | 不接入 | Apache-2.0 | 拒绝；由 StockTs `analysis/` 统一 |

### `global-stock-data` 到 StockTs

| 能力组 | 主要来源 | 规范化对象 | 页面 / 模块 | 建议 API | 刷新 / 缓存 | 评分策略 | 许可 | 处置 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 港美报价与搜索 | 腾讯、新浪、东财 | `InstrumentRef`、`QuoteSnapshot` | 搜索、个股、跟踪 | `/api/v1/instruments/search`、`/{id}/quote` | 搜索目录日级；报价按需 15–60 秒 | 直接用于行情事实 | C | 现在，仅内部研究开关 |
| 美股新浪 K 线、Yahoo 港美 K 线 | 新浪、Yahoo | `BarSeries` | 个股、跟踪 | `/api/v1/instruments/{id}/bars` | 日线 1–6 小时；分钟线按需 | 直接进入本地技术计算 | C，Yahoo 个人使用 | 现在，仅内部研究 |
| 外部 MA/MACD/RSI/KDJ/布林 | 本地示例代码 | 无 | 无 | 无 | 无 | 不接入 | Apache-2.0 | 拒绝；已有更严格实现 |
| 东财/Yahoo 财报、指标、分析师与机构 | 东财、Yahoo | `FundamentalSnapshot`、`ConsensusForecast`、`OwnershipSnapshot` | 个股、问股 | `/api/v1/instruments/{id}/fundamentals` | 财报日级检查；分析师日级 | 展示/间接 | C | 以后；内部研究且可关闭 |
| SEC submissions、companyfacts | SEC EDGAR | `FilingDocument`、`FundamentalMetric` | 个股、问股、跟踪 | `/api/v1/instruments/{id}/filings`、`/fundamentals` | submissions 30–60 分钟；facts 24 小时 | 间接；来源可追溯 | S | 下一步，最优先美股能力 |
| 东财港美资金流 | 东财 push2his | `CapitalFlowSeries` | 个股 | `/api/v1/instruments/{id}/positioning` | 日级 | 展示；算法口径不透明 | C | 以后 |
| CBOE/Yahoo 期权、0DTE、Greeks | CBOE、Yahoo | `DerivativeChainSnapshot` | 独立“衍生品”页 | `/api/v1/derivatives/{underlying}` | 15–60 秒，仅页面激活 | 展示，不产出交易指令 | C，CBOE 需授权 | 未授权前拒绝生产 |
| 港美全市场列表、新闻、ticker-CIK | 东财、Yahoo、SEC | `InstrumentCatalog`、`RawMarketEvent`、`IdentifierMapping` | 搜索、大盘、问股 | `/api/v1/instruments/search`、`/market-events` | 目录日级；新闻 2–5 分钟；CIK 7 日 | 展示/检索 | 混合 S/C | 搜索与 CIK 下一步；全量榜单以后 |
| FINRA short volume | FINRA Reg SHO | `ShortVolumeSeries` | 个股、美股大盘 | `/api/v1/instruments/{id}/positioning` | 收盘后日级 | 展示；不能称为 short interest | B | 许可确认后 |
| EDGAR 每日事件流与全文搜索 | SEC EDGAR | `FilingEvent`、`SearchHit` | 今日、问股、跟踪 | `/api/v1/markets/US/filings`、`/filings/search` | 日内 30–60 分钟；历史结果长缓存 | 间接事件证据 | S | 下一步 |
| EDGAR frames 全市场横截面 | SEC EDGAR | `FundamentalScreen` | 美股机会、问股 | `/api/v1/markets/US/screens/fundamentals` | 24 小时 / 财季 | 首版展示；验证覆盖后才参与排序 | S | 下一步 |
| Treasury 收益率曲线、CFTC COT | Treasury、CFTC | `MacroObservation`、`PositioningReport` | 今日、美股大盘、问股 | `/api/v1/markets/US/macro` | Treasury 日级；COT 周级 | 间接市场上下文 | S（项目需复核最新条款） | 下一步 |
| Nasdaq 财报日历 | Nasdaq | `EarningsEvent` | 今日、跟踪、持仓 | `/api/v1/markets/US/calendar` | 日级 | 间接风险提醒 | C，条款未核 | 以后 |
| HKEX CCASS | HKEX | 无 | 无 | 无 | 无 | 不接入 | 明确禁止自动抓取 | 拒绝 |

## 页面级集成落点

| 当前页面 | 应新增的能力 | 不应该放入的内容 | 产品结果 |
| --- | --- | --- | --- |
| 今日 | 多源事件、A 股市场微结构、重要公告/解禁提醒、美债曲线与美股申报事件 | 完整公告正文、期权全链、逐笔成交 | 给出跨市场“今天先核验什么”，仍以摘要和下一步为主 |
| 大盘 | 板块资金、题材扩散、龙虎榜统计、北向状态；CN/HK/US 独立市场页签和各自 regime | 把三地涨跌广度合成一个分数 | 每个市场有独立时钟、指数、广度、环境证据和数据状态 |
| 机会 | A 股板块资金确认；美股 EDGAR 基本面横截面；每个策略声明必需数据 | 直接采用热榜、龙虎榜、0DTE 流作为推荐分 | 数据不足时策略不可用；市场规则和币种阈值分开配置 |
| 个股 | “行情技术 / 基本面 / 公告研报 / 资金筹码 / 事件风险”五类证据；美股增加 SEC | 把所有原始表堆成无限长页面；外部供应商的买卖结论 | 现有结论区保持简洁，证据区按类型渐进展开并保留来源 |
| 问股 | 从本地证据仓读取财报、公告、研报、SEC、宏观和持仓上下文，回答带引用 | 每次提问都实时轰炸所有外部 provider；无来源的自然语言总结 | 先解析意图和市场，再查询已有证据；缺失时明确触发有限刷新 |
| 持仓 | 公告/解禁/财报日历风险、市场独立估值；后续增加 FX 与每手股数 | 没有 FX 快照时汇总 CN/HK/US 市值或给跨币种调仓数量 | 首版全球持仓按币种分桶，FX 完成后才开放组合汇总 |
| 跟踪 | 新公告、新研报、财报申报、异常资金和 thesis 失效条件提醒 | 仅因热榜排名变化自动升级为机会 | 把跟踪清单升级成事件驱动的复盘队列 |
| 数据 | 按“能力 × 来源 × 市场”展示状态、许可级别、最近成功/失败、限速预算、缓存年龄 | 只显示一个供应商总体为 ready | 能看出“腾讯港股报价正常，但东财港美资金流失败”这类局部状态 |

## 目标领域契约

不要继续把所有数据压进 `EquityQuote` 或 `research_evidence: list[str]`。建议新增以下严格模型，并让业务层只依赖规范模型：

- `InstrumentRef`：稳定业务 ID、市场、交易所、代码、名称、币种、时区、资产类型、每手股数；供应商代码放在 `ProviderSymbol` 映射中。
- `SourceRef`：来源、端点能力、许可级别、原始 URL、观察时间、抓取时间、延迟类型和解析版本。
- `EvidenceEnvelope`：`kind` 判别字段、`instrument_id`、`source`、有效期、覆盖度、错误，以及严格的 payload 联合类型；不再用无来源字符串代表公告或研报。
- `ResearchDocument`、`FilingDocument`、`CorporateEvent`：分别承载研报、监管/公司申报和解禁/分红/财报日历，不混成新闻。
- `FundamentalSnapshot`、`StatementSeries`、`ConsensusForecast`：保留财期、币种、单位、TTM/年度/季度口径和 restatement 状态。
- `CapitalFlowSeries`、`OwnershipSnapshot`、`TradingAnomaly`、`AttentionSignal`：区分资金算法、股东事实、交易异常和关注度，避免形成一个不可解释的“资金分”。
- `MacroObservation`、`DerivativeChainSnapshot`：市场级和衍生品数据独立建模，不扩张 `StockDossier` 的核心字段。

Provider 也应按能力拆分为 `QuoteProvider`、`BarProvider`、`DocumentProvider`、`FundamentalProvider`、`EventProvider`、`FlowProvider`、`MacroProvider` 和 `DerivativeProvider`，由 registry 按市场、许可开关、优先级和健康状态选择主备；不要再发展一个包含全部方法的巨型 `PublicMarketProvider`。

## 目标集成架构

`architecture` 技能在本报告中采用 Steel Blue 数据管线布局。虚线/灰色阶段代表外部或受许可约束的数据；蓝色阶段是 StockTs 自有边界；所有浏览器流量仍只进入 `/api/v1/*`。

<div style="width: 1200px; box-sizing: border-box; position: relative; background: #f0f4f8; padding: 20px; border-radius: 8px; border: 1px solid #c8d6e5;"><style scoped>.stock-arch-title{text-align:center;font-size:21px;font-weight:bold;color:#1a365d;margin-bottom:16px;font-family:Georgia,serif}.stock-arch-pipeline{display:flex;gap:0;align-items:stretch}.stock-arch-stage{flex:1;padding:13px;border:2px solid #3b82f6;border-radius:6px;background:linear-gradient(135deg,#dbeafe 0%,#bfdbfe 100%);box-shadow:0 1px 4px rgba(30,58,138,.08)}.stock-arch-stage.external{background:linear-gradient(135deg,#edf2f7 0%,#e2e8f0 100%);border:2px dashed #8da3bd}.stock-arch-stage.data{background:linear-gradient(135deg,#ecfdf5 0%,#d1fae5 100%);border-color:#10b981}.stock-arch-stage.logic{background:linear-gradient(135deg,#e0e7ff 0%,#c7d2fe 100%);border-color:#6366f1}.stock-arch-stage-title{font-size:12px;font-weight:bold;color:#1e3a5f;text-align:center;margin-bottom:9px}.stock-arch-box{border-radius:4px;padding:7px;text-align:center;font-size:10px;line-height:1.35;color:#1e293b;background:#fff;border:1px solid #cbd5e1;margin:4px 0}.stock-arch-box.highlight{border:2px solid #2563eb;background:#eff6ff;font-weight:700}.stock-arch-arrow{display:flex;align-items:center;justify-content:center;width:28px;flex-shrink:0;font-size:20px;color:#64748b}.stock-arch-governance{display:grid;grid-template-columns:repeat(5,1fr);gap:7px;margin-top:12px;padding:10px;border:2px solid #7c3aed;border-radius:6px;background:linear-gradient(135deg,#f5f3ff 0%,#ede9fe 100%)}.stock-arch-governance div{text-align:center;font-size:10px;color:#4c1d95;background:#fff;padding:7px;border:1px solid #c4b5fd;border-radius:4px}</style><div class="stock-arch-title">StockTs 多市场证据管线</div><div class="stock-arch-pipeline"><div class="stock-arch-stage external"><div class="stock-arch-stage-title">外部能力源</div><div class="stock-arch-box">CN：腾讯 / 新浪 / 巨潮 / 财联社</div><div class="stock-arch-box">HK/US：腾讯 / 新浪 / Yahoo / 东财</div><div class="stock-arch-box">官方：SEC / Treasury / CFTC</div><div class="stock-arch-box">受限：FINRA / CBOE / Nasdaq</div></div><div class="stock-arch-arrow">→</div><div class="stock-arch-stage"><div class="stock-arch-stage-title">能力 Provider</div><div class="stock-arch-box">Quote + Bar</div><div class="stock-arch-box">Document + Fundamental</div><div class="stock-arch-box">Event + Flow</div><div class="stock-arch-box">Macro + Derivative</div></div><div class="stock-arch-arrow">→</div><div class="stock-arch-stage"><div class="stock-arch-stage-title">规范化与策略</div><div class="stock-arch-box highlight">InstrumentRef + EvidenceEnvelope</div><div class="stock-arch-box">市场日历 / 币种 / 单位</div><div class="stock-arch-box">主备选择 / 限速 / 熔断</div><div class="stock-arch-box">许可与持久化策略</div></div><div class="stock-arch-arrow">→</div><div class="stock-arch-stage data"><div class="stock-arch-stage-title">缓存与分析</div><div class="stock-arch-box">SQLite 规范快照 + TTL</div><div class="stock-arch-box">能力级健康与审计</div><div class="stock-arch-box">现有 deterministic analysis</div><div class="stock-arch-box">证据覆盖 / 缺失 / stale</div></div><div class="stock-arch-arrow">→</div><div class="stock-arch-stage logic"><div class="stock-arch-stage-title">API 与产品</div><div class="stock-arch-box highlight">FastAPI /api/v1/*</div><div class="stock-arch-box">今日 / 大盘 / 机会</div><div class="stock-arch-box">个股 / 问股</div><div class="stock-arch-box">持仓 / 跟踪 / 数据</div></div></div><div class="stock-arch-governance"><div>来源归属与许可等级</div><div>观察/抓取/过期时间</div><div>按 host 请求预算</div><div>fixture 与字段漂移告警</div><div>不把缺失静默写成 0</div></div></div>

## API 与缓存边界

- 保留 `/api/v1/stocks/{symbol}` 作为兼容的组合 dossier；新增通用 `/api/v1/instruments/*`，避免继续用 `stocks` 表达 ETF、指数和期权标的。
- 读接口建议为：`/instruments/search`、`/{id}/quote`、`/{id}/bars`、`/{id}/evidence`、`/{id}/fundamentals`、`/{id}/filings`、`/{id}/events`、`/{id}/positioning`；市场接口使用 `/markets/{CN|HK|US}/signals|macro|calendar|screens`。
- 问股和页面优先读取规范化缓存；只有缓存缺失或过期时才通过 service 触发一个有预算的刷新。浏览器永远不接触 Yahoo crumb、SEC 联系信息或第三方域名。
- SQLite 快照 key 至少包含 `capability + market + instrument + period`；增加 TTL、解析版本、来源和最近错误。高频逐笔、全文 PDF、B/C 级原始载荷默认不落盘；只保存产品需要的规范字段和来源引用。
- 数据状态从“provider ready”升级为“capability/provider/market”三维状态，并展示最近成功时间、连续失败、缓存年龄、限流余量和许可开关。

## 分批交付 Backlog

### Epic 0：多市场与证据基础

依赖：无。范围：`InstrumentRef`、`SourceRef`、严格证据模型、能力型 provider protocol、registry、TTL 缓存、按 host 限速、能力级健康状态。

验收：现有 A 股 API 向后兼容；同一代码不会跨市场误解析；缺失/故障/过期状态可区分；任何证据都能回溯来源与观察时间；单元测试覆盖字段漂移、空载荷和主备切换。

### Epic 1：A 股公司证据包

依赖：Epic 0。范围：巨潮公告、东财研报元数据、公司资料/财务快照、解禁与分红；接入个股、问股、持仓和跟踪。

验收：个股页不再笼统显示“公告研报缺失”；每条证据带日期、来源、链接和 freshness；公告/研报不直接改变技术评分；持仓和跟踪能显示临近风险事件。

### Epic 2：A 股市场情报增强

依赖：Epic 0。范围：财联社快讯备源、板块资金、题材归属、龙虎榜统计；后续可选市场微结构。

验收：东财快讯失败时事件雷达仍有明确备源或 unavailable；板块资金能进入大盘证据覆盖；机会策略只有在所需数据完整时才启用；所有供应商算法字段标明来源。

### Epic 3：港美个股研究

依赖：Epic 0。范围：港美搜索、报价、日线、市场/币种/时区切换，以及个股和跟踪复用现有技术分析。

验收：`AAPL`、`HK.HKEX.00700` 可搜索并打开；交易日和夏令时正确；OHLCV 缺少 amount 时不写 0；CN/HK/US 快照和 regime 不混算；C 级源默认只在内部研究配置启用。

### Epic 4：SEC 美股研究层

依赖：Epic 0、Epic 3 的 instrument/CIK 映射。范围：submissions、companyfacts、每日申报、全文检索和 frames。

验收：10-K/10-Q/8-K/Form 4 可追溯 accession；真实 UA 由环境变量配置且全局低于 8 QPS；instant/duration XBRL 口径被测试；frames 首版只作基本面筛选，不静默改变现有评分。

### Epic 5：事件驱动跟踪与问股

依赖：Epic 1 或 4。范围：公告/申报/财报/解禁提醒、证据变化时间线、问股引用证据缓存。

验收：跟踪项能回答“加入后发生了什么”；问股答案引用具体来源和日期；刷新失败保留用户问题与旧证据并标记 stale；不同账户的提醒和持仓上下文隔离。

### Epic 6：多币种持仓

依赖：Epic 3；另需明确 FX 来源与许可。范围：持仓币种、成本币种、FX 快照、港股每手股数、美股碎股、按币种和折算币种的组合视图。

验收：没有 FX 时只显示币种分桶且不生成跨币种调仓；FX 有来源和时间点；港股调仓遵守每手股数；组合分析不会把 HKD/USD 当 CNY 直接相加。

### Epic 7：受许可的定位与衍生品

依赖：Epic 0、产品价值验证和许可确认。范围：FINRA short volume、CBOE 期权、Nasdaq 财报日历、A 股 ETF 期权或热榜。

验收：每项能力都有书面许可决策和功能开关；short volume 不被表述为 short interest；期权数据不输出自动交易指令；未授权环境 API 明确返回 unavailable 而非空数组。

## 建议的只读集成方案

```text
第三方端点
  -> backend/src/marketdesk/providers/global_market/（请求、限速、解析、主备切换）
  -> 严格 Pydantic 市场契约（market/exchange/currency/timezone/delay/source）
  -> Store 快照缓存（原始载荷不长期落盘；规范化结果可审计、可 stale 回退）
  -> backend/src/marketdesk/analysis/（继续使用 StockTs 自己的确定性计算）
  -> /api/v1/*（浏览器不接触第三方域名、cookie 或 SEC 联系信息）
```

### Phase 0：契约与开关

- 新增市场枚举 `CN/HK/US`、交易所、币种、交易所时区、报价类型 `realtime/delayed/eod`。
- 采用显式规范符号：建议 `US.NASDAQ.AAPL`、`HK.HKEX.00700`，不要把东财 `105/106/116` 或 Yahoo `.HK` 暴露到业务层。
- provider 配置必须按源独立开关；默认关闭所有 C 级源。把 SEC 联系信息放环境变量，不写死在源码。
- 每个 provider 都输出 `observed_at`、`fetched_at`、`source`、`freshness`、`coverage`、`errors`，失败时抛 `ProviderUnavailable`，禁止以 `{}`/`[]` 静默伪装成“无数据”。

### Phase 1：按标的港美报价与 K 线（内部研究 MVP）

- **报价**：港股腾讯主、 新浪备；美股新浪主、腾讯备。先不使用东财全市场列表，避免全量请求和字段缩放问题。
- **K 线**：美股新浪主、Yahoo 备；港股 Yahoo。明确标记此阶段依赖 C 级源，只允许内部研究部署。
- 使用 `httpx.AsyncClient`、按 host 的速率桶、有限重试、指数退避、熔断和请求合并；不复制仓库中的同步全局 session。
- 用固定真实响应 fixture 覆盖：美股/港股字段长度、GBK 解码、空字段、币种、市值单位、港股成交量小数文本、夏令时、非交易日、symbol/name 回验。
- 只做用户打开标的时按需刷新；不要每 2 小时轮询 18,000+ 港股和数千美股。
- 首版只进入搜索、个股研究和跟踪清单；不进入 A 股“大盘/机会”漏斗，也不生成跨币种组合汇总与调仓建议。

### Phase 2：SEC 官方美股研究层

- 接入 ticker-CIK、submissions、companyfacts、daily filings、fulltext search、frames。
- 将 Filing/XBRL 作为研究证据维度，不直接改变现有技术评分；XBRL 横截面先做单指标筛选，明确标签口径与覆盖率。
- SEC 统一 8 QPS 以下、真实 UA、缓存 ticker-CIK；保留 accession URL、form、filed/end/fy/fp 等审计字段。
- 这是最适合公开/商业方向优先做的部分，但仍需项目自行复核 SEC 最新访问政策。

### Phase 3：条件式增强

- **可评估**：Treasury 收益率曲线、CFTC COT；二者作为市场环境证据。
- **需许可确认后再做**：FINRA short volume、Nasdaq 财报日历。
- **需明确授权后再做**：CBOE 期权链/Greeks/0DTE。
- **暂缓**：Yahoo/东财的分析师、机构持仓、资金流、新闻、全市场批量列表；先证明产品价值和许可路径。
- **不做**：HKEX CCASS 自动抓取。

## 可直接借鉴与不可直接复用

### 可借鉴

- 多源优先级和不同风控面的降级设计；
- 明确区分 `DataNotAvailable`、配置错误、网络错误、限流/封禁；
- SEC 真实 UA、按域名限速、403 内容判别；
- 腾讯美股/港股分开字段表、市场代码映射与长度守卫；
- CBOE OCC 代码解析、SEC instant/duration 周期识别等边界案例；
- 将来源、观察时间、抓取时间、覆盖度和错误贯穿 API。

### 不可直接复用

- 整份 `SKILL.md` 作为运行时依赖或 prompt 自动执行；
- 同步 `requests` 函数、模块级可变 session/缓存、硬编码联系人；
- 未经许可的 C/B 级数据用于公开商业产品或再分发；
- 用空 dict/list 代表上游故障；
- 用 0 填充未知成交额、价格或指标；
- 外部仓库的技术指标/交易信号替代 StockTs 的确定性 `analysis/`；
- 自动抓取 HKEX CCASS。

## 推荐决策

**可以用，但要把“用这个项目”理解为：基于固定提交中的接口研究，重写成 StockTs 自己的只读 provider，并按上游许可分级启用。**

推荐优先级：

1. 先改市场/币种/时区/缺失值契约；
2. 内部研究开关下接港美按标的报价与 K 线；
3. 接 SEC Filing/XBRL/frames，形成美股差异化研究能力；
4. 再决定是否为港股商业数据采购持牌源；
5. CBOE、FINRA、Nasdaq、Yahoo/东财批量能力在许可明确前不进入公开生产。

这个顺序能最大限度复用 StockTs 现有 provider、快照、freshness 和确定性分析框架，同时避免把一份便于 AI 复制的接口清单误当成稳定数据基础设施。

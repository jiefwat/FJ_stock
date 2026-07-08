# Architecture

## 项目形态

- 类型：`mixed`，当前以 Python CLI + 可选 Streamlit Dashboard 为主。
- 治理等级：`standard`，遵循 `yqn-dev-skills` 的 `AGENTS.md`、`docs/superpowers/`、`src/`、`tests/` 结构。
- 包名：`stock_ts`。

## 分层边界

```text
CLI / Dashboard
  -> workflow orchestration
  -> analysis services
  -> local imports / notification
  -> provider adapters
  -> external data sources / local cache
  -> report renderer
```

- `src/stock_ts/workflows.py`：CLI/Web 共用服务编排层，统一 provider、analysis、report 流程。
- `src/stock_ts/cli.py`：命令行参数解析、报告输出路径处理，不承载复杂业务规则。
- `src/stock_ts/web.py`：轻量本地 Web 投研工作台，无需额外依赖；使用任务式左侧导航、侧边栏快速个股搜索、全局数据状态条、今日行动台、证据链抽屉、模块卡片、表格、评分条和风险标签，不直接堆叠 Markdown。
- `src/stock_ts/dashboard.py`：可选 Streamlit 入口，默认不启用。
- `src/stock_ts/portfolio.py`：读取本地持仓 CSV，或从交易流水 CSV 按移动加权成本生成当前持仓模型。
- `src/stock_ts/portfolio_advice.py`：组合建议层，基于组合分析、大盘状态、集中度、行业暴露和持仓盈亏输出总体动作、目标现金仓位、每只持仓的目标仓位、调整金额、止损、止盈观察和持仓添加说明。
- `src/stock_ts/imports.py`：读取本地行情 CSV 与新闻舆情 CSV，作为真实数据源未稳定前的导入通道。
- `src/stock_ts/news.py`：新闻舆情的正面/负面/中性聚合与风险提示。
- `src/stock_ts/news_fetcher.py`：外部新闻接口适配，当前支持 AKShare 东方财富个股新闻，并复用情报分类器标记正负面。
- `src/stock_ts/announcements.py`：CNInfo/巨潮公告抓取、公告/财报事件摘要和标题风险标签识别，用于补齐基本面和公告事件入口。
- Web 首屏默认不实时请求巨潮公告，避免外部接口超时拖慢页面；如需页面加载时实时抓取，可设置 `STOCK_TS_WEB_LIVE_ANNOUNCEMENTS=1`。日常公告建议由定时流水线预先写入日报产物。
- `src/stock_ts/symbols.py`：轻量股票名称/代码解析，先覆盖常用标的和当前验证标的，避免中文名称被当作代码查询。
- `src/stock_ts/data_sources.py`：多源数据能力矩阵，统一展示 Tencent、AKShare、TDX MCP 快照、本地导入、CNInfo skill、AgentReach skill 和计划数据源的覆盖范围、限制与接入方式。
- `src/stock_ts/data_quality.py`：多源行情质量摘要，记录主源、失败源、缺失字段和质量等级，避免把降级数据伪装成完整数据。
- `src/stock_ts/realtime_quotes.py`：统一实时行情 quote 类型和 fallback 管理器，后续 Tencent、TDX、AKShare、iTick 实时接口统一接入。
- `src/stock_ts/news_intelligence.py`：实时新闻/情报源轻量层，支持 JSON 新闻源、URL 去重、风险/催化分类和 fail-open 状态。
- `src/stock_ts/analysis.py`：大盘、个股和持仓分析规则，输入领域模型，输出分析模型。
- `src/stock_ts/deep_models.py`：深度分析领域模型，集中放置多角度、潜力观察、对抗轮次、单股/批量/每日深度报告的数据结构。
- `src/stock_ts/deep_analysis.py`：深度分析规则层，组合市场、板块、舆情、持仓和个股基础报告，输出多角度评分、未来上涨潜力观察分和 TradingAgents 式多角色对抗；最终结论必须由个股自身优势、主要矛盾、动作倾向和失效条件组合生成，禁止只按分数档位输出固定套话；保留旧渲染函数 re-export，兼容已有调用方。
- `src/stock_ts/deep_report.py`：深度分析 Markdown 渲染层，负责单股、批量和每日深度复盘文本输出，并对缺失对抗轮次做防御性兜底。
- `src/stock_ts/research_playbook.py`：专业研究仪表盘层，组合深度个股、大盘、板块、持仓、候选池和数据质量，输出策略透镜、研究团队分工、数据块完整性、观察点位和交易纪律。
- `src/stock_ts/research_run_card.py`：研究运行卡层，参考 Vibe-Trading / Vibe-Research / Longbridge 类产品的“目标-证据-动作-边界”范式，把日报和流水线状态压缩成可审计的盘前任务卡；坚持只读研究和纸面推演，不接真实下单。
- `src/stock_ts/professional_research.py`：单股专业研究附录层，输出支撑/压力/失效线、均线、RSI、MACD、量能比、盘口技术结构、公告事件雷达和复核动作；Web 和 CLI `research` 复用。
- `src/stock_ts/trade_plan.py`：明确操作计划层，把深度分析、技术结构、公告事件和数据质量转换成当前动作、目标仓位、买入/加仓触发、止损/减仓触发、止盈计划、禁止动作和盘中执行清单。
- `src/stock_ts/llm.py`：可选大模型增强层，使用 OpenAI-compatible chat completions 接口；无 Key 时输出降级说明，有 Key 时在结构化分析基础上生成 AI 研报。
- `src/stock_ts/watchlist.py`：自选股研究工作台，读取轻量 YAML-like 清单，沉淀研究假设、标签、价格/评分提醒，并复用深度分析生成观察排序。
- `src/stock_ts/backtest.py`：轻量策略验证层，当前支持本地日线 CSV 的 MA 均线回测，输出收益、买入持有对照、最大回撤、胜率、交易明细和限制说明。
- `src/stock_ts/indicators.py`：均线、涨跌幅、波动率等可测试指标函数。
- `src/stock_ts/models.py`：领域数据结构，避免业务层直接依赖外部 SDK 字段。
- `src/stock_ts/providers/`：数据源适配层。AKShare、Tushare、pytdx、缓存都应在此收敛。
- `src/stock_ts/report.py`：Markdown 报告渲染，统一免责声明和章节结构。
- `src/stock_ts/html_report.py`：单文件 HTML 结论页渲染，不依赖 CDN，供本地打开、归档和后续通知外发复用。
- `src/stock_ts/output.py`：文本写文件工具，供 CLI 等入口复用，避免各命令重复处理目录创建和编码。
- `src/stock_ts/notification.py`：邮件 SMTP、企业微信 Webhook、飞书 Webhook 外发，以及按渠道切换 full/digest/action 报告样式；凭证只从本地环境读取。

## 数据源策略

- `sample`：离线样例数据，用于 smoke test、演示和无网络环境；Web 会显式标记为示例数据，避免误认为真实行情。
- 本地 CSV 导入：用于导入已有行情、手工整理新闻、第三方导出的舆情列表；不依赖网络。
- `tencent` / `auto`：无额外依赖的腾讯行情源，当前用于较新的 A 股指数、个股 quote 与日线 K 线；板块和候选池暂时使用 sample 兜底并通过 Web 数据质量模块提示来源边界。
- `eltdx`：通过 `python3.11` 桥接 `eltdx` MCP/TDX 能力，补最新 quote、日线、题材和主题轮动；为避免公开 Web 首屏被桥接超时拖慢，`auto` 默认优先使用 Tencent，只有设置 `STOCK_TS_AUTO_PREFER_ELTDX=1` 时才优先使用它。
- `tdx-snapshot`：面向 TDX MCP/通达信服务的本地 JSON 快照 provider；Codex 会话可用 MCP 查行情，项目运行时读取落地后的 `data/imports/tdx_snapshots.json`，避免业务代码直接依赖聊天工具。Web 工作台固定使用该源，缺少大盘、板块、候选池或个股快照时直接报错，不用 sample 伪装真实行情。全市场智能选股通过 `scripts/refresh_tdx_snapshot.py --quote-only` 先扫描全市场行情分页，再写入预筛候选和扫描元数据；深度数据通过 `--enrich-existing` 对现有候选前排补真实日线和主题；K 线、估值、资金流和新闻通过 `scripts/enrich_tdx_snapshot.py` 先写回快照。页面必须展示扫描总数、预筛数量、深度补强数量、资金抱团/市场热度/超跌反弹/风险排查等策略分层和口径限制。
- 板块主题口径：页面里的“板块/方向/主题”必须是行业、概念或题材，如白酒、商业航天、通用设备、机器人概念；不得把创业板、科创板、沪市主板、深市主板等交易板当作板块主题。TDX 主题缺失时显示“未识别主题”或跳过聚合，不用交易板兜底。
- `akshare`：首个真实数据源适配，依赖 `akshare` 包；当前支持指数/个股、行业板块、候选池和个股新闻。全市场 spot 失败时大盘降级为指数行情，候选池回退到行业板块成份；外部接口全部不可用时使用 sample 兜底并输出 warning。
- `tushare`：A 股日线 K 线主源，适合财务、资金流、指数成分、交易日历；`scripts/refresh_a_share_kline.py` 会在盘后流水线里优先用 Tushare `daily` 刷新持仓和候选池日线，港股等非 A 股必须跳过并记录，不用错误 K 线兜底。
- `itick`：可选 HTTP API 补强源，配置 `ITICK_API_KEY` 后用于快照脚本补 A股/港股/美股报价和 K 线；当前不提供估值、新闻、基本面和资金流，A股代码格式需用真实 Key 持续校验。
- `pytdx`：后续补充实时/盘口类数据。
- 本地缓存：已提供 `JsonCacheStore` 作为最小无依赖缓存；下一阶段建议用 SQLite 存元数据、Parquet 存日线和全市场快照。

## 板块主题备用源

当 TDX 主题不准、取不到或覆盖率过低时，后续 provider 应先在 `providers/` 增加二源校验，不要在 Web 层临时抓取：

- AKShare（https://github.com/akfamily/akshare）：优先补东方财富概念/行业板块接口，用于概念名称和成份校验。
- efinance（https://github.com/Micro-sheep/efinance）：可作为轻量行情与东方财富数据补充源。
- pytdx（https://github.com/rainx/pytdx）：可作为通达信协议级补充源，适合继续补板块、行情和本地缓存链路。

## 错误处理

- 数据源不可用时抛出 provider 层异常，不在分析层吞掉错误；Web 层展示可读错误页和下一步处理建议。
- Web 层必须展示请求源、实际 Provider、个股行情日期、大盘交易日和数据质量告警；样例或降级数据不能伪装成真实专业分析。
- Web 数据质量页必须读取 `reports/daily/pipeline.status`，展示自动更新最近运行、每 2 小时刷新节奏、分步骤结果和处理建议，避免旧数据被误认为当天数据。
- 分析层只接收标准领域模型，缺失数据由 provider 或 orchestration 层处理。
- 报告必须保留“不构成投资建议”免责声明。
- 未来上涨相关输出必须使用“观察分、潜力、情景、失效条件”等表述，不能承诺确定收益或明日必涨。
- 操作计划可以给出明确动作、仓位和价格触发线，但必须基于条件和失效规则，不能承诺收益或无风险交易。
- 大模型 Key 只能来自环境变量或本地 `.env`，报告、日志、doctor 和错误信息不得输出真实 Key。
- LLM 失败不能阻断规则分析报告，必须降级为可读说明。
- 通知外发默认先用 `send-daily --dry-run` 或 Web 单渠道测试验证；真实发送不得在日志或页面暴露 token、授权码、Webhook 完整地址。

## 测试策略

- 单元测试覆盖分析规则、报告结构和 CLI 输出。
- 数据源测试优先使用 sample provider；真实数据源放入 integration 测试，避免日常测试依赖网络。
- 每次修改分析口径时同步更新 `docs/superpowers/<requirement>/test.md`。
- 深度分析新增能力必须至少覆盖：单股多角度、批量排序、多轮对抗、HTML 结构、CLI 烟测。
- 专业单股研究包必须覆盖：技术结构、公告事件、持仓/风控复核动作和 Web 可见性；公告接口不可用时要安全降级，不能阻断核心行情分析。
- watchlist/backtest 类研究工作流必须保持离线可用，不能依赖真实行情接口才能通过测试。
- LLM 集成必须覆盖：无 Key 降级、configured/missing 安全摘要、Key 不出现在输出、CLI 烟测。


## 持仓输入

当前使用本地 CSV，不接券商账户。支持两种输入：

```text
data/portfolio/holdings.csv
data/portfolio/transactions.csv
```

持仓快照字段：`code,name,shares,cost_price,sector,note`。

Web 页面会直接展示默认持仓文件路径和表头；CLI `portfolio` 会在 Markdown 报告中追加“我的持仓在哪添加”和“组合整体建议”。

开启账号体系后，账号只隔离个人持仓账本：每个登录用户自动使用 `data/auth/users/<user_id>/holdings.csv`，首次访问只创建空 CSV 表头，不复制站长或默认持仓；行情、板块、智能选股、日报产物、通知配置和系统数据仍保持全站一致。开启账号体系时，页面和表单里的 `holdings` / `holdings_path` 参数不再决定写入位置，服务端会按当前登录用户重定向到其专属持仓文件，避免不同账号互相覆盖。

交易流水字段：`date,code,name,side,shares,price,fee,tax,sector,note`。`side` 支持 `buy/sell`、`买入/卖出`。使用交易流水时，系统按移动加权成本生成当前持仓，适合逐步升级为组合账本；当前版本暂不把手续费、印花税纳入成本，也不计算已实现盈亏。

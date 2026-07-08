# StockTS 股票分析系统优化重构交接文档

> 面向接手 agent：请先读本文件，再读 `README.md`、`TODO.md`、`plan.md`、`docs/architecture/README.md` 和 `tests/`。本文件记录上一轮调研结论、系统设计方向、已完成改动和后续重构建议。

## 1. 项目目标

把 StockTS 从一个样例 CLI 项目优化为“可用、能用、好用”的 A 股研究与复盘工作台。

核心目标：

- 可用：离线 sample 数据能稳定跑通全部主流程；真实 AKShare 数据源有清晰入口和错误提示。
- 能用：用户能通过 CLI 和本地 Web 页面完成大盘、个股、持仓、完整日报分析。
- 好用：报告结构清晰、指标解释可读、风险提示明确、页面有一眼可看的工作台体验。

项目边界：

- 不做自动交易。
- 不接券商账户。
- 不提交真实凭证、内部地址或线上配置。
- 不输出确定性收益承诺或无风险买卖建议。
- AI 只能作为结构化数据转文字的增强层，不能直接编造行情或替用户决策。

## 2. 调研结论

参考 `ZhuLinsen/daily_stock_analysis` 后，股票分析系统可以拆成以下能力包：

1. 数据获取：AKShare、Tushare、pytdx、sample 等数据源适配。
2. 数据缓存：SQLite 管元数据，Parquet 管日线、指数、市场快照。
3. 指标分析：MA、MACD、RSI、BOLL、ATR、成交量均线、涨跌幅、波动率。
4. 大盘复盘：指数趋势、市场广度、短线情绪、资金流、板块强弱、风险状态。
5. 个股分析：趋势、量能、指标、估值、资金、风险等级、后续观察点。
6. 持仓/自选股分析：仓位、盈亏、行业集中度、个股风险、市场主线匹配。
7. 报告渲染：Markdown、JSON、页面展示数据。
8. 展示页面：先用轻量本地 Web 或 Streamlit；成熟后再考虑 FastAPI + React。
9. AI 复盘：只基于结构化数据生成可审查文本，必须有 Prompt 契约和免责声明。

推荐路线：先做轻量工程版，不直接照搬 `daily_stock_analysis` 的完整产品化复杂度。

第一版目标架构：

```text
External Data Sources
  -> Provider Adapters
  -> Cache Layer
  -> Domain Models
  -> Indicators
  -> Analysis Services
  -> Report Renderer
  -> CLI / Local Web / Reports
```

## 3. 当前代码状态

上一轮已经推进了一部分实现，当前仓库还没有初始 commit，所有文件在 git 中仍是 untracked。接手 agent 不要以 git 历史判断改动归属，应直接按文件内容和测试结果判断。

已存在并应保留的主流程：

- `stock-ts market`：生成每日大盘分析。
- `stock-ts stock CODE`：生成单股分析。
- `stock-ts portfolio`：读取 `data/portfolio/holdings.csv` 生成持仓分析。
- `stock-ts daily`：生成大盘 + 持仓完整日报。
- `python -m stock_ts.web`：启动轻量本地页面，展示大盘、持仓、个股、完整日报。

关键文件：

- `src/stock_ts/models.py`：领域模型，已包含市场维度、持仓、组合分析模型。
- `src/stock_ts/indicators.py`：指标函数，已补 MA 基础函数、EMA、MACD、RSI、BOLL、成交量均线。
- `src/stock_ts/analysis.py`：大盘、个股、持仓分析逻辑。
- `src/stock_ts/portfolio.py`：本地持仓 CSV 读取。
- `src/stock_ts/report.py`：大盘、个股、持仓、完整日报 Markdown 渲染。
- `src/stock_ts/cli.py`：CLI 子命令入口。
- `src/stock_ts/web.py`：轻量本地 Web 工作台。
- `src/stock_ts/providers/sample.py`：离线样例数据。
- `src/stock_ts/providers/akshare_provider.py`：AKShare 数据源适配入口。
- `tests/test_portfolio_daily.py`：持仓、日报、页面主流程测试。
- `tests/test_indicators.py`：指标函数测试。
- `tests/test_analysis.py`：大盘和个股分析测试。

## 4. 已验证命令

上一轮已跑通过：

```bash
python3 -m pytest -q
PYTHONPATH=src python3 -m stock_ts.cli portfolio --provider sample --holdings data/portfolio/holdings.csv
PYTHONPATH=src python3 -m stock_ts.cli daily --provider sample --holdings data/portfolio/holdings.csv --output reports/daily-sample-check.md
```

接手后建议先重新跑：

```bash
make test
make lint
PYTHONPATH=src python3 -m stock_ts.cli market --provider sample
PYTHONPATH=src python3 -m stock_ts.cli stock 600519 --provider sample
PYTHONPATH=src python3 -m stock_ts.cli portfolio --provider sample --holdings data/portfolio/holdings.csv
PYTHONPATH=src python3 -m stock_ts.cli daily --provider sample --holdings data/portfolio/holdings.csv --output reports/daily/sample-full.md
```

如要启动页面：

```bash
PYTHONPATH=src python3 -m stock_ts.web
```

访问：`http://127.0.0.1:8501`

## 5. 下一步重构重点

### 5.1 先整理模型命名

当前模型里存在 `PositionAnalysis`、`PortfolioAnalysisReport` 等命名。建议保持兼容，不要大范围重命名导致测试和报告破裂。若要重命名，必须先加测试再迁移。

建议目标：

- 市场原始数据：`MarketRawData`
- 市场分析结果：`MarketSnapshot`
- 个股原始数据：`StockRawData`
- 个股分析结果：`StockAnalysisReport`
- 持仓输入：`Holding`
- 持仓分析项：`PositionAnalysis`
- 组合分析结果：`PortfolioAnalysisReport`

### 5.2 抽出 Orchestrator

当前 CLI 里直接编排 provider、analysis、report。后续可新增 `src/stock_ts/services.py` 或 `src/stock_ts/workflows.py`：

- `build_market_report(provider)`
- `build_stock_report(provider, code)`
- `build_portfolio_report(provider, holdings_path)`
- `build_daily_report(provider, holdings_path, stock_codes=None)`

这样 CLI、Web、后续 API 可以复用同一套流程。

### 5.3 强化 Provider 层

AKShare 真实接口字段可能变。建议：

- 给 provider 层增加字段兼容工具。
- AKShare 缺包时继续抛清晰 `DataProviderError`。
- 真实数据源测试放 integration，不进入日常测试。
- sample provider 必须覆盖所有主流程字段，保证离线演示稳定。

### 5.4 加缓存层

下一阶段最重要的是缓存：

```text
data/
  metadata.sqlite
  daily/{code}.parquet
  index/{code}.parquet
  market_snapshot/{date}.parquet
  sector_snapshot/{date}.parquet
```

建议先做最小缓存：

- 个股日线 Parquet 缓存。
- 市场快照 JSON 或 Parquet 缓存。
- 刷新记录存 SQLite。
- CLI 增加 `--refresh` 和 `--cache-dir`。

缓存必须在报告里标明：数据日期、数据源、缓存命中与否。

### 5.5 页面体验优化

当前 `web.py` 是标准库轻量页面，优点是无依赖、容易启动。下一步可以继续优化它，而不是马上上重前端：

- 增加导航锚点：大盘、持仓、个股、完整日报。
- 增加 provider 和 holdings path 查询参数。
- 增加清晰错误页面，避免接口失败时白屏。
- Markdown 区域增加复制提示。
- 卡片化展示核心指标，不只显示长 Markdown。

如果要做更强交互，再升级 Streamlit；如果要做产品级，再考虑 FastAPI + React。

### 5.6 报告可读性

报告应保持业务语言：

- 先结论，后证据。
- 每一节都要有风险提示。
- 指标不要只给数值，要给解释。
- 持仓分析要突出集中度、行业暴露、市场主线匹配。
- 所有报告保留“不构成投资建议”。

## 6. 建议实施顺序

请接手 agent 按 TDD 小步推进，不要一次性大改。

### Task A：服务编排层

目标：把 CLI/Web 共用流程抽出来。

建议新增：`src/stock_ts/workflows.py`

验收：

- 原 CLI 命令输出不变。
- `tests/test_cli.py` 和 `tests/test_portfolio_daily.py` 通过。

### Task B：页面错误处理与可用性

目标：页面即使持仓文件缺失、股票代码错误、provider 异常，也显示可读错误。

验收：

- 新增测试覆盖 `render_page` 对缺失 holdings 文件的处理。
- 页面包含错误提示和免责声明。

### Task C：缓存设计最小实现

目标：增加本地缓存接口，不一定一口气接真实 AKShare。

建议新增：

- `src/stock_ts/cache.py`
- `tests/test_cache.py`

验收：

- 可写入/读取个股日线缓存。
- 可记录数据源和刷新时间。
- 不破坏 sample provider。

### Task D：AKShare 实测与字段兼容

目标：真实数据源能跑通基本命令。

验收：

```bash
python3 -m pip install -e '.[data]'
PYTHONPATH=src python3 -m stock_ts.cli market --provider akshare
PYTHONPATH=src python3 -m stock_ts.cli stock 600519 --provider akshare
```

注意：真实接口失败时不要让测试依赖网络；integration 测试需要显式开关。

### Task E：日报进一步好用

目标：日报适合每天复制到微信/文档。

建议：

- 增加“今日一句话”。
- 增加“最需要关注的 3 件事”。
- 增加“持仓风险 Top 3”。
- 降低重复免责声明，只保留顶部和底部即可。

## 7. 测试要求

必须坚持：先写失败测试，再实现。

日常验证：

```bash
make lint
make test
```

主流程 smoke：

```bash
PYTHONPATH=src python3 -m stock_ts.cli daily --provider sample --holdings data/portfolio/holdings.csv --output reports/daily/sample-full.md
PYTHONPATH=src python3 -m stock_ts.web
```

不要让普通测试依赖网络、AKShare、Tushare token 或真实交易日。

## 8. 风险提示

- 当前仓库没有初始 commit，提交前要先确认用户是否希望一次性纳入全部文件。
- `reports/` 下可能有生成物，提交前需要判断哪些是样例资产，哪些是临时验证产物。
- `akshare` 接口字段和返回结构可能变化，不要在分析层直接依赖中文列名。
- 页面端不要吞异常，要把“哪个数据源失败、下一步怎么处理”展示给用户。
- 所有分析文案必须避免“必涨、稳赚、无风险、强烈买入”等确定性表达。

## 9. 给接手 agent 的一句话方向

请把 StockTS 优化成一个稳定、可测试、可本地使用的 A 股复盘工作台：先保证 sample 全流程永远可用，再让 AKShare 真实数据可用；先让 CLI 和轻量 Web 好用，再考虑缓存、AI 和重前端。

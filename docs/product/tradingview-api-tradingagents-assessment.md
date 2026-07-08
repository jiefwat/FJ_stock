# TradingView-API 与 TradingAgents 评估

更新时间：2026-07-08

## Mathieu2301/TradingView-API 是否可用

结论：可以作为 StockTS 的可选增强源，但不建议作为 A 股主数据源。

适合使用的场景：

- 补全球市场、港美股、指数、Crypto 的实时观察价。
- 补 TradingView 技术分析、公开 Screener、Hotlists、Calendar。
- 用 Node.js 桥接到 Python，把结果写入本地快照，再由 Web 读取。

不适合作为主源的原因：

- 它是 JavaScript / TypeScript 生态，StockTS 当前主链路是 Python，需要额外 Node 桥接进程。
- 依赖 TradingView 非官方接口和 socket 行为，稳定性、限频、登录态、Premium 权限都可能变化。
- A 股代码、交易所映射、复权、涨跌停、板块主题、公告和资金流仍需要 TDX/Tushare/AKShare 这类本地化数据源校验。
- 不能把 TradingView 返回值直接当“权威事实”，必须进入 StockTS 的 data quality gate。

建议接入方式：

1. 新增 `scripts/tradingview_bridge.js`，只负责拉 quote / TA / screener，不直接服务 Web。
2. 新增 `scripts/enrich_tradingview_snapshot.py`，调用 Node 桥接并写入 `data/imports/tradingview_snapshot.json`。
3. Provider 层只读取本地 JSON 快照，不在页面请求时实时访问 TradingView。
4. 页面和邮件只展示“TradingView 补强：成功/失败/部分成功”，不能伪装成主源。

## TauricResearch/TradingAgents 可迁移的方法

TradingAgents 的核心不是某个指标，而是投研组织方式：

1. Analyst Team：基本面、情绪/新闻、技术分析分别给证据。
2. Researcher Team：多头和空头研究员互相反驳。
3. Trader：把研究结论转成条件化执行方案。
4. Risk Manager：先定义风险、失效条件和降级机制。
5. Portfolio Manager：最后从组合暴露角度批准或拒绝。

StockTS 不做真实交易，因此只迁移“思考方法”，不迁移自动下单：

- Analyst Team -> `DeepStockReport.debate_rounds` 中的技术分析师、基本面分析师、新闻情绪分析师。
- Researcher Team -> 多头研究员、空头研究员。
- Trader -> 条件化执行清单，只说触发/不触发。
- Risk Manager -> 失效条件和风险降级。
- Portfolio Manager -> 组合仓位、持仓影响、总风险预算。

## 已落地

`src/stock_ts/deep_analysis.py` 的多轮对抗已从旧三段式：

- 多头观点
- 空头观点
- 裁判结论

升级为 TradingAgents 式角色链：

- 技术分析师
- 基本面分析师
- 新闻情绪分析师
- 多头研究员
- 空头研究员
- 交易员
- 风控经理
- 组合经理

同时修复了旧结论的套话问题：

- 不再只按分数输出固定结论。
- 不再把市场环境当作个股优势。
- 不再把“未识别/未提供/暂无”当作优势。
- 结论必须包含优势、主要矛盾或待验证点、触发条件、失效条件。

## 后续建议

1. 先继续强化 TradingAgents 角色链和证据质量，不急着接 TradingView。
2. 如果接 TradingView，先做离线快照桥接，不做页面实时请求。
3. TradingView 只作为增强源；A 股主源仍保持 TDX/Tushare/AKShare 组合。
4. 所有外部数据都要进入 `research_run_card` 的数据质量闸门。

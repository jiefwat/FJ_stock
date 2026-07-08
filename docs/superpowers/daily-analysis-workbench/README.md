# Daily Analysis Workbench

## 目标

把 StockTS 从样例大盘/个股报告升级为每日复盘工作台，覆盖每日大盘多维分析、每日持仓分析、报告输出和轻量 Web 页面展示。

## 范围

- 每日大盘分析：指数、广度、情绪、资金、板块、风险、明日观察点。
- 每日持仓分析：收益、仓位、行业集中度、个股风险、与大盘关系、组合健康度。
- 本地持仓输入：`data/portfolio/holdings.csv`。
- 输出：CLI、Markdown 报告、轻量 Web 页面。

## 不做事项

- 不接券商账户。
- 不做自动交易。
- 不输出确定性买卖建议。
- 不要求 Streamlit 或大型 Dashboard 依赖。

## 验收方式

- `python3 -m pytest` 通过。
- `PYTHONPATH=src python3 -m stock_ts.cli portfolio --provider sample --holdings data/portfolio/holdings.csv` 输出持仓分析。
- `PYTHONPATH=src python3 -m stock_ts.cli daily --provider sample --holdings data/portfolio/holdings.csv --output reports/daily/sample-full.md` 生成完整日报。
- `PYTHONPATH=src python3 -m stock_ts.web` 页面展示大盘、持仓、个股和报告入口。

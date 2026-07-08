# Bootstrap Project: StockTS A股分析软件

## 目标

从空仓库初始化一个符合 `yqn-dev-skills` standard 治理结构的 A 股分析软件，首版覆盖每日大盘分析、个股分析、Markdown 报告输出和后续 Dashboard/真实数据源扩展边界。

## 不做事项

- 不做自动交易。
- 不输出确定性投资建议。
- 不提交真实 token、内部地址或生产配置。
- 不让核心分析逻辑直接依赖 AKShare/Tushare SDK 字段。

## 验收方式

- `PYTHONPATH=src python3 -m stock_ts.cli market --provider sample` 能输出大盘 Markdown。
- `PYTHONPATH=src python3 -m stock_ts.cli stock 600519 --provider sample` 能输出个股 Markdown。
- `python3 -m pytest` 通过。
- README、架构文档、TODO 与代码入口一致。

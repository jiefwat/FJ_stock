# Sector Candidate Workbench

## 目标

在每日复盘工作台中增加“每日板块情况”和“明日强势候选观察池 Top 20”，帮助用户从市场主线、板块强度、个股量价和风险维度做次日观察准备。

## 范围

- 板块分析：热度榜、持续性、资金活跃、轮动状态、风险提示。
- 候选票分析：输出 Top 20 明日观察候选，包含评分、所属板块、入选理由、风险点、观察条件。
- 输出入口：CLI、Markdown 日报、轻量 Web 页面。
- 第一版使用 sample 数据跑通结构，后续接 AKShare/Tushare 真实数据源。

## 命名与合规边界

- 功能命名为“明日强势候选观察池”，不称为确定性荐股。
- 不承诺明天上涨，不输出无风险买卖建议。
- 每只候选必须包含风险提示和观察条件。

## 验收方式

- `python3 -m pytest` 通过。
- `stock_ts.cli sectors --provider sample` 输出板块情况。
- `stock_ts.cli candidates --provider sample --limit 20` 输出 20 只候选观察票。
- 完整日报和页面包含板块情况、明日 Top20 候选观察池。

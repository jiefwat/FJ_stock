# 交付说明

## 目标

四个研究工作台在外部研究额度耗尽或网络失败时仍有可读、可核查的内容，并保持统一顺序：

`数据状态 -> 结论 -> 动作 -> 风险 -> 三条依据 -> 模块内容 -> 完整依据`

## 关键实现

- `src/stock_ts/research_fallback.py`：四模块本地证据适配器。
- `src/stock_ts/research_delivery.py`：快照、实时、历史和本地证据交付顺序。
- `src/stock_ts/web.py`：认证持仓路径注入和本地 Provider 接入。
- `src/stock_ts/webapp/engine_workspace.py`：数据状态、降级原因和刷新保留。
- `src/stock_ts/webapp/styles.py`：实时、快照、本地、历史和缺失状态样式。

## 运维约束

- 公网代码目录：`/opt/stock-ts`。
- 只重启 `stock-ts.service`。
- 必须保留 `.env`、`.secrets`、`data`、`reports`、认证数据库、私有持仓和 `.deploy_backups`。
- `stock-ts-daily-research.timer` 和 `stock-ts-daily-analysis.timer` 不重启、不禁用。
- 部署后必须确认 GitHub、本地独立分支和服务器提交一致，确认 `main` 仍为改造前基线，并验证 `/healthz`、登录跳转和登录态四模块 API。

## 回滚

代码回滚到部署前提交并只重启 `stock-ts.service`；如果只需切回旧页面，可设置 `STOCK_TS_WEB_VERSION=legacy`。数据、账号、凭证和历史报告不随代码回滚。

## 公网交付

- 公网地址：`https://stock.jiewat-kaka-fj.com/`。
- 部署前源码备份：`/opt/stock-ts/.deploy_backups/always-visible-20260715-155740/source-before.tar`。
- 部署保留了服务器 `.env`、`.secrets`、`data`、`reports`、认证库、私有持仓和既有备份目录。
- 登录态四个研究接口和匿名健康检查均已验证。

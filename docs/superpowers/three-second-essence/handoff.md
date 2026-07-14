# 三秒精华版交接

## 当前状态

- 分支：`main`
- 工作树：`/Users/fangjie/.config/superpowers/worktrees/StockTs/main-research-integration`
- 原始脏工作树 `/Users/fangjie/Documents/StockTs` 未修改。
- 四工作台实现、专项测试、全 Web 测试、全量 Ruff、桌面/移动端验收、公网部署和生产数据刷新均已完成。
- 公网入口：`https://stock.jiewat-kaka-fj.com/`。

## 展示契约

- 大盘：结论、动作、最大风险；轨道、情景、维度和行情证据折叠。
- 持仓：组合结论、动作、最大风险、最多 3 只优先处理；指标、暴露、完整队列和边界折叠。
- 个股：投资判断、动作、失效条件、最多 3 条事实且含反证；完整档案折叠。
- 机会：机会闸门、动作、最大风险、最多 3 只候选；漏斗、风险、其余候选和来源折叠。
- 问财：四页均为同级的“问财核查 · 按需展开”，默认关闭且不自动调用。

## 部署边界

- 只允许快进服务器 `/opt/stock-ts` 的 `main`。
- 必须保留 `.env`、`.secrets`、`data`、`reports`、认证和持仓数据。
- 只重启 `stock-ts.service`；部署后复核 StockTS、Signal Desk 和 Nginx。
- 禁止在输出、日志或提交中回显 `IWENCAI_API_KEY`。

## 部署记录

- 运行代码提交：`1e40f2893fe44644de426eade1aa38cbf9a3c2b7`。
- 回滚包：`/opt/stock-ts/.deploy_backups/three-second-essence-20260714-175255/source-before.tar.gz`。
- StockTS、Signal Desk、Nginx、日报定时器和公网 `/healthz` 均正常。
- 根路径保持登录保护；匿名问财返回 `401 login_required`。
- 生产刷新状态为 `ok`，交易日 `2026-07-14`，数据链七个步骤全部为 `ok`。

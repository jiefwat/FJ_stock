# Handoff

## 当前状态

四模块技能路由、通用 endpoint、共享研究坞、四页接入、响应式布局、代码审查、本地验证和公网部署均已完成。

公网入口：`https://stock.jiewat-kaka-fj.com/`

## 工作分支

`main`

## 功能映射

- 每日大盘：指数结构、宏观变量、主线板块、风险新闻。
- 我的持仓：业绩风险、公告核查、机构下修、资金异动；只发送单只股票代码和名称。
- 个股分析：保留财务、机构、事件、行业等现有深度追问。
- 热点机会：板块持续性、A 股筛选、事件催化、风险排除。

## 部署记录

- 运行代码提交：`ca286f55ef3772a58b7a045d8203f22c9165c910`。
- 服务器目录：`/opt/stock-ts`，分支 `main`，tracked worktree 干净。
- 回滚包：`/opt/stock-ts/.deploy_backups/iwencai-four-workspaces-20260714-164557/source-before.tar.gz`。
- `stock-ts.service`、`stock-ts-signal-desk.service` 和 Nginx 保持 `active`。
- 四模块真实调用和公网登录态调用均通过，响应无 Key 回显。

## 必须保留

- 本地结论、stale 闸门、市场风险预算和机会排序优先。
- 问财结果只作外部核查，不自动写入持仓、候选或交易计划。
- Key 只在服务器环境，响应和日志不得回显。
- 持仓数量、成本、权重、组合列表、账号和 Cookie 不发送到问财。
- 公网只允许登录用户使用，四页共用用户级限流。

# Review

## Scope

- `src/stock_ts/iwencai.py`
- `src/stock_ts/web.py`
- `src/stock_ts/webapp/research_console.py`
- 四个 workspace、共享脚本、样式和新增测试

## Findings

最终复审未发现未解决的 P0/P1/P2 finding。

审查中发现并已修复：

- `[P2]` 热点机会选择器直接暴露全部板块和候选，真实页面达到 40 项；现限制为最多 5 个板块和 8 只候选，并增加上限测试。
- `[P2]` 空持仓或空候选时控件仍可点击，只能从 endpoint 得到 400；现直接禁用并给出“先录入持仓”或“先刷新候选”。

## Security Boundaries

- 浏览器不能提供技能 ID、endpoint、Base URL 或外部请求头；服务端按模块白名单路由。
- market 主动丢弃代码、名称和板块上下文；portfolio 只保留单只股票代码、名称和问题。
- `shares`、`cost_price`、`weight` 和任意额外 context 字段在请求解析层丢弃，测试同时检查 HTML 与 endpoint 捕获 payload。
- 四个模块共用登录校验和用户级限流，不能通过切换页面绕过额度控制。
- 外部响应继续使用 DOM node 和 `textContent`，不使用 `innerHTML` 注入动态字段。

## Residual Risks

- 问财动态字段可能变化，页面仍限制为 5 条事实、每条 6 个字段；重要结论需复核公告或研报原文。
- 限流为单进程内存状态，服务重启会重置；多实例部署时需改为共享限流存储。
- 机会页外部筛选结果只显示为证据，不写入本地候选池；这是刻意的安全边界，不是自动选股同步。

## Decision

通过代码、隐私、交互和测试门禁，可推送并部署；生产四模块真实调用需在部署后完成。

# 三秒精华版审查记录

## 审查范围

- `src/stock_ts/webapp/market_workspace.py`
- `src/stock_ts/webapp/portfolio_workspace.py`
- `src/stock_ts/webapp/stock_workspace.py`
- `src/stock_ts/webapp/opportunity_workspace.py`
- `src/stock_ts/webapp/research_console.py`
- `src/stock_ts/webapp/styles.py`
- `src/stock_ts/web.py` 中机会来源表的单层展开适配
- 对应 Web 测试与需求文档

## Findings

未发现未解决的 P0、P1 或 P2 finding。

审查中发现并已修复：

1. 浅色结论卡继承旧深色卡白字，浏览器实看对比度不足；已增加明确的浅色文字覆盖和回归测试。
2. 机会来源账本在“展开筛选依据”内再次使用 `<details>`；已摊平成普通证据区，并增加禁止嵌套展开测试。
3. 大盘首屏动作曾由 renderer 新拼接；已改为复用现有风险轨道的仓位后果，避免展示层改变研究口径。
4. 持仓卡删除优先级序号后仍沿用三列 header；已收敛为内容加状态的两列布局。

## Open Questions / Assumptions

- 本次只改变默认展示层级，不重新定义风险预算、候选排序、仓位边界或个股研究权重。
- 站点仍坚持条件化研究，不输出确定收益承诺或自动交易动作。

## Residual Risks / Testing Gaps

- 视觉验收使用 sample/stale 页面；部署后还需复核公网登录边界和真实数据页面。
- 全项目仍有 5 个与本次无关的日报流水线基线失败，需作为独立需求修复。
- 浏览器字体由运行环境提供，未引入外部字体请求；不同系统的字宽可能略有差异，但 390px 无溢出契约已有验证。

## Decision

改动满足三秒精华版规格，可以进入提交与部署。

# Review

## 范围

- `src/stock_ts/research/stock_dossier.py`
- `src/stock_ts/research/stock_dossier_models.py`
- `src/stock_ts/webapp/stock_workspace.py`
- `src/stock_ts/webapp/styles.py`
- `src/stock_ts/web.py`
- 对应研究与 Web 测试

## Findings

未发现未解决的 P0/P1/P2 finding。

审查中发现并已修复：

- `[P1]` stale 三情景仍引用旧支撑、压力与失效价；已改为纯数据恢复情景并补回归测试。
- `[P1]` stale 的资金价格证据仍按旧技术结构标支持/反证；已降级为未知且只保留审计说明。
- `[P1]` 单期财务被写成“质量延续”，三期财务仅因期数足够就可能标支持；已按收入与利润同比连续方向分类，单期只等待下一财报确认。
- `[P2]` 390px 首个投资判断要到约 710px 才出现；已移除重复模块头并压缩身份刷新条，提前到约 486px。
- `[P2]` 方法旁白函数在页面移除后成为死代码；已删除对应渲染器和只被它调用的辅助函数。

## Assumptions

- 行业上下文当前不是结构化排名，因此只标中性，不自动成为支持证据。
- 未接入盈利一致预期，因此预期差只标不可量化，不推断上修或下修幅度。
- 事件分类仍是标题/摘要初筛，高等级风险必须回到公告原文复核。

## Residual Risks

- 财务同比跨报告期仍受基数和口径影响，页面保留该限制，不把连续改善写成确定趋势。
- 服务器与 GitHub 尚未更新，本轮验证仅代表本地分支。

## Decision

通过本地质量门禁，可进入提交与后续合并/部署流程；全量 pytest 的 5 个既有日报流水线失败需单独治理。

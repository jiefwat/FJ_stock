# Review

## 范围

- `src/stock_ts/iwencai.py`
- `src/stock_ts/web.py`
- `src/stock_ts/webapp/stock_workspace.py`
- `src/stock_ts/webapp/shell.py`
- `src/stock_ts/webapp/styles.py`
- 对应客户端、endpoint、鉴权和页面测试

## Findings

最终复审未发现未解决的 P0/P1/P2 finding。

审查中发现并已修复：

- `[P1]` 公开只读且关闭认证时可匿名消耗问财额度；现改为公网无认证直接禁用，匿名模式仅本地显式开启。
- `[P2]` Nginx 后所有用户可能共享 `127.0.0.1` 限流桶；现优先按登录用户 ID，匿名开发模式只信任 loopback 代理后的规范化 IP。
- `[P2]` 外部失败边界缺少超时、网络失败、超大响应和 HTTP 200 业务错误测试；均已补齐。
- `[P2]` 成功 payload 的字段值、字段名和业务状态可能回显 Key；现做递归 value/key 脱敏，并处理字段名冲突。
- `[P2]` 登录不可用时页面仍可能显示“已连接”；现显示“需启用登录”并禁用所有查询控件。

## Residual Risks

- 服务器当前未配置 `IWENCAI_API_KEY`，部署后先显示明确未配置状态，无法完成真实问财数据验收。
- 问财外部字段是动态契约，页面限制为 5 条、每条 6 个字段，并要求重要结论回到公告或研报原文。
- 进程内限流在服务重启后重置；当前规模足够，后续多实例部署需迁移到共享限流存储。

## Decision

通过本地质量门禁，可提交、合并和部署；真实问财查询需在服务器补充 Key 后完成。

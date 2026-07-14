# Tech Specs

## 基线

- Python：`3.11+`
- Lint / Format：ruff
- Test：pytest
- 包目录：`src/stock_ts/`

## 配置

配置通过环境变量或安全配置源注入，不在仓库提交真实凭证。

- `IWENCAI_API_KEY`：问财 SkillHub 服务端密钥，只允许出现在运行环境；浏览器、日志、HTML、JSON 错误和配置摘要不得回显。
- `STOCK_TS_IWENCAI_ALLOW_ANONYMOUS`：仅限本地开发的显式开关，默认关闭；公网必须启用 StockTs 登录后才能调用问财。
- `STOCK_TS_WEB_VERSION`：默认 `native`，四个核心模块只走服务端研究能力；显式设为 `legacy` 时才启用旧页面，用于回归和紧急回滚。
- 问财 OpenAPI 固定使用 `https://openapi.iwencai.com`，不接受浏览器传入自定义网关地址。
- 单能力调用默认 12 秒超时、1 MiB 响应上限；模块允许部分成功，全部失败时明确暂停判断，不回退旧结论。
- 产品 endpoint 为 `POST /api/research/workspace`，浏览器只能提交模块、代码/名称/板块和刷新标记；不能提交能力 id、版本或网关。

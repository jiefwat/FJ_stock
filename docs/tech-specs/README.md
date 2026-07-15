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
- `STOCK_TS_WEB_VERSION`：默认 `native`，四个核心模块使用本地确定性分析作为主判断，并可在服务端融合补充证据；显式设为 `legacy` 时启用历史长页面，仅用于回归和紧急排障。
- 问财 OpenAPI 固定使用 `https://openapi.iwencai.com`，不接受浏览器传入自定义网关地址。
- 单能力调用默认 12 秒超时、1 MiB 响应上限；模块允许部分成功，外部能力全部失败时保留本地分析并降低证据覆盖度。
- 产品 endpoint 为 `POST /api/research/workspace`，浏览器只能提交模块、代码/名称/板块和刷新标记；不能提交能力 id、版本或网关。

## 专业工作台质量门

```bash
make lint
python3 -m pytest -q \
  tests/test_professional_analytics.py \
  tests/test_research_fusion.py \
  tests/test_research_fallback.py \
  tests/test_web_research_workspace_api.py \
  tests/test_web_native_research_workspaces.py \
  tests/test_research_snapshots.py \
  tests/test_auth.py \
  tests/test_web_auth.py \
  tests/test_systemd_timer_contract.py
```

- 市场统计必须区分全市场涨跌家数和候选扫描样本，不能把样本极端涨跌伪装成全市场分布。
- 外部证据只能补齐覆盖率、事实和缺失维度，不能直接设置动作、风险预算或失效线。
- HTML 和产品 JSON 不得出现供应商品牌、能力 id、trace、网关字段、API key 或独立外部研究入口。
- 部署只重启 `stock-ts.service`，不新增 timer，不迁移账号、持仓、快照和报告目录。

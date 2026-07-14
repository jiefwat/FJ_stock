# 验证记录

## 自动化

- 新版专项与安全回归：`92 passed in 12.86s`。
- `make lint`：`All checks passed`；`git diff --check`：通过。
- 研究引擎：固定能力包、未知模块、持仓隐私、3 只上限、部分失败、全部失败、缓存、强制刷新、结果上限和内部元数据过滤。
- 产品 API：allowlist 上下文、错误请求、登录、16 KiB 限制、JSON 类型和供应商中性响应。
- 页面：不调用本地 Provider、四工作台结构、页面用语、持仓上下文、纯文本渲染、初始 hash 和移动端宽度。
- 安全回归：旧适配器的官方 HTTPS、trace 长度、超时、响应大小、密钥脱敏和旧 endpoint 保护保持覆盖。

## 浏览器

- `1280x720`：四工作台均存在，市场页首屏只有判断、动作、风险和三条发现；`scrollWidth=1280`。
- `390x844`：修复网格子项收缩后，工作台宽度从 `268px` 恢复为父容器的 `366px`；页面 `scrollWidth=390`。
- 页面可见文本未发现“问财”“iWencai”“同花顺”“Skill”“外部证据”。
- 从每日大盘切换到个股分析后，hash 为 `#stock`，活动工作台为 `stock`；浏览器控制台无 warning/error。

## 全量边界

- 默认新页面全量结果：`569 passed / 141 failed`。失败数量与可用性改造前一致；其中 136 项要求旧四页本地分析内容继续存在，与本分支完全替换目标冲突，另外 5 项为日报流水线新鲜度基线。
- 设置 `STOCK_TS_WEB_VERSION=legacy` 后结果为 `701 passed / 9 failed`。5 项仍为日报流水线新鲜度测试；4 项来自 native 页面专项在强制 legacy 环境下仍断言原生工作台存在，属于测试模式冲突。

## 可用性第二轮

- 专项回归：`104 passed in 1.83s`，覆盖能力级字段提取、语义门禁、专业结论、查询校准、供应商中性 API、页面结构与安全适配器。
- `make lint`：`All checks passed`；`git diff --check`：通过。
- 真实 `603278 大业股份`：个股 `complete`，财务、经营、机构预期、事件均为 `ready`；首屏显示最新事件、财务方向和机构预期，不再重复代码、名称、价格和涨跌幅。
- 真实大盘：`partial`，指数、行业和新闻可用；宏观能力只返回指数报价，被语义门禁标记为 `insufficient`。
- 真实持仓：`partial`，事件、公告和行情可用；身份/报价型机构预期被标记为 `insufficient`。
- 真实机会：`complete`，概念方向 5 条、A 股候选 10 条、事件和新闻均可用；默认排除“融资融券”泛标签。
- 1280px：页面宽与 `scrollWidth` 均为 1280px，三张首屏卡各 316px；证据覆盖度正确显示。
- 390px：页面 `scrollWidth=390`、工作台宽 366px、卡片宽 310px；个股页覆盖度 4/4；浏览器控制台无 warning/error。
- 四模块真实产品响应未发现供应商品牌、能力 id、trace、请求头、API key 或网关字段。

## 研究行动坞交互升级

- TDD 红绿过程：行动轨/移动导航的 3 项 HTML 契约先以缺少对应节点失败；状态与快捷键脚本先以缺少 `setEngineNavigationState` 失败；移动样式先以缺少 `.engine-mobile-dock` 失败；浏览器发现顶部重复导航后，回归测试先以缺少隐藏规则失败。
- 最终专项研究/API/UI/安全回归：`109 passed in 1.84s`；其中原生页面专项为 `13 passed`。
- `make lint`：`All checks passed`；`git diff --check` 与真实凭证特征扫描通过。
- `1280x900`：页面 `scrollWidth=1280`；桌面四个核心导航均可见，移动行动坞为 `display:none`，三项结果直达等宽展示。
- `390x844`：页面 `scrollWidth=390`；底部行动坞四个按钮高度均为 `44px`，主内容底部留白为 `94px`；顶部隐藏四个重复核心入口，只保留数据中台和账户管理。
- 交互验证：风险直达后焦点位于风险卡；完整依据会展开并聚焦摘要；`Escape` 关闭依据并保留摘要焦点；数字键 `3` 切换到个股页并同步桌面/移动 `aria-current`；搜索输入框获得焦点时数字键不会切换模块。
- 本机匿名验证最初捕获到 `分析中 -> 暂不可用`，进一步定位为 Framework Python 3.12 缺少系统 CA，并非官方接口无数据；接入 `certifi` 后同一运行时恢复真实结果。
- 浏览器控制台无 warning/error；页面未出现供应商品牌、能力 id、trace、API key 或网关字段。

## 证书修复与公网部署

- 证书链 TDD：默认客户端加载可信 CA 和传入 HTTPS context 的两项测试先因缺少 `certifi` / `_trusted_ssl_context` 失败，修复后通过。
- 最终专项研究/API/UI/安全回归：`111 passed in 1.83s`；`make lint`、`git diff --check` 和凭证特征扫描通过。
- 本机 Python 3.12 真实调用：指数返回 3 行；大盘 `partial 3/4`、持仓 `partial 9/12`、个股 `complete 4/4`、机会 `complete 4/4`，四页均展示三条发现。
- 公网服务器登录态 API：大盘、持仓、个股、机会均为 HTTP 200 且 `ok=true`；每个模块都有 findings 和 details。
- 公网登录态 HTML：四个 `data-engine-workspace`、移动行动坞和 `/api/research/workspace` 均存在，产品可见 HTML 保持供应商中性。
- GitHub `main`、本地 `main` 和服务器 `/opt/stock-ts/main` 首次部署均为 `19ad5bf67f8a839e700442310611487663fdb04c`。
- 首次部署前备份：`/opt/stock-ts/.deploy_backups/iwencai-native-20260714-235652/source-before.tar`。
- 服务：`stock-ts.service=active`；公网 `/healthz=200`，根路径按预期 303 到登录页，登录页与注册入口均为 200/可用。

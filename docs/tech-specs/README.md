# Aster Market 技术规格

## 技术基线

- Python `3.11+`
- 生产依赖：仅 Python 标准库
- 开发依赖：Pytest、Ruff
- 桌面最小宽度：`1180px`
- 浏览器资源：HTML、CSS、SVG、原生 JavaScript

页面不包含 viewport 声明、手机导航、抽屉、窄屏媒体查询或响应式手机布局。

## HTTP 契约

| 路由 | 类型 | 缓存 | 说明 |
| --- | --- | --- | --- |
| `/` | `text/html` | `no-store` | 市场地形工作台 |
| `/healthz` | `text/plain` | `no-store` | 固定返回 `ok` |
| `/api/snapshot` | `application/json` | `no-store` | 供应商中立页面数据 |
| `/api/analysis/market` | `application/json` | `no-store` | 大盘四维分析 |
| `/api/opportunities` | `application/json` | `no-store` | 主题机会走廊 |
| `/api/stocks?query=` | `application/json` | `no-store` | 股票搜索，最多 40 字符 |
| `/api/stocks/<code>` | `application/json` | `no-store` | 单股分析详情 |
| `/assets/app.css` | `text/css` | 300 秒 | 视觉系统 |
| `/assets/modules.css` | `text/css` | 300 秒 | 四模块分析甲板 |
| `/assets/app.js` | JavaScript | 300 秒 | 模块切换与股票查询 |
| `/assets/portfolio.js` | JavaScript | 300 秒 | 浏览器私有持仓 |

其他路径返回 404。服务不会发起登录跳转，也不会设置 Cookie。

## 快照契约

根对象读取 `source`、`generated_at`、`market`、`sectors`、`candidate_universe.items`、`stocks` 和 `market_news`。

`market` 支持：

- `trade_date`
- `indices[].code/name/close/pct_chg`
- `advancing`、`declining`
- `limit_up`、`limit_down`
- `northbound_net_inflow`

主题读取 `name`、`pct_chg`、`advancing_ratio`、`amount_change`、`consecutive_days` 和 `high_divergence`。候选读取代码、名称、主题和最后一根 K 线；若候选自身没有 K 线，会按代码读取 `stocks`。市场事件只读取时间、来源、标题和摘要。

股票档案合并 `stocks` 与候选池的代码、名称、主题、K 线、估值、成交、内外盘、数据质量、新闻和公告。缺失数字保留为 `null`，浏览器显示 `—`，不得转成 0。

## 状态推导

- 广度不低于 `0.58` 且跌停不超过 `10`：`扩张`
- 广度不高于 `0.42` 或跌停不少于 `25`：`收缩`
- 其他情况：`轮动`

这些标签是观察状态，不是买卖建议。主题排序由涨幅、上涨占比、成交变化、连续性和高分歧惩罚共同决定。

## 分析规则

- 大盘分析：指数方向、上涨参与度、跌停压力、主题集中度四条证据。
- 市场机会：按主题强度排序，阶段为扩散、加速、分歧或观察，每条带失效条件。
- 股票趋势：最新价相对 5 日/20 日均值分为强、平、弱或样本不足。
- 股票动量：5 日和 20 日收益率；样本不足返回 `null`。
- 股票波动：最近十根 K 线平均日内振幅。
- 内外盘差：仅在两个字段都存在时计算，不称为主力资金。

## 持仓隐私

持仓键为 `aster.portfolio.v1`，值只包含代码、数量和成本。所有市值、盈亏、收益率、主题暴露和集中度均在浏览器计算。服务器没有持仓读取或写入接口，股票查询 URL 只包含公开股票代码。

## 配置

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | 监听地址 |
| `PORT` | `8501` | 监听端口 |
| `ASTER_SNAPSHOT_PATH` | `data/market_snapshot.json` | 快照路径 |

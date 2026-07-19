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
| `/assets/app.css` | `text/css` | 300 秒 | 视觉系统 |
| `/assets/app.js` | JavaScript | 300 秒 | 搜索、视图跳转和刷新 |

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

## 状态推导

- 广度不低于 `0.58` 且跌停不超过 `10`：`扩张`
- 广度不高于 `0.42` 或跌停不少于 `25`：`收缩`
- 其他情况：`轮动`

这些标签是观察状态，不是买卖建议。主题排序由涨幅、上涨占比、成交变化、连续性和高分歧惩罚共同决定。

## 配置

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | 监听地址 |
| `PORT` | `8501` | 监听端口 |
| `ASTER_SNAPSHOT_PATH` | `data/market_snapshot.json` | 快照路径 |

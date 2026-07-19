# Aster Market 架构

## 产品边界

Aster Market 是公开、只读、无账户的 A 股分析应用。它读取一份本地 JSON 快照，输出大盘环境、市场机会、股票证据和市场事件。它没有数据库、交易接口、服务端持仓、通知、AI 对话或写操作；“我的持仓”只使用当前浏览器的本地存储。

## 数据流

```text
JSON 快照
  -> snapshot.py 解析与降级
  -> models.py 不可变领域模型
  -> analysis.py 确定性分析
  -> presenter.py 供应商中立摘要
  -> ui.py / ui_modules.py / web.py
  -> HTML + 只读 JSON API
```

所有动态请求都会重新读取快照，因此行情文件更新后不需要重启进程。快照缺失或损坏时，页面仍返回 200 并展示明确中断状态；API 返回 503 和 `status=unavailable`，不会用演示价格补位。

## 模块职责

- `models.py`：指数、主题、股票、K 线、估值、资金、事件和市场快照的不可变模型。
- `snapshot.py`：只读 JSON 适配器，合并股票主档案与候选档案；不发起网络请求。
- `analysis.py`：大盘四维证据、机会阶段、股票趋势/动量/波动和搜索。
- `presenter.py`：市场状态、风险、主题排序与地平线轨迹推导。
- `ui.py`、`ui_modules.py`：分析甲板 HTML 渲染和外部字符串转义。
- `web.py`：标准库 HTTP 路由、安全头和进程入口。
- `assets/app.js`：模块切换、股票搜索和详情渲染。
- `assets/portfolio.js`：浏览器私有持仓账本；数量和成本不进入网络请求。

## 安全边界

- 只开放 `GET` 路由，不实现交易和状态变更接口。
- 外部文本进入 HTML 前统一 `html.escape`。
- 动态股票文本使用 `textContent` 写入 DOM，不使用 `innerHTML`。
- 持仓只保存为 `aster.portfolio.v1`，服务器不读取、不接收也不记录持仓。
- 动态响应使用 `Cache-Control: no-store`，全部响应使用 `nosniff` 与 CSP。
- 运行配置只来自环境变量；仓库不保存凭证、内部地址或线上配置。

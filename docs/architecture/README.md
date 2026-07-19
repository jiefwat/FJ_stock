# Aster Market 架构

## 产品边界

Aster Market 是公开、只读、无账户的 A 股市场态势应用。它读取一份本地 JSON 快照，输出市场状态、主题强度、候选观察流和市场事件。它没有数据库、交易接口、用户持仓、通知、AI 对话或写操作。

## 数据流

```text
JSON 快照
  -> snapshot.py 解析与降级
  -> models.py 不可变领域模型
  -> presenter.py 供应商中立视图
  -> ui.py / web.py
  -> HTML + /api/snapshot
```

所有动态请求都会重新读取快照，因此行情文件更新后不需要重启进程。快照缺失或损坏时，页面仍返回 200 并展示明确中断状态；API 返回 503 和 `status=unavailable`，不会用演示价格补位。

## 模块职责

- `models.py`：指数、主题、候选、事件和市场快照的不可变模型。
- `snapshot.py`：只读 JSON 适配器；不发起网络请求。
- `presenter.py`：市场状态、风险、主题排序与地平线轨迹推导。
- `ui.py`：服务端 HTML 渲染和外部字符串转义。
- `web.py`：标准库 HTTP 路由、安全头和进程入口。
- `assets/`：独立 CSS 与原生 JavaScript；无构建步骤和前端依赖。

## 安全边界

- 只开放 `GET` 路由，不实现交易和状态变更接口。
- 外部文本进入 HTML 前统一 `html.escape`。
- 动态响应使用 `Cache-Control: no-store`，全部响应使用 `nosniff` 与 CSP。
- 运行配置只来自环境变量；仓库不保存凭证、内部地址或线上配置。

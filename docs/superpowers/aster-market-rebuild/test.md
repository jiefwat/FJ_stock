# Aster Market 验证记录

## 自动化

- `PYTHONPATH=src python -m pytest -q`：15 passed
- `ruff check src tests`：All checks passed
- `PYTHONPATH=src python -m compileall -q src`：退出码 0

## 浏览器

使用真实浏览器和测试快照完成：

- 1280 × 900：页面宽度与视口均为 1280，无横向溢出。
- 1536 × 960：页面宽度与视口均为 1536，无横向溢出。
- 1920 × 1080：主内容宽度 1740，无横向溢出，控制台错误为 0。
- 搜索“中芯”后只显示中芯国际，清空搜索后恢复全部候选。

## 发布后验证

- 公网首页返回 200，无登录跳转或 Cookie，包含 `data-aster-app="market-horizon"`。
- `/healthz` 返回 200 和 `ok`。
- `/api/snapshot` 返回 200、`status=ready`，包含 3 个指数、19 个主题、300 个候选和 23 条事件。
- 首页、健康检查和 API 均返回 `Cache-Control: no-store` 与 `X-Content-Type-Options: nosniff`。
- 主服务、旁路服务和 Nginx 均为 `active`；主服务重启次数为 0，最近日志无 warning。

## 真实快照预检

使用 18MB 运行时快照完成本机 HTTP 验收：

- API 返回 `status=ready`、交易日 `2026-07-10`。
- 正确输出 3 个指数、19 个主题、300 个候选和 23 条事件。
- 真实数据下 1280 与 1536 宽度无横向溢出，控制台错误为 0。
- 首页、健康检查和 API 均包含预期缓存与安全响应头。

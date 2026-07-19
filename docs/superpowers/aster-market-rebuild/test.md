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

## 发布后待验证

- 公网首页无需登录，包含 `data-aster-app="market-horizon"`。
- `/healthz` 返回 `ok`。
- `/api/snapshot` 返回 `status=ready` 且不泄露供应商内部结构。
- 旁路服务保持健康。

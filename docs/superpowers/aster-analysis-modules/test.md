# 四模块分析甲板验证记录

## 自动化

- `PYTHONPATH=src python -m pytest -q`：29 passed
- `ruff check src tests`：All checks passed
- `python -m compileall -q src`：退出码 0
- `node --check app.js` 与 `node --check portfolio.js`：退出码 0

## 真实快照浏览器

- 大盘分析默认打开，四维证据完整。
- 市场机会显示 8 条机会走廊并可进入股票分析。
- 搜索“大金重工”返回唯一结果；详情显示趋势、六个维度、证据、风险和事件。
- 测试持仓新增后正确计算市值、成本、盈亏和收益率；编辑、刷新持久化和删除均通过。
- 服务日志只出现公开 GET 股票请求，没有数量或成本。
- 1280、1536、1920 宽度无横向溢出；控制台无页面错误。

## 发布后待验证

- 公网四个模块均可切换。
- 四类新增 API 返回 200、`no-store` 和供应商中立 JSON。
- 持仓刷新后保留，服务器日志不出现数量或成本。
- 主服务、Signal Desk 和 Nginx 保持健康。

# Test Evidence

验证日期：2026-07-13

## 结果

- Ruff：`ruff check src tests`，通过，`All checks passed!`。
- 个股研究专项：166 passed。
- Python 3.9：`tests/test_stock_dossier.py tests/test_web_stock_dossier.py`，21 passed。
- 全量 pytest：519 passed、6 failed、11 warnings；失败数和失败用例与开发前基线一致，本需求没有新增失败。
- 真实 `603278` 快照 HTTP：200，HTML 316,993 bytes，唯一投委会结论 1 个。
- 真实快照口径：展示亏损、PE 失效、PB 口径冲突、65.72% 质押风险与禁止动作。
- 陈旧行情硬停：五步轨道不再显示旧支撑/压力/失效价格，价格相关证据均标记 stale。
- 响应式：桌面 1440px 与移动 390px 浏览器渲染通过；移动端文档宽度与视口均为 390px，无页面级横向溢出。

## 已知基线失败

- `tests/test_daily_pipeline.py` 5 项：既有日报流水线状态断言失败。
- `tests/test_web_data_accuracy.py::test_web_blocks_opportunity_ranking_when_snapshot_trade_date_is_stale`：既有陈旧机会文案断言失败。

这些失败在本需求开始前已存在，且不涉及新增个股档案代码。未修改其业务逻辑或用跳过标记隐藏失败。

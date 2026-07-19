# Aster Market 今日研判链测试记录

## 进行中验证

- 决策简报 RED：测试因 `build_decision_brief` 不存在而失败。
- 决策简报 GREEN：扩张、轮动、收缩和无主题 4 项测试通过。
- `tests/test_analysis.py`：9 项通过。
- `ruff check src/aster_market/analysis.py tests/test_analysis.py`：通过。

## 待完成

- Presenter 与 HTTP 合同。
- UI 信息架构和三档桌面浏览器。
- 全量测试、代码审查和公网验收。

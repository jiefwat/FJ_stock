# Aster Market 今日研判链测试记录

## 自动化验证

- 决策简报 RED：测试因 `build_decision_brief` 不存在而失败。
- 决策简报 GREEN：扩张、轮动、收缩和无主题 4 项测试通过。
- `tests/test_analysis.py`：9 项通过。
- `ruff check src/aster_market/analysis.py tests/test_analysis.py`：通过。
- Presenter / HTTP RED：测试因 view 缺少 `decision_brief` 而失败。
- Presenter / HTTP GREEN：11 项通过，`/api/snapshot` 已包含主线主题。
- Presenter / HTTP 相关 Ruff 检查：通过。
- UI / HTTP 聚焦测试：21 项通过。
- `ruff check src tests`：通过。
- `node --check src/aster_market/assets/app.js`：通过。
- `node --check src/aster_market/assets/portfolio.js`：通过。
- 独立审查回归 RED：缺失分歧字段仍确认主线、防守市场仍返回扩散/分歧、旧 view 字段仍存在等 6 项测试按预期失败。
- 独立审查回归 GREEN：上述 6 项聚焦测试通过。
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 make test`：50 项全部通过。
- `python3 -m compileall -q src`：通过。
- `git diff --check`：通过。

## 页面精简

- 首页只保留五步研判链、今日结论与升级条件、指数与四条证据、主线梯队。
- 已删除市场地平线、主题强度场、事件流、全市场候选流、英文装饰标题和重复解释。
- 旧渲染函数、旧 CSS 选择器和旧动画均已物理删除；测试明确禁止这些结构重新出现。

## 浏览器验收

- 主线扫描切换正常。
- 主线股票“双林股份”可进入个股验证，并正确加载 `300100` 当前快照。
- 全局搜索“中芯国际”返回 `688981 · 半导体`。
- 持仓完成保存、编辑数量、重新计算和删除；删除后恢复空账本。
- 1280x800、1536x900、1920x1080 均使用当前构建重新实测，横向溢出均为 `0px`。
- 三档首页主体底部分别约为 878px、896px、898px，五步研判链完整显示。
- 页面 console error / warning 为 0。

## 待完成

- 公网实时快照与服务健康验收。

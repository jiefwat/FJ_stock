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

## 公网验收

- release：`20260719-185300-be67997`，`current` 与服务器唯一 release 均指向该目录。
- 公网 `/healthz`、首页、快照、大盘、机会和生产真实个股接口均返回 200；首页使用 `decision-v1`，没有 viewport、旧地平线、事件流或候选流。
- 实时快照链接继续指向 `/opt/stock-ts/data/imports/tdx_snapshots.json`，文件大小 84,137,234 字节，没有复制或改写行情原文件。
- 实时交易日为 `2026-07-17`：市场为“收缩”，参与许可为“防守等待”，人工智能标记为“逆势异动”，没有误写成确认主线。
- `/api/opportunities` 返回 8 个方向且全部为“逆势异动”；真实个股 `300795` 返回“米奥会展 / 人工智能 / 强趋势”。
- 页面 view 与 `/api/snapshot` 不再含 `candidates`、`news`、`horizon_points` 旧字段。
- 服务端热请求：首页 37.39ms、快照 1.67ms、大盘 2.90ms、机会 1.67ms、个股 31.00ms。
- `stock-ts.service`、`stock-ts-signal-desk.service` 和 Nginx 均为 active；主服务 `NRestarts=0`，近 10 分钟 warning 为 0。
- 公网浏览器自动化导航连续超时；公网 HTML、CSS、JavaScript 与 API 由外部 HTTPS 请求验证，真实浏览器交互使用同一提交的本地服务完成。

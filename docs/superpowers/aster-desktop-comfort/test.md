# Aster Market 桌面舒适度验收

## 自动化验证

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q`：38 项通过。
- `ruff check src tests`：通过。
- `python3 -m compileall -q src`：通过。
- `node --check src/aster_market/assets/app.js`：通过。
- `node --check src/aster_market/assets/portfolio.js`：通过。
- `git diff --check`：通过。

## 本地浏览器验证

- 四个模块按钮和数字键 `1` 至 `4` 均能切换甲板，hash、按钮状态和可见内容同步。
- `/` 能聚焦全局股票搜索；共享防抖后只展示最终查询结果。
- `Escape` 第一次清空全局与模块搜索，第二次退出输入框。
- 机会候选可直接进入股票分析；股票详情使用结构化加载状态。
- 加入持仓、保存、编辑和删除均成功，数量和成本只存在当前浏览器。
- 个股与持仓渲染均使用请求序号，旧请求不能覆盖新的选择或账本状态。
- 任一持仓行情不可用时，组合市值、盈亏和收益率显示 `—`，不会把缺失价格当作 0。
- 大盘滚动位置在模块往返后精确恢复，实测 `438px -> 0 -> 438px`。
- 1280x800、1536x900、1920x1080 下四模块横向溢出均为 `0px`。
- 浏览器控制台没有 error 或 warning。

## 本地热缓存性能

使用测试快照预热后测得：

| 路由 | HTTP | 首字节 | 总耗时 |
| --- | ---: | ---: | ---: |
| `/` | 200 | 2.48ms | 2.54ms |
| `/api/snapshot` | 200 | 1.02ms | 1.08ms |
| `/api/analysis/market` | 200 | 0.73ms | 0.78ms |
| `/api/opportunities` | 200 | 0.83ms | 0.88ms |
| `/api/stocks/300100` | 200 | 0.83ms | 0.87ms |

## 公网验收

- release：`20260719-175050-9a1d197`，服务器仅保留该 release。
- 公网首页和四个模块返回 200，静态资源版本为 `comfort-v4`；没有登录跳转、Cookie 或手机 viewport。
- 实时快照为 84,137,234 字节，交易日 `2026-07-17`，生成时间 `2026-07-19T07:06:05.143048+00:00`。
- 快照包含 3 个指数、17 个主题、8 条市场机会、500 个候选和 358 条事件。
- 搜索“米奥会展”唯一返回 `300795`，个股详情返回 200。
- 服务端热缓存首字节：首页 1.97ms、快照 3.94ms、大盘 1.13ms、机会 1.53ms、个股 2.39ms。
- 公网复用连接后首页与分析接口典型首字节为 80 至 90ms；首次 TLS 建连约 293ms。
- `stock-ts.service`、`stock-ts-signal-desk.service` 和 Nginx 均为 active；主服务 `NRestarts=0`，warning 日志为 0。

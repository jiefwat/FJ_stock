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

公网部署完成后补充 release、真实快照日期、热缓存首字节和服务状态。

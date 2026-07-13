# 大盘与个股专业研究升级测试报告

日期：2026-07-13

## 1. 环境

- 分支：`codex/market-stock-research-upgrade`
- worktree：`/Users/fangjie/.config/superpowers/worktrees/StockTs/codex-market-stock-research-upgrade`
- Python：3.12.0
- 测试框架：pytest 8.3.5
- 本地烟测：`http://127.0.0.1:8514/`

## 2. 基线

从当前主工作区导入尚未提交但相互配套的 UI/测试改动，并复制被 Git 忽略的本地持仓与 TDX 快照后，完整基线为：

- 通过：446
- 失败：6
- 警告：11

既有失败为 `tests/test_daily_pipeline.py` 5 项，以及 `tests/test_web_data_accuracy.py::test_web_blocks_opportunity_ranking_when_snapshot_trade_date_is_stale` 1 项。本次不修改这些不相关问题。

## 3. 新增验证

新增测试覆盖：

- 证据审计状态与必需数据阻断。
- 进攻、风险释放、数据暂停等市场阶段。
- 只有当日截面时的跨期结论降级。
- 大盘偏强/基准/偏弱三情景。
- 绝对估值与相对估值边界。
- 单期财务、标题级公告、未持仓上下文的安全表述。
- 个股乐观/基准/悲观三情景。
- 大盘和个股工作区的首屏顺序、缺失状态和证据审计。

聚焦命令：

```bash
PYTHONPATH=src pytest -q \
  tests/test_research_evidence.py \
  tests/test_market_regime.py \
  tests/test_stock_research_memo.py \
  tests/test_web_market_research_workspace.py \
  tests/test_web_stock_research_workspace.py \
  tests/test_agentic_stock_method.py \
  tests/test_professional_research.py \
  tests/test_latest_stock_method_unified.py \
  tests/test_web_module_decisions.py \
  tests/test_web_design_guide_shell.py \
  tests/test_web_layout.py
```

结果：132 passed。

## 4. 全量结果

```text
make lint: PASS
make test: 463 passed, 6 failed, 11 warnings
```

失败集合与基线完全一致，通过数增加 17，未新增回归。

## 5. 本地 HTTP 烟测

启动命令：

```bash
STOCK_TS_PORT=8514 PYTHONPATH=src python3 -m stock_ts.web
```

请求：

```text
GET /?provider=tdx-snapshot&code=603278&holdings=data%2Fportfolio%2Fholdings.csv
```

结果：

- HTTP 200，响应 310995 bytes。
- 大盘状态：`风险释放`。
- 个股研究状态：`条件研究`。
- 页面可见市场风险预算、核心矛盾、两组三情景、六类证据和两处证据审计。
- 本次只验证本地运行，不包含公开域名或服务器部署验证。

## 6. 已知风险

- 市场趋势、流动性和风格目前只有当日截面，系统已降级标注；要形成真正跨期研究，需要新增历史市场序列。
- 个股估值历史分位和行业可比数据不是所有标的都具备，缺少时只显示绝对估值。
- 公告仍主要依赖标题级风险扫描，研究结论要求人工打开原文复核。
- 全量套件的 6 个既有失败仍需单独排期处理，不能把本报告理解为全仓零失败。

# 三秒精华版测试记录

## 自动化验证

- 四工作台结构契约：主结论唯一、动作唯一、风险唯一、默认最多三项、依据与问财默认关闭、依据区不再嵌套二次展开。
- 问财契约：四模块入口、登录边界、上下文选择、禁用状态、同源 API 与安全 DOM 渲染保持不变。
- 研究契约：过期数据暂停、市场风险轨道、持仓审计、个股完整档案、机会来源账本仍保留在折叠区。

执行命令：

```bash
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest tests/test_web_*.py -q
PATH=/Users/fangjie/Documents/StockTs/.venv/bin:$PATH make lint
PYTHONPATH=src /Users/fangjie/Documents/StockTs/.venv/bin/python -m pytest -q
```

结果：

- Web 全量：`255 passed`。
- Ruff 全量：`All checks passed!`。
- 项目全量：`651 passed, 5 failed, 10 warnings`。
- 5 个失败均为改版前已存在的 `tests/test_daily_pipeline.py` 失败，失败用例与基线完全一致；本次未修改日报流水线。

## 浏览器验证

本地地址：`http://127.0.0.1:8765/?provider=sample`

- `1280x900`：大盘、持仓、个股、机会均无横向溢出；个股、持仓、机会结论文字为深色高对比；复杂内容默认关闭。
- `390x844`：四页 `scrollWidth == clientWidth == 390`；首屏先出现结论、动作和风险；持仓与机会各显示 3 项，个股显示 3 条依据。
- 交互：市场“展开市场依据”点击一次即可看到五步轨道、三情景和维度；问财与完整依据为同级入口，不互相嵌套。
- 控制台：无 `error`、`warn` 或 `warning`。

## 安全检查

- HTML、diff 与测试输出未出现问财 Key、密码、Token 或私钥。
- 问财仍需登录后主动提交，不自动调用外部服务。
- 用户持仓路径与隔离逻辑未修改。

## 生产部署与刷新

- 运行代码提交：`1e40f2893fe44644de426eade1aa38cbf9a3c2b7`。
- 服务器：`admin@47.82.145.207:/opt/stock-ts`，分支 `main`，tracked 工作树干净。
- 回滚包：`/opt/stock-ts/.deploy_backups/three-second-essence-20260714-175255/source-before.tar.gz`。
- 传输：完整 Git bundle 校验 SHA-256 后，服务器使用 `git merge --ff-only` 快进。
- `.env` 权限保持 `600`；`.env`、`.secrets`、`data`、`reports`、账号和持仓数据均保留。
- 只重启 `stock-ts.service`；StockTS、Signal Desk、Nginx 和日报定时器均保持正常。

生产刷新于 `2026-07-14T18:22:32` 完成：

```text
status=ok
refresh=ok
tdx_enrich=ok
a_share_kline=ok
external_enrich=ok
announcements=ok
report=ok
data_chain=ok
```

- 全市场扫描：`5,533` 只；候选：`300` 只；TDX 深度补强：`23` 只。
- A 股日线：请求 `311` 只，更新 `310` 只，失败 `0`，非 A 股跳过 `1`。
- 外部补强：持仓优先和候选分批全部 `error_count=0`；市场新闻 `161` 条。
- 最新日报：`trade_date=2026-07-14`，Markdown、决策 JSON 和 HTML 均已生成。

公网验证：

- `https://stock.jiewat-kaka-fj.com/healthz` 返回 `ok`。
- 根路径返回 HTTP `303`，跳转 `/login?next=%2F`。
- 匿名问财返回 HTTP `401`、`status=login_required`，未回显 Key。

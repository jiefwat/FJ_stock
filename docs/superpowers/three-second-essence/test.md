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

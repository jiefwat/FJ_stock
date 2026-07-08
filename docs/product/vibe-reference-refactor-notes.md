# Vibe-Trading / Vibe-Research / Longbridge 参考重构笔记

更新时间：2026-07-08

## 参考边界

本轮参考用户指定的公开方向：

- HKUDS/Vibe-Trading：`https://github.com/HKUDS/Vibe-Trading`
- simonlin1212/Vibe-Research：`https://github.com/simonlin1212/Vibe-Research`
- Longbridge ChatGPT app 方向：`https://chatgpt.com/apps?q=longbridge`

当前网络环境下 GitHub API 返回 rate limit，raw/clone 多次超时，因此本轮不把外部项目内部实现细节写成事实；只吸收可迁移的产品范式：自然语言研究目标、证据链、只读/纸面交易边界、每日研究工作流、移动端可读输出、多数据源可信度闸门。

## 对 StockTS 的重构判断

StockTS 之前已经有大盘、板块、持仓、候选池、个股、邮件、自动流水线，但这些能力分散在报告和脚本里。用户真正需要的是一个“研究运行系统”：

1. 先回答今天的研究目标是什么。
2. 再说明哪些证据支持或反对。
3. 明确今天持仓怎么处理。
4. 明确机会只观察还是可跟踪。
5. 明确哪些数据缺口会降低可信度。
6. 明确系统只做研究和纸面推演，不做真实交易下单。

## 已落地模块

新增 `src/stock_ts/research_run_card.py`：

- `ResearchRunCard`：一次盘前研究运行卡。
- `ResearchRunTask`：可审计任务，包含问题、证据、动作和边界。
- `build_research_run_card()`：从最新日报 Markdown 与 pipeline.status 提取研究任务。
- `render_research_run_card_markdown()`：输出移动端可读 Markdown。

当前任务固定为 4 个层级：

1. `市场状态确认`：判断今天能否提高风险暴露。
2. `持仓风险处置`：优先处理高风险/下降趋势持仓。
3. `机会池验证`：候选股只做条件观察，不追高。
4. `数据质量闸门`：数据缺口相关结论降级，不伪造强证据。

## 输出接入点

- `scripts/send_morning_report.py`：早间邮件在“一句话结论”后直接显示 `## 研究运行卡`。
- `src/stock_ts/deep_report.py`：每日深度复盘 Markdown 也输出同一套研究运行卡。

这样邮件、日报、Web 读取的 latest.md 会共享同一个研究任务结构。

## Shadow Account 边界

参考交易型产品的安全隔离思路，StockTS 的策略边界固定为：

> 只读研究和纸面推演；不接真实下单、不保存券商交易凭证。

这条边界必须出现在研究运行卡里，避免后续 agent 把 StockTS 改成真实交易系统。

## 后续可继续的大重构

1. 将 `scripts/send_morning_report.py` 中剩余 Markdown 解析函数逐步下沉到 `research_run_card` 或独立 parser。
2. 为 Web 首页增加“研究运行卡”视觉模块，替代散装摘要。
3. 为每个任务增加状态：`open / confirmed / blocked / expired`，让系统形成每日研究日志。
4. 将候选股机会从“Top 列表”升级为“研究任务队列”，记录触发条件、风险、复盘结果。
5. 引入纸面组合（shadow account）数据结构，只记录假设、观察和虚拟执行，不连接真实券商下单。

## 2026-07-08 反模板分析修正

用户反馈“股票分析太简单，都是固定套话”。根因定位到 `src/stock_ts/deep_analysis.py::_final_conclusion`：旧逻辑只按综合分数三档输出固定句式，导致不同股票只是股票名和分数不同，结论没有真实证据差异。

已修正为证据驱动结论：

- 从多角度评分里选最高分证据作为“优势”。
- 从低分角度里选主要约束作为“主要矛盾”。
- 按综合分与风险等级生成动作倾向。
- 必须带触发条件和失效条件。
- 禁止输出“当前信号不足”“处于中性偏强观察区”“不适合给出确定性判断”等模板句。

后续所有个股分析、日报、邮件和 Web 展示都应复用这条原则：先证据，后判断；先矛盾，后动作；任何动作必须有失效线。

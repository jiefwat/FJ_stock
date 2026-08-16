# StockTS

本地优先的 A 股投研工具。核心路径是：看市场 -> 找机会 -> 问个股 -> 处理持仓。

## 模块

- 大盘：指数、广度、板块热度、资金主线、龙虎榜和市场异动。
- 机会：按趋势、放量、低估、超跌等条件筛出未来更可能上涨的候选。
- 个股：价格趋势、直接建议、风险、估值、公告、研报和题材。
- 问股：接入大模型联网问答，并保留股票、板块、机会、持仓上下文。
- 持仓：保存真实持仓、成本、目标仓位，并给出简洁处理动作。

## 启动

```bash
make setup
make start
```

默认打开 <http://127.0.0.1:8765>；如果端口已被其他程序占用，启动脚本会自动选择后续空闲端口并打印实际地址。停止服务：

```bash
make stop
```

开发模式使用 `make dev`，前端为 `http://127.0.0.1:5173`，API 为 `http://127.0.0.1:8000`。

## 验证

```bash
make test
make verify
```

`make verify` 会检查 Python lint/type/test、前端 type/test/build，并从真实数据源验证 A 股数量、核心字段覆盖率、指数集合、行业数量和数值有效性。公网服务默认每 2 小时自动刷新一次市场数据。

## 数据来源与限制

- A 股全市场快照：新浪公开行情列表。
- 核心指数与个股复权日线：腾讯公开行情接口。
- 行业热度：新浪行业行情与东方财富板块资金流增强。
- 公司公告：巨潮资讯公告元数据与原文链接；不缓存公告正文或 PDF。
- 研报与题材：东方财富研报元数据、原文链接和题材归属；只作研究上下文，不进入评分。
- 市场异动：东方财富龙虎榜与公开快讯；快讯不可用时尝试财联社独立备源。
- 金融大模型问股：可选增强项；通过 OpenAI 兼容接口接收本地行情、确定性分析、账户持仓和最近对话，未配置或调用失败时自动回退到本地分析。
- AInvest：仅用于产品交互参考，不是数据依赖。

公开接口可能限流或调整。服务优先展示最后一次有效快照并标记时效；外部证据分别标记 ready、partial、empty 或 unavailable，不把上游失败解释为没有数据。当前产品用于个人投研辅助，不构成投资建议。公开或商业部署前需要重新核查巨潮资讯、东方财富、财联社等数据授权与服务条款。

## 问股边界

问股会保留最近对话里的股票、板块、机会和持仓上下文。涉及具体股票时，服务端先整理当前全市场快照、个股确定性结论、技术指标、风险证据和账户持仓，再把这份有界上下文交给金融大模型。全市场排行与硬指标仍由确定性代码计算；模型未配置或调用失败时自动回退到本地答案，不会把缺失数据补成确定结论。

服务端可配置任意 OpenAI Chat Completions 兼容的金融模型；以下示例使用 DashScope，默认只使用系统提供的上下文：

```bash
export MARKETDESK_FINANCIAL_LLM_API_KEY="<server-side-secret>"
export MARKETDESK_FINANCIAL_LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export MARKETDESK_FINANCIAL_LLM_MODEL="qwen3.7-plus"
export MARKETDESK_FINANCIAL_LLM_API_STYLE="chat_completions"
export MARKETDESK_FINANCIAL_LLM_WEB_SEARCH_ENABLED="false"
```

旧的 `DASHSCOPE_API_KEY` 与 `MARKETDESK_LLM_WEB_*` 配置继续兼容。若模型支持服务端搜索，可显式把 `MARKETDESK_FINANCIAL_LLM_WEB_SEARCH_ENABLED` 设为 `true`。凭证只允许放在服务端环境中，不返回浏览器，也不能写入仓库。公网部署脚本会把本机 `.env` 单独同步到远端 `/opt/aster-market/.env`，不会打进发布代码包。

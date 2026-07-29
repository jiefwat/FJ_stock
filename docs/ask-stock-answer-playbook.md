# Ask Stock Answer Playbook

This playbook keeps Ask Stock answers aligned with the user's question before any score or Stock Lab detail is shown. It borrows the useful parts of public stock-analysis skills: intent routing, 3D evidence separation, and trading-process gates, while keeping all provider access server-side and deterministic analysis inside `backend/src/marketdesk/analysis/`.

## Global Rules

1. Answer the asked question first. Do not start with a participation verdict unless the user asks what to do.
2. Every answer starts with `结论：`, then gives the minimum evidence needed to make that conclusion understandable.
3. Separate proven local evidence from unverified external causes. Never invent a news reason for a price move.
4. Use stock scores as support, not as the answer. The score explains confidence; it does not replace reasoning.
5. When evidence is missing, say what is missing and where the user should verify next.
6. Keep user-facing wording as research assistance, not buy/sell instruction.

## Intent Routes

| Intent | User asks | Answer first | Must not do |
| --- | --- | --- | --- |
| `movement` | 为什么大涨/大跌、异动、怎么回事 | Quantify 1/5/20-day move, then explain price structure, volume, flow, drawdown, and board context | Do not answer with `暂不参与` or target price first |
| `risk` | 风险、利空、隐患、下跌风险、回撤风险 | Name the main risk and invalidation line | Do not pretend it explains a recent move |
| `trend` | 趋势、技术、均线、MACD、RSI | State trend direction and key drivers | Do not turn it into a buy/sell answer |
| `valuation` | 估值、PE/PB、贵不贵、便宜、同行比较 | State valuation constraint and comparable evidence | Do not claim cheap equals buyable |
| `fundamental` | 基本面、财报、业绩、利润、营收、现金流、负债、ROE | State fundamental-quality evidence and missing financial context | Do not use only price action as fundamental proof |
| `catalyst` | 消息面、公告、研报、题材、催化、龙虎榜 | State verified catalyst evidence and what still needs source checks | Do not invent a catalyst when the provider has no evidence |
| `action` | 能不能买/卖、仓位、止损、止盈、目标价、操作 | Give action discipline, entry/stop/take-profit constraints | Do not promise price targets |
| `portfolio` | 我的持仓、组合、调仓、仓位偏离 | Use only current-account holdings | Do not leak other accounts or default holdings |
| `screening` | 找股票、低估值、题材股、推荐候选 | Return candidates as research leads | Do not call them final recommendations |
| `overview` | 怎么看、综合分析 | Summarize final gate, core reason, main risk, next step | Do not dump every Stock Lab section |

## Regression Examples

- `最近大业股份怎么大跌` -> `movement`; answer recent decline evidence and possible local structural causes.
- `大业股份基本面怎么样` -> `fundamental`; answer basic quality,公告研报/财务缺口, not trading action.
- `大业股份有什么公告催化` -> `catalyst`; answer verified catalyst evidence or say no verified catalyst.
- `贵州茅台未来可能涨到多少` -> `action`; answer pressure/take-profit discipline, not a promised target.

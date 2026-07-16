# Five-Role Professional Stock Terminal Design

## Decision

StockTS is a personal A-share research and risk-control terminal. It is not an order-entry system, a news portal, or a model-score showroom. Every visible conclusion must answer four questions: what is known, what is inferred, what must happen next, and what invalidates the view.

The selected approach combines a strict research truth contract with task-specific workspaces. It rejects both a full institutional rebuild and a visual-only redesign.

## Five-Role Adversarial Review

| Role | Strongest objection | Accepted decision |
| --- | --- | --- |
| Stock analyst | Price continuation is being presented too close to investability; unsupported risk budgets and hit rates look executable | Market remains factual; opportunity language becomes conditional observation; unsupported precision is removed |
| UI designer | The four native pages share one SaaS-like template and lose their different jobs | Keep one protocol but give every module a distinct question, horizon, first action, and information order |
| Data engineer | A fresh generation timestamp can hide stale underlying facts; production sources can silently degrade | Freshness uses fact `as_of`; source/demo provenance remains an explicit future P0 |
| Strategy lead | A full factor and position engine now would create false precision | Ship only deterministic semantic and evaluability gates; defer portfolio sizing and model optimization |
| Daily user | More indicators and protocol fields increase reading time | Show one compact session line in plain Chinese; keep evidence details folded and cap visible findings |

## Product Architecture

```text
Validated facts
  -> descriptive interpretation
  -> conditional forecast
  -> portfolio-relative action
  -> immutable feedback
```

The layers must not leak into each other:

- Market facts: `as_of`, coverage, indices, breadth, volume, limit-up/down and observed themes. No future stock selection, account position or buy/sell wording.
- Stock memo: company and price evidence, counter-evidence, unknowns, confirmation, invalidation and review event. A score never replaces evidence.
- Opportunity forecast: horizon, baseline, support, counter-evidence, confirmation, invalidation and review date. It is a research candidate, not an investment instruction.
- Portfolio action: risk order and relative exposure only until account assets and cash are known. No account percentage is inferred from the stock basket.
- Feedback: only machine-evaluable forecasts enter hit-rate denominators. Zero evaluable samples means “暂无可回评样本”, never “0% hit rate”.

## Workspace Contract

| Workspace | User question | Statement type | Default horizon | Primary output |
| --- | --- | --- | --- | --- |
| Daily market | 今天市场发生了什么？ | Fact | Current session | Breadth, indices, volume, observed themes and missing data |
| Portfolio | 今天先处理哪只持仓？ | Relative action | Today / next review | Risk-ordered positions and prohibited actions |
| Stock | 这只股票现在怎么看？ | Research memo | 1-20 trading days | Thesis, strongest support, strongest counter, confirmation and invalidation |
| Opportunity | 今天值得继续研究哪些股票？ | Conditional forecast | T+1 / T+3 / T+5 | Forward watchlist with reasons, risks and exit rules |

Each native workspace displays one plain-language session line immediately under the header:

`结论类型 | 适用周期 | 数据时点 | 证据覆盖`

The labels are user language, not raw provider or protocol fields. Stale or blocked data overrides every score and action.

## Analysis Rules

### Market

- Use descriptive labels: `宽度偏强`, `宽度均衡`, `宽度偏弱`, `数据不足`.
- Keep market-regime calculations as internal interpretation inputs, but do not expose `risk_budget`, `structure attack`, `buy`, `sell` or future-candidate language on the market page.
- Market movers explain the observed move and risk only. Forecast confirmation and invalidation belong to Opportunity.

### Opportunity

- Rename the highest currently supported stage from `可进入投资候选` to `价格延续观察`.
- Scores represent ordering, not probability, target return or position size.
- News and announcements do not increase positive evidence merely by existing.
- Top10 is a maximum. The system does not lower gates to fill ten rows.

### Freshness

- Snapshot freshness is based on the earliest usable fact date, preferring payload `as_of` over `generated_at`.
- A newly regenerated payload with old facts is stale.
- Historical snapshots may be delivered as reference, but cannot inherit current actions.

## Interaction And Visual Rules

- Desktop 1440-1920 is primary: 214px navigation, maximum 1580px research canvas.
- Main titles are 28-32px; the first module-specific evidence section must appear within a 900px-high screen.
- Use market red/green only for price direction. Research status uses ink, copper, amber and gray.
- Replace “当前判断 / 现在怎么做 / 最大风险” with “一句话结论 / 今天怎么做 / 最需要防什么”.
- Remove the redundant “先看风险” jump because risk is already visible.
- Keep complete evidence folded, first-run auto analysis, safe DOM rendering, keyboard focus, reduced motion, account isolation and public read-only behavior.

## Deferred Work

- Atomic multi-artifact bundle manifests and removal of silent sample fallback.
- Full fact-level lineage and source timestamps.
- Account asset/cash model and portfolio sizing.
- Relative industry benchmarks, valuation history and expectation-revision factors.
- Intraday rules, automated weight tuning and automatic trading.

## Acceptance Criteria

- A fresh `generated_at` cannot make an old `as_of` snapshot current.
- Market public text contains no risk-budget, account-position, investment-candidate or buy/sell wording.
- Opportunity public text no longer contains `可进入投资候选`.
- Negative news/announcement presence does not raise positive evidence coverage.
- Each workspace exposes its statement type and horizon in plain Chinese.
- Existing research API, authentication, snapshot fallback, scheduled refresh and privacy tests remain green.

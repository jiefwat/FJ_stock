# Ask Stock Workbench Design

Date: 2026-07-25
Status: Approved under delegated product authority

## 1. Decision

Add an authenticated Ask Stock page without changing the existing Market Desk layout. The first release uses a hybrid answer path:

1. Questions containing one A-share name or six-digit code are answered from the existing full-market snapshot and deterministic Stock Lab dossier.
2. Questions without a locally identifiable stock are sent to the existing optional semantic-research provider as a natural-language stock screen.
3. If semantic research is not configured, the application returns an explicit unavailable state and asks the user to include a stock name or code. It must not invent an answer.

The feature is a research interface, not an unrestricted chatbot and not an automated trading system.

## 2. User Experience

Add one `问股` item to the existing sidebar and one `/ask` route. Keep the current warm-paper, deep-green, evidence-ledger visual language and leave all existing page composition unchanged.

The page contains:

- a short question input with examples such as `贵州茅台现在主要风险是什么` and `600519 的趋势和止损纪律`;
- suggested prompts for risk, trend, valuation, and action-discipline questions;
- a result header showing the matched stock, answer intent, market observation time, and data source;
- a concise answer followed by evidence, risk, and next-action sections;
- a bounded table for semantic screening results when that provider is configured;
- explicit pending, validation, unavailable, and provider-error states.

Only the latest submitted question is displayed. Conversation history, streaming text, Markdown execution, file upload, and free-form model chat are outside this release.

## 3. Backend Boundaries

Browser code continues to depend only on `/api/v1/*`. Provider access remains under `backend/src/marketdesk/providers/`, and deterministic answer composition remains inside `MarketService` or a pure analysis module.

Add `POST /api/v1/ask-stock` with this request boundary:

```json
{"question": "贵州茅台现在主要风险是什么"}
```

The question is trimmed, must contain 2 through 160 visible characters, and is never logged with credentials. Application authentication middleware protects the endpoint.

For a locally matched stock, return:

```json
{
  "kind": "stock_analysis",
  "question": "贵州茅台现在主要风险是什么",
  "intent": "risk",
  "symbol": "SH.600519",
  "name": "贵州茅台",
  "answer": "...",
  "evidence": ["..."],
  "risks": ["..."],
  "next_actions": ["..."],
  "observed_at": "2026-07-25T01:00:00Z",
  "source": "本地行情快照 + 确定性分析",
  "disclaimer": "研究辅助信息，不构成投资建议。"
}
```

The intent classifier is deterministic:

- risk keywords select `risk`;
- trend and technical keywords select `trend`;
- valuation and comparison keywords select `valuation`;
- buy, sell, position, stop, and action keywords select `action`;
- all other named-stock questions use `overview`.

Stock resolution searches exact six-digit codes first, then normalized names contained in the question. If multiple stocks match, return HTTP 422 and require one stock per question. If no stock matches and semantic research is unavailable, return HTTP 503 with a bounded, user-readable explanation.

## 4. Optional Semantic Screening

Extend the existing `IwencaiProvider`; do not introduce browser scraping or expose a Cookie to frontend code. The configured provider receives only the natural-language question, query type `stock`, and a result limit.

Normalize provider payloads into a bounded response:

- at most 20 rows;
- at most 12 columns;
- JSON scalar cell values only;
- stock code and name columns first when recognizable;
- no raw provider headers, cookies, tokens, HTML, or unbounded nested objects.

The provider remains optional. A missing endpoint or API key must not affect named-stock questions, market refresh, holdings, opportunities, or Stock Lab.

## 5. Answer Honesty

- Answers reuse the existing `StockDossier`; no second scoring algorithm is introduced.
- Missing evidence remains missing and is shown as a limitation.
- The result includes the market observation time so delayed snapshots cannot look real-time.
- The answer never claims certainty or promises future returns.
- Provider failure never falls back to fabricated semantic results.
- Question text is rendered as plain text; the frontend does not inject returned HTML.

## 6. Verification

Backend tests cover request validation, authentication, code/name resolution, every intent branch, ambiguous stocks, semantic-provider fallback, result bounding, and provider failure.

Frontend tests cover navigation, suggested prompts, pending state, named-stock answer rendering, semantic table rendering, and unavailable/error messaging. The production build must remain usable at desktop widths and 390 px without horizontal document overflow.

Acceptance requires `make verify`, a production-build browser workflow, an authenticated live request for a named stock, an anonymous 401 check, and confirmation that `/opt/aster-market/data` remains untouched by deployment.

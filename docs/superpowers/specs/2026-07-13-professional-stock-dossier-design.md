# Professional Stock Dossier Design

**Date:** 2026-07-13

**Scope:** Replace the shallow and duplicated single-stock analysis surface with one auditable professional research dossier.

## 1. Problem

The current stock workspace contains a research memo, a legacy trade-plan conclusion, a multi-role table, a dimension table, and raw evidence tables. It exposes many sections but still gives limited guidance because:

- the memo verdict is driven mainly by missing-block counts rather than the direction and severity of actual evidence;
- available absolute financial fields are ignored when growth-history fields are absent;
- negative PE is displayed as a multiple instead of being classified as economically invalid;
- reported valuation values are not cross-checked against price and per-share fundamentals;
- technical evidence is shown but does not materially affect the research stance;
- turnover and estimated transaction activity can look like institutional fund-flow evidence;
- risk events are listed but do not consistently constrain the action and position budget;
- the new memo and legacy analysis chain can present overlapping or conflicting conclusions;
- scenario and role text remains generic even when the stock-specific evidence is materially different.

For the current `603278` snapshot, the system has 120 daily bars, negative EPS, operating loss, net loss, positive operating cash flow, net assets per share, valuation fields, turnover evidence, announcements, news, and controlling-shareholder pledge evidence. The page still describes the financial block as completely missing. This is the primary acceptance fixture for the redesign.

## 2. Outcome

The stock workspace becomes an investment-committee one-pager that answers, in order:

1. What is the current action?
2. Why is that action justified?
3. What evidence would upgrade the stance?
4. What evidence would downgrade or invalidate it?
5. How much risk may be allocated if the trigger occurs?
6. What must be checked next, and when?

The output is conditional research guidance, not an unconditional recommendation or return promise.

## 3. Selected Approach

Create a deterministic `stock_dossier` research layer using existing typed data. The layer produces one directional, auditable decision object consumed by the stock workspace.

Rejected alternatives:

- UI-only expansion leaves shallow decision logic unchanged.
- LLM-authored long reports can appear professional while inventing unsupported links between incomplete data. LLM output may be added later as a clearly separated commentary layer, but it is not the source of the dossier decision.

## 4. Scope

### In Scope

- deterministic financial, valuation, technical, capital, event, and portfolio diagnostics;
- a unified research stance and evidence grade;
- stock-specific upgrade, downgrade, and invalidation conditions;
- separate guidance for non-holders and current holders;
- a risk register and evidence ledger;
- a redesigned stock workspace centered on a decision rail;
- responsive desktop and mobile rendering;
- regression tests for complete, partial, stale, loss-making, valuation-conflict, and high-risk-event cases;
- removal of duplicated primary conclusions from the stock page.

### Out Of Scope

- broker integration or live order placement;
- automatic PDF announcement interpretation;
- model-generated target prices;
- uncalibrated numeric scenario probabilities;
- a new external market-data provider;
- changing the market, portfolio, or opportunity workspace beyond the stock links they already expose.

## 5. Architecture

Add `src/stock_ts/research/stock_dossier.py` with typed immutable output models:

- `DossierVerdict`: stance, action, evidence grade, confidence, horizon, thesis, strongest evidence, strongest counter-evidence, and next review.
- `DecisionStep`: label, state, condition, and consequence for the decision rail.
- `DiagnosticBlock`: block name, status, conclusion, facts, risks, and source limitation.
- `RiskItem`: severity, category, evidence, consequence, and monitoring condition.
- `PositionGuidance`: audience, current action, position cap, risk budget, entry trigger, add trigger, reduce trigger, invalidation, and prohibited action.
- `ProfessionalStockDossier`: identity, verdict, decision steps, diagnostics, risks, scenarios, position guidance, and evidence ledger.

The builder receives:

```text
StockRawData
+ TechnicalProfile
+ EventRadar
+ Holding | None
+ ResearchInputQuality
+ market/sector context strings already calculated by the Web orchestration
-> ProfessionalStockDossier
```

`web.py` remains orchestration only. Research rules live in `stock_dossier.py`; rendering lives in `webapp/stock_workspace.py`.

The existing `StockResearchMemo` remains available for compatibility and supporting tests, but the stock workspace uses the dossier as its single primary conclusion. Legacy trade-plan and multi-role outputs may appear only in a collapsed evidence drawer and may not create a second top-level verdict.

## 6. Evidence Rules

### 6.1 Evidence Grade

Evidence grade measures research completeness, not attractiveness:

| Grade | Minimum evidence |
| --- | --- |
| A | fresh quote, at least 60 bars, at least three financial periods, comparable valuation, usable events, and portfolio context when held |
| B | fresh quote, at least 60 bars, a usable financial snapshot or history, and usable events |
| C | fresh quote and usable price history, but financial, valuation, or event evidence remains materially incomplete |
| D | stale or blocked quote, missing usable price history, or a hard data-quality blocker |

Confidence is derived from transparent completeness components. It must not be presented as probability of price appreciation.

The completeness score uses fixed weights:

- fresh quote: 25;
- at least 60 bars: 15;
- usable financial snapshot: 15;
- at least three comparable financial periods: 10;
- comparable valuation: 10;
- usable event evidence: 10;
- correctly identified capital-flow or transaction-activity source: 5;
- sector context: 5;
- holding context when the stock is held, or confirmed non-holding status: 5.

The score is capped at 100. A stale or blocked quote overrides the score to 0.

### 6.2 Financial Snapshot

A financial snapshot is usable when at least one of these fields is present:

- `eps`
- `operating_revenue`
- `operating_profit`
- `net_profit`
- `operating_cash_flow`
- `net_asset_per_share`
- `total_assets`
- `shareholder_count`

The dossier may derive ratios only from fields with compatible units:

- operating margin = operating profit / operating revenue;
- net margin = net profit / operating revenue;
- cash conversion = operating cash flow / net profit only when net profit is positive;
- price-to-book cross-check = latest close / net assets per share when both are positive.

When profit is negative and operating cash flow is positive, the conclusion is "cash flow is positive but accounting profit remains negative". It must not be described as healthy cash conversion.

Absolute snapshot facts support a current-state diagnosis. Only two periods support period-over-period change, and only at least three aligned periods support continuous improvement or weakening language.

### 6.3 Valuation

- PE is economically meaningful only when PE is positive and profit evidence is not negative.
- Negative PE is rendered as "loss-making; PE is not a valid valuation anchor".
- Reported PB is cross-checked against latest close / net assets per share.
- A relative PB difference greater than 30% creates a valuation-source conflict. The dossier uses the derived value as a cross-check fact, marks valuation degraded, and does not call the stock cheap.
- Historical PE percentile requires at least 20 unique positive observations.
- A low absolute multiple without a historical or peer reference is not labeled undervalued.

### 6.4 Technical Regime

When enough bars exist, calculate:

- 5-, 20-, and 60-session return;
- distance from the 60-session high and low;
- MA5, MA10, MA20, support, resistance, RSI14, MACD state, and volume ratio from the existing technical profile;
- 20-session realized volatility when at least 21 closes exist;
- current state as trend continuation, rebound attempt, range, weakening trend, or breakdown risk.

A one-day rebound after a material 20- or 60-session decline is a rebound attempt, not a confirmed trend reversal.

Minimum classification rules:

- `rebound attempt`: latest or 5-session return is positive while 20-session return is at most -10%;
- `weakening trend`: close is below MA20 and 20-session return is negative;
- `breakdown risk`: close is within 3% of the 20-session low and below MA20;
- `trend continuation`: close is above MA20, 20-session return is positive, and volume ratio is at least 1.0;
- `range`: none of the stronger conditions applies.

### 6.5 Capital Evidence

- `main_net_inflow*` fields may be described as main-fund flow when their source supports that interpretation.
- turnover, transaction amount, inside/outer volume, and derived volume-price signals are transaction-activity evidence only.
- one-session activity never proves persistence.
- a high turnover rate with a weak technical regime is treated as disagreement or distribution risk, not automatically as positive attention.

### 6.6 Event Risk

Risk events are categorized and prioritized:

| Severity | Examples | Consequence |
| --- | --- | --- |
| Critical | regulatory penalty, material litigation, delisting or solvency signal | block new entry until resolved |
| High | controlling-shareholder high pledge, reduction, guarantee, material financial assistance, major loss warning | cap stance at wait/risk-control |
| Medium | ordinary volatility, non-material uncertainty, unverified catalyst | require confirmation |
| Low | neutral operational update | record without changing stance |

Title classification remains a screening tool. The dossier always states that the original announcement must be reviewed.

A controlling-shareholder pledge is high severity when the disclosed cumulative pledge is at least 50% of that holder's position. When the title signals a pledge but the percentage is unavailable, it remains high severity with an explicit "percentage pending original-document review" limitation. Percentage extraction may use announcement/news title and summary text, but the extracted value must remain linked to its source text.

## 7. Verdict And Action Rules

Available stances:

- `数据暂停`: Grade D or stale quote; no current action.
- `风险规避`: critical event risk, or high event risk combined with loss-making and weak technical structure.
- `等待修复`: evidence is usable but technical or financial conditions do not support entry.
- `条件观察`: evidence is at least Grade B and explicit upgrade conditions exist.
- `持仓管理`: current holding exists; output prioritizes reduce, hold, add, and invalidation conditions relative to cost and risk budget.

The decision rail contains exactly five steps:

1. current state;
2. upgrade trigger;
3. add/confirmation trigger;
4. downgrade trigger;
5. invalidation/exit.

For a non-holder:

- blocking or high combined risk produces a 0% new-position cap;
- Grade C produces observation only;
- Grade B or A may allow a trial position no greater than 5% only after both price and evidence triggers occur;
- prohibited actions explicitly include chasing a one-day rebound, averaging down before invalidation is repaired, and treating low PB alone as a reason to buy.

For a holder:

- guidance incorporates cost, current P/L, technical invalidation, event severity, and available portfolio context;
- the page may recommend reduce/hold/conditional add, but never assumes the user's cost is bullish evidence;
- no position increase is allowed while a blocking risk remains unresolved.

## 8. Scenario Rules

Keep optimistic, base, and adverse scenarios without numeric probabilities. Each scenario must contain:

- stock-specific premise;
- observable confirmation signals;
- action;
- invalidation;
- evidence source.

Generic phrases such as "profit improves and price resonates" are insufficient when concrete stock evidence is available.

## 9. Workspace Design

The visual direction is a disciplined investment-committee worksheet inside the existing StockTs design system. The signature element is the decision rail; no new decorative theme is introduced.

Desktop structure:

```text
identity / freshness / source
decision brief: stance + thesis + evidence grade + action
--------------------------------------------------------
decision rail                     risk register
current -> upgrade -> add         severity / evidence
        -> downgrade -> exit      consequence / monitor
--------------------------------------------------------
financial + valuation             technical + capital
event + portfolio                 three scenarios
--------------------------------------------------------
evidence ledger and raw details (collapsed)
```

Mobile order:

1. identity and freshness;
2. decision brief;
3. decision rail;
4. position guidance;
5. risk register;
6. diagnostics;
7. scenarios;
8. evidence ledger.

Visual rules:

- stance and action use the strongest typography, not a generic score;
- evidence grade is always labeled as completeness;
- adverse risk is shown before optimistic catalysts;
- exact price conditions use tabular numerals;
- no more than one expanded table appears before the evidence drawer;
- keyboard focus, reduced motion, and mobile overflow remain supported;
- existing StockTs colors and typography remain authoritative.

## 10. Error And Safety Behavior

- stale quotes force `数据暂停`, confidence 0, position cap 0%, and refresh instructions;
- missing financial history does not erase usable absolute financial facts;
- missing events never means no event risk;
- conflicting valuation sources are surfaced, not silently resolved as cheap;
- no conclusion may use a holding cost as evidence that the business is attractive;
- no raw credential, token, private account value, or private holding is added to public diagnostics;
- every action remains conditional and includes invalidation.

## 11. Testing

Add focused tests for:

- negative profit and negative PE;
- positive cash flow with negative profit;
- reported-versus-derived PB conflict;
- complete three-period improvement;
- stale quote hard stop;
- 5/20/60-session trend and drawdown classification;
- high-risk pledge/reduction events constraining position guidance;
- transaction activity not being labeled main-fund flow;
- held versus non-held guidance;
- stock-specific scenarios;
- one primary verdict and no duplicated legacy conclusion;
- desktop and mobile semantic structure;
- real `603278` snapshot smoke output.

Verification commands:

```bash
make lint
PYTHONPATH=src .venv/bin/pytest -q tests/test_stock_dossier.py tests/test_web_stock_dossier.py
PYTHONPATH=src .venv/bin/pytest -q
```

The six documented repository baseline failures remain separately reported until fixed.

## 12. Acceptance Criteria

- The stock page has exactly one primary stance and one action contract.
- `603278` explicitly shows loss-making status, invalid negative PE, the PB source conflict, high pledge/reduction risk, multi-horizon price damage, and conditional risk guidance.
- Available absolute financial facts are no longer labeled as completely missing.
- Technical, financial, valuation, capital, and event evidence materially affect the stance.
- A one-day rebound cannot be labeled a confirmed reversal after a material multi-session decline.
- Turnover evidence cannot be presented as institutional net inflow.
- Non-holders and holders receive different, bounded guidance.
- Every entry or add condition has a downgrade and invalidation condition.
- Missing or stale data reduces guidance rather than causing invented confidence.
- The page remains usable on desktop and mobile.

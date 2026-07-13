# Professional Core Workspaces Design

Date: 2026-07-13

## 1. Goal

Upgrade the remaining three daily decision surfaces so they match the professional standard of the stock dossier:

1. Daily market defines the market regime and risk budget.
2. Portfolio converts that budget into an ordered risk-treatment queue.
3. Opportunities filters the candidate universe before assigning research priority.

The page remains a read-only research terminal. It does not place orders, promise returns, invent target prices, or treat a score as a probability.

## 2. Scope

In scope:

- `每日大盘`: tighten the existing market-regime workspace and expose one authoritative risk gate.
- `我的持仓`: replace generic bullish/light/watch summaries with a portfolio committee verdict, ordered treatment queue, risk budget, exposure register, and per-position boundaries.
- `热点机会`: replace recommendation-first language with a gate-first research funnel, explicit candidate states, exclusion reasons, and source coverage.
- Propagate stale/blocked quote status into portfolio and opportunity behavior.
- Preserve account isolation, public read-only mode, existing edit forms, and stock-analysis deep links.

Out of scope:

- New market data providers or broker integration.
- Automatic trading, order simulation, or portfolio rebalancing execution.
- LLM-generated core conclusions.
- Uncalibrated upside probability, target price, or certain-return language.
- Reworking account management, notification delivery, DSA, or the server data pipeline.

## 3. Approaches Considered

### A. Visual cleanup only

Reuse all current copy and merely improve spacing, colors, and cards.

Rejected because the opportunity page can say `排序暂停` while still showing `推荐股票`, and the portfolio page can emit numeric actions when the global quote is stale. Styling cannot resolve contradictory behavior.

### B. Module-specific decision dossiers on existing domain models

Keep `MarketRegimeAssessment`, `PortfolioAnalysisReport`, `PortfolioAdvice`, and `CandidatePoolReport`, then add focused portfolio/opportunity decision models and renderers.

Chosen because it makes safety rules testable without replacing providers or analysis services. Each module keeps one responsibility and can be rolled back independently.

### C. One generic cross-module decision engine

Create a shared rule graph for market, portfolio, stock, and opportunity decisions.

Rejected as premature abstraction. The modules have different evidence, actions, and failure semantics; a generic engine would hide those distinctions and increase regression risk.

## 4. Cross-Module Decision Flow

```text
Data quality / quote freshness
            |
            v
MarketRegimeAssessment
  stage + risk budget + invalidation
       |                         |
       v                         v
Portfolio dossier          Opportunity dossier
risk treatment queue       candidate eligibility funnel
       |                         |
       +----------+--------------+
                  v
          Professional stock dossier
          six-dimension verification
```

The market workspace is the authority for risk budget. Portfolio and opportunity modules may further reduce risk, but they must not silently relax the market gate.

## 5. Shared Safety Contract

When quote status is `stale` or `blocked`:

- Market stage is `数据暂停`, confidence is `0`, and risk budget is `0%`.
- Portfolio may show ledger facts, historical cost, and exposure, but all price-dependent actions, target weights, stop lines, and adjustment amounts become `待刷新`.
- Opportunity ranking stops. Every candidate becomes `待补数据`; no candidate may appear under recommendation, verification-open, or top-ranked wording.
- The page must not display old numeric trigger levels in a primary decision surface.
- Refresh and data-center actions remain available.

When data is fresh but incomplete:

- The market assessment may be degraded but remains explicit about missing dimensions.
- Portfolio actions may be conditional only when the corresponding price and position evidence is present.
- Opportunity candidates with incomplete price, risk, or source evidence stay in `待补数据` and do not participate in research priority ordering.

## 6. Daily Market Workspace

The existing typed `MarketRegimeAssessment` remains authoritative. The upgrade is a contract and presentation refinement, not a second market model.

Primary surface:

- market stage;
- risk budget;
- evidence completeness;
- thesis;
- strongest support;
- primary risk;
- invalidation condition;
- next review time.

Decision rail:

1. Current regime.
2. Risk-on confirmation.
3. Position-budget consequence.
4. Downgrade trigger.
5. Invalidation/reassessment.

Supporting sections remain trend/breadth/liquidity/style/sentiment diagnostics, breadth statistics, sector heatmap, event sentiment, scenarios, and evidence audit. When stale, raw statistics remain audit evidence but are visually secondary and never restore an action recommendation.

## 7. Portfolio Dossier

### 7.1 Model

Create a portfolio research model with:

- `PortfolioVerdict`: state, action, risk budget, confidence, thesis, primary risk, next review.
- `PortfolioMetric`: market value, total P/L, top-position concentration, top-sector concentration, weak-position count.
- `PortfolioQueueItem`: priority, state, stock, current weight, cost/P&L context, reason, trigger, invalidation.
- `PortfolioExposure`: name, weight, severity, consequence.
- `PortfolioBoundary`: current action, target range, reduce trigger, invalidation, prohibited action.

The builder consumes existing portfolio analysis/advice plus market assessment and quote status. It does not recalculate provider data in the renderer.

### 7.2 Classification

Queue order is deterministic:

1. `必须处理`: high risk, downtrend, concentration breach, or explicit reduce action.
2. `重点观察`: conflicting evidence or near-boundary position.
3. `可继续持有`: risk within budget and no invalidation breach.
4. `待补数据`: missing or stale quote evidence.

Cost basis may explain P/L and risk distance. It must never become bullish evidence or justify averaging down.

### 7.3 Layout

Desktop order:

1. One portfolio committee verdict.
2. Risk metrics and risk budget.
3. Ordered treatment queue.
4. Industry and single-name exposure register.
5. Per-position execution boundaries.
6. Existing edit form and supporting position analysis.

Mobile converts the queue and boundaries to stacked cards. Edit controls remain private/local only.

## 8. Opportunity Dossier

### 8.1 Model

Create an opportunity research model with:

- `OpportunityGate`: state, action, market constraint, data state, scanned count, eligible count, next step.
- `FunnelStage`: scanned, evidence-ready, risk-excluded, watch, verification-open.
- `CandidateDecision`: state, strategy, evidence, counter-evidence, data date/status, next verification, exclusion reason.
- `OpportunityRisk`: market, sector, event, liquidity, or data-quality exclusion.

Candidate states are mutually exclusive:

- `可验证`: fresh, evidence-ready, no blocking risk; this is permission to open the stock dossier, not permission to buy.
- `只观察`: incomplete confirmation or market budget does not support active verification.
- `风险排除`: explicit event, liquidity, sector, or price-structure exclusion.
- `待补数据`: stale or missing price/source evidence.

### 8.2 Gate Rules

- Stale/blocked quote status forces `数据暂停`; eligible count is zero.
- Market `数据暂停` or risk budget `0%` blocks verification-open candidates.
- Defensive/risk-release regimes may keep candidates visible for research but downgrade aggressive breakout/chase strategies to `只观察`.
- A candidate with unreliable price evidence cannot be ranked.
- Candidate score is retained internally as a research-priority input, never shown as buy probability or recommendation.

### 8.3 Layout

Desktop order:

1. One opportunity gate verdict.
2. Funnel counts and strategy lanes.
3. Verification-open/watch candidate cards.
4. Risk-exclusion register.
5. Filter/source coverage ledger.
6. Sector context.

Primary labels use `研究候选`, `进入个股分析`, and `继续验证`. The primary page must not use `推荐买入`, `推荐股票`, or generic buy/sell guidance.

## 9. Visual Direction

Preserve the established navy, warm paper, amber, and restrained red/green terminal language. Match the stock dossier rather than introducing a new theme.

- One high-contrast verdict per module.
- Large state/action typography, not a large score.
- Mono numerals for dates, weights, P/L, and counts.
- Risk register before optimistic scenarios or candidates.
- Thin decision rails and editorial section labels instead of repeated generic KPI cards.
- Motion is limited to one load reveal and disabled under reduced-motion preferences.
- At 760px and below, all primary grids stack to one column; tables that remain must scroll inside their own container without widening the document.

## 10. Error And Empty States

- Empty portfolio: show ledger setup and no calculated action.
- Missing cost: show `成本待补录`; do not calculate relative P/L from zero.
- Empty candidate pool: show zero funnel counts and refresh/source instructions.
- Missing metadata: display `扫描范围未知`; never substitute a fabricated universe size.
- Renderer escapes all user/provider text.

## 11. Testing

Domain tests:

- stale quote hard-stops portfolio and opportunity actions;
- portfolio queue priority and concentration risk;
- no division by zero for missing cost;
- candidate states are mutually exclusive;
- blocked candidates cannot appear as verification-open;
- market risk budget cannot be relaxed downstream;
- risk exclusions preserve evidence and reason.

Web tests:

- exactly one primary verdict per module;
- opportunity page contains no recommendation/buy language;
- stale opportunity page exposes zero eligible candidates and no ranked table;
- stale portfolio page contains no numeric stop/target action in the primary surface;
- private edit controls and account isolation remain unchanged;
- responsive CSS covers verdict, queue, funnel, exposure, and reduced motion.

Quality gates:

- focused market/portfolio/opportunity tests;
- Python 3.9 compatibility for new typed models;
- Ruff;
- full pytest compared with the documented six-failure baseline;
- local real-snapshot HTTP and desktop/mobile browser smoke;
- review before merge and deployment.

## 12. Acceptance Criteria

- A user can move from market regime to portfolio risk treatment to opportunity verification without encountering contradictory actions.
- Stale data never produces a current buy, sell, target-weight, or ranked-candidate instruction.
- Portfolio treatment order is explicit and tied to concentration, trend, P/L, and invalidation evidence.
- Opportunity candidates show both supporting evidence and counter-evidence, plus a clear next verification step.
- All three modules use one primary verdict and preserve detailed evidence as supporting layers.
- Local `main`, GitHub `main`, and the deployed server commit match after release.

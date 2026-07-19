# Market Intelligence Workbench Design

Date: 2026-07-19
Status: Approved by delegated product authority

## 1. Product Decision

Build a local-first A-share research workbench. A shares are the decision market; Hong Kong, US, Korean, and macro data are supporting signals. The product is a decision console rather than a generic financial dashboard or an automated trading system.

The primary interaction model is a fixed, auditable workflow with contextual AI-style explanations:

1. Determine the market regime and risk budget.
2. Identify strong or improving sectors.
3. Pass candidates through explicit opportunity gates.
4. Inspect one stock through price, fundamentals, capital, events, and risks.
5. Save a candidate to the watchlist and record a review note.

No page may present an unqualified buy or sell instruction. Candidate results are observation priorities supported by evidence and risk exclusions.

## 2. Goals and Non-goals

### Goals

- Answer four questions quickly: what is the market state, where are opportunities, why is a stock interesting, and what should be reviewed next?
- Cover market analysis, stock analysis, market opportunities, watchlist, and data health as first-class modules.
- Run locally without mandatory paid credentials.
- Show source, observation time, freshness, and missing-data state for every decision surface.
- Produce deterministic scores that can be tested independently of an LLM.
- Use optional AI only to explain structured facts, never to invent facts or silently replace failed data.
- Work as a desktop workbench with keyboard-accessible controls and clear loading, empty, stale, partial, and error states.

### Non-goals

- Automated trading, broker connectivity, or order placement.
- Tick-level or low-latency quantitative trading.
- Claims of guaranteed returns or direct buy/sell recommendations.
- Copying AInvest content or treating its public pages as a production data feed.
- Depending on undocumented logged-in browser sessions.

## 3. Information Architecture

The persistent navigation contains six modules:

1. **Today**: the daily command center.
2. **Market**: indices, breadth, liquidity, sectors, capital, and risk.
3. **Opportunities**: strategy funnel, risk exclusions, candidate ranking, and evidence.
4. **Stock Lab**: search and one-page stock dossier.
5. **Watchlist**: saved candidates, review status, and notes.
6. **Data Center**: provider availability, freshness, coverage, failures, and manual refresh.

Global controls include a stock search, market session timestamp, data quality badge, theme control, and refresh action. Mobile navigation becomes a compact bottom bar plus a module drawer.

## 4. Core User Flows

### 4.1 Daily Review

The user opens Today and sees, in order:

- market regime: risk-on, balanced, cautious, or risk-off;
- recommended exposure ceiling expressed as a research risk budget, not a trading order;
- the three most important market signals and their evidence;
- strongest and improving sectors;
- opportunity funnel counts: universe, passed liquidity, passed risk, final candidates;
- a short checklist linking directly to the relevant Market, Opportunities, and Stock Lab views.

The page must prioritize decisions over metric density. Every conclusion links to the data that produced it.

### 4.2 Opportunity Discovery

The user selects a preset such as trend continuation, improving sector, capital confirmation, or oversold rebound. The page shows the active rules before results.

The funnel applies these gates in order:

1. valid and fresh quote;
2. investable security: exclude ST, delisting-risk, suspended, and abnormal price records;
3. minimum liquidity and market-cap thresholds;
4. market-regime compatibility;
5. strategy conditions;
6. risk penalty and evidence completeness.

Each result displays total score, score decomposition, disqualifying risks, source time, and a Stock Lab action. Sorting and filtering never hide the active rule set.

### 4.3 Stock Research

The user searches by code or Chinese name. Stock Lab presents:

- identity and live quote;
- trend chart with MA5, MA20, and MA60;
- momentum, volume, volatility, support, and resistance;
- valuation and company snapshot;
- capital-flow summary;
- recent announcements and news when available;
- bull case, bear case, invalidation conditions, and missing evidence;
- a final research stance: strong watch, watch, neutral, avoid, or insufficient data.

The stance is deterministic and must be reproducible from the displayed inputs. The user can add the stock to the watchlist with a thesis and invalidation note.

### 4.4 Data Failure

If one provider fails, the application serves the most recent cached snapshot and marks it stale. If no snapshot exists, affected components show a bounded unavailable state while unrelated modules remain usable. No zero, empty list, or fabricated narrative may masquerade as valid data.

## 5. Module Content

### Today

- market regime and research risk budget;
- index spine and breadth lamps;
- sector heat strip;
- top three opportunities with score explanations;
- risk alerts and scheduled events;
- next-action checklist;
- global data freshness banner.

### Market

- Shanghai Composite, Shenzhen Component, ChiNext, CSI 300, SSE 50, STAR 50;
- optional Hang Seng, Hang Seng Tech, S&P 500, Nasdaq, KOSPI, US 10Y, and VIX signals;
- advancing, declining, unchanged, limit-up, limit-down, and median return;
- total turnover and turnover change versus the previous comparable session;
- sector ranking by return, breadth, turnover, and main capital flow;
- market regime score and transparent factor weights;
- source and freshness drawer.

### Opportunities

- preset strategies and a readable rule builder;
- funnel counts and excluded-reason distribution;
- ranked candidate table with component scores;
- sector concentration warning;
- candidate evidence drawer;
- CSV export of the visible filtered set;
- watchlist action.

### Stock Lab

- fuzzy search by code or name;
- price and technical chart;
- technical, valuation, capital, catalyst, and risk cards;
- evidence timeline;
- deterministic stance and invalidation conditions;
- watchlist note editor;
- optional contextual question box operating only on the loaded evidence packet.

### Watchlist

- status: new, researching, waiting, invalidated, archived;
- thesis, invalidation condition, target review date, and last reviewed timestamp;
- current quote and thesis-change alerts;
- no portfolio accounting or trade execution in the first release.

### Data Center

- provider status and response latency;
- last successful observation and fetch times;
- row coverage and missing-field ratios;
- cache age and stale thresholds;
- failure reason with a retry action;
- data provenance for every dataset;
- optional credential configuration guidance without exposing secrets.

## 6. Data Acquisition

### 6.1 Core, No-key Providers

| Dataset | Primary source | Fallback | Refresh policy |
| --- | --- | --- | --- |
| A-share and index quotes | Eastmoney public market endpoints | latest valid local snapshot | 60 seconds during market hours, 15 minutes otherwise |
| A-share universe and quote fields | Eastmoney market list | latest valid local snapshot | 5 minutes during market hours |
| Sector ranking and capital flow | Eastmoney sector endpoints | last snapshot | 5 minutes during market hours |
| Daily K-line | Eastmoney historical endpoints | local snapshot | on demand, then daily |
| Global macro | FRED public CSV | local snapshot | daily |
| Company/news links | public issuer/exchange or Eastmoney endpoints where available | unavailable state | 15 minutes to daily by dataset |

The application must send conservative timeouts, bounded retries, a descriptive user agent, and rate limits. Cached source payloads are normalized before use. External terms and production licensing must be reviewed before any public or commercial deployment.

### 6.2 Optional Enhanced Provider

When semantic research credentials are configured, the optional research provider can enrich:

- financial indicators;
- company operations and shareholder structure;
- announcements, events, and research reports;
- industry data;
- natural-language stock and sector screening.

This adapter is optional. Its absence cannot break core market, opportunity, stock-price, watchlist, or data-health flows. The SkillHub catalog is used to understand capability boundaries, not as proof that data APIs are accessible without credentials.

### 6.3 Explicit Reference-only Sources

AInvest informs interaction patterns such as industry-chain drill-down, macro regime, bubble/risk monitoring, event timelines, and source-linked topic narratives. Its pages and endpoints are not copied into the product and are not a production dependency.

## 7. Normalized Data Contracts

Every dataset includes:

- `source`: provider identifier;
- `observed_at`: the market timestamp represented by the value;
- `fetched_at`: local retrieval timestamp;
- `freshness`: fresh, delayed, stale, or unavailable;
- `coverage`: present fields divided by required fields;
- `errors`: structured provider or normalization errors;
- `items`: normalized business records.

Security identifiers use `market.code`, for example `SH.600519`, `SZ.000001`, and `US.NVDA`. Raw provider identifiers remain metadata only.

## 8. Scoring and Analysis

### 8.1 Market Regime

The zero-to-100 market score is deterministic:

- breadth: 30%;
- index trend: 25%;
- liquidity: 15%;
- sector participation: 15%;
- capital flow: 10%;
- external risk signals: 5% when available, otherwise weights renormalize.

Thresholds are: risk-off below 35, cautious 35-49, balanced 50-64, risk-on 65 or above. Missing factors reduce confidence and are never scored as zero.

### 8.2 Opportunity Score

After hard exclusions, the candidate score is:

- price and trend quality: 25%;
- relative sector strength: 25%;
- capital confirmation: 20%;
- liquidity and tradability: 15%;
- valuation sanity: 10%;
- catalyst evidence: 5% when available, otherwise weights renormalize.

The UI shows raw values, normalized factor scores, weights, penalties, and final score. A high score means high review priority, not predicted return.

### 8.3 Stock Stance

Stock stance combines trend, momentum, valuation, capital, catalyst, and risk evidence. A stance is `insufficient_data` when required quote history or more than 35% of required evidence is missing. The bull case, bear case, and invalidation conditions are templates populated from structured facts.

## 9. Technical Architecture

Use a single repository with strong module boundaries:

- `backend`: Python FastAPI API, provider adapters, normalization, scoring, SQLite cache, and tests;
- `frontend`: React, TypeScript, Vite, TanStack Query, and ECharts;
- `data`: local SQLite database and cache, excluded from Git;
- `scripts`: one-command setup, development start, production build, and verification;
- `docs`: product and operating documentation.

The browser never calls market providers directly. It calls versioned local APIs. Provider failures are converted into normalized partial-data responses, not unhandled HTTP 500 errors.

SQLite stores normalized snapshots, watchlist records, notes, provider health, and refresh logs. Secrets are read from `.env` and never returned by an API or rendered in logs.

## 10. Visual and Interaction Direction

Use an editorial market-desk visual language: warm paper surfaces, deep green navigation, restrained red and amber risk accents, and compact data typography. Avoid a generic blue SaaS dashboard and avoid decorative finance imagery.

Interaction requirements:

- progressive disclosure: conclusion first, evidence on demand;
- visible active filters and strategy rules;
- URL-addressable modules and stock pages;
- skeleton loading without layout shifts;
- keyboard focus and semantic labels;
- no color-only signals;
- desktop tables stay dense, readable, and avoid narrow-screen alternate layouts;
- every refresh action shows scope, completion, and resulting data time.

## 11. Verification and Acceptance

The release is incomplete until all gates pass.

### Data Gate

- required index set returns valid values or an explicit unavailable state;
- A-share universe has at least 90% required-field coverage on a normal market snapshot;
- timestamps and freshness classification are correct;
- no NaN, infinity, placeholder, or zero-as-missing value reaches a decision card;
- stale-cache fallback is verified by simulated provider failure;
- optional-provider absence does not break core flows.

### Functional Gate

- all six routes load;
- stock search resolves both code and name;
- scoring is reproducible in unit tests;
- strategy filters and exclusion reasons match fixtures;
- watchlist create, edit, status change, and delete work locally;
- CSV export contains the visible filtered candidates;
- refresh updates provider health and does not duplicate snapshots.

### Interaction Gate

- the daily path Today -> Opportunities -> Stock Lab -> Watchlist completes without dead ends;
- loading, empty, partial, stale, and error states are readable;
- desktop at 1440 x 900, 1536 x 900, and 1920 x 1080 has no clipped controls or unusable tables;
- primary actions are reachable by keyboard;
- data source and timestamp are available within one interaction from every conclusion.

### Engineering Gate

- backend unit and API tests pass;
- frontend unit tests pass;
- production frontend build passes;
- lint and type checks pass;
- a browser smoke suite passes against a clean local startup;
- the operator verification script exits non-zero on any failed gate.

If any core gate fails, fix or redesign the affected component and rerun the entire relevant gate. Startup success alone is not acceptance.

## 12. Local Operation

Provide these commands:

- `make setup`: install backend and frontend dependencies;
- `make dev`: start API and frontend development servers;
- `make test`: run backend and frontend tests;
- `make verify`: run lint, type checks, tests, builds, data-quality checks, and browser smoke checks;
- `make start`: build and start the production-style local application on a documented URL.

The README must document source limitations, optional semantic research configuration, troubleshooting, and how to interpret stale or partial data.

# Actionable Core Workspaces V3 Design

## Goal

Restore the useful market, portfolio, stock-selection, and opportunity operations that
were hidden when the native research workspaces replaced the legacy page, without
restoring the long legacy page or changing authentication, holdings isolation, data
providers, timers, or the local-primary research boundary.

## Diagnosis

- The market result ranks a small candidate set but does not expose a dedicated
  abnormal-move analysis based on the full scan sample.
- Holdings write handlers and legacy forms still exist, but the native page does not
  render them, pass the active edit code, or link holding rows to stock analysis.
- The stock page has a headline verdict but no compact execution record or visible
  in-page entry for another stock and the full-market opportunity scan.
- Opportunity candidates are rendered once from `opportunity-candidates` and again
  from `module_items`, while top candidate findings repeat the same names a third time.

## Product Shape

### Daily market

Keep the market pulse, breadth, and theme sections. Add an `market-movers` section
derived from the full candidate universe. Include stocks moving at least 3% in either
direction; if no stock reaches the threshold, show the five largest absolute moves and
label them as the scan-sample watch list.

Each row contains stock, theme, move, the strongest available cause, confirmation
condition, invalidation/risk, and a link to stock analysis. Causes must come from theme
strength, trend, volume, fund flow, or event evidence; a price change alone is not a
cause.

### Portfolio

Keep the native portfolio verdict and theme analysis. Add a server-rendered management
surface using the authenticated user's effective holdings path. It supports add, edit,
delete, and stock-analysis drill-down while preserving the existing `/holdings` POST
contract and per-user ledger isolation.

Every analyzed holding must state one action, one main reason, one confirmation
condition, and one invalidation condition. Holding quantity and cost remain in the
server-rendered authenticated management surface and are never sent to external
research.

### Stock analysis

Add a compact stock switcher at the top of the stock workspace with a code/name input,
an `分析这只股票` action, and an `进入全市场筛选` link. Add an
`stock-decision` section before the eight-dimension matrix containing the overall
action, strongest support, strongest counter-evidence, strengthen condition, and
invalidation condition.

The local evidence matrix remains the only source of verdict, action, and risk.

### Opportunities

Keep a short theme strip, then render one candidate list only. Do not render the same
candidates again under `今日机会` or repeat the top three candidates as findings.

The list columns are rank, stock, theme, score/move, inclusion reason, risk/invalidation,
confirmation condition, and action. Desktop uses a table-like list; mobile stacks each
row without horizontal page overflow. Each row links to stock analysis.

## Safety And Compatibility

- Keep login, account isolation, holdings POST handlers, routes, and hash navigation.
- Keep external research server-side and provider-neutral.
- Do not add a timer, service, database migration, or new writable endpoint.
- Preserve local fallback behavior when external research is unavailable.
- Use safe DOM creation and `textContent`; do not render API values through `innerHTML`.

## Acceptance Criteria

- Market shows pulse, breadth, themes, and a non-empty abnormal-move/watch list when a
  candidate scan exists.
- Portfolio visibly supports add/edit/delete and every holding links to stock analysis.
- Portfolio items contain action, reason, trigger, and invalidation text.
- Stock shows an overall execution record and both direct-stock and full-market entry
  points.
- Opportunity candidates appear once in a reasoned list and do not repeat under a
  second `今日机会` block.
- 1440 x 900, 1280 x 720, and 390 x 844 have no horizontal page overflow.
- No provider brand, capability id, trace field, gateway field, key, holding quantity,
  cost, account identity, or note is sent to an external research request.

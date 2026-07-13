# Commuter Morning Brief V2 Design

Date: 2026-07-13
Branch: `codex/commuter-morning-brief-v2`
Status: approved by the user's standing instruction to proceed autonomously

## Goal

Make the scheduled morning email readable in about 30 seconds on a phone during a subway commute, without weakening stale-data gates or hiding where full evidence can be reviewed.

## Observed Problem

The current production brief is already labeled as a subway edition, but it still contains 1,929 characters and 41 lines. The `投资建议 15只票` section alone contains 1,174 characters, about 61% of the email. The first screen therefore competes with a long candidate list instead of answering what the user should do first.

## Considered Directions

1. **Recommended: 30-second action brief.** Keep only the market gate, the highest-priority holding actions, three watch candidates, and three disciplines. Route full evidence to the authenticated web workspaces.
2. **Compress all 15 candidates further.** Preserves breadth but still forces scanning and encourages treating a ranking as a trade list.
3. **Use collapsible sections.** Rejected because email-client support for interactive disclosure is inconsistent.

## Content Contract

The email uses five short sections in this order:

1. `30秒结论`
   - whether today's data permits conditional execution;
   - one market sentence;
   - the first holding priority;
   - the first opportunity or a no-trade fallback.
2. `先处理持仓`
   - at most four holdings;
   - one action-first line per holding;
   - keep judgment, action, and invalidation; remove repeated methodology.
3. `今日只看3只`
   - at most three candidates;
   - each line keeps name, theme, reason, risk, and trigger in compressed form;
   - label them as observation candidates, never as buy recommendations.
4. `三条纪律`
   - stale-data or degraded-source guard first;
   - no chasing, no averaging down solely because of losses, no action without a trigger;
   - announcement or automation exception only when actionable.
5. `到公司再看`
   - links to market, portfolio, stock, opportunity, and data workspaces;
   - research-only disclaimer and trade date.

## Density Rules

- Target total body length: at most 900 Chinese characters for a normal populated report.
- Target total lines: at most 28 non-empty lines.
- Candidate detail: at most three lines.
- Holding detail: at most four lines.
- Action line: at most 96 characters; 30-second summary line: at most 72 characters.
- Do not print raw command errors, provider codes, method-chain counts, file paths, or all 15 candidates.

## Safety And Data Boundaries

- `pipeline.status`, trade date, and structured decision artifacts remain authoritative.
- Stale or failed data must appear in `30秒结论` before any candidate.
- A candidate is an observation target, not a buy instruction.
- Full evidence is not deleted from reports or the web app; it is removed only from the email body.
- The existing per-user holdings path and delivery schedule remain unchanged.

## Visual Direction

The signature is a red/amber/green action strip expressed through section order and concise labels, not decorative dashboard cards. Markdown remains the transport contract so existing email rendering continues to work. On phone widths the email stays a single reading column with no tables.

## Acceptance Criteria

- Production-like fixture renders no `投资建议 15只票` heading.
- `30秒结论` appears first and surfaces stale execution guards before holdings or candidates.
- No more than three candidate action lines and four holding lines appear.
- Full-workspace links use the supplied `site_url`.
- Existing personalized holdings and dry-run dispatch contracts remain valid.
- Focused morning-report tests, lint, Python compilation, and server dry-run pass.

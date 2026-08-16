# Decision Change Center Design

Date: 2026-08-16
Status: Approved under delegated product authority

## 1. Decision

Add a persistent, account-scoped decision change center. The server continues to refresh market data every ten minutes, compares each monitored decision with its previous value, and records only material changes. The product tells the user what changed and what to do; it does not ask the user to inspect indicators or operate the monitoring workflow.

This release does not place trades. A user must still confirm any buy, add, trim, or exit action.

## 2. Product Boundary

The first release monitors two decision sources:

- every holding owned by an account;
- the visible top candidate for every monitored opportunity strategy.

It does not create events for score-only changes, minor candidate reordering, unchanged actions, provider failures, stale data, or the initial baseline. Candidate events are account-scoped copies so unread state and future delivery preferences remain simple and private.

The direct decision vocabulary remains:

- candidates: `可小仓试探`, `仅观察`, `暂不买入`, `暂不参与`;
- holdings: `继续持有`, `仅小幅加仓`, `建议分批减仓`, `优先减仓或止损`, `暂不操作`.

## 3. Persistent Contracts

Add a deterministic server-side decision presentation contract with action, summary, severity, whether the user must act, and a stable reason code. The frontend renders this contract instead of independently translating raw analysis labels.

Add two account-scoped tables:

- `decision_snapshots` stores the latest decision for one `source + strategy/symbol` key, including the normalized action, severity, reason code, explanation, deep link, and observation time;
- `decision_events` stores immutable before/after changes, an unread/read timestamp, email delivery state, retry metadata, and a stable deduplication key.

Foreign keys cascade from users. A unique event key prevents duplicate rows when the refresh loop retries the same observation.

## 4. Refresh And Comparison Flow

After a successful market refresh and opportunity precomputation:

1. List real registered users, excluding the disabled migration owner.
2. Analyse each user's holdings from the refreshed snapshot.
3. Read the warmed top result for every monitored strategy.
4. Convert holdings and candidates into normalized decision snapshots.
5. Compare each snapshot with the persisted previous snapshot.
6. On first observation, save the baseline without creating an event.
7. When the normalized action changes, save one immutable event and replace the latest snapshot in the same database transaction.
8. Preserve the previous snapshot when analysis is unavailable, stale, incomplete, or failed.

Removed holdings have their latest holding snapshot deleted so adding the stock again establishes a fresh baseline. Candidate ranking alone does not create an event; the monitored top candidate must change and the new candidate must have a different participation decision, or the same candidate's action must change.

## 5. Severity And Delivery

Severity is deterministic:

- `critical`: a holding changes to `优先减仓或止损`;
- `high`: a holding changes to `建议分批减仓`;
- `action`: a candidate changes to `可小仓试探` or a holding changes to `仅小幅加仓`;
- `info`: all other material action changes.

All material changes appear in the in-app center. Only `critical` and `high` events are eligible for email. A separate application email-dispatch loop reads pending events after they are committed; SMTP work runs outside the event loop. Delivery is idempotent: an SMTP error never rolls back the event or blocks market refresh, and a successfully delivered event is never sent again.

The existing SMTP configuration and real-recipient filtering are reused. If SMTP is not configured, the event remains available in the application and records a bounded delivery error for later retry.

## 6. API And Frontend

Add authenticated browser APIs under `/api/v1/*`:

- `GET /api/v1/decision-events` returns unread count, actionable changes, monitoring-only changes, and the latest monitoring time;
- `POST /api/v1/decision-events/{id}/read` marks one owned event read;
- `POST /api/v1/decision-events/read-all` clears the owned unread count.

Add a lazy-loaded `/decisions` route and a `决定` navigation entry with an unread badge. The page leads with `今天需要你处理什么` and separates:

- `需要你处理`: events whose normalized contract requires user action;
- `系统继续监控`: material changes that do not require a trade decision.

Each card shows the current action, previous action, plain-language reason, observed time, and a deep link. Opening a deep link marks that event read. The empty state says `当前无需操作，系统继续监控` and contains no checklist for the user.

The shell polls only the lightweight event summary, refetches on window focus, and never triggers provider calls directly.

## 7. Failure And Noise Controls

- No event is created from missing or stale analysis.
- Provider failure keeps the previous decision and records operational health separately.
- Snapshot and event writes occur in one transaction.
- One failed user's holding analysis does not stop other users or global candidate monitoring.
- Email failures use bounded retries and retain the in-app event.
- Events are immutable except for read and delivery metadata.
- The API enforces account ownership for every read mutation.

## 8. Verification

Backend tests must prove baseline suppression, action-change detection, deduplication, account isolation, stale/failure suppression, severity classification, and email idempotency. Frontend tests must prove direct wording, unread badge behavior, grouping, empty state, read mutations, and 390px layout safety.

Before deployment:

- run `make verify`;
- complete authenticated desktop and 390px browser acceptance;
- confirm the ten-minute production refresh remains active;
- confirm a synthetic baseline creates no event and one synthetic action transition creates exactly one event;
- deploy to the existing public URL and verify health plus the authenticated decision center.

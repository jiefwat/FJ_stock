# Decision Change Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an account-scoped decision change center that records only material holding and candidate action changes, surfaces them in the application, and emails only high-risk holding changes.

**Architecture:** Add one deterministic decision contract under `analysis/`, persist latest snapshots plus immutable events in SQLite, and run comparison after the existing ten-minute market/opportunity refresh. Expose an authenticated feed under `/api/v1/*`, render it through a lazy frontend route and unread badge, and dispatch eligible email from a separate retrying application loop.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, SQLite, pytest, React 19, TypeScript, TanStack Query, Vitest, Testing Library, CSS.

---

## File Map

- Create `backend/src/marketdesk/analysis/decisions.py`: pure candidate/holding decision normalization and severity rules.
- Modify `backend/src/marketdesk/models.py`: decision presentation, snapshot, event, and feed contracts.
- Modify `backend/src/marketdesk/analysis/opportunities.py`: attach the normalized decision to every ranked candidate.
- Modify `backend/src/marketdesk/analysis/holding.py`: attach the normalized decision to every holding dossier.
- Create `backend/tests/test_decisions.py`: deterministic decision vocabulary and severity coverage.
- Modify `backend/src/marketdesk/store.py`: decision tables, transactional comparison, read state, and delivery state.
- Create `backend/tests/test_decision_store.py`: baseline, transition, deduplication, isolation, and deletion coverage.
- Modify `backend/src/marketdesk/services.py`: account monitoring orchestration after warmed opportunity results.
- Modify `backend/src/marketdesk/api.py`: refresh integration, email loop, and authenticated decision APIs.
- Create `backend/src/marketdesk/decision_email.py`: pending high-risk event delivery with bounded retries.
- Modify `backend/tests/test_api.py`: scheduled-monitor and authenticated API behavior.
- Create `backend/tests/test_decision_email.py`: eligibility, idempotency, and failure retry tests.
- Modify `frontend/src/lib/api.ts`: typed decision contracts and API helpers.
- Create `frontend/src/features/decisions/DecisionCenterPage.tsx`: decision-first feed UI.
- Create `frontend/src/features/decisions/DecisionCenterPage.test.tsx`: grouping, empty state, and read interactions.
- Modify `frontend/src/app/App.tsx`: lazy route, navigation entry, and unread badge.
- Modify `frontend/src/app/App.test.tsx`: authenticated route and badge tests.
- Modify `frontend/src/app/styles.css`: desktop and 390px decision-center layout.
- Modify `docs/superpowers/market-intelligence-workbench/TODO.md`: release acceptance record.

Implementation commits are intentionally omitted from the task steps because the shared worktree already contains user-owned edits in the same files. Keep changes scoped, inspect the diff after every task, and do not stage unrelated modifications.

### Task 1: Server-owned Decision Vocabulary

**Files:**
- Create: `backend/src/marketdesk/analysis/decisions.py`
- Modify: `backend/src/marketdesk/models.py`
- Modify: `backend/src/marketdesk/analysis/opportunities.py`
- Modify: `backend/src/marketdesk/analysis/holding.py`
- Test: `backend/tests/test_decisions.py`
- Test: `backend/tests/test_analysis.py`

- [ ] **Step 1: Write failing normalization tests**

Create tests that construct ranked candidates and holding dossiers at each boundary:

```python
def test_candidate_decision_uses_direct_participation_vocabulary() -> None:
    assert candidate_decision(candidate(score=82, coverage=0.82)).action == "可小仓试探"
    assert candidate_decision(candidate(score=66, context_penalty=8)).action == "暂不买入"
    assert candidate_decision(candidate(coverage=0.5)).action == "暂不参与"


def test_holding_decision_marks_only_trade_changes_as_actionable() -> None:
    assert holding_decision("hold").model_dump() == {
        "action": "继续持有",
        "summary": "当前没有触发调仓条件，系统继续监控。",
        "severity": "info",
        "user_required": False,
        "reason_code": "holding_hold",
        "layer": None,
    }
    assert holding_decision("exit_watch").severity == "critical"
    assert holding_decision("exit_watch").user_required is True
```

- [ ] **Step 2: Run the focused tests and confirm the missing-contract failure**

Run: `cd backend && uv run pytest -q tests/test_decisions.py`

Expected: collection fails because `marketdesk.analysis.decisions` and `DecisionPresentation` do not exist.

- [ ] **Step 3: Add the strict presentation contract and pure functions**

Add this contract to `models.py`:

```python
DecisionSeverity = Literal["critical", "high", "action", "info"]


class DecisionPresentation(StrictModel):
    action: str = Field(min_length=1, max_length=40)
    summary: str = Field(min_length=1, max_length=300)
    severity: DecisionSeverity
    user_required: bool
    reason_code: str = Field(min_length=1, max_length=80)
    layer: Literal["priority", "review", "watch_only", "high_risk"] | None = None
```

Implement `candidate_decision(candidate: RankedCandidate)` and `holding_decision(action: str)` in `analysis/decisions.py` using the current frontend thresholds. Candidate reasons must distinguish history risk, insufficient coverage, risk-off penalty, qualified trial, weak score, and watch-only. Holding action mappings must use the five approved labels and assign `critical` only to `exit_watch`, `high` only to `trim`, and `action` only to `add_watch`.

- [ ] **Step 4: Attach decisions to analysis responses**

Add `decision: DecisionPresentation` to `RankedCandidate` and `HoldingDossier`. In `rank_candidates`, attach the decision after history checks and final score are known. In `analyse_holding`, attach the presentation derived from the existing action code. Do not let presentation fields feed back into scores.

- [ ] **Step 5: Run deterministic analysis tests**

Run: `cd backend && uv run pytest -q tests/test_decisions.py tests/test_analysis.py`

Expected: all decision and existing analysis tests pass.

### Task 2: Persistent Snapshot And Event Ledger

**Files:**
- Modify: `backend/src/marketdesk/models.py`
- Modify: `backend/src/marketdesk/store.py`
- Create: `backend/tests/test_decision_store.py`

- [ ] **Step 1: Write failing store tests**

Cover baseline suppression, one transition, replay deduplication, account isolation, read state, and removed holding cleanup:

```python
def test_first_snapshot_is_baseline_and_action_change_creates_one_event(tmp_path) -> None:
    store = Store(tmp_path / "decision.db")
    user = create_user(store, "one@example.test")
    assert store.record_decision_snapshot(user.id, snapshot("仅观察")) is None
    event = store.record_decision_snapshot(user.id, snapshot("可小仓试探"))
    assert event is not None
    assert event.previous_action == "仅观察"
    assert event.action == "可小仓试探"
    assert store.record_decision_snapshot(user.id, snapshot("可小仓试探")) is None
    assert len(store.list_decision_events(user.id)) == 1


def test_decision_events_are_account_scoped(tmp_path) -> None:
    store = Store(tmp_path / "isolated.db")
    first, second = two_users(store)
    create_transition(store, first.id)
    assert len(store.list_decision_events(first.id)) == 1
    assert store.list_decision_events(second.id) == []
```

- [ ] **Step 2: Run the focused tests and confirm missing methods**

Run: `cd backend && uv run pytest -q tests/test_decision_store.py`

Expected: failures for missing snapshot/event models and store methods.

- [ ] **Step 3: Add event models**

Add strict models with these fields:

```python
class DecisionSnapshot(StrictModel):
    source: Literal["holding", "opportunity"]
    subject_key: str
    symbol: str
    name: str
    strategy: str | None = None
    decision: DecisionPresentation
    href: str
    observed_at: datetime


class DecisionEvent(StrictModel):
    id: int
    source: Literal["holding", "opportunity"]
    subject_key: str
    symbol: str
    name: str
    strategy: str | None
    previous_action: str
    action: str
    summary: str
    severity: DecisionSeverity
    user_required: bool
    reason_code: str
    href: str
    observed_at: datetime
    created_at: datetime
    read_at: datetime | None
    email_status: Literal["not_required", "pending", "sent", "failed"]
    email_attempts: int
    email_error: str | None
    email_sent_at: datetime | None
```

- [ ] **Step 4: Add tables and transactional comparison**

Create `decision_snapshots` with `UNIQUE(user_id, source, subject_key)` and `decision_events` with a unique `dedup_key`. `record_decision_snapshot` must open one connection and transaction, insert the initial baseline without an event, update unchanged metadata without an event, and insert the event before replacing a changed snapshot. Compute `dedup_key` from user, source, subject key, previous action, new action, and observation time with SHA-256.

Add methods:

```python
record_decision_snapshot(user_id, snapshot) -> DecisionEvent | None
delete_missing_holding_decision_snapshots(user_id, active_subject_keys) -> None
list_decision_events(user_id, limit=100) -> list[DecisionEvent]
mark_decision_event_read(event_id, user_id) -> DecisionEvent
mark_all_decision_events_read(user_id) -> int
list_pending_decision_emails(limit=50, max_attempts=3) -> list[tuple[UserAccount, DecisionEvent]]
mark_decision_email_result(event_id, *, sent, error=None) -> None
```

- [ ] **Step 5: Run store tests and inspect schema migration safety**

Run: `cd backend && uv run pytest -q tests/test_decision_store.py`

Expected: all tests pass both on a new database and on a database initialized before the new tables exist.

### Task 3: Ten-minute Decision Monitor

**Files:**
- Modify: `backend/src/marketdesk/services.py`
- Modify: `backend/src/marketdesk/api.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing monitor tests**

Use a stateful fixture provider and two users:

```python
@pytest.mark.asyncio
async def test_scheduled_monitor_establishes_baseline_then_records_one_change(tmp_path) -> None:
    provider = MutableDecisionProvider()
    service = MarketService(provider=provider, store=Store(tmp_path / "monitor.db"))
    user = registered_user(service.store)
    service.store.create_holding(
        symbol="SH.600519",
        name="贵州茅台",
        quantity=100,
        cost_price=1_300,
        target_weight=0.2,
        thesis="现金流稳定",
        invalidation="跌破成本且趋势转弱",
        user_id=user.id,
    )
    await service.refresh_decision_monitor()
    assert service.store.list_decision_events(user.id) == []
    provider.price = provider.exit_price
    await service.refresh(force=True)
    await service.refresh_decision_monitor()
    events = service.store.list_decision_events(user.id)
    assert [event.action for event in events] == ["优先减仓或止损"]
```

Add a failure test proving that a provider exception leaves the previous snapshot intact and creates no event.

- [ ] **Step 2: Run the monitor tests and confirm the missing orchestration failure**

Run: `cd backend && uv run pytest -q tests/test_api.py -k 'decision_monitor'`

Expected: fail because `refresh_decision_monitor` does not exist.

- [ ] **Step 3: Implement snapshot builders and monitoring**

Add focused helpers in `MarketService`:

```python
def _holding_decision_snapshot(dossier: HoldingDossier, observed_at: datetime) -> DecisionSnapshot
def _opportunity_decision_snapshot(preset: str, candidate: RankedCandidate, observed_at: datetime) -> DecisionSnapshot
async def refresh_decision_monitor(self) -> dict[str, int]
```

The monitor must exclude `owner@marketdesk.local`, isolate each user's exceptions, reuse already warmed opportunity results, analyse holdings from the current snapshot, establish baselines, delete missing holding snapshots, and return counts for users, baselines, and events. It must skip any decision whose underlying dossier is insufficient or whose market snapshot freshness is stale.

- [ ] **Step 4: Integrate after scheduled opportunity refresh**

Call `refresh_decision_monitor()` once at the end of `_safe_auto_refresh`, after all monitored opportunity presets have run. A monitor failure must be logged without terminating the ten-minute loop.

- [ ] **Step 5: Run monitor and scheduler tests**

Run: `cd backend && uv run pytest -q tests/test_api.py -k 'auto_refresh or opportunity_monitor or decision_monitor'`

Expected: existing refresh tests and new decision tests pass.

### Task 4: High-risk Email Dispatcher

**Files:**
- Create: `backend/src/marketdesk/decision_email.py`
- Modify: `backend/src/marketdesk/api.py`
- Modify: `backend/tests/test_decision_email.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing dispatcher tests**

Cover non-high-risk suppression, a successful send, no duplicate send, and three bounded failures:

```python
@pytest.mark.asyncio
async def test_dispatch_sends_each_pending_high_risk_event_once(tmp_path, monkeypatch) -> None:
    service, event = pending_event(tmp_path, severity="critical")
    sent = []
    monkeypatch.setattr("marketdesk.decision_email._send", lambda message, settings: sent.append(message))
    first = await dispatch_decision_emails(service, settings())
    second = await dispatch_decision_emails(service, settings())
    assert first.sent == 1
    assert second.sent == 0
    assert len(sent) == 1
```

- [ ] **Step 2: Run the focused tests and confirm the missing dispatcher failure**

Run: `cd backend && uv run pytest -q tests/test_decision_email.py`

Expected: collection fails because `decision_email.py` does not exist.

- [ ] **Step 3: Implement bounded delivery**

Create a small dispatcher that reads `list_pending_decision_emails`, rejects local/example/smoke recipients, renders one plain-text and HTML message with current action, previous action, reason, time, and public deep link, and runs SMTP work with `asyncio.to_thread`. Mark success once; on failure increment attempts and retain a bounded error class name without credentials or provider payloads.

Expose a summary contract:

```python
@dataclass(frozen=True)
class DecisionEmailSummary:
    sent: int
    failed: int
    skipped: int
```

- [ ] **Step 4: Add a separate delivery loop to application lifespan**

Start one `_decision_email_loop` at a 60-second interval when automatic refresh is enabled. It must dispatch already committed events, survive individual send failures, and be cancelled during shutdown independently of the market refresh task.

- [ ] **Step 5: Run email and lifespan tests**

Run: `cd backend && uv run pytest -q tests/test_decision_email.py tests/test_api.py -k 'decision_email or lifespan or auto_refresh'`

Expected: all focused tests pass and no SMTP call occurs inside the market refresh transaction.

### Task 5: Authenticated Decision Feed API

**Files:**
- Modify: `backend/src/marketdesk/models.py`
- Modify: `backend/src/marketdesk/services.py`
- Modify: `backend/src/marketdesk/api.py`
- Modify: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Test authentication, grouping, ownership, single read, and read-all:

```python
def test_decision_feed_groups_actionable_and_monitoring_events(tmp_path) -> None:
    service, first_api, second_api = decision_clients(tmp_path)
    create_events_for_both_users(service.store)
    response = first_api.get("/api/v1/decision-events")
    assert response.status_code == 200
    assert response.json()["unread_count"] == 2
    assert response.json()["requires_action"][0]["action"] == "建议分批减仓"
    assert response.json()["monitoring"][0]["action"] == "暂不买入"
    assert second_api.post(
        f"/api/v1/decision-events/{response.json()['requires_action'][0]['id']}/read"
    ).status_code == 404
```

- [ ] **Step 2: Run focused API tests and confirm 404 failures**

Run: `cd backend && uv run pytest -q tests/test_api.py -k 'decision_feed or decision_event'`

Expected: decision endpoints return 404 because routes do not exist.

- [ ] **Step 3: Add feed contract and service grouping**

Add:

```python
class DecisionEventFeed(StrictModel):
    unread_count: int
    requires_action: list[DecisionEvent]
    monitoring: list[DecisionEvent]
    monitored_at: datetime | None
```

Group by `event.user_required`, order unread before read and newest before older, cap each list at 50, and derive `monitored_at` from decision snapshot status rather than triggering a refresh.

- [ ] **Step 4: Add authenticated routes**

Implement only `/api/v1/*` routes. Read mutations must use the current authenticated user's ID and translate a missing owned event to 404.

- [ ] **Step 5: Run all backend checks**

Run: `cd backend && uv run ruff check . && uv run mypy src && uv run pytest -q`

Expected: lint and types pass; the complete backend suite passes.

### Task 6: Decision Center Frontend

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/features/decisions/DecisionCenterPage.tsx`
- Create: `frontend/src/features/decisions/DecisionCenterPage.test.tsx`
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/app/App.test.tsx`
- Modify: `frontend/src/app/styles.css`

- [ ] **Step 1: Write failing page tests**

Render a feed with one critical event and one informational event:

```tsx
expect(await screen.findByRole("heading", { name: "今天需要你处理什么" })).toBeInTheDocument();
expect(screen.getByText("优先减仓或止损")).toBeInTheDocument();
expect(screen.getByText("之前：继续持有")).toBeInTheDocument();
expect(screen.getByText("系统继续监控")).toBeInTheDocument();
fireEvent.click(screen.getByRole("link", { name: /查看恺英网络决定/ }));
await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
  "/api/v1/decision-events/12/read",
  expect.objectContaining({ method: "POST" }),
));
```

Add an empty feed assertion for `当前无需操作，系统继续监控` and no user checklist.

- [ ] **Step 2: Run the focused tests and confirm the missing component failure**

Run: `cd frontend && pnpm test --run src/features/decisions/DecisionCenterPage.test.tsx`

Expected: fail because the component does not exist.

- [ ] **Step 3: Add typed feed client and page**

Define `DecisionEvent` and `DecisionEventFeed` in `api.ts`. Build the page with one query key `['decision-events']`, direct action cards, previous action, plain-language summary, observed time, and deep link. Read mutations update the cached event and unread count immediately, then invalidate in the background. Do not expose email retry internals in the UI.

- [ ] **Step 4: Add lazy route and unread badge**

Add `决定` as the first navigation item, lazy-load `/decisions`, and query the lightweight feed in the authenticated shell with a 60-second stale time and `refetchOnWindowFocus: true`. Render a bounded badge (`99+`) only when unread count is positive. Preserve `/market` as the default route in this phase.

- [ ] **Step 5: Add responsive styles**

Use the existing warm-paper/deep-green visual system. Make actionable events visually dominant without red-filling the entire card; use a narrow severity rail, large direct action, and compact before/after copy. At `max-width: 640px`, use one column, keep links at least 44px tall, and guarantee no document overflow at 390px.

- [ ] **Step 6: Run frontend checks**

Run: `cd frontend && pnpm test --run && pnpm typecheck && pnpm build`

Expected: all frontend tests, types, and production build pass.

### Task 7: Browser Acceptance, Documentation, And Deployment

**Files:**
- Modify: `docs/superpowers/market-intelligence-workbench/TODO.md`
- Modify only implementation files required by acceptance findings.

- [ ] **Step 1: Run the repository gate**

Run: `make verify`

Expected: backend lint/types/tests, frontend types/tests/build, and live-data quality all pass.

- [ ] **Step 2: Perform deterministic local acceptance**

Use a temporary account and fixture/state transition to prove:

1. first refresh creates zero events;
2. one holding action transition creates exactly one event;
3. repeating the refresh keeps exactly one event;
4. another account cannot read or mutate it;
5. `/decisions` shows the direct action and unread badge;
6. marking it read clears the badge;
7. desktop and 390px widths have `scrollWidth - clientWidth === 0`.

- [ ] **Step 3: Record the completed release slice**

Add checked TODO entries for persistent monitoring, low-noise event rules, high-risk email delivery, authenticated decision feed, and responsive browser acceptance.

- [ ] **Step 4: Re-run final checks**

Run: `git diff --check && make verify`

Expected: no whitespace errors and all gates pass after documentation updates.

- [ ] **Step 5: Deploy and verify production**

Run:

```bash
DEPLOY_HOST=stock.jiewat-kaka-fj.com \
DEPLOY_USER=admin \
SSH_KEY=/Users/fangjie/.ssh/stockts_aliyun_deploy \
./deploy/deploy_public.sh
```

Verify `/healthz`, authenticated `/api/v1/decision-events`, the `/decisions` page, the 600-second refresh environment, and one baseline-safe monitor run. Remove only the exact temporary account and local data created for acceptance.

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from marketdesk.auth import hash_token
from marketdesk.models import (
    DecisionEvent,
    DecisionSnapshot,
    EquityViewFilters,
    HoldingItem,
    RecommendationObservation,
    RecommendationSnapshot,
    SavedEquityView,
    UserAccount,
    UserPreferences,
    WatchlistItem,
)


@dataclass(frozen=True)
class SnapshotRecord:
    dataset: str
    observed_at: datetime
    payload: dict[str, object]


@dataclass(frozen=True)
class UserRecord:
    account: UserAccount
    password_hash: str


@dataclass(frozen=True)
class RecommendationRunRecord:
    id: int
    snapshot: RecommendationSnapshot


class Store:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _public_row(self, row: sqlite3.Row) -> dict[str, object]:
        values = dict(row)
        values.pop("user_id", None)
        return values

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS snapshots (id INTEGER PRIMARY KEY, dataset TEXT NOT NULL, observed_at TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
                CREATE TABLE IF NOT EXISTS user_preferences (user_id INTEGER PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
                CREATE TABLE IF NOT EXISTS saved_equity_views (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, name TEXT NOT NULL, filters TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(user_id, name), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
                CREATE TABLE IF NOT EXISTS recommendation_runs (id INTEGER PRIMARY KEY, preset TEXT NOT NULL, algorithm_version TEXT NOT NULL, trading_date TEXT NOT NULL, observed_at TEXT NOT NULL, payload TEXT NOT NULL, UNIQUE(preset, trading_date, algorithm_version));
                CREATE TABLE IF NOT EXISTS recommendation_observations (id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL, trading_date TEXT NOT NULL, observed_at TEXT NOT NULL, payload TEXT NOT NULL, UNIQUE(run_id, trading_date), FOREIGN KEY(run_id) REFERENCES recommendation_runs(id) ON DELETE CASCADE);
                CREATE TABLE IF NOT EXISTS decision_snapshots (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    subject_key TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    name TEXT NOT NULL,
                    strategy TEXT,
                    action TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    user_required INTEGER NOT NULL,
                    reason_code TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    confidence REAL,
                    href TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id,source,subject_key),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS decision_events (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    subject_key TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    name TEXT NOT NULL,
                    strategy TEXT,
                    previous_action TEXT NOT NULL,
                    action TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    user_required INTEGER NOT NULL,
                    reason_code TEXT NOT NULL,
                    confidence REAL,
                    href TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    read_at TEXT,
                    email_status TEXT NOT NULL,
                    email_attempts INTEGER NOT NULL DEFAULT 0,
                    email_error TEXT,
                    email_sent_at TEXT,
                    dedup_key TEXT NOT NULL UNIQUE,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)
            self._ensure_recommendation_versioning(connection)
            self._ensure_decision_confidence(connection)
            owner_id = self._ensure_default_user(connection)
            self._ensure_personal_table(
                connection,
                "watchlist",
                owner_id,
                """
                CREATE TABLE watchlist (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    name TEXT NOT NULL,
                    thesis TEXT NOT NULL,
                    invalidation TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, symbol),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """,
                "symbol,name,thesis,invalidation,status,created_at,updated_at",
            )
            self._ensure_personal_table(
                connection,
                "holdings",
                owner_id,
                """
                CREATE TABLE holdings (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    name TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    cost_price REAL NOT NULL,
                    target_weight REAL NOT NULL,
                    thesis TEXT NOT NULL,
                    invalidation TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, symbol),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """,
                "symbol,name,quantity,cost_price,target_weight,thesis,invalidation,status,created_at,updated_at",
            )

    def _ensure_recommendation_versioning(self, connection: sqlite3.Connection) -> None:
        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(recommendation_runs)").fetchall()
        }
        if "algorithm_version" in columns:
            return

        connection.executescript("""
            CREATE TABLE recommendation_runs_new (
                id INTEGER PRIMARY KEY,
                preset TEXT NOT NULL,
                algorithm_version TEXT NOT NULL,
                trading_date TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                payload TEXT NOT NULL,
                UNIQUE(preset, trading_date, algorithm_version)
            );
            INSERT INTO recommendation_runs_new(
                id,preset,algorithm_version,trading_date,observed_at,payload
            )
            SELECT id,preset,'v1',trading_date,observed_at,payload
            FROM recommendation_runs;
            CREATE TABLE recommendation_observations_new (
                id INTEGER PRIMARY KEY,
                run_id INTEGER NOT NULL,
                trading_date TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                payload TEXT NOT NULL,
                UNIQUE(run_id, trading_date),
                FOREIGN KEY(run_id) REFERENCES recommendation_runs_new(id)
                    ON DELETE CASCADE
            );
            INSERT INTO recommendation_observations_new(
                id,run_id,trading_date,observed_at,payload
            )
            SELECT id,run_id,trading_date,observed_at,payload
            FROM recommendation_observations;
            DROP TABLE recommendation_observations;
            DROP TABLE recommendation_runs;
            ALTER TABLE recommendation_runs_new RENAME TO recommendation_runs;
            ALTER TABLE recommendation_observations_new
                RENAME TO recommendation_observations;
        """)

    @staticmethod
    def _ensure_decision_confidence(connection: sqlite3.Connection) -> None:
        for table in ("decision_snapshots", "decision_events"):
            columns = {
                str(row["name"])
                for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
            }
            if "confidence" not in columns:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN confidence REAL")

    def _ensure_default_user(self, connection: sqlite3.Connection) -> int:
        now = datetime.now(UTC).isoformat()
        connection.execute(
            """
            INSERT OR IGNORE INTO users(email,display_name,password_hash,created_at,updated_at)
            VALUES(?,?,?,?,?)
            """,
            ("owner@marketdesk.local", "默认用户", "disabled", now, now),
        )
        row = connection.execute(
            "SELECT id FROM users WHERE email=?", ("owner@marketdesk.local",)
        ).fetchone()
        if row is None:
            raise RuntimeError("default user was not initialized")
        return int(row["id"])

    def _ensure_personal_table(
        self,
        connection: sqlite3.Connection,
        table: str,
        owner_id: int,
        create_sql: str,
        data_columns: str,
    ) -> None:
        existing = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if existing is None:
            connection.execute(create_sql)
            return
        columns = {
            str(row["name"]) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if "user_id" in columns:
            return
        legacy = f"{table}_legacy"
        connection.execute(f"ALTER TABLE {table} RENAME TO {legacy}")
        connection.execute(create_sql)
        connection.execute(
            f"""
            INSERT INTO {table}(user_id,{data_columns})
            SELECT ?,{data_columns} FROM {legacy}
            """,
            (owner_id,),
        )
        connection.execute(f"DROP TABLE {legacy}")

    @property
    def default_user_id(self) -> int:
        with self._connect() as connection:
            return self._ensure_default_user(connection)

    def save_snapshot(
        self, dataset: str, observed_at: datetime, payload: dict[str, object]
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO snapshots(dataset, observed_at, payload) VALUES (?, ?, ?)",
                (dataset, observed_at.isoformat(), json.dumps(payload, ensure_ascii=False)),
            )

    def latest_snapshot(self, dataset: str) -> SnapshotRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM snapshots WHERE dataset=? ORDER BY observed_at DESC, id DESC LIMIT 1",
                (dataset,),
            ).fetchone()
        return (
            None
            if row is None
            else SnapshotRecord(
                dataset=row["dataset"],
                observed_at=datetime.fromisoformat(row["observed_at"]),
                payload=json.loads(row["payload"]),
            )
        )

    def recommendation_run_exists(
        self, preset: str, trading_date: date, algorithm_version: str = "v1"
    ) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM recommendation_runs
                WHERE preset=? AND trading_date=? AND algorithm_version=? LIMIT 1
                """,
                (preset, trading_date.isoformat(), algorithm_version),
            ).fetchone()
        return row is not None

    def save_recommendation_run(self, snapshot: RecommendationSnapshot) -> RecommendationRunRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO recommendation_runs(
                    preset,algorithm_version,trading_date,observed_at,payload
                )
                VALUES(?,?,?,?,?)
                """,
                (
                    snapshot.preset,
                    snapshot.algorithm_version,
                    snapshot.trading_date.isoformat(),
                    snapshot.observed_at.isoformat(),
                    snapshot.model_dump_json(),
                ),
            )
            row = connection.execute(
                """
                SELECT id,payload FROM recommendation_runs
                WHERE preset=? AND trading_date=? AND algorithm_version=?
                """,
                (
                    snapshot.preset,
                    snapshot.trading_date.isoformat(),
                    snapshot.algorithm_version,
                ),
            ).fetchone()
        if row is None:
            raise RuntimeError("recommendation run insert did not return a row")
        return RecommendationRunRecord(
            id=int(row["id"]),
            snapshot=RecommendationSnapshot.model_validate_json(row["payload"]),
        )

    def list_recommendation_runs(
        self,
        preset: str,
        limit: int = 90,
        algorithm_version: str | None = "v1",
    ) -> list[RecommendationRunRecord]:
        with self._connect() as connection:
            if algorithm_version is None:
                rows = connection.execute(
                    """
                    SELECT id,payload FROM recommendation_runs
                    WHERE preset=? ORDER BY trading_date DESC, id DESC LIMIT ?
                    """,
                    (preset, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT id,payload FROM recommendation_runs
                    WHERE preset=? AND algorithm_version=?
                    ORDER BY trading_date DESC, id DESC LIMIT ?
                    """,
                    (preset, algorithm_version, limit),
                ).fetchall()
        return [
            RecommendationRunRecord(
                id=int(row["id"]),
                snapshot=RecommendationSnapshot.model_validate_json(row["payload"]),
            )
            for row in rows
        ]

    def save_recommendation_observation(
        self, run_id: int, observation: RecommendationObservation
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO recommendation_observations(run_id,trading_date,observed_at,payload)
                VALUES(?,?,?,?)
                ON CONFLICT(run_id,trading_date) DO UPDATE SET
                    observed_at=excluded.observed_at,
                    payload=excluded.payload
                """,
                (
                    run_id,
                    observation.trading_date.isoformat(),
                    observation.observed_at.isoformat(),
                    observation.model_dump_json(),
                ),
            )

    def list_recommendation_observations(
        self, run_ids: list[int]
    ) -> dict[int, list[RecommendationObservation]]:
        if not run_ids:
            return {}
        placeholders = ",".join("?" for _ in run_ids)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT run_id,payload FROM recommendation_observations
                WHERE run_id IN ({placeholders})
                ORDER BY trading_date ASC, id ASC
                """,
                run_ids,
            ).fetchall()
        observations: dict[int, list[RecommendationObservation]] = {
            run_id: [] for run_id in run_ids
        }
        for row in rows:
            observations[int(row["run_id"])].append(
                RecommendationObservation.model_validate_json(row["payload"])
            )
        return observations

    def create_user(self, email: str, display_name: str, password_hash: str) -> UserAccount:
        normalized_email = email.strip().lower()
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO users(email,display_name,password_hash,created_at,updated_at)
                VALUES(?,?,?,?,?)
                """,
                (
                    normalized_email,
                    display_name.strip() or normalized_email,
                    password_hash,
                    now,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT id,email,display_name,created_at,updated_at FROM users WHERE email=?",
                (normalized_email,),
            ).fetchone()
        if row is None:
            raise RuntimeError("user insert did not return an account")
        return UserAccount(**dict(row))

    def get_user(self, user_id: int) -> UserAccount:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id,email,display_name,created_at,updated_at FROM users WHERE id=?",
                (user_id,),
            ).fetchone()
        if row is None:
            raise KeyError(user_id)
        return UserAccount(**dict(row))

    def get_user_by_email(self, email: str) -> UserRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE email=?", (email.strip().lower(),)
            ).fetchone()
        if row is None:
            return None
        return UserRecord(
            account=UserAccount(
                id=row["id"],
                email=row["email"],
                display_name=row["display_name"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            ),
            password_hash=str(row["password_hash"]),
        )

    def list_users(self) -> list[UserAccount]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id,email,display_name,created_at,updated_at FROM users ORDER BY id"
            ).fetchall()
        return [UserAccount(**dict(row)) for row in rows]

    def create_session(self, user_id: int, token: str) -> None:
        now = datetime.now(UTC)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions(token_hash,user_id,created_at,expires_at)
                VALUES(?,?,?,?)
                """,
                (
                    hash_token(token),
                    user_id,
                    now.isoformat(),
                    (now + timedelta(days=30)).isoformat(),
                ),
            )

    def user_for_token(self, token: str) -> UserAccount | None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT users.id, users.email, users.display_name, users.created_at, users.updated_at
                FROM sessions
                JOIN users ON users.id=sessions.user_id
                WHERE sessions.token_hash=? AND sessions.expires_at>?
                """,
                (hash_token(token), now),
            ).fetchone()
        return None if row is None else UserAccount(**dict(row))

    def delete_session(self, token: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token_hash=?", (hash_token(token),))

    def get_preferences(self, user_id: int | None = None) -> UserPreferences:
        resolved_user_id = user_id or self.default_user_id
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM user_preferences WHERE user_id=?", (resolved_user_id,)
            ).fetchone()
        if row is None:
            return UserPreferences()
        return UserPreferences.model_validate(json.loads(row["payload"]))

    def update_preferences(self, user_id: int | None = None, **changes: object) -> UserPreferences:
        resolved_user_id = user_id or self.default_user_id
        current = self.get_preferences(resolved_user_id).model_dump()
        allowed = set(current)
        current.update({key: value for key, value in changes.items() if key in allowed})
        preferences = UserPreferences.model_validate(current)
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO user_preferences(user_id,payload,updated_at) VALUES(?,?,?)
                ON CONFLICT(user_id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at
                """,
                (
                    resolved_user_id,
                    preferences.model_dump_json(),
                    now,
                ),
            )
        return preferences

    def create_equity_view(
        self,
        name: str,
        filters: EquityViewFilters,
        user_id: int | None = None,
    ) -> SavedEquityView:
        resolved_user_id = user_id or self.default_user_id
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO saved_equity_views(user_id,name,filters,created_at,updated_at)
                VALUES(?,?,?,?,?)
                """,
                (
                    resolved_user_id,
                    name.strip(),
                    filters.model_dump_json(),
                    now,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM saved_equity_views WHERE id=? AND user_id=?",
                (cursor.lastrowid, resolved_user_id),
            ).fetchone()
        if row is None:
            raise RuntimeError("saved equity view insert did not return an item")
        return self._equity_view_from_row(row)

    def list_equity_views(self, user_id: int | None = None) -> list[SavedEquityView]:
        resolved_user_id = user_id or self.default_user_id
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM saved_equity_views
                WHERE user_id=? ORDER BY updated_at DESC, id DESC
                """,
                (resolved_user_id,),
            ).fetchall()
        return [self._equity_view_from_row(row) for row in rows]

    def delete_equity_view(self, view_id: int, user_id: int | None = None) -> bool:
        resolved_user_id = user_id or self.default_user_id
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM saved_equity_views WHERE id=? AND user_id=?",
                (view_id, resolved_user_id),
            )
        return cursor.rowcount > 0

    def _equity_view_from_row(self, row: sqlite3.Row) -> SavedEquityView:
        return SavedEquityView(
            id=row["id"],
            name=row["name"],
            filters=EquityViewFilters.model_validate_json(row["filters"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create_watchlist(
        self,
        symbol: str,
        name: str,
        thesis: str,
        invalidation: str,
        user_id: int | None = None,
    ) -> WatchlistItem:
        resolved_user_id = user_id or self.default_user_id
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO watchlist(user_id,symbol,name,thesis,invalidation,status,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (resolved_user_id, symbol, name, thesis, invalidation, "new", now, now),
            )
            row = connection.execute(
                "SELECT * FROM watchlist WHERE user_id=? AND symbol=?",
                (resolved_user_id, symbol),
            ).fetchone()
        if row is None:
            raise RuntimeError("watchlist insert did not return an item")
        return WatchlistItem.model_validate(self._public_row(row))

    def get_watchlist(self, item_id: int, user_id: int | None = None) -> WatchlistItem:
        resolved_user_id = user_id or self.default_user_id
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM watchlist WHERE id=? AND user_id=?",
                (item_id, resolved_user_id),
            ).fetchone()
        if row is None:
            raise KeyError(item_id)
        return WatchlistItem.model_validate(self._public_row(row))

    def list_watchlist(self, user_id: int | None = None) -> list[WatchlistItem]:
        resolved_user_id = user_id or self.default_user_id
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM watchlist WHERE user_id=? ORDER BY updated_at DESC",
                (resolved_user_id,),
            ).fetchall()
        return [WatchlistItem.model_validate(self._public_row(row)) for row in rows]

    def update_watchlist(
        self, item_id: int, user_id: int | None = None, **changes: str
    ) -> WatchlistItem:
        resolved_user_id = user_id or self.default_user_id
        allowed = {"thesis", "invalidation", "status"}
        selected = {key: value for key, value in changes.items() if key in allowed}
        selected["updated_at"] = datetime.now(UTC).isoformat()
        assignments = ",".join(f"{key}=?" for key in selected)
        with self._connect() as connection:
            connection.execute(
                f"UPDATE watchlist SET {assignments} WHERE id=? AND user_id=?",
                (*selected.values(), item_id, resolved_user_id),
            )
        return self.get_watchlist(item_id, resolved_user_id)

    def delete_watchlist(self, item_id: int, user_id: int | None = None) -> None:
        resolved_user_id = user_id or self.default_user_id
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM watchlist WHERE id=? AND user_id=?", (item_id, resolved_user_id)
            )

    def create_holding(
        self,
        symbol: str,
        name: str,
        quantity: float,
        cost_price: float,
        target_weight: float,
        thesis: str,
        invalidation: str,
        user_id: int | None = None,
    ) -> HoldingItem:
        resolved_user_id = user_id or self.default_user_id
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO holdings(user_id,symbol,name,quantity,cost_price,target_weight,thesis,invalidation,status,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    resolved_user_id,
                    symbol,
                    name,
                    quantity,
                    cost_price,
                    target_weight,
                    thesis,
                    invalidation,
                    "holding",
                    now,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM holdings WHERE user_id=? AND symbol=?",
                (resolved_user_id, symbol),
            ).fetchone()
        if row is None:
            raise RuntimeError("holding insert did not return an item")
        return HoldingItem.model_validate(self._public_row(row))

    def get_holding(self, item_id: int, user_id: int | None = None) -> HoldingItem:
        resolved_user_id = user_id or self.default_user_id
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM holdings WHERE id=? AND user_id=?",
                (item_id, resolved_user_id),
            ).fetchone()
        if row is None:
            raise KeyError(item_id)
        return HoldingItem.model_validate(self._public_row(row))

    def list_holdings(self, user_id: int | None = None) -> list[HoldingItem]:
        resolved_user_id = user_id or self.default_user_id
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM holdings WHERE user_id=? ORDER BY updated_at DESC",
                (resolved_user_id,),
            ).fetchall()
        return [HoldingItem.model_validate(self._public_row(row)) for row in rows]

    def update_holding(
        self, item_id: int, user_id: int | None = None, **changes: object
    ) -> HoldingItem:
        resolved_user_id = user_id or self.default_user_id
        allowed = {
            "symbol",
            "name",
            "quantity",
            "cost_price",
            "target_weight",
            "thesis",
            "invalidation",
            "status",
        }
        selected = {key: value for key, value in changes.items() if key in allowed}
        selected["updated_at"] = datetime.now(UTC).isoformat()
        assignments = ",".join(f"{key}=?" for key in selected)
        with self._connect() as connection:
            connection.execute(
                f"UPDATE holdings SET {assignments} WHERE id=? AND user_id=?",
                (*selected.values(), item_id, resolved_user_id),
            )
        return self.get_holding(item_id, resolved_user_id)

    def delete_holding(self, item_id: int, user_id: int | None = None) -> None:
        resolved_user_id = user_id or self.default_user_id
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM holdings WHERE id=? AND user_id=?", (item_id, resolved_user_id)
            )
            connection.execute(
                """
                DELETE FROM decision_snapshots
                WHERE user_id=? AND source='holding' AND subject_key=?
                """,
                (resolved_user_id, str(item_id)),
            )

    @staticmethod
    def _decision_event_from_row(row: sqlite3.Row) -> DecisionEvent:
        values = {
            key: value
            for key, value in dict(row).items()
            if key in DecisionEvent.model_fields
        }
        values["user_required"] = bool(values["user_required"])
        return DecisionEvent.model_validate(values)

    def record_decision_snapshot(
        self, user_id: int, snapshot: DecisionSnapshot
    ) -> DecisionEvent | None:
        now = datetime.now(UTC).isoformat()
        decision = snapshot.decision
        with self._connect() as connection:
            current = connection.execute(
                """
                SELECT * FROM decision_snapshots
                WHERE user_id=? AND source=? AND subject_key=?
                """,
                (user_id, snapshot.source, snapshot.subject_key),
            ).fetchone()
            values = (
                snapshot.symbol,
                snapshot.name,
                snapshot.strategy,
                decision.action,
                decision.severity,
                int(decision.user_required),
                decision.reason_code,
                decision.summary,
                decision.confidence,
                snapshot.href,
                snapshot.observed_at.isoformat(),
                now,
            )
            if current is None:
                connection.execute(
                    """
                    INSERT INTO decision_snapshots(
                        user_id,source,subject_key,symbol,name,strategy,action,severity,
                        user_required,reason_code,summary,confidence,href,observed_at,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (user_id, snapshot.source, snapshot.subject_key, *values),
                )
                return None
            if str(current["action"]) == decision.action:
                connection.execute(
                    """
                    UPDATE decision_snapshots SET
                        symbol=?,name=?,strategy=?,action=?,severity=?,user_required=?,
                        reason_code=?,summary=?,confidence=?,href=?,observed_at=?,updated_at=?
                    WHERE id=?
                    """,
                    (*values, current["id"]),
                )
                return None
            email_status = (
                "pending"
                if snapshot.source == "holding" and decision.severity in {"critical", "high"}
                else "not_required"
            )
            dedup_source = ":".join(
                (
                    str(user_id),
                    snapshot.source,
                    snapshot.subject_key,
                    str(current["action"]),
                    decision.action,
                    snapshot.observed_at.isoformat(),
                )
            )
            dedup_key = hashlib.sha256(dedup_source.encode("utf-8")).hexdigest()
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO decision_events(
                    user_id,source,subject_key,symbol,name,strategy,previous_action,
                    action,summary,severity,user_required,reason_code,confidence,href,observed_at,
                    created_at,read_at,email_status,email_attempts,email_error,
                    email_sent_at,dedup_key
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    user_id,
                    snapshot.source,
                    snapshot.subject_key,
                    snapshot.symbol,
                    snapshot.name,
                    snapshot.strategy,
                    current["action"],
                    decision.action,
                    decision.summary,
                    decision.severity,
                    int(decision.user_required),
                    decision.reason_code,
                    decision.confidence,
                    snapshot.href,
                    snapshot.observed_at.isoformat(),
                    now,
                    None,
                    email_status,
                    0,
                    None,
                    None,
                    dedup_key,
                ),
            )
            connection.execute(
                """
                UPDATE decision_snapshots SET
                    symbol=?,name=?,strategy=?,action=?,severity=?,user_required=?,
                    reason_code=?,summary=?,confidence=?,href=?,observed_at=?,updated_at=?
                WHERE id=?
                """,
                (*values, current["id"]),
            )
            if cursor.rowcount == 0:
                return None
            row = connection.execute(
                "SELECT * FROM decision_events WHERE id=?", (cursor.lastrowid,)
            ).fetchone()
        if row is None:
            raise RuntimeError("decision event insert did not return a row")
        return self._decision_event_from_row(row)

    def delete_missing_holding_decision_snapshots(
        self, user_id: int, active_subject_keys: set[str]
    ) -> int:
        with self._connect() as connection:
            if not active_subject_keys:
                cursor = connection.execute(
                    "DELETE FROM decision_snapshots WHERE user_id=? AND source='holding'",
                    (user_id,),
                )
            else:
                placeholders = ",".join("?" for _ in active_subject_keys)
                cursor = connection.execute(
                    f"""
                    DELETE FROM decision_snapshots
                    WHERE user_id=? AND source='holding'
                    AND subject_key NOT IN ({placeholders})
                    """,
                    (user_id, *sorted(active_subject_keys)),
                )
        return cursor.rowcount

    def list_decision_events(self, user_id: int, limit: int = 100) -> list[DecisionEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM decision_events WHERE user_id=?
                ORDER BY read_at IS NULL DESC, observed_at DESC, id DESC LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [self._decision_event_from_row(row) for row in rows]

    def latest_decision_monitored_at(self, user_id: int) -> datetime | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT MAX(observed_at) AS monitored_at FROM decision_snapshots WHERE user_id=?",
                (user_id,),
            ).fetchone()
        value = None if row is None else row["monitored_at"]
        return None if value is None else datetime.fromisoformat(str(value))

    def get_decision_event(self, event_id: int, user_id: int) -> DecisionEvent:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM decision_events WHERE id=? AND user_id=?",
                (event_id, user_id),
            ).fetchone()
        if row is None:
            raise KeyError(event_id)
        return self._decision_event_from_row(row)

    def mark_decision_event_read(self, event_id: int, user_id: int) -> DecisionEvent:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE decision_events SET read_at=COALESCE(read_at, ?)
                WHERE id=? AND user_id=?
                """,
                (datetime.now(UTC).isoformat(), event_id, user_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(event_id)
        return self.get_decision_event(event_id, user_id)

    def mark_all_decision_events_read(self, user_id: int) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE decision_events SET read_at=?
                WHERE user_id=? AND read_at IS NULL
                """,
                (datetime.now(UTC).isoformat(), user_id),
            )
        return cursor.rowcount

    def list_pending_decision_emails(
        self, limit: int = 50, max_attempts: int = 3
    ) -> list[tuple[UserAccount, DecisionEvent]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    decision_events.*,
                    users.email AS account_email,
                    users.display_name AS account_display_name,
                    users.created_at AS account_created_at,
                    users.updated_at AS account_updated_at
                FROM decision_events
                JOIN users ON users.id=decision_events.user_id
                WHERE decision_events.email_status='pending'
                AND decision_events.email_attempts < ?
                ORDER BY decision_events.created_at, decision_events.id
                LIMIT ?
                """,
                (max_attempts, limit),
            ).fetchall()
        pending: list[tuple[UserAccount, DecisionEvent]] = []
        for row in rows:
            values = dict(row)
            account = UserAccount(
                id=values["user_id"],
                email=values.pop("account_email"),
                display_name=values.pop("account_display_name"),
                created_at=values.pop("account_created_at"),
                updated_at=values.pop("account_updated_at"),
            )
            pending.append((account, self._decision_event_from_row(row)))
        return pending

    def mark_decision_email_result(
        self, event_id: int, *, sent: bool, error: str | None = None
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT email_attempts FROM decision_events WHERE id=?", (event_id,)
            ).fetchone()
            if row is None:
                raise KeyError(event_id)
            attempts = int(row["email_attempts"]) + 1
            status = "sent" if sent else "failed" if attempts >= 3 else "pending"
            connection.execute(
                """
                UPDATE decision_events SET email_status=?,email_attempts=?,
                    email_error=?,email_sent_at=? WHERE id=?
                """,
                (
                    status,
                    attempts,
                    None if sent else (error or "send failed")[:300],
                    now if sent else None,
                    event_id,
                ),
            )

    def abandon_decision_email(self, event_id: int, error: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE decision_events SET email_status='failed',email_attempts=3,
                    email_error=?,email_sent_at=NULL WHERE id=?
                """,
                (error[:300], event_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(event_id)

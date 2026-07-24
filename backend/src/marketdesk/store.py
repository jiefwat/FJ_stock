from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from marketdesk.auth import hash_token
from marketdesk.models import (
    EquityViewFilters,
    HoldingItem,
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


class Store:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
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
            """)
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
            str(row["name"])
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
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

    def create_user(self, email: str, display_name: str, password_hash: str) -> UserAccount:
        normalized_email = email.strip().lower()
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO users(email,display_name,password_hash,created_at,updated_at)
                VALUES(?,?,?,?,?)
                """,
                (normalized_email, display_name.strip() or normalized_email, password_hash, now, now),
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

    def update_preferences(
        self, user_id: int | None = None, **changes: object
    ) -> UserPreferences:
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

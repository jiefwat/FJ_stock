from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from marketdesk.models import HoldingItem, WatchlistItem


@dataclass(frozen=True)
class SnapshotRecord:
    dataset: str
    observed_at: datetime
    payload: dict[str, object]


class Store:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS snapshots (id INTEGER PRIMARY KEY, dataset TEXT NOT NULL, observed_at TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS watchlist (id INTEGER PRIMARY KEY, symbol TEXT NOT NULL UNIQUE, name TEXT NOT NULL, thesis TEXT NOT NULL, invalidation TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS holdings (id INTEGER PRIMARY KEY, symbol TEXT NOT NULL UNIQUE, name TEXT NOT NULL, quantity REAL NOT NULL, cost_price REAL NOT NULL, target_weight REAL NOT NULL, thesis TEXT NOT NULL, invalidation TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            """)

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

    def create_watchlist(
        self, symbol: str, name: str, thesis: str, invalidation: str
    ) -> WatchlistItem:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO watchlist(symbol,name,thesis,invalidation,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (symbol, name, thesis, invalidation, "new", now, now),
            )
            row = connection.execute(
                "SELECT * FROM watchlist WHERE symbol=?", (symbol,)
            ).fetchone()
        if row is None:
            raise RuntimeError("watchlist insert did not return an item")
        return WatchlistItem(**dict(row))

    def get_watchlist(self, item_id: int) -> WatchlistItem:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM watchlist WHERE id=?", (item_id,)).fetchone()
        if row is None:
            raise KeyError(item_id)
        return WatchlistItem(**dict(row))

    def list_watchlist(self) -> list[WatchlistItem]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM watchlist ORDER BY updated_at DESC").fetchall()
        return [WatchlistItem(**dict(row)) for row in rows]

    def update_watchlist(self, item_id: int, **changes: str) -> WatchlistItem:
        allowed = {"thesis", "invalidation", "status"}
        selected = {key: value for key, value in changes.items() if key in allowed}
        selected["updated_at"] = datetime.now(UTC).isoformat()
        assignments = ",".join(f"{key}=?" for key in selected)
        with self._connect() as connection:
            connection.execute(
                f"UPDATE watchlist SET {assignments} WHERE id=?", (*selected.values(), item_id)
            )
        return self.get_watchlist(item_id)

    def delete_watchlist(self, item_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM watchlist WHERE id=?", (item_id,))

    def create_holding(
        self,
        symbol: str,
        name: str,
        quantity: float,
        cost_price: float,
        target_weight: float,
        thesis: str,
        invalidation: str,
    ) -> HoldingItem:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO holdings(symbol,name,quantity,cost_price,target_weight,thesis,invalidation,status,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
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
            row = connection.execute("SELECT * FROM holdings WHERE symbol=?", (symbol,)).fetchone()
        if row is None:
            raise RuntimeError("holding insert did not return an item")
        return HoldingItem(**dict(row))

    def get_holding(self, item_id: int) -> HoldingItem:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM holdings WHERE id=?", (item_id,)).fetchone()
        if row is None:
            raise KeyError(item_id)
        return HoldingItem(**dict(row))

    def list_holdings(self) -> list[HoldingItem]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM holdings ORDER BY updated_at DESC").fetchall()
        return [HoldingItem(**dict(row)) for row in rows]

    def update_holding(self, item_id: int, **changes: object) -> HoldingItem:
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
                f"UPDATE holdings SET {assignments} WHERE id=?", (*selected.values(), item_id)
            )
        return self.get_holding(item_id)

    def delete_holding(self, item_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM holdings WHERE id=?", (item_id,))

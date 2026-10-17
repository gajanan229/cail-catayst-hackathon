"""SQLite access (one connection, WAL). Services go through these helpers, never raw SQL elsewhere,
except the knowledge index which owns its FTS/vector tables."""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable

import orjson

SCHEMA = Path(__file__).with_name("schema.sql")

RUNTIME_TABLES = [
    "events", "episodes", "signals", "situations", "situation_members", "incidents", "incident_timeline",
    "threads", "runs", "trace_steps", "cards", "plan_steps", "approvals", "executions", "execution_tokens",
    "undo_entries", "audit_log", "ledger_entries", "ledger_events", "catalog_requests",
]


def dumps(obj: Any) -> str:
    return orjson.dumps(obj, default=_default).decode()


def _default(obj: Any):
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, (set, tuple)):
        return list(obj)
    raise TypeError(type(obj))


def loads(text: str | bytes | None) -> Any:
    return orjson.loads(text) if text else None


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.conn.executescript(SCHEMA.read_text(encoding="utf-8"))

    def close(self) -> None:
        with self.lock:
            self.conn.close()

    def execute(self, sql: str, params: Iterable = ()) -> sqlite3.Cursor:
        with self.lock:
            return self.conn.execute(sql, tuple(params))

    def executemany(self, sql: str, rows: list) -> None:
        if not rows:
            return
        with self.lock:
            self.conn.execute("BEGIN")
            try:
                self.conn.executemany(sql, rows)
                self.conn.execute("COMMIT")
            except Exception:
                self.conn.execute("ROLLBACK")
                raise

    def query(self, sql: str, params: Iterable = ()) -> list[sqlite3.Row]:
        with self.lock:
            return self.conn.execute(sql, tuple(params)).fetchall()

    # ------------------------------------------------------------ JSON document helpers

    def put(self, table: str, id_: str, data: Any, key: str = "id", **cols: Any) -> None:
        names = [key, *cols.keys(), "data"]
        values = [id_, *cols.values(), dumps(data)]
        placeholders = ",".join("?" for _ in names)
        updates = ",".join(f"{n}=excluded.{n}" for n in names[1:])
        self.execute(f"INSERT INTO {table} ({','.join(names)}) VALUES ({placeholders}) "
                     f"ON CONFLICT({key}) DO UPDATE SET {updates}", values)

    def get(self, table: str, id_: str, key: str = "id") -> Any:
        rows = self.query(f"SELECT data FROM {table} WHERE {key}=?", (id_,))
        return loads(rows[0]["data"]) if rows else None

    def all(self, table: str, where: str = "", params: Iterable = (), order: str = "", limit: int | None = None) -> list:
        sql = f"SELECT data FROM {table}"
        if where:
            sql += f" WHERE {where}"
        if order:
            sql += f" ORDER BY {order}"
        if limit:
            sql += f" LIMIT {int(limit)}"
        return [loads(r["data"]) for r in self.query(sql, params)]

    def kv_get(self, key: str, default: Any = None) -> Any:
        rows = self.query("SELECT value FROM kv WHERE key=?", (key,))
        return loads(rows[0]["value"]) if rows else default

    def kv_set(self, key: str, value: Any) -> None:
        self.execute("INSERT INTO kv (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                     (key, dumps(value)))

    def clear_runtime(self) -> None:
        with self.lock:
            self.conn.execute("BEGIN")
            for t in RUNTIME_TABLES:
                self.conn.execute(f"DELETE FROM {t}")
            self.conn.execute("DELETE FROM claims WHERE runtime = 1")
            self.conn.execute("DELETE FROM claim_reviews WHERE id LIKE 'rvw_%'")
            self.conn.execute("DELETE FROM kv WHERE key NOT IN ('read_only_default')")
            self.conn.execute("COMMIT")

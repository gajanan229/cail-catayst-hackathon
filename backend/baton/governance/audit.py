"""Append-only, hash-chained audit log (MVP spec §9.6).

hash = sha256(prev_hash + canonical JSON of the row without `hash`). GET /api/audit/verify recomputes it.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from ..core.timeutil import wall_now
from ..db.store import Store, loads

GENESIS = "0" * 64
FIELDS = ["seq", "wall_ts", "sim_ts", "actor_type", "actor_id", "action", "target", "payload", "policy_rule_ids",
          "model_id", "prompt_hash", "incident_id", "prev_hash"]


def canonical(row: dict) -> str:
    return json.dumps({k: row.get(k) for k in FIELDS}, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def row_hash(row: dict) -> str:
    return hashlib.sha256((row["prev_hash"] + canonical(row)).encode("utf-8")).hexdigest()


class AuditLog:
    def __init__(self, store: Store, publish: Callable[[str, str, Any], Any], sim_ts: Callable[[], str | None]):
        self.store = store
        self.publish = publish
        self.sim_ts = sim_ts

    def _head(self) -> tuple[int, str]:
        rows = self.store.query("SELECT seq, hash FROM audit_log ORDER BY seq DESC LIMIT 1")
        return (rows[0]["seq"], rows[0]["hash"]) if rows else (0, GENESIS)

    def append(self, actor_type: str, actor_id: str, action: str, target: str | None = None,
               payload: dict | None = None, policy_rule_ids: list[str] | None = None, model_id: str | None = None,
               prompt_hash: str | None = None, incident_id: str | None = None) -> dict:
        with self.store.lock:
            seq, prev = self._head()
            row = {
                "seq": seq + 1, "wall_ts": wall_now(), "sim_ts": self.sim_ts(), "actor_type": actor_type,
                "actor_id": actor_id, "action": action, "target": target,
                "payload": json.loads(json.dumps(payload or {}, default=str)),
                "policy_rule_ids": list(policy_rule_ids or []), "model_id": model_id, "prompt_hash": prompt_hash,
                "incident_id": incident_id, "prev_hash": prev,
            }
            row["hash"] = row_hash(row)
            self.store.execute(
                "INSERT INTO audit_log (seq, wall_ts, sim_ts, actor_type, actor_id, action, target, payload, policy_rule_ids, "
                "model_id, prompt_hash, incident_id, prev_hash, hash) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (row["seq"], row["wall_ts"], row["sim_ts"], actor_type, actor_id, action, target,
                 json.dumps(row["payload"], sort_keys=True), json.dumps(row["policy_rule_ids"]), model_id, prompt_hash,
                 incident_id, prev, row["hash"]))
        self.publish("audit", "audit.append", row)
        return row

    def _rows(self, where: str = "", params: tuple = (), limit: int | None = None, desc: bool = False) -> list[dict]:
        sql = "SELECT * FROM audit_log"
        if where:
            sql += f" WHERE {where}"
        sql += " ORDER BY seq " + ("DESC" if desc else "ASC")
        if limit:
            sql += f" LIMIT {int(limit)}"
        out = []
        for r in self.store.query(sql, params):
            d = dict(r)
            d["payload"] = loads(d["payload"]) or {}
            d["policy_rule_ids"] = loads(d["policy_rule_ids"]) or []
            out.append(d)
        return out

    def list(self, limit: int = 500, incident_id: str | None = None) -> list[dict]:
        if incident_id:
            return self._rows("incident_id = ?", (incident_id,), limit, desc=True)
        return self._rows(limit=limit, desc=True)

    def verify(self) -> dict:
        prev = GENESIS
        n = 0
        for row in self._rows():
            n += 1
            if row["prev_hash"] != prev or row_hash(row) != row["hash"]:
                return {"valid": False, "entries": n, "head_hash": row["hash"], "first_bad_seq": row["seq"]}
            prev = row["hash"]
        return {"valid": True, "entries": n, "head_hash": prev, "first_bad_seq": None}

"""Trust ledger (MVP spec §9.3): per (catalog_id, param_class, role) counters and autonomy level.

Promotion candidate (T0, L1 → L2): ≥ 20 approved unchanged, no rejection in the last 20, ≥ 2 distinct
approvers. Demotion: rejection with reason unsafe_now, verification failure, or undo after an auto-run →
down one level (minimum L1)."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import yaml

from ..core.ids import new_id
from ..core.timeutil import wall_now
from ..db.store import Store

COUNTERS = ["approved_unchanged", "edited", "rejected", "executed", "verified_ok", "verified_fail", "undone"]
ORDER = ["L0", "L1", "L2", "L3"]


def key_of(catalog_id: str, param_class: str, role: str) -> str:
    return f"{catalog_id}|{param_class}|{role}"


class Ledger:
    def __init__(self, store: Store, seed_path: Path, publish: Callable, names: Callable[[str], str],
                 tier_of: Callable[[str], str | None]):
        self.store = store
        self.seed_path = seed_path
        self.publish = publish
        self.names = names
        self.tier_of = tier_of

    # ------------------------------------------------------------ seed

    def seed(self) -> None:
        doc = yaml.safe_load(self.seed_path.read_text(encoding="utf-8"))
        for s in doc["entries"]:
            cid, pclass, role = s["key"].split("|")
            n = int(s.get("approved_unchanged", 0))
            rej = int(s.get("rejected", 0))
            outcomes = (["approved"] * min(n, 20 - min(rej, 20)) + ["rejected"] * min(rej, 20))[-20:]
            entry = {
                "key": s["key"], "catalog_id": cid, "param_class": pclass, "role": role, "level": s["level"],
                "counters": {c: 0 for c in COUNTERS}, "approvers": list(s.get("approvers") or []),
                "distinct_approvers": len(s.get("approvers") or []), "granted_by": s.get("granted_by"),
                "granted_at": s.get("granted_at"), "grant_reason": s.get("grant_reason"), "eligible_for": None,
                "recent_rejections": outcomes.count("rejected"), "last_outcomes": outcomes,
                "tier": self.tier_of(cid) if "*" not in cid else "T0",
                "history": [{"kind": "seed", "actor": "system", "reason": "Ledger seed (synthetic history)",
                             "at": s.get("granted_at") or "2026-09-01", "from_level": None, "to_level": s["level"]}],
            }
            entry["counters"]["approved_unchanged"] = n
            entry["counters"]["rejected"] = rej
            entry["counters"]["executed"] = n
            entry["counters"]["verified_ok"] = n
            self._save(entry, publish=False)

    # ------------------------------------------------------------ access

    def _save(self, entry: dict, publish: bool = True) -> dict:
        self.store.put("ledger_entries", entry["key"], entry, key="key")
        if publish:
            self.publish("ledger", "ledger.upsert", self.public(entry))
        return entry

    def public(self, e: dict) -> dict:
        granted_by = e.get("granted_by")
        return {
            "key": e["key"], "catalog_id": e["catalog_id"], "param_class": e["param_class"], "role": e["role"],
            "level": e["level"], "counters": e["counters"], "distinct_approvers": e["distinct_approvers"],
            "granted_by": self.names(granted_by) if granted_by and granted_by != "system" else granted_by,
            "granted_at": e.get("granted_at"), "grant_reason": e.get("grant_reason"), "eligible_for": e.get("eligible_for"),
            "recent_rejections": e.get("recent_rejections", 0), "tier": e.get("tier"),
            "history": e.get("history", [])[-20:],
        }

    def raw(self, key: str) -> dict | None:
        return self.store.get("ledger_entries", key, key="key")

    def get_or_create(self, catalog_id: str, param_class: str, role: str) -> dict:
        if catalog_id.startswith("baton."):
            e = self.raw("baton.*|any|any")
            if e:
                return e
        key = key_of(catalog_id, param_class, role)
        e = self.raw(key)
        if e is None:
            e = {"key": key, "catalog_id": catalog_id, "param_class": param_class, "role": role, "level": "L1",
                 "counters": {c: 0 for c in COUNTERS}, "approvers": [], "distinct_approvers": 0, "granted_by": None,
                 "granted_at": None, "grant_reason": None, "eligible_for": None, "recent_rejections": 0,
                 "last_outcomes": [], "tier": self.tier_of(catalog_id), "history": []}
        return e

    def list(self) -> list[dict]:
        return [self.public(e) for e in self.store.all("ledger_entries", order="key")]

    def level(self, catalog_id: str, param_class: str, role: str) -> dict:
        e = self.get_or_create(catalog_id, param_class, role)
        n = e["counters"]["approved_unchanged"]
        progress = f"{n} clean runs" if e["level"] in ("L2", "L3", "system") else f"{min(n, 20)}/20 clean runs" if n < 20 else f"{n} clean runs"
        if e["level"] == "L1" and n < 20:
            progress = f"{n} of 20 clean runs"
        granted = e.get("granted_by")
        return {"level": e["level"], "key": e["key"], "progress": progress,
                "granted_by": self.names(granted) if granted and granted != "system" else None,
                "card_progress": f"{n}/20 clean runs" if e["level"] == "L1" and n < 20 else f"{n} clean runs"}

    # ------------------------------------------------------------ outcomes

    def record_decision(self, catalog_id: str, param_class: str, role: str, approver: str, outcome: str,
                        reason_code: str | None = None, evaluate: bool = True) -> dict:
        """outcome: approved (unchanged) | edited | rejected."""
        e = self.get_or_create(catalog_id, param_class, role)
        if e["level"] == "system":
            return e
        if outcome == "approved":
            e["counters"]["approved_unchanged"] += 1
        elif outcome == "edited":
            e["counters"]["edited"] += 1
        elif outcome == "rejected":
            e["counters"]["rejected"] += 1
        e["last_outcomes"] = (e.get("last_outcomes", []) + [outcome])[-20:]
        e["recent_rejections"] = e["last_outcomes"].count("rejected")
        if approver and approver not in e["approvers"]:
            e["approvers"].append(approver)
            e["distinct_approvers"] = len(e["approvers"])
        if outcome == "rejected" and reason_code == "unsafe_now":
            self._demote(e, approver, "Rejected as unsafe now")
        self._save(e)
        if evaluate:
            self.evaluate_promotion(e["key"])
        return e

    def record_execution(self, catalog_id: str, param_class: str, role: str) -> None:
        e = self.get_or_create(catalog_id, param_class, role)
        if e["level"] == "system":
            return
        e["counters"]["executed"] += 1
        self._save(e)

    def record_verification(self, catalog_id: str, param_class: str, role: str, ok: bool) -> None:
        e = self.get_or_create(catalog_id, param_class, role)
        if e["level"] == "system":
            return
        e["counters"]["verified_ok" if ok else "verified_fail"] += 1
        if not ok:
            self._demote(e, "system", "Verification failed")
        self._save(e)

    def record_undo(self, catalog_id: str, param_class: str, role: str, after_auto: bool, actor: str) -> None:
        e = self.get_or_create(catalog_id, param_class, role)
        if e["level"] == "system":
            return
        e["counters"]["undone"] += 1
        if after_auto:
            self._demote(e, actor, "Undo after an auto-run")
        self._save(e)

    def _demote(self, e: dict, actor: str, reason: str) -> None:
        cur = e["level"]
        if cur not in ORDER or ORDER.index(cur) <= 1:
            return
        new = ORDER[ORDER.index(cur) - 1]
        e["level"] = new
        e["history"].append({"kind": "demotion", "actor": actor, "reason": reason, "at": wall_now(),
                             "from_level": cur, "to_level": new})
        self.store.put("ledger_events", new_id("lev"), {"key": e["key"], "kind": "demotion", "reason": reason}, key="id",
                       kind="demotion")

    def candidate_status(self, e: dict) -> bool:
        if e["level"] != "L1" or e.get("tier") not in (None, "T0"):
            return False
        last = e.get("last_outcomes", [])[-20:]
        return (e["counters"]["approved_unchanged"] >= 20 and "rejected" not in last and e["distinct_approvers"] >= 2)

    def evaluate_promotion(self, key: str, publish: bool = True) -> dict | None:
        e = self.raw(key)
        if not e:
            return None
        if self.candidate_status(e) and e.get("eligible_for") != "L2":
            e["eligible_for"] = "L2"
            e["history"].append({"kind": "promotion_candidate", "actor": "system",
                                 "reason": f"{e['counters']['approved_unchanged']} clean runs", "at": wall_now(),
                                 "from_level": "L1", "to_level": "L2"})
            self._save(e)
            role_title = e["role"].capitalize()
            text = f"{e['catalog_id']} · {role_title}: {e['counters']['approved_unchanged']} clean runs, eligible for L2"
            if publish:
                self.publish("ledger", "ledger.promotion_candidate", {"entry": self.public(e), "text": text})
            return {"entry": self.public(e), "text": text}
        return None

    def candidates(self) -> list[dict]:
        return [self.public(e) for e in self.store.all("ledger_entries") if e.get("eligible_for")]

    def grant(self, key: str, level: str, reason: str, actor: str) -> dict:
        e = self.raw(key)
        if e is None:
            raise KeyError(key)
        prev = e["level"]
        e["level"] = level
        e["granted_by"] = actor
        e["granted_at"] = wall_now()
        e["grant_reason"] = reason
        e["eligible_for"] = None
        e["history"].append({"kind": "grant", "actor": actor, "reason": reason, "at": wall_now(),
                             "from_level": prev, "to_level": level})
        self.store.put("ledger_events", new_id("lev"), {"key": key, "kind": "grant", "actor": actor, "reason": reason},
                       key="id", kind="grant")
        self._save(e)
        return self.public(e)

    def revoke(self, key: str, reason: str, actor: str) -> dict:
        e = self.raw(key)
        if e is None:
            raise KeyError(key)
        prev = e["level"]
        e["level"] = "L1"
        e["eligible_for"] = None
        e["history"].append({"kind": "revocation", "actor": actor, "reason": reason, "at": wall_now(),
                             "from_level": prev, "to_level": "L1"})
        self.store.put("ledger_events", new_id("lev"), {"key": key, "kind": "revocation", "actor": actor, "reason": reason},
                       key="id", kind="revocation")
        self._save(e)
        return self.public(e)

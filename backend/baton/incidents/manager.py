"""Incidents, timeline and undo stack (MVP spec §7.1 step 8, §9.5, §13.5)."""
from __future__ import annotations

from typing import Any, Callable

from ..core.ids import new_id
from ..core.timeutil import wall_now
from ..db.store import Store

STATUS_ORDER = ["open", "mitigating", "verifying", "resolved"]


class IncidentManager:
    def __init__(self, store: Store, publish: Callable, sim_ts: Callable[[], str | None]):
        self.store = store
        self.publish = publish
        self.sim_ts = sim_ts

    # ------------------------------------------------------------ incidents

    def _next_display_id(self) -> str:
        n = int(self.store.kv_get("incident_counter", 0)) + 1
        self.store.kv_set("incident_counter", n)
        return f"INC-{n:04d}"

    def create(self, situation: dict, thread_id: str | None = None) -> dict:
        inc = {
            "id": new_id("inc"), "display_id": self._next_display_id(), "title": situation["title"],
            "severity": situation["severity"], "status": "open", "situation_id": situation["id"], "thread_id": thread_id,
            "opened_at": self.sim_ts(), "resolved_at": None,
            "impact": {"service": (situation.get("services") or [None])[0], "p95_ms_peak": None, "timeout_pct_peak": None},
            "hypotheses_top": [], "undo_stack": [],
        }
        self.save(inc)
        self.timeline(inc["id"], "situation", {"type": "system", "id": "system", "name": "Baton pipeline"},
                      f"Situation opened: {situation['title']}",
                      f"{situation['counts']['raw_events']} events → 1 situation", {"type": "situation", "id": situation["id"]})
        return inc

    def save(self, inc: dict) -> dict:
        self.store.put("incidents", inc["id"], inc, display_id=inc["display_id"], status=inc["status"],
                       situation_id=inc["situation_id"], thread_id=inc["thread_id"], opened_at=inc["opened_at"])
        self.publish("incidents", "incident.upsert", inc)
        return inc

    def get(self, incident_id: str) -> dict | None:
        return self.store.get("incidents", incident_id)

    def list(self) -> list[dict]:
        return self.store.all("incidents", order="opened_at DESC")

    def update(self, incident_id: str, **changes: Any) -> dict | None:
        inc = self.get(incident_id)
        if not inc:
            return None
        inc.update(changes)
        return self.save(inc)

    def set_status(self, incident_id: str, status: str, actor: dict, detail: str = "") -> dict | None:
        inc = self.get(incident_id)
        if not inc or inc["status"] == status:
            return inc
        prev = inc["status"]
        inc["status"] = status
        if status == "resolved":
            inc["resolved_at"] = self.sim_ts()
        self.save(inc)
        self.timeline(incident_id, "status_change", actor, f"Status: {prev} → {status}", detail, {"type": "incident", "id": incident_id})
        return inc

    def track_impact(self, incident_id: str, values: dict[str, float]) -> None:
        inc = self.get(incident_id)
        if not inc or inc["status"] == "resolved":
            return
        svc = (inc["impact"].get("service") or "svc:atm").split(":")[-1]
        p95 = values.get(f"svc.{svc}.p95_ms")
        to = values.get(f"svc.{svc}.timeout_pct")
        changed = False
        imp = inc["impact"]
        if p95 is not None and (imp.get("p95_ms_peak") is None or p95 > imp["p95_ms_peak"]):
            imp["p95_ms_peak"] = round(p95)
            changed = True
        if to is not None and (imp.get("timeout_pct_peak") is None or to > imp["timeout_pct_peak"]):
            imp["timeout_pct_peak"] = round(to, 2)
            changed = True
        if changed:
            self.save(inc)

    # ------------------------------------------------------------ timeline

    def timeline(self, incident_id: str, kind: str, actor: dict, title: str, detail: str = "",
                 ref: dict | None = None) -> dict:
        item = {"id": new_id("tli"), "incident_id": incident_id, "sim_ts": self.sim_ts(), "wall_ts": wall_now(),
                "kind": kind, "actor": actor, "title": title, "detail": detail, "ref": ref}
        self.store.put("incident_timeline", item["id"], item, incident_id=incident_id, sim_ts=item["sim_ts"],
                       wall_ts=item["wall_ts"], kind=kind)
        self.publish("incidents", "timeline.append", {"incident_id": incident_id, "item": item})
        return item

    def timeline_items(self, incident_id: str) -> list[dict]:
        return self.store.all("incident_timeline", "incident_id = ?", (incident_id,), order="sim_ts, wall_ts")

    # ------------------------------------------------------------ undo stack

    def push_undo(self, incident_id: str, entry: dict) -> None:
        inc = self.get(incident_id)
        if not inc:
            return
        inc["undo_stack"] = [entry, *[e for e in inc["undo_stack"] if e["id"] != entry["id"]]]
        self.store.put("undo_entries", entry["id"], entry, incident_id=incident_id, execution_id=entry["execution_id"],
                       status=entry["status"])
        self.save(inc)

    def mark_undo(self, incident_id: str, undo_id: str, status: str) -> None:
        inc = self.get(incident_id)
        if not inc:
            return
        for e in inc["undo_stack"]:
            if e["id"] == undo_id:
                e["status"] = status
                self.store.put("undo_entries", e["id"], e, incident_id=incident_id, execution_id=e["execution_id"], status=status)
        self.save(inc)

    # ------------------------------------------------------------ postmortem

    def save_postmortem(self, incident_id: str, pm: dict) -> None:
        self.store.kv_set(f"postmortem:{incident_id}", pm)

    def postmortem(self, incident_id: str) -> dict | None:
        return self.store.kv_get(f"postmortem:{incident_id}")

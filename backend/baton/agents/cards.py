"""Card store and builders (MVP spec §13.4, §15.2). Cards are validated against the contract on write,
persisted per thread with a stable `seq`, and published as card.upsert on thread:{id}."""
from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter

from ..core.ids import new_id
from ..core.timeutil import iso_sim, wall_now
from ..schemas.cards import Card

CARD = TypeAdapter(Card)


class CardStore:
    def __init__(self, rt):
        self.rt = rt

    def _next_seq(self, thread_id: str) -> int:
        rows = self.rt.store.query("SELECT MAX(seq) AS s FROM cards WHERE thread_id = ?", (thread_id,))
        return int(rows[0]["s"] or 0) + 1

    def get(self, card_id: str) -> dict | None:
        return self.rt.store.get("cards", card_id)

    def upsert(self, card: dict) -> dict:
        existing = self.get(card["id"]) if card.get("id") else None
        if existing:
            card = {**existing, **card, "seq": existing["seq"], "created_at": existing["created_at"]}
        else:
            card.setdefault("id", new_id("card"))
            card.setdefault("seq", self._next_seq(card["thread_id"]))
            card.setdefault("created_at", wall_now())
            card.setdefault("sim_ts", iso_sim(self.rt.sim.now))
        card.setdefault("citations", [])
        card.setdefault("actions", [])
        card.setdefault("source", None)
        data = CARD.validate_python(card).model_dump(mode="json", by_alias=True)
        self.rt.store.put("cards", data["id"], data, thread_id=data["thread_id"], incident_id=data.get("incident_id"),
                          type=data["type"], seq=data["seq"])
        self.rt.hub.publish(f"thread:{data['thread_id']}", "card.upsert", data)
        return data

    def patch(self, card_id: str, **changes: Any) -> dict | None:
        card = self.get(card_id)
        if not card:
            return None
        body = changes.pop("body", None)
        if body:
            card["body"] = {**card["body"], **body}
        card.update(changes)
        return self.upsert(card)

    def for_thread(self, thread_id: str) -> list[dict]:
        return self.rt.store.all("cards", "thread_id = ?", (thread_id,), order="seq")

    def for_incident(self, incident_id: str) -> list[dict]:
        return self.rt.store.all("cards", "incident_id = ?", (incident_id,), order="seq")


def command_body(p, *, purpose: str | None = None, why_now: dict | None = None, expected: str | None = None,
                 approval_id: str | None = None, approval_progress: str | None = None) -> dict:
    v = p.validation
    e = p.entry
    undo = None
    if v.undo and v.undo_rendered:
        undo = {"catalog_id": v.undo["catalog_id"], "params": v.undo["params"], "rendered": v.undo_rendered}
    autonomy = None if e.internal else {"level": p.autonomy["level"], "key": p.autonomy["key"],
                                        "progress": p.autonomy["progress"], "granted_by": p.autonomy["granted_by"]}
    return {
        "step_id": p.step_id, "catalog_id": p.catalog_id, "interpreter": e.interpreter,
        "rendered": v.rendered or e.title, "params": v.params, "purpose": purpose or e.description,
        "why_now": why_now, "expected": expected, "risks": e.risks if not e.side_effects.startswith("None") else e.risks,
        "tier": v.tier, "internal": e.internal, "autonomy": autonomy, "policy": p.policy, "undo": undo,
        "approval_id": approval_id, "approval_progress": approval_progress, "approvers": [], "execution": None,
        "validation_errors": list(v.errors),
    }


def command_status(p) -> tuple[str, list[str]]:
    if p.denied:
        return "blocked", []
    if p.auto:
        return "auto_running", []
    return "awaiting_approval", ["approve", "edit", "reject"]


def execution_block(rt, ex: dict, summary: str | None = None, summary_source: str | None = None) -> dict:
    from ..commands.executor import facts_table

    started, ended = ex.get("started_at"), ex.get("ended_at")
    dur = None
    try:
        from datetime import datetime
        if started and ended:
            f = "%Y-%m-%dT%H:%M:%S.%fZ"
            dur = int((datetime.strptime(ended, f) - datetime.strptime(started, f)).total_seconds() * 1000)
    except ValueError:
        dur = None
    return {"exec_id": ex["id"], "status": ex["status"], "duration_ms": dur, "raw_output": ex.get("raw_text"),
            "facts": ex.get("facts"), "facts_table": facts_table(ex["catalog_id"], ex.get("facts") or {}),
            "summary": summary, "summary_source": summary_source,
            "approved_by": [rt.users.name(a) for a in ex.get("approved_by", [])], "auto": bool(ex.get("auto"))}

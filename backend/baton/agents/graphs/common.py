"""Helpers shared by the graphs: runtime access, trace context, card helpers, approval waiting."""
from __future__ import annotations

from typing import Any

from langgraph.types import interrupt

from ...api.deps import rt as get_rt
from ...core.timeutil import iso_sim


def ctx(config: dict) -> dict:
    c = config.get("configurable", {})
    return {"thread_id": c.get("baton_thread"), "run_id": c.get("run_id"), "graph_key": c.get("graph_key")}


def node(config: dict, name: str, label: str, step_id: str | None = None):
    rt = get_rt()
    return rt.agents.tracer.node(ctx(config), name, label, step_id=step_id)


def card(config: dict, **kw) -> dict:
    rt = get_rt()
    c = ctx(config)
    kw.setdefault("thread_id", c["thread_id"])
    return rt.agents.cards.upsert(kw)


def patch(card_id: str, **changes: Any) -> dict | None:
    return get_rt().agents.cards.patch(card_id, **changes)


def wait_for_approval(approval_id: str, prompt: str) -> dict:
    """Pause the graph until the approval is complete. If it already is (decided while the graph was busy),
    return its status without interrupting."""
    rt = get_rt()
    a = rt.approvals.get(approval_id)
    rt.approvals.check_expired(a)
    if a["status"] in ("approved", "rejected", "expired"):
        return {"approval_id": approval_id, "status": a["status"], "decisions": a["decisions"]}
    return interrupt({"kind": "approval", "approval_id": approval_id, "prompt": prompt})


def sim_ts() -> str | None:
    return iso_sim(get_rt().sim.now)


def edited_params(decisions: list[dict]) -> dict | None:
    for d in decisions:
        if d.get("decision") == "edit_approve" and d.get("params"):
            return d["params"]
    return None

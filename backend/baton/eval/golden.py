"""A scripted operator that drives an incident through the REST API, the way the golden path does
(MVP spec §3 Flow A). Used by tests/test_golden_s1.py, scripts/record_ws.py, `make record` and the
diagnosis eval (S1, S3)."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from ..core.timeutil import parse_sim

FLOW_B = [("Is ATM auth keeping up?", "u_priya"),
          ("What's the difference between NUMSTATIC and MAXSERVERS?", "u_priya")]
FLOW_C = [("reload CPU 3", "u_priya"), ("stop TMF", "u_priya"), ("suspend $PM1", "u_priya")]


@dataclass
class DriveResult:
    incident: dict | None = None
    situation: dict | None = None
    top_hypothesis: str | None = None
    top_p: float | None = None
    options: list = field(default_factory=list)
    situation_at: str | None = None
    stop_met_at: str | None = None
    first_action_at: str | None = None
    resolved_at: str | None = None
    claims: list = field(default_factory=list)
    log: list = field(default_factory=list)
    ok: bool = False
    error: str | None = None


async def until(fn, timeout=60.0, step=0.05, what="condition"):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        v = await fn()
        if v:
            return v
        await asyncio.sleep(step)
    raise TimeoutError(f"timed out waiting for {what}")


async def wait_run_idle(api: httpx.AsyncClient, thread_id: str, timeout: float = 30.0) -> dict:
    async def idle():
        d = (await api.get(f"/api/threads/{thread_id}")).json()
        return d if d["thread"]["status"] in ("idle", "waiting", "done", "failed") else None
    return await until(idle, timeout, what="thread idle")


async def flow_b(api: httpx.AsyncClient, log: list) -> None:
    """Before the fault: plain language → command plan, edit-and-approve the second card, then a question."""
    t = (await api.post("/api/threads", json={"mode": "auto", "actor": "u_priya"})).json()
    await api.post(f"/api/threads/{t['id']}/messages", json={"text": FLOW_B[0][0], "actor": "u_priya"})

    async def pending():
        aps = (await api.get("/api/approvals", params={"status": "pending"})).json()["approvals"]
        return next((a for a in aps if a["thread_id"] == t["id"]), None)
    try:
        a = await until(pending, 20, what="Flow B approval")
        step = a["step_ids"][0]
        prev = (await api.post("/api/commands/preview", json={"catalog_id": "pathcom.stats_server",
                                                              "params": {"server_class": "ATM-AUTH"}, "actor": "u_priya"})).json()
        log.append(("flow_b.preview", prev.get("valid")))
        await api.post(f"/api/approvals/{a['id']}/decide", json={"decision": "edit_approve", "params": {"server_class": "ATM-AUTH"},
                                                                 "actor": "u_priya"})
        log.append(("flow_b.approved", a["rendered"]))
    except TimeoutError:
        log.append(("flow_b.no_approval", None))
    await wait_run_idle(api, t["id"])
    await api.post(f"/api/threads/{t['id']}/messages", json={"text": FLOW_B[1][0], "actor": "u_priya"})
    await wait_run_idle(api, t["id"])


async def flow_c(api: httpx.AsyncClient, log: list) -> None:
    t = (await api.post("/api/threads", json={"mode": "auto", "actor": "u_priya"})).json()
    for text, actor in FLOW_C:
        await api.post(f"/api/threads/{t['id']}/messages", json={"text": text, "actor": actor})
        await wait_run_idle(api, t["id"])
    log.append(("flow_c.done", t["id"]))


async def drive_incident(api: httpx.AsyncClient, rt, *, scenario: str = "S1", profile: str = "test", inject: dict | None = None,
                         ask: str | None = "ATM withdrawals are slow. What's going on?", timeout: float = 180.0,
                         with_flows: bool = False, learn: bool = True) -> DriveResult:
    res = DriveResult()
    log = res.log
    try:
        r = await api.post("/api/sim/start", json={"scenario": scenario, "profile": profile, "actor": "u_priya"})
        r.raise_for_status()
        if with_flows:
            await flow_b(api, log)
            await flow_c(api, log)
        if inject:
            await api.post("/api/sim/inject", json={**inject, "actor": "u_priya"})

        async def incident():
            incs = (await api.get("/api/incidents")).json()["incidents"]
            return incs[0] if incs and incs[0].get("thread_id") else None
        inc = await until(incident, timeout, what="incident")
        res.incident = inc
        sits = (await api.get("/api/situations")).json()["situations"]
        res.situation = next((s for s in sits if s["id"] == inc["situation_id"]), None)
        res.situation_at = (res.situation or {}).get("first_at")
        thread = inc["thread_id"]
        asked = False
        t_end = time.monotonic() + timeout
        decided = set()
        while time.monotonic() < t_end:
            d = (await api.get(f"/api/threads/{thread}")).json()
            i = (await api.get(f"/api/incidents/{inc['id']}")).json()
            hyp = next((c for c in d["cards"] if c["type"] == "hypotheses"), None)
            if hyp:
                res.top_hypothesis = hyp["body"]["hypotheses"][0]["id"]
                res.top_p = hyp["body"]["hypotheses"][0]["p"]
                if hyp["body"]["stop_rule"]["met"] and not res.stop_met_at:
                    res.stop_met_at = rt.sim.state_dict()["sim_ts"]
            if i["status"] == "resolved":
                res.resolved_at = i["resolved_at"]
                break
            if d["thread"]["status"] == "failed" or any(c["type"] == "escalation" for c in d["cards"]) and d["thread"]["status"] != "running":
                res.error = "escalated or failed"
                break
            aps = (await api.get("/api/approvals")).json()["approvals"]
            for a in aps:
                if a["thread_id"] != thread or a["id"] in decided:
                    continue
                if a["status"] == "pending" and a["step_ids"] and a["step_ids"][0].startswith("stp_decision_"):
                    dc = next((c for c in d["cards"] if c["type"] == "decision"), None)
                    if not dc:
                        continue
                    res.options = dc["body"]["options"]
                    rec = next((o["id"] for o in dc["body"]["options"] if o.get("recommended")), None)
                    if ask and not asked:
                        await api.post(f"/api/threads/{thread}/messages", json={"text": ask, "actor": "u_priya"})
                        asked = True
                    r = await api.post(f"/api/approvals/{a['id']}/decide",
                                       json={"decision": "approve", "option_ids": [rec], "actor": "u_priya"})
                    log.append(("decide", rec, r.status_code))
                    res.first_action_at = rt.sim.state_dict()["sim_ts"]
                    decided.add(a["id"])
                elif a["status"] == "pending":
                    r = await api.post(f"/api/approvals/{a['id']}/decide", json={"decision": "approve", "actor": "u_priya"})
                    log.append(("approve", a["rendered"], r.status_code))
                    decided.add(a["id"])
                elif a["status"] == "partially_approved":
                    r = await api.post(f"/api/approvals/{a['id']}/decide", json={"decision": "approve", "actor": "u_sam"})
                    log.append(("second", a["rendered"], r.status_code))
                    decided.add(a["id"])
            await asyncio.sleep(0.05)
        if learn and res.resolved_at:
            async def learned():
                cl = (await api.get("/api/claims", params={"status": "pending_review"})).json()["claims"]
                mine = [c for c in cl if c["provenance"]["source_id"] == inc["id"]]
                return mine if len(mine) >= 2 else None
            try:
                res.claims = await until(learned, 30, what="claims")
            except TimeoutError:
                pass
        res.ok = res.resolved_at is not None
    except Exception as e:  # report, do not raise: eval runners record failures
        res.error = f"{type(e).__name__}: {e}"
    return res


def sim_seconds(a: str | None, b: str | None) -> float | None:
    if not a or not b:
        return None
    return (parse_sim(b) - parse_sim(a)).total_seconds()

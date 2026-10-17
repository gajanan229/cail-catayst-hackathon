"""Learn (MVP spec §11.1, §12.7): postmortem (Scribe), claims (Curator), ledger updates, audit.
Model first, template fallback."""
from __future__ import annotations

from .. import prompts as P

SHORT = {"atm": "ATM", "pos": "POS"}


def _incident_facts(rt, state: dict) -> dict:
    inc = rt.incidents.get(state["incident_id"])
    timeline = rt.incidents.timeline_items(state["incident_id"])
    executed = [o for o in state.get("options", []) if o["id"] in state.get("executed", []) and o.get("steps")]
    return {"incident": inc, "timeline": timeline, "executed": executed}


async def write_postmortem(rt, state: dict, run_id: str) -> tuple[dict, str, str | None]:
    f = _incident_facts(rt, state)
    inc, timeline, executed = f["incident"], f["timeline"], f["executed"]
    v = state.get("vars", {})
    lead = state["hyps"][0]
    imp = inc.get("impact", {})
    svc = SHORT.get((imp.get("service") or "svc:atm").split(":")[-1], "ATM")
    actions = [f"{st['rendered']} (undo: {st['undo']})" if st.get("undo") else st["rendered"] for o in executed for st in o["steps"]]
    follow = []
    for o in executed:
        for st in o["steps"]:
            if st["catalog_id"] == "pathcom.alter_numstatic":
                follow.append(f"After hardware repair, set NUMSTATIC back to {v.get('current_numstatic') or 20}")
            if st["catalog_id"] == "tacl.suspend_process":
                follow.append(f"ACTIVATE {st['params'].get('process')} after 13:00")
    if v.get("down_cpu") is not None:
        follow.append(f"Reload CPU {v['down_cpu']} with hardware support, then rebalance server classes before the next peak (C-016)")
    lines = [f"- {(it['sim_ts'] or '')[11:19]} {it['title']}" for it in timeline if it["kind"] in
             ("situation", "check", "approval_decided", "action_executed", "verification", "status_change")]
    fallback = {
        "incident_id": inc["id"],
        "summary": f"{inc['title']} on \\TORBANK. Baton opened {inc['display_id']}, diagnosed {lead['label'][0].lower() + lead['label'][1:]} "
                   f"({lead['p']:.2f}) and the team mitigated it with {len(actions)} approved action(s).",
        "impact": f"{svc} authorization p95 peaked at {imp.get('p95_ms_peak') or '?'} ms with timeouts up to "
                  f"{imp.get('timeout_pct_peak') or 0}%.",
        "timeline_md": "\n".join(lines[:20]),
        "cause": f"{lead['label']}: " + ", ".join(x["label"] for x in lead.get("for", [])[:3]) + ".",
        "actions": actions,
        "follow_ups": follow,
    }
    out, src, phash = await rt.gateway.complete("scribe", P.SYSTEM, P.render(
        "scribe", incident={k: inc.get(k) for k in ("display_id", "title", "impact", "severity")},
        timeline=[{"t": it["sim_ts"], "title": it["title"], "actor": it["actor"]["name"]} for it in timeline[:40]],
        options=[o["label"] for o in executed], verification=state.get("verification", {}).get("title")), P.ScribeOut,
        run_id=run_id, node="postmortem")
    pm = {**fallback, **out} if out else fallback
    pm["incident_id"] = inc["id"]
    pm["source"] = src if out else "fallback"
    from ...core.timeutil import iso_sim
    pm["created_sim_ts"] = iso_sim(rt.sim.now)
    rt.incidents.save_postmortem(inc["id"], pm)
    return pm, pm["source"], phash


TEMPLATES = {
    "cpu_capacity_loss": [
        lambda v, d: {
            "statement": f"When a CPU halts at peak on \\TORBANK, suspending {d.get('batch', '$STMT1')} and raising "
                         f"{v.get('server_class', 'ATM-AUTH')} NUMSTATIC by 8 restores {v.get('SERVICE', 'ATM')} p95 to band within about 2 minutes.",
            "subject": [d.get("batch", "$STMT1"), v.get("server_class", "ATM-AUTH"), f"CPU {v.get('hottest_cpu', 5)}"],
            "condition": "Peak day, one CPU down, the critical server class lost servers",
            "assertion": "Suspending the noon batch and adding 8 static servers recovers the service latency",
            "recommendation": {"catalog_id": "pathcom.alter_numstatic",
                               "params": {"server_class": v.get("server_class", "ATM-AUTH"), "n": d.get("n", 28)}},
            "rationale": f"{d['display_id']}: {v.get('SERVICE', 'ATM')} p95 back in band 60 s after both actions",
            "scope": {"site": "TORBANK", "calendar": [d.get("calendar", "black_friday")]}, "confidence": "likely"},
        lambda v, d: {
            "statement": f"After losing CPU {v.get('down_cpu', 3)}, PATHMON does not restart the lost {v.get('server_class', 'ATM-AUTH')} "
                         f"servers by itself; plan the extra static servers before the next peak.",
            "subject": [v.get("server_class", "ATM-AUTH"), "PATHMON $PM1"],
            "condition": "Any CPU loss while PATHMON runs on its backup",
            "assertion": "Lost servers stay lost until NUMSTATIC is raised or the CPU returns",
            "recommendation": None,
            "rationale": f"{d['display_id']}: running stayed at {v.get('current_running', 20)} until NUMSTATIC was raised",
            "scope": {"site": "TORBANK"}, "confidence": "likely"},
    ],
}


async def draft_claims(rt, state: dict, run_id: str) -> tuple[list[dict], str]:
    f = _incident_facts(rt, state)
    inc = f["incident"]
    v = state.get("vars", {})
    mode = state["hyps"][0]["id"]
    approvals = rt.store.all("approvals", "incident_id = ?", (inc["id"],))
    author = next((d["actor"] for a in approvals if a.get("kind") == "decision" for d in a["decisions"]), None) or "u_priya"
    reviewer = "u_dave" if author != "u_dave" else "u_maria"
    batch = next((st["params"].get("process") for o in f["executed"] for st in o["steps"] if st["catalog_id"] == "tacl.suspend_process"), None)
    n = next((st["params"].get("n") for o in f["executed"] for st in o["steps"] if st["catalog_id"] == "pathcom.alter_numstatic"), None)
    m = rt.sim.model
    d = {"display_id": inc["display_id"], "batch": batch or "$STMT1", "n": n or 28,
         "calendar": (m.calendar.get("type") if m else "black_friday") or "normal"}
    drafts = []
    src = "fallback"
    out, msrc, _ = await rt.gateway.complete("curator", P.SYSTEM, P.render(
        "curator", incident={"display_id": inc["display_id"], "title": inc["title"], "impact": inc["impact"],
                             "actions": [o["label"] for o in f["executed"]], "diagnosis": state["hyps"][0]["label"]},
        expert=state.get("expert") or {}, approvals=[{"rendered": a["rendered"], "status": a["status"],
                                                       "decisions": [x["decision"] for x in a["decisions"]]} for a in approvals]),
        P.CuratorOut, run_id=run_id, node="claims")
    if out:
        drafts = [dict(c) for c in out["claims"][:2]]
        src = msrc
    if len(drafts) < 2:
        tpls = TEMPLATES.get(mode, [])
        drafts += [t(v, d) for t in tpls][len(drafts):2]
    if len(drafts) < 2:
        lead = state["hyps"][0]
        drafts += [{"statement": f"{inc['title']}: {lead['label']} was confirmed by " + ", ".join(x["label"] for x in lead["for"][:2]),
                    "subject": [v.get("server_class", "")], "condition": inc["title"], "assertion": lead["label"],
                    "recommendation": None, "rationale": inc["display_id"], "scope": {"site": "TORBANK"}, "confidence": "tentative"}]
    created = []
    for dr in drafts[:2]:
        structured = {"subject": dr.get("subject", []), "condition": dr.get("condition", ""), "assertion": dr.get("assertion", ""),
                      "recommendation": dr.get("recommendation"), "rationale": dr.get("rationale", "")}
        c = rt.claims.create_draft(dr["statement"], structured, dr.get("scope") or {"site": "TORBANK"},
                                   dr.get("confidence", "likely"), author, reviewer, inc["id"])
        created.append(c)
    return created, src

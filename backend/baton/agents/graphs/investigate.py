"""Investigate graph (MVP spec §11.1, §12): the incident loop, from situation to verified recovery and learning.

A pre-investigation runs with actor "Baton" in auto-only mode: it auto-runs only what the ledger allows and pauses
for everything else; humans join the same thread through approvals.
"""
from __future__ import annotations

import asyncio
import copy
import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ...api.deps import rt as get_rt
from ...core.ids import new_id
from ...core.timeutil import iso_sim
from ...knowledge.claims import build_expert_card
from .. import prompts as P
from ..cards import command_body, execution_block
from .command import _cmd_citations, interpret_template
from .common import card, ctx, node, patch, wait_for_approval
from .learn import draft_claims, write_postmortem

SHORT = {"atm": "ATM", "pos": "POS", "bal": "Balance inquiry", "card": "Card maintenance"}
CLASS_OF = {"atm": "ATM-AUTH", "pos": "POS-AUTH", "bal": "BAL-INQ", "card": "CARD-MGMT"}
VERIFY_TIMEOUT_S = 420
TEMPLATE_HINTS = {"cpu_loss_cascade": "CPU halt peak takeover servers", "audit_trail_pressure": "audit trail month-end batch",
                  "fallback": "link errors 1034 MAXSERVERS"}


class InvState(TypedDict, total=False):
    thread_id: str
    incident_id: str
    situation_id: str
    actor: str
    auto_only: bool
    vars: dict
    obs: dict
    evidence: list
    hyps: list
    prev: dict
    round: int
    checks_run: list
    batch: list
    cards: dict
    stop: dict
    expert: dict | None
    options: list
    decision_approval_id: str | None
    selected: list
    option_approvals: dict
    executed: list
    verification: dict
    outcome: str
    decided_by: str | None
    current_wait: str | None


# ---------------------------------------------------------------- helpers

def _evidence(state: InvState, type_: str, label: str, source: str, preview: dict) -> tuple[list, str]:
    ev = list(state.get("evidence", []))
    eid = f"ev_{len(ev) + 1:02d}"
    ev.append({"id": eid, "type": type_, "label": label, "source": source, "preview": preview})
    return ev, eid


def _mode_ctx(state: InvState) -> dict:
    v = dict(state.get("vars", {}))
    return v


def _hyp_body(rt, state: InvState, hyps: list, round_: int, stop: dict | None, narrative=None, narrative_source=None) -> dict:
    stop = stop or rt.diagnosis.stop_rule(hyps, round_)
    return {"round": round_, "stop_rule": {"met": stop["met"], "top": stop["top"], "margin": stop["margin"], "reason": stop["reason"]},
            "hypotheses": [{k: h[k] for k in ("id", "label", "p", "delta", "for", "against", "would_change_mind")} for h in hyps],
            "narrative": narrative, "narrative_source": narrative_source}


def _publish_hyps(config, state: InvState, hyps: list, round_: int, stop: dict | None = None, narrative=None, nsrc=None) -> None:
    rt = get_rt()
    cid = state["cards"].get("hypotheses")
    body = _hyp_body(rt, state, hyps, round_, stop, narrative, nsrc)
    if cid:
        if narrative is None:
            old = rt.agents.cards.get(cid)
            body["narrative"] = old["body"].get("narrative") if old else None
            body["narrative_source"] = old["body"].get("narrative_source") if old else None
        patch(cid, body=body)
    top = [{"id": h["id"], "label": h["label"], "p": h["p"]} for h in hyps[:3]]
    rt.incidents.update(state["incident_id"], hypotheses_top=top)
    rt.store.kv_set(f"incident_state:{state['incident_id']}", {**(rt.store.kv_get(f"incident_state:{state['incident_id']}", {})),
                                                             "hypotheses": body["hypotheses"], "round": round_,
                                                             "stop_rule": body["stop_rule"]})


def _rescore(state: InvState, obs: dict) -> list:
    rt = get_rt()
    prev = {h["id"]: h["p"] for h in state.get("hyps", [])}
    return rt.diagnosis.score(obs, _mode_ctx(state), prev)


def _check_params(catalog_id: str, v: dict) -> dict:
    if catalog_id in ("pathcom.status_server", "pathcom.info_server", "pathcom.stats_server"):
        return {"server_class": v.get("server_class", "ATM-AUTH")}
    if catalog_id == "tacl.status_cpu":
        return {"cpu": v.get("hottest_cpu", 5)}
    if catalog_id == "baton.service_kpis":
        return {"service": v.get("service", "atm")}
    return {}


def _check_texts(catalog_id: str, v: dict, check: dict) -> tuple[str, str, dict | None]:
    cls, down, svc = v.get("server_class", "ATM-AUTH"), v.get("down_cpu"), v.get("SERVICE", "ATM")
    why = {"hypothesis_id": check.get("hypothesis_id")}
    if check.get("claim_id"):
        why["claim_id"] = check["claim_id"]
    texts = {
        "meas.cpu_busy": ("Which survivor is hottest after the CPU loss?", "One survivor near saturation if capacity was lost"),
        "pathcom.status_server": (f"How many {cls} servers were lost with CPU {down}?" if down is not None else f"Is {cls} at its limit?",
                                  f"Running below {v.get('running_before', 24)} if servers died with CPU {down}" if down is not None
                                  else "Running at MAXSERVERS with a queue if the class is starved"),
        "pathcom.info_server": (f"Is {cls} configured with room to grow?", "MAXSERVERS above the running count"),
        "tmfcom.status_audittrail": ("Rule out TMF audit-trail pressure, rare but costly on a peak day" if check.get("rule_out")
                                     else "How full is the TMF audit trail?", "Fill well below the 80% overflow threshold"),
        "tmfcom.status_tmf": ("Is TMF healthy?", "TMF started with a normal abort rate"),
        "baton.n1_headroom": ("What is left if another CPU fails?", "Worst survivor below 90%"),
        "baton.service_kpis": (f"How much are {svc} customers affected?", "p95 inside the baseline band"),
        "tacl.status_cpu": (f"What is using CPU {v.get('hottest_cpu')}?", "No single process above 40%"),
    }
    purpose, expected = texts.get(catalog_id, (f"Test {check.get('hypothesis_id')}", None))
    return purpose, expected, why


def observations_from_facts(rt, catalog_id: str, facts: dict, v: dict) -> tuple[dict[str, str], dict]:
    """Return ({observation: label}, context updates)."""
    obs: dict[str, str] = {}
    upd: dict[str, Any] = {}
    if catalog_id == "meas.cpu_busy" and facts.get("cpus"):
        up = {int(c): x["busy"] for c, x in facts["cpus"].items() if x["state"] == "UP" and x["busy"] is not None}
        if up:
            hot = max(up, key=lambda c: up[c])
            upd.update(hottest_cpu=hot, hottest_busy=up[hot])
            if up[hot] >= 90:
                obs["cpu_busy_high_survivor"] = f"CPU {hot} at {up[hot]:.0f}%"
            m = rt.sim.model
            at_max = any(sc.running(m.tick) >= sc.maxservers for sc in m.classes.values()) if m else False
            any_down = any(x["state"] == "DOWN" for x in facts["cpus"].values())
            # a node with a processor down is not "internally healthy", however quiet the survivors are
            if all(b < 75 for b in up.values()) and not at_max and not any_down:
                obs["internals_healthy"] = "All CPUs below 75%, no class at max"
    elif catalog_id == "pathcom.status_server" and "running" in facts:
        run, mx, q = facts["running"], facts["maxservers"], facts["queued"]
        upd.update(current_running=run, current_max=mx, current_numstatic=facts["numstatic"])
        m = rt.sim.model
        # "lost" = servers that died with a halted CPU (recorded by the simulator), not a configuration cap
        lost = m.lost_servers.get(facts["server_class"], 0) if m else 0
        if lost and lost / (run + lost) >= 0.15:
            obs["sc_lost_servers"] = f"{facts['server_class']} lost {lost} servers"
        if run < mx:
            obs["sc_not_at_max"] = f"{run} of {mx} running: not at max"
        elif q > 0:
            obs["sc_at_max_queued"] = f"{facts['server_class']} at MAXSERVERS ({run}/{mx}), {q} queued"
    elif catalog_id == "tmfcom.status_audittrail" and "fill_pct" in facts:
        f = facts["fill_pct"]
        if f >= 70:
            obs["audit_fill_high"] = f"Audit trail {f:.0f}% full"
        elif f < 50:
            obs["audit_fill_normal"] = f"Audit trail {f:.0f}%: normal"
        trend = rt.pipeline.fill_trend()
        if trend is not None and trend > 0.5:
            obs["audit_fill_rising"] = f"Audit fill rising {trend:.1f}%/min"
    elif catalog_id == "tacl.status_cpu" and facts.get("processes"):
        top = facts["processes"][0]
        if top["busy"] >= 40 and not top["name"].endswith(")"):
            obs["one_process_hot"] = f"{top['name']} at {top['busy']:.0f}% of a CPU"
            upd["hot_process"] = top["name"]
    elif catalog_id == "baton.service_kpis" and facts.get("p95_ms") is not None:
        if not facts.get("in_band"):
            obs["latency_out_of_band"] = f"{facts['service'].upper()} p95 {facts['p95_ms']:.0f} ms above band"
    return obs, upd


# ---------------------------------------------------------------- nodes

async def read_situation(state: InvState, config) -> dict:
    rt = get_rt()
    async with node(config, "read_situation", "Read the situation") as s:
        sit = rt.pipeline.situation_detail(state["situation_id"]) or {}
        v: dict[str, Any] = {}
        origin = sit.get("origin", {}).get("component_id", "")
        if origin.startswith("cpu:"):
            v["down_cpu"] = int(origin.split(":")[1])
        svc = (sit.get("services") or ["svc:atm"])[0].split(":")[-1]
        v.update(service=svc, SERVICE=SHORT.get(svc, svc.upper()), server_class=CLASS_OF.get(svc, "ATM-AUTH"))
        for c in sit.get("components", []):
            if c.startswith("sc:") and c[3:] == CLASS_OF.get(svc):
                v["server_class"] = c[3:]
        # servers running before the fault (for sc_lost_servers): max over the last 5 minutes of history
        hist = rt.metrics.window(f"sc.{v['server_class']}.running", 60)
        if hist:
            v["running_before"] = int(max(hist))
        m = rt.sim.model
        v["peak_day"] = bool(m and m.calendar.get("type") in ("black_friday", "christmas_eve", "month_end"))
        counts = sit.get("counts", {"raw_events": 0, "episodes": 0, "signals": 0})
        age = 0
        sc = card(config, type="situation", status="info", title=sit.get("title", "Situation"), incident_id=state["incident_id"],
                  body={"situation_id": state["situation_id"], "severity": sit.get("severity", 4),
                        "components": sit.get("components", []), "services": sit.get("services", []), "counts": counts,
                        "collapse_text": f"{counts['raw_events']} events → 1 situation", "template": sit.get("template", ""),
                        "first_at": sit.get("first_at") or iso_sim(rt.sim.now), "age_s": age,
                        "suggested_playbooks": sit.get("suggested_playbooks", [])},
                  actions=["open_incident_room"])
        rt.incidents.timeline(state["incident_id"], "note", rt.users.actor_ref("baton"), "Pre-investigation started",
                              "Baton is gathering evidence (auto-only)", {"type": "card", "id": sc["id"]})
        s.summary = f"{sit.get('title')} · {counts['raw_events']} events, {counts['signals']} signals"
        s.tools = ["pipeline.situation"]
    return {"vars": v, "obs": {}, "evidence": [], "round": 0, "checks_run": [], "batch": [], "cards": {"situation": sc["id"]},
            "executed": [], "option_approvals": {}, "selected": [], "outcome": "open"}


async def gather(state: InvState, config) -> dict:
    rt = get_rt()
    async with node(config, "gather", "Gather evidence") as s:
        # let the situation mature briefly: link errors and latency arrive seconds after a CPU halt
        for _ in range(15):
            eps = rt.pipeline.episodes_matching("PATHWAY", 5)
            if any(e["event_number"] in (1007, 1034) for e in eps):
                break
            if rt.sim.status.paused or not rt.sim.status.running:
                break
            await rt.clock.wait(1)
        v = dict(state["vars"])
        sit = rt.pipeline.situation_detail(state["situation_id"]) or {}

        async def telemetry():
            return dict(rt.health.values)

        async def episodes():
            return rt.pipeline.episodes_matching(None, 10)

        hint = TEMPLATE_HINTS.get(sit.get("template", ""), "")

        async def retrieval():
            return rt.kb.search(f"{sit.get('title', '')} {hint}", k=4, types=["playbook", "claim", "operator_message", "concept"])["results"]

        async def similar():
            return rt.kb.search(f"{sit.get('title', '')} {hint}", k=2, types=["incident"])["results"]

        vals, eps, docs, sims = await asyncio.gather(telemetry(), episodes(), retrieval(), similar())
        obs: dict[str, dict] = {}
        st: InvState = dict(state)  # type: ignore
        st["evidence"] = []

        def add(oid, type_, label, source, preview):
            ev, eid = _evidence(st, type_, label, source, preview)
            st["evidence"] = ev
            if oid:
                obs[oid] = {"evidence_id": eid, "label": label}

        sigs = {x["kind"] for x in sit.get("signals", [])}
        if "down_cpu" in v or "cpu_down" in sigs:
            text = next((e["example_text"] for e in eps if e["subsystem"] == "OMF" and e["event_number"] == 103), f"CPU {v.get('down_cpu')} down")
            add("cpu_down", "event", f"CPU {v.get('down_cpu')} down (OMF 103)", "EMS", {"text": text})
        to = [e for e in eps if (e["subsystem"], e["event_number"]) in (("PATHWAY", 1077), ("OMF", 217))]
        if to or "takeover" in sigs:
            add("takeover", "episode", "PATHMON takeover (1077)" if any(e["event_number"] == 1077 for e in to) else "Takeover by backup",
                "PATHWAY 1077 / OMF 217", {"text": to[0]["example_text"] if to else ""})
        link = [e for e in eps if e["subsystem"] == "PATHWAY" and e["event_number"] in (1007, 1034)]
        if link or "link_errors" in sigs:
            n = sum(e["count"] for e in link)
            add("link_errors", "episode", f"1034 link errors ×{n}" if n else "1034 link errors", "PATHWAY 1007/1034",
                {"text": link[0]["example_text"] if link else ""})
        svc = v.get("service", "atm")
        p95, hi = vals.get(f"svc.{svc}.p95_ms"), vals.get(f"svc.{svc}.band_high")
        if (p95 is not None and hi is not None and p95 > hi) or "latency_out_of_band" in sigs:
            add("latency_out_of_band", "metric", f"{v['SERVICE']} p95 {p95:.0f} ms above band", f"telemetry svc.{svc}.p95_ms",
                {"key": f"svc.{svc}.p95_ms", "value": p95, "band_high": hi})
        if any(e["subsystem"] == "OMF" and e["event_number"] == 1204 for e in eps):
            add("audit_over_threshold_event", "event", "Audit trail over threshold (OMF 1204)", "EMS", {})
        if "audit_fill_rising" in sigs:
            add("audit_fill_rising", "metric", "Audit fill rising", "telemetry tmf.mat.fill_pct", {})
        if "audit_fill_high" in sigs:
            add("audit_fill_high", "metric", f"Audit trail {vals.get('tmf.mat.fill_pct', 0):.0f}% full", "telemetry tmf.mat.fill_pct", {})
        if "sc_at_max" in sigs and "sc_queue" in sigs:
            sc_name = v.get("server_class")
            add("sc_at_max_queued", "metric", f"{sc_name} at MAXSERVERS with a queue", f"telemetry sc.{sc_name}.queued", {})
        for d in docs[:2]:
            add(None, "knowledge", d["title"], d["provenance"], {"snippet": d["snippet"], "id": d["id"]})
        for d in sims[:1]:
            add(None, "knowledge", f"Similar: {d['title']}", "incident", {"snippet": d["snippet"], "id": d["id"]})
        ec = card(config, type="evidence", status="info", title="Evidence", incident_id=state["incident_id"],
                  body={"items": st["evidence"]})
        s.summary = f"{len(obs)} observations from telemetry, episodes, retrieval and similar incidents"
        s.evidence_ids = [o["evidence_id"] for o in obs.values()]
        s.tools = ["telemetry", "episodes", "retrieval", "similar_incidents"]
    cards = {**state["cards"], "evidence": ec["id"]}
    return {"obs": obs, "evidence": st["evidence"], "cards": cards}


async def score(state: InvState, config) -> dict:
    rt = get_rt()
    async with node(config, "score", "Score hypotheses") as s:
        hyps = _rescore(state, state["obs"])
        round_ = max(1, state.get("round", 0))
        cards = dict(state["cards"])
        if "hypotheses" not in cards:
            hc = card(config, type="hypotheses", status="info", title="Hypotheses", incident_id=state["incident_id"],
                      body=_hyp_body(rt, state, hyps, round_, None))
            cards["hypotheses"] = hc["id"]
        st = {**state, "cards": cards}
        _publish_hyps(config, st, hyps, round_)
        s.summary = "; ".join(f"{h['label']} {h['p']:.2f}" for h in hyps[:2])
        s.tools = ["diagnosis.score"]
        s.evidence_ids = [o["evidence_id"] for o in state["obs"].values()]
    return {"hyps": hyps, "cards": cards, "round": round_}


async def pick(state: InvState, config) -> dict:
    rt = get_rt()
    async with node(config, "pick", "Pick next checks") as s:
        v = state["vars"]
        budget = rt.diagnosis.budgets.get("checks_per_incident", 6) - len(state.get("checks_run", []))

        def auto_ok(cid: str) -> bool:
            return rt.commands.prepare(cid, _check_params(cid, v), "baton", state["incident_id"]).auto

        batch = rt.diagnosis.next_checks(state["hyps"], set(state.get("checks_run", [])), v.get("peak_day", False), auto_ok,
                                         k=min(3, max(0, budget)))
        items = [{"catalog_id": c["catalog_id"], "params": _check_params(c["catalog_id"], v), "reason": c["reason"],
                  "hypothesis_id": c.get("hypothesis_id"), "claim_id": c.get("claim_id"), "rule_out": c.get("rule_out", False),
                  "value": c["value"], "status": "proposed"} for c in batch]
        s.summary = ", ".join(i["catalog_id"] for i in items) or "No useful checks left"
        s.tools = ["diagnosis.next_checks"]
    return {"batch": items}


def after_pick(state: InvState) -> str:
    return "policy" if state.get("batch") else "enough"


async def check_policy(state: InvState, config) -> dict:
    rt = get_rt()
    c = ctx(config)
    batch = []
    async with node(config, "check_policy", "Check policy") as s:
        v = state["vars"]
        for item in state["batch"]:
            p = rt.commands.prepare(item["catalog_id"], item["params"], "baton", state["incident_id"])
            purpose, expected, why = _check_texts(item["catalog_id"], v, item)
            body = command_body(p, purpose=purpose, why_now=why, expected=expected)
            title = p.entry.title + (f" {p.validation.target}" if p.validation.target and p.validation.target not in p.entry.title else "")
            if p.entry.internal:
                title = f"Baton check: {p.entry.title}"
            cites = _cmd_citations(rt, item["catalog_id"])
            if item.get("claim_id") and f"claim:{item['claim_id']}" in rt.kb.records:
                cites.append(rt.kb.citation(f"claim:{item['claim_id']}"))
            if p.denied:
                status, actions = "blocked", []
            elif p.auto:
                status, actions = "auto_running", []
            else:
                status, actions = "awaiting_approval", ["approve", "edit", "reject"]
            cd = card(config, type="command", status=status, title=title, incident_id=state["incident_id"], body=body,
                      actions=actions, citations=[x for x in cites if x])
            rec = {**item, "step_id": p.step_id, "card_id": cd["id"], "status": status, "auto": p.auto, "approval_id": None}
            if status == "awaiting_approval":
                a = rt.approvals.create(kind="command", thread_id=c["thread_id"], incident_id=state["incident_id"], card_id=cd["id"],
                                        steps=[p.step_dict()], tier=p.validation.tier, policy=p.policy, requested_by="baton",
                                        graph_key=c["graph_key"])
                patch(cd["id"], body={"approval_id": a["id"], "approval_progress": a["progress_text"]})
                rec["approval_id"] = a["id"]
                rt.incidents.timeline(state["incident_id"], "approval_requested", rt.users.actor_ref("baton"),
                                      f"Needs approval: {p.validation.rendered}", p.policy["explanation"],
                                      {"type": "approval", "id": a["id"]})
            batch.append(rec)
        s.summary = "; ".join(f"{b['catalog_id']}: {'auto' if b['auto'] else b['status']}" for b in batch)
        s.tools = ["policy", "ledger"]
    return {"batch": batch}


async def _run_check(state: InvState, config, item: dict, approval: dict | None, live: dict) -> dict:
    """Execute one check, update its card, re-score into `live` (shared across parallel checks)."""
    rt = get_rt()
    c = ctx(config)
    p = rt.commands.prepare(item["catalog_id"], item["params"], "baton", state["incident_id"], step_id=item["step_id"])
    approved_by = rt.approvals.approvers(approval) if approval else []
    patch(item["card_id"], status="running", actions=[], body={"approvers": [rt.users.name(a) for a in approved_by]})
    try:
        ex = await rt.commands.run(p, actor="baton" if approval is None else approved_by[0], approved_by=approved_by,
                                   auto=approval is None, approval_id=approval["id"] if approval else None,
                                   thread_id=c["thread_id"], incident_id=state["incident_id"])
    except Exception as e:
        patch(item["card_id"], status="failed", body={"validation_errors": [str(e)]})
        return {**item, "status": "failed"}
    facts = ex.get("facts") or {}
    summary = interpret_template(rt, item["catalog_id"], facts)
    patch(item["card_id"], status="done" if ex["status"] == "done" else "failed",
          body={"execution": execution_block(rt, ex, summary, "fallback")})
    new_obs, upd = observations_from_facts(rt, item["catalog_id"], facts, {**state["vars"], **live["vars"]})
    live["vars"].update(upd)
    for oid, label in new_obs.items():
        ev, eid = _evidence({"evidence": live["evidence"]}, "output_fact", label, item["catalog_id"], {"facts": facts})
        live["evidence"] = ev
        live["obs"][oid] = {"evidence_id": eid, "label": label}
    st = {**state, "obs": live["obs"], "vars": {**state["vars"], **live["vars"]}, "hyps": live["hyps"]}
    hyps = _rescore(st, live["obs"])
    live["hyps"] = hyps
    _publish_hyps(config, {**state, "cards": state["cards"]}, hyps, state.get("round", 1))
    patch(state["cards"]["evidence"], body={"items": live["evidence"]})
    return {**item, "status": ex["status"], "exec_id": ex["id"]}


async def run_checks(state: InvState, config) -> dict:
    async with node(config, "run_checks", "Run checks") as s:
        live = {"obs": dict(state["obs"]), "evidence": list(state["evidence"]), "vars": {}, "hyps": state["hyps"]}
        batch = list(state["batch"])
        idx = [i for i, b in enumerate(batch) if b["status"] == "auto_running"]
        results = await asyncio.gather(*[_run_check(state, config, batch[i], None, live) for i in idx])
        for i, r in zip(idx, results):
            batch[i] = r
        s.summary = f"Auto-ran {len(idx)} check(s)" + (f"; {sum(1 for b in batch if b['status'] == 'awaiting_approval')} waiting"
                                                         if any(b["status"] == "awaiting_approval" for b in batch) else "")
        s.tools = [batch[i]["catalog_id"] for i in idx]
    return {"batch": batch, "obs": live["obs"], "evidence": live["evidence"], "vars": {**state["vars"], **live["vars"]},
            "hyps": live["hyps"], "checks_run": state.get("checks_run", []) + [batch[i]["catalog_id"] for i in idx]}


def checks_pending(state: InvState) -> str:
    return "wait_checks" if any(b["status"] == "awaiting_approval" for b in state["batch"]) else "read_results"


async def wait_checks(state: InvState, config) -> dict:
    item = next(b for b in state["batch"] if b["status"] == "awaiting_approval")
    async with node(config, "wait_checks", "Wait for approval", step_id=f"stp_wait_{item['approval_id']}") as s:
        s.summary = f"Waiting: {item['catalog_id']} needs approval"
        resp = wait_for_approval(item["approval_id"], f"Approve {item['catalog_id']}?")
        s.summary = f"{item['catalog_id']}: {resp['status']}"
    return {"current_wait": item["approval_id"]}


async def run_approved_check(state: InvState, config) -> dict:
    rt = get_rt()
    batch = list(state["batch"])
    i = next(i for i, b in enumerate(batch) if b.get("approval_id") == state["current_wait"])
    a = rt.approvals.get(state["current_wait"])
    async with node(config, "run_checks", "Run checks") as s:
        live = {"obs": dict(state["obs"]), "evidence": list(state["evidence"]), "vars": {}, "hyps": state["hyps"]}
        if a["status"] == "approved":
            batch[i] = await _run_check(state, config, batch[i], a, live)
            s.summary = f"Ran {batch[i]['catalog_id']}"
        else:
            batch[i] = {**batch[i], "status": a["status"]}
            patch(batch[i]["card_id"], status="rejected" if a["status"] == "rejected" else "expired", actions=[])
            s.summary = f"{batch[i]['catalog_id']} {a['status']}"
    return {"batch": batch, "obs": live["obs"], "evidence": live["evidence"], "vars": {**state["vars"], **live["vars"]},
            "hyps": live["hyps"], "checks_run": state.get("checks_run", []) + [batch[i]["catalog_id"]], "current_wait": None}


async def read_results(state: InvState, config) -> dict:
    rt = get_rt()
    c = ctx(config)
    async with node(config, "read_results", "Read the results") as s:
        hyps = _rescore(state, state["obs"])
        lead, rest = hyps[0], hyps[1]
        fors = ", ".join(f["label"] for f in lead["for"][:2]) or "the situation"
        againsts = ", ".join(a["label"] for a in rest["against"][:1]) or "weaker evidence"
        fallback = f"Leading: {lead['label']} ({lead['p']:.2f}) because {fors}; ruled down: {rest['label']} because {againsts}."
        # Publish the template narrative now; the model narrative replaces it when it arrives, so a slow model
        # never delays the expert card and the decision.
        _publish_hyps(config, state, hyps, state.get("round", 1), narrative=fallback, nsrc="fallback")
        prompt = P.render("diagnostician", situation=state["vars"],
                          hypotheses=[{k: h[k] for k in ("label", "p", "for", "against")} for h in hyps[:4]],
                          evidence=[{"id": e["id"], "label": e["label"]} for e in state["evidence"]])
        rt.spawn(_narrate_later(rt, state["cards"].get("hypotheses"), prompt, c["run_id"]))
        s.model = "fallback"
        s.summary = fallback[:160] + (" (model narrative to follow)" if rt.gateway.live or rt.gateway.mode == "replay" else "")
    return {"hyps": hyps}


async def _narrate_later(rt, card_id: str | None, prompt: str, run_id: str) -> None:
    if not card_id:
        return
    out, src, _ = await rt.gateway.complete("diagnostician", P.SYSTEM, prompt, P.DiagnosticianOut, run_id=run_id, node="narrate")
    if out:
        patch(card_id, body={"narrative": out["narrative"], "narrative_source": src})


async def enough(state: InvState, config) -> dict:
    rt = get_rt()
    async with node(config, "enough", "Enough evidence?") as s:
        stop = rt.diagnosis.stop_rule(state["hyps"], state.get("round", 1))
        _publish_hyps(config, state, state["hyps"], state.get("round", 1), stop)
        s.summary = ("yes: " if stop["met"] else "no: ") + stop["reason"]
        out_of_evidence = (stop["exhausted"] or not state.get("batch")
                           or len(state.get("checks_run", [])) >= rt.diagnosis.budgets.get("checks_per_incident", 6)
                           or state.get("round", 1) >= rt.diagnosis.stop["max_rounds"])
        if not stop["met"] and out_of_evidence:
            stop["out_of_evidence"] = True
            # A clear leader below the bar: continue to options, but say plainly that Baton is not certain.
            if stop["top"] >= 0.6 and stop["margin"] >= 0.3:
                stop["proceed"] = True
                lead = state["hyps"][0]
                card(config, type="text", status="info", title="Baton is not certain", incident_id=state["incident_id"],
                     body={"markdown": f"No more useful checks. The leading explanation is **{lead['label']}** at "
                                       f"{lead['p']:.2f}, below the 0.85 Baton normally requires. Options follow for that "
                                       "explanation; ask the on-call expert (Dave) to confirm before acting."})
                s.summary += f" (out of checks; continuing with the leader at {lead['p']:.2f}, flagged as uncertain)"
            else:
                s.summary += " (out of checks: escalate)"
    rounds = state.get("round", 1) + (0 if stop["met"] else 1)
    return {"stop": stop, "round": rounds}


def after_enough(state: InvState) -> str:
    stop = state["stop"]
    if stop["met"] or stop.get("proceed"):
        return "expert"
    if stop.get("out_of_evidence"):
        return "escalate"
    return "pick"


async def escalate(state: InvState, config) -> dict:
    rt = get_rt()
    async with node(config, "escalate", "Close incident") as s:
        lead = state["hyps"][0]
        summary = (f"After {state.get('round', 1)} rounds Baton is not sure. Leading: {lead['label']} ({lead['p']:.2f}). "
                   f"Evidence: " + "; ".join(e["label"] for e in state["evidence"][:5]))
        card(config, type="escalation", status="info", title="Escalate: not enough evidence", incident_id=state["incident_id"],
             body={"reason": "Stop rule not met after 3 rounds", "contact": "On-call expert Dave", "summary": summary,
                   "evidence_pack": [e["id"] for e in state["evidence"]]}, actions=["copy_summary"])
        rt.incidents.timeline(state["incident_id"], "note", rt.users.actor_ref("baton"), "Escalated to on-call expert", summary)
        s.summary = "Escalated with a summary"
    return {"outcome": "escalated"}


async def expert(state: InvState, config) -> dict:
    rt = get_rt()
    async with node(config, "expert", "Find expert knowledge") as s:
        sit = rt.pipeline.situation_detail(state["situation_id"]) or {}
        mode = rt.diagnosis.modes[state["hyps"][0]["id"]]
        comps = sit.get("components", []) + [f"sc:{state['vars'].get('server_class')}"]
        if state["vars"].get("hottest_cpu") is not None:
            b = _batch_on_cpu(rt, state["vars"]["hottest_cpu"])
            if b:
                comps.append(f"proc:{b}")
        body = build_expert_card(rt.kb, rt.claims, rt.users, sit, mode, comps)
        if body:
            vb = " and ".join(x["name"] for x in body["verified_by"]) or "nobody yet"
            title = f"{body['title']}: {body['author']['name']}'s {body['kind']}, verified by {vb}, v{body['version']}"
            cites = []
            if body["kind"] == "playbook":
                cites.append(rt.kb.citation(f"playbook:{body['id']}"))
            cites += [rt.kb.citation(f"claim:{cid}") for cid in body["claim_ids"]]
            ec = card(config, type="expert", status="info", title=title, incident_id=state["incident_id"], body=body,
                      citations=[c for c in cites if c])
            rt.incidents.timeline(state["incident_id"], "note", rt.users.actor_ref("baton"), f"Expert knowledge: {title}", body["tip"],
                                  {"type": "card", "id": ec["id"]})
            s.summary = title
            s.evidence_ids = [body["id"], *body["claim_ids"]]
        else:
            s.summary = "No verified playbook or claim for this situation"
        s.tools = ["retrieval", "expert_card"]
    return {"expert": body}


def _batch_on_cpu(rt, cpu: int) -> str | None:
    m = rt.sim.model
    for p in m.processes.values():
        if p.is_batch and p.cpu == cpu and m.batch_active(p):
            return p.name
    return None


def _resolve_params(rt, params: dict, v: dict) -> dict:
    """Resolve placeholders such as $batch_on_hottest_cpu; literal values (e.g. "$STMT1", 100) pass through."""
    out = {}
    for k, val in params.items():
        if val == "$batch_on_hottest_cpu":
            out[k] = _batch_on_cpu(rt, v.get("hottest_cpu", 5))   # None when no batch runs there: option skipped
        elif val == "$affected_critical_class":
            out[k] = v.get("server_class", "ATM-AUTH")
        elif val == "$current_running + 8":
            out[k] = int(v.get("current_running") or v.get("running_before", 20)) + 8
        elif val == "$down_cpu":
            out[k] = v.get("down_cpu", 3)
        elif val == "$restore_maxservers":
            cls = v.get("server_class", "ATM-AUTH")
            out[k] = next(s["maxservers"] for s in rt.sim.site["server_classes"] if s["name"] == cls)
        elif val == "$current_max":
            out[k] = int(v.get("current_max") or 0)
        elif val == "$audit_heavy_batch":
            out[k] = "$MEB01"
        elif val == "$hot_process":
            out[k] = v.get("hot_process") or "$RPT2"
        else:
            out[k] = val
    return out


def _predict_cpus(rt, cls: str, n: int) -> list[int]:
    try:
        m = copy.deepcopy(rt.sim.model)
        return sorted(set(m.set_numstatic(cls, n)["started_on"]))
    except Exception:
        return []


def _claim_risk(rt, catalog_id: str, params: dict) -> tuple[str | None, dict | None]:
    for c in rt.store.all("claims", "status = ?", ("verified",)):
        rec = (c.get("structured") or {}).get("recommendation") or {}
        if isinstance(rec, dict) and rec.get("catalog_id") == catalog_id and rec.get("params", {}) == params:
            st = c["statement"]
            m = re.search(r"resume (?:it )?(?:with ACTIVATE )?after (\d\d:\d\d)", st)
            d = re.search(r"due by (\d\d:\d\d)", (c.get("structured") or {}).get("rationale", ""))
            if m:
                tail = f"resume after {m.group(1)}" + (f" to meet the {d.group(1)} deadline" if d else "")
                return f"{tail} ({c['id']})", c
            return None, c
    return None, None


async def build_options(state: InvState, config) -> dict:
    rt = get_rt()
    c = ctx(config)
    async with node(config, "options", "Build options") as s:
        v = state["vars"]
        mode_id = state["hyps"][0]["id"]
        mode = rt.diagnosis.modes[mode_id]
        playbook = (state.get("expert") or {}) if (state.get("expert") or {}).get("kind") == "playbook" else None
        pb_rec = rt.kb.records.get(f"playbook:{playbook['id']}", {}).get("record") if playbook else None
        options = []
        letters = iter("abcdefgh")
        by_name = {}
        for mit in mode.get("mitigations", []):
            letter = next(letters)
            oid = f"opt_{letter}"
            if mit.get("escalate"):
                options.append({"id": oid, "label": mit["label"].format(**v), "steps": [], "tier": None, "blocked": False,
                                "escalation": mit["escalate"], "expected_effect": None, "risks": None, "recommended": False,
                                "status": "available", "benefit": mit.get("benefit", 1)})
                by_name[mit["option"]] = oid
                continue
            steps, tier_rank, label_vars, risks, rec = [], 0, dict(v), [], None
            blocked, block_reason, escalation = False, None, None
            pb_expected = None
            resolved = [_resolve_params(rt, stp["params"], v) for stp in mit["steps"]]
            if any(x is None for prm in resolved for x in prm.values()):
                continue          # e.g. no batch is running on the hottest CPU: this option does not apply
            for stp, params in zip(mit["steps"], resolved):
                p = rt.commands.prepare(stp["catalog_id"], params, "baton", state["incident_id"])
                val = p.validation
                steps.append({"catalog_id": stp["catalog_id"], "params": val.params, "rendered": val.rendered or p.entry.title,
                              "tier": val.tier, "undo": val.undo_rendered})
                tier_rank = max(tier_rank, int(val.tier[1]))
                label_vars.update({k: val.params.get(k) for k in val.params})
                label_vars.update(process=val.params.get("process"), cpu=v.get("hottest_cpu"), n=val.params.get("n"),
                                  current=v.get("current_numstatic") or v.get("current_running"),
                                  current_max=v.get("current_max"), server_class=val.params.get("server_class", v.get("server_class")))
                if p.policy["effect"] == "deny":
                    blocked, block_reason, escalation = True, p.policy["explanation"], p.policy.get("escalation") or p.entry.escalation
                risk = p.entry.risks
                if stp["catalog_id"] == "tacl.suspend_process":
                    risk = "Statements wait until ACTIVATE" if val.params.get("process") == "$STMT1" else f"{val.params.get('process')} work waits until ACTIVATE"
                if stp["catalog_id"] == "pathcom.alter_numstatic":
                    cpus = _predict_cpus(rt, val.params["server_class"], int(val.params["n"]))
                    mx = rt.sim.model.classes[val.params["server_class"]].maxservers
                    risk = (f"Adds load on CPUs {' and '.join(map(str, cpus))}; " if cpus else "Adds CPU load where the new servers land; ") + \
                           f"must stay at or below MAXSERVERS {mx} (PATHWAY 2049)"
                if stp["catalog_id"] == "pathcom.alter_maxservers":
                    risk = "More servers add CPU and disk load; never above 40 on ATM-AUTH (C-004)"
                claim_tail, claim = _claim_risk(rt, stp["catalog_id"], val.params)
                if claim_tail:
                    risk += f"; {claim_tail}"
                risks.append(risk)
                # recommender: the playbook when it names this exact action, else a verified claim, else the library
                pb_step = next((x for x in (pb_rec or {}).get("steps", []) if x.get("kind") == "action"
                                and x.get("catalog_id") == stp["catalog_id"]), None)
                if pb_step and pb_step.get("expected_effect"):
                    pb_expected = pb_step["expected_effect"]
                if pb_step and all(not str(x).startswith("+") for x in (pb_step.get("params") or {}).values()):
                    rec = {"kind": "playbook", "id": pb_rec["id"], "author": rt.users.name(pb_rec["author"]),
                           "verified_by": [rt.users.name(x["user"]) for x in pb_rec.get("verified_by", [])]}
                elif claim:
                    rec = {"kind": "claim", "id": claim["id"], "author": rt.users.name(claim["author"]),
                           "verified_by": [rt.users.name(r["user"]) for r in claim.get("reviews", []) if r.get("decision") != "reject"]}
                else:
                    rec = {"kind": "library", "id": mode_id, "author": None, "verified_by": []}
            tier = f"T{tier_rank}"
            expected = pb_expected or (mit.get("expected_effect") or "").format(**{**label_vars, "cpu": v.get("hottest_cpu"),
                                                                                 "SERVICE": v.get("SERVICE")})
            label = _fmt(mit["label"], label_vars)
            proc = label_vars.get("process")
            if mit["option"] == "suspend_batch_on_hottest_cpu" and proc in rt.sim.model.processes:
                desc = rt.sim.model.processes[proc].description or "batch"
                label = f"Suspend the {desc[0].lower() + desc[1:]} {proc}"
            opt = {"id": oid, "label": label,
                   "steps": steps, "tier": tier, "required_approvers": 2 if tier == "T2" else 1 if tier == "T1" else None,
                   "recommender": rec, "expected_effect": expected if not blocked else None, "risks": "; ".join(risks) if not blocked else None,
                   "prediction": None, "recommended": False, "blocked": blocked, "block_reason": block_reason,
                   "escalation": escalation, "includes": [], "status": "blocked" if blocked else "available",
                   "benefit": mit.get("benefit", 1)}
            if blocked:
                opt["required_approvers"] = None
            options.append(opt)
            by_name[mit["option"]] = oid
        combo = [by_name[n] for n in mode.get("combine", []) if n in by_name]
        if len(combo) >= 2:
            parts = [o for o in options if o["id"] in combo]
            if all(not o["blocked"] for o in parts):
                letters_ = " then ".join(o["id"].split("_")[1].upper() for o in parts)
                options.append({"id": "opt_" + "".join(o["id"].split("_")[1] for o in parts), "label": letters_,
                                "steps": [], "tier": max((o["tier"] for o in parts), key=lambda t: int(t[1])),
                                "required_approvers": max(o["required_approvers"] or 1 for o in parts),
                                "recommender": None, "expected_effect": _combined_effect(v), "risks": "Combined risks of " +
                                " and ".join(o["id"].split("_")[1].upper() for o in parts), "prediction": None,
                                "recommended": False, "blocked": False, "block_reason": None, "escalation": None,
                                "includes": combo, "status": "available", "benefit": sum(o["benefit"] for o in parts)})
        # customers affected? (latency above band or requests queuing) — if not, changing things is not worth the risk
        vals = rt.health.values
        impacted = ("latency_out_of_band" in state["obs"] or "sc_at_max_queued" in state["obs"]
                    or vals.get(f"sc.{v.get('server_class', 'ATM-AUTH')}.queued", 0) > 0
                    or (vals.get(f"svc.{v.get('service', 'atm')}.p95_ms", 0) > vals.get(f"svc.{v.get('service', 'atm')}.band_high", 1e9)))
        cands = [o for o in options if not o["blocked"] and o.get("tier") and int(o["tier"][1]) <= 2]
        if cands and impacted:
            best = max(cands, key=lambda o: (o["benefit"], -int(o["tier"][1])))
            best["recommended"] = True
        dn = mode.get("do_nothing") or {}
        dn_effect, dn_risk = dn.get("expected_effect"), dn.get("risks")
        if not impacted:
            where = f"CPU {v['down_cpu']}" if v.get("down_cpu") is not None else "the failed part"
            dn_effect = f"No customer impact now: {v.get('SERVICE', 'ATM')} is inside its normal band. Keep watching; call HPE hardware support about {where}."
            dn_risk = "Capacity stays reduced until the repair; another failure would reach customers (see N-1)"
        options.append({"id": "opt_none", "label": "Do nothing", "steps": [], "tier": None, "required_approvers": None,
                        "recommender": None, "expected_effect": dn_effect, "risks": dn_risk,
                        "prediction": None, "recommended": not impacted, "blocked": False, "block_reason": None,
                        "escalation": None, "includes": [], "status": "available", "benefit": 0})
        await _attach_predictions(rt, options, v.get("service", "atm"))
        for o in options:
            o.pop("benefit", None)
        policy = {"effect": "require_approval", "required_approvers": 1, "required_roles": ["operator", "senior", "expert"],
                  "at_least_one_of": [], "rule_ids": ["decision"],
                  "explanation": "Choose the options to approve; each selected option then gets its own approval"}
        dc = card(config, type="decision", status="proposed", title="Options", incident_id=state["incident_id"],
                  body={"approval_id": None, "options": options, "selected": []}, actions=["approve_selected"],
                  citations=[x for x in [rt.kb.citation(f"playbook:{(state.get('expert') or {}).get('id')}")] if x])
        a = rt.approvals.create(kind="decision", thread_id=c["thread_id"], incident_id=state["incident_id"], card_id=dc["id"],
                                steps=[{"step_id": f"stp_decision_{dc['id'][5:]}", "rendered": "Choose options"}], tier="T1",
                                policy=policy, requested_by="baton", graph_key=c["graph_key"],
                                extra={"options": options})
        patch(dc["id"], body={"approval_id": a["id"]})
        rt.store.kv_set(f"incident_state:{state['incident_id']}", {**rt.store.kv_get(f"incident_state:{state['incident_id']}", {}),
                                                                 "options": options})
        rt.incidents.timeline(state["incident_id"], "approval_requested", rt.users.actor_ref("baton"), "Options ready for a decision",
                              ", ".join(o["label"] for o in options), {"type": "card", "id": dc["id"]})
        s.summary = "; ".join(f"{o['label']}{' (recommended)' if o['recommended'] else ''}" for o in options)
        s.tools = ["failure_modes", "playbooks", "claims"]
    return {"options": options, "decision_approval_id": a["id"], "cards": {**state["cards"], "decision": dc["id"]}}


async def _attach_predictions(rt, options: list[dict], service: str) -> None:
    """P1 what-if: 600 sim-second prediction per option (and for doing nothing) from a simulator fork."""
    from ...ops import predict_async
    jobs = []
    for o in options:
        if o.get("blocked"):
            continue
        if o["id"] == "opt_none":
            acts = []
        elif o.get("includes"):
            acts = [st for x in options if x["id"] in o["includes"] for st in x.get("steps", [])]
        elif o.get("steps"):
            acts = o["steps"]
        else:
            continue
        jobs.append((o, [{"catalog_id": st["catalog_id"], "params": st["params"]} for st in acts]))
    try:
        results = await asyncio.gather(*[predict_async(rt, acts, service) for _, acts in jobs], return_exceptions=True)
    except Exception:
        return
    for (o, _), res in zip(jobs, results):
        if isinstance(res, dict):
            o["prediction"] = res


def _fmt(template: str, values: dict) -> str:
    class Safe(dict):
        def __missing__(self, key):
            return "?"
    return template.format_map(Safe({k: x for k, x in values.items() if x is not None}))


def _combined_effect(v: dict) -> str:
    return f"CPU {v.get('hottest_cpu', 5)} near 80% and {v.get('SERVICE', 'ATM')} p95 back in band within about 2 minutes"


async def wait_decision(state: InvState, config) -> dict:
    async with node(config, "wait_decision", "Wait for approval", step_id=f"stp_wait_{state['decision_approval_id']}") as s:
        s.summary = "Waiting for a decision"
        resp = wait_for_approval(state["decision_approval_id"], "Choose the options to approve")
        s.summary = f"Decision {resp['status']}"
    rt = get_rt()
    a = rt.approvals.get(state["decision_approval_id"])
    sel = (a.get("extra") or {}).get("selected", [])
    return {"selected": sel if a["status"] == "approved" else [], "option_approvals": (a.get("extra") or {}).get("option_approvals", {}),
            "decided_by": (a["decisions"][-1]["actor"] if a["decisions"] else None)}


def after_decision(state: InvState) -> str:
    return "act" if state.get("selected") else "close"


def _update_option_status(state: InvState, oid: str, status: str) -> None:
    rt = get_rt()
    cid = state["cards"].get("decision")
    cd = rt.agents.cards.get(cid) if cid else None
    if not cd:
        return
    opts = cd["body"]["options"]
    for o in opts:
        if o["id"] == oid:
            o["status"] = status
    patch(cid, body={"options": opts})


async def act(state: InvState, config) -> dict:
    rt = get_rt()
    c = ctx(config)
    executed = list(state.get("executed", []))
    async with node(config, "act", "Act") as s:
        notes = []
        for oid in state["selected"]:
            if oid in executed:
                continue
            apr_id = state["option_approvals"].get(oid)
            a = rt.approvals.get(apr_id)
            if a["status"] in ("pending", "partially_approved"):
                break                       # one step at a time: wait for this option before the next
            if a["status"] != "approved":
                _update_option_status(state, oid, "rejected")
                executed.append(oid)
                notes.append(f"{oid} {a['status']}")
                continue
            opt = next(o for o in state["options"] if o["id"] == oid)
            approvers = rt.approvals.approvers(a)
            for stp in opt["steps"]:
                p = rt.commands.prepare(stp["catalog_id"], stp["params"], approvers[0], state["incident_id"])
                if not p.validation.valid or p.denied:
                    notes.append(f"{stp['rendered']} refused: {p.policy['explanation']}")
                    _update_option_status(state, oid, "rejected")
                    continue
                cd = card(config, type="command", status="running", title=f"Act: {opt['label']}", incident_id=state["incident_id"],
                          body={**command_body(p, purpose=opt["label"], expected=opt.get("expected_effect")),
                                "approval_id": apr_id, "approval_progress": a["progress_text"],
                                "approvers": [rt.users.name(x) for x in approvers]},
                          actions=[], citations=_cmd_citations(rt, stp["catalog_id"]))
                ex = await rt.commands.run(p, actor=approvers[0], approved_by=approvers, auto=False, approval_id=apr_id,
                                           thread_id=c["thread_id"], incident_id=state["incident_id"])
                summary = interpret_template(rt, stp["catalog_id"], ex.get("facts") or {})
                patch(cd["id"], status="done" if ex["status"] == "done" else "failed", actions=["undo"] if ex.get("undo_entry_id") else [],
                      body={"execution": execution_block(rt, ex, summary, "fallback")})
                notes.append(f"{stp['rendered']} ({' and '.join(rt.users.name(x) for x in approvers)})")
            _update_option_status(state, oid, "executed")
            executed.append(oid)
        inc = rt.incidents.get(state["incident_id"])
        if inc and inc["status"] == "open" and executed:
            rt.incidents.set_status(state["incident_id"], "mitigating", rt.users.actor_ref("baton"), "Mitigation actions running")
        s.summary = "; ".join(notes) or "Waiting for approvals"
        s.tools = [st["catalog_id"] for o in state["options"] if o["id"] in executed for st in o["steps"]]
    return {"executed": executed}


def after_act(state: InvState) -> str:
    rt = get_rt()
    for oid in state["selected"]:
        if oid not in state.get("executed", []):
            a = rt.approvals.get(state["option_approvals"][oid])
            if a["status"] in ("pending", "partially_approved"):
                return "act_wait"
            return "act"
    return "verify"


async def act_wait(state: InvState, config) -> dict:
    oid = next(o for o in state["selected"] if o not in state.get("executed", []))
    apr = state["option_approvals"][oid]
    async with node(config, "act_wait", "Wait for approval", step_id=f"stp_wait_{apr}") as s:
        rt = get_rt()
        a = rt.approvals.get(apr)
        s.summary = a["progress_text"]
        _update_option_status(state, oid, a["status"] if a["status"] in ("partially_approved", "awaiting_approval") else "awaiting_approval")
        resp = wait_for_approval(apr, f"Approve option {oid}?")
        s.summary = f"Option {oid}: {resp['status']}"
    return {}


def _criteria(rt, mode: dict, v: dict) -> list[dict]:
    out = []
    for cr in mode.get("verification", []):
        fmt = {**v, "SERVICE": v.get("SERVICE", "ATM"), "service": v.get("service", "atm"), "server_class": v.get("server_class", "ATM-AUTH")}
        out.append({**cr, "metric": cr["metric"].format(**fmt), "ref": cr.get("ref", "").format(**fmt) if cr.get("ref") else None,
                    "text": cr["text"].format(**fmt)})
    return out


def _value(rt, metric: str) -> float | None:
    vals = rt.health.values
    if metric == "max_cpu_busy":
        return max((vals[k] for k in vals if k.startswith("cpu.") and k.endswith(".busy")), default=None)
    if metric == "tmf_fill_trend":
        return rt.pipeline.fill_trend()
    return vals.get(metric)


def _met(rt, cr: dict) -> tuple[bool, str]:
    val = _value(rt, cr["metric"])
    ref = rt.health.values.get(cr["ref"]) if cr.get("ref") else cr.get("value")
    if val is None or ref is None:
        return False, "n/a"
    ok = val <= ref if cr["op"] == "<=" else val < ref
    if cr["metric"] == "max_cpu_busy":
        hot = max((k for k in rt.health.values if k.startswith("cpu.") and k.endswith(".busy")), key=lambda k: rt.health.values[k])
        return ok, f"CPU {hot.split('.')[1]} at {val:.0f}%"
    if cr.get("ref"):
        lo = rt.health.values.get(cr["ref"].replace("band_high", "band_low"))
        if lo is not None and val < lo:
            return ok, f"{val:.0f} ms, below the band ({lo:.0f}–{ref:.0f}): more servers than a normal peak"
        return ok, f"{val:.0f} ms (band {lo:.0f}–{ref:.0f})" if lo is not None else f"{val:.0f} (limit {ref:.0f})"
    return ok, f"{val:.1f}"


async def verify(state: InvState, config) -> dict:
    rt = get_rt()
    async with node(config, "verify", "Verify recovery") as s:
        prof = rt.sim.profile_cfg
        if prof.get("after_actions_speed"):
            rt.set_speed(int(prof["after_actions_speed"]))
        rt.incidents.set_status(state["incident_id"], "verifying", rt.users.actor_ref("baton"), "Watching recovery")
        mode = rt.diagnosis.modes[state["hyps"][0]["id"]]
        crits = _criteria(rt, mode, state["vars"])
        window = max([c.get("for_s", 0) for c in crits] or [60]) or 60
        start = iso_sim(rt.sim.now)
        vc = card(config, type="verification", status="running", title="Verifying recovery", incident_id=state["incident_id"],
                  body={"failure_mode": mode["id"], "criteria": [{"text": c["text"], "met": False, "value": None} for c in crits],
                        "window_s": window, "window_start_sim_ts": start, "window_end_sim_ts": None, "result": "pending",
                        "summary": f"Watching for {window} sim-seconds"})
        ok_since = None
        waited = 0
        key = crits[0]["metric"] if crits else None
        base = _value(rt, key) if key else None
        regression = False
        result = "not_recovered"
        rows = []
        while waited < VERIFY_TIMEOUT_S:
            await rt.clock.wait(1)
            waited += 1
            rows = []
            all_ok = True
            for cr in crits:
                ok, shown = _met(rt, cr)
                rows.append({"text": cr["text"], "met": ok, "value": shown})
                all_ok = all_ok and ok
            if key and base and waited <= 60:
                cur = _value(rt, key)
                if cur is not None and cur > base * 1.2 and "p95" in key and waited > 20:
                    regression = True
            if all_ok:
                ok_since = ok_since if ok_since is not None else waited
                if waited - ok_since >= window:
                    result = "recovered"
                    break
            else:
                ok_since = None
            if waited % 5 == 0:
                patch(vc["id"], body={"criteria": rows, "summary": f"{'In band' if all_ok else 'Not yet'} · {waited} s"})
        end = iso_sim(rt.sim.now)
        undo_ids = [u["id"] for u in (rt.incidents.get(state["incident_id"]) or {}).get("undo_stack", []) if u["status"] == "pending"]
        if result == "recovered":
            svc = state["vars"].get("SERVICE", "ATM")
            title = f"Recovered: {svc} p95 in band for {window} s" if mode["id"] == "cpu_capacity_loss" else f"Recovered: {crits[0]['text'] if crits else ''}"
            patch(vc["id"], status="resolved", title=title, body={"criteria": rows, "window_end_sim_ts": end, "result": "recovered",
                                                                  "summary": title})
        else:
            title = "Not recovered: propose undo" if regression else "Not recovered yet"
            patch(vc["id"], status="failed", title=title, actions=["propose_undo"] if undo_ids else [],
                  body={"criteria": rows, "window_end_sim_ts": end, "result": "regression" if regression else "not_recovered",
                        "summary": title, "propose_undo": undo_ids})
        for o in state["options"]:
            if o["id"] in state.get("executed", []):
                for stp in o["steps"]:
                    p = rt.commands.prepare(stp["catalog_id"], stp["params"], "baton")
                    rt.ledger.record_verification(stp["catalog_id"], p.validation.param_class, "operator", result == "recovered")
        rt.incidents.timeline(state["incident_id"], "verification", rt.users.actor_ref("baton"), title, "; ".join(
            f"{'✓' if r['met'] else '✗'} {r['text']} ({r['value']})" for r in rows), {"type": "card", "id": vc["id"]})
        s.summary = title
    ver = {"result": result, "criteria": rows, "window_s": window, "start": start, "end": end, "title": title}
    rt.store.kv_set(f"incident_state:{state['incident_id']}", {**rt.store.kv_get(f"incident_state:{state['incident_id']}", {}),
                                                             "verification": ver})
    return {"verification": ver, "outcome": result}


def after_verify(state: InvState) -> str:
    return "close" if state.get("outcome") == "recovered" else "end"


async def close(state: InvState, config) -> dict:
    rt = get_rt()
    async with node(config, "close", "Close incident") as s:
        if state.get("outcome") == "recovered":
            rt.incidents.set_status(state["incident_id"], "resolved", rt.users.actor_ref("baton"), "Verified recovery")
            rt.audit.append("agent", "baton", "incident.resolve", state["incident_id"], {"verification": state["verification"]["title"]},
                            incident_id=state["incident_id"])
            s.summary = "Incident resolved"
        else:
            s.summary = "Decision: no action; incident stays open until the underlying fault is repaired"
            card(config, type="text", status="info", title="No action taken", incident_id=state["incident_id"],
                 body={"markdown": "The decision was to change nothing. The incident stays open until the underlying fault is "
                                   "repaired; Baton keeps watching the health board and will open a new situation if "
                                   "customers are affected."})
    return {}


async def learn(state: InvState, config) -> dict:
    rt = get_rt()
    c = ctx(config)
    async with node(config, "learn", "Write postmortem and claims") as s:
        # the Scribe and Curator calls are independent: run them together (with models on this halves the wait)
        (pm, pm_src, phash), (claims, cl_src) = await asyncio.gather(write_postmortem(rt, state, c["run_id"]),
                                                                      draft_claims(rt, state, c["run_id"]))
        card(config, type="postmortem", status="info", title=f"Postmortem {rt.incidents.get(state['incident_id'])['display_id']}",
             incident_id=state["incident_id"], body={k: pm[k] for k in ("incident_id", "summary", "impact", "timeline_md", "cause",
                                                                         "actions", "follow_ups")},
             actions=["open_incident_room"], source=pm_src)
        for cl in claims:
            card(config, type="claim_review", status="proposed", title=f"Claim to review: {cl['id']}", incident_id=state["incident_id"],
                 body={"claim_id": cl["id"], "statement": cl["statement"], "structured": cl["structured"], "scope": cl["scope"],
                       "author": cl["author"], "assigned_reviewer": cl.get("assigned_reviewer"),
                       "source": {"type": "incident", "id": state["incident_id"],
                                  "display_id": rt.incidents.get(state["incident_id"])["display_id"]}},
                 actions=["confirm", "edit_confirm", "reject"], source=cl_src)
            rt.incidents.timeline(state["incident_id"], "claim_drafted", rt.users.actor_ref("baton"), f"Claim drafted: {cl['id']}",
                                  cl["statement"], {"type": "claim", "id": cl["id"]})
        promoted = []
        for a in rt.store.all("approvals", "incident_id = ?", (state["incident_id"],)):
            for stp in a.get("steps", []):
                if stp.get("catalog_id"):
                    key = f"{stp['catalog_id']}|{stp.get('param_class', 'any')}|operator"
                    cand = rt.ledger.evaluate_promotion(key)
                    if cand:
                        promoted.append(cand["text"])
        rt.audit.append("agent", "baton", "learn.complete", state["incident_id"],
                        {"claims": [c_["id"] for c_ in claims], "promotion_candidates": promoted}, incident_id=state["incident_id"])
        s.summary = f"Postmortem written; {len(claims)} claims drafted" + (f"; {promoted[0]}" if promoted else "")
        s.model = pm_src if pm_src == cl_src else ("fallback" if "fallback" in (pm_src, cl_src) else pm_src)
        s.prompt_hash = phash
    return {}


# ---------------------------------------------------------------- graph

def build(saver):
    g = StateGraph(InvState)
    for name, fn in [("read_situation", read_situation), ("gather", gather), ("score", score), ("pick", pick),
                     ("check_policy", check_policy), ("run_checks", run_checks), ("wait_checks", wait_checks),
                     ("run_approved_check", run_approved_check), ("read_results", read_results), ("enough", enough),
                     ("escalate", escalate), ("expert", expert), ("options", build_options), ("wait_decision", wait_decision),
                     ("act", act), ("act_wait", act_wait), ("verify", verify), ("close", close), ("learn", learn)]:
        g.add_node(name, fn)
    g.add_edge(START, "read_situation")
    g.add_edge("read_situation", "gather")
    g.add_edge("gather", "score")
    g.add_edge("score", "pick")
    g.add_conditional_edges("pick", after_pick, {"policy": "check_policy", "enough": "enough"})
    g.add_edge("check_policy", "run_checks")
    g.add_conditional_edges("run_checks", checks_pending, {"wait_checks": "wait_checks", "read_results": "read_results"})
    g.add_edge("wait_checks", "run_approved_check")
    g.add_conditional_edges("run_approved_check", checks_pending, {"wait_checks": "wait_checks", "read_results": "read_results"})
    g.add_edge("read_results", "enough")
    g.add_conditional_edges("enough", after_enough, {"expert": "expert", "pick": "pick", "escalate": "escalate"})
    g.add_edge("escalate", END)
    g.add_edge("expert", "options")
    g.add_edge("options", "wait_decision")
    g.add_conditional_edges("wait_decision", after_decision, {"act": "act", "close": "close"})
    g.add_conditional_edges("act", after_act, {"act_wait": "act_wait", "act": "act", "verify": "verify"})
    g.add_edge("act_wait", "act")
    g.add_conditional_edges("verify", after_verify, {"close": "close", "end": END})
    g.add_conditional_edges("close", lambda st: "learn" if st.get("outcome") == "recovered" else "end",
                            {"learn": "learn", "end": END})
    g.add_edge("learn", END)
    return g.compile(checkpointer=saver)

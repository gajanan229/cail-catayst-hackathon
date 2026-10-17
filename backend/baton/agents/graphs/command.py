"""Command graph (MVP spec §8.2, §11.1): plain language → plan of catalog commands → validate → policy →
auto-run or approval → execute (token-checked) → parse → explain."""
from __future__ import annotations

import asyncio
import json
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ...api.deps import rt as get_rt
from .. import prompts as P
from ..cards import command_body, command_status, execution_block
from .common import card, ctx, edited_params, node, patch, wait_for_approval

MAX_STEPS = 6


class CommandState(TypedDict, total=False):
    thread_id: str
    text: str
    actor: str
    incident_id: str | None
    entities: dict
    candidates: list
    plan: list
    rationale: str
    plan_source: str
    refused: bool
    refuse_reason: str
    alternatives: list
    steps: list            # prepared step records: {step_id, catalog_id, params, card_id, approval_id, status, exec_id}
    plan_card_id: str | None
    current: dict | None
    done: list


def _ts():
    from .common import sim_ts
    return sim_ts()


async def understand(state: CommandState, config) -> dict:
    async with node(config, "understand", "Understand") as s:
        s.summary = f"Request: {state['text'][:80]}"
        s.inputs = state["text"]
    return {}


async def resolve(state: CommandState, config) -> dict:
    rt = get_rt()
    async with node(config, "resolve", "Resolve names") as s:
        ents = rt.commands.entities(state["text"])
        shown = {k: v for k, v in ents.items() if k in ("cpu", "process", "server_class", "volume", "n", "relative_n", "subsystem")}
        s.summary = ", ".join(f"{k}={v}" for k, v in shown.items()) or "No names found"
        s.tools = ["entities"]
    return {"entities": ents}


async def find(state: CommandState, config) -> dict:
    rt = get_rt()
    async with node(config, "find", "Find catalog entries") as s:
        cands = rt.commands.candidates(state["text"])
        s.summary = ", ".join(c for c, _ in cands[:4]) or "No candidates"
        s.tools = ["catalog.search"]
    return {"candidates": [c for c, _ in cands]}


async def plan(state: CommandState, config) -> dict:
    rt = get_rt()
    c = ctx(config)
    async with node(config, "plan", "Plan") as s:
        fb = rt.commands.plan_fallback(state["text"])
        steps, rationale, source = [], fb.rationale, "fallback"
        refused = fb.refused
        reason = fb.rationale if fb.refused else ""
        is_unsupported = bool(rt.commands.refuse_reason(state["text"].lower()))
        cand_ids = list(dict.fromkeys(state.get("candidates", []) + [st.catalog_id for st in fb.steps]))
        if not is_unsupported and cand_ids:
            cand_desc = []
            for cid in cand_ids[:8]:
                e = rt.catalog.get(cid)
                cand_desc.append({"id": cid, "title": e.title, "params": {k: v.model_dump(exclude_none=True) for k, v in e.params.items()},
                                  "examples": [x.model_dump() for x in e.examples[:2]]})
            site = {"server_classes": list(rt.sim.site and [s_["name"] for s_ in rt.sim.site["server_classes"]]),
                    "batch_processes": [p["name"] for p in rt.sim.site["processes"] if "batch" in (p.get("tags") or [])]}
            out, source_m, phash = await rt.gateway.complete("planner", P.SYSTEM, P.render(
                "planner", candidates=cand_desc, entities=state.get("entities", {}), site=site, request=state["text"]),
                P.PlannerOut, run_id=c["run_id"], node="plan")
            s.prompt_hash = phash
            if out is not None:
                good = [st for st in out["steps"] if st["catalog_id"] in cand_ids][:MAX_STEPS]
                if good:
                    steps = [{"catalog_id": st["catalog_id"], "params": st.get("params") or {}, "purpose": st.get("purpose", ""),
                              "parallel_group": st.get("parallel_group", 0)} for st in good]
                    rationale, source, refused = out.get("rationale", ""), source_m, False
                elif not out["steps"]:
                    source = source_m
            if source == "fallback":
                s.model = "fallback"
            else:
                s.model = source
        if not steps and not refused:
            steps = [{"catalog_id": st.catalog_id, "params": st.params, "purpose": st.purpose, "parallel_group": 0}
                     for st in fb.steps][:MAX_STEPS]
            if source != "fallback" and not steps:
                refused, reason = True, "No catalog entry matches this request"
        if is_unsupported:
            steps, refused, reason = [], True, fb.rationale
        s.summary = ("Refused: " + reason) if refused else f"{len(steps)} step(s): " + ", ".join(x["catalog_id"] for x in steps)
        s.output = json.dumps(steps)[:400]
    return {"plan": steps, "rationale": rationale, "plan_source": source, "refused": refused, "refuse_reason": reason,
            "alternatives": fb.alternatives}


def after_plan(state: CommandState) -> str:
    return "not_in_catalog" if state.get("refused") or not state.get("plan") else "validate"


async def not_in_catalog(state: CommandState, config) -> dict:
    rt = get_rt()
    async with node(config, "not_in_catalog", "Find catalog entries") as s:
        alts = []
        for cid in state.get("alternatives", [])[:2]:
            e = rt.catalog.get(cid)
            if e:
                alts.append({"catalog_id": cid, "title": e.title, "rendered": e.template or e.title})
        rt.store.put("catalog_requests", f"req_{ctx(config)['run_id']}", {"utterance": state["text"], "actor": state["actor"],
                                                                          "status": "open"})
        md = (f"**Not in Baton's catalog.** {state.get('refuse_reason') or 'No catalog command matches this request.'} "
              "Baton only runs commands from its reviewed catalog. Your request was logged as a catalog request.")
        card(config, type="text", status="info", title="Not in Baton's catalog", incident_id=state.get("incident_id"),
             body={"markdown": md, "alternatives": alts}, source=state.get("plan_source"))
        s.summary = "Refused; logged a catalog request"
    return {}


async def validate_steps(state: CommandState, config) -> dict:
    rt = get_rt()
    out = []
    async with node(config, "validate", "Validate") as s:
        errors = 0
        for st in state["plan"]:
            p = rt.commands.prepare(st["catalog_id"], st["params"], state["actor"], state.get("incident_id"))
            rec = {"step_id": p.step_id, "catalog_id": st["catalog_id"], "params": p.validation.params, "purpose": st.get("purpose"),
                   "valid": p.validation.valid, "errors": p.validation.errors, "card_id": None, "approval_id": None,
                   "status": "proposed", "exec_id": None, "parallel_group": st.get("parallel_group", 0)}
            errors += 0 if p.validation.valid else 1
            out.append(rec)
        s.summary = "All steps valid" if not errors else f"{errors} step(s) failed validation"
        s.tools = ["validator"]
    return {"steps": out}


async def check_policy(state: CommandState, config) -> dict:
    rt = get_rt()
    c = ctx(config)
    steps = []
    async with node(config, "policy", "Check policy") as s:
        effects = []
        for st in state["steps"]:
            p = rt.commands.prepare(st["catalog_id"], st["params"], state["actor"], state.get("incident_id"), step_id=st["step_id"])
            body = command_body(p, purpose=st.get("purpose") or p.entry.description)
            title = p.entry.title + (f" {p.validation.target}" if p.validation.target and p.validation.target not in p.entry.title else "")
            if not p.validation.valid:
                status, actions = "failed", []
                body["policy"] = {**p.policy, "explanation": "; ".join(p.validation.errors)}
            else:
                status, actions = command_status(p)
            cd = card(config, type="command", status=status, title=title, incident_id=state.get("incident_id"), body=body,
                      actions=actions, citations=_cmd_citations(rt, p.catalog_id), source=None)
            st = {**st, "card_id": cd["id"], "status": status}
            if p.validation.valid and p.policy["effect"] == "require_approval":
                a = rt.approvals.create(kind="command", thread_id=c["thread_id"], incident_id=state.get("incident_id"),
                                        card_id=cd["id"], steps=[p.step_dict()], tier=p.validation.tier, policy=p.policy,
                                        requested_by=state["actor"], graph_key=c["graph_key"])
                patch(cd["id"], body={"approval_id": a["id"], "approval_progress": a["progress_text"]})
                st["approval_id"] = a["id"]
                if state.get("incident_id"):
                    rt.incidents.timeline(state["incident_id"], "approval_requested", rt.users.actor_ref(state["actor"]),
                                          f"Approval requested: {p.validation.rendered}", a["progress_text"],
                                          {"type": "approval", "id": a["id"]})
            if p.validation.valid and p.policy["effect"] == "deny":
                rt.audit.append("agent", "baton", "policy.deny", p.validation.rendered or p.catalog_id,
                                {"catalog_id": p.catalog_id, "params": p.validation.params, "explanation": p.policy["explanation"],
                                 "requested_by": state["actor"]}, policy_rule_ids=p.policy["rule_ids"],
                                incident_id=state.get("incident_id"))
            effects.append(f"{p.catalog_id}: {p.policy['effect']}")
            steps.append(st)
        plan_card_id = None
        if len(steps) > 1:
            pc = card(config, type="plan", status="proposed", title=state["text"][:80], incident_id=state.get("incident_id"),
                      body={"request": state["text"], "rationale": state.get("rationale") or "",
                            "steps": [_plan_item(rt, x) for x in steps]},
                      actions=[], source=state.get("plan_source"))
            plan_card_id = pc["id"]
        s.summary = "; ".join(effects)
        s.tools = ["policy"]
    return {"steps": steps, "plan_card_id": plan_card_id}


def _plan_item(rt, st: dict) -> dict:
    e = rt.catalog.get(st["catalog_id"])
    p = rt.store.get("cards", st["card_id"]) if st.get("card_id") else None
    rendered = p["body"]["rendered"] if p else e.title
    tier = p["body"]["tier"] if p else e.tier
    return {"step_id": st["step_id"], "catalog_id": st["catalog_id"], "rendered": rendered, "tier": tier,
            "parallel_group": st.get("parallel_group", 0), "status": st["status"], "card_id": st.get("card_id")}


def _cmd_citations(rt, catalog_id: str) -> list[dict]:
    cites = []
    kb = getattr(rt, "kb", None)
    if kb and f"cmdref:{catalog_id}" in kb.records:
        cites.append(kb.citation(f"cmdref:{catalog_id}"))
    for ref in (rt.catalog.get(catalog_id).doc_refs or [])[:1]:
        cites.append({"id": f"doc:{catalog_id}", "label": ref["label"], "kind": "hpe_manual", "url": ref["url"]})
    return [c for c in cites if c]


async def _execute(state: CommandState, config, st: dict, approval: dict | None) -> dict:
    rt = get_rt()
    c = ctx(config)
    params = st["params"]
    edited = edited_params(approval["decisions"]) if approval else None
    if edited:
        params = {**params, **edited}
    p = rt.commands.prepare(st["catalog_id"], params, state["actor"], state.get("incident_id"), step_id=st["step_id"])
    if not p.validation.valid or p.denied:
        reason = "; ".join(p.validation.errors) or p.policy["explanation"]
        patch(st["card_id"], status="blocked" if p.denied else "failed", actions=[],
              body={"policy": p.policy, "validation_errors": p.validation.errors})
        return {**st, "status": "failed", "error": reason}
    auto = approval is None
    approved_by = rt.approvals.approvers(approval) if approval else []
    patch(st["card_id"], status="running", actions=[], body={"approvers": [rt.users.name(a) for a in approved_by]})
    try:
        ex = await rt.commands.run(p, actor="baton" if auto else (approved_by[0] if approved_by else state["actor"]),
                                   approved_by=approved_by, auto=auto, approval_id=approval["id"] if approval else None,
                                   thread_id=c["thread_id"], incident_id=state.get("incident_id"))
    except Exception as e:
        patch(st["card_id"], status="failed", body={"validation_errors": [str(e)]})
        return {**st, "status": "failed", "error": str(e)}
    summary = interpret_template(rt, st["catalog_id"], ex.get("facts") or {})
    rt.store.put("executions", ex["id"], {**ex, "summary": summary}, catalog_id=ex["catalog_id"], status=ex["status"], sim_ts=ex["sim_ts"])
    acts = ["undo"] if ex.get("undo_entry_id") else []
    patch(st["card_id"], status="done" if ex["status"] == "done" else "failed", actions=acts,
          body={"execution": execution_block(rt, ex, summary, "fallback"), "params": p.validation.params,
                "rendered": p.validation.rendered})
    return {**st, "status": ex["status"], "exec_id": ex["id"], "params": p.validation.params}


async def run_auto(state: CommandState, config) -> dict:
    async with node(config, "run", "Run") as s:
        steps = list(state["steps"])
        idx = [i for i, st in enumerate(steps) if st["status"] == "auto_running"]
        results = await asyncio.gather(*[_execute(state, config, steps[i], None) for i in idx])
        for i, r in zip(idx, results):
            steps[i] = r
        s.summary = f"Auto-ran {len(idx)} step(s)" if idx else "Nothing to auto-run"
        s.tools = [steps[i]["catalog_id"] for i in idx]
    _refresh_plan(state, steps)
    return {"steps": steps}


def _refresh_plan(state: CommandState, steps: list) -> None:
    if state.get("plan_card_id"):
        rt = get_rt()
        patch(state["plan_card_id"], body={"steps": [_plan_item(rt, x) for x in steps]},
              status="done" if all(x["status"] in ("done", "failed", "rejected", "blocked") for x in steps) else "proposed")


def next_pending(state: CommandState) -> str:
    return "wait" if any(st.get("approval_id") and st["status"] == "awaiting_approval" for st in state["steps"]) else "read"


async def wait(state: CommandState, config) -> dict:
    st = next(st for st in state["steps"] if st.get("approval_id") and st["status"] == "awaiting_approval")
    async with node(config, "wait", "Wait for approval", step_id=f"stp_wait_{st['approval_id']}") as s:
        s.summary = "Waiting for approval"
        resp = wait_for_approval(st["approval_id"], f"Approve {st['catalog_id']}?")
        s.summary = f"Approval {resp['status']}"
    return {"current": {"step_id": st["step_id"], **resp}}


async def run_approved(state: CommandState, config) -> dict:
    rt = get_rt()
    cur = state["current"]
    steps = list(state["steps"])
    i = next(i for i, st in enumerate(steps) if st["step_id"] == cur["step_id"])
    async with node(config, "run", "Run") as s:
        a = rt.approvals.get(cur["approval_id"])
        if cur["status"] == "approved":
            steps[i] = await _execute(state, config, steps[i], a)
            s.summary = f"Ran {steps[i]['catalog_id']} ({steps[i]['status']})"
        else:
            steps[i] = {**steps[i], "status": "rejected" if cur["status"] == "rejected" else "expired"}
            patch(steps[i]["card_id"], status=steps[i]["status"], actions=[])
            s.summary = f"Not run: {cur['status']}"
    _refresh_plan(state, steps)
    return {"steps": steps, "current": None}


async def read_output(state: CommandState, config) -> dict:
    async with node(config, "read", "Read output") as s:
        done = [st for st in state["steps"] if st.get("exec_id")]
        s.summary = f"Parsed {len(done)} output(s)"
        s.evidence_ids = [st["exec_id"] for st in done]
        s.tools = ["parsers"]
    return {"done": done}


async def explain(state: CommandState, config) -> dict:
    rt = get_rt()
    c = ctx(config)
    async with node(config, "explain", "Explain") as s:
        done = [st for st in state["steps"] if st.get("exec_id")]
        if not done:
            s.summary = "Nothing to explain"
            return {}
        execs = [rt.executor.get(st["exec_id"]) for st in done]
        texts, sources, cites = [], set(), []
        for ex in execs:
            facts = ex.get("facts") or {}
            fallback = interpret_template(rt, ex["catalog_id"], facts)
            context = expectation_context(rt, ex["catalog_id"], facts)
            docs = _docs_for(rt, ex["catalog_id"])
            out, src, phash = await rt.gateway.complete("interpreter", P.SYSTEM, P.render(
                "interpreter", catalog_id=ex["catalog_id"], facts=facts, expectations=context,
                docs=[{"id": d["id"], "text": d["text"][:500]} for d in docs]), P.InterpreterOut, run_id=c["run_id"], node="explain")
            s.prompt_hash = phash
            if out:
                texts.append(out["summary"])
                sources.add(src)
            else:
                texts.append(fallback + (f" {context['verdict']}" if context.get("verdict") else ""))
                sources.add("fallback")
            cites += [rt.kb.citation(d["id"]) for d in docs if rt.kb.citation(d["id"])]
        source = sorted(sources)[0] if len(sources) == 1 else ("fallback" if "fallback" in sources else sorted(sources)[0])
        s.model = source
        title = "What this shows"
        md = " ".join(texts)
        card(config, type="text", status="info", title=title, incident_id=state.get("incident_id"),
             body={"markdown": md}, citations=_dedupe(cites)[:4], source=source)
        s.summary = md[:140]
    return {}


async def learn(state: CommandState, config) -> dict:
    rt = get_rt()
    async with node(config, "learn", "Learn") as s:
        keys = []
        if not state.get("incident_id"):
            for st in state["steps"]:
                if st.get("approval_id"):
                    p = rt.commands.prepare(st["catalog_id"], st["params"], state["actor"])
                    cand = rt.ledger.evaluate_promotion(p.autonomy["key"])
                    if cand:
                        keys.append(p.autonomy["key"])
        s.summary = ("Promotion candidate: " + ", ".join(keys)) if keys else "Ledger updated"
        s.tools = ["ledger"]
    return {}


def _docs_for(rt, catalog_id: str) -> list[dict]:
    out = []
    if f"cmdref:{catalog_id}" in rt.kb.records:
        out.append(rt.kb.records[f"cmdref:{catalog_id}"])
    if catalog_id.startswith("pathcom") and "concept:server-classes" in rt.kb.records:
        out.append(rt.kb.records["concept:server-classes"])
    return out


def _dedupe(cites: list[dict]) -> list[dict]:
    seen, out = set(), []
    for c in cites:
        if c and c["id"] not in seen:
            seen.add(c["id"])
            out.append(c)
    return out


def time_label(dt) -> str:
    h = dt.hour + dt.minute / 60
    if h < 6:
        return "overnight"
    if h < 10:
        return "early morning"
    if h < 11:
        return "mid-morning"
    if h < 12:
        return "late morning"
    if h < 14:
        return "midday"
    if h < 17:
        return "afternoon"
    return "evening"


def expectation_context(rt, catalog_id: str, facts: dict) -> dict:
    v = rt.health.values
    m = rt.sim.model
    cal = (m.calendar.get("type") if m else "normal") or "normal"
    day = {"black_friday": "Black Friday", "month_end": "month-end", "normal": "a normal day"}.get(cal, cal)
    when = f"{day} {time_label(m.now)}" if m else day
    ctx_: dict[str, Any] = {"when": when}
    if catalog_id in ("pathcom.status_server", "pathcom.stats_server") and facts.get("server_class"):
        svc = {"ATM-AUTH": "atm", "POS-AUTH": "pos"}.get(facts["server_class"])
        if svc:
            p95, hi = v.get(f"svc.{svc}.p95_ms"), v.get(f"svc.{svc}.band_high")
            ctx_.update({"service_p95_ms": p95, "band_high_ms": hi, "band_low_ms": v.get(f"svc.{svc}.band_low")})
            ok = p95 is not None and hi is not None and p95 <= hi and not facts.get("queued")
            ctx_["verdict"] = f"Within normal range for {when}." if ok else f"Outside the normal range for {when}."
    if catalog_id == "tmfcom.status_audittrail" and "fill_pct" in facts:
        ctx_["verdict"] = ("Well below the overflow threshold." if facts["fill_pct"] < 50 else
                           "Approaching the overflow threshold." if facts["fill_pct"] >= 70 else "Elevated but below thresholds.")
    return ctx_


def interpret_template(rt, catalog_id: str, f: dict) -> str:
    """Deterministic interpreter fallback, one template per parser (MVP spec §8.2)."""
    try:
        if catalog_id == "pathcom.status_server":
            return f"{f['running']} of {f['maxservers']} {f['server_class']} servers running, {f['queued']} queued, average {f['avg_ms']} ms."
        if catalog_id == "pathcom.stats_server":
            return f"{f['server_class']} is handling {f['requests_per_s']:.0f} requests per second, average {f['avg_ms']:.0f} ms, maximum {f['max_ms']:.0f} ms."
        if catalog_id == "pathcom.info_server":
            return (f"{f['server_class']} runs on CPUs {', '.join(map(str, f['cpus']))} with NUMSTATIC {f['numstatic']}, "
                    f"MAXSERVERS {f['maxservers']} and MAXLINKS {f['maxlinks']}.")
        if catalog_id == "meas.cpu_busy":
            down = f.get("down") or []
            d = f" CPU {', '.join(map(str, down))} is down." if down else " All CPUs are up."
            return f"Hottest CPU is {f['hottest_cpu']} at {f['hottest_busy']:.0f}% busy.{d}"
        if catalog_id == "tmfcom.status_audittrail":
            return (f"Audit trail {f['trail']} is {f['fill_pct']:.0f}% full; overflow at {f['overflow_pct']:.0f}%, "
                    f"begin-transaction disable at {f['btd_pct']:.0f}%.")
        if catalog_id == "tmfcom.status_tmf":
            return f"TMF is {f['state'].lower()}, {f['tps']:.0f} transactions per second, {f['aborts_per_s']:.2f} aborts per second."
        if catalog_id == "tacl.status_cpu":
            top = f.get("processes", [])[:3]
            return "Top work: " + ", ".join(f"{p['name']} {p['busy']:.0f}%" for p in top) + "."
        if catalog_id == "tacl.status_process":
            b = f"backup on CPU {f['backup_cpu']}" if f.get("backup_cpu") is not None else "no backup"
            return f"{f['process']} is {f['state'].lower()} on CPU {f['cpu']} ({b}), priority {f['priority']}."
        if catalog_id == "pathcom.status_pathmon":
            b = f"backup on CPU {f['backup_cpu']}" if f.get("backup_cpu") is not None else "running without a backup"
            return f"PATHMON {f['pathmon']} primary is on CPU {f['primary_cpu']}, {b}."
        if catalog_id == "scf.status_disk":
            return f"Both halves are {f['primary_half'].lower()}; the process pair is on its {f['process_pair'].lower()} path." \
                if f.get("process_pair") == "BACKUP" else f"Both halves are {str(f.get('primary_half', '')).lower()}."
        if catalog_id == "baton.service_kpis":
            return (f"{f['service'].upper()} p95 is {f['p95_ms']:.0f} ms against a band of {f['band_low']:.0f}–{f['band_high']:.0f} ms; "
                    f"timeouts {f['timeout_pct']:.2f}%.")
        if catalog_id == "baton.n1_headroom":
            return f.get("text", "N-1 computed.")
        if catalog_id == "baton.recent_events":
            eps = f.get("episodes", [])[:3]
            return f"{f.get('count', 0)} episodes; top: " + "; ".join(f"{e['subsystem']} {e['event_number']} ×{e['count']}" for e in eps) + "."
        if catalog_id.startswith("tacl.") or catalog_id.startswith("pathcom.alter"):
            if "error" in f:
                return f"Rejected: {f.get('error_text') or f['error']}."
            if "servers_starting" in f:
                return f"{f['server_class']} NUMSTATIC now {f.get('numstatic')}; {f['servers_starting']} servers starting on CPUs {', '.join(map(str, f['on_cpus']))}."
            if "numstatic" in f or "maxservers" in f:
                k = "numstatic" if "numstatic" in f else "maxservers"
                return f"{f['server_class']} {k.upper()} now {f[k]} (was {f['previous']})."
            if "priority" in f:
                return f"{f['process']} priority now {f['priority']} (was {f['previous_priority']})."
            return f"{f.get('process')} is now {str(f.get('state', '')).lower()}."
    except (KeyError, TypeError, ValueError):
        pass
    return "Command completed."


def build(saver):
    g = StateGraph(CommandState)
    g.add_node("understand", understand)
    g.add_node("resolve", resolve)
    g.add_node("find", find)
    g.add_node("plan", plan)
    g.add_node("not_in_catalog", not_in_catalog)
    g.add_node("validate", validate_steps)
    g.add_node("policy", check_policy)
    g.add_node("run_auto", run_auto)
    g.add_node("wait", wait)
    g.add_node("run_approved", run_approved)
    g.add_node("read", read_output)
    g.add_node("explain", explain)
    g.add_node("learn", learn)
    g.add_edge(START, "understand")
    g.add_edge("understand", "resolve")
    g.add_edge("resolve", "find")
    g.add_edge("find", "plan")
    g.add_conditional_edges("plan", after_plan, {"not_in_catalog": "not_in_catalog", "validate": "validate"})
    g.add_edge("not_in_catalog", END)
    g.add_edge("validate", "policy")
    g.add_edge("policy", "run_auto")
    g.add_conditional_edges("run_auto", next_pending, {"wait": "wait", "read": "read"})
    g.add_edge("wait", "run_approved")
    g.add_conditional_edges("run_approved", next_pending, {"wait": "wait", "read": "read"})
    g.add_edge("read", "explain")
    g.add_edge("explain", "learn")
    g.add_edge("learn", END)
    return g.compile(checkpointer=saver)

"""Brief graph (P1; FS §7 "System briefs"): facts first, then narration that cites fact IDs, then a numeric
consistency check. If any number in the narration is not in the facts, Baton shows the facts alone.
Rendered as a text card: a green/amber/red headline and three bullets (what changed, what is at risk, what to do)."""
from __future__ import annotations

import re
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from ...api.deps import rt as get_rt
from ...core.timeutil import iso_sim, parse_sim
from .. import prompts as P
from .common import card, ctx, node

NUMBER = re.compile(r"(?<![A-Za-z$*])(\d+(?:\.\d+)?)")
LEVEL_WORD = {"green": "Green", "amber": "Amber", "red": "Red"}


class BriefState(TypedDict, total=False):
    thread_id: str
    text: str
    actor: str
    incident_id: str | None
    facts: list
    level: str
    brief: dict
    source: str


def gather_facts(rt) -> tuple[list[dict], str]:
    """Return (facts, headline level). Each fact: {id, text, numbers[]}."""
    facts: list[dict] = []

    def add(fid: str, text: str) -> None:
        facts.append({"id": fid, "text": text, "numbers": [float(x) for x in NUMBER.findall(text)]})

    m = rt.sim.model
    v = rt.health.values
    snap = rt.health.build_snapshot(m) if m else None
    since = rt.store.kv_get("last_brief_sim_ts")
    level = "green"
    incidents = [i for i in rt.incidents.list() if i["status"] != "resolved"]
    for inc in incidents[:2]:
        add(f"fact:incident:{inc['display_id']}", f"{inc['display_id']} {inc['title']} is {inc['status']} (severity {inc['severity']})")
        level = "red" if inc["severity"] >= 4 else "amber"
    sits = [s for s in rt.pipeline.list_situations() if s["status"] != "resolved" and not s.get("incident_id")]
    for s in sits[:2]:
        add(f"fact:situation:{s['id'][-6:]}", f"Open situation: {s['title']}")
        level = "amber" if level == "green" else level
    if snap:
        bad = [c for c in snap["components"] if c["state"] in ("degraded", "critical", "down")]
        for c in bad[:4]:
            reason = c["reasons"][0]["text"] if c["reasons"] else c["state"]
            add(f"fact:component:{c['id']}", f"{c['name']} is {c['state']}: {reason}")
            if c["state"] in ("critical", "down") and level != "red":
                level = "red" if c["type"] in ("cpu", "service") else "amber"
            elif level == "green":
                level = "amber"
        n1 = snap["n1"]
        add("fact:n1", n1["text"])
        if not n1["safe"] and level == "green":
            level = "amber"
    for svc in ("atm", "pos"):
        p95, lo, hi = v.get(f"svc.{svc}.p95_ms"), v.get(f"svc.{svc}.band_low"), v.get(f"svc.{svc}.band_high")
        if p95 is not None and hi is not None:
            where = "inside" if p95 <= hi else "above"
            add(f"fact:svc:{svc}", f"{svc.upper()} p95 is {p95:.0f} ms, {where} its {lo:.0f}–{hi:.0f} ms band")
    fill = v.get("tmf.mat.fill_pct")
    if fill is not None:
        trend = rt.pipeline.fill_trend()
        t = f", rising {trend:.1f}% per minute" if trend and trend > 0.5 else ""
        add("fact:tmf", f"TMF audit trail is {fill:.0f}% full (overflow at 80%){t}")
    if m:
        cal = m.calendar.get("type")
        if cal and cal != "normal":
            add("fact:calendar", f"Today is {cal.replace('_', ' ')}")
        for p in m.processes.values():
            if p.is_batch and p.window and m.batch_active(p):
                end = f"{int(p.window[1] // 60):02d}:{int(p.window[1] % 60):02d}"
                add(f"fact:batch:{p.name}", f"{p.name} ({p.description or 'batch'}) is running on CPU {p.cpu} until {end}")
            elif p.is_batch and p.state == "SUSPENDED":
                add(f"fact:batch:{p.name}", f"{p.name} is suspended")
    if since:
        execs = [e for e in rt.store.all("executions", "sim_ts >= ?", (since,)) if e.get("tier") in ("T1", "T2") and e["status"] == "done"]
        for e in execs[:3]:
            add(f"fact:action:{e['id'][-6:]}", f"Since the last brief: {e['rendered']}")
    return facts, level


def fallback_brief(facts: list[dict], level: str) -> dict:
    by = {f["id"]: f for f in facts}
    changed = [f for f in facts if f["id"].startswith(("fact:incident", "fact:situation", "fact:action"))]
    # what is at risk, most customer-facing first: a service out of band, then N-1, then other components
    risk = [f for f in facts if f["id"].startswith("fact:svc") and "above" in f["text"]]
    risk += [f for f in facts if f["id"] == "fact:n1" and not f["text"].startswith("N-1 safe")]
    risk += [f for f in facts if f["id"].startswith("fact:component") and "down" not in f["text"]]
    risk += [f for f in facts if f["id"] == "fact:tmf" and "rising" in f["text"]]
    todo = []
    inc = next((f for f in facts if f["id"].startswith("fact:incident")), None)
    if inc:
        todo.append({"text": f"Follow {inc['id'].split(':')[-1]} in the Incident Room.", "fact_ids": [inc["id"]]})
    n1 = by.get("fact:n1")
    if n1 and "risk" in n1["text"]:
        todo.append({"text": "Keep the CPU-loss-at-peak playbook ready (PB-CPU-LOSS-PEAK).", "fact_ids": ["fact:n1"]})
    if not todo:
        todo.append({"text": "No action needed; keep watching the health board.", "fact_ids": []})
    headline = {"green": "All clear", "amber": "Watch closely", "red": "Incident in progress"}[level]

    def first(items, default):
        return {"text": items[0]["text"] + ".", "fact_ids": [items[0]["id"]]} if items else {"text": default, "fact_ids": []}

    return {"level": level, "headline": headline,
            "changed": first(changed, "Nothing new since the last brief."),
            "at_risk": first(risk, "Nothing at risk."),
            "to_do": todo[0]}


def numbers_ok(text: str, facts: list[dict]) -> bool:
    allowed = [n for f in facts for n in f["numbers"]]
    for raw in NUMBER.findall(text):
        x = float(raw)
        if not any(abs(x - a) <= max(1.0, 0.02 * abs(a)) for a in allowed):
            return False
    return True


async def facts_node(state: BriefState, config) -> dict:
    rt = get_rt()
    async with node(config, "facts", "Gather facts") as s:
        facts, level = gather_facts(rt)
        s.summary = f"{len(facts)} facts; headline {level}"
        s.evidence_ids = [f["id"] for f in facts]
        s.tools = ["health", "pipeline", "incidents", "calendar"]
    return {"facts": facts, "level": level}


async def narrate(state: BriefState, config) -> dict:
    rt = get_rt()
    c = ctx(config)
    async with node(config, "narrate", "Write the brief") as s:
        facts, level = state["facts"], state["level"]
        out, src, phash = await rt.gateway.complete("briefer", P.SYSTEM, P.render(
            "briefer", level=level, facts=[{"id": f["id"], "text": f["text"]} for f in facts]), P.BriefOut,
            run_id=c["run_id"], node="brief")
        s.prompt_hash = phash
        brief, source = None, "fallback"
        if out:
            texts = [out["changed"]["text"], out["at_risk"]["text"], out["to_do"]["text"], out["headline"]]
            ids_ok = all(i in {f["id"] for f in facts} for part in ("changed", "at_risk", "to_do") for i in out[part]["fact_ids"])
            if ids_ok and all(numbers_ok(t, facts) for t in texts):
                headline = re.sub(r"^(green|amber|red)\s*[:\-·]\s*", "", out["headline"].strip(), flags=re.I)
                brief, source = {**out, "headline": headline, "level": level}, src
            else:
                s.summary = "Model brief failed the numeric check; showing facts only"
        if brief is None:
            brief = fallback_brief(facts, level)
        s.model = source
        s.summary = s.summary or f"{LEVEL_WORD[level]}: {brief['headline']}"
    return {"brief": brief, "source": source}


async def publish(state: BriefState, config) -> dict:
    rt = get_rt()
    async with node(config, "publish", "Publish brief") as s:
        b = state["brief"]
        when = iso_sim(rt.sim.now)
        sents = [{"text": f"**{LEVEL_WORD[b['level']]}: {b['headline']}**", "citation_ids": []},
                 {"text": f"What changed: {b['changed']['text']}", "citation_ids": b["changed"]["fact_ids"]},
                 {"text": f"At risk: {b['at_risk']['text']}", "citation_ids": b["at_risk"]["fact_ids"]},
                 {"text": f"To do: {b['to_do']['text']}", "citation_ids": b["to_do"]["fact_ids"]}]
        md = "\n".join([sents[0]["text"], "", *[f"- {x['text']}" for x in sents[1:]]])
        facts = {f["id"]: f for f in state["facts"]}
        cites, seen = [], set()
        for x in sents:
            for fid in x["citation_ids"]:
                if fid in facts and fid not in seen:
                    seen.add(fid)
                    cites.append({"id": fid, "label": facts[fid]["text"][:40], "kind": "evidence"})
        time_txt = when[11:16] if when else ""
        card(config, type="text", status="info", title=f"Shift brief {time_txt} · {LEVEL_WORD[b['level']]}",
             incident_id=state.get("incident_id"), body={"markdown": md, "sentences": sents}, citations=cites,
             source=state.get("source"))
        rt.store.kv_set("last_brief_sim_ts", when)
        s.summary = f"{LEVEL_WORD[b['level']]} brief published"
    return {}


def build(saver):
    g = StateGraph(BriefState)
    g.add_node("facts", facts_node)
    g.add_node("narrate", narrate)
    g.add_node("publish", publish)
    g.add_edge(START, "facts")
    g.add_edge("facts", "narrate")
    g.add_edge("narrate", "publish")
    g.add_edge("publish", END)
    return g.compile(checkpointer=saver)

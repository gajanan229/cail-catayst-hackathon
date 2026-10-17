"""Ask graph (MVP spec §11.1): entities → retrieve → optional read-only telemetry facts → answer with
citations → citation check. In an incident, the answer comes from the current evidence and hypotheses."""
from __future__ import annotations

import re
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from ...api.deps import rt as get_rt
from .. import prompts as P
from .common import card, ctx, node


class AskState(TypedDict, total=False):
    thread_id: str
    text: str
    actor: str
    incident_id: str | None
    entities: list
    pack: list
    facts: list
    answer: dict
    source: str


async def understand(state: AskState, config) -> dict:
    rt = get_rt()
    async with node(config, "understand", "Understand") as s:
        ents, _ = rt.kb.entities(state["text"])
        s.summary = ", ".join(ents) or "Question"
        s.inputs = state["text"]
    return {"entities": ents}


async def retrieve(state: AskState, config) -> dict:
    rt = get_rt()
    async with node(config, "retrieve", "Find knowledge") as s:
        q = state["text"]
        if state.get("incident_id"):
            ist = rt.store.kv_get(f"incident_state:{state['incident_id']}", {})
            h = (ist.get("hypotheses") or [{}])[0]
            q = " ".join([q, h.get("label", ""), *[x["label"] for x in h.get("for", [])[:3]], "1034 link errors"])
        res = rt.kb.search(q, k=6)
        pack = [{"id": r["id"], "title": r["title"], "text": rt.kb.records[r["id"]]["text"][:600], "doc_type": r["doc_type"]}
                for r in res["results"]]
        s.summary = ", ".join(p["id"] for p in pack[:4]) or "Nothing found"
        s.evidence_ids = [p["id"] for p in pack]
        s.tools = ["kb.search"]
    return {"pack": pack}


async def telemetry(state: AskState, config) -> dict:
    rt = get_rt()
    facts = []
    async with node(config, "telemetry", "Read telemetry") as s:
        if state.get("incident_id"):
            inc = rt.incidents.get(state["incident_id"])
            ist = rt.store.kv_get(f"incident_state:{state['incident_id']}", {})
            hyps = ist.get("hypotheses") or []
            v = rt.health.values
            svc = ((inc or {}).get("impact", {}).get("service") or "svc:atm").split(":")[-1]
            facts.append({"id": "evidence:incident", "title": inc["display_id"] if inc else "Incident",
                          "text": f"{inc['title']} (opened {(inc['opened_at'] or '')[11:16]})" if inc else ""})
            if hyps:
                h = hyps[0]
                facts.append({"id": "evidence:hypothesis", "title": "Leading hypothesis",
                              "text": f"{h['label']} ({h['p']:.2f}); for: " + ", ".join(x["label"] for x in h.get("for", [])[:3])})
            hot = max(((k, x) for k, x in v.items() if k.startswith("cpu.") and k.endswith(".busy")), key=lambda kv: kv[1], default=None)
            if hot:
                facts.append({"id": "evidence:cpu", "title": "Hottest CPU", "text": f"CPU {hot[0].split('.')[1]} at {hot[1]:.0f}%"})
            p95, hi, q = v.get(f"svc.{svc}.p95_ms"), v.get(f"svc.{svc}.band_high"), v.get("sc.ATM-AUTH.queued")
            if p95 is not None:
                facts.append({"id": "evidence:latency", "title": f"{svc.upper()} latency",
                              "text": f"{svc.upper()} p95 {p95:.0f} ms against a {v.get(f'svc.{svc}.band_low', 0):.0f}–{hi:.0f} ms band; "
                                      f"{q:.0f} ATM requests queued; timeouts {v.get(f'svc.{svc}.timeout_pct', 0):.1f}%"})
            s.summary = f"{len(facts)} incident facts"
        else:
            facts = live_entity_facts(rt, state["text"])
            s.summary = f"{len(facts)} live facts for the names in the question" if facts else "No incident: knowledge only"
        s.tools = ["telemetry"] if facts else []
    return {"facts": facts}


def live_entity_facts(rt, text: str) -> list[dict]:
    """Read-only telemetry facts for a CPU, server class or service named in a question (spec §11.1 Ask)."""
    from ...commands.parsers import tacl_status_cpu
    from ...sim.handlers import h_status_cpu
    m = rt.sim.model
    if m is None:
        return []
    ents = rt.commands.entities(text)
    v = rt.health.values
    facts = []
    if "cpu" in ents and 0 <= ents["cpu"] < m.cpu_count:
        c = ents["cpu"]
        if not m.cpu_up[c]:
            facts.append({"id": f"evidence:cpu{c}", "title": f"CPU {c}", "text": f"CPU {c} is down"})
        else:
            procs = tacl_status_cpu(h_status_cpu(rt.sim, {"cpu": c}))[0].get("processes", [])[:3]
            top = ", ".join(f"{p['name']} {p['busy']:.0f}%" for p in procs)
            facts.append({"id": f"evidence:cpu{c}", "title": f"CPU {c}",
                          "text": f"CPU {c} is {m.cpu_busy[c]:.0f}% busy; the largest users are {top}"})
    cls = ents.get("server_class")
    if cls and f"sc.{cls}.running" in v:
        facts.append({"id": f"evidence:{cls}", "title": cls,
                      "text": f"{cls} has {v[f'sc.{cls}.running']:.0f} of {v[f'sc.{cls}.max']:.0f} servers running and "
                              f"{v[f'sc.{cls}.queued']:.0f} requests queued"})
        svc = {"ATM-AUTH": "atm", "POS-AUTH": "pos"}.get(cls)
        if svc:
            facts.append({"id": f"evidence:svc-{svc}", "title": f"{svc.upper()} latency",
                          "text": f"{svc.upper()} p95 is {v.get(f'svc.{svc}.p95_ms', 0):.0f} ms against a "
                                  f"{v.get(f'svc.{svc}.band_low', 0):.0f}–{v.get(f'svc.{svc}.band_high', 0):.0f} ms band"})
    return facts


def fallback_answer(state: AskState) -> dict:
    """Top three evidence snippets with a lead-in sentence (MVP spec §11.2)."""
    sentences = []
    if state.get("incident_id") and state.get("facts"):
        f = {x["id"]: x for x in state["facts"]}
        inc = f.get("evidence:incident")
        hyp = f.get("evidence:hypothesis")
        lat = f.get("evidence:latency")
        cpu = f.get("evidence:cpu")
        if inc:
            sentences.append({"text": f"This is {inc['title']}: {inc['text']}.", "citation_ids": ["evidence:incident"]})
        if lat and cpu:
            sentences.append({"text": f"{cpu['text']}; {lat['text']}.", "citation_ids": ["evidence:cpu", "evidence:latency"]})
        if hyp:
            sentences.append({"text": f"Baton's leading explanation is {hyp['text']}.", "citation_ids": ["evidence:hypothesis"]})
        msg = next((p for p in state.get("pack", []) if p["doc_type"] in ("claim", "operator_message") and "1034" in p["text"]), None)             or next((p for p in state.get("pack", []) if p["doc_type"] in ("claim", "operator_message")), None)
        if msg:
            sentences.append({"text": _first_sentence(msg["text"]), "citation_ids": [msg["id"]]})
        return {"sentences": sentences[:4], "unknown": False, "ask_whom": None}
    if state.get("facts"):   # live facts for the names in the question come first, then one supporting document
        sentences = [{"text": f["text"] + ".", "citation_ids": [f["id"]]} for f in state["facts"]]
        doc = next((p for p in state.get("pack", []) if p["doc_type"] in ("claim", "concept", "site_fact", "playbook")), None)
        if doc:
            sentences.append({"text": _first_sentence(doc["text"]), "citation_ids": [doc["id"]]})
        return {"sentences": sentences, "unknown": False, "ask_whom": None}
    pack = state.get("pack", [])[:3]
    if not pack:
        return {"sentences": [{"text": "Baton's knowledge base has nothing on this yet.", "citation_ids": []}], "unknown": True,
                "ask_whom": "On-call expert Dave"}
    pack = sorted(pack, key=lambda p: {"concept": 0, "operator_message": 1, "command_ref": 2, "claim": 3}.get(p["doc_type"], 4))
    for p in pack:
        sentences.append({"text": _first_sentence(p["text"], 2), "citation_ids": [p["id"]]})
    return {"sentences": sentences, "unknown": False, "ask_whom": None}


def _first_sentence(text: str, n: int = 1) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[:n]).strip()


async def answer(state: AskState, config) -> dict:
    rt = get_rt()
    c = ctx(config)
    async with node(config, "answer", "Answer") as s:
        evidence = [{"id": x["id"], "title": x["title"], "text": x["text"]} for x in state.get("facts", []) + state.get("pack", [])]
        out, src, phash = await rt.gateway.complete("answerer", P.SYSTEM, P.render("answerer", question=state["text"], evidence=evidence),
                                                    P.AnswererOut, run_id=c["run_id"], node="answer",
                                                    stable_key=None if state.get("facts") else
                                                    state["text"].strip().lower())
        s.prompt_hash = phash
        if out:
            ans, source = out, src
        else:
            ans, source = fallback_answer(state), "fallback"
        s.model = source
        s.summary = " ".join(x["text"] for x in ans["sentences"])[:160]
    return {"answer": ans, "source": source}


async def check_citations(state: AskState, config) -> dict:
    rt = get_rt()
    async with node(config, "check_citations", "Check citations") as s:
        ans = dict(state["answer"])
        valid = {x["id"] for x in state.get("facts", []) + state.get("pack", [])}
        dropped = 0
        sents = []
        for x in ans["sentences"]:
            ids = [i for i in x.get("citation_ids", []) if i in valid]
            dropped += len(x.get("citation_ids", [])) - len(ids)
            sents.append({"text": x["text"], "citation_ids": ids})
        if state.get("source") not in ("fallback",) and not any(x["citation_ids"] for x in sents):
            ans, src = fallback_answer(state), "fallback"
            sents = ans["sentences"]
            state = {**state, "source": src}
        cites, seen = [], set()
        facts = {x["id"]: x for x in state.get("facts", [])}
        for x in sents:
            for cid in x["citation_ids"]:
                if cid in seen:
                    continue
                seen.add(cid)
                if cid in facts:
                    cites.append({"id": cid, "label": facts[cid]["text"][:40], "kind": "evidence"})
                else:
                    cc = rt.kb.citation(cid)
                    if cc:
                        cites.append(cc)
        md = " ".join(x["text"] for x in sents)
        link = {"label": "Open Incident Room", "incident_id": state["incident_id"]} if state.get("incident_id") else None
        title = state["text"][:70]
        card(config, type="text", status="info", title=title, incident_id=state.get("incident_id"),
             body={"markdown": md, "sentences": sents, "unknown": bool(ans.get("unknown")), "ask_whom": ans.get("ask_whom"),
                   "link": link}, citations=cites, actions=["open_incident_room"] if link else [], source=state.get("source"))
        s.summary = f"{len(cites)} citations" + (f"; dropped {dropped} unknown" if dropped else "")
    return {}


def build(saver):
    g = StateGraph(AskState)
    g.add_node("understand", understand)
    g.add_node("retrieve", retrieve)
    g.add_node("telemetry", telemetry)
    g.add_node("answer", answer)
    g.add_node("check_citations", check_citations)
    g.add_edge(START, "understand")
    g.add_edge("understand", "retrieve")
    g.add_edge("retrieve", "telemetry")
    g.add_edge("telemetry", "answer")
    g.add_edge("answer", "check_citations")
    g.add_edge("check_citations", END)
    return g.compile(checkpointer=saver)

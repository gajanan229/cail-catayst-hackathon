"""Executor (MVP spec §8.2, §9): token check → ghost typing → simulator handler → parser → facts,
execution record, undo entry, audit. Model output never reaches the system: only rendered catalog
commands with a valid execution token run."""
from __future__ import annotations

import asyncio
from typing import Any

from ..api.errors import ApiError
from ..core.ids import new_id
from ..core.timeutil import iso_sim, wall_now
from ..governance.tokens import TokenError
from ..sim.handlers import run_handler
from .parsers import parse

FACT_LABELS = {
    "pathcom.status_server": [("Running", lambda f: f"{f['running']} of {f['maxservers']}"), ("NUMSTATIC", lambda f: str(f["numstatic"])),
                              ("Queued", lambda f: str(f["queued"])), ("Average", lambda f: f"{f['avg_ms']} ms")],
    "pathcom.info_server": [("CPU list", lambda f: ", ".join(str(c) for c in f["cpus"])), ("NUMSTATIC", lambda f: str(f["numstatic"])),
                            ("MAXSERVERS", lambda f: str(f["maxservers"])), ("MAXLINKS", lambda f: str(f["maxlinks"]))],
    "pathcom.stats_server": [("Requests/s", lambda f: f"{f['requests_per_s']:.0f}"), ("Average", lambda f: f"{f['avg_ms']:.0f} ms"),
                             ("Maximum", lambda f: f"{f['max_ms']:.0f} ms")],
    "tmfcom.status_audittrail": [("Fill", lambda f: f"{f['fill_pct']:.1f}%"), ("Overflow threshold", lambda f: f"{f['overflow_pct']:.0f}%"),
                                 ("Begin-trans disable", lambda f: f"{f['btd_pct']:.0f}%"), ("Dumps", lambda f: f["dumps"])],
    "tmfcom.status_tmf": [("State", lambda f: f["state"]), ("TPS", lambda f: f"{f['tps']:.0f}"), ("Aborts/s", lambda f: f"{f['aborts_per_s']:.2f}")],
    "meas.cpu_busy": [("Hottest", lambda f: f"CPU {f['hottest_cpu']} at {f['hottest_busy']:.0f}%"),
                      ("Down", lambda f: ", ".join(f"CPU {c}" for c in f["down"]) or "none")],
}


def facts_table(catalog_id: str, facts: dict) -> list[dict]:
    rows = []
    for label, fn in FACT_LABELS.get(catalog_id, []):
        try:
            rows.append({"label": label, "value": fn(facts)})
        except (KeyError, TypeError):
            pass
    if not rows and facts:
        for k, v in list(facts.items())[:6]:
            if isinstance(v, (str, int, float)):
                rows.append({"label": k.replace("_", " ").capitalize(), "value": str(v)})
    return rows


class Executor:
    def __init__(self, rt):
        self.rt = rt
        self.prompt_n = 12
        self.terminal_lock = asyncio.Lock()
        self.state_lock = asyncio.Lock()

    def prompt(self) -> str:
        return f"$SYSTEM STARTUP {self.prompt_n}> "

    def get(self, exec_id: str) -> dict:
        e = self.rt.store.get("executions", exec_id)
        if not e:
            raise ApiError("NOT_FOUND", f"Execution {exec_id} not found")
        return e

    def internal_facts(self, catalog_id: str, params: dict) -> tuple[dict, str]:
        rt = self.rt
        v = rt.health.values
        if catalog_id == "baton.service_kpis":
            svc = params.get("service", "atm")
            f = {"service": svc, "tps": v.get(f"svc.{svc}.tps"), "p95_ms": v.get(f"svc.{svc}.p95_ms"),
                 "timeout_pct": v.get(f"svc.{svc}.timeout_pct"), "band_low": v.get(f"svc.{svc}.band_low"),
                 "band_high": v.get(f"svc.{svc}.band_high")}
            f["in_band"] = f["p95_ms"] is not None and f["band_high"] is not None and f["p95_ms"] <= f["band_high"]
            return f, f"{svc.upper()} p95 {f['p95_ms']:.0f} ms (band {f['band_low']:.0f}–{f['band_high']:.0f}), timeouts {f['timeout_pct']:.2f}%"
        if catalog_id == "baton.n1_headroom":
            n1 = dict(rt.health.n1)
            return n1, n1.get("text", "")
        if catalog_id == "baton.recent_events":
            eps = rt.pipeline.episodes_matching(params.get("subsystem"), float(params.get("minutes") or 10))
            eps = [e for e in eps if e["subsystem"] != "APP"][:10]
            return {"episodes": eps, "count": len(eps)}, f"{len(eps)} episodes"
        raise KeyError(catalog_id)

    async def execute(self, *, catalog_id: str, params: dict, rendered: str, token: str, actor: str,
                      approved_by: list[str], auto: bool, tier: str, param_class: str, role: str,
                      step_id: str | None = None, thread_id: str | None = None, incident_id: str | None = None,
                      undo: dict | None = None, undo_rendered: str | None = None, label: str | None = None,
                      previous: dict | None = None) -> dict:
        rt = self.rt
        if rt.sim.model is None or not rt.sim.status.running:
            raise ApiError("SIM_NOT_RUNNING", "The simulator is not running")
        entry = rt.catalog.get(catalog_id)
        if entry is None or entry.blocked or tier == "T3":
            raise ApiError("POLICY_DENIED", "Not executable from Baton", {"catalog_id": catalog_id})
        try:
            approval_ref = rt.tokens.consume(token, rendered)
        except TokenError as e:
            rt.audit.append("system", "executor", "command.refused", rendered, {"reason": str(e), "catalog_id": catalog_id},
                            incident_id=incident_id)
            raise ApiError("POLICY_DENIED", f"Execution token rejected: {e}", {"catalog_id": catalog_id})
        exec_id = new_id("exe")
        started_wall = wall_now()
        sim_ts = iso_sim(rt.sim.now)
        record = {"id": exec_id, "step_id": step_id, "catalog_id": catalog_id, "params": params, "rendered": rendered,
                  "approved_by": approved_by, "auto": auto, "actor": actor, "status": "running", "started_at": started_wall,
                  "ended_at": None, "sim_ts": sim_ts, "raw_text": None, "facts": None, "parse_confidence": None,
                  "undo_entry_id": None, "summary": None, "thread_id": thread_id, "incident_id": incident_id,
                  "tier": tier, "param_class": param_class, "role": role, "approval_ref": approval_ref}
        rt.store.put("executions", exec_id, record, catalog_id=catalog_id, status="running", sim_ts=sim_ts)
        if entry.internal:
            facts, summary = self.internal_facts(catalog_id, params)
            record.update(status="done", facts=facts, raw_text=summary, parse_confidence=1.0, ended_at=wall_now())
        else:
            mutating = tier in ("T1", "T2")
            lock = self.state_lock if mutating else None
            if lock:
                await lock.acquire()
            try:
                async with self.terminal_lock:
                    names = [rt.users.name(a) for a in approved_by]
                    if auto:
                        lvl = rt.ledger.level(catalog_id, param_class, role)
                        by = f" (granted by {lvl['granted_by']})" if lvl.get("granted_by") else ""
                        ghost_label = label or f"Baton · auto · {lvl['level']}{by}"
                    else:
                        ghost_label = label or ("Baton · approved by " + " and ".join(names) if names else f"{rt.users.name(actor)} · typed")
                    ms = rt.config.typing_ms_per_char
                    rt.hub.publish("terminal", "terminal.ghost", {"exec_id": exec_id, "actor": actor, "approved_by": names,
                                                                  "auto": auto, "label": ghost_label, "text": rendered,
                                                                  "ms_per_char": ms})
                    if ms:
                        await asyncio.sleep(len(rendered) * ms / 1000.0 + 0.15)
                    try:
                        lines = run_handler(rt.sim, catalog_id, params)
                        status = "done"
                    except Exception as e:  # handler failure is an execution failure, not a crash
                        lines, status = [f"*ERROR* {e}"], "failed"
                    echo = f"{self.prompt()}{rendered}"
                    self.prompt_n += 1
                    rt.hub.publish("terminal", "terminal.output", {"exec_id": exec_id, "lines": lines})
                    rt.hub.publish("terminal", "terminal.prompt", {"text": self.prompt()})
                facts, conf = parse(entry.parser, lines)
                if "error" in facts:
                    status = "failed"
                record.update(status=status, raw_text="\n".join([echo, *lines]), facts=facts, parse_confidence=conf,
                              ended_at=wall_now())
                if mutating and status == "done" and undo and incident_id:
                    u = {"id": new_id("und"), "execution_id": exec_id, "catalog_id": undo["catalog_id"],
                         "params": undo["params"], "rendered": undo_rendered or "", "label": _undo_label(undo_rendered),
                         "status": "pending", "created_sim_ts": iso_sim(rt.sim.now)}
                    rt.incidents.push_undo(incident_id, u)
                    record["undo_entry_id"] = u["id"]
            finally:
                if lock:
                    lock.release()
        record["ended_at"] = record["ended_at"] or wall_now()
        rt.store.put("executions", exec_id, record, catalog_id=catalog_id, status=record["status"], sim_ts=sim_ts)
        rt.ledger.record_execution(catalog_id, param_class, role)
        rt.audit.append("agent" if actor == "baton" else "user", actor, "command.execute", rendered,
                        {"catalog_id": catalog_id, "params": params, "auto": auto, "approved_by": approved_by,
                         "status": record["status"], "exec_id": exec_id, "tier": tier},
                        policy_rule_ids=[approval_ref.split(":")[1]] if approval_ref.startswith("auto:") else [],
                        incident_id=incident_id)
        if incident_id and not entry.internal:
            kind = "action_executed" if tier in ("T1", "T2") else "check"
            who = "Baton (auto)" if auto else " and ".join(rt.users.name(a) for a in approved_by) or rt.users.name(actor)
            rt.incidents.timeline(incident_id, kind, rt.users.actor_ref(actor),
                                  f"{'Ran' if record['status'] == 'done' else 'Failed'}: {rendered}", f"{who}",
                                  {"type": "execution", "id": exec_id})
        return record


def _undo_label(rendered: str | None) -> str:
    if not rendered:
        return "Undo"
    body = rendered.split("; ", 1)[-1]
    if body.startswith("ALTER SERVER") and "," in body:
        return "ALTER ..." + body.split(",", 1)[1]
    return body


def public_execution(e: dict) -> dict:
    keys = ["id", "step_id", "catalog_id", "params", "rendered", "approved_by", "auto", "actor", "status", "started_at",
            "ended_at", "sim_ts", "raw_text", "facts", "parse_confidence", "undo_entry_id", "summary"]
    return {k: e.get(k) for k in keys}


def as_any(x: Any) -> Any:
    return x

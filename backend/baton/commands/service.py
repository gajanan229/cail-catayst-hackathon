"""Command pipeline services (MVP spec §8.2): entities, catalog candidates, deterministic planner
(top candidate + regex slot filling, with plan templates for common multi-step requests), prepare
(validate + policy + autonomy), preview, and run (token → executor)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from ..core.ids import new_id
from ..core.timeutil import iso_sim, parse_sim
from ..governance.policy import PolicyContext
from .validator import Inventory, normalize_class, validate

CLASS_WORDS = [
    (r"\batm[\s-]*auth(?:ori[sz]ation)?\b|\batm\b", "ATM-AUTH"),
    (r"\bpos[\s-]*auth(?:ori[sz]ation)?\b|\bpos\b", "POS-AUTH"),
    (r"\bbal[\s-]*inq\b|\bbalance[\s-]*inquir(?:y|ies)\b", "BAL-INQ"),
    (r"\bcard[\s-]*(?:mgmt|management|maintenance)\b", "CARD-MGMT"),
]
# Verbs that change state; requests whose main verb is mutating but maps to nothing are refused.
MUTATING_VERBS = {
    "suspend": ["tacl.suspend_process"], "pause": ["tacl.suspend_process"], "hold": ["tacl.suspend_process"],
    "freeze": ["tacl.suspend_process"], "activate": ["tacl.activate_process"], "resume": ["tacl.activate_process"],
    "unsuspend": ["tacl.activate_process"], "stop": ["tacl.stop_process", "tmfcom.stop_tmf"],
    "kill": ["tacl.stop_process"], "terminate": ["tacl.stop_process"], "reload": ["sys.reload_cpu"],
    "reboot": ["sys.reload_cpu"], "restart": ["sys.reload_cpu"], "altpri": ["tacl.altpri_process"],
    "alter": ["pathcom.alter_numstatic", "pathcom.alter_maxservers"],
}
UNSUPPORTED_VERBS = {"purge", "delete", "remove", "erase", "wipe", "format", "drop", "truncate", "shell", "disable",
                     "uninstall", "rename", "copy", "move", "reinstall", "shutdown", "grant", "password"}
READ_HINTS = {"status", "show", "how", "what", "which", "is", "are", "list", "check", "where", "stats", "info", "busy"}


@dataclass
class PlanStep:
    catalog_id: str
    params: dict
    purpose: str = ""
    parallel_group: int = 0


@dataclass
class Plan:
    steps: list[PlanStep]
    rationale: str
    confidence: float
    refused: bool = False
    alternatives: list[str] = field(default_factory=list)
    source: str = "fallback"


@dataclass
class Prepared:
    step_id: str
    catalog_id: str
    entry: Any
    params: dict
    validation: Any
    policy: dict
    autonomy: dict
    role: str
    actor: str

    @property
    def auto(self) -> bool:
        return self.policy["effect"] == "allow_auto"

    @property
    def denied(self) -> bool:
        return self.policy["effect"] == "deny"

    def step_dict(self) -> dict:
        v = self.validation
        return {"step_id": self.step_id, "catalog_id": self.catalog_id, "params": v.params, "rendered": v.rendered,
                "tier": v.tier, "param_class": v.param_class, "undo": v.undo, "undo_rendered": v.undo_rendered,
                "target": v.target, "previous": v.previous}


class CommandService:
    def __init__(self, rt):
        self.rt = rt

    # ------------------------------------------------------------ inventory

    def inventory(self) -> Inventory:
        m = self.rt.sim.model
        site = self.rt.sim.site
        if m is None:
            procs = {p["name"]: {"state": "RUNNING", "tags": p.get("tags", []), "protected": p.get("protected", False),
                                 "priority": p.get("priority", 150), "cpu": p["primary_cpu"]} for p in site["processes"]}
            classes = {s["name"]: {"tag": s.get("tag"), "numstatic": s["numstatic"], "maxservers": s["maxservers"]}
                       for s in site["server_classes"]}
            cpus = {c: True for c in range(int(site["cpus"]["count"]))}
        else:
            procs = {p.name: {"state": p.state, "tags": p.tags, "protected": p.protected, "priority": p.priority, "cpu": p.cpu}
                     for p in m.processes.values()}
            classes = {sc.name: {"tag": sc.tag, "numstatic": sc.numstatic, "maxservers": sc.maxservers,
                                 "running": sc.running(m.tick)} for sc in m.classes.values()}
            cpus = {c: m.cpu_up[c] for c in range(m.cpu_count)}
        return Inventory(cpus_up=cpus, processes=procs, classes=classes, volumes=list(site.get("volumes") or []),
                         protected_patterns=list(self.rt.policy.protected))

    # ------------------------------------------------------------ entities

    def entities(self, text: str) -> dict:
        low = text.lower()
        ents: dict[str, Any] = {}
        m = re.search(r"\b(?:cpu|processor|proc)\s*#?\s*(\d)\b", low)
        if m:
            ents["cpu"] = int(m.group(1))
        procs = [p.upper() for p in re.findall(r"\$[A-Za-z][A-Za-z0-9]{0,6}", text)]
        vols = [p for p in procs if p.startswith("$DATA")]
        if vols:
            ents["volume"] = vols[0]
        if procs:
            ents["process"] = procs[0]
        for pat, cls in CLASS_WORDS:
            if re.search(pat, low) or cls.lower() in low:
                ents["server_class"] = cls
                break
        ents["service"] = "pos" if re.search(r"\bpos\b", low) else "atm"
        nums = [int(n) for n in re.findall(r"(?<![\w$*])(\d{1,3})(?![\w%])", low)]
        if "cpu" in ents and ents["cpu"] in nums:
            nums.remove(ents["cpu"])
        m = re.search(r"\b(?:add|plus|another)\s+(\d{1,2})\s+(?:more\s+)?", low) or re.search(r"\+(\d{1,2})\b", low)
        if m:
            ents["relative_n"] = int(m.group(1))
        m = re.search(r"\b(?:to|=|at)\s+(\d{1,3})\b", low)
        if m:
            ents["n"] = int(m.group(1))
        elif nums and "relative_n" not in ents:
            ents["n"] = nums[-1]
        m = re.search(r"last\s+(\d{1,2})\s*min", low)
        if m:
            ents["minutes"] = int(m.group(1))
        for sub in ("PATHWAY", "OMF", "APP"):
            if re.search(rf"\b{sub.lower()}\b", low):
                ents["subsystem"] = sub
        if "statement batch" in low and "process" not in ents:
            ents["process"] = "$STMT1"
        if "report batch" in low and "process" not in ents:
            ents["process"] = "$RPT2"
        if "month-end batch" in low or "month end batch" in low:
            ents.setdefault("process", "$MEB01")
        return ents

    # ------------------------------------------------------------ candidates and planning

    def candidates(self, text: str, k: int = 8) -> list[tuple[str, float]]:
        low = text.lower()
        words = set(re.findall(r"[a-z0-9$\-]+", low))
        scores: dict[str, float] = {}
        for e in self.rt.catalog.all():
            s = 0.0
            for a in e.aliases:
                if re.search(rf"(?<![\w-]){re.escape(a.lower())}(?![\w-])", low):
                    s += 1.0 + 0.4 * len(a.split())
            title = set(re.findall(r"[a-z0-9]+", e.title.lower())) - {"a", "of", "the", "s"}
            s += 0.3 * len(title & words)
            for ex in e.examples:
                ew = set(re.findall(r"[a-z0-9$\-]+", ex.utterance.lower()))
                if ew:
                    s += 1.5 * len(ew & words) / len(ew | words)
            if s > 0:
                scores[e.id] = s
        kb = getattr(self.rt, "kb", None)
        if kb is not None:
            for rank, r in enumerate(kb.search(text, k=8, types=["catalog"])["results"]):
                cid = r["id"].split(":", 1)[1]
                scores[cid] = scores.get(cid, 0.0) + 0.6 / (1 + rank)
        return sorted(scores.items(), key=lambda x: -x[1])[:k]

    def _verb_rules(self, low: str, ents: dict) -> list[str] | None:
        """High-precision intent rules; return catalog IDs or None."""
        if re.search(r"\b(stop|shut\s*down)\b.*\btmf\b|\btmf\b.*\b(stop|shut\s*down)\b", low):
            return ["tmfcom.stop_tmf"]
        if re.search(r"\b(reload|reboot|restart)\b.*\b(cpu|processor)\b|\b(cpu|processor)\b.*\b(reload|reboot)\b", low):
            return ["sys.reload_cpu"]
        if re.search(r"\b(numstatic|static servers?)\b", low) and re.search(r"\b(set|raise|alter|add|increase|lower|change|to)\b", low):
            return ["pathcom.alter_numstatic"]
        if re.search(r"\b(add|start)\b.*\bservers?\b", low) and "server_class" in ents:
            return ["pathcom.alter_numstatic"]
        if re.search(r"\bmax\s*servers\b|\bmaxservers\b", low):
            asking = re.match(r"^(what|which|how|is|are|show|tell)\b", low) and not re.search(r"\b(raise|increase|lower)\b", low)
            if not asking and re.search(r"\b(set|raise|alter|increase|lower|change)\b", low):
                return ["pathcom.alter_maxservers"]
            return ["pathcom.info_server"]
        if re.search(r"\b(altpri|priority)\b", low) and "process" in ents:
            return ["tacl.altpri_process"]
        if re.search(r"\b(suspend|pause|hold|freeze)\b", low):
            return ["tacl.suspend_process"]
        if re.search(r"\b(activate|resume|unsuspend)\b", low):
            return ["tacl.activate_process"]
        if re.search(r"\b(stop|kill|terminate)\b", low) and "process" in ents:
            return ["tacl.stop_process"]
        if re.search(r"keeping up|keep up|holding up|coping|doing ok|how is .* doing", low) and "server_class" in ents:
            return ["pathcom.status_server", "pathcom.stats_server"]
        if re.search(r"\b(stats|statistics|throughput|requests per second)\b", low) and "server_class" in ents:
            return ["pathcom.stats_server"]
        if re.search(r"\b(config|configuration|cpu list|info)\b", low) and "server_class" in ents:
            return ["pathcom.info_server"]
        if re.search(r"\b(disk|mirror|volume|path)", low) and "volume" in ents:
            return ["scf.status_disk"]
        if re.search(r"\baudit\s*trail|audittrail|audit fill\b", low):
            return ["tmfcom.status_audittrail"]
        if re.search(r"\btmf\b", low):
            return ["tmfcom.status_tmf"]
        if re.search(r"\bpathmon\b", low):
            return ["pathcom.status_pathmon"]
        if re.search(r"\b(n-1|n1|headroom|survive losing)\b", low):
            return ["baton.n1_headroom"]
        if re.search(r"\b(events?|messages|what happened|ems)\b", low):
            return ["baton.recent_events"]
        if re.search(r"\b(p95|latency|timeouts?|kpis?)\b", low) or re.search(r"\b(atm|pos)\s+service\b", low):
            return ["baton.service_kpis"]
        if re.search(r"(running on|processes (in|on))\s+(cpu|processor)", low) or ("cpu" in ents and re.search(r"\bprocess", low)):
            return ["tacl.status_cpu"]
        if re.search(r"\b(cpus?|processors?)\b", low) and re.search(r"\b(busy|load|hot|hottest|utili[sz]ation)\b", low):
            return ["meas.cpu_busy"]
        if "server_class" in ents and re.search(r"\b(servers?|status|running|queue|queued|queuing)\b", low):
            return ["pathcom.status_server"]
        if "process" in ents and re.search(r"\b(status|running|state|up)\b", low):
            return ["tacl.status_process"]
        return None

    def refuse_reason(self, low: str) -> str | None:
        words = set(re.findall(r"[a-z]+", low))
        bad = sorted(words & UNSUPPORTED_VERBS)
        if bad:
            return f"'{bad[0]}' is not something Baton's catalog can do"
        if re.search(r"super\.super|root access|shell", low):
            return "Baton never opens free-form sessions"
        return None

    def plan_fallback(self, text: str) -> Plan:
        low = text.lower()
        ents = self.entities(text)
        reason = self.refuse_reason(low)
        if reason:
            cands = [c for c, _ in self.candidates(text) if not self.rt.catalog.get(c).is_mutating][:2]
            return Plan([], reason, 0.0, refused=True, alternatives=cands)
        ids = self._verb_rules(low, ents)
        if not ids:
            cands = self.candidates(text)
            if not cands or cands[0][1] < 1.0:
                return Plan([], "No catalog entry matches this request", 0.0, refused=True,
                            alternatives=[c for c, _ in cands if not self.rt.catalog.get(c).is_mutating][:2])
            ids = [cands[0][0]]
        steps = [PlanStep(cid, self.fill(cid, ents), purpose=self.rt.catalog.get(cid).title) for cid in ids]
        return Plan(steps, "Matched by Baton's catalog rules", 0.7)

    def fill(self, catalog_id: str, ents: dict) -> dict:
        entry = self.rt.catalog.get(catalog_id)
        inv = self.inventory()
        params: dict[str, Any] = {}
        for name, spec in entry.params.items():
            if spec.type == "cpu" and "cpu" in ents:
                params[name] = ents["cpu"]
            elif spec.type == "process" and "process" in ents:
                params[name] = ents["process"]
            elif spec.type == "volume" and "volume" in ents:
                params[name] = ents["volume"]
            elif spec.type == "server_class" and "server_class" in ents:
                params[name] = ents["server_class"]
            elif name == "service":
                params[name] = ents.get("service", "atm")
            elif name == "subsystem" and "subsystem" in ents:
                params[name] = ents["subsystem"]
            elif name == "minutes":
                params[name] = ents.get("minutes", spec.default or 10)
            elif name == "priority" and "n" in ents:
                params[name] = ents["n"]
            elif name == "n":
                cls = inv.classes.get(params.get("server_class") or ents.get("server_class", ""), {})
                if "relative_n" in ents and cls:
                    base = cls.get("numstatic") if catalog_id == "pathcom.alter_numstatic" else cls.get("maxservers")
                    params[name] = int(base) + ents["relative_n"]
                elif "n" in ents:
                    params[name] = ents["n"]
        return params

    # ------------------------------------------------------------ prepare, preview, run

    def role_of(self, actor: str) -> str:
        if actor in ("baton", "system"):
            return "operator"
        return self.rt.users.get(actor)["role"]

    def state_changes_recent(self, incident_id: str | None) -> int:
        if not incident_id or self.rt.sim.now is None:
            return 0
        since = iso_sim(self.rt.sim.now - timedelta(seconds=600))
        rows = self.rt.store.all("executions", "sim_ts >= ?", (since,))
        return sum(1 for r in rows if r.get("incident_id") == incident_id and r.get("tier") in ("T1", "T2")
                   and r.get("status") == "done")

    def prepare(self, catalog_id: str, params: dict, actor: str, incident_id: str | None = None,
                step_id: str | None = None) -> Prepared:
        rt = self.rt
        entry = rt.catalog.get(catalog_id)
        if entry is None:
            raise KeyError(catalog_id)
        inv = self.inventory()
        v = validate(entry, params, inv)
        role = self.role_of(actor)
        lvl = rt.ledger.level(catalog_id, v.param_class, role)
        ctx = PolicyContext(catalog_id=catalog_id, tier=v.tier, target=v.params.get("process"), actor_role=role,
                            ledger_level=lvl["level"], ledger_progress=lvl["progress"], ledger_granted_by=lvl["granted_by"],
                            internal=entry.internal, read_only=rt.read_only,
                            state_changes_recent=self.state_changes_recent(incident_id), escalation=entry.escalation)
        decision = rt.policy.evaluate(ctx).as_dict()
        autonomy = {"level": lvl["level"] if lvl["level"] != "system" else "system", "key": lvl["key"],
                    "progress": lvl["card_progress"], "granted_by": lvl["granted_by"]}
        return Prepared(step_id=step_id or new_id("stp"), catalog_id=catalog_id, entry=entry, params=v.params,
                        validation=v, policy=decision, autonomy=autonomy, role=role, actor=actor)

    def preview(self, catalog_id: str, params: dict, actor: str) -> dict:
        if self.rt.catalog.get(catalog_id) is None:
            from ..api.errors import ApiError
            raise ApiError("NOT_FOUND", f"Catalog entry {catalog_id} not found")
        p = self.prepare(catalog_id, params, actor)
        v = p.validation
        return {"valid": v.valid, "errors": v.errors, "rendered": v.rendered, "tier": v.tier,
                "policy": p.policy if v.valid else None, "undo": v.undo_rendered}

    async def run(self, p: Prepared, *, actor: str, approved_by: list[str], auto: bool, approval_id: str | None,
                  thread_id: str | None, incident_id: str | None) -> dict:
        v = p.validation
        rendered = v.rendered or p.entry.id
        token = self.rt.tokens.issue(rendered, approval_id or f"auto:{p.policy['rule_ids'][0]}")
        return await self.rt.executor.execute(
            catalog_id=p.catalog_id, params=v.params, rendered=rendered, token=token, actor=actor,
            approved_by=approved_by, auto=auto, tier=v.tier, param_class=v.param_class, role=p.role,
            step_id=p.step_id, thread_id=thread_id, incident_id=incident_id, undo=v.undo, undo_rendered=v.undo_rendered,
            previous=v.previous)

    def match_line(self, line: str) -> tuple[str, dict] | None:
        """Manual terminal input: parse a typed line against catalog templates."""
        text = line.strip()
        text = re.sub(r"^\$\S+ \S+ \d+> ", "", text)
        for e in self.rt.catalog.all():
            if not e.template or e.internal or e.blocked and e.id == "sys.reload_cpu":
                continue
            body = e.template
            full = f"{e.interpreter}; {body}" if e.interpreter else body
            pattern = "^" + re.escape(full).replace(r"\ ", r"\s+") + "$"
            pattern = re.sub(r"\\\{(\w+)\\\}", lambda m: f"(?P<{m.group(1)}>[A-Za-z0-9$\\-]+)", pattern)
            mm = re.match(pattern, text, re.IGNORECASE)
            if mm:
                params = {k: (int(v) if v.isdigit() else v.upper()) for k, v in mm.groupdict().items()}
                if "server_class" in params:
                    params["server_class"] = normalize_class(params["server_class"])
                return e.id, params
        return None

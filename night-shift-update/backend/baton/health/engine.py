"""Health model (MVP spec §7.2): telemetry values, baseline bands, component states with reasons, N-1."""
from __future__ import annotations

import math
from datetime import datetime

from ..core.timeutil import iso_sim
from ..sim.model import SimModel
from .n1 import compute_n1

SHORT = {"atm": "ATM", "pos": "POS", "bal": "Balance inquiry", "card": "Card maintenance"}
ORDER = {"ok": 0, "unknown": 0, "degraded": 1, "critical": 2, "down": 3}


class HealthEngine:
    def __init__(self, site: dict, rules: dict):
        self.site = site
        self.rules = rules
        self.band = tuple(rules.get("latency_band", [0.8, 1.4]))
        self.n1_every = int(rules.get("n1", {}).get("every_s", 5))
        self.n1_threshold = float(rules.get("n1", {}).get("threshold", 90.0))
        self.reset()

    def reset(self) -> None:
        self.n1: dict = {"safe": True, "worst_lost_cpu": None, "worst_survivor_cpu": None, "worst_survivor_busy": None,
                         "threshold": self.n1_threshold, "text": "N-1: waiting for data", "per_cpu": {}}
        self.critical_since: dict[int, int] = {}
        self.values: dict[str, float] = {}
        self.snapshot: dict | None = None

    # ------------------------------------------------------------ baseline

    def expected_p95(self, m: SimModel, service: str, at: datetime) -> float:
        """Fault-free model at the same sim time: expected arrivals, initial configuration, no queue."""
        svc = m.services[service]
        cfg = next(s for s in self.site["server_classes"] if s["name"] == svc.server_class)
        targets = (m.dyn.get("init_target_rho") or {})
        target = targets.get(svc.server_class, 0.87) if isinstance(targets, dict) else 0.87
        per = 1000.0 / float(cfg["service_ms"])
        a = m.expected_arrivals(service, at)
        running = max(int(cfg["numstatic"]), min(int(cfg["maxservers"]), math.ceil(a / (per * target))))
        rho = a / (running * per)
        return svc.base_latency_ms + float(cfg["service_ms"]) / (1.0 - min(rho, m.dyn["rho_cap"]))

    # ------------------------------------------------------------ per tick

    def sample(self, m: SimModel, events_per_min: float) -> dict[str, float]:
        v: dict[str, float] = {}
        for c in range(m.cpu_count):
            v[f"cpu.{c}.busy"] = round(m.cpu_busy[c], 1)
            v[f"cpu.{c}.up"] = 1.0 if m.cpu_up[c] else 0.0
        for sid in ("atm", "pos"):
            exp = self.expected_p95(m, sid, m.now)
            v[f"svc.{sid}.tps"] = round(m.svc_tps.get(sid, 0.0), 1)
            v[f"svc.{sid}.p95_ms"] = round(m.svc_p95.get(sid, 0.0), 1)
            v[f"svc.{sid}.timeout_pct"] = round(m.svc_timeout.get(sid, 0.0), 2)
            v[f"svc.{sid}.band_low"] = round(exp * self.band[0], 1)
            v[f"svc.{sid}.band_high"] = round(exp * self.band[1], 1)
        for name, sc in m.classes.items():
            v[f"sc.{name}.running"] = float(sc.running(m.tick))
            v[f"sc.{name}.max"] = float(sc.maxservers)
            v[f"sc.{name}.queued"] = float(round(sc.queued))
            v[f"sc.{name}.avg_ms"] = round(sc.avg_ms, 1)
        v["tmf.mat.fill_pct"] = round(m.tmf.fill_pct, 1)
        for vol, fill in m.volume_fill.items():
            v[f"disk.{vol}.fill_pct"] = round(fill, 1)
        v["tmf.tps"] = round(m.tmf.tps, 1)
        v["ems.rate_per_min"] = float(events_per_min)
        if m.tick % self.n1_every == 0 or self.n1["worst_lost_cpu"] is None:
            self.n1 = compute_n1(m, self.n1_threshold)
        v["n1.worst_busy"] = float(self.n1["worst_survivor_busy"] or 0.0)
        v["n1.worst_cpu"] = float(self.n1["worst_survivor_cpu"] if self.n1["worst_survivor_cpu"] is not None else -1)
        self.values = v
        return v

    def build_snapshot(self, m: SimModel) -> dict:
        v = self.values
        comps = []
        n1 = self.n1
        for c in range(m.cpu_count):
            busy = v.get(f"cpu.{c}.busy", 0.0)
            reasons = []
            at_risk = False
            if not m.cpu_up[c]:
                state = "down"
                reasons.append({"rule_id": "cpu-down", "text": f"CPU {c} is down (OMF 103)"})
                self.critical_since.pop(c, None)
            else:
                if busy >= 95.0:
                    self.critical_since.setdefault(c, m.tick)
                else:
                    self.critical_since.pop(c, None)
                if c in self.critical_since and m.tick - self.critical_since[c] >= 60:
                    state = "critical"
                    reasons.append({"rule_id": "cpu-busy-critical", "text": f"Busy {busy:.0f}% ≥ 95% for 1 min", "value": busy, "threshold": 95.0})
                elif busy >= 80.0:
                    state = "degraded"
                    reasons.append({"rule_id": "cpu-busy-high", "text": f"Busy {busy:.0f}% ≥ 80%", "value": busy, "threshold": 80.0})
                else:
                    state = "ok"
                if not n1["safe"] and n1.get("worst_survivor_cpu") == c:
                    at_risk = True
                    reasons.append({"rule_id": "n1-risk", "text": f"Would reach ~{n1['worst_survivor_busy']:.0f}% if CPU {n1['worst_lost_cpu']} is lost",
                                    "value": n1["worst_survivor_busy"], "threshold": n1["threshold"]})
            comps.append({"id": f"cpu:{c}", "type": "cpu", "name": f"CPU {c}", "state": state, "reasons": reasons,
                          "at_risk": at_risk, "metrics": {"busy": busy}})
        for name, sc in m.classes.items():
            svc = m.services[sc.service]
            run, mx, q = v[f"sc.{name}.running"], v[f"sc.{name}.max"], v[f"sc.{name}.queued"]
            p95 = m.svc_p95.get(sc.service, 0.0)
            reasons = []
            state = "ok"
            if q >= 5 and (run >= mx or p95 > svc.p95_target_ms):
                state = "critical"
            elif q >= 5 or run >= mx:
                state = "degraded"
            if q >= 5:
                reasons.append({"rule_id": "sc-queued", "text": f"{q:.0f} requests queued", "value": q, "threshold": 0})
            if run >= mx:
                reasons.append({"rule_id": "sc-at-max", "text": f"Running at MAXSERVERS ({run:.0f}/{mx:.0f})", "value": run, "threshold": mx})
            lost = sum(1 for c in range(m.cpu_count) if not m.cpu_up[c] and c in sc.cpus)
            if lost and sc.dynamic_frozen:
                reasons.append({"rule_id": "sc-lost-servers", "text": f"Lost servers on CPU {', '.join(str(c) for c in range(m.cpu_count) if not m.cpu_up[c] and c in sc.cpus)}"})
            comps.append({"id": f"sc:{name}", "type": "server_class", "name": name, "state": state, "reasons": reasons,
                          "at_risk": False, "metrics": {"running": run, "max": mx, "queued": q, "avg_ms": v[f"sc.{name}.avg_ms"],
                                                        "numstatic": float(sc.numstatic)}})
        fill = v["tmf.mat.fill_pct"]
        t_state = "critical" if fill >= 80 else "degraded" if fill >= 70 else "ok"
        t_reasons = [{"rule_id": "tmf-fill", "text": f"Audit trail {fill:.0f}% full", "value": fill, "threshold": 70.0}] if t_state != "ok" else []
        comps.append({"id": "tmf:mat", "type": "tmf", "name": "TMF audit trail (MAT)", "state": t_state, "reasons": t_reasons,
                      "at_risk": False, "metrics": {"fill_pct": fill, "overflow_pct": m.tmf.overflow_pct, "btd_pct": m.tmf.btd_pct}})
        vol_rules = (self.rules.get("states") or {}).get("volume") or {"critical": {"fill_gte": 90.0}, "degraded": {"fill_gte": 80.0}}
        for vol in m.volume_fill:
            fill = v.get(f"disk.{vol}.fill_pct", 0.0)
            start = m.volume_start.get(vol, fill)
            crit, deg = vol_rules["critical"]["fill_gte"], vol_rules["degraded"]["fill_gte"]
            d_state = "critical" if fill >= crit else "degraded" if fill >= deg else "ok"
            d_reasons = []
            if d_state != "ok":
                d_reasons.append({"rule_id": "disk-fill", "text": f"{fill:.0f}% used (alarm at {deg:.0f}%)", "value": fill, "threshold": deg})
            if fill - start >= 2.0:
                d_reasons.append({"rule_id": "disk-growth", "text": f"Grew from {start:.0f}% at {m.start:%H:%M}", "value": fill - start})
            comps.append({"id": f"vol:{vol}", "type": "volume", "name": f"Disk {vol}", "state": d_state, "reasons": d_reasons,
                          "at_risk": False, "metrics": {"fill_pct": fill, "start_pct": start, "alarm_pct": deg}})
        for sid in ("atm", "pos"):
            svc = m.services[sid]
            p95, hi, lo = v[f"svc.{sid}.p95_ms"], v[f"svc.{sid}.band_high"], v[f"svc.{sid}.band_low"]
            to = v[f"svc.{sid}.timeout_pct"]
            reasons = []
            if p95 > svc.p95_target_ms or (p95 > hi and to >= 1.0):
                state = "critical"
            elif p95 > hi:
                state = "degraded"
            else:
                state = "ok"
            if p95 > hi:
                reasons.append({"rule_id": "latency-out-of-band", "text": f"p95 {p95:.0f} ms above band {lo:.0f}–{hi:.0f} ms", "value": p95, "threshold": hi})
            if to >= 1.0:
                reasons.append({"rule_id": "timeouts", "text": f"Timeouts {to:.1f}%", "value": to, "threshold": 1.0})
            comps.append({"id": f"svc:{sid}", "type": "service", "name": svc.name, "state": state, "reasons": reasons,
                          "at_risk": False, "metrics": {"p95_ms": p95, "band_low": lo, "band_high": hi,
                                                        "target_ms": svc.p95_target_ms, "timeout_pct": to}})
        worst = max((ORDER[c["state"]] for c in comps), default=0)
        overall = ["ok", "degraded", "critical", "critical"][worst]
        if overall == "ok" and not n1["safe"]:
            overall = "degraded"
        self.snapshot = {"sim_ts": iso_sim(m.now), "overall": overall, "components": comps, "n1": dict(n1)}
        return self.snapshot

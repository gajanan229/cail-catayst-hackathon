"""What-if predictions (MVP spec §6.7, P1): deep-copy the simulator state, apply candidate actions, run
600 sim-seconds without emitting events, and return series for cpu.*.busy, svc.atm.p95_ms and svc.atm.timeout_pct."""
from __future__ import annotations

import copy

from ..core.timeutil import iso_sim
from .model import SimModel

HORIZON_S = 600
SAMPLE_S = 10


def apply(m: SimModel, catalog_id: str, params: dict) -> None:
    """Apply a catalog action to a forked model (no events, no audit: this is a prediction)."""
    if catalog_id == "tacl.suspend_process":
        m.processes[params["process"]].state = "SUSPENDED"
    elif catalog_id == "tacl.activate_process":
        m.processes[params["process"]].state = "RUNNING"
    elif catalog_id == "tacl.stop_process":
        m.processes[params["process"]].state = "STOPPED"
    elif catalog_id == "tacl.altpri_process":
        p = m.processes[params["process"]]
        base = next((x for x in m.site["processes"] if x["name"] == p.name), {}).get("demand", p.demand)
        p.priority = int(params["priority"])
        if p.is_batch:
            p.demand = float(base) * max(0.3, min(1.0, p.priority / 150.0))
    elif catalog_id == "pathcom.alter_numstatic":
        m.set_numstatic(params["server_class"], int(params["n"]))
    elif catalog_id == "pathcom.alter_maxservers":
        sc = m.classes[params["server_class"]]
        sc.maxservers = int(params["n"])
        sc.dynamic_frozen = False
    else:
        raise ValueError(f"what-if cannot model {catalog_id}")


def predict(model: SimModel, actions: list[dict], horizon_s: int = HORIZON_S, service: str = "atm") -> dict:
    """Run on a deep copy; the caller passes a copy it made on the event-loop thread."""
    m = model
    for a in actions:
        apply(m, a["catalog_id"], a.get("params") or {})
    keys = [f"svc.{service}.p95_ms", f"svc.{service}.timeout_pct"] + [f"cpu.{c}.busy" for c in range(m.cpu_count)]
    series: dict[str, list] = {k: [] for k in keys}

    def sample():
        t = iso_sim(m.now)[11:19]
        series[f"svc.{service}.p95_ms"].append([t, round(m.svc_p95.get(service, 0.0))])
        series[f"svc.{service}.timeout_pct"].append([t, round(m.svc_timeout.get(service, 0.0), 2)])
        for c in range(m.cpu_count):
            series[f"cpu.{c}.busy"].append([t, round(m.cpu_busy[c], 1)])

    sample()
    for i in range(1, horizon_s + 1):
        m.step()
        if i % SAMPLE_S == 0:
            sample()
    # keep the CPUs that matter: down CPUs drop out, the three hottest by the end stay
    up = [c for c in range(m.cpu_count) if m.cpu_up[c]]
    hot = sorted(up, key=lambda c: -series[f"cpu.{c}.busy"][-1][1])[:3]
    out = {k: v for k, v in series.items() if not k.startswith("cpu.") or int(k.split(".")[1]) in hot}
    summary = {}
    for k, v in out.items():
        summary[k] = {"from": v[0][1], "to": v[-1][1], "max": max(x[1] for x in v)}
    return {"series": out, "summary": summary, "horizon_s": horizon_s}


def fork(model: SimModel) -> SimModel:
    return copy.deepcopy(model)

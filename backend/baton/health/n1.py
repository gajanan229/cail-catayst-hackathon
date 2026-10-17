"""N-1 headroom (MVP spec §7.2): for each up CPU, move its primaries to their backups, drop its servers,
recompute busy; publish the worst survivor and its predicted busy."""
from __future__ import annotations

from ..sim.model import SimModel


def lose_cpu(model: SimModel, lost: int) -> list[float]:
    """Predicted raw busy per CPU if `lost` halted now (no dynamic restarts, same arrivals)."""
    cpu_up = list(model.cpu_up)
    cpu_up[lost] = False
    proc_cpu: dict[str, int] = {}
    takeover = dict(model.takeover_until)
    for p in model.processes.values():
        c = p.cpu
        if c == lost:
            if p.has_backup and p.backup_cpu is not None and cpu_up[p.backup_cpu]:
                c = p.backup_cpu
                takeover[c] = model.tick + model.dyn["takeover_decay_s"]
        proc_cpu[p.name] = c
    class_servers: dict[str, list[int]] = {}
    served: dict[str, float] = {}
    svc_tps: dict[str, float] = {}
    for name, sc in model.classes.items():
        cpus = [s.cpu for s in sc.servers if s.ready_at <= model.tick and s.cpu != lost and cpu_up[s.cpu]]
        class_servers[name] = cpus
        served[name] = min(sc.arrivals, len(cpus) * sc.per_server_rps)
        svc_tps[sc.service] = served[name]
    return model.compute_cpu(cpu_up, proc_cpu, class_servers, served, model.tick, takeover, svc_tps)


def compute_n1(model: SimModel, threshold: float = 90.0) -> dict:
    per_cpu: dict[str, dict[str, float]] = {}
    worst = None
    for lost in range(model.cpu_count):
        if not model.cpu_up[lost]:
            continue
        busy = lose_cpu(model, lost)
        survivors = [c for c in range(model.cpu_count) if model.cpu_up[c] and c != lost]
        if not survivors:
            continue
        hot = max(survivors, key=lambda c: busy[c])
        value = round(min(100.0, busy[hot]), 1)
        per_cpu[str(lost)] = {"survivor_cpu": hot, "survivor_busy": value}
        if worst is None or value > worst[2]:
            worst = (lost, hot, value)
    if worst is None:
        return {"safe": True, "worst_lost_cpu": None, "worst_survivor_cpu": None, "worst_survivor_busy": None,
                "threshold": threshold, "text": "N-1: not computed", "per_cpu": {}}
    lost, hot, value = worst
    safe = value < threshold
    down = [c for c in range(model.cpu_count) if not model.cpu_up[c]]
    if safe:
        text = f"N-1 safe: worst case losing CPU {lost} puts CPU {hot} at ~{value:.0f}%"
    elif down:
        text = f"N-1 unsafe: CPU {down[0]} is already down; losing CPU {lost} puts CPU {hot} at ~{value:.0f}%"
    else:
        text = f"N-1 at risk: losing CPU {lost} puts CPU {hot} at ~{value:.0f}%"
    return {"safe": safe, "worst_lost_cpu": lost, "worst_survivor_cpu": hot, "worst_survivor_busy": value,
            "threshold": threshold, "text": text, "per_cpu": per_cpu}

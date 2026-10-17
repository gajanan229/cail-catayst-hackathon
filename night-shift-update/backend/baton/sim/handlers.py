"""Simulator command handlers (MVP spec §6.6): one per catalog entry, returning utility-style text.

Layouts are simulated and stable because the parsers read them; fixtures live in data/catalog/fixtures/.
Facts are NOT returned here: the executor runs the parser on the text, as it would against a real system.
"""
from __future__ import annotations

from typing import Callable

from .engine import Simulator


def _pct(v: float) -> str:
    return f"{v:6.1f}"


def h_meas_cpu(sim: Simulator, p: dict) -> list[str]:
    m = sim.model
    out = ["CPU  STATE    BUSY-%"]
    for c in range(m.cpu_count):
        if m.cpu_up[c]:
            out.append(f"{c:3d}  UP       {_pct(m.cpu_busy[c])}")
        else:
            out.append(f"{c:3d}  DOWN          -")
    return out


def h_status_cpu(sim: Simulator, p: dict) -> list[str]:
    m = sim.model
    cpu = int(p["cpu"])
    rows = []
    proc_cpu, class_servers = m.placement()
    for proc in m.processes.values():
        if proc.cpu != cpu or proc.state == "STOPPED":
            continue
        if proc.is_batch:
            busy = proc.demand if m.batch_active(proc) else 0.0
        else:
            busy = proc.load + sum(k * m.svc_tps.get(s, 0.0) for s, k in proc.load_per_tps.items())
            if proc.role == "link_manager":
                busy += sum(w * m.dyn["link_storm_per_queued"] * sc.queued for sc in m.classes.values()
                            for lm, w in sc.link_managers.items() if lm == proc.name)
        rows.append((proc.name, proc.priority, proc.state, busy))
    for name, cpus in class_servers.items():
        n = sum(1 for c in cpus if c == cpu)
        if n:
            sc = m.classes[name]
            busy = sc.served / max(1, len(cpus)) * sc.cpu_cost * n
            rows.append((f"{name}({n})", 150, "RUNNING", busy))
    rows.sort(key=lambda r: -r[3])
    out = ["PROCESS          PRI  STATE       BUSY-%"]
    for name, pri, state, busy in rows:
        out.append(f"{name:<15} {pri:4d}  {state:<10} {_pct(busy)}")
    return out


def h_status_process(sim: Simulator, p: dict) -> list[str]:
    proc = sim.model.processes[p["process"]]
    backup = str(proc.backup_cpu) if proc.has_backup and proc.backup_cpu is not None else "-"
    return ["PROCESS   STATE       PRI  PRIMARY  BACKUP",
            f"{proc.name:<9} {proc.state:<10} {proc.priority:4d}  {proc.cpu:7d}  {backup:>6}"]


def h_status_pathmon(sim: Simulator, p: dict) -> list[str]:
    pm = sim.model.processes["$PM1"]
    backup = str(pm.backup_cpu) if pm.has_backup and pm.backup_cpu is not None else "-"
    return ["PATHMON  STATE     PRIMARY-CPU  BACKUP-CPU",
            f"$PM1     RUNNING   {pm.cpu:11d}  {backup:>10}"]


def h_status_server(sim: Simulator, p: dict) -> list[str]:
    m = sim.model
    sc = m.classes[p["server_class"]]
    running = sc.running(m.tick)
    return ["SERVER     STATE    RUNNING  NUMSTATIC  MAXSERVERS  LINKS  QUEUED  AVG-MS",
            f"{sc.name:<10} {'RUNNING':<8} {running:7d} {sc.numstatic:10d} {sc.maxservers:11d} {min(running, sc.maxlinks):6d} "
            f"{round(sc.queued):7d} {round(sc.avg_ms):7d}"]


def h_info_server(sim: Simulator, p: dict) -> list[str]:
    sc = sim.model.classes[p["server_class"]]
    cpus = "(" + ",".join(str(c) for c in sc.cpus) + ")"
    return ["SERVER     CPUS            NUMSTATIC  MAXSERVERS  MAXLINKS",
            f"{sc.name:<10} {cpus:<15} {sc.numstatic:9d} {sc.maxservers:11d} {sc.maxlinks:9d}"]


def h_stats_server(sim: Simulator, p: dict) -> list[str]:
    sc = sim.model.classes[p["server_class"]]
    mx = max(sc.p95_ms * 1.6, sc.avg_ms)
    return ["SERVER     REQ/S     AVG-MS    MAX-MS",
            f"{sc.name:<10} {sc.served:7.1f} {sc.avg_ms:9.1f} {mx:9.1f}"]


def h_status_tmf(sim: Simulator, p: dict) -> list[str]:
    t = sim.model.tmf
    return ["TMF       STATE     TPS       ABORTS/S",
            f"\\TORBANK  {t.state:<8} {t.tps:8.1f} {t.aborts_per_s:10.2f}"]


def h_status_audittrail(sim: Simulator, p: dict) -> list[str]:
    t = sim.model.tmf
    return ["TRAIL  FILE-ID   FILL-%  OVERFLOW-%  BEGIN-TRANS-DISABLE-%  DUMPS",
            f"{t.trail:<6} {t.file_id:<9} {t.fill_pct:6.1f} {t.overflow_pct:11.1f} {t.btd_pct:22.1f}  {'ENABLED' if t.dump_slow <= 1 else 'SLOW'}"]


def h_status_disk(sim: Simulator, p: dict) -> list[str]:
    m = sim.model
    vol = p["volume"]
    proc = m.processes.get(vol)
    primary_ok = proc is not None and proc.cpu == proc.primary_cpu
    path = "STARTED" if primary_ok else "BACKUP"
    return ["VOLUME    HALF  PATH-STATE  NOTE",
            f"{vol:<9} -P    STARTED     {'' if primary_ok else 'PRIMARY CPU INACCESSIBLE'}".rstrip(),
            f"{vol:<9} -M    STARTED     {'' if primary_ok else 'SERVED BY BACKUP CPU ' + str(proc.cpu)}".rstrip(),
            f"PROCESS PAIR: {path}"]


VOLUME_MB = 1_048_576   # every simulated volume is 1 TB


def h_disk_space(sim: Simulator, p: dict) -> list[str]:
    m = sim.model
    vol = p["volume"]
    used_pct = m.volume_fill.get(vol, 0.0)
    used = round(VOLUME_MB * used_pct / 100.0)
    rate = 0.0
    for proc in m.processes.values():
        if proc.log_volume == vol and m.batch_active(proc):
            rate += proc.log_pct_per_min
    return ["VOLUME    CAPACITY-MB  USED-MB  FREE-MB  USED-%  GROWTH-%/MIN",
            f"{vol:<9} {VOLUME_MB:11d} {used:8d} {VOLUME_MB - used:8d} {used_pct:7.1f} {rate:+13.2f}"]


def h_ack_tacl(sim: Simulator, catalog_id: str, p: dict) -> list[str]:
    name = p["process"]
    if catalog_id == "tacl.suspend_process":
        sim.set_process_state(name, "SUSPENDED")
        return [f"PROCESS {name} SUSPENDED"]
    if catalog_id == "tacl.activate_process":
        sim.set_process_state(name, "RUNNING")
        return [f"PROCESS {name} ACTIVATED"]
    if catalog_id == "tacl.stop_process":
        sim.set_process_state(name, "STOPPED")
        return [f"PROCESS {name} STOPPED"]
    if catalog_id == "tacl.altpri_process":
        prev = sim.altpri(name, int(p["priority"]))
        return [f"PROCESS {name} PRIORITY {int(p['priority'])} (WAS {prev})"]
    raise KeyError(catalog_id)


def h_ack_pathcom(sim: Simulator, catalog_id: str, p: dict) -> list[str]:
    cls = p["server_class"]
    n = int(p["n"])
    sc = sim.model.classes[cls]
    if catalog_id == "pathcom.alter_numstatic":
        if n > sc.maxservers:
            return [f"*ERROR* 2049 NUMSTATIC EXCEEDS MAXSERVERS"]
        result = sim.alter_numstatic(cls, n)
        started = result["started_on"]
        lines = [f"SERVER {cls} ALTERED: NUMSTATIC {n} (WAS {result['previous']})"]
        if started:
            cpus = ",".join(str(c) for c in sorted(set(started)))
            lines.append(f"{len(started)} SERVERS STARTING ON CPUS {cpus}")
        return lines
    if catalog_id == "pathcom.alter_maxservers":
        if n < sc.numstatic:
            return [f"*ERROR* 2049 NUMSTATIC EXCEEDS MAXSERVERS"]
        prev = sim.alter_maxservers(cls, n)
        return [f"SERVER {cls} ALTERED: MAXSERVERS {n} (WAS {prev})"]
    raise KeyError(catalog_id)


READ_HANDLERS: dict[str, Callable[[Simulator, dict], list[str]]] = {
    "meas.cpu_busy": h_meas_cpu,
    "tacl.status_cpu": h_status_cpu,
    "tacl.status_process": h_status_process,
    "pathcom.status_pathmon": h_status_pathmon,
    "pathcom.status_server": h_status_server,
    "pathcom.info_server": h_info_server,
    "pathcom.stats_server": h_stats_server,
    "tmfcom.status_tmf": h_status_tmf,
    "tmfcom.status_audittrail": h_status_audittrail,
    "scf.status_disk": h_status_disk,
    "dsap.disk_space": h_disk_space,
}


def run_handler(sim: Simulator, catalog_id: str, params: dict) -> list[str]:
    if catalog_id in READ_HANDLERS:
        return READ_HANDLERS[catalog_id](sim, params)
    if catalog_id.startswith("tacl."):
        return h_ack_tacl(sim, catalog_id, params)
    if catalog_id.startswith("pathcom.alter"):
        return h_ack_pathcom(sim, catalog_id, params)
    raise KeyError(f"no simulator handler for {catalog_id}")

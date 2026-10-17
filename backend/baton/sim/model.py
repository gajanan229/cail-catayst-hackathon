"""\\TORBANK simulator state and dynamics (MVP spec §6.3). One tick = one sim-second.

Calibration targets are in §6.2; constants live in data/site/torbank.yaml under `dynamics`.
The CPU-load computation is a pure function of the state so N-1 can reuse it on hypothetical copies.
"""
from __future__ import annotations

import copy
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..core.timeutil import hhmm_to_minutes, minutes_of_day

DEFAULT_DYNAMICS = {
    "noise_pct": 5.0,           # ±5% arrival noise (smoothed AR(1))
    "noise_alpha": 0.08,
    "rho_cap": 0.965,           # p95 ≈ service / (1 − min(rho, cap)) + queue wait
    "queue_k": 2600.0,          # standing queue Q* = queue_k × max(0, rho − queue_rho0)
    "queue_rho0": 1.0,
    "queue_soft_k": 140.0,      # small queue near saturation: queue_soft_k × max(0, rho − 0.94) / 0.06
    "queue_tau_s": 12.0,        # queue relaxes toward Q* with this time constant
    "timeout_k": 55.0,          # timeout % = timeout_k × max(0, rho − timeout_rho0)
    "timeout_rho0": 0.985,
    "stretch_start": 80.0,      # service time stretches above this host CPU busy
    "stretch_k": 0.6,
    "takeover_overhead": 6.0,   # extra busy on the backup CPU after a takeover
    "takeover_decay_s": 900.0,
    "backup_load": 0.3,         # a backup process costs a little on its CPU
    "dyn_start_rho": 0.93,      # PATHMON starts a dynamic server when rho exceeds this ...
    "dyn_stop_rho": 0.70,       # ... and stops one below this (never below NUMSTATIC)
    "dyn_interval_s": 10,
    "queue_soft_rho0": 0.96,
    "link_storm_per_queued": 0.13,
    "pressure_tau_s": 360.0,
    "pressure_p95_k": 0.5,
    "pressure_timeout_k": 3.5,
    "server_start_s": 6,        # a new server takes this long to become ready
}


@dataclass
class Process:
    name: str
    role: str
    primary_cpu: int
    backup_cpu: int | None
    cpu: int                      # where the primary runs now
    protected: bool = False
    load: float = 0.0
    load_per_tps: dict[str, float] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    priority: int = 150
    state: str = "RUNNING"        # RUNNING | SUSPENDED | STOPPED
    has_backup: bool = True
    demand: float = 0.0
    window: tuple[float, float] | None = None
    calendar: list[str] | None = None
    audit_per_min: float = 0.0
    description: str = ""

    @property
    def is_batch(self) -> bool:
        return "batch" in self.tags


@dataclass
class Server:
    cpu: int
    ready_at: float = 0.0         # tick when the server becomes ready
    static: bool = True


@dataclass
class ServerClass:
    name: str
    service: str
    cpus: list[int]
    numstatic: int
    maxservers: int
    maxlinks: int
    service_ms: float
    cpu_cost: float
    tag: str
    servers: list[Server] = field(default_factory=list)
    queued: float = 0.0
    p95_ms: float = 0.0
    avg_ms: float = 0.0
    timeout_pct: float = 0.0
    rho: float = 0.0
    arrivals: float = 0.0
    served: float = 0.0
    dynamic_frozen: bool = False
    last_dyn_tick: int = -999
    requests_total: float = 0.0
    link_managers: dict[str, float] = field(default_factory=dict)
    pressure: float = 0.0
    max_ms_window: float = 0.0
    state: str = "RUNNING"

    def running(self, tick: float) -> int:
        return sum(1 for s in self.servers if s.ready_at <= tick)

    def servers_on(self, cpu: int, tick: float) -> int:
        return sum(1 for s in self.servers if s.cpu == cpu and s.ready_at <= tick)

    @property
    def per_server_rps(self) -> float:
        return 1000.0 / self.service_ms


@dataclass
class Service:
    id: str
    name: str
    server_class: str
    p95_target_ms: float
    base_latency_ms: float
    base_tps: float


@dataclass
class Tmf:
    trail: str
    file_id: str
    overflow_pct: float
    btd_pct: float
    fill_per_ktps_min: float
    dump_every_s: int
    dump_drain_pct: float
    fill_pct: float
    audit_factor: float = 1.0
    dump_slow: float = 1.0
    last_dump_tick: int = 0
    tps: float = 0.0
    aborts_per_s: float = 0.0
    state: str = "STARTED"
    fill_history: list[tuple[int, float]] = field(default_factory=list)


class SimModel:
    """Mutable simulator state plus the dynamics step. Owns no I/O; the emitter reads it to make events."""

    def __init__(self, site: dict, scenario: dict, seed: int):
        self.site = site
        self.scenario = scenario
        self.seed = seed
        self.dyn = {**DEFAULT_DYNAMICS, **(site.get("dynamics") or {})}
        self.rng_arrivals = random.Random(seed * 1000 + 1)
        self.rng_noise = random.Random(seed * 1000 + 3)
        self.tick = 0
        self.start: datetime = datetime.fromisoformat(scenario["start"])
        self.now: datetime = self.start
        self.cpu_count = int(site["cpus"]["count"])
        self.base_overhead = float(site["cpus"]["base_overhead"])
        self.cpu_overhead = list(site["cpus"].get("overhead") or [0.0] * int(site["cpus"]["count"]))
        self.cpu_up = [True] * self.cpu_count
        self.cpu_busy = [0.0] * self.cpu_count
        self.cpu_raw = [0.0] * self.cpu_count
        self.takeover_until: dict[int, float] = {}
        self.calendar = self._calendar_for(self.start)
        self.scenario_load = (scenario.get("load_multiplier") or {})
        self.processes: dict[str, Process] = {}
        for p in site["processes"]:
            window = None
            if p.get("window"):
                window = (hhmm_to_minutes(p["window"][0]), hhmm_to_minutes(p["window"][1]))
            self.processes[p["name"]] = Process(
                name=p["name"], role=p["role"], primary_cpu=p["primary_cpu"], backup_cpu=p.get("backup_cpu"),
                cpu=p["primary_cpu"], protected=bool(p.get("protected")), load=float(p.get("load", 0.0)),
                load_per_tps=dict(p.get("load_per_tps") or {}), tags=list(p.get("tags") or []),
                priority=int(p.get("priority", 150)), has_backup=p.get("backup_cpu") is not None,
                demand=float(p.get("demand", 0.0)), window=window, calendar=p.get("calendar"),
                audit_per_min=float(p.get("audit_per_min", 0.0)), description=p.get("description", ""),
            )
        self.services: dict[str, Service] = {
            s["id"]: Service(id=s["id"], name=s["name"], server_class=s["server_class"],
                             p95_target_ms=float(s["p95_target_ms"]), base_latency_ms=float(s.get("base_latency_ms", 0)),
                             base_tps=float(s["base_tps"]))
            for s in site["services"]
        }
        self.classes: dict[str, ServerClass] = {}
        for sc in site["server_classes"]:
            self.classes[sc["name"]] = ServerClass(
                name=sc["name"], service=sc["service"], cpus=list(sc["cpus"]), numstatic=int(sc["numstatic"]),
                maxservers=int(sc["maxservers"]), maxlinks=int(sc.get("maxlinks", sc["maxservers"])),
                service_ms=float(sc["service_ms"]), cpu_cost=float(sc["cpu_cost"]), tag=sc.get("tag", "normal"),
                link_managers=dict(sc.get("link_managers") or {}),
            )
        t = site["tmf"]
        init = scenario.get("initial") or {}
        self.tmf = Tmf(trail=t["trail"], file_id=t["file_id"], overflow_pct=float(t["overflow_pct"]),
                       btd_pct=float(t["btd_pct"]), fill_per_ktps_min=float(t["fill_per_ktps_min"]),
                       dump_every_s=int(t["dump_every_s"]), dump_drain_pct=float(t["dump_drain_pct"]),
                       fill_pct=float(init.get("tmf_fill_pct", t["initial_fill_pct"])))
        self.noise = {sid: 0.0 for sid in self.services}
        self.arrivals: dict[str, float] = {}
        self.svc_p95: dict[str, float] = {}
        self.svc_timeout: dict[str, float] = {}
        self.svc_tps: dict[str, float] = {}
        self.svc_band: dict[str, tuple[float, float]] = {}
        self.overrides: dict[str, Any] = {}
        self._init_servers()

    # ------------------------------------------------------------------ setup

    def _calendar_for(self, dt: datetime) -> dict:
        cal = self.site.get("calendar") or {}
        return cal.get(dt.strftime("%Y-%m-%d")) or cal.get("default") or {"type": "normal", "multipliers": {}}

    def demand_multiplier(self, service: str, dt: datetime) -> float:
        curve = self.site["demand_curve"]
        pts = sorted((hhmm_to_minutes(k), float(v)) for k, v in curve.items())
        m = minutes_of_day(dt)
        shape = pts[-1][1]
        for (m0, v0), (m1, v1) in zip(pts, pts[1:]):
            if m0 <= m <= m1:
                shape = v0 + (v1 - v0) * ((m - m0) / (m1 - m0) if m1 > m0 else 0)
                break
        cal = self._calendar_for(dt).get("multipliers", {}).get(service, 1.0)
        return shape * cal * float(self.scenario_load.get(service, 1.0))

    def expected_arrivals(self, service: str, dt: datetime) -> float:
        return self.services[service].base_tps * self.demand_multiplier(service, dt)

    def _init_servers(self) -> None:
        """Start NUMSTATIC servers round-robin, then the dynamic servers the starting load needs."""
        for sc in self.classes.values():
            sc.servers = []
            for i in range(sc.numstatic):
                sc.servers.append(Server(cpu=sc.cpus[i % len(sc.cpus)], static=True))
            svc = self.services[sc.service]
            a = self.expected_arrivals(svc.id, self.now)
            target = self.dyn.get("init_target_rho", {}).get(sc.name, 0.87) if isinstance(self.dyn.get("init_target_rho"), dict) else 0.87
            need = math.ceil(a / (sc.per_server_rps * target))
            extra = max(0, min(sc.maxservers, need) - sc.numstatic)
            for i in range(extra):
                sc.servers.append(Server(cpu=sc.cpus[(sc.numstatic + i) % len(sc.cpus)], static=False))
            sc.last_dyn_tick = 0

    # ------------------------------------------------------------------ helpers

    def batch_active(self, p: Process, dt: datetime | None = None) -> bool:
        dt = dt or self.now
        if not p.is_batch or p.state != "RUNNING" or not self.cpu_up[p.cpu]:
            return False
        if p.calendar and self._calendar_for(dt).get("type") not in p.calendar:
            return False
        if p.window:
            m = minutes_of_day(dt)
            return p.window[0] <= m <= p.window[1]
        return True

    def least_busy_cpu(self, cpus: list[int], extra: dict[int, float] | None = None) -> int:
        extra = extra or {}
        candidates = [c for c in cpus if self.cpu_up[c]]
        return min(candidates, key=lambda c: (self.cpu_busy[c] + extra.get(c, 0.0), c))

    # ------------------------------------------------------------------ CPU load (pure)

    def compute_cpu(self, cpu_up: list[bool], proc_cpu: dict[str, int], class_servers: dict[str, list[int]],
                    served: dict[str, float], tick: float, takeover: dict[int, float],
                    svc_tps: dict[str, float] | None = None, queued: dict[str, float] | None = None) -> list[float]:
        """Raw CPU busy per CPU (may exceed 100) for a given placement and served load."""
        busy = [self.base_overhead + self.cpu_overhead[c] if cpu_up[c] else 0.0 for c in range(self.cpu_count)]
        queued = {n: sc.queued for n, sc in self.classes.items()} if queued is None else queued
        svc_tps = self.svc_tps if svc_tps is None else svc_tps
        for p in self.processes.values():
            c = proc_cpu.get(p.name, p.cpu)
            if c is None or not cpu_up[c] or p.state == "STOPPED":
                continue
            if p.is_batch:
                if self.batch_active(p) and p.state == "RUNNING":
                    busy[c] += p.demand
                continue
            busy[c] += p.load
            if p.role == "link_manager":
                for sc in self.classes.values():
                    w = sc.link_managers.get(p.name)
                    if w:
                        busy[c] += w * self.dyn["link_storm_per_queued"] * queued.get(sc.name, 0.0)
            for svc, k in p.load_per_tps.items():
                busy[c] += k * svc_tps.get(svc, 0.0)
            if p.has_backup and p.backup_cpu is not None and c == p.primary_cpu and cpu_up[p.backup_cpu]:
                busy[p.backup_cpu] += self.dyn["backup_load"]
        for name, cpus in class_servers.items():
            sc = self.classes[name]
            n = len(cpus)
            if n == 0:
                continue
            per_server = served.get(name, 0.0) / n
            for c in cpus:
                if cpu_up[c]:
                    busy[c] += per_server * sc.cpu_cost
        for c, until in takeover.items():
            if cpu_up[c] and until > tick:
                remaining = (until - tick) / self.dyn["takeover_decay_s"]
                busy[c] += self.dyn["takeover_overhead"] * min(1.0, 0.4 + remaining)
        return busy

    def placement(self) -> tuple[dict[str, int], dict[str, list[int]]]:
        proc_cpu = {p.name: p.cpu for p in self.processes.values()}
        class_servers = {name: [s.cpu for s in sc.servers if s.ready_at <= self.tick] for name, sc in self.classes.items()}
        return proc_cpu, class_servers

    # ------------------------------------------------------------------ dynamics

    def step(self) -> None:
        self.tick += 1
        self.now = self._advance()
        self._arrivals()
        self._classes()
        self._cpu()
        self._tmf()
        self._dynamic_servers()

    def _advance(self) -> datetime:
        from datetime import timedelta
        return self.start + timedelta(seconds=self.tick)

    def _arrivals(self) -> None:
        sigma = self.dyn["noise_pct"] / 100.0
        alpha = self.dyn["noise_alpha"]
        for sid, svc in self.services.items():
            self.noise[sid] = (1 - alpha) * self.noise[sid] + alpha * self.rng_arrivals.gauss(0.0, sigma * 2.2)
            self.noise[sid] = max(-sigma, min(sigma, self.noise[sid]))
            self.arrivals[sid] = self.expected_arrivals(sid, self.now) * (1.0 + self.noise[sid])

    def class_metrics(self, sc: ServerClass, arrivals: float, running: int, stretch: float, queued: float) -> dict:
        d = self.dyn
        cap = running * sc.per_server_rps
        rho = arrivals / cap if cap > 0 else 9.99
        q_target = 0.0
        r0 = d["queue_soft_rho0"]
        if rho >= r0:
            q_target += d["queue_soft_k"] * min(1.0, (rho - r0) / (1.0 - r0))
        if rho > d["queue_rho0"]:
            q_target += d["queue_k"] * (rho - d["queue_rho0"])
        if cap > 0:
            q_target = min(q_target, arrivals * 2.0)     # requests waiting > 2 s time out
        else:
            q_target = arrivals * 2.0
        wait_ms = 1000.0 * queued / cap if cap > 0 else 2000.0
        svc_ms = sc.service_ms * stretch
        boost = 1.0 + d["pressure_p95_k"] * sc.pressure
        p95 = (svc_ms / (1.0 - min(rho, d["rho_cap"])) + min(wait_ms, 2000.0)) * boost
        timeout = d["timeout_k"] * max(0.0, rho - d["timeout_rho0"]) + d["pressure_timeout_k"] * sc.pressure
        if cap <= 0:
            timeout = 100.0
        avg = svc_ms / (1.0 - min(rho, d["rho_cap"])) * 0.55 + min(wait_ms, 2000.0)
        served = min(arrivals, cap)
        return {"cap": cap, "rho": rho, "q_target": q_target, "p95": p95, "timeout": min(timeout, 100.0),
                "avg": avg, "served": served}

    def stretch_for(self, sc: ServerClass) -> float:
        running = [s for s in sc.servers if s.ready_at <= self.tick and self.cpu_up[s.cpu]]
        if not running:
            return 1.0
        d = self.dyn
        total = 0.0
        for s in running:
            b = self.cpu_busy[s.cpu]
            raw = self.cpu_raw[s.cpu]
            total += 1.0 + d["stretch_k"] * max(0.0, b - d["stretch_start"]) / 20.0 + 1.5 * max(0.0, raw - 100.0) / 100.0
        return total / len(running)

    def _classes(self) -> None:
        tau = self.dyn["queue_tau_s"]
        for sc in self.classes.values():
            svc = self.services[sc.service]
            a = self.arrivals[svc.id]
            running = sc.running(self.tick)
            m = self.class_metrics(sc, a, running, self.stretch_for(sc), sc.queued)
            sc.queued += (m["q_target"] - sc.queued) / tau
            if m["rho"] > 1.0:
                sc.pressure = min(1.0, sc.pressure + 1.0 / self.dyn["pressure_tau_s"])
            else:
                sc.pressure = max(0.0, sc.pressure - 1.0 / 30.0)
            if sc.queued < 0.5 and m["q_target"] == 0:
                sc.queued = 0.0
            sc.arrivals, sc.rho, sc.served = a, m["rho"], m["served"]
            sc.p95_ms = svc.base_latency_ms + m["p95"]
            sc.avg_ms = svc.base_latency_ms * 0.6 + m["avg"]
            sc.timeout_pct = m["timeout"]
            sc.requests_total += m["served"]
            self.svc_p95[svc.id] = sc.p95_ms
            self.svc_timeout[svc.id] = sc.timeout_pct
            self.svc_tps[svc.id] = m["served"]

    def _cpu(self) -> None:
        proc_cpu, class_servers = self.placement()
        served = {name: sc.served for name, sc in self.classes.items()}
        raw = self.compute_cpu(self.cpu_up, proc_cpu, class_servers, served, self.tick, self.takeover_until)
        self.cpu_raw = raw
        noise = [self.rng_noise.gauss(0.0, 0.35) for _ in range(self.cpu_count)]
        self.cpu_busy = [0.0 if not self.cpu_up[c] else max(0.0, min(100.0, raw[c] + noise[c])) for c in range(self.cpu_count)]

    def _tmf(self) -> None:
        t = self.tmf
        tps = sum(self.svc_tps.values())
        t.tps = tps
        t.aborts_per_s = 0.0004 * tps + sum(sc.timeout_pct / 100 * sc.arrivals for sc in self.classes.values()) * 0.1
        per_s = t.fill_per_ktps_min * (tps / 1000.0) / 60.0
        batch_audit = sum(p.audit_per_min for p in self.processes.values() if p.audit_per_min and self.batch_active(p)) / 60.0
        # the S2 fault multiplies the month-end batch's audit generation, not ordinary transaction audit (§6.4)
        t.fill_pct += per_s + batch_audit * t.audit_factor
        interval = int(t.dump_every_s * t.dump_slow)
        if self.tick - t.last_dump_tick >= interval:
            t.last_dump_tick = self.tick
            floor = float(self.site["tmf"].get("dump_floor_pct", 5.0))
            t.fill_pct = max(min(floor, t.fill_pct), t.fill_pct - t.dump_drain_pct / t.dump_slow)
        t.fill_pct = min(100.0, t.fill_pct)
        if self.tick % 5 == 0:
            t.fill_history.append((self.tick, t.fill_pct))
            if len(t.fill_history) > 400:
                t.fill_history = t.fill_history[-400:]

    def _dynamic_servers(self) -> None:
        d = self.dyn
        for sc in self.classes.values():
            if sc.dynamic_frozen or self.tick - sc.last_dyn_tick < d["dyn_interval_s"]:
                continue
            total = len(sc.servers)
            if sc.rho > d["dyn_start_rho"] and total < sc.maxservers:
                cpu = self.least_busy_cpu(sc.cpus)
                sc.servers.append(Server(cpu=cpu, ready_at=self.tick + d["server_start_s"], static=False))
                sc.last_dyn_tick = self.tick
            elif sc.rho < d["dyn_stop_rho"] and total > sc.numstatic:
                dyn = [s for s in sc.servers if not s.static]
                if dyn:
                    sc.servers.remove(dyn[-1])
                    sc.last_dyn_tick = self.tick
            if total > sc.maxservers:
                sc.servers = sc.servers[: sc.maxservers]

    # ------------------------------------------------------------------ faults and actions

    def halt_cpu(self, cpu: int) -> dict:
        """CPU halt: primaries switch to their backups, servers on the CPU die, batches on it stop."""
        self.cpu_up[cpu] = False
        moved, lost, stopped = [], {}, []
        for p in self.processes.values():
            if p.cpu == cpu:
                if p.has_backup and p.backup_cpu is not None and self.cpu_up[p.backup_cpu]:
                    p.cpu = p.backup_cpu
                    p.has_backup = False
                    moved.append(p.name)
                    self.takeover_until[p.backup_cpu] = self.tick + self.dyn["takeover_decay_s"]
                else:
                    if p.is_batch or p.role == "link_manager":
                        p.state = "STOPPED"
                    stopped.append(p.name)
            elif p.backup_cpu == cpu:
                p.has_backup = False
        for sc in self.classes.values():
            before = len(sc.servers)
            sc.servers = [s for s in sc.servers if s.cpu != cpu]
            if len(sc.servers) != before:
                lost[sc.name] = before - len(sc.servers)
                sc.dynamic_frozen = True     # PATHMON does not restart them elsewhere by itself (§6.3.7)
        return {"cpu": cpu, "moved": moved, "lost_servers": lost, "stopped": stopped}

    def set_audit_pressure(self, factor: float) -> None:
        self.tmf.audit_factor = factor
        self.tmf.dump_slow = 2.0

    def set_maxservers(self, class_name: str, value: int) -> dict:
        sc = self.classes[class_name]
        prev = {"maxservers": sc.maxservers, "numstatic": sc.numstatic}
        sc.maxservers = value
        if sc.numstatic > value:
            sc.numstatic = max(1, value - 4)
        if len(sc.servers) > value:
            sc.servers = sc.servers[:value]
        return prev

    def set_numstatic(self, class_name: str, n: int) -> dict:
        """ALTER SERVER ..., NUMSTATIC n. New servers land on the least-busy CPUs in the class's list."""
        sc = self.classes[class_name]
        prev = sc.numstatic
        sc.numstatic = n
        started: list[int] = []
        extra: dict[int, float] = {}
        # each new server's eventual share of the class load (the load spreads over n servers)
        per_server_load = (sc.arrivals / max(1, n)) * sc.cpu_cost
        statics = [s for s in sc.servers if s.static]
        # dynamic servers become static first
        for s in sc.servers:
            if not s.static and len(statics) < n:
                s.static = True
                statics.append(s)
        while len([s for s in sc.servers if s.static]) < n and len(sc.servers) < sc.maxservers:
            cpu = self.least_busy_cpu(sc.cpus, extra)
            extra[cpu] = extra.get(cpu, 0.0) + per_server_load
            sc.servers.append(Server(cpu=cpu, ready_at=self.tick + self.dyn["server_start_s"], static=True))
            started.append(cpu)
        while len([s for s in sc.servers if s.static]) > n:
            for s in reversed(sc.servers):
                if s.static:
                    sc.servers.remove(s)
                    break
        return {"previous": prev, "started_on": started}

    def snapshot_state(self) -> "SimModel":
        """Deep copy for what-if and N-1 (RNG included so forks are deterministic)."""
        return copy.deepcopy(self)

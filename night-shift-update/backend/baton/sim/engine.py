"""Simulator engine: scenario loading, steps, faults, operator actions, emitted lines (MVP spec §6).

The runtime's clock loop calls `step()` once per sim-second. Everything is deterministic for a given
scenario, seed and sequence of actions (separate RNG streams for arrivals, chatter and noise).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from ..core.timeutil import hhmm_to_minutes, iso_sim, minutes_of_day
from .ems_emitter import Emitter
from .model import SimModel

SPEEDS = (1, 2, 4, 8, 16)
RESTART_AFTER_S = (150, 330)   # sim-seconds of starvation before the first and second server restart


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@dataclass
class FaultRecord:
    fault: str
    params: dict
    injected_sim_ts: str


@dataclass
class SimStatus:
    scenario: str | None = None
    profile: str = "demo"
    seed: int = 42
    speed: int = 4
    paused: bool = True
    running: bool = False
    faults: list[FaultRecord] = field(default_factory=list)


class Simulator:
    def __init__(self, data_dir: Path, chatter_scale: float = 1.0):
        self.data_dir = data_dir
        self.site = load_yaml(data_dir / "site" / "torbank.yaml")
        self.messages = load_yaml(data_dir / "rules" / "ems_messages.yaml")
        self.scenarios = {p.stem: load_yaml(p) for p in sorted((data_dir / "scenarios").glob("S*.yaml"))}
        self.chatter_scale = chatter_scale
        self.status = SimStatus()
        self.model: SimModel | None = None
        self.emitter: Emitter | None = None
        self.scenario: dict | None = None
        self.pending_lines: list[str] = []
        self.steps_done: set[int] = set()
        self.server_seq = 100
        self.starved_since: dict[int, int] = {}
        self.restarts_done = 0

    # ------------------------------------------------------------ lifecycle

    @property
    def system(self) -> str:
        return self.site["system"]

    def load(self, scenario_id: str, profile: str = "demo", seed: int | None = None, speed: int | None = None) -> None:
        if scenario_id not in self.scenarios:
            raise KeyError(scenario_id)
        sc = self.scenarios[scenario_id]
        prof = (sc.get("profiles") or {}).get(profile, {})
        seed = int(seed if seed is not None else sc.get("seed", 42))
        self.scenario = sc
        self.model = SimModel(self.site, sc, seed)
        chatter = sc.get("chatter") or {}
        self.emitter = Emitter(self.system, self.messages, seed, float(chatter.get("per_min", 300)) * self.chatter_scale,
                               bool(chatter.get("injection_test", True)))
        default_speed = int(prof.get("speed", sc.get("speed", 4)))
        self.status = SimStatus(scenario=scenario_id, profile=profile, seed=seed,
                                speed=self._clamp_speed(speed or default_speed), paused=False, running=True)
        self.pending_lines = []
        self.steps_done = set()
        self.server_seq = 100
        self.starved_since = {}
        self.restarts_done = 0

    def unload(self) -> None:
        self.model = None
        self.emitter = None
        self.scenario = None
        self.status = SimStatus()
        self.pending_lines = []

    @staticmethod
    def _clamp_speed(speed: int) -> int:
        return min(SPEEDS, key=lambda s: abs(s - int(speed)))

    @property
    def profile_cfg(self) -> dict:
        if not self.scenario:
            return {}
        return (self.scenario.get("profiles") or {}).get(self.status.profile, {})

    @property
    def now(self) -> datetime | None:
        return self.model.now if self.model else None

    def state_dict(self) -> dict:
        return {
            "scenario": self.status.scenario,
            "scenario_name": self.scenario.get("name") if self.scenario else None,
            "profile": self.status.profile,
            "seed": self.status.seed,
            "sim_ts": iso_sim(self.now),
            "speed": self.status.speed,
            "paused": self.status.paused,
            "running": self.status.running,
            "active_faults": [f.__dict__ for f in self.status.faults],
            "calendar": self.model.calendar.get("type") if self.model else None,
        }

    # ------------------------------------------------------------ tick

    def step(self) -> list[str]:
        """Advance one sim-second; return the EMS lines emitted during it."""
        m = self.model
        assert m is not None and self.emitter is not None
        m.step()
        lines = self.pending_lines
        self.pending_lines = []
        lines += self._scenario_steps()
        lines += self._starvation_restarts()
        lines += self.emitter.tick(m)
        return lines

    def _starvation_restarts(self) -> list[str]:
        """Servers starved by a higher-priority loop stop answering; after RESTART_AFTER_S of starvation
        one is stopped and restarted on the same CPU (OMF 608, then PATHWAY 1043). At most two."""
        m = self.model
        starved = m.starved_cpus()
        out: list[str] = []
        for cpu in list(self.starved_since):
            if cpu not in starved:
                self.starved_since.pop(cpu)
        for cpu in sorted(starved):
            since = self.starved_since.setdefault(cpu, m.tick)
            due = RESTART_AFTER_S[self.restarts_done] if self.restarts_done < len(RESTART_AFTER_S) else None
            if due is not None and m.tick - since >= due:
                hit = m.restart_server_on(cpu, self.restarts_done)
                if hit:
                    self.restarts_done += 1
                    self.server_seq += 1
                    out += self.emitter.server_restart(m, hit[0], f"$S{self.server_seq:03d}", cpu)
        return out

    def _scenario_steps(self) -> list[str]:
        out: list[str] = []
        m = self.model
        for i, st in enumerate(self.scenario.get("steps") or []):
            if i in self.steps_done:
                continue
            if st.get("profile") and st["profile"] != self.status.profile:
                continue
            if minutes_of_day(m.now) >= hhmm_to_minutes(st["at"]):
                self.steps_done.add(i)
                out += self.inject(st["fault"], st.get("params") or {}, queue=False)
        return out

    # ------------------------------------------------------------ faults

    def inject(self, fault: str, params: dict, queue: bool = True) -> list[str]:
        m = self.model
        if m is None:
            raise RuntimeError("simulator not running")
        lines: list[str] = []
        if fault == "cpu_halt":
            cpu = int(params.get("cpu", 3))
            if not m.cpu_up[cpu]:
                return []
            result = m.halt_cpu(cpu)
            lines = self.emitter.cpu_halt(m, result)
        elif fault == "runaway_batch":
            name = params.get("process", "$RECN1")
            p = m.processes[name]
            if p.state == "RUNNING" and p.demand > 0:
                return []
            result = m.start_runaway(name)
            lines = self.emitter.batch_started(m, result)
            self.starved_since = {}
            self.restarts_done = 0
        elif fault == "audit_pressure":
            m.set_audit_pressure(float(params.get("factor", 3.0)))
        elif fault == "maxservers_change":
            cls = params.get("server_class", "ATM-AUTH")
            value = int(params.get("value", 12))
            prev = m.set_maxservers(cls, value)
            sc = m.classes[cls]
            text = (f"ALTER SERVER {cls}, NUMSTATIC {sc.numstatic}, MAXSERVERS {value} "
                    f"(was NUMSTATIC {prev['numstatic']}, MAXSERVERS {prev['maxservers']}) BY CHANGE CR-4471")
            lines = self.emitter.pathcom_alter(m, "$PM1", text, [])
        else:
            raise ValueError(f"unknown fault {fault}")
        self.status.faults.append(FaultRecord(fault=fault, params=params, injected_sim_ts=iso_sim(m.now)))
        if queue:
            self.pending_lines += lines
            return lines
        return lines

    # ------------------------------------------------------------ operator actions (via command handlers)

    def set_process_state(self, name: str, state: str) -> tuple[str, str]:
        m = self.model
        p = m.processes[name]
        prev = p.state
        p.state = state
        self.pending_lines += self.emitter.process_state(m, name, state, prev)
        return prev, state

    def altpri(self, name: str, priority: int) -> int:
        p = self.model.processes[name]
        prev = p.priority
        p.priority = priority
        if p.is_batch:
            # lower priority yields CPU to the transaction servers: model as reduced effective demand
            base = p.base_demand if p.base_demand is not None else \
                next(x for x in self.site["processes"] if x["name"] == name).get("demand", p.demand)
            share = max(0.3, min(1.0, priority / 150.0))
            p.demand = float(base) * share
            if p.base_log_pct_per_min:
                p.log_pct_per_min = p.base_log_pct_per_min * share
        return prev

    def alter_numstatic(self, cls: str, n: int) -> dict:
        m = self.model
        result = m.set_numstatic(cls, n)
        started = []
        for cpu in result["started_on"]:
            self.server_seq += 1
            started.append((f"SERVER {cls} ($S{self.server_seq:03d} CPU {cpu})", cpu))
        text = f"ALTER SERVER {cls}, NUMSTATIC {n} (was {result['previous']})"
        self.pending_lines += self.emitter.pathcom_alter(m, "$PM1", text, started)
        return result

    def alter_maxservers(self, cls: str, n: int) -> int:
        m = self.model
        sc = m.classes[cls]
        prev = sc.maxservers
        sc.maxservers = n
        sc.dynamic_frozen = False if n > prev else sc.dynamic_frozen
        text = f"ALTER SERVER {cls}, MAXSERVERS {n} (was {prev})"
        self.pending_lines += self.emitter.pathcom_alter(m, "$PM1", text, [])
        return prev

    # ------------------------------------------------------------ inventory

    def inventory(self) -> dict:
        m = self.model
        return {
            "cpus": list(range(m.cpu_count)) if m else list(range(int(self.site["cpus"]["count"]))),
            "processes": [p["name"] for p in self.site["processes"]],
            "server_classes": [s["name"] for s in self.site["server_classes"]],
            "volumes": list(self.site.get("volumes") or []),
        }

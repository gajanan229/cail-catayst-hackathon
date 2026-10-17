"""The Runtime: one per process. Owns the simulator clock loop and every service; REST and WebSocket
handlers only talk to this facade (MVP spec §5: one Python process, asyncio tasks, SQLite)."""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

import yaml

from .api.errors import ApiError
from .core.config import Config
from .core.hub import Hub
from .core.timeutil import iso_sim
from .db.store import Store
from .governance.audit import AuditLog
from .health.engine import HealthEngine
from .health.metrics import MetricsStore
from .incidents.manager import IncidentManager
from .ops import Ops
from .schemas.common import CONTRACT_VERSION
from .sim.engine import SPEEDS, Simulator
from .telemetry.enrich import MessageCatalog
from .telemetry.pipeline import Pipeline

log = logging.getLogger("baton")


def _yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class Users:
    def __init__(self, data_dir: Path):
        self.users = _yaml(data_dir / "site" / "users.yaml")["users"]
        self.by_id = {u["id"]: u for u in self.users}

    def list(self) -> list[dict]:
        return [dict(u) for u in self.users]

    def get(self, user_id: str) -> dict:
        u = self.by_id.get(user_id)
        if not u:
            raise ApiError("VALIDATION_FAILED", f"Unknown actor '{user_id}'", {"actor": user_id})
        return u

    def name(self, user_id: str) -> str:
        if user_id in ("baton", "system"):
            return "Baton" if user_id == "baton" else "System"
        return self.by_id.get(user_id, {}).get("name", user_id)

    def actor_ref(self, user_id: str) -> dict:
        if user_id == "baton":
            return {"type": "agent", "id": "baton", "name": "Baton"}
        if user_id == "system":
            return {"type": "system", "id": "system", "name": "System"}
        return {"type": "user", "id": user_id, "name": self.name(user_id)}


class SimClock:
    """Sim-time waiters for graph nodes (e.g. 'verify for 60 sim-seconds')."""

    def __init__(self):
        self.tick = 0
        self.waiters: list[tuple[int, asyncio.Future]] = []

    def advance(self, tick: int) -> None:
        self.tick = tick
        due = [w for w in self.waiters if w[0] <= tick]
        if due:
            self.waiters = [w for w in self.waiters if w[0] > tick]
            for _, fut in due:
                if not fut.done():
                    fut.set_result(tick)

    async def wait(self, sim_seconds: int) -> None:
        fut = asyncio.get_running_loop().create_future()
        self.waiters.append((self.tick + int(sim_seconds), fut))
        await fut

    def cancel_all(self) -> None:
        for _, fut in self.waiters:
            if not fut.done():
                fut.cancel()
        self.waiters = []


class Runtime(Ops):
    def __init__(self, config: Config):
        self.config = config
        self.data_dir = config.data_dir
        self.store = Store(config.db_path)
        self.hub = Hub()
        self.users = Users(self.data_dir)
        self.sim = Simulator(self.data_dir, chatter_scale=config.chatter_scale)
        self.hub.sim_ts_fn = lambda: iso_sim(self.sim.now)
        self.audit = AuditLog(self.store, self.hub.publish, lambda: iso_sim(self.sim.now))
        self.metrics = MetricsStore()
        self.health = HealthEngine(self.sim.site, _yaml(self.data_dir / "rules" / "health_rules.yaml"))
        self.incidents = IncidentManager(self.store, self.hub.publish, lambda: iso_sim(self.sim.now))
        self.catalog_msgs = MessageCatalog(_yaml(self.data_dir / "rules" / "ems_messages.yaml"),
                                           self.data_dir / "content" / "operator_messages.jsonl")
        self.pipeline = Pipeline(
            self.catalog_msgs, _yaml(self.data_dir / "rules" / "causal_templates.yaml"),
            _yaml(self.data_dir / "rules" / "health_rules.yaml"), self._publish_now, store=self.store,
            impact_fn=self._impact_of_cpu, on_situation_opened=self._on_situation_opened,
        )
        self.clock = SimClock()
        self.read_only = bool(self.store.kv_get("read_only", False))
        self.replay_mode = config.replay
        self._loop_task: asyncio.Task | None = None
        self._stopping = False
        self._last_publish = 0.0
        self._last_state_publish = 0.0
        self._tick_hooks: list = []
        self.agents = None          # set by start(): agents service (LangGraph runtime)
        self._background: set[asyncio.Task] = set()

    @classmethod
    def from_env(cls) -> "Runtime":
        return cls(Config.from_env())

    # ------------------------------------------------------------ lifecycle

    async def start(self) -> None:
        from .services import install_services

        await install_services(self)
        self._loop_task = asyncio.create_task(self._clock_loop())
        if self.config.autostart and not self.sim.status.running:
            # Load the scenario but keep runtime state (threads, approvals, checkpoints), so a pending approval
            # survives a server restart (MVP spec §18 resume test). Director Start and Reset still clear everything.
            scen, _, prof = self.config.autostart.partition(":")
            self.sim.load(scen or "S1", prof or "demo")
            self.health.sample(self.sim.model, 0.0)
            self.publish_sim_state()

    async def stop(self) -> None:
        self._stopping = True
        self.clock.cancel_all()
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except (asyncio.CancelledError, Exception):
                pass
        for t in list(self._background):
            t.cancel()
        if self.agents is not None:
            await self.agents.close()
        self.store.close()

    def spawn(self, coro) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._background.add(task)
        task.add_done_callback(self._background.discard)
        return task

    def _publish_now(self, topic: str, type_: str, payload: Any) -> None:
        self.hub.publish(topic, type_, payload)

    # ------------------------------------------------------------ clock loop

    @property
    def tick_rate(self) -> float:
        return float(self.sim.status.speed) * self.config.time_scale

    async def _clock_loop(self) -> None:
        t0 = time.monotonic()
        done = 0
        rate = self.tick_rate
        while not self._stopping:
            try:
                st = self.sim.status
                if st.running and not st.paused and self.sim.model is not None:
                    if rate != self.tick_rate:
                        rate, t0, done = self.tick_rate, time.monotonic(), 0
                    due = int((time.monotonic() - t0) * rate) - done
                    for _ in range(min(max(due, 0), 64)):
                        self._tick()
                        done += 1
                        if not st.running or st.paused or rate != self.tick_rate:
                            break
                    if due > 64:            # fell behind: drop the backlog rather than spiral
                        t0, done = time.monotonic(), 0
                else:
                    t0, done = time.monotonic(), 0
                now = time.monotonic()
                if now - self._last_publish >= 1.0:
                    self._last_publish = now
                    self._publish_periodic()
                await asyncio.sleep(0.005 if rate > 50 else 0.01)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("clock loop error")
                await asyncio.sleep(0.2)

    def _tick(self) -> None:
        lines = self.sim.step()
        m = self.sim.model
        values = self.health.sample(m, self.pipeline.rate()["per_min"])
        self.pipeline.ingest(lines, m.now, values)
        if m.tick % 5 == 0:
            self.metrics.record(m.now, values)
        self.clock.advance(m.tick)
        for hook in list(self._tick_hooks):
            try:
                hook(m, values)
            except Exception:
                log.exception("tick hook failed")

    def _publish_periodic(self) -> None:
        if self.sim.model is None:
            return
        m = self.sim.model
        self.hub.publish("telemetry", "telemetry.tick", {"sim_ts": iso_sim(m.now), "values": self.health.values})
        self.hub.publish("health", "health.snapshot", self.health.build_snapshot(m))
        self.pipeline.flush()
        now = time.monotonic()
        if now - self._last_state_publish >= 5.0:
            self._last_state_publish = now
            self.publish_sim_state()

    def publish_sim_state(self) -> dict:
        state = self.sim.state_dict()
        self.hub.publish("sim", "sim.state", state)
        return state

    # ------------------------------------------------------------ pipeline callbacks

    def _impact_of_cpu(self, cpu: int) -> list[dict]:
        m = self.sim.model
        if m is None:
            return []
        out = []
        for sc in m.classes.values():
            if cpu in sc.cpus and sc.tag == "critical":
                running = sc.running(m.tick)
                cap = running * sc.per_server_rps
                out.append({"server_class": sc.name, "service": sc.service,
                            "rho_after": (sc.arrivals / cap) if cap else 9.9})
        return out

    def _on_situation_opened(self, situation: dict) -> None:
        if situation["severity"] >= 4 or situation.get("services"):
            inc = self.incidents.create(situation)
            self.pipeline.set_incident(situation["id"], inc["id"])
            self.audit.append("system", "pipeline", "incident.open", inc["id"],
                              {"situation_id": situation["id"], "title": inc["title"], "display_id": inc["display_id"]},
                              incident_id=inc["id"])
            prof = self.sim.profile_cfg
            if prof.get("on_incident_speed"):
                self.set_speed(int(prof["on_incident_speed"]))
            self._tick_hooks.append(lambda m, v, iid=inc["id"]: self._track(iid, v))
            if self.agents is not None:
                self.spawn(self.agents.start_pre_investigation(inc, situation))

    def _track(self, incident_id: str, values: dict) -> None:
        if self.sim.model and self.sim.model.tick % 5 == 0:
            self.incidents.track_impact(incident_id, values)

    # ------------------------------------------------------------ system

    def system_status(self) -> dict:
        return {
            "system": self.sim.system, "sim": self.sim.state_dict(),
            "llm_provider": "nemotron" if self.config.llm_provider == "nemotron" else "none",
            "model_fast": self.config.model_fast if self.config.llm_provider == "nemotron" else None,
            "model_strong": self.config.model_strong if self.config.llm_provider == "nemotron" else None,
            "replay_mode": self.replay_mode, "embeddings": self.config.embeddings if self.config.embeddings in ("local", "none") else "none",
            "read_only": self.read_only, "contract_version": CONTRACT_VERSION,
        }

    def set_read_only(self, enabled: bool, actor: str) -> dict:
        self.users.get(actor)
        self.read_only = bool(enabled)
        self.store.kv_set("read_only", self.read_only)
        self.audit.append("user", actor, "system.read_only", "system", {"enabled": self.read_only})
        self.hub.publish("sim", "sim.state", self.sim.state_dict())
        if hasattr(self, "approvals"):
            for a in self.approvals.list(None):
                if a["status"] in ("pending", "partially_approved"):
                    self.hub.publish("approvals", "approval.upsert", a)
        return self.system_status()

    def set_replay(self, mode: str, actor: str) -> dict:
        self._actor(actor)
        self.replay_mode = mode
        if hasattr(self, "gateway"):
            self.gateway.set_replay(mode)
        self.audit.append(*self._actor_parts(actor), "system.replay_mode", "system", {"mode": mode})
        return self.system_status()

    def _actor(self, actor: str) -> dict:
        if actor in ("system", "baton"):
            return self.users.actor_ref(actor)
        return self.users.get(actor)

    def _actor_parts(self, actor: str) -> tuple[str, str]:
        if actor in ("system", "baton"):
            return ("system" if actor == "system" else "agent", actor)
        self.users.get(actor)
        return ("user", actor)

    # ------------------------------------------------------------ simulator

    def sim_state(self) -> dict:
        return self.sim.state_dict()

    def _require_sim(self) -> None:
        if self.sim.model is None or not self.sim.status.running:
            raise ApiError("SIM_NOT_RUNNING", "The simulator is not running. Start a scenario from the Director.")

    async def sim_start(self, scenario: str, profile: str, seed: int | None, speed: int | None, actor: str) -> dict:
        self._actor(actor)
        if scenario not in self.sim.scenarios:
            raise ApiError("NOT_FOUND", f"Unknown scenario {scenario}")
        await self._clear_runtime(keep_scenario=False)
        self.sim.load(scenario, profile, seed, speed)
        self.audit.append(*self._actor_parts(actor), "sim.start", scenario,
                          {"scenario": scenario, "profile": profile, "seed": self.sim.status.seed, "speed": self.sim.status.speed})
        self.health.sample(self.sim.model, 0.0)
        return self.publish_sim_state()

    def sim_inject(self, fault: str, params: dict, actor: str) -> dict:
        self._require_sim()
        self._actor(actor)
        self.sim.inject(fault, params)
        self.audit.append(*self._actor_parts(actor), "sim.inject", fault, {"fault": fault, "params": params})
        prof = self.sim.profile_cfg
        return self.publish_sim_state()

    def set_speed(self, speed: int) -> None:
        self.sim.status.speed = self.sim._clamp_speed(speed)
        self.publish_sim_state()

    def sim_clock(self, speed: int | None, paused: bool | None, step: int | None, actor: str) -> dict:
        self._require_sim()
        self._actor(actor)
        if speed is not None:
            if speed not in SPEEDS:
                raise ApiError("VALIDATION_FAILED", f"speed must be one of {SPEEDS}")
            self.sim.status.speed = speed
        if paused is not None:
            self.sim.status.paused = paused
        if step:
            for _ in range(max(1, min(int(step), 600))):
                self._tick()
        return self.publish_sim_state()

    async def reset(self, actor: str) -> dict:
        self._actor(actor)
        scenario = self.sim.status.scenario or "S1"
        profile = self.sim.status.profile
        await self._clear_runtime(keep_scenario=True)
        self.sim.load(scenario, profile)
        self.health.sample(self.sim.model, 0.0)
        self.audit.append(*self._actor_parts(actor), "sim.reset", scenario, {"scenario": scenario, "profile": profile})
        return self.publish_sim_state()

    async def _clear_runtime(self, keep_scenario: bool) -> None:
        """Clear runtime tables, restore the ledger seed, keep knowledge indexes (MVP spec §6.7)."""
        if self.agents is not None:
            await self.agents.reset()
        self.clock.cancel_all()
        self._tick_hooks = []
        self.store.clear_runtime()
        self.store.kv_set("read_only", self.read_only)
        self.pipeline.reset()
        self.health.reset()
        self.metrics.reset()
        self.hub.clear_history()
        if hasattr(self, "after_reset"):
            self.after_reset()

    # ------------------------------------------------------------ telemetry

    def topology(self) -> dict:
        site = self.sim.site
        nodes = [{"id": "system:TORBANK", "type": "system", "name": site["system"], "attributes": {}, "tags": []}]
        edges = []
        for c in range(int(site["cpus"]["count"])):
            nodes.append({"id": f"cpu:{c}", "type": "cpu", "name": f"CPU {c}", "attributes": {}, "tags": []})
        for p in site["processes"]:
            pid = f"proc:{p['name']}"
            nodes.append({"id": pid, "type": "process", "name": p["name"],
                          "attributes": {"role": p["role"], "primary_cpu": p["primary_cpu"], "backup_cpu": p.get("backup_cpu")},
                          "tags": list(p.get("tags") or []) + (["protected"] if p.get("protected") else [])})
            edges.append({"source": pid, "target": f"cpu:{p['primary_cpu']}", "kind": "runs_on"})
            if p.get("backup_cpu") is not None:
                edges.append({"source": pid, "target": f"cpu:{p['backup_cpu']}", "kind": "backup_on"})
        for sc in site["server_classes"]:
            sid = f"sc:{sc['name']}"
            nodes.append({"id": sid, "type": "server_class", "name": sc["name"],
                          "attributes": {"numstatic": sc["numstatic"], "maxservers": sc["maxservers"], "cpus": sc["cpus"]},
                          "tags": [sc.get("tag", "normal")]})
            for c in sc["cpus"]:
                edges.append({"source": sid, "target": f"cpu:{c}", "kind": "runs_on"})
            edges.append({"source": sid, "target": f"svc:{sc['service']}", "kind": "serves"})
        for s in site["services"]:
            nodes.append({"id": f"svc:{s['id']}", "type": "service", "name": s["name"], "attributes": {}, "tags": []})
        nodes.append({"id": "tmf:mat", "type": "tmf", "name": "TMF audit trail (MAT)", "attributes": {}, "tags": []})
        for v in site.get("volumes") or []:
            nodes.append({"id": f"vol:{v}", "type": "volume", "name": v, "attributes": {}, "tags": []})
            edges.append({"source": f"proc:{v}", "target": f"vol:{v}", "kind": "uses_volume"})
        return {"nodes": nodes, "edges": edges}

    def health_snapshot(self) -> dict:
        self._require_sim()
        return self.health.build_snapshot(self.sim.model)

    async def investigate_situation(self, situation_id: str, actor: str) -> dict:
        return await self.agents.investigate_situation(situation_id, actor)

    def metrics_query(self, keys: list[str], window_s: int) -> dict:
        return {"window_s": window_s, "series": self.metrics.query(keys, window_s)}

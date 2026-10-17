"""Agent runtime (MVP spec §11): threads, runs, LangGraph graphs on an SQLite checkpointer, interrupts and resume.

Graph thread keys: '{thread}:investigate' for an incident thread, '{thread}:{graph}:{run}' for one-shot
Command and Ask runs. Approvals carry their graph key; a complete approval resumes it with Command(resume=...).
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from ..api.errors import ApiError
from ..core.ids import new_id
from ..core.timeutil import wall_now
from .cards import CardStore
from .trace import Tracer

log = logging.getLogger("baton.agents")


class AgentService:
    def __init__(self, rt):
        self.rt = rt
        self.cards = CardStore(rt)
        self.tracer = Tracer(rt)
        self.conn: aiosqlite.Connection | None = None
        self.saver: AsyncSqliteSaver | None = None
        self.graphs: dict = {}
        self.locks: dict[str, asyncio.Lock] = {}
        self.tasks: set[asyncio.Task] = set()

    # ------------------------------------------------------------ lifecycle

    async def open(self) -> None:
        path: Path = self.rt.config.checkpoint_path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = await aiosqlite.connect(str(path))
        self.saver = AsyncSqliteSaver(self.conn)
        await self.saver.setup()
        from .graphs import ask, command, investigate
        self.graphs = {"command": command.build(self.saver), "ask": ask.build(self.saver),
                       "investigate": investigate.build(self.saver)}

    async def close(self) -> None:
        for t in list(self.tasks):
            t.cancel()
        if self.conn is not None:
            await self.conn.close()
            self.conn = None

    async def reset(self) -> None:
        for t in list(self.tasks):
            t.cancel()
        for t in list(self.tasks):
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
        self.tasks.clear()
        self.locks.clear()
        if self.conn is not None:
            await self.conn.execute("DELETE FROM checkpoints")
            await self.conn.execute("DELETE FROM writes")
            await self.conn.commit()

    def spawn(self, coro) -> asyncio.Task:
        t = asyncio.create_task(coro)
        self.tasks.add(t)
        t.add_done_callback(self.tasks.discard)
        return t

    # ------------------------------------------------------------ threads

    def create_thread(self, mode: str, incident_id: str | None, actor: str, title: str | None = None) -> dict:
        if actor not in ("baton", "system"):
            self.rt.users.get(actor)
        if incident_id:
            inc = self.rt.incidents.get(incident_id)
            if not inc:
                raise ApiError("NOT_FOUND", f"Incident {incident_id} not found")
            if inc.get("thread_id") and mode in ("auto", "investigate"):
                existing = self.get_thread(inc["thread_id"])
                if existing:
                    return existing
        t = {"id": new_id("thr"), "mode": mode, "actor": actor, "incident_id": incident_id,
             "title": title or ("New conversation" if not incident_id else "Incident thread"), "status": "idle",
             "created_at": wall_now()}
        self.save_thread(t)
        return t

    def save_thread(self, t: dict) -> None:
        self.rt.store.put("threads", t["id"], t, mode=t["mode"], incident_id=t["incident_id"], created_at=t["created_at"])

    def get_thread(self, thread_id: str) -> dict | None:
        return self.rt.store.get("threads", thread_id)

    def require_thread(self, thread_id: str) -> dict:
        t = self.get_thread(thread_id)
        if not t:
            raise ApiError("NOT_FOUND", f"Thread {thread_id} not found")
        return t

    def set_status(self, thread_id: str, status: str) -> None:
        t = self.get_thread(thread_id)
        if t and t["status"] != status:
            t["status"] = status
            self.save_thread(t)

    def interrupts(self, thread_id: str) -> list[dict]:
        return self.rt.store.kv_get(f"interrupts:{thread_id}", [])

    def _set_interrupts(self, thread_id: str, items: list[dict]) -> None:
        self.rt.store.kv_set(f"interrupts:{thread_id}", items)

    def thread_detail(self, thread_id: str) -> dict:
        t = self.require_thread(thread_id)
        return {"thread": t, "cards": self.cards.for_thread(thread_id), "trace": self.tracer.for_thread(thread_id),
                "pending_interrupts": [{k: i[k] for k in ("id", "thread_id", "run_id", "kind", "approval_id", "prompt", "raised_at",
                                                          "resolved")} for i in self.interrupts(thread_id) if not i.get("resolved")]}

    # ------------------------------------------------------------ messages and routing

    async def post_message(self, thread_id: str, text: str, actor: str) -> dict:
        t = self.require_thread(thread_id)
        self.rt.users.get(actor)
        text = (text or "").strip()
        if not text:
            raise ApiError("VALIDATION_FAILED", "Empty message")
        from .graphs.supervisor import route
        graph, incident_id = await route(self.rt, t, text, actor)
        run_id = new_id("run")
        key = f"{thread_id}:{graph}:{run_id}"
        payload = {"text": text, "actor": actor, "incident_id": incident_id}
        self.rt.audit.append("user", actor, "thread.message", thread_id, {"text": text[:500], "routed_to": graph},
                             incident_id=incident_id)
        self.spawn(self._run(thread_id, graph, key, payload, run_id))
        return {"run_id": run_id, "thread_id": thread_id}

    async def resume_question(self, thread_id: str, interrupt_id: str, response: dict, actor: str) -> dict:
        self.require_thread(thread_id)
        items = self.interrupts(thread_id)
        it = next((i for i in items if i["id"] == interrupt_id and not i.get("resolved")), None)
        if not it:
            raise ApiError("NOT_FOUND", f"Interrupt {interrupt_id} not pending")
        if it["kind"] == "approval":
            raise ApiError("CONFLICT", "Approval interrupts are resumed through /api/approvals/{id}/decide")
        run_id = new_id("run")
        self.spawn(self._run(thread_id, it["graph"], it["graph_key"], Command(resume={**response, "actor": actor}), run_id,
                             interrupt_id=interrupt_id))
        return {"run_id": run_id, "thread_id": thread_id}

    # ------------------------------------------------------------ incidents

    async def start_pre_investigation(self, incident: dict, situation: dict) -> None:
        t = self.create_thread("investigate", None, "baton", title=f"{incident['display_id']} · {incident['title']}")
        t["incident_id"] = incident["id"]
        self.save_thread(t)
        self.rt.incidents.update(incident["id"], thread_id=t["id"])
        run_id = new_id("run")
        payload = {"incident_id": incident["id"], "situation_id": situation["id"], "actor": "baton", "auto_only": True}
        await self._run(t["id"], "investigate", f"{t['id']}:investigate", payload, run_id)

    async def investigate_situation(self, situation_id: str, actor: str) -> dict:
        self.rt.users.get(actor)
        sit = self.rt.pipeline.situation_detail(situation_id)
        if not sit:
            raise ApiError("NOT_FOUND", f"Situation {situation_id} not found")
        if sit.get("incident_id"):
            inc = self.rt.incidents.get(sit["incident_id"])
            for _ in range(20):
                if inc and inc.get("thread_id"):
                    break
                await asyncio.sleep(0.05)
                inc = self.rt.incidents.get(sit["incident_id"])
            return {"thread_id": inc.get("thread_id") or "", "incident_id": inc["id"]}
        inc = self.rt.incidents.create(sit)
        self.rt.pipeline.set_incident(situation_id, inc["id"])
        self.rt.audit.append("user", actor, "incident.open", inc["id"], {"situation_id": situation_id}, incident_id=inc["id"])
        task = self.spawn(self.start_pre_investigation(inc, sit))
        for _ in range(40):
            inc = self.rt.incidents.get(inc["id"])
            if inc.get("thread_id"):
                break
            await asyncio.sleep(0.025)
        return {"thread_id": inc.get("thread_id") or "", "incident_id": inc["id"]}

    # ------------------------------------------------------------ approvals → resume

    async def on_approval_complete(self, approval: dict) -> bool:
        key = approval.get("graph_key")
        if not key:
            return False
        thread_id = approval["thread_id"]
        graph = key.split(":")[1]
        self.spawn(self._resume_for_approval(thread_id, graph, key, approval))
        return True

    async def _resume_for_approval(self, thread_id: str, graph: str, key: str, approval: dict) -> None:
        lock = self.locks.setdefault(key, asyncio.Lock())
        async with lock:
            g = self.graphs[graph]
            cfg = {"configurable": {"thread_id": key}}
            state = await g.aget_state(cfg)
            waiting = [i for i in state.interrupts if (i.value or {}).get("approval_id") == approval["id"]]
            if not waiting:
                return   # the graph already moved on (it reads approval status itself) or never asked
        resume = {"approval_id": approval["id"], "status": approval["status"], "decisions": approval["decisions"]}
        items = self.interrupts(thread_id)
        for it in items:
            if it.get("approval_id") == approval["id"] and not it.get("resolved"):
                it["resolved"] = True
                self.rt.hub.publish(f"thread:{thread_id}", "interrupt.resolved",
                                    {"interrupt_id": it["id"], "thread_id": thread_id,
                                     "response": {"approval_id": approval["id"], "status": approval["status"]}})
        self._set_interrupts(thread_id, items)
        await self._run(thread_id, graph, key, Command(resume=resume), new_id("run"))

    # ------------------------------------------------------------ runs

    async def _run(self, thread_id: str, graph: str, key: str, payload, run_id: str, interrupt_id: str | None = None) -> None:
        lock = self.locks.setdefault(key, asyncio.Lock())
        async with lock:
            run = {"id": run_id, "thread_id": thread_id, "graph": graph, "status": "running", "started_at": wall_now(),
                   "ended_at": None}
            self.rt.store.put("runs", run_id, run, thread_id=thread_id, status="running", started_at=run["started_at"])
            self.rt.hub.publish(f"thread:{thread_id}", "run.started", run)
            self.set_status(thread_id, "running")
            g = self.graphs[graph]
            cfg = {"configurable": {"thread_id": key, "baton_thread": thread_id, "run_id": run_id, "graph_key": key},
                   "recursion_limit": 120}
            try:
                if isinstance(payload, dict):
                    payload = {**payload, "thread_id": thread_id}
                await g.ainvoke(payload, cfg)
                state = await g.aget_state(cfg)
                if state.interrupts:
                    items = self.interrupts(thread_id)
                    for intr in state.interrupts:
                        val = intr.value or {}
                        if any(i.get("lg_id") == intr.id and not i.get("resolved") for i in items):
                            continue
                        it = {"id": new_id("int"), "lg_id": intr.id, "thread_id": thread_id, "run_id": run_id,
                              "kind": val.get("kind", "approval"), "approval_id": val.get("approval_id"),
                              "prompt": val.get("prompt", "Waiting for approval"), "raised_at": wall_now(),
                              "resolved": False, "graph": graph, "graph_key": key}
                        items.append(it)
                        self.rt.hub.publish(f"thread:{thread_id}", "interrupt.raised",
                                            {k: it[k] for k in ("id", "thread_id", "run_id", "kind", "approval_id", "prompt",
                                                                "raised_at", "resolved")})
                    self._set_interrupts(thread_id, items)
                    run["status"] = "waiting"
                    self.set_status(thread_id, "waiting")
                else:
                    run["status"] = "completed"
                    self.set_status(thread_id, "done" if graph == "investigate" else "idle")
                run["ended_at"] = wall_now()
                self.rt.store.put("runs", run_id, run, thread_id=thread_id, status=run["status"], started_at=run["started_at"])
                if run["status"] == "completed":
                    self.rt.hub.publish(f"thread:{thread_id}", "run.completed", {"run": run, "summary": ""})
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.exception("run %s failed", run_id)
                run.update(status="failed", ended_at=wall_now())
                self.rt.store.put("runs", run_id, run, thread_id=thread_id, status="failed", started_at=run["started_at"])
                self.rt.hub.publish(f"thread:{thread_id}", "run.failed", {"run": run, "error": str(e)[:300]})
                self.set_status(thread_id, "failed")

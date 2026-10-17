"""Agent trace (MVP spec §11.5): node.started / node.ended per node with label, duration, status,
summary and detail (tools, evidence IDs, model or 'fallback' or 'replay', prompt hash)."""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

from ..core.ids import new_id
from ..core.timeutil import wall_now


class Step:
    def __init__(self):
        self.summary = ""
        self.tools: list[str] = []
        self.evidence_ids: list[str] = []
        self.model: str | None = None
        self.prompt_hash: str | None = None
        self.inputs: str | None = None
        self.output: str | None = None
        self.status: str | None = None


class Tracer:
    def __init__(self, rt):
        self.rt = rt

    def _emit(self, thread_id: str, run_id: str, step_id: str, node: str, label: str, status: str, started: str,
              duration_ms: int | None, s: Step, kind: str) -> dict:
        step = {"run_id": run_id, "step_id": step_id, "node": node, "label": label, "status": status, "started_at": started,
                "duration_ms": duration_ms, "summary": s.summary,
                "detail": {"tools": s.tools, "evidence_ids": s.evidence_ids, "model": s.model, "prompt_hash": s.prompt_hash,
                           "inputs": s.inputs, "output": s.output}}
        seq = self.rt.store.query("SELECT COUNT(*) AS n FROM trace_steps WHERE thread_id = ?", (thread_id,))[0]["n"]
        existing = self.rt.store.query("SELECT seq FROM trace_steps WHERE id = ?", (step_id,))
        self.rt.store.put("trace_steps", step_id, step, run_id=run_id, thread_id=thread_id,
                          seq=existing[0]["seq"] if existing else seq + 1)
        self.rt.hub.publish(f"thread:{thread_id}", kind, step)
        return step

    @asynccontextmanager
    async def node(self, state: dict, node: str, label: str, step_id: str | None = None):
        thread_id, run_id = state["thread_id"], state.get("run_id") or "run_unknown"
        sid = step_id or new_id("stp")
        started = wall_now()
        t0 = time.monotonic()
        s = Step()
        self._emit(thread_id, run_id, sid, node, label, "running", started, None, s, "node.started")
        try:
            yield s
        except Exception as e:
            from langgraph.errors import GraphInterrupt
            if isinstance(e, GraphInterrupt):
                s.summary = s.summary or "Waiting for a person"
                self._emit(thread_id, run_id, sid, node, label, "waiting", started, int((time.monotonic() - t0) * 1000), s,
                           "node.ended")
            else:
                s.summary = f"Failed: {e}"[:200]
                self._emit(thread_id, run_id, sid, node, label, "failed", started, int((time.monotonic() - t0) * 1000), s,
                           "node.ended")
            raise
        status = s.status or ("fallback" if s.model == "fallback" else "done")
        self._emit(thread_id, run_id, sid, node, label, status, started, int((time.monotonic() - t0) * 1000), s, "node.ended")

    def for_thread(self, thread_id: str) -> list[dict]:
        return self.rt.store.all("trace_steps", "thread_id = ?", (thread_id,), order="seq")

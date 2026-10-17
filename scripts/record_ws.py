"""Record a real golden run (S1, Flows B, C and A) into a WebSocket timeline for the frontend mock mode.

    python scripts/record_ws.py [--out contracts/recordings/golden_s1.json] [--time-scale 2] [--models]

Output format (contracts/recordings/README.md):
    {"version", "scenario", "profile", "recorded_at", "sim_start", "events": [{"t_ms", "sim_ts", "envelope"}],
     "requests": [{"t_ms", "method", "path", "status", "body"}], "rest": {"GET /api/...": <final response>}}
`t_ms` is wall time since the start of the recording; `envelope` is exactly what /api/ws sent.
Agent B can replay events on a mock clock by `t_ms` (real pacing) or by `sim_ts` (sim pacing).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))


async def main(out: Path, time_scale: float, models: bool) -> int:
    os.environ.setdefault("BATON_LLM_PROVIDER", "nemotron" if models else "none")
    os.environ.setdefault("BATON_REPLAY", "replay")
    import httpx

    from baton.api.deps import set_runtime
    from baton.app import create_app
    from baton.core.config import Config
    from baton.core.timeutil import wall_now
    from baton.eval.golden import drive_incident
    from baton.runtime import Runtime
    from baton.schemas.common import CONTRACT_VERSION

    tmp = Path(tempfile.mkdtemp(prefix="baton_rec_"))
    cfg = Config.from_env()
    cfg.var_dir, cfg.db_path, cfg.checkpoint_path = tmp, tmp / "baton.db", tmp / "checkpoints.db"
    cfg.time_scale = time_scale
    cfg.embeddings = os.environ.get("BATON_EMBEDDINGS", "none")
    cfg.typing_ms_per_char = int(os.environ.get("BATON_TYPING_MS_PER_CHAR", "25"))
    rt = Runtime(cfg)
    set_runtime(rt)
    await rt.start()
    t0 = time.monotonic()
    events, requests = [], []

    def on_env(env):
        events.append({"t_ms": int((time.monotonic() - t0) * 1000), "sim_ts": env.get("sim_ts"), "envelope": env})

    rt.hub.add_listener(on_env)

    async def log_request(response: httpx.Response):
        await response.aread()
        req = response.request
        body = None
        if req.content:
            try:
                body = json.loads(req.content)
            except json.JSONDecodeError:
                body = None
        requests.append({"t_ms": int((time.monotonic() - t0) * 1000), "method": req.method, "path": str(req.url.path)
                         + (f"?{req.url.query.decode()}" if req.url.query else ""), "status": response.status_code, "body": body})

    app = create_app(start_runtime=False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test",
                                 event_hooks={"response": [log_request]}) as api:
        res = await drive_incident(api, rt, scenario="S1", profile="test", with_flows=True, timeout=240)
        await asyncio.sleep(0.5)
        rest = {}
        for path in ["/api/system/status", "/api/users", "/api/sim/state", "/api/health", "/api/topology", "/api/situations",
                     "/api/incidents", "/api/approvals", "/api/catalog", "/api/claims", "/api/ledger", "/api/audit",
                     "/api/audit/verify", "/api/playbooks", "/api/policies"]:
            rest[f"GET {path}"] = (await api.get(path)).json()
        if res.incident:
            iid = res.incident["id"]
            for path in [f"/api/incidents/{iid}", f"/api/incidents/{iid}/timeline", f"/api/incidents/{iid}/postmortem",
                         f"/api/threads/{res.incident['thread_id']}"]:
                rest[f"GET {path}"] = (await api.get(path)).json()
    rt.hub.remove_listener(on_env)
    await rt.stop()
    set_runtime(None)
    # keep only lightweight requests (polling GETs are noise for a mock)
    requests = [r for r in requests if r["method"] != "GET"]
    doc = {"version": CONTRACT_VERSION, "scenario": "S1", "profile": "test", "time_scale": time_scale,
           "recorded_at": wall_now(), "ok": res.ok, "error": res.error, "events": events, "requests": requests, "rest": rest}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    kinds = {}
    for e in events:
        kinds[e["envelope"]["type"]] = kinds.get(e["envelope"]["type"], 0) + 1
    print(f"recorded {len(events)} events, {len(requests)} requests -> {out} (ok={res.ok}{', ' + res.error if res.error else ''})")
    print(", ".join(f"{k}:{v}" for k, v in sorted(kinds.items())))
    return 0 if res.ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "contracts" / "recordings" / "golden_s1.json"))
    ap.add_argument("--time-scale", type=float, default=2.0)
    ap.add_argument("--models", action="store_true", help="use Nemotron (BATON_LLM_PROVIDER=nemotron)")
    a = ap.parse_args()
    sys.exit(asyncio.run(main(Path(a.out), a.time_scale, a.models)))

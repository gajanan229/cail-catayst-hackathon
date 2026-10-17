"""make record: run the golden path (Flows B, C and A) twice with Nemotron and BATON_REPLAY=record,
appending successful model outputs to data/replay/<task>.jsonl (MVP spec §4.2 G4, §11.6).

    python scripts/record.py [--runs 2] [--time-scale 1]

Two runs fill gaps left by endpoint errors in the first. Recordings are committed so the demo replays offline.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))


async def one_run(i: int, time_scale: float) -> dict:
    import httpx

    from baton.api.deps import set_runtime
    from baton.app import create_app
    from baton.core.config import Config
    from baton.eval.golden import drive_incident
    from baton.runtime import Runtime

    tmp = Path(tempfile.mkdtemp(prefix=f"baton_record{i}_"))
    cfg = Config.from_env()
    cfg.var_dir, cfg.db_path, cfg.checkpoint_path = tmp, tmp / "baton.db", tmp / "checkpoints.db"
    cfg.llm_provider, cfg.replay, cfg.time_scale = "nemotron", "record", time_scale
    cfg.embeddings = os.environ.get("BATON_EMBEDDINGS", "local")
    cfg.typing_ms_per_char = 0
    if not cfg.models_enabled:
        raise SystemExit("NVIDIA_API_KEY is not set; nothing to record")
    rt = Runtime(cfg)
    set_runtime(rt)
    await rt.start()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(start_runtime=False)),
                                     base_url="http://record") as api:
            res = await drive_incident(api, rt, with_flows=True, timeout=600)
        rows = rt.store.query("SELECT cache_hit, COUNT(*) AS n FROM model_calls GROUP BY cache_hit")
        return {"ok": res.ok, "error": res.error, "calls": {r["cache_hit"]: r["n"] for r in rows}}
    finally:
        await rt.stop()
        set_runtime(None)


async def main(runs: int, time_scale: float) -> int:
    ok = True
    for i in range(1, runs + 1):
        r = await one_run(i, time_scale)
        print(f"run {i}: ok={r['ok']} calls={r['calls']}{' error=' + r['error'] if r['error'] else ''}", flush=True)
        ok = ok and r["ok"]
    replay = ROOT / "data" / "replay"
    for p in sorted(replay.glob("*.jsonl")):
        print(f"  {p.name}: {sum(1 for _ in p.open(encoding='utf-8'))} recordings")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--time-scale", type=float, default=1.0)
    a = ap.parse_args()
    sys.exit(asyncio.run(main(a.runs, a.time_scale)))

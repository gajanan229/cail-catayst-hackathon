"""make eval: commands, safety, diagnosis (S1, S3) and retrieval suites (MVP spec §17).

    python scripts/run_eval.py [--suites commands,safety,diagnosis,retrieval] [--run-id evr_...]

Runs on a throwaway runtime and saves the run to BATON_DB (var/baton.db), where /api/eval/latest reads it.
Models follow BATON_LLM_PROVIDER / BATON_REPLAY like the app.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))


async def main(suites, run_id) -> int:
    from baton.core.config import Config
    from baton.eval.runner import run_eval_isolated

    run = await run_eval_isolated(Config.from_env(), suites, run_id)
    print(f"eval {run['id']}: {run['status']} in {run['config'].get('seconds')}s")
    for t in run["tiles"]:
        print(f"  {'PASS' if t['passed'] else 'FAIL'}  {t['label']:<26} {t['display']:<22} target {t['target']}")
    for r in run["results"]:
        if not r["passed"]:
            print(f"  ✗ {r['suite']}/{r['case_id']}: {r['input'][:70]} | expected {str(r['expected'])[:120]} | got {str(r['actual'])[:160]}")
    return 0 if run["status"] == "done" and all(t["passed"] for t in run["tiles"]) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--suites", default=None)
    ap.add_argument("--run-id", default=None)
    a = ap.parse_args()
    sys.exit(asyncio.run(main(a.suites.split(",") if a.suites else None, a.run_id)))

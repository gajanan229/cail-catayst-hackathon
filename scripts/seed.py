"""make seed: build var/ from data/ (database, ledger seed, claims, knowledge indexes, embedding cache)."""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))


async def main() -> int:
    from baton.core.config import Config
    from baton.runtime import Runtime

    cfg = Config.from_env()
    t0 = time.monotonic()
    for p in (cfg.db_path, cfg.checkpoint_path):
        for suffix in ("", "-wal", "-shm"):
            f = Path(str(p) + suffix)
            if f.exists():
                f.unlink()
    rt = Runtime(cfg)
    await rt.start()
    n = rt.store.query("SELECT COUNT(*) AS n FROM chunks")[0]["n"]
    vec = rt.store.query("SELECT COUNT(*) AS n FROM chunk_vectors_blob")[0]["n"]
    ledger = rt.store.query("SELECT COUNT(*) AS n FROM ledger_entries")[0]["n"]
    claims = rt.store.query("SELECT COUNT(*) AS n FROM claims")[0]["n"]
    await rt.stop()
    print(f"seeded {cfg.db_path}: {n} chunks, {vec} vectors ({cfg.embeddings}), {ledger} ledger entries, {claims} claims "
          f"in {time.monotonic() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

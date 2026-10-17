"""make reset: POST /api/sim/reset if the backend is running; otherwise clear runtime tables offline."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))


def main() -> int:
    t0 = time.monotonic()
    try:
        import httpx
        r = httpx.post("http://127.0.0.1:8000/api/sim/reset", json={"actor": "system"}, timeout=10)
        r.raise_for_status()
        print(f"reset via running backend in {time.monotonic() - t0:.2f}s")
        return 0
    except Exception:
        pass
    from baton.core.config import Config
    from baton.db.store import Store

    cfg = Config.from_env()
    if not cfg.db_path.exists():
        print("no database yet (run make seed)")
        return 0
    store = Store(cfg.db_path)
    store.clear_runtime()
    store.close()
    if cfg.checkpoint_path.exists():
        cfg.checkpoint_path.unlink()
    print(f"reset offline in {time.monotonic() - t0:.2f}s (ledger seed is restored at next start)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

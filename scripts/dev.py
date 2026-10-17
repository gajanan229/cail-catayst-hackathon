"""make dev: backend on :8000 and (if present) the frontend on :5173. Ctrl+C stops both."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    env = dict(os.environ)
    env.setdefault("BATON_AUTOSTART", "S1:demo")
    env["PYTHONPATH"] = str(ROOT / "backend") + os.pathsep + env.get("PYTHONPATH", "")
    procs = [subprocess.Popen([sys.executable, "-m", "uvicorn", "baton.app:app", "--host", "127.0.0.1", "--port", "8000",
                               "--log-level", "warning"], cwd=str(ROOT / "backend"), env=env)]
    print("Baton backend: http://localhost:8000  (API docs: http://localhost:8000/docs)", flush=True)
    frontend = ROOT / "frontend"
    if "--backend-only" not in sys.argv and (frontend / "package.json").exists():
        npm = shutil.which("npm") or shutil.which("npm.cmd")
        if npm:
            procs.append(subprocess.Popen([npm, "run", "dev", "--", "--port", "5173"], cwd=str(frontend), env=env))
            print("Baton console: http://localhost:5173", flush=True)
    try:
        return procs[0].wait()
    except KeyboardInterrupt:
        return 0
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()


if __name__ == "__main__":
    sys.exit(main())

"""make setup helper: npm install in frontend/ when it exists (Agent B owns the frontend)."""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
fe = ROOT / "frontend"
if (fe / "package.json").exists():
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if npm:
        sys.exit(subprocess.call([npm, "install"], cwd=str(fe)))
print("frontend/ not present yet; skipping npm install")

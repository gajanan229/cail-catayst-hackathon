import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("BATON_LLM_PROVIDER", "none")
os.environ.setdefault("BATON_REPLAY", "off")

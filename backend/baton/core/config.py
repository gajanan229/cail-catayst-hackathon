"""Process configuration from environment variables (MVP spec §5.4, with Nemotron as the provider)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"
NEMOTRON_120B = "nvidia/nemotron-3.5-super-vl-120b-a12b"

load_dotenv(ROOT / ".env")


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return default if value is None or value == "" else value


@dataclass
class Config:
    llm_provider: str = "none"
    model_fast: str = NEMOTRON_120B
    model_strong: str = NEMOTRON_120B
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nemotron_thinking: bool = False
    model_timeout_s: float = 20.0
    replay: str = "replay"
    embeddings: str = "local"
    seed: int = 42
    db_path: Path = ROOT / "var" / "baton.db"
    checkpoint_path: Path = ROOT / "var" / "checkpoints.db"
    var_dir: Path = ROOT / "var"
    data_dir: Path = DATA
    # Test and tooling knobs (not in the spec's table; documented in README).
    time_scale: float = 1.0          # multiplies the simulator speed (tests run at e.g. 8x the 16x test profile)
    typing_ms_per_char: int = 25     # ghost typing speed; output is held back for len(text) * this
    chatter_scale: float = 1.0       # scales the 300/min chatter
    autostart: str | None = None     # e.g. "S1:demo" to start a scenario at boot
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "Config":
        var_dir = Path(_env("BATON_VAR", str(ROOT / "var")))
        db = Path(_env("BATON_DB", str(var_dir / "baton.db")))
        return cls(
            llm_provider=_env("BATON_LLM_PROVIDER", "none").lower(),
            model_fast=_env("BATON_MODEL_FAST", NEMOTRON_120B),
            model_strong=_env("BATON_MODEL_STRONG", NEMOTRON_120B),
            nvidia_base_url=_env("BATON_NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
            nemotron_thinking=_env("BATON_NEMOTRON_THINKING", "0") in ("1", "true", "yes"),
            model_timeout_s=float(_env("BATON_MODEL_TIMEOUT_S", "20")),
            replay=_env("BATON_REPLAY", "replay").lower(),
            embeddings=_env("BATON_EMBEDDINGS", "local").lower(),
            seed=int(_env("BATON_SEED", "42")),
            db_path=db,
            checkpoint_path=Path(_env("BATON_CHECKPOINTS", str(db.parent / "checkpoints.db"))),
            var_dir=var_dir,
            time_scale=float(_env("BATON_TIME_SCALE", "1")),
            typing_ms_per_char=int(_env("BATON_TYPING_MS_PER_CHAR", "25")),
            chatter_scale=float(_env("BATON_CHATTER_SCALE", "1")),
            autostart=os.environ.get("BATON_AUTOSTART") or None,
        )

    @property
    def nvidia_api_key(self) -> str | None:
        return os.environ.get("NVIDIA_API_KEY") or None

    @property
    def models_enabled(self) -> bool:
        return self.llm_provider == "nemotron" and bool(self.nvidia_api_key)

"""Shared test helpers: an in-process Runtime on a temp database."""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from baton.core.config import Config


def make_config(tmp_path, **overrides) -> Config:
    cfg = Config.from_env()
    cfg.var_dir = tmp_path
    cfg.db_path = tmp_path / "baton.db"
    cfg.checkpoint_path = tmp_path / "checkpoints.db"
    cfg.embeddings = overrides.pop("embeddings", "none")
    cfg.llm_provider = overrides.pop("llm_provider", "none")
    cfg.replay = overrides.pop("replay", "off")
    cfg.time_scale = overrides.pop("time_scale", 1.0)
    cfg.typing_ms_per_char = overrides.pop("typing_ms_per_char", 0)
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


@asynccontextmanager
async def runtime(tmp_path, **overrides):
    from baton.api.deps import set_runtime
    from baton.runtime import Runtime

    rt = Runtime(make_config(tmp_path, **overrides))
    set_runtime(rt)
    await rt.start()
    try:
        yield rt
    finally:
        await rt.stop()
        set_runtime(None)


def advance(rt, seconds: int) -> None:
    """Run sim ticks synchronously (the clock loop is paused by the caller)."""
    for _ in range(seconds):
        rt._tick()

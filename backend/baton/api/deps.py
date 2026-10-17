"""Access to the process-wide Runtime from route handlers."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runtime import Runtime

_runtime: "Runtime | None" = None


def set_runtime(runtime: "Runtime | None") -> None:
    global _runtime
    _runtime = runtime


def rt() -> "Runtime":
    if _runtime is None:
        raise RuntimeError("Runtime not started")
    return _runtime

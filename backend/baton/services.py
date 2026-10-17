"""Wire the services that sit on top of the core runtime (governance, commands, knowledge, agents)."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .runtime import Runtime


async def install_services(rt: "Runtime") -> None:
    """Filled in as services land; each one attaches itself to the runtime."""
    return None

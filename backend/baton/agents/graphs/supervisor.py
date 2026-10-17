"""Supervisor (MVP spec §11.1): rules first, then the router model, then keyword rules."""
from __future__ import annotations

import re

from .. import prompts as P

CATALOG_VERBS = ("status", "show", "list", "suspend", "activate", "resume", "alter", "altpri", "stop", "reload",
                 "pause", "set", "raise", "lower", "add", "check", "info", "stats", "kill", "restart", "run", "start")
QUESTION = re.compile(r"^(what|why|how|when|where|who|which|is|are|does|do|can|should|explain|tell me|difference)\b|\?$",
                      re.IGNORECASE)
SYMPTOM = re.compile(r"\b(slow|down|failing|failed|errors?|timeouts?|what'?s going on|what is going on|problem|broken|issue)\b",
                     re.IGNORECASE)


def active_incident(rt) -> dict | None:
    for inc in rt.incidents.list():
        if inc["status"] != "resolved":
            return inc
    return None


def keyword_route(text: str) -> str:
    low = text.lower().strip()
    first = re.split(r"\W+", low, maxsplit=1)[0]
    if first in CATALOG_VERBS:
        return "command"
    if re.search(r"\b(keeping up|how busy|how full|how many|running on|is .* running|is tmf ok|status of)\b", low):
        return "command"
    if QUESTION.search(low):
        return "ask"
    return "command"


async def route(rt, thread: dict, text: str, actor: str) -> tuple[str, str | None]:
    """Return (graph name, incident_id for context)."""
    low = text.lower().strip()
    first = re.split(r"\W+", low, maxsplit=1)[0]
    incident_id = thread.get("incident_id")
    inc = rt.incidents.get(incident_id) if incident_id else None
    if first in CATALOG_VERBS and not QUESTION.search(low[:4]):
        return "command", incident_id or (active_incident(rt) or {}).get("id")
    if inc is None:
        live = active_incident(rt)
        if live and SYMPTOM.search(low):
            return "ask", live["id"]
    if inc is not None:
        return ("ask" if QUESTION.search(low) or SYMPTOM.search(low) else keyword_route(text)), inc["id"]
    if rt.gateway.live or rt.gateway.mode == "replay":
        out, _, _ = await rt.gateway.complete("router", P.SYSTEM, P.render("router", text=text, has_incident=False,
                                                                           last_mode=thread.get("mode")), P.RouterOut)
        if out and out["intent"] in ("ask", "command") and out.get("confidence", 0) >= 0.6:
            if out["intent"] == "ask" and keyword_route(text) == "command" and re.search(
                    r"\b(keeping up|how busy|how full|how many)\b", low):
                return "command", None
            return out["intent"], None
    return keyword_route(text), None

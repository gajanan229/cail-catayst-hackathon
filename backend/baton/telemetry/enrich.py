"""Enrichment (MVP spec §7.1 step 2-3): message definitions, variable extraction, component resolution,
severity, quarantine of instruction-like text, fingerprint."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .ems_parser import ParsedLine

INSTRUCTION_LIKE = re.compile(
    r"(ignore (all |any )?(previous|prior|above) instructions|disregard (all |previous )?instructions|"
    r"\bnote to (the )?(operator )?ai\b|you are now|system prompt|\bas an ai\b|run stop tmf|execute the following)",
    re.IGNORECASE,
)
SERVER_CLASS = re.compile(r"\b(ATM-AUTH|POS-AUTH|BAL-INQ|CARD-MGMT)\b")


def template_regex(template: str) -> re.Pattern:
    """'*1034* {link_manager}, NO SERVER ...' -> regex with named groups; '$' before a {var} stays literal."""
    parts = re.split(r"(\{[a-z_]+\})", template)
    out = []
    seen: set[str] = set()
    for i, part in enumerate(parts):
        if part.startswith("{") and part.endswith("}"):
            name = part[1:-1]
            last = i == len(parts) - 1
            if name in seen:
                out.append(".+?")
            else:
                seen.add(name)
                out.append(f"(?P<{name}>.+)" if last else f"(?P<{name}>.+?)")
        else:
            out.append(re.escape(part))
    return re.compile("^" + "".join(out) + "$")


@dataclass
class MessageDef:
    subsystem: str
    number: int
    template: str
    regex: re.Pattern
    critical: bool
    severity_hint: int
    real: bool
    component: str
    cause: str | None = None
    effect: str | None = None
    recovery: str | None = None
    source: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class MessageCatalog:
    def __init__(self, ems_messages: dict, content_file: Path | None = None):
        self.defs: dict[tuple[str, int], MessageDef] = {}
        for m in ems_messages["messages"]:
            self.defs[(m["subsystem"], int(m["number"]))] = MessageDef(
                subsystem=m["subsystem"], number=int(m["number"]), template=m["template"],
                regex=template_regex(m["template"]), critical=bool(m.get("critical")),
                severity_hint=int(m.get("severity_hint", 2)), real=bool(m.get("real")),
                component=m.get("component", "unknown"), cause=m.get("cause"), effect=m.get("effect"),
                recovery=m.get("recovery"), source=m.get("source"),
            )
        if content_file and content_file.exists():
            self._overlay(content_file)

    def _overlay(self, path: Path) -> None:
        """Content-pack records (real manual text) override the fallback cause/effect/recovery."""
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = (rec.get("subsystem"), int(rec.get("number", -1)))
            d = self.defs.get(key)
            if d:
                d.cause = rec.get("cause") or d.cause
                d.effect = rec.get("effect") or d.effect
                d.recovery = rec.get("recovery") or d.recovery
                d.source = rec.get("source") or d.source

    def get(self, subsystem: str, number: int) -> MessageDef | None:
        return self.defs.get((subsystem, number))


def resolve_component(d: MessageDef | None, fields: dict[str, str], parsed: ParsedLine) -> tuple[str | None, str]:
    """Map extracted variables to a component ID and a component class."""
    kind = d.component if d else "unknown"
    if "cpu" in fields and kind == "cpu":
        return f"cpu:{fields['cpu'].strip()}", "cpu"
    if "volume" in fields:
        return f"vol:${fields['volume'].strip()}", "volume"
    if "process" in fields:
        return f"proc:${fields['process'].strip()}", "process"
    if "link_manager" in fields:
        return f"proc:{fields['link_manager'].strip()}", "link_manager"
    if kind == "server":
        m = SERVER_CLASS.search(fields.get("object", ""))
        return (f"sc:{m.group(1)}" if m else f"proc:{parsed.process}"), "server"
    if kind == "pathmon":
        if parsed.number == 1166:
            m = SERVER_CLASS.search(fields.get("text", ""))
            if m:
                return f"sc:{m.group(1)}", "server_class"
        return f"proc:{parsed.process}", "pathmon"
    if kind == "tmf":
        return "tmf:mat", "tmf"
    if kind == "application":
        return None, "application"
    return f"proc:{parsed.process}", kind


def enrich(parsed: ParsedLine, catalog: MessageCatalog) -> dict:
    d = catalog.get(parsed.subsystem, parsed.number)
    fields: dict[str, str] = {}
    if d:
        m = d.regex.match(parsed.text)
        if m:
            fields = {k: v for k, v in m.groupdict().items() if v is not None}
    component_id, component_class = resolve_component(d, fields, parsed)
    severity = d.severity_hint if d else 2
    if parsed.critical:
        severity = max(severity, 4)
    quarantined = bool(INSTRUCTION_LIKE.search(parsed.text))
    if quarantined:
        severity = 1
    fingerprint = f"{parsed.subsystem}:{parsed.number}:{component_class}"
    return {
        "sim_at": parsed.at,
        "system": parsed.system,
        "process": parsed.process,
        "subsystem": parsed.subsystem,
        "event_number": parsed.number,
        "critical": parsed.critical,
        "severity": severity,
        "text": parsed.text,
        "raw": parsed.raw,
        "fields": fields,
        "component_id": component_id,
        "component_class": component_class,
        "fingerprint": fingerprint,
        "quarantined": quarantined,
        "simulated": not (d.real if d else False),
        "manual": {"cause": d.cause, "effect": d.effect, "recovery": d.recovery, "url": d.source} if d and d.real else None,
    }

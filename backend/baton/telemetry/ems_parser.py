"""Parse printing-format EMS lines into canonical events (MVP spec §7.1 step 1)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

HEADER = re.compile(
    r"^(?P<date>\d\d-\d\d-\d\d) (?P<time>\d\d:\d\d:\d\d) "
    r"(?P<system>\\[A-Z0-9]+)\.(?P<process>\$[A-Z0-9]+)\s+"
    r"(?P<critical>\*)?\s*"
    r"(?P<owner>[A-Z0-9]+)\.(?P<subsystem>[A-Z0-9]+)\.(?P<version>[A-Z0-9]+)\s+"
    r"(?P<number>\d{6}) (?P<text>.*)$"
)


@dataclass
class ParsedLine:
    at: datetime
    system: str
    process: str
    critical: bool
    owner: str
    subsystem: str
    version: str
    number: int
    text: str
    raw: str


def parse_line(line: str) -> ParsedLine | None:
    m = HEADER.match(line.rstrip("\r\n"))
    if not m:
        return None
    at = datetime.strptime(f"{m['date']} {m['time']}", "%y-%m-%d %H:%M:%S")
    return ParsedLine(
        at=at, system=m["system"], process=m["process"], critical=m["critical"] == "*", owner=m["owner"],
        subsystem=m["subsystem"], version=m["version"], number=int(m["number"]), text=m["text"], raw=line,
    )

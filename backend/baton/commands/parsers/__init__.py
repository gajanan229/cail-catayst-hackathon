"""Output parsers: utility text → facts (MVP spec §8.2). One parser per output layout; each returns
(facts, confidence). Confidence 1.0 when every expected row parsed, lower when some did not."""
from __future__ import annotations

import re
from typing import Callable

Parsed = tuple[dict, float]


def _body(lines: list[str]) -> list[str]:
    """Drop the echoed prompt line if present."""
    return [l for l in lines if l.strip() and not re.match(r"^\$\S+ \S+ \d+> ", l)]


def meas_cpu(lines: list[str]) -> Parsed:
    cpus = {}
    rows = _body(lines)[1:]
    for l in rows:
        m = re.match(r"^\s*(\d+)\s+(UP|DOWN)\s+([\d.]+|-)\s*$", l)
        if m:
            cpus[int(m.group(1))] = {"state": m.group(2), "busy": None if m.group(3) == "-" else float(m.group(3))}
    up = {c: v["busy"] for c, v in cpus.items() if v["state"] == "UP"}
    hottest = max(up, key=lambda c: up[c]) if up else None
    facts = {"cpus": {str(c): v for c, v in cpus.items()}, "down": [c for c, v in cpus.items() if v["state"] == "DOWN"],
             "hottest_cpu": hottest, "hottest_busy": up.get(hottest) if hottest is not None else None}
    return facts, (1.0 if cpus and len(cpus) == len(rows) else 0.5 if cpus else 0.0)


def tacl_status_cpu(lines: list[str]) -> Parsed:
    procs = []
    rows = _body(lines)[1:]
    for l in rows:
        m = re.match(r"^(\S+)\s+(\d+)\s+(\S+)\s+([\d.]+)\s*$", l)
        if m:
            procs.append({"name": m.group(1), "priority": int(m.group(2)), "state": m.group(3), "busy": float(m.group(4))})
    top = procs[0] if procs else None
    return {"processes": procs, "top_process": top["name"] if top else None,
            "top_busy": top["busy"] if top else None}, (1.0 if procs and len(procs) == len(rows) else 0.5 if procs else 0.0)


def tacl_status_process(lines: list[str]) -> Parsed:
    for l in _body(lines)[1:]:
        m = re.match(r"^(\$\S+)\s+(\S+)\s+(\d+)\s+(\d+)\s+(\S+)\s*$", l)
        if m:
            return {"process": m.group(1), "state": m.group(2), "priority": int(m.group(3)), "cpu": int(m.group(4)),
                    "backup_cpu": None if m.group(5) == "-" else int(m.group(5))}, 1.0
    return {}, 0.0


def pathcom_status_pathmon(lines: list[str]) -> Parsed:
    for l in _body(lines)[1:]:
        m = re.match(r"^(\$\S+)\s+(\S+)\s+(\d+)\s+(\S+)\s*$", l)
        if m:
            return {"pathmon": m.group(1), "state": m.group(2), "primary_cpu": int(m.group(3)),
                    "backup_cpu": None if m.group(4) == "-" else int(m.group(4))}, 1.0
    return {}, 0.0


def pathcom_status_server(lines: list[str]) -> Parsed:
    for l in _body(lines)[1:]:
        m = re.match(r"^(\S+)\s+(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$", l)
        if m:
            return {"server_class": m.group(1), "state": m.group(2), "running": int(m.group(3)),
                    "numstatic": int(m.group(4)), "maxservers": int(m.group(5)), "links": int(m.group(6)),
                    "queued": int(m.group(7)), "avg_ms": int(m.group(8))}, 1.0
    return {}, 0.0


def pathcom_info_server(lines: list[str]) -> Parsed:
    for l in _body(lines)[1:]:
        m = re.match(r"^(\S+)\s+\(([\d,]+)\)\s+(\d+)\s+(\d+)\s+(\d+)\s*$", l)
        if m:
            return {"server_class": m.group(1), "cpus": [int(c) for c in m.group(2).split(",")],
                    "numstatic": int(m.group(3)), "maxservers": int(m.group(4)), "maxlinks": int(m.group(5))}, 1.0
    return {}, 0.0


def pathcom_stats_server(lines: list[str]) -> Parsed:
    for l in _body(lines)[1:]:
        m = re.match(r"^(\S+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$", l)
        if m:
            return {"server_class": m.group(1), "requests_per_s": float(m.group(2)), "avg_ms": float(m.group(3)),
                    "max_ms": float(m.group(4))}, 1.0
    return {}, 0.0


def tmfcom_status_tmf(lines: list[str]) -> Parsed:
    for l in _body(lines)[1:]:
        m = re.match(r"^(\S+)\s+(\S+)\s+([\d.]+)\s+([\d.]+)\s*$", l)
        if m:
            return {"state": m.group(2), "tps": float(m.group(3)), "aborts_per_s": float(m.group(4))}, 1.0
    return {}, 0.0


def tmfcom_status_audittrail(lines: list[str]) -> Parsed:
    for l in _body(lines)[1:]:
        m = re.match(r"^(\S+)\s+(\S+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\S+)\s*$", l)
        if m:
            return {"trail": m.group(1), "file_id": m.group(2), "fill_pct": float(m.group(3)),
                    "overflow_pct": float(m.group(4)), "btd_pct": float(m.group(5)), "dumps": m.group(6)}, 1.0
    return {}, 0.0


def scf_status_disk(lines: list[str]) -> Parsed:
    halves = {}
    pair = None
    note = []
    for l in _body(lines)[1:]:
        m = re.match(r"^(\$\S+)\s+(-[PM])\s+(\S+)\s*(.*)$", l)
        if m:
            halves[m.group(2)] = m.group(3)
            if m.group(4):
                note.append(m.group(4).strip())
        m2 = re.match(r"^PROCESS PAIR: (\S+)", l)
        if m2:
            pair = m2.group(1)
    return {"primary_half": halves.get("-P"), "mirror_half": halves.get("-M"), "process_pair": pair,
            "notes": note}, (1.0 if len(halves) == 2 else 0.5 if halves else 0.0)


def tacl_ack(lines: list[str]) -> Parsed:
    for l in _body(lines):
        m = re.match(r"^PROCESS (\$\S+) (SUSPENDED|ACTIVATED|STOPPED)", l)
        if m:
            return {"process": m.group(1), "state": {"ACTIVATED": "RUNNING"}.get(m.group(2), m.group(2))}, 1.0
        m = re.match(r"^PROCESS (\$\S+) PRIORITY (\d+) \(WAS (\d+)\)", l)
        if m:
            return {"process": m.group(1), "priority": int(m.group(2)), "previous_priority": int(m.group(3))}, 1.0
    return {"error": " ".join(_body(lines))}, 0.0


def pathcom_ack(lines: list[str]) -> Parsed:
    facts: dict = {}
    for l in _body(lines):
        m = re.match(r"^SERVER (\S+) ALTERED: (NUMSTATIC|MAXSERVERS) (\d+) \(WAS (\d+)\)", l)
        if m:
            facts.update({"server_class": m.group(1), m.group(2).lower(): int(m.group(3)),
                          "previous": int(m.group(4))})
        m = re.match(r"^(\d+) SERVERS STARTING ON CPUS ([\d,]+)", l)
        if m:
            facts.update({"servers_starting": int(m.group(1)), "on_cpus": [int(c) for c in m.group(2).split(",")]})
        m = re.match(r"^\*ERROR\* (\d+) (.*)$", l)
        if m:
            facts.update({"error": int(m.group(1)), "error_text": m.group(2)})
    return facts, (1.0 if facts and "error" not in facts else 0.0)


PARSERS: dict[str, Callable[[list[str]], Parsed]] = {
    "meas_cpu": meas_cpu, "tacl_status_cpu": tacl_status_cpu, "tacl_status_process": tacl_status_process,
    "pathcom_status_pathmon": pathcom_status_pathmon, "pathcom_status_server": pathcom_status_server,
    "pathcom_info_server": pathcom_info_server, "pathcom_stats_server": pathcom_stats_server,
    "tmfcom_status_tmf": tmfcom_status_tmf, "tmfcom_status_audittrail": tmfcom_status_audittrail,
    "scf_status_disk": scf_status_disk, "tacl_ack": tacl_ack, "pathcom_ack": pathcom_ack,
}


def parse(parser_id: str, lines: list[str]) -> Parsed:
    fn = PARSERS.get(parser_id)
    if fn is None:
        return {}, 0.0
    return fn(lines)

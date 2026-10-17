"""EMS emitter: printing-distributor style lines (MVP spec §6.5, Appendix A).

    26-11-27 11:52:04 \\TORBANK.$ZOMF    * TANDEM.OMF.L01      000103 CPU 3, Current State = DOWN, ...
"""
from __future__ import annotations

import random
from datetime import datetime

from .model import SimModel

PROCESS_WIDTH = 18
OWNER_WIDTH = 20


def format_line(system: str, process: str, owner: str, subsystem: str, version: str, number: int,
                text: str, critical: bool, at: datetime) -> str:
    origin = f"{system}.{process}"
    flag = "* " if critical else "  "
    owner_id = f"{owner}.{subsystem}.{version}"
    return f"{at:%y-%m-%d %H:%M:%S} {origin:<{PROCESS_WIDTH}}{flag}{owner_id:<{OWNER_WIDTH}}{number:06d} {text}"


class Emitter:
    def __init__(self, system: str, messages: dict, seed: int, chatter_per_min: float, injection: bool):
        self.system = system
        self.version = messages.get("format_version_token", "L01")
        self.defs = {(m["subsystem"], int(m["number"])): m for m in messages["messages"]}
        self.chatter = messages.get("chatter") or []
        self.weights = [c["weight"] for c in self.chatter]
        self.injection_cfg = messages.get("injection_test") if injection else None
        self.injection_done = False
        self.rng = random.Random(seed * 1000 + 2)
        self.chatter_per_min = chatter_per_min
        self.chatter_acc = 0.0
        self.counter = 1000
        self.cpu_over_since: dict[int, int] = {}
        self.cpu_last_101: dict[int, int] = {}
        self.cpu_last_102: dict[int, int] = {}
        self.link_acc: dict[str, float] = {}
        self.audit_last_1204 = -999

    # ------------------------------------------------------------ helpers

    def line(self, subsystem: str, number: int, at: datetime, process: str | None = None, **vars) -> str:
        d = self.defs[(subsystem, number)]
        text = d["template"].format(**vars) if vars or "{" in d["template"] else d["template"]
        proc = process or d.get("process")
        if proc in (None, "link_manager", "app"):
            proc = vars.get("link_manager") or "$ZAPP"
        return format_line(self.system, proc, d.get("owner", "TANDEM"), subsystem, self.version, number, text,
                           bool(d.get("critical")), at)

    def _omf_process(self, number: int, at: datetime, name: str, **vars) -> str:
        """OMF process-state messages: the line's origin is $ZOMF and the text names the process."""
        d = self.defs[("OMF", number)]
        text = d["template"].replace("${process}", name).format(**vars)
        return format_line(self.system, "$ZOMF", "TANDEM", "OMF", self.version, number, text, bool(d.get("critical")), at)

    def app_line(self, process: str, text: str, at: datetime) -> str:
        return format_line(self.system, process, "TORBANK", "APP", self.version, 512, text, False, at)

    # ------------------------------------------------------------ per tick

    def tick(self, m: SimModel) -> list[str]:
        out: list[str] = []
        at = m.now
        out += self._chatter(m, at)
        out += self._cpu_threshold(m, at)
        out += self._link_errors(m, at)
        out += self._audit(m, at)
        if self.injection_cfg and not self.injection_done and m.tick >= int(self.injection_cfg.get("at_s", 150)):
            self.injection_done = True
            out.append(self.app_line(self.injection_cfg["process"], self.injection_cfg["text"], at))
        return out

    def _chatter(self, m: SimModel, at: datetime) -> list[str]:
        if not self.chatter:
            return []
        self.chatter_acc += self.chatter_per_min / 60.0
        n = int(self.chatter_acc)
        self.chatter_acc -= n
        out = []
        for _ in range(n):
            c = self.rng.choices(self.chatter, weights=self.weights)[0]
            if c["subsystem"] == "APP":
                self.counter += self.rng.randint(1, 9)
                out.append(self.app_line(c["process"], c["text"].format(n=self.counter), at))
            elif c["number"] == 600:
                procs = [p for p in m.processes.values() if p.state == "RUNNING" and m.cpu_up[p.cpu]]
                p = self.rng.choice(procs)
                out.append(self._omf_process(600, at, p.name, prev="RUNNING", n=1))
            elif c["number"] == 1203:
                if m.tmf.fill_pct < 70:
                    out.append(self.line("OMF", 1203, at, id=m.tmf.file_id, usage=f"{m.tmf.fill_pct:.0f}%", thr="70%"))
        return out

    def _cpu_threshold(self, m: SimModel, at: datetime) -> list[str]:
        out = []
        for c in range(m.cpu_count):
            busy = m.cpu_busy[c]
            if not m.cpu_up[c] or busy < 90.0:
                self.cpu_over_since.pop(c, None)
                continue
            since = self.cpu_over_since.setdefault(c, m.tick)
            if m.tick - since < 5:
                continue
            if m.tick - self.cpu_last_101.get(c, -999) >= 60:
                self.cpu_last_101[c] = m.tick
                out.append(self.line("OMF", 101, at, cpu=c, prev="NORMAL", usage=f"{busy:.0f}%", thr="90%", n=1))
            if m.cpu_raw[c] >= 100.0 and m.tick - self.cpu_last_102.get(c, -999) >= 60:
                self.cpu_last_102[c] = m.tick
                out.append(self.line("OMF", 102, at, cpu=c, prev="OVER THRESHOLD", usage="100%", thr="90%", n=1))
        return out

    def _link_errors(self, m: SimModel, at: datetime) -> list[str]:
        out = []
        for sc in m.classes.values():
            if not sc.link_managers or sc.queued <= 50:
                continue
            per_min = max(30.0, min(60.0, 30.0 + (sc.queued - 50.0) / 4.0))
            lms = [lm for lm in sc.link_managers if m.processes.get(lm) and m.cpu_up[m.processes[lm].cpu]]
            for lm in lms:
                self.link_acc[lm] = self.link_acc.get(lm, 0.0) + per_min / 60.0 / len(lms) * (0.8 + 0.4 * self.rng.random())
                while self.link_acc[lm] >= 1.0:
                    self.link_acc[lm] -= 1.0
                    nested = f"*1034* {lm}, NO SERVER AVAILABLE FOR REQUESTING TCP"
                    out.append(self.line("PATHWAY", 1007, at, process=lm, link_manager=lm, nested=nested))
        return out

    def _audit(self, m: SimModel, at: datetime) -> list[str]:
        if m.tmf.fill_pct >= 70.0 and m.tick - self.audit_last_1204 >= 60:
            self.audit_last_1204 = m.tick
            return [self.line("OMF", 1204, at, id=m.tmf.file_id, usage=f"{m.tmf.fill_pct:.0f}%", thr="70%")]
        return []

    # ------------------------------------------------------------ faults and actions

    def cpu_halt(self, m: SimModel, result: dict) -> list[str]:
        at = m.now
        cpu = result["cpu"]
        out = [self.line("OMF", 103, at, cpu=cpu, prev="UP", n=1)]
        for name in result["moved"]:
            p = m.processes[name]
            if p.role == "pathmon":
                out.append(self.line("PATHWAY", 1077, at, process=name))
                out.append(self.line("PATHWAY", 1093, at, process=name, object=f"PATHMON {name}"))
            elif p.role == "disk":
                out.append(self.line("OMF", 217, at, volume=name[1:], n=1))
        for name in result["stopped"]:
            p = m.processes[name]
            if p.is_batch:
                out.append(self._omf_process(608, at, name, prev="RUNNING", cpu=cpu, pri=p.priority, n=1))
        return out

    def process_state(self, m: SimModel, name: str, state: str, prev: str) -> list[str]:
        p = m.processes[name]
        number = {"SUSPENDED": 604, "RUNNING": 600, "STOPPED": 608}[state]
        if number == 600:
            return [self._omf_process(600, m.now, name, prev=prev, n=1)]
        return [self._omf_process(number, m.now, name, prev=prev, cpu=p.cpu, pri=p.priority, n=1)]

    def pathcom_alter(self, m: SimModel, pathmon: str, text: str, started: list[tuple[str, int]]) -> list[str]:
        out = [self.line("PATHWAY", 1166, m.now, process=pathmon, text=text)]
        for proc, _cpu in started:
            out.append(self.line("PATHWAY", 1043, m.now, process=pathmon, object=proc))
        return out

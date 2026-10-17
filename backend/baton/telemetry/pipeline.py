"""Deterministic EMS pipeline (MVP spec §7.1): parse → enrich → fingerprint → episodes → signals →
correlate → situations → escalate. Runs in-process, one `ingest()` per sim-second."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable

from ..core.ids import new_id
from ..core.timeutil import iso_sim, wall_now
from .ems_parser import parse_line
from .enrich import MessageCatalog, enrich

GAP_TIMEOUT_S = 120
STABLE_AFTER_S = 180
RESOLVE_AFTER_S = 120
BENIGN = {("APP", 512), ("OMF", 600), ("OMF", 1203), ("PATHWAY", 1043)}
SERVICE_SHORT = {"atm": "ATM", "pos": "POS", "bal": "Balance inquiry", "card": "Card maintenance"}
SIGNAL_SEVERITY = {"cpu_down": 5, "latency_out_of_band": 4, "audit_fill_high": 4, "sc_queue": 3, "sc_at_max": 3,
                   "cpu_busy_high": 3, "link_errors": 3, "takeover": 3, "audit_over_threshold_event": 4,
                   "audit_fill_rising": 3}


@dataclass
class EpisodeState:
    id: str
    key: tuple
    fingerprint: str
    subsystem: str
    event_number: int
    component_id: str | None
    severity: int
    critical: bool
    quarantined: bool
    first_at: datetime
    last_at: datetime
    example_text: str
    manual: dict | None
    count: int = 0
    exemplars: list[str] = field(default_factory=list)
    recent: deque = field(default_factory=lambda: deque(maxlen=400))
    status: str = "open"

    def to_dict(self, now: datetime) -> dict:
        cutoff = now - timedelta(seconds=60)
        rate = sum(1 for t in self.recent if t >= cutoff)
        return {
            "id": self.id, "fingerprint": self.fingerprint, "subsystem": self.subsystem,
            "event_number": self.event_number, "example_text": self.example_text, "component_id": self.component_id,
            "count": self.count, "rate_per_min": float(rate), "first_at": iso_sim(self.first_at),
            "last_at": iso_sim(self.last_at), "severity": self.severity, "critical": self.critical,
            "quarantined": self.quarantined, "status": self.status, "manual": self.manual,
        }


@dataclass
class SignalState:
    id: str
    kind: str
    component_id: str
    started_at: datetime
    ended_at: datetime | None = None
    value: float | None = None
    detail: str = ""
    last_seen: datetime | None = None
    situation_id: str | None = None

    @property
    def active(self) -> bool:
        return self.ended_at is None

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "component_id": self.component_id,
                "started_at": iso_sim(self.started_at), "ended_at": iso_sim(self.ended_at),
                "value": self.value, "detail": self.detail}


@dataclass
class SituationState:
    id: str
    template: str
    title: str
    severity: int
    origin: str
    first_at: datetime
    last_at: datetime
    services: list[str]
    components: list[str]
    suggested_playbooks: list[str]
    status: str = "open"
    incident_id: str | None = None
    episode_ids: list[str] = field(default_factory=list)
    signal_ids: list[str] = field(default_factory=list)
    last_member_at: datetime | None = None
    all_clear_since: datetime | None = None
    vars: dict = field(default_factory=dict)


class Pipeline:
    def __init__(self, catalog: MessageCatalog, templates: dict, rules: dict, publish: Callable,
                 store=None, impact_fn: Callable[[int], list[dict]] | None = None,
                 on_situation_opened: Callable[[dict], None] | None = None):
        self.catalog = catalog
        self.templates = templates
        self.rules = rules["signals"]
        self.publish = publish
        self.store = store
        self.impact_fn = impact_fn or (lambda cpu: [])
        self.on_situation_opened = on_situation_opened
        self.reset()

    def reset(self) -> None:
        self.events: deque = deque(maxlen=5000)
        self.raw_total = 0
        self.episodes: dict[str, EpisodeState] = {}
        self.episode_by_key: dict[tuple, EpisodeState] = {}
        self.signals: dict[str, SignalState] = {}
        self.signal_by_key: dict[tuple, SignalState] = {}
        self.situations: dict[str, SituationState] = {}
        self.cond_since: dict[tuple, datetime] = {}
        self.event_times: dict[str, deque] = {"link": deque(maxlen=2000)}
        self.fill_hist: deque = deque(maxlen=120)
        self.dirty_episodes: set[str] = set()
        self.dirty_situations: set[str] = set()
        self.minute_counts: deque = deque(maxlen=61)
        self.now: datetime | None = None
        self.pending_rows: list[tuple] = []

    # ------------------------------------------------------------ ingest

    def ingest(self, lines: list[str], now: datetime, values: dict[str, float]) -> None:
        self.now = now
        self.minute_counts.append((now, len(lines)))
        for line in lines:
            parsed = parse_line(line)
            if not parsed:
                continue
            ev = enrich(parsed, self.catalog)
            self._episode(ev)
            self._event_signals(ev)
            self.raw_total += 1
        self._metric_signals(now, values)
        self._expire_event_signals(now)
        self._correlate(now)
        self._lifecycle(now)
        if self.store is not None and self.pending_rows:
            self.store.executemany(
                "INSERT OR IGNORE INTO events (id, sim_ts, wall_ts, subsystem, event_number, component_id, episode_id, quarantined, data) "
                "VALUES (?,?,?,?,?,?,?,?,?)", self.pending_rows)
            self.pending_rows = []
        self._flush_situations()

    def _episode(self, ev: dict) -> None:
        key = (ev["fingerprint"], ev["component_id"], ev["quarantined"])
        ep = self.episode_by_key.get(key)
        at = ev["sim_at"]
        if ep is None or (at - ep.last_at).total_seconds() > GAP_TIMEOUT_S:
            if ep is not None:
                ep.status = "closed"
                self.dirty_episodes.add(ep.id)
            ep = EpisodeState(id=new_id("epi"), key=key, fingerprint=ev["fingerprint"], subsystem=ev["subsystem"],
                              event_number=ev["event_number"], component_id=ev["component_id"], severity=ev["severity"],
                              critical=ev["critical"], quarantined=ev["quarantined"], first_at=at, last_at=at,
                              example_text=ev["text"], manual=ev["manual"])
            self.episodes[ep.id] = ep
            self.episode_by_key[key] = ep
            if len(self.episodes) > 3000:
                for old in list(self.episodes.values())[:500]:
                    if old.status == "closed":
                        self.episodes.pop(old.id, None)
        ep.count += 1
        ep.last_at = at
        ep.severity = max(ep.severity, ev["severity"]) if not ep.quarantined else 1
        ep.recent.append(at)
        if len(ep.exemplars) < 2 and ev["text"] not in ep.exemplars:
            ep.exemplars.append(ev["text"])
        self.dirty_episodes.add(ep.id)
        eid = new_id("evt")
        record = {
            "id": eid, "sim_ts": iso_sim(at), "system": ev["system"], "process": ev["process"],
            "subsystem": ev["subsystem"], "event_number": ev["event_number"], "critical": ev["critical"],
            "severity": ev["severity"], "text": ev["text"], "raw": ev["raw"], "fields": ev["fields"],
            "component_id": ev["component_id"], "fingerprint": ev["fingerprint"], "episode_id": ep.id,
            "quarantined": ev["quarantined"], "simulated": ev["simulated"],
        }
        self.events.append(record)
        self.pending_rows.append((eid, record["sim_ts"], wall_now(), ev["subsystem"], ev["event_number"],
                                  ev["component_id"], ep.id, int(ev["quarantined"]), _json(record)))
        # attach to an open situation when relevant
        if not ev["quarantined"] and (ev["subsystem"], ev["event_number"]) not in BENIGN:
            for sit in self.situations.values():
                if sit.status != "resolved" and at >= sit.first_at - timedelta(seconds=60) and ep.id not in sit.episode_ids:
                    if self._episode_relevant(sit, ep):
                        sit.episode_ids.append(ep.id)
                        sit.last_member_at = at
                        self._touch(sit)

    def _episode_relevant(self, sit: SituationState, ep: EpisodeState) -> bool:
        if sit.template in ("cpu_loss_cascade", "fallback"):
            return ep.subsystem in ("OMF", "PATHWAY") and ep.event_number not in (1203, 1204)
        if sit.template == "audit_trail_pressure":
            return ep.subsystem == "OMF" and ep.event_number in (1204, 604, 101)
        return False

    # ------------------------------------------------------------ signals

    def _signal(self, kind: str, component: str, at: datetime, value: float | None = None, detail: str = "") -> SignalState:
        key = (kind, component)
        sig = self.signal_by_key.get(key)
        if sig is None or not sig.active:
            sig = SignalState(id=new_id("sig"), kind=kind, component_id=component, started_at=at, value=value, detail=detail)
            self.signals[sig.id] = sig
            self.signal_by_key[key] = sig
            if self.store is not None:
                self.store.put("signals", sig.id, sig.to_dict(), kind=kind, component_id=component,
                               started_at=iso_sim(at), ended_at=None)
        sig.last_seen = at
        if value is not None:
            sig.value = value
        if detail:
            sig.detail = detail
        return sig

    def _end_signal(self, kind: str, component: str, at: datetime) -> None:
        sig = self.signal_by_key.get((kind, component))
        if sig and sig.active:
            sig.ended_at = at
            if self.store is not None:
                self.store.put("signals", sig.id, sig.to_dict(), kind=kind, component_id=component,
                               started_at=iso_sim(sig.started_at), ended_at=iso_sim(at))

    def _event_signals(self, ev: dict) -> None:
        at, sub, num = ev["sim_at"], ev["subsystem"], ev["event_number"]
        if ev["quarantined"]:
            return
        if sub == "OMF" and num == 103 and ev["component_id"]:
            self._signal("cpu_down", ev["component_id"], at, detail=f"{ev['component_id'].replace('cpu:', 'CPU ')} down (OMF 103)")
        elif (sub == "PATHWAY" and num == 1077) or (sub == "OMF" and num == 217):
            self._signal("takeover", ev["component_id"] or "proc:$PM1", at,
                         detail="PATHMON takeover by backup (PATHWAY 1077)" if num == 1077 else f"{ev['component_id']} on backup (OMF 217)")
        elif sub == "PATHWAY" and num in (1007, 1034):
            times = self.event_times["link"]
            times.append(at)
            cfg = self.rules["link_errors"]
            cutoff = at - timedelta(seconds=cfg["window_s"])
            n = sum(1 for t in times if t >= cutoff)
            if n >= cfg["min_count"]:
                self._signal("link_errors", "pathway:$PM1", at, value=float(n), detail=f"{n} link errors (1007/1034) in 2 min")
        elif sub == "OMF" and num == 1204:
            self._signal("audit_over_threshold_event", "tmf:mat", at, detail="Audit trail over threshold (OMF 1204)")

    def _expire_event_signals(self, now: datetime) -> None:
        clear = self.rules.get("clear_after_s", 120)
        for sig in list(self.signals.values()):
            if sig.active and sig.kind in ("takeover", "link_errors", "audit_over_threshold_event"):
                if sig.last_seen and (now - sig.last_seen).total_seconds() > clear:
                    self._end_signal(sig.kind, sig.component_id, now)

    def _held(self, key: tuple, cond: bool, now: datetime, for_s: float) -> bool:
        if not cond:
            self.cond_since.pop(key, None)
            return False
        since = self.cond_since.setdefault(key, now)
        return (now - since).total_seconds() >= for_s

    def _metric_signals(self, now: datetime, v: dict[str, float]) -> None:
        r = self.rules
        n_cpu = sum(1 for k in v if k.startswith("cpu.") and k.endswith(".up"))
        for c in range(n_cpu):
            comp = f"cpu:{c}"
            if v.get(f"cpu.{c}.up", 1.0) < 0.5:
                self._signal("cpu_down", comp, now, detail=f"CPU {c} down")
            else:
                self._end_signal("cpu_down", comp, now)
            busy = v.get(f"cpu.{c}.busy", 0.0)
            if self._held(("busy", c), busy >= r["cpu_busy_high"]["threshold"], now, r["cpu_busy_high"]["for_s"]):
                self._signal("cpu_busy_high", comp, now, value=busy, detail=f"CPU {c} at {busy:.0f}%")
            elif busy < r["cpu_busy_high"]["threshold"] - 3:
                self._end_signal("cpu_busy_high", comp, now)
        for svc in ("atm", "pos"):
            p95, hi = v.get(f"svc.{svc}.p95_ms"), v.get(f"svc.{svc}.band_high")
            if p95 is None or hi is None:
                continue
            comp = f"svc:{svc}"
            if self._held(("lat", svc), p95 > hi, now, r["latency_out_of_band"]["for_s"]):
                self._signal("latency_out_of_band", comp, now, value=p95,
                             detail=f"{SERVICE_SHORT[svc]} p95 {p95:.0f} ms above band ({hi:.0f} ms)")
            elif p95 <= hi:
                self._end_signal("latency_out_of_band", comp, now)
        classes = {k.split(".")[1] for k in v if k.startswith("sc.")}
        for cls in classes:
            comp = f"sc:{cls}"
            q, run, mx = v.get(f"sc.{cls}.queued", 0), v.get(f"sc.{cls}.running", 0), v.get(f"sc.{cls}.max", 0)
            if self._held(("q", cls), q >= r["sc_queue"]["threshold"], now, r["sc_queue"]["for_s"]):
                self._signal("sc_queue", comp, now, value=q, detail=f"{cls} {q:.0f} queued")
            elif q < 1:
                self._end_signal("sc_queue", comp, now)
            if self._held(("max", cls), mx > 0 and run >= mx, now, r["sc_at_max"]["for_s"]):
                self._signal("sc_at_max", comp, now, value=run, detail=f"{cls} at MAXSERVERS ({run:.0f}/{mx:.0f})")
            elif run < mx:
                self._end_signal("sc_at_max", comp, now)
        fill = v.get("tmf.mat.fill_pct")
        if fill is not None:
            self.fill_hist.append((now, fill))
            if fill >= r["audit_fill_high"]["threshold"]:
                self._signal("audit_fill_high", "tmf:mat", now, value=fill, detail=f"Audit trail {fill:.0f}% full")
            elif fill < r["audit_fill_high"]["threshold"] - 3:
                self._end_signal("audit_fill_high", "tmf:mat", now)
            trend = self.fill_trend()
            if trend is not None and trend > r["audit_fill_rising"]["per_min"]:
                self._signal("audit_fill_rising", "tmf:mat", now, value=trend, detail=f"Audit fill rising {trend:.1f}%/min")
            elif trend is not None and trend <= 0:
                self._end_signal("audit_fill_rising", "tmf:mat", now)

    def fill_trend(self) -> float | None:
        """Least-squares slope of audit fill over the last ~5 minutes, in % per minute."""
        pts = [(t, f) for t, f in self.fill_hist]
        if len(pts) < 10:
            return None
        cutoff = pts[-1][0] - timedelta(seconds=300)
        pts = [(t, f) for t, f in pts if t >= cutoff]
        if len(pts) < 10:
            return None
        t0 = pts[0][0]
        xs = [(t - t0).total_seconds() / 60.0 for t, _ in pts]
        ys = [f for _, f in pts]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        den = sum((x - mx) ** 2 for x in xs)
        if den == 0:
            return 0.0
        return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den

    # ------------------------------------------------------------ correlation

    def _free_signals(self) -> list[SignalState]:
        return [s for s in self.signals.values() if s.active and s.situation_id is None]

    def _correlate(self, now: datetime) -> None:
        window = timedelta(seconds=self.templates.get("window_s", 300))
        free = self._free_signals()
        # attach new signals to open situations first
        for sig in free:
            for sit in self.situations.values():
                if sit.status != "resolved" and sig.started_at >= sit.first_at - window and self._signal_relevant(sit, sig):
                    sig.situation_id = sit.id
                    sit.signal_ids.append(sig.id)
                    sit.last_member_at = now
                    if sig.component_id not in sit.components:
                        sit.components.append(sig.component_id)
                    if sig.kind == "latency_out_of_band" and sig.component_id not in sit.services:
                        sit.services.append(sig.component_id)
                    self._touch(sit)
                    break
        free = self._free_signals()
        for tpl in self.templates.get("templates", []):
            for anchor in [s for s in free if s.kind == tpl["anchor"] and s.situation_id is None]:
                partners = [s for s in free if s.kind in tpl["any_of"] and s.situation_id is None
                            and abs((s.started_at - anchor.started_at).total_seconds()) <= window.total_seconds()]
                if partners:
                    self._open(tpl, anchor, partners, now)
        free = self._free_signals()
        fb = self.templates.get("fallback")
        if fb and free:
            by_comp: dict[str, list[SignalState]] = {}
            for s in free:
                if (now - s.started_at).total_seconds() < 5:
                    continue      # give the causal templates a moment first
                by_comp.setdefault(s.component_id, []).append(s)
            for comp, sigs in by_comp.items():
                if len(sigs) >= fb.get("min_signals", 2):
                    self._open_fallback(fb, comp, sigs, now)

    def _signal_relevant(self, sit: SituationState, sig: SignalState) -> bool:
        if sit.template == "cpu_loss_cascade":
            return sig.kind in ("takeover", "link_errors", "latency_out_of_band", "cpu_busy_high", "sc_queue",
                                "cpu_down", "sc_at_max") and not (sig.kind == "cpu_down" and sig.component_id != sit.origin)
        if sit.template == "audit_trail_pressure":
            return sig.component_id == "tmf:mat"
        if sit.template == "fallback":
            related = {sit.origin, *sit.components}
            return sig.component_id in related or sig.kind in ("link_errors", "latency_out_of_band")
        return False

    def _open(self, tpl: dict, anchor: SignalState, partners: list[SignalState], now: datetime) -> None:
        vars: dict[str, Any] = {}
        services: list[str] = []
        components = [anchor.component_id]
        if tpl["id"] == "cpu_loss_cascade":
            cpu = int(anchor.component_id.split(":")[1])
            vars["cpu"] = cpu
            impacts = sorted(self.impact_fn(cpu), key=lambda i: -i.get("rho_after", 0))
            for imp in impacts:
                components.append(f"sc:{imp['server_class']}")
            if impacts:
                services = [f"svc:{impacts[0]['service']}"]
                vars["service"] = SERVICE_SHORT.get(impacts[0]["service"], impacts[0]["service"])
            else:
                vars["service"] = "service"
        elif tpl["id"] == "audit_trail_pressure":
            h = self.now.hour if self.now else 0
            vars["window"] = "the month-end batch window" if h >= 21 else "the business day"
        title = tpl["title"].format(**vars)
        sit = SituationState(id=new_id("sit"), template=tpl["id"], title=title, severity=int(tpl.get("severity", 4)),
                             origin=anchor.component_id, first_at=anchor.started_at, last_at=now, services=services,
                             components=components, suggested_playbooks=list(tpl.get("suggested_playbooks") or []),
                             vars=vars, last_member_at=now)
        for s in [anchor, *partners]:
            s.situation_id = sit.id
            sit.signal_ids.append(s.id)
            if s.component_id not in sit.components:
                sit.components.append(s.component_id)
        self._attach_existing_episodes(sit)
        self.situations[sit.id] = sit
        self._touch(sit)
        self._flush_situations()
        if self.on_situation_opened:
            self.on_situation_opened(self.situation_dict(sit))

    def _open_fallback(self, fb: dict, comp: str, sigs: list[SignalState], now: datetime) -> None:
        name = comp.split(":", 1)[1] if ":" in comp else comp
        services = []
        if comp.startswith("sc:"):
            services = [f"svc:{svc}" for cls, svc in (("ATM-AUTH", "atm"), ("POS-AUTH", "pos"), ("BAL-INQ", "bal"),
                                                     ("CARD-MGMT", "card")) if cls == name]
        elif comp.startswith("svc:"):
            services = [comp]
        severity = max(SIGNAL_SEVERITY.get(s.kind, 3) for s in sigs)
        if services and services[0] in ("svc:atm", "svc:pos"):
            severity = max(severity, 4)
        playbooks: list[str] = []
        for s in sigs:
            for pb in (fb.get("suggested_playbooks_by_signal") or {}).get(s.kind, []):
                if pb not in playbooks:
                    playbooks.append(pb)
        sit = SituationState(id=new_id("sit"), template="fallback", title=fb["title"].format(n=len(sigs), component=name),
                             severity=severity, origin=comp, first_at=min(s.started_at for s in sigs), last_at=now,
                             services=services, components=[comp, *services], suggested_playbooks=playbooks,
                             last_member_at=now)
        for s in sigs:
            s.situation_id = sit.id
            sit.signal_ids.append(s.id)
        self._attach_existing_episodes(sit)
        self.situations[sit.id] = sit
        self._touch(sit)
        self._flush_situations()
        if self.on_situation_opened:
            self.on_situation_opened(self.situation_dict(sit))

    def _attach_existing_episodes(self, sit: SituationState) -> None:
        cutoff = sit.first_at - timedelta(seconds=60)
        for ep in self.episodes.values():
            if ep.quarantined or (ep.subsystem, ep.event_number) in BENIGN or ep.last_at < cutoff:
                continue
            if self._episode_relevant(sit, ep) and ep.id not in sit.episode_ids:
                sit.episode_ids.append(ep.id)
                if ep.component_id and ep.component_id not in sit.components:
                    sit.components.append(ep.component_id)

    def _lifecycle(self, now: datetime) -> None:
        for sit in self.situations.values():
            if sit.status == "resolved":
                continue
            sigs = [self.signals[i] for i in sit.signal_ids if i in self.signals]
            if sigs and all(not s.active for s in sigs):
                sit.all_clear_since = sit.all_clear_since or now
                if (now - sit.all_clear_since).total_seconds() >= RESOLVE_AFTER_S:
                    sit.status = "resolved"
                    self._touch(sit, member=False)
                    continue
            else:
                sit.all_clear_since = None
            if sit.status in ("open", "updating") and sit.last_member_at and \
                    (now - sit.last_member_at).total_seconds() >= STABLE_AFTER_S:
                sit.status = "stable"
                self._touch(sit, member=False)

    def _touch(self, sit: SituationState, member: bool = True) -> None:
        if member and sit.status in ("stable",) and sit.id in self.situations:
            sit.status = "updating"
        elif member and sit.status == "open" and sit.id in self.situations and sit.episode_ids and \
                self.now and (self.now - sit.first_at).total_seconds() > 3:
            sit.status = "updating"
        sit.last_at = self.now or sit.last_at
        self.dirty_situations.add(sit.id)

    def set_incident(self, situation_id: str, incident_id: str) -> None:
        sit = self.situations.get(situation_id)
        if sit:
            sit.incident_id = incident_id
            self.dirty_situations.add(sit.id)
            self._flush_situations()

    # ------------------------------------------------------------ views and publishing

    def situation_dict(self, sit: SituationState) -> dict:
        eps = [self.episodes[i] for i in sit.episode_ids if i in self.episodes]
        return {
            "id": sit.id, "title": sit.title, "severity": sit.severity, "status": sit.status,
            "origin": {"component_id": sit.origin}, "components": list(sit.components), "services": list(sit.services),
            "counts": {"raw_events": sum(e.count for e in eps), "episodes": len(eps), "signals": len(sit.signal_ids)},
            "template": sit.template, "first_at": iso_sim(sit.first_at), "last_at": iso_sim(sit.last_at),
            "incident_id": sit.incident_id, "suggested_playbooks": list(sit.suggested_playbooks),
        }

    def _flush_situations(self) -> None:
        for sid in list(self.dirty_situations):
            sit = self.situations.get(sid)
            if not sit:
                continue
            d = self.situation_dict(sit)
            self.publish("situations", "situation.upsert", d)
            if self.store is not None:
                self.store.put("situations", sit.id, d, status=sit.status, template=sit.template,
                               first_at=d["first_at"], incident_id=sit.incident_id)
        self.dirty_situations.clear()

    def flush(self) -> None:
        """Publish dirty episodes and the event rate (called about once per real second)."""
        if self.now is None:
            return
        for eid in list(self.dirty_episodes):
            ep = self.episodes.get(eid)
            if ep:
                self.publish("events", "episode.upsert", ep.to_dict(self.now))
        self.dirty_episodes.clear()
        self.publish("events", "events.rate", self.rate())

    def rate(self) -> dict:
        if self.now is None:
            return {"per_min": 0.0, "raw_total": self.raw_total, "episodes_open": 0, "situations_open": 0}
        cutoff = self.now - timedelta(seconds=60)
        per_min = float(sum(n for t, n in self.minute_counts if t > cutoff))
        return {"per_min": per_min, "raw_total": self.raw_total,
                "episodes_open": sum(1 for e in self.episodes.values() if e.status == "open"),
                "situations_open": sum(1 for s in self.situations.values() if s.status != "resolved")}

    def recent_events(self, limit: int = 200, quarantined: bool | None = None) -> list[dict]:
        evs = list(self.events)
        if quarantined is not None:
            evs = [e for e in evs if e["quarantined"] == quarantined]
        return evs[-limit:][::-1]

    def list_episodes(self, status: str | None = None) -> list[dict]:
        now = self.now or datetime.min
        eps = [e for e in self.episodes.values() if status is None or e.status == status]
        eps.sort(key=lambda e: (-e.severity, -e.count))
        return [e.to_dict(now) for e in eps[:300]]

    def list_situations(self) -> list[dict]:
        return [self.situation_dict(s) for s in sorted(self.situations.values(), key=lambda s: s.first_at, reverse=True)]

    def situation_detail(self, situation_id: str) -> dict | None:
        sit = self.situations.get(situation_id)
        if not sit:
            return None
        d = self.situation_dict(sit)
        now = self.now or datetime.min
        d["episodes"] = [self.episodes[i].to_dict(now) for i in sit.episode_ids if i in self.episodes]
        d["signals"] = [self.signals[i].to_dict() for i in sit.signal_ids if i in self.signals]
        return d

    def active_signals(self) -> list[dict]:
        return [s.to_dict() for s in self.signals.values() if s.active]

    def episodes_matching(self, subsystem: str | None = None, minutes: float = 10) -> list[dict]:
        if self.now is None:
            return []
        cutoff = self.now - timedelta(minutes=minutes)
        out = [e for e in self.episodes.values() if e.last_at >= cutoff and not e.quarantined
               and (subsystem is None or e.subsystem == subsystem.upper())]
        out.sort(key=lambda e: (-e.severity, -e.count))
        return [e.to_dict(self.now) for e in out]


def _json(obj) -> str:
    from ..db.store import dumps
    return dumps(obj)

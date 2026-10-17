"""Realtime contract (MVP spec §15). One WebSocket at /api/ws; envelopes are discriminated by `type`."""
from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import Field

from .cards import Card
from .common import Model
from .shapes import (
    Approval, AuditRow, Claim, Episode, EventsRate, HealthSnapshot, Incident, Interrupt, LedgerEntry,
    Run, SimState, Situation, TimelineItem, TraceStep,
)


# ---------------------------------------------------------------- client -> server

class WsSubscribe(Model):
    op: Literal["subscribe"]
    topics: list[str] = Field(description="telemetry, events, situations, health, incidents, approvals, ledger, claims, audit, sim, terminal, thread:{id}")


class WsUnsubscribe(Model):
    op: Literal["unsubscribe"]
    topics: list[str]


class WsResume(Model):
    op: Literal["resume"]
    since_seq: int


class WsPing(Model):
    op: Literal["ping"]


WsClientMessage = Annotated[Union[WsSubscribe, WsUnsubscribe, WsResume, WsPing], Field(discriminator="op")]


# ---------------------------------------------------------------- payloads

class TelemetryTick(Model):
    sim_ts: str
    values: dict[str, float] = Field(description="Metric keys per §15, e.g. cpu.0.busy, svc.atm.p95_ms, sc.ATM-AUTH.queued")


class TimelineAppend(Model):
    incident_id: str
    item: TimelineItem


class CardRemove(Model):
    card_id: str
    thread_id: str


class InterruptResolved(Model):
    interrupt_id: str
    thread_id: str
    response: dict[str, Any]


class RunCompleted(Model):
    run: Run
    summary: str = ""


class RunFailed(Model):
    run: Run
    error: str


class PromotionCandidate(Model):
    entry: LedgerEntry
    text: str = Field(description="e.g. 'tmfcom.status_audittrail · Operator: 20 clean runs, eligible for L2'")


class TerminalGhost(Model):
    exec_id: str
    actor: str
    approved_by: list[str]
    auto: bool
    label: str = Field(description="e.g. 'Baton · auto · L2 (granted by Dave)' or 'Baton · approved by Priya'")
    text: str
    ms_per_char: int


class TerminalOutput(Model):
    exec_id: str | None
    lines: list[str]


class TerminalText(Model):
    text: str


# ---------------------------------------------------------------- envelopes

class _Env(Model):
    topic: str
    seq: int
    ts: str
    sim_ts: str | None


class TelemetryTickEvent(_Env):
    type: Literal["telemetry.tick"]
    payload: TelemetryTick


class EpisodeUpsertEvent(_Env):
    type: Literal["episode.upsert"]
    payload: Episode


class EventsRateEvent(_Env):
    type: Literal["events.rate"]
    payload: EventsRate


class SituationUpsertEvent(_Env):
    type: Literal["situation.upsert"]
    payload: Situation


class HealthSnapshotEvent(_Env):
    type: Literal["health.snapshot"]
    payload: HealthSnapshot


class IncidentUpsertEvent(_Env):
    type: Literal["incident.upsert"]
    payload: Incident


class TimelineAppendEvent(_Env):
    type: Literal["timeline.append"]
    payload: TimelineAppend


class RunStartedEvent(_Env):
    type: Literal["run.started"]
    payload: Run


class NodeStartedEvent(_Env):
    type: Literal["node.started"]
    payload: TraceStep


class NodeEndedEvent(_Env):
    type: Literal["node.ended"]
    payload: TraceStep


class CardUpsertEvent(_Env):
    type: Literal["card.upsert"]
    payload: Card


class CardRemoveEvent(_Env):
    type: Literal["card.remove"]
    payload: CardRemove


class InterruptRaisedEvent(_Env):
    type: Literal["interrupt.raised"]
    payload: Interrupt


class InterruptResolvedEvent(_Env):
    type: Literal["interrupt.resolved"]
    payload: InterruptResolved


class RunCompletedEvent(_Env):
    type: Literal["run.completed"]
    payload: RunCompleted


class RunFailedEvent(_Env):
    type: Literal["run.failed"]
    payload: RunFailed


class ApprovalUpsertEvent(_Env):
    type: Literal["approval.upsert"]
    payload: Approval


class LedgerUpsertEvent(_Env):
    type: Literal["ledger.upsert"]
    payload: LedgerEntry


class LedgerPromotionCandidateEvent(_Env):
    type: Literal["ledger.promotion_candidate"]
    payload: PromotionCandidate


class ClaimUpsertEvent(_Env):
    type: Literal["claim.upsert"]
    payload: Claim


class AuditAppendEvent(_Env):
    type: Literal["audit.append"]
    payload: AuditRow


class SimStateEvent(_Env):
    type: Literal["sim.state"]
    payload: SimState


class TerminalGhostEvent(_Env):
    type: Literal["terminal.ghost"]
    payload: TerminalGhost


class TerminalOutputEvent(_Env):
    type: Literal["terminal.output"]
    payload: TerminalOutput


class TerminalPromptEvent(_Env):
    type: Literal["terminal.prompt"]
    payload: TerminalText


class TerminalSystemEvent(_Env):
    type: Literal["terminal.system"]
    payload: TerminalText


WsEvent = Annotated[
    Union[
        TelemetryTickEvent, EpisodeUpsertEvent, EventsRateEvent, SituationUpsertEvent, HealthSnapshotEvent,
        IncidentUpsertEvent, TimelineAppendEvent, RunStartedEvent, NodeStartedEvent, NodeEndedEvent,
        CardUpsertEvent, CardRemoveEvent, InterruptRaisedEvent, InterruptResolvedEvent, RunCompletedEvent,
        RunFailedEvent, ApprovalUpsertEvent, LedgerUpsertEvent, LedgerPromotionCandidateEvent,
        ClaimUpsertEvent, AuditAppendEvent, SimStateEvent, TerminalGhostEvent, TerminalOutputEvent,
        TerminalPromptEvent, TerminalSystemEvent,
    ],
    Field(discriminator="type"),
]

# event type -> (topic or topic prefix, payload model)
WS_EVENT_TYPES: dict[str, tuple[str, type]] = {
    "telemetry.tick": ("telemetry", TelemetryTick),
    "episode.upsert": ("events", Episode),
    "events.rate": ("events", EventsRate),
    "situation.upsert": ("situations", Situation),
    "health.snapshot": ("health", HealthSnapshot),
    "incident.upsert": ("incidents", Incident),
    "timeline.append": ("incidents", TimelineAppend),
    "run.started": ("thread:", Run),
    "node.started": ("thread:", TraceStep),
    "node.ended": ("thread:", TraceStep),
    "card.upsert": ("thread:", None),
    "card.remove": ("thread:", CardRemove),
    "interrupt.raised": ("thread:", Interrupt),
    "interrupt.resolved": ("thread:", InterruptResolved),
    "run.completed": ("thread:", RunCompleted),
    "run.failed": ("thread:", RunFailed),
    "approval.upsert": ("approvals", Approval),
    "ledger.upsert": ("ledger", LedgerEntry),
    "ledger.promotion_candidate": ("ledger", PromotionCandidate),
    "claim.upsert": ("claims", Claim),
    "audit.append": ("audit", AuditRow),
    "sim.state": ("sim", SimState),
    "terminal.ghost": ("terminal", TerminalGhost),
    "terminal.output": ("terminal", TerminalOutput),
    "terminal.prompt": ("terminal", TerminalText),
    "terminal.system": ("terminal", TerminalText),
}

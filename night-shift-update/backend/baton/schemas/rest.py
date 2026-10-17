"""REST request and response bodies (MVP spec §14)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from .cards import Card
from .common import Level, Model, Tier
from .shapes import (
    Approval, AuditRow, CatalogEntryPublic, Claim, Episode, EvalRun, Execution, FaultKind, HealthSnapshot,
    Incident, Interrupt, LedgerEntry, NormalizedEvent, Playbook, PolicyDecision, Postmortem, SimState,
    Situation, Thread, ThreadMode, TimelineItem, TraceStep, User,
)

# ---------------------------------------------------------------- requests


class ReadOnlyRequest(Model):
    enabled: bool
    actor: str


class SimStartRequest(Model):
    scenario: Literal["S0", "S1", "S2", "S3", "S4"]
    profile: Literal["demo", "test"] = "demo"
    seed: int | None = None
    speed: int | None = None
    actor: str


class SimInjectRequest(Model):
    fault: FaultKind
    params: dict[str, Any] = Field(default={}, description="cpu_halt: {cpu}; maxservers_change: {server_class, value}; audit_pressure: {factor}")
    actor: str


class SimClockRequest(Model):
    speed: int | None = Field(None, description="1, 2, 4, 8 or 16")
    paused: bool | None = None
    step: int | None = Field(None, description="Advance N sim-seconds while paused")
    actor: str


class SimReplayRequest(Model):
    mode: Literal["off", "record", "replay"]
    actor: str


class ActorOnly(Model):
    actor: str


class ThreadCreateRequest(Model):
    mode: ThreadMode = "auto"
    incident_id: str | None = None
    actor: str


class MessageRequest(Model):
    text: str
    actor: str


class ResumeRequest(Model):
    interrupt_id: str
    response: dict[str, Any]
    actor: str


class ApprovalDecideRequest(Model):
    decision: Literal["approve", "edit_approve", "reject"]
    params: dict[str, Any] | None = Field(None, description="Edited parameters (edit_approve); for multi-step approvals {step_id: params}")
    option_ids: list[str] | None = Field(None, description="Decision cards: the options ticked by the operator")
    reason_code: Literal["wrong_command", "wrong_target", "unsafe_now", "not_needed", "other"] | None = None
    comment: str | None = None
    actor: str


class CommandPreviewRequest(Model):
    catalog_id: str
    params: dict[str, Any] = {}
    actor: str


class TerminalInputRequest(Model):
    line: str
    actor: str


class ClaimReviewRequest(Model):
    decision: Literal["confirm", "edit_confirm", "reject"]
    edits: dict[str, Any] | None = Field(None, description="Fields to change: statement, structured, scope, confidence")
    reason: str | None = None
    actor: str


class LedgerGrantRequest(Model):
    level: Level
    reason: str = Field(min_length=1)
    actor: str


class LedgerRevokeRequest(Model):
    reason: str = Field(min_length=1)
    actor: str


class WhatIfRequest(Model):
    actions: list[dict[str, Any]]


class EvalRunRequest(Model):
    suites: list[Literal["commands", "safety", "diagnosis", "retrieval"]] | None = None
    actor: str | None = None


# ---------------------------------------------------------------- responses


class UsersResponse(Model):
    users: list[User]


class SimStateResponse(SimState):
    pass


class InvestigateResponse(Model):
    thread_id: str
    incident_id: str


class ThreadDetail(Model):
    thread: Thread
    cards: list[Card]
    trace: list[TraceStep]
    pending_interrupts: list[Interrupt]


class RunAccepted(Model):
    run_id: str
    thread_id: str


class ApprovalsResponse(Model):
    approvals: list[Approval]


class ApprovalDecideResponse(Model):
    approval: Approval
    resumed: bool = Field(description="True when the decision completed the approval and resumed the thread")


class CatalogResponse(Model):
    entries: list[CatalogEntryPublic]


class CommandPreviewResponse(Model):
    valid: bool
    errors: list[str]
    rendered: str | None
    tier: Tier | None
    policy: PolicyDecision | None
    undo: str | None = None


class TerminalInputResponse(Model):
    accepted: bool
    message: str
    catalog_id: str | None = None
    exec_id: str | None = None
    card_id: str | None = None
    thread_id: str | None = None


class UndoResponse(Model):
    accepted: bool
    message: str
    approval_id: str | None = None
    exec_id: str | None = None


class EventsResponse(Model):
    events: list[NormalizedEvent]


class EpisodesResponse(Model):
    episodes: list[Episode]


class SituationsResponse(Model):
    situations: list[Situation]


class IncidentsResponse(Model):
    incidents: list[Incident]


class IncidentDetail(Incident):
    hypotheses: list[dict[str, Any]] = []
    options: list[dict[str, Any]] = []
    approvals: list[Approval] = []
    executions: list[Execution] = []
    verification: dict[str, Any] | None = None
    postmortem_ready: bool = False
    cards: list[Card] = []


class TimelineResponse(Model):
    items: list[TimelineItem]


class ClaimsResponse(Model):
    claims: list[Claim]


class PlaybooksResponse(Model):
    playbooks: list[Playbook]


class LedgerResponse(Model):
    entries: list[LedgerEntry]


class PoliciesResponse(Model):
    version: int
    document: str
    rules: list[dict[str, Any]]
    protected_processes: list[str]
    limits: dict[str, Any]
    read_only: bool


class AuditResponse(Model):
    rows: list[AuditRow]


class EvalLatestResponse(Model):
    run: EvalRun | None


class EvalRunAccepted(Model):
    run_id: str


class HealthResponse(HealthSnapshot):
    pass


class PostmortemResponse(Postmortem):
    pass

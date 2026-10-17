"""Domain shapes shared by REST and WebSocket (MVP spec §15.1, plus shapes §14 implies)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from .common import ActorRef, Citation, Level, Model, OpenModel, Role, Tier

# ---------------------------------------------------------------- system / sim

ComponentState = Literal["ok", "degraded", "critical", "down", "unknown"]
FaultKind = Literal["cpu_halt", "audit_pressure", "maxservers_change"]


class User(Model):
    id: str
    name: str
    role: Role
    initials: str
    title: str


class ActiveFault(Model):
    fault: FaultKind
    params: dict[str, Any]
    injected_sim_ts: str


class SimState(Model):
    scenario: str | None
    scenario_name: str | None
    profile: Literal["demo", "test"]
    seed: int
    sim_ts: str | None
    speed: int
    paused: bool
    running: bool
    active_faults: list[ActiveFault] = []
    calendar: str | None = None


class SystemStatus(Model):
    system: str = "\\TORBANK"
    sim: SimState
    llm_provider: Literal["nemotron", "none"]
    model_fast: str | None
    model_strong: str | None
    replay_mode: Literal["off", "record", "replay"]
    embeddings: Literal["local", "none"]
    read_only: bool
    contract_version: str


# ---------------------------------------------------------------- telemetry / health

class MetricSeries(Model):
    key: str
    points: list[tuple[str, float]] = Field(description="[sim_ts, value] pairs, oldest first")


class MetricsResponse(Model):
    window_s: int
    series: list[MetricSeries]


class HealthReason(Model):
    rule_id: str
    text: str
    value: float | None = None
    threshold: float | None = None


class HealthComponent(Model):
    id: str = Field(description="Component ID, e.g. 'cpu:3', 'sc:ATM-AUTH', 'tmf:mat', 'svc:atm'")
    type: Literal["cpu", "server_class", "tmf", "service", "process", "volume"]
    name: str
    state: ComponentState
    reasons: list[HealthReason] = []
    at_risk: bool = False
    metrics: dict[str, float] = {}


class N1Status(Model):
    safe: bool
    worst_lost_cpu: int | None
    worst_survivor_cpu: int | None
    worst_survivor_busy: float | None
    threshold: float = 90.0
    text: str = Field(description="e.g. 'N-1 at risk: losing CPU 3 puts CPU 5 at ~96%'")
    per_cpu: dict[str, dict[str, float]] = Field(
        default={}, description="lost CPU -> {survivor_cpu, survivor_busy}"
    )


class HealthSnapshot(Model):
    sim_ts: str
    overall: ComponentState
    components: list[HealthComponent]
    n1: N1Status


class TopologyNode(Model):
    id: str
    type: Literal["system", "cpu", "process", "server_class", "tmf", "volume", "service"]
    name: str
    attributes: dict[str, Any] = {}
    tags: list[str] = []


class TopologyEdge(Model):
    source: str
    target: str
    kind: Literal["runs_on", "backup_on", "serves", "depends_on", "writes_audit_to", "uses_volume"]


class Topology(Model):
    nodes: list[TopologyNode]
    edges: list[TopologyEdge]


# ---------------------------------------------------------------- events / situations

class ManualRef(Model):
    cause: str | None = None
    effect: str | None = None
    recovery: str | None = None
    url: str | None = None


class NormalizedEvent(Model):
    id: str
    sim_ts: str
    system: str
    process: str
    subsystem: str
    event_number: int
    critical: bool
    severity: int
    text: str
    raw: str
    fields: dict[str, Any] = {}
    component_id: str | None
    fingerprint: str
    episode_id: str | None
    quarantined: bool = False
    simulated: bool = Field(description="True when the message is invented (not from the HPE manual)")


class Episode(Model):
    id: str
    fingerprint: str
    subsystem: str
    event_number: int
    example_text: str
    component_id: str | None
    count: int
    rate_per_min: float
    first_at: str
    last_at: str
    severity: int
    critical: bool
    quarantined: bool
    status: Literal["open", "closed"] = "open"
    manual: ManualRef | None = None


class SituationCounts(Model):
    raw_events: int
    episodes: int
    signals: int


class SituationOrigin(Model):
    component_id: str


class Signal(Model):
    id: str
    kind: str
    component_id: str
    started_at: str
    ended_at: str | None = None
    value: float | None = None
    detail: str = ""


class Situation(Model):
    id: str
    title: str
    severity: int
    status: Literal["open", "updating", "stable", "resolved"]
    origin: SituationOrigin
    components: list[str]
    services: list[str]
    counts: SituationCounts
    template: str
    first_at: str
    last_at: str
    incident_id: str | None
    suggested_playbooks: list[str] = []


class SituationDetail(Situation):
    episodes: list[Episode] = []
    signals: list[Signal] = []


class EventsRate(Model):
    per_min: float
    raw_total: int
    episodes_open: int = 0
    situations_open: int = 0


# ---------------------------------------------------------------- incidents

class IncidentImpact(Model):
    service: str | None
    p95_ms_peak: float | None
    timeout_pct_peak: float | None


class HypothesisTop(Model):
    id: str
    label: str
    p: float


class UndoEntry(Model):
    id: str
    execution_id: str
    catalog_id: str
    params: dict[str, Any]
    rendered: str
    label: str
    status: Literal["pending", "applied", "discarded"]
    created_sim_ts: str


IncidentStatus = Literal["open", "mitigating", "verifying", "resolved"]


class Incident(Model):
    id: str
    display_id: str
    title: str
    severity: int
    status: IncidentStatus
    situation_id: str | None
    thread_id: str | None
    opened_at: str
    resolved_at: str | None
    impact: IncidentImpact
    hypotheses_top: list[HypothesisTop] = []
    undo_stack: list[UndoEntry] = []


TimelineKind = Literal[
    "situation", "episode", "check", "hypothesis_change", "approval_requested", "approval_decided",
    "action_executed", "undo", "verification", "note", "status_change", "claim_drafted",
]


class TimelineRef(Model):
    type: Literal["card", "execution", "approval", "situation", "episode", "claim", "incident", "run"]
    id: str


class TimelineItem(Model):
    id: str
    incident_id: str
    sim_ts: str
    wall_ts: str
    kind: TimelineKind
    actor: ActorRef
    title: str
    detail: str = ""
    ref: TimelineRef | None = None


class Postmortem(Model):
    incident_id: str
    summary: str
    impact: str
    timeline_md: str
    cause: str
    actions: list[str]
    follow_ups: list[str]
    source: str = Field(description="Model ID, 'replay' or 'fallback'")
    created_sim_ts: str


# ---------------------------------------------------------------- agent

class TraceDetail(Model):
    tools: list[str] = []
    evidence_ids: list[str] = []
    model: str | None = Field(None, description="'<model id>' | 'replay' | 'fallback' | null when no model is involved")
    prompt_hash: str | None = None
    inputs: str | None = None
    output: str | None = None


class TraceStep(Model):
    run_id: str
    step_id: str
    node: str
    label: str
    status: Literal["running", "done", "waiting", "failed", "fallback"]
    started_at: str
    duration_ms: int | None
    summary: str
    detail: TraceDetail


ThreadMode = Literal["auto", "ask", "command", "investigate"]


class Thread(Model):
    id: str
    mode: ThreadMode
    actor: str
    incident_id: str | None
    title: str
    status: Literal["idle", "running", "waiting", "done", "failed"]
    created_at: str


class Interrupt(Model):
    id: str
    thread_id: str
    run_id: str
    kind: Literal["approval", "question"]
    approval_id: str | None = None
    prompt: str
    raised_at: str
    resolved: bool = False


class Run(Model):
    id: str
    thread_id: str
    graph: str
    status: Literal["running", "waiting", "completed", "failed"]
    started_at: str
    ended_at: str | None = None


# ---------------------------------------------------------------- governance

class PolicyDecision(Model):
    effect: Literal["allow_auto", "require_approval", "deny"]
    required_approvers: int
    required_roles: list[Role] = []
    at_least_one_of: list[Role] = []
    rule_ids: list[str]
    explanation: str
    escalation: str | None = None


class ApprovalRequired(Model):
    count: int
    roles: list[Role]
    at_least_one_of: list[Role] = []


class ApprovalDecisionRecord(Model):
    actor: str
    actor_name: str
    decision: Literal["approve", "edit_approve", "reject"]
    at: str
    reason_code: Literal["wrong_command", "wrong_target", "unsafe_now", "not_needed", "other"] | None = None
    comment: str | None = None
    params: dict[str, Any] | None = None


ApprovalStatus = Literal["pending", "partially_approved", "approved", "rejected", "expired"]


class Approval(Model):
    id: str
    thread_id: str
    incident_id: str | None
    card_id: str | None
    step_ids: list[str]
    option_ids: list[str] = []
    rendered: list[str]
    tier: Tier
    required: ApprovalRequired
    decisions: list[ApprovalDecisionRecord] = []
    status: ApprovalStatus
    expires_sim_ts: str
    policy: PolicyDecision
    progress_text: str = Field(description="e.g. '1 of 2: needs Senior or Expert'")


class Execution(Model):
    id: str
    step_id: str | None
    catalog_id: str
    params: dict[str, Any] = {}
    rendered: str
    approved_by: list[str]
    auto: bool
    actor: str
    status: Literal["running", "done", "failed"]
    started_at: str
    ended_at: str | None
    sim_ts: str
    raw_text: str | None
    facts: dict[str, Any] | None
    parse_confidence: float | None
    undo_entry_id: str | None
    summary: str | None = None


class LedgerCounters(Model):
    approved_unchanged: int = 0
    edited: int = 0
    rejected: int = 0
    executed: int = 0
    verified_ok: int = 0
    verified_fail: int = 0
    undone: int = 0


class LedgerHistoryItem(Model):
    kind: Literal["seed", "promotion_candidate", "grant", "demotion", "revocation"]
    actor: str
    reason: str
    at: str
    from_level: Level | None = None
    to_level: Level | None = None


class LedgerEntry(Model):
    key: str = Field(description="'{catalog_id}|{param_class}|{role}'")
    catalog_id: str
    param_class: str
    role: str
    level: Level
    counters: LedgerCounters
    distinct_approvers: int
    granted_by: str | None
    granted_at: str | None
    grant_reason: str | None
    eligible_for: Level | None = Field(None, description="Set when a promotion candidate is open")
    recent_rejections: int = 0
    tier: Tier | None = None
    history: list[LedgerHistoryItem] = []


class AuditRow(Model):
    seq: int
    wall_ts: str
    sim_ts: str | None
    actor_type: Literal["user", "agent", "system"]
    actor_id: str
    action: str
    target: str | None
    payload: dict[str, Any]
    policy_rule_ids: list[str] = []
    model_id: str | None = None
    prompt_hash: str | None = None
    incident_id: str | None = None
    prev_hash: str
    hash: str


class AuditVerify(Model):
    valid: bool
    entries: int
    head_hash: str
    first_bad_seq: int | None = None


# ---------------------------------------------------------------- catalog

class CatalogParam(Model):
    name: str
    type: Literal["int", "str", "enum", "process", "cpu", "volume", "server_class"]
    required: bool = True
    min: int | None = None
    max: int | None = None
    max_from: str | None = None
    source: str | None = None
    choices: list[str] | None = None
    description: str | None = None


class CatalogEntryPublic(Model):
    id: str
    title: str
    description: str
    interpreter: str | None
    template: str | None
    syntax_status: Literal["simulated", "verified"]
    tier: Tier
    tier_rules: str
    params: list[CatalogParam]
    reversible: bool
    undo_template: str | None
    side_effects: str
    risks: str
    internal: bool = Field(description="Baton-internal check (baton.*): never typed into the terminal")
    blocked: bool = False
    escalation: str | None = None
    aliases: list[str] = []
    utility: str


# ---------------------------------------------------------------- knowledge

class ClaimStructured(Model):
    subject: list[str]
    condition: str
    assertion: str
    recommendation: dict[str, Any] | str | None = None
    rationale: str


class ClaimReview(Model):
    user: str
    user_name: str | None = None
    decision: Literal["confirm", "edit_confirm", "reject"]
    at: str
    reason: str | None = None
    edits: dict[str, Any] | None = None


class ClaimProvenance(Model):
    source_type: Literal["seed", "incident", "interview", "manual"]
    source_id: str | None


class Claim(Model):
    id: str
    statement: str
    structured: ClaimStructured
    scope: dict[str, Any]
    confidence: Literal["certain", "likely", "tentative"] | str
    status: Literal["pending_review", "verified", "rejected", "retired"]
    author: str
    author_name: str | None = None
    assigned_reviewer: str | None = None
    reviews: list[ClaimReview] = []
    version: int = 1
    provenance: ClaimProvenance
    synthetic: bool = True


class PlaybookStep(OpenModel):
    kind: Literal["check", "action", "note", "escalate"]


class Playbook(Model):
    id: str
    title: str
    version: int
    author: str
    author_name: str | None = None
    verified_by: list[dict[str, Any]]
    synthetic: bool = True
    trigger: dict[str, Any] = {}
    steps: list[dict[str, Any]]


class KbStageScores(Model):
    bm25_rank: int | None
    vector_rank: int | None
    fused: float
    authority: float
    final: float
    pinned: bool = False


class KbResult(Model):
    id: str
    doc_type: Literal[
        "operator_message", "command_ref", "concept", "claim", "playbook", "playbook_step",
        "incident", "glossary", "site_fact", "catalog",
    ]
    title: str
    snippet: str
    provenance: Literal["hpe_manual", "expert_verified", "site", "incident", "synthetic"]
    source_url: str | None = None
    synthetic: bool = False
    scores: KbStageScores | None = None


class KbSearchResponse(Model):
    query: str
    expanded_terms: list[str] = []
    entities: list[str] = []
    results: list[KbResult]


class KbItem(Model):
    id: str
    doc_type: str
    title: str
    text: str
    header: str
    metadata: dict[str, Any] = {}
    provenance: str
    source_url: str | None = None
    synthetic: bool = False
    record: dict[str, Any] = Field(default={}, description="Full source record (message, claim, playbook, ...)")
    citations: list[Citation] = []


# ---------------------------------------------------------------- eval

class EvalTile(Model):
    id: str
    label: str
    value: float
    display: str
    target: str
    passed: bool


class EvalCaseResult(Model):
    suite: Literal["commands", "safety", "diagnosis", "retrieval"]
    case_id: str
    passed: bool
    input: str
    expected: Any
    actual: Any
    detail: str = ""


class EvalRun(Model):
    id: str
    started_at: str
    ended_at: str | None
    status: Literal["running", "done", "failed"]
    config: dict[str, Any] = {}
    tiles: list[EvalTile] = []
    results: list[EvalCaseResult] = []

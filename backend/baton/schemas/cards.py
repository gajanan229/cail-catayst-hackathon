"""Card library contract (MVP spec §13.4, §15.2). Cards are discriminated by `type`."""
from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import Field

from .common import Citation, Level, Model, Tier
from .shapes import PolicyDecision, SituationCounts

CardStatus = Literal[
    "info", "proposed", "awaiting_approval", "partially_approved", "auto_running", "running",
    "done", "failed", "blocked", "rejected", "expired", "resolved",
]
CardAction = Literal[
    "approve", "edit", "reject", "undo", "investigate", "open_incident", "approve_selected",
    "approve_all_readonly", "propose_undo", "copy_summary", "confirm", "edit_confirm", "open_source",
    "open_incident_room",
]


class CardBase(Model):
    id: str
    thread_id: str | None
    incident_id: str | None = None
    status: CardStatus
    title: str
    citations: list[Citation] = []
    actions: list[CardAction] = []
    source: str | None = Field(None, description="Model ID, 'replay', 'fallback', or null when no model was used")
    created_at: str
    sim_ts: str | None
    seq: int = Field(0, description="Order within the thread; cards render sorted by seq")


# ---------------------------------------------------------------- bodies

class TextBody(Model):
    markdown: str
    sentences: list[dict[str, Any]] = Field(
        default=[], description="[{text, citation_ids[]}] when the answer is sentence-cited"
    )
    unknown: bool = False
    ask_whom: str | None = None
    link: dict[str, str] | None = Field(None, description="e.g. {label: 'Open Incident Room', incident_id: 'inc_...'}")
    alternatives: list[dict[str, Any]] = Field(default=[], description="Nearest safe catalog alternatives for 'not in catalog'")


class SituationBody(Model):
    situation_id: str
    severity: int
    components: list[str]
    services: list[str]
    counts: SituationCounts
    collapse_text: str = Field(description="e.g. '612 events → 1 situation'")
    template: str
    first_at: str
    age_s: int
    suggested_playbooks: list[str] = []


class Autonomy(Model):
    level: Level
    key: str
    progress: str
    granted_by: str | None


class UndoSpec(Model):
    catalog_id: str
    params: dict[str, Any]
    rendered: str


class FactsRow(Model):
    label: str
    value: str


class CommandExecution(Model):
    exec_id: str
    status: Literal["running", "done", "failed"]
    duration_ms: int | None
    raw_output: str | None
    facts: dict[str, Any] | None
    facts_table: list[FactsRow] = []
    summary: str | None = None
    summary_source: str | None = None
    approved_by: list[str] = []
    auto: bool = False


class CommandBody(Model):
    step_id: str
    catalog_id: str
    interpreter: str | None
    rendered: str
    params: dict[str, Any] = {}
    purpose: str
    why_now: dict[str, Any] | None = None
    expected: str | None = None
    risks: str
    tier: Tier
    internal: bool = Field(False, description="Baton check: not typed into the terminal")
    autonomy: Autonomy | None
    policy: PolicyDecision
    undo: UndoSpec | None
    approval_id: str | None
    approval_progress: str | None = None
    approvers: list[str] = []
    execution: CommandExecution | None
    validation_errors: list[str] = []


class PlanStepItem(Model):
    step_id: str
    catalog_id: str
    rendered: str
    tier: Tier
    parallel_group: int = 0
    status: CardStatus
    card_id: str | None = None


class PlanBody(Model):
    request: str
    rationale: str
    steps: list[PlanStepItem]


class EvidenceRef(Model):
    evidence_id: str
    label: str


class Hypothesis(Model):
    id: str
    label: str
    p: float
    delta: float
    for_: list[EvidenceRef] = Field(default=[], alias="for")
    against: list[EvidenceRef] = []
    would_change_mind: str | None = None


class StopRule(Model):
    met: bool
    top: float
    margin: float
    reason: str | None = None


class HypothesesBody(Model):
    round: int
    stop_rule: StopRule
    hypotheses: list[Hypothesis]
    narrative: str | None = None
    narrative_source: str | None = None


class EvidenceBody(Model):
    items: list[dict[str, Any]] = Field(
        description="[{id, type: metric|event|episode|output_fact|knowledge|site_fact, label, source, preview}]"
    )


class PersonRef(Model):
    id: str
    name: str
    at: str | None = None


class ExpertBody(Model):
    kind: Literal["playbook", "claim"]
    id: str
    title: str
    version: int
    author: PersonRef
    verified_by: list[PersonRef]
    last_validated: str | None
    tip: str
    steps: list[str] = []
    claim_ids: list[str] = []
    claims: list[dict[str, Any]] = Field(default=[], description="[{id, statement, author, verified_by}]")
    synthetic: bool = True


class OptionStep(Model):
    catalog_id: str
    params: dict[str, Any]
    rendered: str
    tier: Tier
    undo: str | None = None


class Recommender(Model):
    kind: Literal["playbook", "claim", "library"]
    id: str
    author: str | None = None
    verified_by: list[str] = []


class DecisionOption(Model):
    id: str
    label: str
    steps: list[OptionStep] = []
    tier: Tier | None = None
    required_approvers: int | None = None
    recommender: Recommender | None = None
    expected_effect: str | None = None
    risks: str | None = None
    prediction: dict[str, Any] | None = None
    recommended: bool = False
    blocked: bool = False
    block_reason: str | None = None
    escalation: str | None = None
    includes: list[str] = []
    approval_id: str | None = None
    status: Literal["available", "selected", "awaiting_approval", "partially_approved", "approved", "executed", "rejected", "blocked"] = "available"


class DecisionBody(Model):
    approval_id: str | None = Field(None, description="Set once options have been selected and approvals created")
    options: list[DecisionOption]
    selected: list[str] = []


class VerificationCriterion(Model):
    text: str
    met: bool
    value: str | None = None


class VerificationBody(Model):
    failure_mode: str
    criteria: list[VerificationCriterion]
    window_s: int
    window_start_sim_ts: str
    window_end_sim_ts: str | None
    result: Literal["pending", "recovered", "not_recovered", "regression"]
    summary: str
    propose_undo: list[str] = Field(default=[], description="Undo entry IDs to offer on regression")


class EscalationBody(Model):
    reason: str
    contact: str
    summary: str
    evidence_pack: list[str] = []


class PostmortemBody(Model):
    incident_id: str
    summary: str
    impact: str
    timeline_md: str
    cause: str
    actions: list[str]
    follow_ups: list[str]


class ClaimReviewBody(Model):
    claim_id: str
    statement: str
    structured: dict[str, Any]
    scope: dict[str, Any]
    author: str
    assigned_reviewer: str | None
    source: dict[str, Any]


# ---------------------------------------------------------------- cards

class TextCard(CardBase):
    type: Literal["text"] = "text"
    body: TextBody


class SituationCard(CardBase):
    type: Literal["situation"] = "situation"
    body: SituationBody


class CommandCard(CardBase):
    type: Literal["command"] = "command"
    body: CommandBody


class PlanCard(CardBase):
    type: Literal["plan"] = "plan"
    body: PlanBody


class HypothesesCard(CardBase):
    type: Literal["hypotheses"] = "hypotheses"
    body: HypothesesBody


class EvidenceCard(CardBase):
    type: Literal["evidence"] = "evidence"
    body: EvidenceBody


class ExpertCard(CardBase):
    type: Literal["expert"] = "expert"
    body: ExpertBody


class DecisionCard(CardBase):
    type: Literal["decision"] = "decision"
    body: DecisionBody


class VerificationCard(CardBase):
    type: Literal["verification"] = "verification"
    body: VerificationBody


class EscalationCard(CardBase):
    type: Literal["escalation"] = "escalation"
    body: EscalationBody


class PostmortemCard(CardBase):
    type: Literal["postmortem"] = "postmortem"
    body: PostmortemBody


class ClaimReviewCard(CardBase):
    type: Literal["claim_review"] = "claim_review"
    body: ClaimReviewBody


Card = Annotated[
    Union[
        TextCard, SituationCard, CommandCard, PlanCard, HypothesesCard, EvidenceCard, ExpertCard,
        DecisionCard, VerificationCard, EscalationCard, PostmortemCard, ClaimReviewCard,
    ],
    Field(discriminator="type"),
]

CARD_TYPES = {
    "text": TextCard, "situation": SituationCard, "command": CommandCard, "plan": PlanCard,
    "hypotheses": HypothesesCard, "evidence": EvidenceCard, "expert": ExpertCard, "decision": DecisionCard,
    "verification": VerificationCard, "escalation": EscalationCard, "postmortem": PostmortemCard,
    "claim_review": ClaimReviewCard,
}

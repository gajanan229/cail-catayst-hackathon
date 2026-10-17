"""REST routes (MVP spec §14). Handlers are thin: every call goes through the Runtime facade."""
from __future__ import annotations

from urllib.parse import unquote

from fastapi import APIRouter, Query

from ..schemas import rest as R
from ..schemas.common import ErrorResponse, OkResponse
from ..schemas.shapes import (
    Execution, Incident, KbItem, KbSearchResponse, LedgerEntry, Playbook, SituationDetail,
    SystemStatus, Topology, AuditVerify, Claim, MetricsResponse, Thread,
)
from .deps import rt

ERRORS = {400: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse},
          409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}}

router = APIRouter(prefix="/api", responses=ERRORS)


# ---------------------------------------------------------------- system

@router.get("/system/status", response_model=SystemStatus, tags=["system"])
def system_status():
    return rt().system_status()


@router.post("/system/read-only", response_model=SystemStatus, tags=["system"])
def system_read_only(body: R.ReadOnlyRequest):
    return rt().set_read_only(body.enabled, body.actor)


@router.get("/users", response_model=R.UsersResponse, tags=["system"])
def users():
    return {"users": rt().users.list()}


# ---------------------------------------------------------------- simulator (Director)

@router.get("/sim/state", response_model=R.SimStateResponse, tags=["sim"])
def sim_state():
    return rt().sim_state()


@router.post("/sim/start", response_model=R.SimStateResponse, tags=["sim"])
async def sim_start(body: R.SimStartRequest):
    return await rt().sim_start(body.scenario, body.profile, body.seed, body.speed, body.actor)


@router.post("/sim/inject", response_model=R.SimStateResponse, tags=["sim"])
def sim_inject(body: R.SimInjectRequest):
    return rt().sim_inject(body.fault, body.params, body.actor)


@router.post("/sim/clock", response_model=R.SimStateResponse, tags=["sim"])
def sim_clock(body: R.SimClockRequest):
    return rt().sim_clock(body.speed, body.paused, body.step, body.actor)


@router.post("/sim/reset", response_model=R.SimStateResponse, tags=["sim"])
async def sim_reset(body: R.ActorOnly):
    return await rt().reset(body.actor)


@router.post("/sim/replay", response_model=SystemStatus, tags=["sim"])
def sim_replay(body: R.SimReplayRequest):
    return rt().set_replay(body.mode, body.actor)


# ---------------------------------------------------------------- telemetry and health

@router.get("/topology", response_model=Topology, tags=["telemetry"])
def topology():
    return rt().topology()


@router.get("/health", response_model=R.HealthResponse, tags=["telemetry"])
def health():
    return rt().health_snapshot()


@router.get("/metrics", response_model=MetricsResponse, tags=["telemetry"])
def metrics(keys: str = Query("cpu.*.busy,svc.atm.p95_ms"), window_s: int = Query(900, ge=5, le=1800)):
    return rt().metrics_query([k.strip() for k in keys.split(",") if k.strip()], window_s)


@router.get("/events", response_model=R.EventsResponse, tags=["telemetry"])
def events(limit: int = Query(200, ge=1, le=2000), quarantined: bool | None = None):
    return {"events": rt().pipeline.recent_events(limit, quarantined)}


@router.get("/episodes", response_model=R.EpisodesResponse, tags=["telemetry"])
def episodes(status: str | None = Query(None, pattern="^(open|closed)$")):
    return {"episodes": rt().pipeline.list_episodes(status)}


@router.get("/situations", response_model=R.SituationsResponse, tags=["telemetry"])
def situations():
    return {"situations": rt().pipeline.list_situations()}


@router.get("/situations/{situation_id}", response_model=SituationDetail, tags=["telemetry"])
def situation(situation_id: str):
    return rt().pipeline.situation_detail(situation_id)


@router.post("/situations/{situation_id}/investigate", response_model=R.InvestigateResponse, tags=["agent"])
async def investigate(situation_id: str, body: R.ActorOnly):
    return await rt().investigate_situation(situation_id, body.actor)


# ---------------------------------------------------------------- threads and agent

@router.post("/threads", response_model=Thread, tags=["agent"])
def create_thread(body: R.ThreadCreateRequest):
    return rt().agents.create_thread(body.mode, body.incident_id, body.actor)


@router.get("/threads/{thread_id}", response_model=R.ThreadDetail, tags=["agent"])
def thread_detail(thread_id: str):
    return rt().agents.thread_detail(thread_id)


@router.post("/threads/{thread_id}/messages", response_model=R.RunAccepted, tags=["agent"])
async def post_message(thread_id: str, body: R.MessageRequest):
    return await rt().agents.post_message(thread_id, body.text, body.actor)


@router.post("/threads/{thread_id}/resume", response_model=R.RunAccepted, tags=["agent"])
async def resume(thread_id: str, body: R.ResumeRequest):
    return await rt().agents.resume_question(thread_id, body.interrupt_id, body.response, body.actor)


# ---------------------------------------------------------------- approvals and commands

@router.get("/approvals", response_model=R.ApprovalsResponse, tags=["governance"])
def approvals(status: str | None = Query(None, pattern="^(pending|partially_approved|approved|rejected|expired)$")):
    return {"approvals": rt().approvals.list(status)}


@router.post("/approvals/{approval_id}/decide", response_model=R.ApprovalDecideResponse, tags=["governance"])
async def decide(approval_id: str, body: R.ApprovalDecideRequest):
    return await rt().decide_approval(approval_id, body)


@router.get("/catalog", response_model=R.CatalogResponse, tags=["commands"])
def catalog():
    return {"entries": rt().catalog.public_entries()}


@router.post("/commands/preview", response_model=R.CommandPreviewResponse, tags=["commands"])
def preview(body: R.CommandPreviewRequest):
    return rt().preview_command(body.catalog_id, body.params, body.actor)


@router.post("/terminal/input", response_model=R.TerminalInputResponse, tags=["commands"])
async def terminal_input(body: R.TerminalInputRequest):
    return await rt().terminal_input(body.line, body.actor)


@router.get("/executions/{exec_id}", response_model=Execution, tags=["commands"])
def execution(exec_id: str):
    return rt().executor.get(exec_id)


@router.post("/executions/{exec_id}/undo", response_model=R.UndoResponse, tags=["commands"])
async def undo(exec_id: str, body: R.ActorOnly):
    return await rt().undo_execution(exec_id, body.actor)


# ---------------------------------------------------------------- incidents

@router.get("/incidents", response_model=R.IncidentsResponse, tags=["incidents"])
def incidents():
    return {"incidents": rt().incidents.list()}


@router.get("/incidents/{incident_id}", response_model=R.IncidentDetail, tags=["incidents"])
def incident(incident_id: str):
    return rt().incident_detail(incident_id)


@router.get("/incidents/{incident_id}/timeline", response_model=R.TimelineResponse, tags=["incidents"])
def timeline(incident_id: str):
    return {"items": rt().incidents.timeline(incident_id)}


@router.get("/incidents/{incident_id}/postmortem", response_model=R.PostmortemResponse, tags=["incidents"])
def postmortem(incident_id: str):
    return rt().incidents.postmortem(incident_id)


@router.post("/incidents/{incident_id}/close", response_model=Incident, tags=["incidents"])
async def close_incident(incident_id: str, body: R.ActorOnly):
    return await rt().close_incident(incident_id, body.actor)


@router.post("/incidents/{incident_id}/whatif", tags=["incidents"])
def whatif(incident_id: str, body: R.WhatIfRequest):
    return rt().whatif(incident_id, body.actions)


# ---------------------------------------------------------------- knowledge

@router.get("/kb/search", response_model=KbSearchResponse, tags=["knowledge"])
def kb_search(q: str, k: int = Query(8, ge=1, le=30), types: str | None = None, debug: bool = False):
    type_list = [t.strip() for t in types.split(",")] if types else None
    return rt().kb.search(q, k=k, types=type_list, debug=debug)


@router.get("/kb/items/{item_id}", response_model=KbItem, tags=["knowledge"])
def kb_item(item_id: str):
    return rt().kb.item(unquote(item_id))


@router.get("/claims", response_model=R.ClaimsResponse, tags=["knowledge"])
def claims(status: str | None = Query(None, pattern="^(pending_review|verified|rejected|retired)$")):
    return {"claims": rt().claims.list(status)}


@router.post("/claims/{claim_id}/review", response_model=Claim, tags=["knowledge"])
def review_claim(claim_id: str, body: R.ClaimReviewRequest):
    return rt().review_claim(claim_id, body)


@router.get("/playbooks", response_model=R.PlaybooksResponse, tags=["knowledge"])
def playbooks():
    return {"playbooks": rt().kb.playbooks()}


@router.get("/playbooks/{playbook_id}", response_model=Playbook, tags=["knowledge"])
def playbook(playbook_id: str):
    return rt().kb.playbook(playbook_id)


# ---------------------------------------------------------------- governance

@router.get("/ledger", response_model=R.LedgerResponse, tags=["governance"])
def ledger():
    return {"entries": rt().ledger.list()}


@router.post("/ledger/{key:path}/grant", response_model=LedgerEntry, tags=["governance"])
def ledger_grant(key: str, body: R.LedgerGrantRequest):
    return rt().ledger_grant(unquote(key), body.level, body.reason, body.actor)


@router.post("/ledger/{key:path}/revoke", response_model=LedgerEntry, tags=["governance"])
def ledger_revoke(key: str, body: R.LedgerRevokeRequest):
    return rt().ledger_revoke(unquote(key), body.reason, body.actor)


@router.get("/policies", response_model=R.PoliciesResponse, tags=["governance"])
def policies():
    return rt().policy_describe()


@router.get("/audit", response_model=R.AuditResponse, tags=["governance"])
def audit(limit: int = Query(500, ge=1, le=5000), incident_id: str | None = None):
    return {"rows": rt().audit.list(limit, incident_id)}


@router.get("/audit/verify", response_model=AuditVerify, tags=["governance"])
def audit_verify():
    return rt().audit.verify()


# ---------------------------------------------------------------- eval

@router.get("/eval/latest", response_model=R.EvalLatestResponse, tags=["eval"])
def eval_latest():
    return {"run": rt().eval_latest()}


@router.post("/eval/run", response_model=R.EvalRunAccepted, tags=["eval"])
async def eval_run(body: R.EvalRunRequest | None = None):
    return await rt().eval_run(body.suites if body else None)


@router.get("/ping", response_model=OkResponse, tags=["system"], include_in_schema=False)
def ping():
    return {"ok": True}

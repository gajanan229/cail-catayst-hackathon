"""Shared contract primitives (MVP spec §14 conventions)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CONTRACT_VERSION = "1.0.0"

Tier = Literal["T0", "T1", "T2", "T3"]
Level = Literal["L0", "L1", "L2", "L3", "system"]
Role = Literal["operator", "senior", "expert", "steward"]
Severity = int  # 1 (info) .. 5 (critical)
ErrorCode = Literal[
    "VALIDATION_FAILED",
    "POLICY_DENIED",
    "APPROVAL_EXPIRED",
    "NOT_FOUND",
    "CONFLICT",
    "SIM_NOT_RUNNING",
]


class Model(BaseModel):
    """Base for every contract model: unknown keys are rejected on input, kept stable on output."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)


class OpenModel(BaseModel):
    """For loosely typed blobs (facts, params, detail) where extra keys are expected."""

    model_config = ConfigDict(extra="allow")


class ErrorDetail(Model):
    code: ErrorCode
    message: str
    detail: dict[str, Any] | None = None
    correlation_id: str


class ErrorResponse(Model):
    error: ErrorDetail


class ActorRef(Model):
    type: Literal["user", "agent", "system"]
    id: str
    name: str


class Citation(Model):
    id: str = Field(description="Knowledge item ID, e.g. 'opmsg:PATHWAY:1034', 'cmdref:tmfcom.status_audittrail', 'claim:C-001'")
    label: str
    kind: Literal[
        "hpe_manual", "command_ref", "concept", "claim", "playbook", "incident", "site", "glossary", "evidence"
    ]
    url: str | None = None


class ActorBody(Model):
    actor: str = Field(description="User ID of the acting persona, e.g. 'u_priya'")


class OkResponse(Model):
    ok: bool = True

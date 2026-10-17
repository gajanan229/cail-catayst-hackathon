"""Policy engine (MVP spec §9.2): ordered rules, deny overrides allow. Every decision returns
effect, required_approvers, rule_ids and a plain-language explanation."""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path

import yaml

LEVELS = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "system": 9}
ROLE_TITLE = {"operator": "Operator", "senior": "Senior", "expert": "Expert", "steward": "Steward"}


@dataclass
class PolicyContext:
    catalog_id: str
    tier: str
    target: str | None
    actor_role: str
    ledger_level: str
    ledger_progress: str = ""
    ledger_granted_by: str | None = None
    internal: bool = False
    read_only: bool = False
    state_changes_recent: int = 0
    escalation: str | None = None


@dataclass
class Decision:
    effect: str
    required_approvers: int
    required_roles: list[str]
    at_least_one_of: list[str]
    rule_ids: list[str]
    explanation: str
    escalation: str | None = None
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"effect": self.effect, "required_approvers": self.required_approvers,
                "required_roles": self.required_roles, "at_least_one_of": self.at_least_one_of,
                "rule_ids": self.rule_ids, "explanation": self.explanation, "escalation": self.escalation}


class Policy:
    def __init__(self, path: Path):
        self.path = path
        self.document = path.read_text(encoding="utf-8")
        doc = yaml.safe_load(self.document)
        self.version = int(doc.get("version", 1))
        self.rules = doc["rules"]
        self.protected = list(doc.get("protected_processes") or [])
        self.limits = dict(doc.get("limits") or {})
        self.approval_expiry_sim_s = int(doc.get("approval_expiry_sim_s", 600))
        self.token_ttl_s = int(doc.get("token_ttl_s", 120))

    def is_protected(self, target: str | None) -> bool:
        return bool(target) and any(fnmatch.fnmatchcase(str(target), p) for p in self.protected)

    def _matches(self, when: dict, ctx: PolicyContext) -> bool:
        for key, want in when.items():
            if key == "read_only" and ctx.read_only != want:
                return False
            if key == "tier" and ctx.tier != want:
                return False
            if key == "tier_in" and ctx.tier not in want:
                return False
            if key == "target_in" and not self.is_protected(ctx.target):
                return False
            if key == "internal" and ctx.internal != want:
                return False
            if key == "ledger_level_gte" and LEVELS.get(ctx.ledger_level, 0) < LEVELS[want]:
                return False
            if key == "state_changes_exceeded":
                limit = int(self.limits.get("state_changes_per_incident_per_10_sim_min", 3))
                if (ctx.state_changes_recent >= limit) != want:
                    return False
        return True

    def evaluate(self, ctx: PolicyContext) -> Decision:
        matched = [r for r in self.rules if self._matches(r.get("when", {}), ctx)]
        denies = [r for r in matched if r["effect"] == "deny"]
        if denies:
            r = denies[0]
            expl = r.get("explanation", "Denied")
            esc = ctx.escalation if r["id"] == "t3-block" else None
            if r["id"] == "protected":
                expl = f"Protected system process: {ctx.target} is on the protected list"
            return Decision("deny", 0, [], [], [x["id"] for x in denies], expl, esc)
        if not matched:
            return Decision("require_approval", 1, ["operator", "senior", "expert"], [], ["default"], "Needs one approval")
        r = matched[0]
        ap = r.get("approvers") or {}
        expl = r.get("explanation", "")
        if r["id"] == "t0-ledger":
            who = f", granted by {ctx.ledger_granted_by}" if ctx.ledger_granted_by else ""
            expl = f"Read-only; {ROLE_TITLE.get(ctx.actor_role, ctx.actor_role)} earned auto-run ({ctx.ledger_level}{who})"
        elif r["id"] == "t0-default":
            prog = f" ({ctx.ledger_progress})" if ctx.ledger_progress else ""
            expl = f"Read-only, but {ROLE_TITLE.get(ctx.actor_role, ctx.actor_role)} has not yet earned auto-run{prog}"
        if r["effect"] == "allow_auto":
            return Decision("allow_auto", 0, [], [], [r["id"]], expl)
        return Decision("require_approval", int(ap.get("count", 1)), list(ap.get("roles") or ["operator", "senior", "expert"]),
                        list(ap.get("at_least_one_of") or []), [r["id"]], expl)

    def describe(self, read_only: bool) -> dict:
        return {"version": self.version, "document": self.document, "rules": self.rules,
                "protected_processes": self.protected, "limits": self.limits, "read_only": read_only}

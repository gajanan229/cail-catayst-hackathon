"""Approvals (MVP spec §9.4): single and two-person, edit-and-approve, reject with reason, expiry in sim time.

Only a fully approved or rejected approval resumes a LangGraph thread; a partial approval just updates its card.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Callable

from ..api.errors import ApiError
from ..core.ids import new_id
from ..core.timeutil import iso_sim, parse_sim
from ..db.store import Store

ROLE_TITLE = {"operator": "Operator", "senior": "Senior", "expert": "Expert", "steward": "Steward"}


def progress_text(required: dict, decisions: list[dict], status: str) -> str:
    approvals = [d for d in decisions if d["decision"] in ("approve", "edit_approve")]
    need = required["count"]
    if status == "approved":
        return "Approved by " + " and ".join(d["actor_name"] for d in approvals) if approvals else "Approved"
    if status == "rejected":
        rej = next((d for d in decisions if d["decision"] == "reject"), None)
        return f"Rejected by {rej['actor_name']}" if rej else "Rejected"
    if status == "expired":
        return "Expired"
    if need <= 1:
        return "Needs 1 approval"
    alo = required.get("at_least_one_of") or []
    who = " or ".join(ROLE_TITLE[r] for r in alo) if alo else "another approver"
    return f"{len(approvals)} of {need}: needs {who}" if approvals else f"Needs {need} approvals (at least one {who})"


class Approvals:
    def __init__(self, store: Store, publish: Callable, users, sim_now: Callable, expiry_s: int = 600,
                 expiry_override: Callable[[], int | None] | None = None):
        self.store = store
        self.publish = publish
        self.users = users
        self.sim_now = sim_now
        self.default_expiry_s = expiry_s
        self.expiry_override = expiry_override or (lambda: None)

    @property
    def expiry_s(self) -> int:
        """Policy expiry, unless the scenario profile sets its own (a night played at 16x needs hours of sim time)."""
        return int(self.expiry_override() or self.default_expiry_s)

    # ------------------------------------------------------------ records

    def create(self, *, kind: str, thread_id: str, incident_id: str | None, card_id: str | None, steps: list[dict],
               tier: str, policy: dict, option_ids: list[str] | None = None, requested_by: str = "baton",
               graph_key: str | None = None, extra: dict | None = None) -> dict:
        now = self.sim_now()
        required = {"count": max(1, int(policy.get("required_approvers") or 1)),
                    "roles": list(policy.get("required_roles") or ["operator", "senior", "expert"]),
                    "at_least_one_of": list(policy.get("at_least_one_of") or [])}
        a = {
            "id": new_id("apr"), "kind": kind, "thread_id": thread_id, "incident_id": incident_id, "card_id": card_id,
            "step_ids": [s["step_id"] for s in steps], "option_ids": list(option_ids or []),
            "rendered": [s.get("rendered") or "" for s in steps], "tier": tier, "required": required,
            "decisions": [], "status": "pending",
            "expires_sim_ts": iso_sim(now + timedelta(seconds=self.expiry_s)) if now else None,
            "policy": policy, "progress_text": "", "steps": steps, "requested_by": requested_by,
            "graph_key": graph_key, "extra": extra or {},
        }
        a["progress_text"] = progress_text(required, [], "pending")
        self.save(a)
        return a

    def public(self, a: dict) -> dict:
        keys = ["id", "thread_id", "incident_id", "card_id", "step_ids", "option_ids", "rendered", "tier", "required",
                "decisions", "status", "expires_sim_ts", "policy", "progress_text"]
        out = {k: a.get(k) for k in keys}
        out["expires_sim_ts"] = out["expires_sim_ts"] or "2026-01-01T00:00:00Z"
        return out

    def save(self, a: dict) -> dict:
        self.store.put("approvals", a["id"], a, thread_id=a["thread_id"], incident_id=a["incident_id"], status=a["status"])
        self.publish("approvals", "approval.upsert", self.public(a))
        return a

    def get(self, approval_id: str) -> dict:
        a = self.store.get("approvals", approval_id)
        if not a:
            raise ApiError("NOT_FOUND", f"Approval {approval_id} not found")
        return a

    def list(self, status: str | None) -> list[dict]:
        rows = self.store.all("approvals", "status = ?", (status,)) if status else self.store.all("approvals")
        return [self.public(a) for a in rows]

    def open_for_thread(self, thread_id: str) -> list[dict]:
        return [a for a in self.store.all("approvals", "thread_id = ?", (thread_id,))
                if a["status"] in ("pending", "partially_approved")]

    # ------------------------------------------------------------ decisions

    def check_expired(self, a: dict) -> bool:
        now = self.sim_now()
        if a["status"] in ("pending", "partially_approved") and now and a.get("expires_sim_ts") \
                and now > parse_sim(a["expires_sim_ts"]):
            a["status"] = "expired"
            a["progress_text"] = progress_text(a["required"], a["decisions"], "expired")
            self.save(a)
            return True
        return False

    def decide(self, approval_id: str, actor: str, decision: str, *, params: dict | None = None,
               reason_code: str | None = None, comment: str | None = None, read_only: bool = False) -> tuple[dict, bool]:
        """Record one decision. Returns (approval, complete) where complete means approved or rejected."""
        a = self.get(approval_id)
        user = self.users.get(actor)
        if self.check_expired(a):
            raise ApiError("APPROVAL_EXPIRED", "This approval expired; Baton will re-plan if it is still needed",
                           {"approval_id": approval_id})
        if a["status"] not in ("pending", "partially_approved"):
            raise ApiError("CONFLICT", f"Approval is already {a['status']}", {"status": a["status"]})
        if decision == "reject":
            if not reason_code:
                raise ApiError("VALIDATION_FAILED", "Reject needs a reason code",
                               {"reason_codes": ["wrong_command", "wrong_target", "unsafe_now", "not_needed", "other"]})
        else:
            if read_only and a["tier"] in ("T1", "T2", "T3"):
                raise ApiError("POLICY_DENIED", "Read-only mode is on", {"rule_ids": ["read-only"]})
            if user["role"] not in a["required"]["roles"]:
                raise ApiError("POLICY_DENIED", f"{user['name']} ({user['role']}) cannot approve this",
                               {"required_roles": a["required"]["roles"]})
            if any(d["actor"] == actor and d["decision"] != "reject" for d in a["decisions"]):
                raise ApiError("POLICY_DENIED", "The second approver must be a different person", {"rule_ids": ["t2-two-person"]})
            if a["required"]["count"] >= 2:
                prior = [d for d in a["decisions"] if d["decision"] != "reject"]
                alo = a["required"].get("at_least_one_of") or []
                if alo and len(prior) + 1 >= a["required"]["count"]:
                    roles = {self.users.get(d["actor"])["role"] for d in prior} | {user["role"]}
                    if not roles & set(alo):
                        raise ApiError("POLICY_DENIED", "Needs at least one " + " or ".join(ROLE_TITLE[r] for r in alo),
                                       {"rule_ids": ["t2-two-person"]})
        rec = {"actor": actor, "actor_name": user["name"], "decision": decision, "at": iso_sim(self.sim_now()),
               "reason_code": reason_code, "comment": comment, "params": params}
        a["decisions"].append(rec)
        if decision == "reject":
            a["status"] = "rejected"
        else:
            approvals = [d for d in a["decisions"] if d["decision"] != "reject"]
            a["status"] = "approved" if len(approvals) >= a["required"]["count"] else "partially_approved"
        a["progress_text"] = progress_text(a["required"], a["decisions"], a["status"])
        self.save(a)
        return a, a["status"] in ("approved", "rejected")

    def approvers(self, a: dict) -> list[str]:
        return [d["actor"] for d in a["decisions"] if d["decision"] in ("approve", "edit_approve")]

    def approver_names(self, a: dict) -> list[str]:
        return [d["actor_name"] for d in a["decisions"] if d["decision"] in ("approve", "edit_approve")]

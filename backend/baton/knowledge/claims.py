"""Claims, review queue and expert card (MVP spec §10.4, §10.5)."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import yaml

from ..api.errors import ApiError
from ..core.ids import new_id
from ..core.timeutil import wall_now
from ..db.store import Store


class Claims:
    def __init__(self, store: Store, content_dir: Path, kb, publish: Callable, users):
        self.store = store
        self.content_dir = content_dir
        self.kb = kb
        self.publish = publish
        self.users = users

    def seed(self) -> None:
        """(Re)load seed claims; runtime claims are removed by the store reset."""
        d = self.content_dir / "claims"
        for p in sorted(d.glob("*.yaml")) if d.exists() else []:
            c = yaml.safe_load(p.read_text(encoding="utf-8"))
            c.setdefault("version", 1)
            c.setdefault("reviews", [])
            c.setdefault("provenance", {"source_type": "seed", "source_id": None})
            if c["provenance"].get("source_type") not in ("seed", "incident", "interview", "manual"):
                c["provenance"]["source_type"] = "seed"
            self.store.put("claims", c["id"], c, status=c["status"], runtime=0)
            self.kb.upsert_claim(c, runtime=False)

    def public(self, c: dict) -> dict:
        reviews = []
        for r in c.get("reviews", []):
            reviews.append({"user": r["user"], "user_name": self.users.name(r["user"]), "decision": r["decision"],
                            "at": str(r.get("at")), "reason": r.get("reason"), "edits": r.get("edits")})
        s = c.get("structured", {})
        return {
            "id": c["id"], "statement": c["statement"],
            "structured": {"subject": s.get("subject", []), "condition": s.get("condition", ""),
                           "assertion": s.get("assertion", ""), "recommendation": s.get("recommendation"),
                           "rationale": s.get("rationale", "")},
            "scope": c.get("scope", {}), "confidence": c.get("confidence", "likely"), "status": c["status"],
            "author": c["author"], "author_name": self.users.name(c["author"]),
            "assigned_reviewer": c.get("assigned_reviewer"), "reviews": reviews, "version": int(c.get("version", 1)),
            "provenance": {"source_type": c["provenance"].get("source_type", "seed"),
                           "source_id": c["provenance"].get("source_id")},
            "synthetic": bool(c.get("synthetic", True)),
        }

    def get(self, claim_id: str) -> dict:
        c = self.store.get("claims", claim_id)
        if not c:
            raise ApiError("NOT_FOUND", f"Claim {claim_id} not found")
        return c

    def list(self, status: str | None = None) -> list[dict]:
        rows = self.store.all("claims", "status = ?", (status,)) if status else self.store.all("claims")
        rows.sort(key=lambda c: c["id"])
        return [self.public(c) for c in rows]

    def create_draft(self, statement: str, structured: dict, scope: dict, confidence: str, author: str,
                     reviewer: str, incident_id: str) -> dict:
        n = int(self.store.kv_get("claim_counter", 20)) + 1
        self.store.kv_set("claim_counter", n)
        c = {"id": f"C-{n:03d}", "statement": statement, "structured": structured, "scope": scope,
             "confidence": confidence, "status": "pending_review", "author": author, "assigned_reviewer": reviewer,
             "reviews": [], "version": 1, "provenance": {"source_type": "incident", "source_id": incident_id},
             "synthetic": True}
        self.store.put("claims", c["id"], c, status=c["status"], runtime=1)
        self.publish("claims", "claim.upsert", self.public(c))
        return c

    def review(self, claim_id: str, decision: str, edits: dict | None, reason: str | None, actor: str) -> dict:
        user = self.users.get(actor)
        c = self.get(claim_id)
        if c["status"] != "pending_review":
            raise ApiError("CONFLICT", f"Claim {claim_id} is {c['status']}")
        if user["role"] not in ("expert", "senior", "steward"):
            raise ApiError("POLICY_DENIED", "Only experts review claims")
        if actor == c["author"]:
            raise ApiError("POLICY_DENIED", "Authors cannot review their own claims")
        if decision == "reject" and not reason:
            raise ApiError("VALIDATION_FAILED", "Reject needs a reason")
        if decision == "edit_confirm":
            if not edits:
                raise ApiError("VALIDATION_FAILED", "Edit & confirm needs edits")
            for k, v in edits.items():
                if k == "structured" and isinstance(v, dict):
                    c["structured"] = {**c.get("structured", {}), **v}
                elif k in ("statement", "scope", "confidence"):
                    c[k] = v
            c["version"] = int(c.get("version", 1)) + 1
        c["reviews"].append({"user": actor, "decision": decision, "at": wall_now(), "reason": reason, "edits": edits})
        c["status"] = "rejected" if decision == "reject" else "verified"
        runtime = 1 if c.get("provenance", {}).get("source_type") == "incident" else 0
        self.store.put("claims", c["id"], c, status=c["status"], runtime=runtime)
        self.store.put("claim_reviews", new_id("rvw"), {"claim_id": claim_id, "decision": decision, "actor": actor},
                       claim_id=claim_id)
        if c["status"] == "verified":
            self.kb.upsert_claim(c, runtime=bool(runtime))        # hot indexing: searchable immediately
        else:
            self.kb.remove(f"claim:{c['id']}")
        pub = self.public(c)
        self.publish("claims", "claim.upsert", pub)
        return pub

    def pending_count(self) -> int:
        return len(self.store.all("claims", "status = ?", ("pending_review",)))


def build_expert_card(kb, claims: Claims, users, situation: dict, mode: dict, components: list[str]) -> dict | None:
    """Top verified playbook for the situation plus up to two verified claims that recommend its mitigations."""
    q = " ".join([situation.get("template", "").replace("_", " "), mode.get("name", ""), situation.get("title", ""),
                  *[c.split(":", 1)[-1] for c in components]])
    res = kb.search(q, k=12, types=["playbook", "claim"])
    playbook = None
    for r in res["results"]:
        rec = kb.records[r["id"]]["record"]
        if r["doc_type"] == "playbook" and rec.get("trigger", {}).get("causal_template") == situation.get("template"):
            playbook = rec
            break
    if playbook is None:
        playbook = next((kb.records[r["id"]]["record"] for r in res["results"] if r["doc_type"] == "playbook"), None)
    mitigation_ids = {s["catalog_id"] for m in mode.get("mitigations", []) for s in m.get("steps", [])}
    chosen: list[dict] = []
    for c in claims.store.all("claims", "status = ?", ("verified",)):
        rec = (c.get("structured") or {}).get("recommendation") or {}
        if isinstance(rec, dict) and rec.get("catalog_id") in mitigation_ids:
            subj = set(c.get("structured", {}).get("subject", []))
            score = 2 if subj & {x.split(":", 1)[-1] for x in components} else 1
            chosen.append((score, c))
    chosen.sort(key=lambda x: (-x[0], x[1]["id"]))
    picked = [c for _, c in chosen[:2]]
    if playbook is None and not picked:
        return None
    if playbook is None:
        c = picked[0]
        return {"kind": "claim", "id": c["id"], "title": c["statement"][:80], "version": int(c.get("version", 1)),
                "author": {"id": c["author"], "name": users.name(c["author"])},
                "verified_by": [{"id": r["user"], "name": users.name(r["user"]), "at": str(r.get("at"))} for r in c.get("reviews", [])],
                "last_validated": str(c["reviews"][-1]["at"]) if c.get("reviews") else None, "tip": c["statement"],
                "steps": [], "claim_ids": [x["id"] for x in picked],
                "claims": [_claim_summary(x, users) for x in picked], "synthetic": True}
    tip = picked[0]["statement"] if picked else next((s.get("text") for s in playbook["steps"] if s.get("kind") == "note"), playbook["title"])
    if picked and picked[0]["id"] == "C-001":
        tip = "The noon statement batch $STMT1 on CPU 5 is safe to suspend during peaks; resume after 13:00."
    steps = []
    for s in playbook["steps"]:
        if s.get("kind") == "check":
            steps.append(s.get("read") or f"Check {s.get('catalog_id')}")
        elif s.get("kind") == "action":
            steps.append(s.get("when") and f"{s['catalog_id']}: {s['when']}" or f"Action: {s.get('catalog_id')}")
        elif s.get("kind") == "escalate":
            steps.append(s.get("text"))
    vb = [{"id": v["user"], "name": users.name(v["user"]), "at": str(v.get("at"))} for v in playbook.get("verified_by", [])]
    return {"kind": "playbook", "id": playbook["id"], "title": playbook["title"], "version": int(playbook.get("version", 1)),
            "author": {"id": playbook["author"], "name": users.name(playbook["author"])}, "verified_by": vb,
            "last_validated": vb[-1]["at"] if vb else None, "tip": tip, "steps": [s for s in steps if s][:6],
            "claim_ids": [c["id"] for c in picked], "claims": [_claim_summary(c, users) for c in picked],
            "synthetic": bool(playbook.get("synthetic", True))}


def _claim_summary(c: dict, users) -> dict:
    return {"id": c["id"], "statement": c["statement"], "author": users.name(c["author"]),
            "verified_by": [users.name(r["user"]) for r in c.get("reviews", []) if r.get("decision") != "reject"]}

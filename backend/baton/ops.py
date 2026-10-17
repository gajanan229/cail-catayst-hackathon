"""Runtime operations behind the REST routes that span several services (approvals, terminal, undo,
incidents, knowledge review, ledger, eval). Mixed into Runtime."""
from __future__ import annotations

import asyncio
import logging

from .api.errors import ApiError
from .commands.executor import public_execution
from .core.ids import new_id

log = logging.getLogger("baton.ops")


class Ops:
    # ------------------------------------------------------------ commands

    def preview_command(self, catalog_id: str, params: dict, actor: str) -> dict:
        self.users.get(actor)
        return self.commands.preview(catalog_id, params, actor)

    def execution_public(self, exec_id: str) -> dict:
        return public_execution(self.executor.get(exec_id))

    def _terminal_thread(self, actor: str) -> dict:
        tid = self.store.kv_get(f"terminal_thread:{actor}")
        t = self.agents.get_thread(tid) if tid else None
        if not t:
            t = self.agents.create_thread("command", None, actor, title=f"Terminal · {self.users.name(actor)}")
            self.store.kv_set(f"terminal_thread:{actor}", t["id"])
        return t

    async def terminal_input(self, line: str, actor: str) -> dict:
        """Manual typing (MVP spec §8.3): a catalog line goes through validator and policy as the persona's own action."""
        self.users.get(actor)
        self._require_sim()
        self.audit.append("user", actor, "terminal.input", line[:200], {"line": line[:500]})
        m = self.commands.match_line(line)
        if not m:
            self.hub.publish("terminal", "terminal.system", {"text": "*** Not available in the Baton simulator (catalog commands only)"})
            self.hub.publish("terminal", "terminal.prompt", {"text": self.executor.prompt()})
            return {"accepted": False, "message": "Not available in the Baton simulator (catalog commands only)"}
        catalog_id, params = m
        inc = next((i for i in self.incidents.list() if i["status"] != "resolved"), None)
        p = self.commands.prepare(catalog_id, params, actor, inc["id"] if inc else None)
        if not p.validation.valid:
            msg = "; ".join(p.validation.errors)
            self.hub.publish("terminal", "terminal.system", {"text": f"*** {msg}"})
            return {"accepted": False, "message": msg, "catalog_id": catalog_id}
        if p.denied:
            self.hub.publish("terminal", "terminal.system", {"text": f"*** Denied: {p.policy['explanation']}"})
            self.audit.append("user", actor, "policy.deny", p.validation.rendered, {"catalog_id": catalog_id},
                              policy_rule_ids=p.policy["rule_ids"])
            return {"accepted": False, "message": p.policy["explanation"], "catalog_id": catalog_id}
        t = self._terminal_thread(actor)
        if p.validation.tier == "T0":
            approval = self.approvals.create(kind="terminal", thread_id=t["id"], incident_id=inc["id"] if inc else None,
                                             card_id=None, steps=[p.step_dict()], tier="T0",
                                             policy={**p.policy, "effect": "require_approval", "required_approvers": 1},
                                             requested_by=actor)
            approval, _ = self.approvals.decide(approval["id"], actor, "approve")
            ex = await self.commands.run(p, actor=actor, approved_by=[actor], auto=False, approval_id=approval["id"],
                                         thread_id=t["id"], incident_id=inc["id"] if inc else None)
            return {"accepted": True, "message": "Ran (T0, typed by you)", "catalog_id": catalog_id, "exec_id": ex["id"],
                    "thread_id": t["id"]}
        from .agents.cards import command_body
        body = command_body(p, purpose="Typed in the terminal")
        cd = self.agents.cards.upsert({"type": "command", "thread_id": t["id"], "incident_id": inc["id"] if inc else None,
                                       "status": "awaiting_approval", "title": f"Confirm: {p.validation.rendered}",
                                       "body": body, "actions": ["approve", "reject"]})
        policy = {**p.policy, "required_approvers": 1, "required_roles": [p.role] + [r for r in ("senior", "expert") if r != p.role]}
        if p.validation.tier == "T2":
            policy = p.policy
        a = self.approvals.create(kind="terminal", thread_id=t["id"], incident_id=inc["id"] if inc else None, card_id=cd["id"],
                                  steps=[p.step_dict()], tier=p.validation.tier, policy=policy, requested_by=actor)
        self.agents.cards.patch(cd["id"], body={"approval_id": a["id"], "approval_progress": a["progress_text"]})
        return {"accepted": True, "message": f"Confirm to run ({p.validation.tier})", "catalog_id": catalog_id,
                "card_id": cd["id"], "thread_id": t["id"]}

    # ------------------------------------------------------------ approvals

    async def decide_approval(self, approval_id: str, body) -> dict:
        a = self.approvals.get(approval_id)
        actor = body.actor
        user = self.users.get(actor)
        if a.get("kind") == "decision" and body.decision != "reject":
            return await self._decide_options(a, body)
        approval, complete = self.approvals.decide(approval_id, actor, body.decision, params=body.params,
                                                   reason_code=body.reason_code, comment=body.comment, read_only=self.read_only)
        await self._after_decision(approval, body, complete, user)
        return {"approval": self.approvals.public(approval), "resumed": complete and bool(approval.get("graph_key"))}

    async def _after_decision(self, approval: dict, body, complete: bool, user: dict) -> None:
        actor = body.actor
        edited = body.decision == "edit_approve" and body.params is not None and self._params_changed(approval, body.params)
        outcome = "rejected" if body.decision == "reject" else ("edited" if edited else "approved")
        for st in approval.get("steps", []):
            if st.get("catalog_id"):
                self.ledger.record_decision(st["catalog_id"], st.get("param_class", "any"), "operator" if approval.get(
                    "requested_by") in ("baton", None) else self.commands.role_of(approval["requested_by"]),
                    actor, outcome, body.reason_code, evaluate=not approval.get("incident_id"))
        self.audit.append("user", actor, "approval.decide", approval["id"],
                          {"decision": body.decision, "rendered": approval["rendered"], "status": approval["status"],
                           "reason_code": body.reason_code, "params": body.params},
                          policy_rule_ids=approval.get("policy", {}).get("rule_ids", []), incident_id=approval.get("incident_id"))
        if approval.get("incident_id"):
            self.incidents.timeline(approval["incident_id"], "approval_decided", self.users.actor_ref(actor),
                                    f"{user['name']} {'rejected' if body.decision == 'reject' else 'approved'}: "
                                    f"{', '.join(approval['rendered'])}", approval["progress_text"],
                                    {"type": "approval", "id": approval["id"]})
        if approval.get("card_id"):
            card = self.agents.cards.get(approval["card_id"])
            if card and card["type"] == "command":
                status = {"partially_approved": "partially_approved", "rejected": "rejected", "approved": card["status"]}.get(
                    approval["status"], card["status"])
                self.agents.cards.patch(card["id"], status=status if approval["status"] != "approved" else card["status"],
                                        body={"approval_progress": approval["progress_text"],
                                              "approvers": self.approvals.approver_names(approval)},
                                        actions=[] if approval["status"] in ("approved", "rejected") else card["actions"])
            elif card and card["type"] == "decision":
                self._sync_decision_card(approval)
        if approval.get("option_parent"):
            parent = self.approvals.get(approval["option_parent"])
            self._sync_decision_card(parent)
        if complete:
            if approval.get("kind") == "terminal" and approval["status"] == "approved":
                self.spawn(self._run_terminal_approval(approval))
            elif approval.get("graph_key"):
                await self.agents.on_approval_complete(approval)
            elif approval.get("kind") == "undo" and approval["status"] == "approved":
                self.spawn(self._run_undo(approval))

    def _params_changed(self, approval: dict, params: dict) -> bool:
        for st in approval.get("steps", []):
            p = params.get(st["step_id"], params) if isinstance(params, dict) else params
            for k, v in (p or {}).items():
                if str(st.get("params", {}).get(k)) != str(v):
                    return True
        return False

    async def _decide_options(self, a: dict, body) -> dict:
        """Decision card: each selected option gets its own approval record; the decider's approval counts first."""
        if a["status"] not in ("pending", "partially_approved"):
            raise ApiError("CONFLICT", f"Decision already {a['status']}")
        actor = body.actor
        options = {o["id"]: o for o in (a.get("extra") or {}).get("options", [])}
        chosen = list(body.option_ids or [])
        if not chosen:
            raise ApiError("VALIDATION_FAILED", "Select at least one option", {"option_ids": []})
        expanded: list[str] = []
        for oid in chosen:
            o = options.get(oid)
            if not o:
                raise ApiError("VALIDATION_FAILED", f"Unknown option {oid}")
            if o.get("blocked"):
                raise ApiError("POLICY_DENIED", f"{o['label']} is blocked: {o.get('block_reason')}",
                               {"escalation": o.get("escalation")})
            for x in (o.get("includes") or [oid]):
                if x not in expanded and options[x].get("steps"):
                    expanded.append(x)
        if not expanded:
            if chosen != ["opt_none"]:
                raise ApiError("VALIDATION_FAILED", "The selected options have no actions to run")
            # "Do nothing" is a decision too: record it, resume the graph with nothing to execute
            a["option_ids"] = ["opt_none"]
            a["extra"] = {**(a.get("extra") or {}), "selected": [], "option_approvals": {}}
            self.approvals.save(a)
            a, _ = self.approvals.decide(a["id"], actor, "approve")
            a["extra"] = {**(a.get("extra") or {}), "selected": [], "option_approvals": {}}
            self.approvals.save(a)
            self.audit.append("user", actor, "approval.decide", a["id"], {"decision": "do_nothing"},
                              incident_id=a.get("incident_id"))
            if a.get("incident_id"):
                self.incidents.timeline(a["incident_id"], "approval_decided", self.users.actor_ref(actor),
                                        f"{self.users.name(actor)} chose: Do nothing", "No change; incident stays open",
                                        {"type": "approval", "id": a["id"]})
            self._sync_decision_card(a)
            await self.agents.on_approval_complete(a)
            return {"approval": self.approvals.public(a), "resumed": True}
        # validate the actor may make the first approval on each option before creating anything
        user = self.users.get(actor)
        if self.read_only:
            raise ApiError("POLICY_DENIED", "Read-only mode is on", {"rule_ids": ["read-only"]})
        option_approvals = {}
        for oid in expanded:
            o = options[oid]
            steps = []
            policy = None
            for stp in o["steps"]:
                p = self.commands.prepare(stp["catalog_id"], stp["params"], actor, a.get("incident_id"))
                if p.denied:
                    raise ApiError("POLICY_DENIED", p.policy["explanation"], {"rule_ids": p.policy["rule_ids"]})
                steps.append(p.step_dict())
                if policy is None or p.policy["required_approvers"] > policy["required_approvers"]:
                    policy = p.policy
            oa = self.approvals.create(kind="option", thread_id=a["thread_id"], incident_id=a.get("incident_id"),
                                       card_id=a.get("card_id"), steps=steps, tier=o["tier"], policy=policy,
                                       option_ids=[oid], requested_by="baton", graph_key=a.get("graph_key"),
                                       extra={"option_parent": a["id"]})
            oa["option_parent"] = a["id"]
            self.approvals.save(oa)
            oa, complete = self.approvals.decide(oa["id"], actor, "approve", read_only=self.read_only)
            for st in steps:
                self.ledger.record_decision(st["catalog_id"], st.get("param_class", "any"), "operator", actor, "approved",
                                            evaluate=False)
            option_approvals[oid] = oa["id"]
            self.audit.append("user", actor, "approval.decide", oa["id"], {"decision": "approve", "option": oid,
                                                                           "rendered": oa["rendered"], "status": oa["status"]},
                              policy_rule_ids=policy.get("rule_ids", []), incident_id=a.get("incident_id"))
            if a.get("incident_id"):
                self.incidents.timeline(a["incident_id"], "approval_decided", self.users.actor_ref(actor),
                                        f"{user['name']} approved {o['label']}", oa["progress_text"], {"type": "approval", "id": oa["id"]})
        a["option_ids"] = expanded
        a["extra"] = {**(a.get("extra") or {}), "selected": expanded, "option_approvals": option_approvals}
        self.approvals.save(a)
        a, complete = self.approvals.decide(a["id"], actor, "approve", read_only=self.read_only)
        a["extra"] = {**(a.get("extra") or {}), "selected": expanded, "option_approvals": option_approvals}
        self.approvals.save(a)
        self._sync_decision_card(a)
        await self.agents.on_approval_complete(a)
        return {"approval": self.approvals.public(a), "resumed": True}

    def _sync_decision_card(self, decision: dict) -> None:
        card = self.agents.cards.get(decision.get("card_id")) if decision.get("card_id") else None
        if not card or card["type"] != "decision":
            return
        extra = decision.get("extra") or {}
        oas = extra.get("option_approvals", {})
        opts = card["body"]["options"]
        for o in opts:
            if o["id"] in oas:
                oa = self.approvals.get(oas[o["id"]])
                o["approval_id"] = oa["id"]
                if o["status"] not in ("executed",):
                    o["status"] = {"pending": "awaiting_approval", "partially_approved": "partially_approved",
                                   "approved": "approved", "rejected": "rejected", "expired": "rejected"}[oa["status"]]
            elif o["id"] in extra.get("selected", []) or (o.get("includes") and set(o["includes"]) <= set(extra.get("selected", []))):
                o["status"] = "selected"
        self.agents.cards.patch(card["id"], body={"options": opts, "selected": extra.get("selected", []),
                                                  "approval_id": decision["id"]},
                                status="done" if decision["status"] == "approved" else card["status"],
                                actions=[] if decision["status"] == "approved" else card["actions"])

    async def _run_terminal_approval(self, approval: dict) -> None:
        st = approval["steps"][0]
        actor = self.approvals.approvers(approval)[0]
        p = self.commands.prepare(st["catalog_id"], st["params"], actor, approval.get("incident_id"), step_id=st["step_id"])
        try:
            ex = await self.commands.run(p, actor=actor, approved_by=self.approvals.approvers(approval), auto=False,
                                         approval_id=approval["id"], thread_id=approval["thread_id"],
                                         incident_id=approval.get("incident_id"))
            if approval.get("card_id"):
                from .agents.cards import execution_block
                from .agents.graphs.command import interpret_template
                self.agents.cards.patch(approval["card_id"], status="done", actions=["undo"] if ex.get("undo_entry_id") else [],
                                        body={"execution": execution_block(self, ex, interpret_template(self, st["catalog_id"], ex.get("facts") or {}), "fallback")})
        except ApiError as e:
            log.warning("terminal approval run failed: %s", e.message)

    # ------------------------------------------------------------ undo

    async def undo_execution(self, exec_id: str, actor: str) -> dict:
        self.users.get(actor)
        ex = self.executor.get(exec_id)
        if not ex.get("undo_entry_id"):
            raise ApiError("CONFLICT", "This execution has no undo")
        inc_id = ex.get("incident_id")
        inc = self.incidents.get(inc_id) if inc_id else None
        entry = next((u for u in (inc or {}).get("undo_stack", []) if u["id"] == ex["undo_entry_id"]), None)
        if not entry or entry["status"] != "pending":
            raise ApiError("CONFLICT", "Undo already applied or discarded")
        p = self.commands.prepare(entry["catalog_id"], entry["params"], actor, inc_id)
        if not p.validation.valid:
            raise ApiError("VALIDATION_FAILED", "; ".join(p.validation.errors))
        if p.denied:
            raise ApiError("POLICY_DENIED", p.policy["explanation"], {"rule_ids": p.policy["rule_ids"]})
        thread_id = ex.get("thread_id") or self._terminal_thread(actor)["id"]
        a = self.approvals.create(kind="undo", thread_id=thread_id, incident_id=inc_id, card_id=None, steps=[p.step_dict()],
                                  tier=p.validation.tier, policy=p.policy, requested_by=actor,
                                  extra={"undo_entry_id": entry["id"], "exec_id": exec_id})
        self.audit.append("user", actor, "undo.request", p.validation.rendered, {"exec_id": exec_id, "undo_entry_id": entry["id"]},
                          incident_id=inc_id)
        if p.policy["effect"] == "allow_auto":
            a, _ = self.approvals.decide(a["id"], actor, "approve")
            done = await self._run_undo(a)
            return {"accepted": True, "message": "Undo ran", "approval_id": a["id"], "exec_id": done}
        a, complete = self.approvals.decide(a["id"], actor, "approve", read_only=self.read_only)
        if complete:
            done = await self._run_undo(a)
            return {"accepted": True, "message": "Undo ran", "approval_id": a["id"], "exec_id": done}
        return {"accepted": True, "message": a["progress_text"], "approval_id": a["id"]}

    async def _run_undo(self, a: dict) -> str | None:
        st = a["steps"][0]
        approvers = self.approvals.approvers(a)
        p = self.commands.prepare(st["catalog_id"], st["params"], approvers[0], a.get("incident_id"))
        ex = await self.commands.run(p, actor=approvers[0], approved_by=approvers, auto=False, approval_id=a["id"],
                                     thread_id=a["thread_id"], incident_id=None)
        undo_id = (a.get("extra") or {}).get("undo_entry_id")
        orig = self.executor.get((a.get("extra") or {}).get("exec_id"))
        if a.get("incident_id") and undo_id:
            self.incidents.mark_undo(a["incident_id"], undo_id, "applied")
            self.incidents.timeline(a["incident_id"], "undo", self.users.actor_ref(approvers[0]), f"Undo: {p.validation.rendered}",
                                    " and ".join(self.users.name(x) for x in approvers), {"type": "execution", "id": ex["id"]})
        self.ledger.record_undo(orig["catalog_id"], orig.get("param_class", "any"), orig.get("role", "operator"),
                                bool(orig.get("auto")), approvers[0])
        self.audit.append("user", approvers[0], "undo.execute", p.validation.rendered, {"exec_id": ex["id"], "undo_of": orig["id"]},
                          incident_id=a.get("incident_id"))
        return ex["id"]

    # ------------------------------------------------------------ incidents

    def incident_detail(self, incident_id: str) -> dict:
        inc = self.incidents.get(incident_id)
        if not inc:
            raise ApiError("NOT_FOUND", f"Incident {incident_id} not found")
        st = self.store.kv_get(f"incident_state:{incident_id}", {})
        approvals = [self.approvals.public(a) for a in self.store.all("approvals", "incident_id = ?", (incident_id,))]
        execs = [public_execution(e) for e in self.store.all("executions") if e.get("incident_id") == incident_id]
        return {**inc, "hypotheses": st.get("hypotheses", []), "options": st.get("options", []), "approvals": approvals,
                "executions": execs, "verification": st.get("verification"),
                "postmortem_ready": self.incidents.postmortem(incident_id) is not None,
                "cards": self.agents.cards.for_incident(incident_id)}

    async def close_incident(self, incident_id: str, actor: str) -> dict:
        self.users.get(actor)
        inc = self.incidents.get(incident_id)
        if not inc:
            raise ApiError("NOT_FOUND", f"Incident {incident_id} not found")
        inc = self.incidents.set_status(incident_id, "resolved", self.users.actor_ref(actor), "Closed by a person")
        self.audit.append("user", actor, "incident.close", incident_id, {}, incident_id=incident_id)
        return inc

    async def whatif(self, incident_id: str, actions: list) -> dict:
        """P1: predict 600 sim-seconds ahead on a fork of the simulator (no events, nothing executed)."""
        from .sim.whatif import fork, predict
        if incident_id != "none" and not self.incidents.get(incident_id):
            raise ApiError("NOT_FOUND", f"Incident {incident_id} not found")
        self._require_sim()
        checked = []
        for a in actions or []:
            p = self.commands.prepare(a.get("catalog_id", ""), a.get("params") or {}, "baton", incident_id)
            if not p.validation.valid:
                raise ApiError("VALIDATION_FAILED", "; ".join(p.validation.errors), {"catalog_id": a.get("catalog_id")})
            if p.validation.tier == "T3":
                raise ApiError("POLICY_DENIED", "T3 actions are not modeled: human-only, outside Baton")
            checked.append({"catalog_id": p.catalog_id, "params": p.validation.params})
        return await predict_async(self, checked)

    # ------------------------------------------------------------ knowledge

    def review_claim(self, claim_id: str, body) -> dict:
        out = self.claims.review(claim_id, body.decision, body.edits, body.reason, body.actor)
        self.audit.append("user", body.actor, "claim.review", claim_id, {"decision": body.decision, "edits": body.edits,
                                                                          "reason": body.reason})
        return out

    # ------------------------------------------------------------ ledger and policy

    def ledger_grant(self, key: str, level: str, reason: str, actor: str) -> dict:
        user = self.users.get(actor)
        if user["role"] not in ("expert", "steward"):
            raise ApiError("POLICY_DENIED", "Only experts or stewards grant autonomy")
        if level == "system":
            raise ApiError("VALIDATION_FAILED", "Cannot grant the system level")
        e = self.ledger.raw(key)
        if not e:
            raise ApiError("NOT_FOUND", f"Ledger entry {key} not found")
        if e.get("tier") in ("T2", "T3") and level in ("L2", "L3"):
            raise ApiError("POLICY_DENIED", "T2 and T3 commands always need people")
        out = self.ledger.grant(key, level, reason, actor)
        self.audit.append("user", actor, "ledger.grant", key, {"level": level, "reason": reason, "from": e["level"]})
        return out

    def ledger_revoke(self, key: str, reason: str, actor: str) -> dict:
        user = self.users.get(actor)
        if user["role"] not in ("expert", "steward"):
            raise ApiError("POLICY_DENIED", "Only experts or stewards revoke autonomy")
        if not self.ledger.raw(key):
            raise ApiError("NOT_FOUND", f"Ledger entry {key} not found")
        out = self.ledger.revoke(key, reason, actor)
        self.audit.append("user", actor, "ledger.revoke", key, {"reason": reason})
        return out

    def policy_describe(self) -> dict:
        return self.policy.describe(self.read_only)

    # ------------------------------------------------------------ eval

    def eval_latest(self) -> dict | None:
        rows = self.store.all("eval_runs", order="started_at DESC", limit=1)
        return rows[0] if rows else None

    async def eval_run(self, suites: list[str] | None) -> dict:
        from .eval.runner import run_eval_background
        run_id = new_id("evr")
        self.spawn(run_eval_background(self, run_id, suites))
        return {"run_id": run_id}


async def predict_async(rt, actions: list[dict], service: str = "atm") -> dict:
    """Fork on the event-loop thread (consistent snapshot), simulate in a worker thread."""
    from .sim.whatif import fork, predict
    snapshot = fork(rt.sim.model)
    return await asyncio.to_thread(predict, snapshot, actions, 600, service)

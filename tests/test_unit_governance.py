"""Table-driven policy plus persisted ledger, token, approval and audit invariants."""
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from baton.api.errors import ApiError
from baton.db.store import Store
from baton.governance.approvals import Approvals
from baton.governance.audit import AuditLog, GENESIS
from baton.governance.ledger import Ledger
from baton.governance.policy import Policy, PolicyContext
from baton.governance.tokens import TokenError, Tokens

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def store(tmp_path):
    database = Store(tmp_path / "governance.db")
    yield database
    database.close()


@pytest.mark.parametrize("tier,level,target,read_only,internal,effect,count,rule", [
    ("T1", "L3", "$STMT1", True, False, "deny", 0, "read-only"),
    ("T2", "L3", None, True, False, "deny", 0, "read-only"),
    ("T3", "L3", None, False, False, "deny", 0, "t3-block"),
    ("T1", "L3", "$PM1", False, False, "deny", 0, "protected"),
    ("T2", "L3", "$ZLM5", False, False, "deny", 0, "protected"),
    ("T2", "L3", "ATM-AUTH", False, False, "require_approval", 2, "t2-two-person"),
    ("T1", "L1", "$STMT1", False, False, "require_approval", 1, "t1-single"),
    ("T1", "L3", "$STMT1", False, False, "allow_auto", 0, "t1-ledger-l3"),
    ("T0", "L2", None, False, False, "allow_auto", 0, "t0-ledger"),
    ("T0", "L1", None, False, False, "require_approval", 1, "t0-default"),
    ("T0", "L2", None, True, False, "allow_auto", 0, "t0-ledger"),
    ("T0", "L1", None, True, True, "allow_auto", 0, "system-lane"),
])
def test_policy_table(tier, level, target, read_only, internal, effect, count, rule):
    policy = Policy(ROOT / "data/policies/policy.yaml")
    decision = policy.evaluate(PolicyContext("test.command", tier, target, "operator", level,
                                             read_only=read_only, internal=internal))
    assert (decision.effect, decision.required_approvers) == (effect, count)
    assert rule in decision.rule_ids
    assert decision.explanation
    if rule == "t2-two-person":
        assert set(decision.at_least_one_of) == {"senior", "expert"}


def test_deny_overrides_granted_autonomy_and_state_change_limit():
    policy = Policy(ROOT / "data/policies/policy.yaml")
    decision = policy.evaluate(PolicyContext("tacl.suspend_process", "T1", "$PM1", "expert", "L3",
                                             read_only=True, state_changes_recent=3))
    assert decision.effect == "deny"
    assert set(decision.rule_ids) == {"read-only", "protected", "rate-limit"}


@pytest.fixture
def ledger(store):
    return Ledger(store, ROOT / "data/policies/ledger_seed.yaml", lambda *args: None,
                  lambda uid: uid, lambda cid: "T0" if cid.startswith("test.read") else "T1")


def record(ledger, cid, n, approvers=2, outcome="approved", **kwargs):
    for i in range(n):
        ledger.record_decision(cid, "any", "operator", f"operator-{i % approvers}", outcome, **kwargs)


def test_ledger_promotes_only_after_twenty_unchanged_and_two_approvers(ledger):
    cid = "test.read_threshold"
    record(ledger, cid, 19)
    assert ledger.raw(cid + "|any|operator")["eligible_for"] is None
    record(ledger, cid, 1)
    assert ledger.raw(cid + "|any|operator")["eligible_for"] == "L2"
    assert ledger.level(cid, "any", "operator")["level"] == "L1"  # candidate still needs expert grant
    record(ledger, "test.read_single", 20, approvers=1)
    assert ledger.raw("test.read_single|any|operator")["eligible_for"] is None
    record(ledger, "test.mutation", 20)
    assert ledger.raw("test.mutation|any|operator")["eligible_for"] is None


def test_ledger_rejection_ages_out_after_twenty_clean_decisions(ledger):
    cid = "test.read_window"
    record(ledger, cid, 1, outcome="rejected")
    record(ledger, cid, 19)
    entry = ledger.raw(cid + "|any|operator")
    assert not ledger.candidate_status(entry)
    record(ledger, cid, 1)
    entry = ledger.raw(cid + "|any|operator")
    assert entry["eligible_for"] == "L2" and entry["recent_rejections"] == 0


def test_edited_decisions_do_not_count_as_unchanged(ledger):
    record(ledger, "test.read_edited", 19)
    record(ledger, "test.read_edited", 1, outcome="edited")
    entry = ledger.raw("test.read_edited|any|operator")
    assert entry["counters"]["approved_unchanged"] == 19
    assert entry["eligible_for"] is None


@pytest.mark.parametrize("cause", ["unsafe_now", "verify_fail", "undo_auto"])
def test_ledger_demotes_one_level_with_floor_l1(ledger, cause):
    cid, key = "test.read_demote", "test.read_demote|any|operator"
    record(ledger, cid, 20)
    ledger.grant(key, "L2", "Synthetic test grant", "u_dave")
    for _ in range(2):
        if cause == "unsafe_now":
            record(ledger, cid, 1, outcome="rejected", reason_code="unsafe_now")
        elif cause == "verify_fail":
            ledger.record_verification(cid, "any", "operator", False)
        else:
            ledger.record_undo(cid, "any", "operator", True, "u_priya")
        assert ledger.raw(key)["level"] == "L1"
    assert sum(h["kind"] == "demotion" for h in ledger.raw(key)["history"]) == 1


def test_manual_undo_does_not_demote(ledger):
    cid, key = "test.read_manual", "test.read_manual|any|operator"
    record(ledger, cid, 20)
    ledger.grant(key, "L2", "Synthetic test grant", "u_dave")
    ledger.record_undo(cid, "any", "operator", False, "u_priya")
    assert ledger.raw(key)["level"] == "L2"


def test_execution_token_single_use_and_wrong_command(store):
    tokens = Tokens(store, secret=b"synthetic-unit-test-key")
    token = tokens.issue("STATUS $STMT1", "approval-1")
    with pytest.raises(TokenError, match="does not match"):
        tokens.consume(token, "STOP $STMT1")
    assert tokens.consume(token, "STATUS $STMT1") == "approval-1"
    with pytest.raises(TokenError, match="already used"):
        tokens.consume(token, "STATUS $STMT1")


def test_execution_token_expiry_and_signature(store, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr("baton.governance.tokens.time.time", lambda: now[0])
    tokens = Tokens(store, ttl_s=120, secret=b"synthetic-unit-test-key")
    token = tokens.issue("STATUS $STMT1", "approval-1")
    tid, _ = token.split(".", 1)
    with pytest.raises(TokenError, match="signature"):
        tokens.consume(tid + ".bad", "STATUS $STMT1")
    now[0] += 121
    with pytest.raises(TokenError, match="expired"):
        tokens.consume(token, "STATUS $STMT1")


def test_audit_hash_chain_and_payload_tampering(store):
    audit = AuditLog(store, lambda *args: None, lambda: "2026-11-27T11:52:00Z")
    assert audit.verify()["valid"] and audit.verify()["entries"] == 0
    first = audit.append("user", "u_priya", "approve", payload={"synthetic": True, "target": "$STMT1"})
    second = audit.append("system", "baton", "execute", payload={"synthetic": True})
    assert first["prev_hash"] == GENESIS and second["prev_hash"] == first["hash"]
    assert audit.verify() == {"valid": True, "entries": 2, "head_hash": second["hash"], "first_bad_seq": None}
    store.execute("UPDATE audit_log SET payload=? WHERE seq=1", ('{"synthetic":true,"target":"$PM1"}',))
    assert audit.verify()["valid"] is False
    assert audit.verify()["first_bad_seq"] == 1


def test_audit_missing_predecessor_detected(store):
    audit = AuditLog(store, lambda *args: None, lambda: None)
    audit.append("system", "baton", "one")
    audit.append("system", "baton", "two")
    store.execute("DELETE FROM audit_log WHERE seq=1")
    assert audit.verify()["valid"] is False and audit.verify()["first_bad_seq"] == 2


@pytest.fixture
def approvals(store):
    clock = [datetime(2026, 11, 27, 11, 52)]
    users = {uid: {"name": uid, "role": role} for uid, role in [
        ("u_priya", "operator"), ("operator2", "operator"), ("u_sam", "senior"),
        ("u_dave", "expert"), ("u_lee", "steward")
    ]}
    service = Approvals(store, lambda *args: None, SimpleNamespace(get=users.__getitem__), lambda: clock[0])
    return service, clock


def approval(service, count=2):
    return service.create(kind="command", thread_id="synthetic-thread", incident_id=None, card_id=None,
                          steps=[{"step_id": "synthetic-step", "rendered": "ALTER SERVER ATM-AUTH, NUMSTATIC 28"}],
                          tier="T2" if count == 2 else "T1",
                          policy={"required_approvers": count, "required_roles": ["operator", "senior", "expert"],
                                  "at_least_one_of": ["senior", "expert"] if count == 2 else []})


def test_two_person_requires_distinct_eligible_people(approvals):
    service, _ = approvals
    pending = approval(service)
    first, complete = service.decide(pending["id"], "u_priya", "approve")
    assert first["status"] == "partially_approved" and not complete
    with pytest.raises(ApiError, match="different person"):
        service.decide(pending["id"], "u_priya", "approve")
    with pytest.raises(ApiError, match="at least one"):
        service.decide(pending["id"], "operator2", "approve")
    final, complete = service.decide(pending["id"], "u_sam", "approve")
    assert final["status"] == "approved" and complete
    assert service.approvers(final) == ["u_priya", "u_sam"]


def test_role_check_and_read_only_revalidate_pending_approval(approvals):
    service, _ = approvals
    pending = approval(service, 1)
    with pytest.raises(ApiError, match="cannot approve"):
        service.decide(pending["id"], "u_lee", "approve")
    with pytest.raises(ApiError, match="Read-only"):
        service.decide(pending["id"], "u_priya", "approve", read_only=True)
    assert service.get(pending["id"])["decisions"] == []


def test_reject_requires_reason_and_finishes_approval(approvals):
    service, _ = approvals
    pending = approval(service)
    with pytest.raises(ApiError, match="reason code"):
        service.decide(pending["id"], "u_priya", "reject")
    rejected, complete = service.decide(pending["id"], "u_priya", "reject", reason_code="unsafe_now")
    assert rejected["status"] == "rejected" and complete
    assert service.approvers(rejected) == []


def test_expiry_uses_sim_time_without_sleeping(approvals):
    service, clock = approvals
    pending = approval(service)
    clock[0] += timedelta(seconds=601)
    with pytest.raises(ApiError, match="expired"):
        service.decide(pending["id"], "u_sam", "approve")
    assert service.get(pending["id"])["status"] == "expired"

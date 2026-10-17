"""Scorer reproduces the S1 trajectory in MVP spec §12.2; next-best batch; stop rule."""
from baton.core.config import DATA
from baton.diagnosis.engine import Diagnosis

D = Diagnosis(DATA / "rules")


def ev(*names):
    return {n: {"evidence_id": f"ev_{n}", "label": n} for n in names}


def p(hyps, mid):
    return next(h["p"] for h in hyps if h["id"] == mid)


def test_s1_trajectory():
    situation = ev("cpu_down", "takeover", "link_errors", "latency_out_of_band")
    h0 = D.score(situation)
    assert abs(p(h0, "cpu_capacity_loss") - 0.54) < 0.01
    assert abs(p(h0, "server_class_starvation") - 0.30) < 0.01
    h1 = D.score({**situation, **ev("cpu_busy_high_survivor", "sc_lost_servers", "sc_not_at_max")})
    assert abs(p(h1, "cpu_capacity_loss") - 0.94) < 0.01
    h2 = D.score({**situation, **ev("cpu_busy_high_survivor", "sc_lost_servers", "sc_not_at_max", "audit_fill_normal")})
    assert abs(p(h2, "cpu_capacity_loss") - 0.95) < 0.01
    assert D.stop_rule(h2, 2)["met"] and not D.stop_rule(h0, 1)["met"]


def test_batch_of_three_on_a_peak_day():
    h0 = D.score(ev("cpu_down", "takeover", "link_errors", "latency_out_of_band"))
    auto = {"meas.cpu_busy", "pathcom.status_server", "pathcom.info_server", "baton.n1_headroom"}
    batch = D.next_checks(h0, set(), peak_day=True, auto_runnable=lambda c: c in auto)
    ids = [c["catalog_id"] for c in batch]
    assert ids[:2] == ["pathcom.status_server", "meas.cpu_busy"]
    assert ids[2] == "tmfcom.status_audittrail"


def test_s3_starvation_ends_near_087():
    # ATM-AUTH is at MAXSERVERS, so internals_healthy does not fire
    h = D.score(ev("link_errors", "latency_out_of_band", "sc_at_max_queued"))
    assert h[0]["id"] == "server_class_starvation"
    assert 0.8 < h[0]["p"] < 0.95

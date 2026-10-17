"""MVP §6.2 calibration on a seeded model, advanced synchronously in sim-seconds."""
from pathlib import Path

import pytest
import yaml

from baton.health.n1 import compute_n1
from baton.sim.model import SimModel

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def model():
    def read(path):
        return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))
    return SimModel(read("data/site/torbank.yaml"), read("data/scenarios/S1.yaml"), 42)


def step(model, seconds):
    for _ in range(seconds):
        model.step()


def halt_at_peak(model):
    step(model, 420)
    model.halt_cpu(3)
    step(model, 60)


def test_n1_warns_at_s1_start_without_mutating_placement(model):
    step(model, 20)
    before = (list(model.cpu_up), [(p.name, p.cpu, p.state) for p in model.processes.values()])
    result = compute_n1(model)
    assert result["safe"] is False
    assert (result["worst_lost_cpu"], result["worst_survivor_cpu"]) == (3, 5)
    assert 95 <= result["worst_survivor_busy"] <= 97
    assert set(result["per_cpu"]) == {str(c) for c in range(8)}
    assert before == (model.cpu_up, [(p.name, p.cpu, p.state) for p in model.processes.values()])


def test_healthy_calibration(model):
    step(model, 20)
    atm, pos = model.classes["ATM-AUTH"], model.classes["POS-AUTH"]
    assert all(45 <= busy <= 65 for busy in model.cpu_busy)
    assert model.cpu_busy[5] == pytest.approx(62, abs=3)
    assert 150 <= atm.p95_ms <= 200
    assert 140 <= pos.p95_ms <= 180
    assert 25 <= model.tmf.fill_pct <= 35
    assert atm.running(model.tick) == 24


def test_halt_plus_60_seconds_calibration(model):
    halt_at_peak(model)
    atm = model.classes["ATM-AUTH"]
    assert model.cpu_up[3] is False
    assert 95 <= model.cpu_busy[5] <= 98
    assert all(75 <= model.cpu_busy[c] <= 85 for c in (2, 4))
    assert atm.running(model.tick) == 20
    assert 100 <= atm.queued <= 180
    assert 750 <= atm.p95_ms <= 1000
    assert 2 <= atm.timeout_pct <= 4
    assert "3" not in compute_n1(model)["per_cpu"]


def mitigated(model):
    halt_at_peak(model)
    step(model, 180)
    before = model.cpu_busy[5]
    model.processes["$STMT1"].state = "SUSPENDED"
    step(model, 30)
    drop = before - model.cpu_busy[5]
    step(model, 10)
    placed = model.set_numstatic("ATM-AUTH", 28)
    step(model, 60)
    return drop, placed


def test_suspend_drop_and_static_server_placement(model):
    drop, placed = mitigated(model)
    assert 12 <= drop <= 18
    assert len(placed["started_on"]) == 8
    assert set(placed["started_on"]) == {1, 6}
    atm = model.classes["ATM-AUTH"]
    assert atm.running(model.tick) == 28
    assert atm.queued == pytest.approx(0, abs=2)  # fractional queue smoothing; within two requests of empty
    assert atm.timeout_pct < 0.2


@pytest.mark.xfail(reason="B-REQ-6: recovered ATM p95 is below the 200–260 ms calibration target", strict=True)
def test_numstatic_plus_60_latency_target(model):
    mitigated(model)
    assert 200 <= model.classes["ATM-AUTH"].p95_ms <= 260


def test_do_nothing_plus_ten_minutes(model):
    halt_at_peak(model)
    step(model, 540)
    atm = model.classes["ATM-AUTH"]
    assert atm.p95_ms > 1200
    assert 5 <= atm.timeout_pct <= 8

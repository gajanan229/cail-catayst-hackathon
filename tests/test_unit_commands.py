"""Renderer safety, inventory/domain validation, and exact manual catalog matching."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from baton.commands.catalog import Catalog
from baton.commands.service import CommandService
from baton.commands.validator import render_template, validate
from baton.governance.policy import Policy, PolicyContext
from baton.sim.engine import Simulator

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def services():
    sim = Simulator(ROOT / "data", chatter_scale=0)
    sim.load("S1", "demo", seed=42)
    sim.status.paused = True
    catalog = Catalog(ROOT / "data/catalog")
    policy = Policy(ROOT / "data/policies/policy.yaml")
    commands = CommandService(SimpleNamespace(sim=sim, catalog=catalog, policy=policy))
    return catalog, commands, policy


@pytest.mark.parametrize("value", ["$STMT1;STOP", "$ST MT1", "$STMT1\nSTOP TMF", "$STMT1\r", "$STMT1\tX"])
def test_renderer_rejects_shell_separators_and_whitespace(value):
    with pytest.raises(ValueError, match="unsafe value"):
        render_template("SUSPEND {process}", {"process": value})


def test_renderer_rejects_trailing_newline():
    with pytest.raises(ValueError, match="unsafe value"):
        render_template("SUSPEND {process}", {"process": "$STMT1\n"})


def test_safe_rendering_is_exact():
    assert render_template("ALTER SERVER {server_class}, NUMSTATIC {n}", {"server_class": "ATM-AUTH", "n": 28}) == \
        "ALTER SERVER ATM-AUTH, NUMSTATIC 28"


@pytest.mark.parametrize("n,valid", [(28, True), (32, True), (33, False)])
def test_numstatic_does_not_exceed_maxservers(services, n, valid):
    catalog, commands, _ = services
    result = validate(catalog.get("pathcom.alter_numstatic"), {"server_class": "ATM-AUTH", "n": n}, commands.inventory())
    assert result.valid is valid
    assert result.tier == "T2"
    if not valid:
        assert any("2049" in error for error in result.errors)
    else:
        assert result.undo["params"]["n"] == 20


@pytest.mark.parametrize("target", ["$PM1", "$DATA02", "$ZLM5", "$TMP"])
def test_protected_inventory_and_policy_deny_state_change(services, target):
    _, commands, policy = services
    assert commands.inventory().is_protected(target)
    decision = policy.evaluate(PolicyContext("tacl.suspend_process", "T2", target, "operator", "L3"))
    assert decision.effect == "deny" and "protected" in decision.rule_ids


def test_unknown_process_rejected_and_alias_normalized(services):
    catalog, commands, _ = services
    inv = commands.inventory()
    unknown = validate(catalog.get("tacl.status_process"), {"process": "$MISSING"}, inv)
    assert not unknown.valid and any("does not exist" in e for e in unknown.errors)
    known = validate(catalog.get("pathcom.status_server"), {"server_class": "ATM auth"}, inv)
    assert known.valid and known.params == {"server_class": "ATM-AUTH"}


@pytest.mark.parametrize("line,cid,params", [
    ("PATHCOM $PM1; STATUS SERVER ATM-AUTH", "pathcom.status_server", {"server_class": "ATM-AUTH"}),
    ("pathcom $pm1; alter server atm-auth, numstatic 28", "pathcom.alter_numstatic", {"server_class": "ATM-AUTH", "n": 28}),
    ("SUSPEND $STMT1", "tacl.suspend_process", {"process": "$STMT1"}),
    ("TMFCOM; STATUS AUDITTRAIL", "tmfcom.status_audittrail", {}),
    ("$SYSTEM STARTUP 14> STATUS $STMT1", "tacl.status_process", {"process": "$STMT1"}),
    ("TMFCOM; STOP TMF", "tmfcom.stop_tmf", {}),
])
def test_manual_lines_match_catalog_without_executing(services, line, cid, params):
    _, commands, _ = services
    assert commands.match_line(line) == (cid, params)


@pytest.mark.parametrize("line", ["STOP TMF; PURGE *", "SUSPEND $STMT1; STOP TMF", "not a command", "Reload processor 3", "PATHCOM $PM2; STATUS SERVER ATM-AUTH"])
def test_manual_non_catalog_lines_rejected(services, line):
    assert services[1].match_line(line) is None

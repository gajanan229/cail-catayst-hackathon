"""Parse frozen synthetic outputs produced by actual S1 simulator handlers.

Each <catalog_id>.txt has healthy and CPU3-halted sections, with JSON generation
metadata in comments. Run this file with --generate to create missing fixtures;
it refuses to overwrite any fixture, preserving the shared-copy ownership rule.
"""
import json
from pathlib import Path

import pytest

from baton.commands.catalog import Catalog
from baton.commands.parsers import PARSERS, parse
from baton.sim.engine import Simulator
from baton.sim.handlers import run_handler

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data/catalog/fixtures"
CATALOG = Catalog(ROOT / "data/catalog")
ENTRIES = [entry for entry in CATALOG.all() if not entry.internal and not entry.blocked]
PARAMS = {
    "tacl.status_cpu": {"cpu": 5}, "tacl.status_process": {"process": "$STMT1"},
    "scf.status_disk": {"volume": "$DATA02"},
    "dsap.disk_space": {"volume": "$DATA03"},
    "tacl.suspend_process": {"process": "$STMT1"}, "tacl.activate_process": {"process": "$STMT1"},
    "tacl.altpri_process": {"process": "$RPT2", "priority": 100}, "tacl.stop_process": {"process": "$RPT2"},
    "pathcom.alter_numstatic": {"server_class": "ATM-AUTH", "n": 28},
    "pathcom.alter_maxservers": {"server_class": "ATM-AUTH", "n": 40},
}
EXPECTED = {
    "meas.cpu_busy": {"hottest_cpu": 5}, "tacl.status_cpu": {},
    "tacl.status_process": {"process": "$STMT1", "state": "RUNNING", "cpu": 5},
    "pathcom.status_pathmon": {"pathmon": "$PM1", "state": "RUNNING"},
    "pathcom.status_server": {"server_class": "ATM-AUTH", "numstatic": 20, "maxservers": 32},
    "pathcom.info_server": {"server_class": "ATM-AUTH", "numstatic": 20, "maxservers": 32},
    "pathcom.stats_server": {"server_class": "ATM-AUTH"}, "tmfcom.status_tmf": {"state": "STARTED"},
    "tmfcom.status_audittrail": {"trail": "MAT", "overflow_pct": 80.0},
    "scf.status_disk": {"primary_half": "STARTED", "mirror_half": "STARTED"},
    "dsap.disk_space": {"volume": "$DATA03", "used_pct": 72.0},
    "tacl.suspend_process": {"process": "$STMT1", "state": "SUSPENDED"},
    "tacl.activate_process": {"process": "$STMT1", "state": "RUNNING"},
    "tacl.stop_process": {"process": "$RPT2", "state": "STOPPED"},
    "tacl.altpri_process": {"process": "$RPT2", "priority": 100},
    "pathcom.alter_numstatic": {"server_class": "ATM-AUTH", "numstatic": 28},
    "pathcom.alter_maxservers": {"server_class": "ATM-AUTH", "maxservers": 40, "previous": 32},
}


def sections(path):
    parts = {}
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# phase: "):
            current = line.removeprefix("# phase: ")
            parts[current] = []
        elif not line.startswith("#") and current is not None:
            parts[current].append(line)
    return parts


def generate_missing_fixtures():
    FIXTURES.mkdir(parents=True, exist_ok=True)
    for entry in ENTRIES:
        path = FIXTURES / f"{entry.id}.txt"
        if path.exists():
            continue
        params = PARAMS.get(entry.id, {"server_class": "ATM-AUTH"} if "server_class" in entry.params else {})
        lines = ["# synthetic: true", "# generator: tests/test_unit_parsers.py --generate",
                 "# scenario: S1 demo; seed: 42; healthy +20s; halted +60s after healthy",
                 "# params: " + json.dumps(params, sort_keys=True)]
        for phase in ("healthy", "cpu3_halted"):
            sim = Simulator(ROOT / "data", chatter_scale=0)
            sim.load("S1", "demo", seed=42)
            sim.status.paused = True
            for _ in range(20):
                sim.step()
            if phase == "cpu3_halted":
                sim.inject("cpu_halt", {"cpu": 3})
                for _ in range(60):
                    sim.step()
            if entry.id == "tacl.activate_process":
                sim.set_process_state("$STMT1", "SUSPENDED")
            lines += ["# phase: " + phase, *run_handler(sim, entry.id, params)]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(path.name)


@pytest.mark.parametrize("entry", ENTRIES, ids=lambda e: e.id)
@pytest.mark.parametrize("phase", ["healthy", "cpu3_halted"])
def test_catalog_parser_against_handler_fixture(entry, phase):
    path = FIXTURES / f"{entry.id}.txt"
    assert path.exists(), f"Missing fixture for {entry.id}"
    assert "# synthetic: true" in path.read_text(encoding="utf-8")
    facts, confidence = parse(entry.parser, sections(path)[phase])
    assert confidence == 1.0
    assert {key: facts[key] for key in EXPECTED[entry.id]} == EXPECTED[entry.id]
    if entry.id == "tacl.status_cpu":
        assert facts["top_process"] == ("ATM-AUTH(4)" if phase == "cpu3_halted" else "$STMT1")
        assert "$STMT1" in [p["name"] for p in facts["processes"]]
    if entry.id == "pathcom.alter_numstatic":
        assert facts["servers_starting"] == (8 if phase == "cpu3_halted" else 4)
        assert facts["on_cpus"] == ([1, 6] if phase == "cpu3_halted" else [1, 2, 4, 6])
    if entry.id == "meas.cpu_busy":
        assert facts["down"] == ([3] if phase == "cpu3_halted" else [])
        assert facts["cpus"]["3"]["busy"] is None if phase == "cpu3_halted" else facts["cpus"]["3"]["busy"] > 0
    if entry.id == "pathcom.status_server":
        assert facts["running"] == (20 if phase == "cpu3_halted" else 24)
        assert facts["queued"] > 0 if phase == "cpu3_halted" else facts["queued"] == 0
    if entry.id == "pathcom.status_pathmon":
        assert facts["primary_cpu"] == (5 if phase == "cpu3_halted" else 3)
    if entry.id == "scf.status_disk":
        assert facts["process_pair"] == ("BACKUP" if phase == "cpu3_halted" else "STARTED")


def test_every_output_parser_has_a_fixture():
    assert {entry.parser for entry in ENTRIES} == set(PARSERS)


@pytest.mark.parametrize("parser_id", sorted(PARSERS))
def test_empty_output_has_zero_confidence(parser_id):
    _, confidence = parse(parser_id, [])
    assert confidence == 0


def test_error_and_unknown_parser_fail_closed():
    facts, confidence = parse("pathcom_ack", ["*ERROR* 2049 NUMSTATIC EXCEEDS MAXSERVERS"])
    assert confidence == 0 and facts["error"] == 2049
    assert parse("not_in_catalog", ["anything"]) == ({}, 0.0)


if __name__ == "__main__":
    import sys
    if sys.argv[1:] != ["--generate"]:
        raise SystemExit("Usage: python tests/test_unit_parsers.py --generate")
    generate_missing_fixtures()

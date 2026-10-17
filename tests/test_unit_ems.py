"""Printing-format fixtures from MVP §6.5 and deterministic template enrichment."""
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from baton.telemetry.ems_parser import parse_line
from baton.telemetry.enrich import MessageCatalog, enrich, template_regex

ROOT = Path(__file__).resolve().parents[1]
LINES = [
    r"26-11-27 11:52:04 \TORBANK.$ZOMF    * TANDEM.OMF.L01      000103 CPU 3, Current State = DOWN, Previous State = UP, Sampling Interval = 1 minutes",
    r"26-11-27 11:52:05 \TORBANK.$PM1     * TANDEM.PATHWAY.L01  001077 *1077* PATHMON, TAKEOVER BY BACKUP",
    r"26-11-27 11:53:12 \TORBANK.$ZLM5      TANDEM.PATHWAY.L01  001007 *1007* $ZLM5, CAN'T GRANT LINK: *1034* $ZLM5, NO SERVER AVAILABLE FOR REQUESTING TCP",
]


@pytest.fixture(scope="module")
def catalog():
    return MessageCatalog(yaml.safe_load((ROOT / "data/rules/ems_messages.yaml").read_text(encoding="utf-8")),
                          ROOT / "data/content/operator_messages.jsonl")


@pytest.mark.parametrize("line,number,process,critical", [
    (LINES[0], 103, "$ZOMF", True), (LINES[1], 1077, "$PM1", True), (LINES[2], 1007, "$ZLM5", False),
])
def test_printing_format_fixture(line, number, process, critical):
    parsed = parse_line(line + "\r\n")
    assert parsed.at.date() == datetime(2026, 11, 27).date()
    assert (parsed.system, parsed.process, parsed.number, parsed.critical) == (r"\TORBANK", process, number, critical)
    assert (parsed.owner, parsed.version) == ("TANDEM", "L01")
    assert parsed.text == line.split(f"{number:06d} ", 1)[1]


@pytest.mark.parametrize("line", ["", "STATUS CPU 3", LINES[0].replace("000103", "103"), LINES[0].replace("TANDEM.OMF.L01", "OMF")])
def test_non_printing_line_rejected(line):
    assert parse_line(line) is None


@pytest.mark.parametrize("subsystem,number,fields,component", [
    ("OMF", 103, {"cpu": "3", "prev": "UP", "n": "1"}, "cpu:3"),
    ("OMF", 217, {"volume": "DATA02", "n": "1"}, "vol:$DATA02"),
    ("OMF", 604, {"process": "STMT1", "prev": "RUNNING", "cpu": "5", "pri": "140", "n": "1"}, "proc:$STMT1"),
    ("PATHWAY", 1034, {"link_manager": "$ZLM5"}, "proc:$ZLM5"),
    ("PATHWAY", 1043, {"object": "SERVER ATM-AUTH $Z123"}, "sc:ATM-AUTH"),
    ("PATHWAY", 1166, {"text": "ALTER SERVER ATM-AUTH, NUMSTATIC 28"}, "sc:ATM-AUTH"),
    ("OMF", 1204, {"id": "MAT01", "usage": "75", "thr": "70"}, "tmf:mat"),
])
def test_variables_and_component_resolution(catalog, subsystem, number, fields, component):
    definition = catalog.get(subsystem, number)
    text = definition.template.format(**fields)
    line = f"26-11-27 11:52:04 \\TORBANK.$ZOMF    TANDEM.{subsystem}.L01 {number:06d} {text}"
    event = enrich(parse_line(line), catalog)
    assert event["fields"] == fields
    assert event["component_id"] == component
    assert event["manual"]["url"].endswith(".html")
    assert event["simulated"] is False


def test_nested_link_template_extracts_entire_nested_message(catalog):
    event = enrich(parse_line(LINES[2]), catalog)
    assert event["fields"] == {"link_manager": "$ZLM5", "nested": "*1034* $ZLM5, NO SERVER AVAILABLE FOR REQUESTING TCP"}
    assert event["fingerprint"] == "PATHWAY:1007:link_manager"


def test_template_literals_and_repeated_variables():
    regex = template_regex("PROCESS ${process}: [{state}] {state}")
    assert regex.fullmatch("PROCESS $STMT1: [RUNNING] RUNNING").groupdict() == {"process": "STMT1", "state": "RUNNING"}
    assert regex.fullmatch("PROCESS XSTMT1: [RUNNING] RUNNING") is None


def test_critical_header_sets_severity_floor_and_unknown_message(catalog):
    event = enrich(parse_line(LINES[0].replace("000103", "009999")), catalog)
    assert event["severity"] >= 4
    assert event["fields"] == {}
    assert event["manual"] is None
    assert event["component_id"] == "proc:$ZOMF"

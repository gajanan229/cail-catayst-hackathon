"""Offline fetcher checks; no network or private manual cache required."""
import importlib.util
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fetch_opmsgs", ROOT / "scripts/fetch_opmsgs.py")
fetcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetcher)


def test_parse_manual_markers_and_replaceable_span():
    # Synthetic HTML fixture exercises the source structure without inventing an HPE message.
    raw = b'''<!--omm.message key="TEST/DEMO/EN/00/1"-->
    <p><tt class="computeroutput">TEST <i class="replaceable"><tt>object-name</tt></i>, OK</tt></p>
    <!--omm.cause-->Synthetic cause.<!--/omm.cause-->
    <!--omm.effect-->Synthetic effect.<!--/omm.effect-->
    <!--omm.recovery-->Synthetic recovery.<!--/omm.recovery--><!--/omm.message-->'''
    record, = fetcher.parse_chapter(raw, 68)
    assert record["text_template"] == "TEST {object_name}, OK"
    assert record["variables"] == ["object_name"]
    assert record["cause"] == "Synthetic cause."


def test_committed_pack_preserves_simulator_templates_and_manual_fields():
    records = [json.loads(line) for line in (ROOT / "data/content/operator_messages.jsonl").read_text(encoding="utf-8").splitlines()]
    assert 60 <= len(records) <= 150
    assert len({r["id"] for r in records}) == len(records)
    by_key = {(r["subsystem"], r["number"]): r for r in records}
    rules = yaml.safe_load((ROOT / "data/rules/ems_messages.yaml").read_text(encoding="utf-8"))
    for rule in rules["messages"]:
        record = by_key[(rule["subsystem"], rule["number"])]
        if rule["real"]:
            assert record["text_template"] == rule["template"]
            assert record["real"] is True
        assert all(record[field] for field in ("cause", "effect", "recovery"))


def test_unavailable_source_retains_existing_pack(tmp_path, capsys):
    assert fetcher.load_chapter(68, tmp_path, offline=True, refresh=False) is None
    assert "no cache" in capsys.readouterr().err
    existing = [{"id": "opmsg:DEMO:1", "subsystem": "DEMO", "number": 1, "synthetic": True}]
    assert fetcher.merge(existing, [[]], [], 150) == existing

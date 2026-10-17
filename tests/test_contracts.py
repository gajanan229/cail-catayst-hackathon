import json
from pathlib import Path

from pydantic import TypeAdapter

from baton.schemas.cards import Card
from baton.schemas.common import CONTRACT_VERSION
from baton.schemas.ws import WS_EVENT_TYPES, WsEvent

CONTRACTS = Path(__file__).resolve().parent.parent / "contracts"


def test_version_file_matches_code():
    assert (CONTRACTS / "VERSION").read_text().strip() == CONTRACT_VERSION


def test_every_ws_event_type_has_a_valid_example():
    adapter = TypeAdapter(WsEvent)
    seen = set()
    for f in (CONTRACTS / "examples" / "ws").glob("*.json"):
        env = adapter.validate_python(json.loads(f.read_text(encoding="utf-8")))
        seen.add(env.type)
    assert seen == set(WS_EVENT_TYPES)


def test_card_examples_validate():
    adapter = TypeAdapter(Card)
    files = list((CONTRACTS / "examples" / "cards").glob("*.json"))
    assert len(files) >= 12
    for f in files:
        adapter.validate_python(json.loads(f.read_text(encoding="utf-8")))

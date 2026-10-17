"""Generate contracts/: openapi.json, ws-events.schema.json, cards.schema.json, examples/, VERSION.

Run: make contracts   (or: python scripts/gen_contracts.py)
Every example is validated against its model before it is written.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from pydantic import TypeAdapter  # noqa: E402

from baton.app import create_app  # noqa: E402
from baton.schemas import examples as X  # noqa: E402
from baton.schemas.cards import Card  # noqa: E402
from baton.schemas.common import CONTRACT_VERSION  # noqa: E402
from baton.schemas.ws import WS_EVENT_TYPES, WsClientMessage, WsEvent  # noqa: E402

OUT = ROOT / "contracts"


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / "VERSION").write_text(CONTRACT_VERSION + "\n", encoding="utf-8")

    app = create_app(start_runtime=False)
    dump(OUT / "openapi.json", app.openapi())

    server = TypeAdapter(WsEvent).json_schema()
    client = TypeAdapter(WsClientMessage).json_schema()
    defs = {**server.pop("$defs", {}), **client.pop("$defs", {})}
    ws_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Baton realtime contract",
        "version": CONTRACT_VERSION,
        "description": "Server -> client envelopes ({topic, type, seq, ts, sim_ts, payload}) on GET /api/ws. "
        "Client -> server messages: subscribe, unsubscribe, resume {since_seq}, ping.",
        "oneOf": [{"$ref": "#/$defs/ServerEvent"}, {"$ref": "#/$defs/ClientMessage"}],
        "event_topics": {k: v[0] for k, v in WS_EVENT_TYPES.items()},
        "$defs": {**defs, "ServerEvent": server, "ClientMessage": client},
    }
    dump(OUT / "ws-events.schema.json", ws_schema)
    dump(OUT / "cards.schema.json", TypeAdapter(Card).json_schema())

    ex_dir = OUT / "examples"
    if ex_dir.exists():
        shutil.rmtree(ex_dir)

    ws_adapter = TypeAdapter(WsEvent)
    ws = X.ws_examples()
    missing = set(WS_EVENT_TYPES) - {v.type for v in ws.values()}
    if missing:
        raise SystemExit(f"Missing WS examples for: {sorted(missing)}")
    for name, env in ws.items():
        data = env.model_dump(mode="json")
        ws_adapter.validate_python(data)
        dump(ex_dir / "ws" / f"{name}.json", data)

    card_adapter = TypeAdapter(Card)
    for name, fn in X.CARD_EXAMPLES.items():
        data = fn().model_dump(mode="json")
        card_adapter.validate_python(data)
        dump(ex_dir / "cards" / f"{name}.json", data)

    for name, obj in X.rest_examples().items():
        dump(ex_dir / "rest" / f"{name}.json", obj.model_dump(mode="json"))

    n = sum(1 for _ in ex_dir.rglob("*.json"))
    print(f"contracts {CONTRACT_VERSION}: openapi.json, ws-events.schema.json, cards.schema.json, {n} examples")


if __name__ == "__main__":
    main()

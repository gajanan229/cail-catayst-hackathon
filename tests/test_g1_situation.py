"""G1: S1 runs; a situation arrives over the WebSocket within 2 s of the fault."""
import json
import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BATON_VAR", str(tmp_path))
    monkeypatch.setenv("BATON_DB", str(tmp_path / "baton.db"))
    monkeypatch.setenv("BATON_EMBEDDINGS", "none")
    from baton.app import create_app
    with TestClient(create_app()) as c:
        yield c


def test_situation_within_two_seconds_of_cpu_halt(client):
    r = client.post("/api/sim/start", json={"scenario": "S1", "profile": "demo", "actor": "u_priya"})
    assert r.status_code == 200, r.text
    with client.websocket_connect("/api/ws") as ws:
        ws.send_text(json.dumps({"op": "subscribe", "topics": ["situations", "health"]}))
        # wait for a health snapshot so the sim is ticking
        while json.loads(ws.receive_text())["type"] != "health.snapshot":
            pass
        t0 = time.monotonic()
        r = client.post("/api/sim/inject", json={"fault": "cpu_halt", "params": {"cpu": 3}, "actor": "u_priya"})
        assert r.status_code == 200, r.text
        while True:
            env = json.loads(ws.receive_text())
            if env["type"] == "situation.upsert":
                break
        elapsed = time.monotonic() - t0
        assert elapsed < 2.0, elapsed
        sit = env["payload"]
        assert sit["template"] == "cpu_loss_cascade"
        assert sit["title"] == "CPU 3 down; ATM latency rising"
        assert sit["severity"] == 5
    incidents = client.get("/api/incidents").json()["incidents"]
    assert incidents and incidents[0]["display_id"] == "INC-0001"

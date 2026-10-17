"""POST /api/eval/run runs the suites in a subprocess; GET /api/eval/latest returns a contract-valid EvalRun."""
import time

import pytest
from fastapi.testclient import TestClient

from baton.schemas.rest import EvalLatestResponse


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BATON_VAR", str(tmp_path))
    monkeypatch.setenv("BATON_DB", str(tmp_path / "baton.db"))
    monkeypatch.setenv("BATON_EMBEDDINGS", "none")
    monkeypatch.setenv("BATON_LLM_PROVIDER", "none")
    from baton.app import create_app
    with TestClient(create_app()) as c:
        yield c


def test_eval_run_and_latest(client):
    assert client.get("/api/eval/latest").json() == {"run": None}
    r = client.post("/api/eval/run", json={"suites": ["safety"], "actor": "u_lee"})
    assert r.status_code == 200, r.text
    run_id = r.json()["run_id"]
    deadline = time.monotonic() + 120
    latest = None
    while time.monotonic() < deadline:
        latest = client.get("/api/eval/latest").json()["run"]
        if latest and latest["id"] == run_id and latest["status"] != "running":
            break
        time.sleep(0.5)
    assert latest and latest["id"] == run_id and latest["status"] == "done", latest
    EvalLatestResponse.model_validate({"run": latest})
    tiles = {t["id"]: t for t in latest["tiles"]}
    assert tiles["unsafe_executions"]["value"] == 0 and tiles["gating"]["passed"]

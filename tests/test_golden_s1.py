"""Golden path, headless (MVP spec §18): S1 test profile with BATON_LLM_PROVIDER=none, approvals driven
through the REST API as Priya and Sam. Asserts: situation opened; top hypothesis cpu_capacity_loss ≥ 0.85;
options include both actions; recovery within 240 sim-seconds; two claims drafted; promotion candidate for
tmfcom.status_audittrail; audit chain valid. Every WebSocket envelope must match the contract."""
from __future__ import annotations

import asyncio
import os
import time
from urllib.parse import quote

import httpx
import pytest
from pydantic import TypeAdapter

from baton.app import create_app
from baton.core.timeutil import parse_sim
from baton.schemas.ws import WsEvent
from helpers import runtime

WS = TypeAdapter(WsEvent)


async def until(fn, timeout=60.0, step=0.05, what="condition"):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        v = await fn()
        if v:
            return v
        await asyncio.sleep(step)
    raise AssertionError(f"timed out waiting for {what}")


@pytest.mark.asyncio
async def test_golden_s1(tmp_path):
    await run_golden(tmp_path, time_scale=8.0)


@pytest.mark.asyncio
@pytest.mark.skipif(os.environ.get("BATON_LIVE_MODELS") != "1" or not os.environ.get("NVIDIA_API_KEY"),
                    reason="set BATON_LIVE_MODELS=1 (and NVIDIA_API_KEY) to run with Nemotron")
async def test_golden_s1_models_on(tmp_path):
    """Same acceptance checks with Nemotron 120B behind the gateway. Slower sim so model calls fit in sim time;
    with BATON_REPLAY=record it also fills data/replay/."""
    mode = os.environ.get("BATON_REPLAY", "off")
    sources = await run_golden(tmp_path, time_scale=2.0, llm_provider="nemotron", replay=mode, step_timeout=240.0)
    # at least some model nodes must have produced real output (not only fallbacks)
    assert any(s not in (None, "fallback") for s in sources), sources


async def run_golden(tmp_path, step_timeout: float = 60.0, **overrides) -> list:
    async with runtime(tmp_path, **overrides) as rt:
        bad, types = [], {}

        def check(env):
            types[env["type"]] = types.get(env["type"], 0) + 1
            try:
                WS.validate_python(env)
            except Exception as e:
                bad.append((env["type"], str(e)[:300]))

        rt.hub.add_listener(check)
        app = create_app(start_runtime=False)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as api:
            r = await api.post("/api/sim/start", json={"scenario": "S1", "profile": "test", "actor": "u_priya"})
            assert r.status_code == 200, r.text

            # A3: situation and incident
            async def incident():
                incs = (await api.get("/api/incidents")).json()["incidents"]
                return incs[0] if incs and incs[0].get("thread_id") else None
            inc = await until(incident, step_timeout * 1.00, what="incident")
            sits = (await api.get("/api/situations")).json()["situations"]
            assert sits[0]["template"] == "cpu_loss_cascade" and sits[0]["incident_id"] == inc["id"]
            assert inc["display_id"] == "INC-0001"
            thread = inc["thread_id"]

            # A4: two auto checks, third waits for approval
            async def tmf_approval():
                aps = (await api.get("/api/approvals", params={"status": "pending"})).json()["approvals"]
                return next((a for a in aps if a["rendered"] == ["TMFCOM; STATUS AUDITTRAIL"]), None)
            tmf = await until(tmf_approval, step_timeout * 1.00, what="TMF approval")
            detail = (await api.get(f"/api/threads/{thread}")).json()
            cmd_cards = [c for c in detail["cards"] if c["type"] == "command"]
            auto = [c for c in cmd_cards if c["status"] == "done" and c["body"]["policy"]["effect"] == "allow_auto"]
            assert {c["body"]["catalog_id"] for c in auto} >= {"pathcom.status_server", "meas.cpu_busy"}
            hyp = next(c for c in detail["cards"] if c["type"] == "hypotheses")
            assert hyp["body"]["hypotheses"][0]["id"] == "cpu_capacity_loss"
            assert hyp["body"]["hypotheses"][0]["p"] >= 0.9

            # A5: question in the incident thread
            r = await api.post(f"/api/threads/{thread}/messages", json={"text": "ATM withdrawals are slow. What's going on?",
                                                                        "actor": "u_priya"})
            assert r.status_code == 200, r.text

            # A6: Priya approves the TMF check
            r = await api.post(f"/api/approvals/{tmf['id']}/decide", json={"decision": "approve", "actor": "u_priya"})
            assert r.status_code == 200, r.text
            assert r.json()["approval"]["status"] == "approved"

            # A8: decision card
            async def decision():
                d = (await api.get(f"/api/threads/{thread}")).json()
                dc = next((c for c in d["cards"] if c["type"] == "decision" and c["body"].get("approval_id")), None)
                return dc
            dc = await until(decision, step_timeout * 1.00, what="decision card")
            opts = {o["id"]: o for o in dc["body"]["options"]}
            steps = {s["catalog_id"] for o in opts.values() for s in o.get("steps", [])}
            assert {"tacl.suspend_process", "pathcom.alter_numstatic"} <= steps
            assert opts["opt_a"]["steps"][0]["rendered"] == "SUSPEND $STMT1"
            assert opts["opt_b"]["steps"][0]["rendered"] == "PATHCOM $PM1; ALTER SERVER ATM-AUTH, NUMSTATIC 28"
            assert opts["opt_ab"]["recommended"] and opts["opt_c"]["blocked"] and "opt_none" in opts
            # P1 what-if: predictions on the options; A+B ends far below doing nothing
            p95 = lambda o: opts[o]["prediction"]["summary"]["svc.atm.p95_ms"]["to"]
            assert p95("opt_ab") < 300 < 1000 < p95("opt_none")
            assert opts["opt_c"].get("prediction") is None
            d = (await api.get(f"/api/threads/{thread}")).json()
            hyp = next(c for c in d["cards"] if c["type"] == "hypotheses")
            assert hyp["body"]["hypotheses"][0]["p"] >= 0.85 and hyp["body"]["stop_rule"]["met"]
            assert any(c["type"] == "expert" and c["body"]["id"] == "PB-CPU-LOSS-PEAK" for c in d["cards"])
            async def answer():
                d = (await api.get(f"/api/threads/{thread}")).json()
                return next((c for c in d["cards"] if c["type"] == "text" and c["incident_id"] == inc["id"]
                             and c["body"].get("link")), None)
            ans = await until(answer, step_timeout * 0.5, what="A5 answer card")
            assert ans["citations"], ans

            # A9: Priya approves A+B; Sam approves B
            r = await api.post(f"/api/approvals/{dc['body']['approval_id']}/decide",
                               json={"decision": "approve", "option_ids": ["opt_ab"], "actor": "u_priya"})
            assert r.status_code == 200, r.text
            first_action_sim = parse_sim(rt.sim.state_dict()["sim_ts"])

            async def b_partial():
                aps = (await api.get("/api/approvals", params={"status": "partially_approved"})).json()["approvals"]
                return next((a for a in aps if "NUMSTATIC 28" in a["rendered"][0]), None)
            b = await until(b_partial, step_timeout * 0.50, what="B partially approved")
            assert b["progress_text"] == "1 of 2: needs Senior or Expert"
            r = await api.post(f"/api/approvals/{b['id']}/decide", json={"decision": "approve", "actor": "u_priya"})
            assert r.status_code == 403   # same person twice
            r = await api.post(f"/api/approvals/{b['id']}/decide", json={"decision": "approve", "actor": "u_sam"})
            assert r.status_code == 200, r.text

            # A10: verification and resolution
            async def resolved():
                i = (await api.get(f"/api/incidents/{inc['id']}")).json()
                return i if i["status"] == "resolved" else None
            done = await until(resolved, step_timeout * 1.50, what="resolved incident")
            recovered_at = parse_sim(done["resolved_at"])
            assert (recovered_at - first_action_sim).total_seconds() <= 240
            assert [u["label"] for u in done["undo_stack"]][:2] == ["ALTER ... NUMSTATIC 20", "ACTIVATE $STMT1"]

            # A11: postmortem, two claims, promotion candidate
            async def learned():
                cl = (await api.get("/api/claims", params={"status": "pending_review"})).json()["claims"]
                runtime_claims = [c for c in cl if c["provenance"]["source_type"] == "incident"]
                return runtime_claims if len(runtime_claims) == 2 else None
            claims = await until(learned, step_timeout * 0.50, what="two drafted claims")
            pm = (await api.get(f"/api/incidents/{inc['id']}/postmortem")).json()
            assert pm["summary"] and pm["follow_ups"]
            ledger = (await api.get("/api/ledger")).json()["entries"]
            tmf_entry = next(e for e in ledger if e["key"] == "tmfcom.status_audittrail|any|operator")
            assert tmf_entry["eligible_for"] == "L2"

            # A12: Dave confirms claim 1, edits claim 2's scope and confirms; searchable immediately
            r = await api.post(f"/api/claims/{claims[0]['id']}/review", json={"decision": "confirm", "actor": "u_dave"})
            assert r.status_code == 200, r.text
            r = await api.post(f"/api/claims/{claims[1]['id']}/review",
                               json={"decision": "edit_confirm", "edits": {"scope": {"site": "TORBANK", "calendar": ["black_friday"]}},
                                     "actor": "u_dave"})
            assert r.status_code == 200 and r.json()["status"] == "verified"
            hits = (await api.get("/api/kb/search", params={"q": claims[0]["statement"][:60]})).json()["results"]
            assert any(h["id"] == f"claim:{claims[0]['id']}" for h in hits)

            # A13: Dave grants L2
            r = await api.post(f"/api/ledger/{quote('tmfcom.status_audittrail|any|operator', safe='')}/grant",
                               json={"level": "L2", "reason": "20 clean runs on peak days", "actor": "u_dave"})
            assert r.status_code == 200 and r.json()["level"] == "L2"

            # A14: audit chain
            v = (await api.get("/api/audit/verify")).json()
            assert v["valid"] and v["entries"] > 10

        await asyncio.sleep(0.1)
        sources = [r["cache_hit"] for r in rt.store.query("SELECT cache_hit FROM model_calls")]
        assert not bad, bad[:3]
        for t in ("card.upsert", "node.started", "node.ended", "approval.upsert", "interrupt.raised", "terminal.ghost",
                  "terminal.output", "ledger.promotion_candidate", "claim.upsert", "run.completed"):
            assert t in types, (t, sorted(types))
        return sources

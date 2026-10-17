"""Night shift, "four alarms, one cause" (S4), headless with models off.

At 01:40 the new nightly batch $RECN1 starts and loops above the servers' priority on CPU 3. Asserts: CPU, latency,
restart and disk alarms land in ONE situation; Baton names $RECN1 on CPU 3 as the cause (≥ 0.85); the operator checks
$DATA03 with DSAP and approves the suspend; the incident resolves; the overnight summary lists the four alarms and the
cause; two lessons are drafted. Every WebSocket envelope must match the contract."""
from __future__ import annotations

import asyncio

import httpx
import pytest
from pydantic import TypeAdapter

from baton.app import create_app
from baton.schemas.ws import WsEvent
from helpers import runtime
from test_golden_s1 import until

WS = TypeAdapter(WsEvent)


@pytest.mark.asyncio
async def test_night_four_alarms_one_cause(tmp_path):
    async with runtime(tmp_path, time_scale=8.0) as rt:
        bad = []

        def check(env):
            try:
                WS.validate_python(env)
            except Exception as e:
                bad.append((env["type"], str(e)[:300]))

        rt.hub.add_listener(check)
        app = create_app(start_runtime=False)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as api:
            r = await api.post("/api/sim/start", json={"scenario": "S4", "profile": "test", "actor": "u_priya"})
            assert r.status_code == 200, r.text

            # The Guard: one situation and incident, opened by the saturated CPU plus a restart or the disk
            async def incident():
                incs = (await api.get("/api/incidents")).json()["incidents"]
                return incs[0] if incs and incs[0].get("thread_id") else None
            inc = await until(incident, 60, what="incident")
            thread = inc["thread_id"]
            sits = (await api.get("/api/situations")).json()["situations"]
            assert len(sits) == 1 and sits[0]["template"] == "runaway_batch_cascade"
            assert sits[0]["origin"]["component_id"] == "cpu:3"

            # "Play the night": nobody touches anything until 01:54, when all four alarms have fired
            async def morning():
                return rt.sim.state_dict()["sim_ts"] >= "2026-11-18T01:54:00"
            await until(morning, 60, what="01:54")
            sit = (await api.get("/api/situations")).json()["situations"][0]
            assert sit["title"] == "CPU 3 saturated: 4 alarms, one cause", sit["title"]

            # status_cpu is L1: Baton pauses for it; Priya approves
            async def cpu_check():
                aps = (await api.get("/api/approvals", params={"status": "pending"})).json()["approvals"]
                return next((a for a in aps if a["rendered"] and "CPU 3" in a["rendered"][0]), None)
            ap = await until(cpu_check, 60, what="status_cpu approval")
            r = await api.post(f"/api/approvals/{ap['id']}/decide", json={"decision": "approve", "actor": "u_priya"})
            assert r.status_code == 200, r.text

            # Baton asks to check the disk (DSAP is L1); the operator approves it and sees the growth
            async def dsap():
                aps = (await api.get("/api/approvals", params={"status": "pending"})).json()["approvals"]
                return next((a for a in aps if a["rendered"] == ["DSAP $DATA03, SHORT"]), None)
            disk_ap = await until(dsap, 60, what="DSAP approval")
            r = await api.post(f"/api/approvals/{disk_ap['id']}/decide", json={"decision": "approve", "actor": "u_priya"})
            assert r.status_code == 200, r.text

            async def disk_facts():
                execs = rt.store.all("executions")
                return next((e for e in execs if e.get("catalog_id") == "dsap.disk_space" and e["status"] == "done"), None)
            ex = await until(disk_facts, 30, what="DSAP execution")
            assert ex["facts"]["volume"] == "$DATA03" and ex["facts"]["growth_pct_per_min"] > 0.2

            # Mentor: the decision names the one cause
            async def decision():
                d = (await api.get(f"/api/threads/{thread}")).json()
                return next((c for c in d["cards"] if c["type"] == "decision" and c["body"].get("approval_id")), None)
            dc = await until(decision, 60, what="decision card")
            d = (await api.get(f"/api/threads/{thread}")).json()
            hyp = next(c for c in d["cards"] if c["type"] == "hypotheses")["body"]
            assert hyp["hypotheses"][0]["id"] == "runaway_process" and hyp["hypotheses"][0]["p"] >= 0.85, hyp["hypotheses"][:2]
            assert "$RECN1" in hyp["hypotheses"][0]["label"] and "CPU 3" in hyp["hypotheses"][0]["label"]
            assert any(c["type"] == "expert" and c["body"]["id"] == "PB-RUNAWAY-BATCH" for c in d["cards"])
            opts = {o["id"]: o for o in dc["body"]["options"]}
            suspend = next(o for o in opts.values() if o.get("steps") and o["steps"][0]["rendered"] == "SUSPEND $RECN1")
            assert suspend["recommended"]

            # Priya approves the suspend; verification resolves the incident
            r = await api.post(f"/api/approvals/{dc['body']['approval_id']}/decide",
                               json={"decision": "approve", "option_ids": [suspend["id"]], "actor": "u_priya"})
            assert r.status_code == 200, r.text

            async def resolved():
                i = (await api.get(f"/api/incidents/{inc['id']}")).json()
                return i if i["status"] == "resolved" else None
            done = await until(resolved, 90, what="resolved incident")
            assert [u["label"] for u in done["undo_stack"]][:1] == ["ACTIVATE $RECN1"]

            # Overnight summary: four alarms, one cause, the disk growth
            r = await api.post(f"/api/threads/{thread}/messages", json={"text": "Give me the shift summary", "actor": "u_priya"})
            assert r.status_code == 200, r.text

            async def summary():
                d = (await api.get(f"/api/threads/{thread}")).json()
                return next((c for c in d["cards"] if c["type"] == "text" and c["title"].startswith("Overnight summary")), None)
            card = await until(summary, 30, what="overnight summary")
            md = card["body"]["markdown"]
            assert "since 01:30: 4 alarms, one cause" in md, md
            for needle in ("CPU 3 at 100%", "p95", "2 server processes restarted on CPU 3", "$DATA03 8",
                           "One cause: Runaway batch $RECN1 on CPU 3", "grew from 72% at 01:30 to 8"):
                assert needle in md, (needle, md)

            # Mentor: how was this solved before? The answer cites a past incident
            r = await api.post(f"/api/threads/{thread}/messages", json={"text": "How was this solved last time?", "actor": "u_priya"})
            assert r.status_code == 200, r.text

            async def answer():
                d = (await api.get(f"/api/threads/{thread}")).json()
                return next((c for c in d["cards"] if c["type"] == "text" and any(
                    x["id"].startswith("incident:INC-2026-") for x in c.get("citations") or [])), None)
            ans = await until(answer, 30, what="answer citing a past incident")

            # Learn: two lessons drafted from this incident
            async def learned():
                cl = (await api.get("/api/claims", params={"status": "pending_review"})).json()["claims"]
                got = [c for c in cl if c["provenance"]["source_type"] == "incident"]
                return got if len(got) == 2 else None
            claims = await until(learned, 30, what="two drafted claims")
            assert any("$RECN1" in c["statement"] for c in claims)

            v = (await api.get("/api/audit/verify")).json()
            assert v["valid"]
        await asyncio.sleep(0.1)
        assert not bad, bad[:3]

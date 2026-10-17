"""Resume test (MVP spec §18): kill the server while an approval is pending; restart; approve; the thread completes."""
import asyncio

import pytest

from baton.schemas.rest import ApprovalDecideRequest
from helpers import runtime


async def wait(fn, timeout=20.0):
    for _ in range(int(timeout / 0.05)):
        v = fn()
        if v:
            return v
        await asyncio.sleep(0.05)
    raise AssertionError("timed out")


@pytest.mark.asyncio
async def test_resume_after_restart(tmp_path):
    # first process: Flow B request; STATS SERVER needs approval (L1)
    async with runtime(tmp_path, autostart="S1:demo") as rt:
        t = rt.agents.create_thread("auto", None, "u_priya")
        await rt.agents.post_message(t["id"], "Is ATM auth keeping up?", "u_priya")
        approval = await wait(lambda: next((a for a in rt.approvals.list("pending") if a["thread_id"] == t["id"]), None))
        await wait(lambda: rt.agents.get_thread(t["id"])["status"] == "waiting")
        thread_id, approval_id = t["id"], approval["id"]
    # "kill": the runtime is stopped; a new one starts on the same database and checkpoints
    async with runtime(tmp_path, autostart="S1:demo") as rt2:
        assert rt2.approvals.get(approval_id)["status"] == "pending"
        out = await rt2.decide_approval(approval_id, ApprovalDecideRequest(decision="approve", actor="u_priya"))
        assert out["resumed"]

        def finished():
            th = rt2.agents.get_thread(thread_id)
            cards = rt2.agents.cards.for_thread(thread_id)
            stats = next((c for c in cards if c["type"] == "command" and c["body"]["catalog_id"] == "pathcom.stats_server"), None)
            return th["status"] == "idle" and stats and stats["status"] == "done" and stats
        stats = await wait(finished)
        assert stats["body"]["execution"]["facts"]["server_class"] == "ATM-AUTH"
        assert any(c["type"] == "text" and c["title"] == "What this shows" for c in rt2.agents.cards.for_thread(thread_id))

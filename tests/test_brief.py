"""Brief graph (P1): facts first, cited narration, numeric consistency check."""
import asyncio

import pytest

from baton.agents.graphs.brief import fallback_brief, gather_facts, numbers_ok
from helpers import advance, runtime


def _briefs(rt, thread_id):
    return [c for c in rt.agents.cards.for_thread(thread_id) if c["title"].startswith("Shift brief")]


async def _brief(rt, thread_id):
    before = len(_briefs(rt, thread_id))
    await rt.agents.post_message(thread_id, "How are we doing?", "u_priya")
    for _ in range(100):
        cards = _briefs(rt, thread_id)
        if len(cards) > before:
            return cards[-1]
        await asyncio.sleep(0.05)
    raise AssertionError("no brief card")


@pytest.mark.asyncio
async def test_brief_amber_then_red(tmp_path):
    async with runtime(tmp_path) as rt:
        await rt.sim_start("S1", "demo", None, None, "u_priya")
        rt.sim.status.paused = True
        advance(rt, 30)
        t = rt.agents.create_thread("auto", None, "u_priya")
        c = await _brief(rt, t["id"])
        assert c["title"].endswith("Amber"), c["title"]
        assert "N-1" in c["body"]["markdown"] and any(x["id"] == "fact:n1" for x in c["citations"])
        rt.sim_inject("cpu_halt", {"cpu": 3}, "u_priya")
        advance(rt, 30)
        c2 = await _brief(rt, t["id"])
        assert c2["title"].endswith("Red"), c2["title"]
        assert "INC-0001" in c2["body"]["markdown"]


def test_numeric_check():
    facts = [{"id": "fact:svc:atm", "text": "ATM p95 is 846 ms", "numbers": [846.0]}]
    assert numbers_ok("ATM latency is 846 ms", facts)
    assert numbers_ok("ATM latency is about 850 ms", facts)        # within 2%
    assert not numbers_ok("ATM latency is 1200 ms", facts)
    b = fallback_brief(facts, "green")
    assert b["level"] == "green" and b["headline"] == "All clear"

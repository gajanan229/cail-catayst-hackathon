"""Every envelope the runtime publishes during S1 validates against the WebSocket contract."""
import asyncio

import pytest
from pydantic import TypeAdapter

from baton.schemas.ws import WsEvent
from helpers import advance, runtime

ADAPTER = TypeAdapter(WsEvent)


@pytest.mark.asyncio
async def test_s1_envelopes_match_contract(tmp_path):
    async with runtime(tmp_path) as rt:
        seen, bad = {}, []

        def check(env):
            seen[env["type"]] = seen.get(env["type"], 0) + 1
            try:
                ADAPTER.validate_python(env)
            except Exception as e:  # collect, assert later
                bad.append((env["type"], str(e)[:400]))

        rt.hub.add_listener(check)
        await rt.sim_start("S1", "test", None, None, "u_priya")
        rt.sim.status.paused = True
        advance(rt, 30)
        rt._publish_periodic()
        advance(rt, 400)           # through the 11:52:00 scheduled halt
        rt._publish_periodic()
        advance(rt, 60)
        rt._publish_periodic()
        await asyncio.sleep(0.2)
        assert not bad, bad[:3]
        for t in ("telemetry.tick", "health.snapshot", "situation.upsert", "incident.upsert", "timeline.append",
                  "episode.upsert", "events.rate", "sim.state", "audit.append"):
            assert t in seen, (t, seen)

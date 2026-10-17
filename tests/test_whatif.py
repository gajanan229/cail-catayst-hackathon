"""What-if (P1): predictions on a fork match the §6.2 direction of travel and never touch the live simulator."""
import pytest

from helpers import advance, runtime


@pytest.mark.asyncio
async def test_whatif_predictions_after_cpu_halt(tmp_path):
    async with runtime(tmp_path) as rt:
        await rt.sim_start("S1", "demo", None, None, "u_priya")
        rt.sim.status.paused = True
        advance(rt, 420)
        rt.sim_inject("cpu_halt", {"cpu": 3}, "u_priya")
        advance(rt, 60)
        live_tick = rt.sim.model.tick
        live_numstatic = rt.sim.model.classes["ATM-AUTH"].numstatic
        nothing = await rt.whatif("none", [])
        both = await rt.whatif("none", [{"catalog_id": "tacl.suspend_process", "params": {"process": "$STMT1"}},
                                        {"catalog_id": "pathcom.alter_numstatic", "params": {"server_class": "ATM-AUTH", "n": 28}}])
        # the live simulator is untouched
        assert rt.sim.model.tick == live_tick and rt.sim.model.classes["ATM-AUTH"].numstatic == live_numstatic
        assert rt.sim.model.processes["$STMT1"].state == "RUNNING"
        p_none = nothing["summary"]["svc.atm.p95_ms"]["to"]
        p_both = both["summary"]["svc.atm.p95_ms"]["to"]
        assert p_none > 1200            # do nothing + 10 min: p95 above 1,200 ms (§6.2)
        assert p_both < 260             # both actions: back in band
        assert both["summary"]["svc.atm.timeout_pct"]["to"] < 0.2
        assert len(both["series"]["svc.atm.p95_ms"]) == 61
        with pytest.raises(Exception):
            await rt.whatif("none", [{"catalog_id": "sys.reload_cpu", "params": {"cpu": 3}}])

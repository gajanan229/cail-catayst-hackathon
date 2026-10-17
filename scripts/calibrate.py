"""Print simulator values at the §6.2 calibration moments (S1). Dev tool: python scripts/calibrate.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
import yaml  # noqa: E402

from baton.health.n1 import compute_n1  # noqa: E402
from baton.sim.model import SimModel  # noqa: E402

site = yaml.safe_load((ROOT / "data/site/torbank.yaml").read_text(encoding="utf-8"))
sc1 = yaml.safe_load((ROOT / "data/scenarios/S1.yaml").read_text(encoding="utf-8"))


def show(m, label):
    a = m.classes["ATM-AUTH"]
    p = m.classes["POS-AUTH"]
    n1 = compute_n1(m)
    print(f"{label:28s} {m.now:%H:%M:%S} cpu={[round(b) for b in m.cpu_busy]} "
          f"ATM run={a.running(m.tick)} q={a.queued:.0f} p95={a.p95_ms:.0f} to={a.timeout_pct:.1f}% rho={a.rho:.3f} "
          f"POS run={p.running(m.tick)} p95={p.p95_ms:.0f} tmf={m.tmf.fill_pct:.1f} | {n1['text']}")


def run(m, secs):
    for _ in range(secs):
        m.step()


def scenario(actions=True, suspend_at=240, alter_at=280):
    m = SimModel(site, sc1, 42)
    run(m, 20); show(m, "11:45 healthy")
    run(m, 400); show(m, "11:52 before halt")
    m.halt_cpu(3)
    run(m, 60); show(m, "halt+60")
    if not actions:
        run(m, 540); show(m, "do nothing +10min")
        return
    run(m, suspend_at - 60)
    b5 = m.cpu_busy[5]
    m.processes["$STMT1"].state = "SUSPENDED"
    run(m, 30); show(m, f"suspend+30 (cpu5 was {b5:.0f})")
    run(m, alter_at - suspend_at - 30)
    r = m.set_numstatic("ATM-AUTH", 28); print("  started on", r["started_on"])
    run(m, 60); show(m, "numstatic28+60")
    run(m, 120); show(m, "numstatic28+180")


scenario()
scenario(actions=False)

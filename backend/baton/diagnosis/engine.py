"""Diagnosis (MVP spec §12): observations → log-odds scores → softmax; batch next-best checks;
stop rule; options from mitigations, playbooks and claims; verification criteria."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import yaml

SERVICE_OF_CLASS = {"ATM-AUTH": "atm", "POS-AUTH": "pos", "BAL-INQ": "bal", "CARD-MGMT": "card"}


class Diagnosis:
    def __init__(self, rules_dir: Path):
        fm = yaml.safe_load((rules_dir / "failure_modes.yaml").read_text(encoding="utf-8"))
        ob = yaml.safe_load((rules_dir / "observations.yaml").read_text(encoding="utf-8"))
        self.modes = {m["id"]: m for m in fm["modes"]}
        self.order = [m["id"] for m in fm["modes"]]
        self.observations = ob["observations"]
        self.stop = ob.get("stop_rule", {"top": 0.85, "margin": 0.30, "max_rounds": 3})
        self.budgets = ob.get("budgets", {"checks_per_incident": 6, "nodes_per_turn": 20})

    # ------------------------------------------------------------ scoring

    def score(self, obs: dict[str, dict], ctx: dict | None = None, previous: dict[str, float] | None = None) -> list[dict]:
        """obs: observation id → evidence {evidence_id, label}. Returns hypotheses sorted by probability."""
        ctx = ctx or {}
        logits = {}
        for mid in self.order:
            s = math.log(self.modes[mid]["prior"])
            for oid in obs:
                s += float(self.observations.get(oid, {}).get("weights", {}).get(mid, 0.0))
            logits[mid] = s
        mx = max(logits.values())
        exps = {k: math.exp(v - mx) for k, v in logits.items()}
        z = sum(exps.values())
        out = []
        for mid in self.order:
            p = exps[mid] / z
            fors, against = [], []
            for oid, ev in obs.items():
                w = float(self.observations.get(oid, {}).get("weights", {}).get(mid, 0.0))
                ref = {"evidence_id": ev["evidence_id"], "label": ev["label"]}
                if w > 0:
                    fors.append((w, ref))
                elif w < 0:
                    against.append((w, ref))
            fors.sort(key=lambda x: -x[0])
            against.sort(key=lambda x: x[0])
            prev = (previous or {}).get(mid)
            out.append({
                "id": mid, "label": self.label(mid, ctx), "p": round(p, 4), "logit": round(logits[mid], 4),
                "delta": round(p - prev, 4) if prev is not None else 0.0,
                "for": [r for _, r in fors][:4], "against": [r for _, r in against][:4],
                "would_change_mind": self.modes[mid].get("would_change_mind"),
            })
        out.sort(key=lambda h: -h["p"])
        return out

    def label(self, mode_id: str, ctx: dict) -> str:
        tpl = self.modes[mode_id].get("label") or self.modes[mode_id]["name"]
        try:
            return tpl.format(**{k: v for k, v in ctx.items() if v is not None})
        except (KeyError, IndexError):
            return self.modes[mode_id]["name"]

    def stop_rule(self, hyps: list[dict], rounds: int) -> dict:
        top = hyps[0]["p"] if hyps else 0.0
        second = hyps[1]["p"] if len(hyps) > 1 else 0.0
        margin = round(top - second, 4)
        met = top >= self.stop["top"] and margin >= self.stop["margin"]
        reason = (f"Top {top:.2f} ≥ {self.stop['top']} and margin {margin:.2f} ≥ {self.stop['margin']}" if met else
                  f"Top {top:.2f}, margin {margin:.2f}: need ≥ {self.stop['top']} and ≥ {self.stop['margin']}")
        exhausted = not met and rounds >= self.stop["max_rounds"]
        return {"met": met, "top": round(top, 4), "margin": margin, "reason": reason, "exhausted": exhausted}

    # ------------------------------------------------------------ next-best checks

    def check_value(self, catalog_id: str, modes: list[str]) -> float:
        total = 0.0
        for oid, o in self.observations.items():
            if catalog_id in (o.get("produced_by") or []):
                for m in modes:
                    total += abs(float(o.get("weights", {}).get(m, 0.0)))
        return total

    def next_checks(self, hyps: list[dict], already: set[str], peak_day: bool, auto_runnable, k: int = 3) -> list[dict]:
        top2 = [h["id"] for h in hyps[:2]]
        cands: dict[str, dict] = {}
        for mid in top2:
            for cid in self.modes[mid].get("discriminating_checks", []):
                if cid in already or cid in cands:
                    continue
                value = self.check_value(cid, top2)
                if value <= 0:
                    continue
                cost = 1 if auto_runnable(cid) else 2
                cands[cid] = {"catalog_id": cid, "value": value, "cost": cost, "score": value / cost,
                              "reason": f"Discriminates {', '.join(top2)}", "hypothesis_id": mid}
        ranked = sorted(cands.values(), key=lambda c: (-c["score"], c["catalog_id"]))
        rule_outs = []
        if peak_day:
            for mid, m in self.modes.items():
                if m.get("rule_out_on_peak_days") and mid not in top2:
                    for cid in m.get("discriminating_checks", [])[:1]:
                        if cid not in already and cid not in cands:
                            value = self.check_value(cid, [mid])
                            cost = 1 if auto_runnable(cid) else 2
                            rule_outs.append({"catalog_id": cid, "value": value, "cost": cost, "score": value / cost,
                                              "reason": "Rule out on a peak day", "hypothesis_id": mid,
                                              "claim_id": m.get("rule_out_claim"), "rule_out": True})
        batch = ranked[: max(0, k - len(rule_outs[:1]))] + rule_outs[:1]
        if len(batch) < k:
            batch += [c for c in ranked if c not in batch][: k - len(batch)]
        return batch[:k]

    # ------------------------------------------------------------ options

    def mitigation(self, mode_id: str, option: str) -> dict | None:
        return next((m for m in self.modes[mode_id].get("mitigations", []) if m["option"] == option), None)

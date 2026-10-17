# Contracts changelog

Owned by Agent A. The only way contracts change after G0. Each entry: date, version, what changed, why, and whether it breaks Agent B.
Minor bump = additive; major bump = breaking (also listed under "Requests to B" in STATUS_A.md).

## 1.0.0 · 2026-10-17 · G0 freeze

- Initial contracts: `contracts/openapi.json` (REST §14), `contracts/ws-events.schema.json` (realtime §15),
  `contracts/cards.schema.json` (card library §13.4/§15.2), examples in `contracts/examples/{ws,cards,rest}/`.
- Additions beyond the MVP spec text (all additive, all optional for B to use):
  - Cards carry `seq` (order within a thread). Command cards add `params`, `internal`, `approval_progress`, `approvers`,
    `validation_errors`; `execution` adds `facts_table`, `summary`, `summary_source`.
  - Decision options add `status` and `approval_id`; Approval adds `card_id`, `policy` and `progress_text`.
  - `TraceStep` adds `step_id`; `TraceDetail` adds `inputs`, `output`.
  - `terminal.ghost` payload adds `label` (the line shown above ghost-typed text).
  - `N1Status` is `{safe, worst_lost_cpu, worst_survivor_cpu, worst_survivor_busy, threshold, text, per_cpu}`.
  - WebSocket client ops also accept `unsubscribe` and `ping` (server answers `{"op":"pong"}`).
- Breaking for B: n/a (first version).

## 1.1.0 · 2026-10-17 · additive, not breaking

- `POST /api/incidents/{id}/whatif` is implemented (P1). Body `{"actions": [{"catalog_id", "params"}]}`; use
  `incident_id = "none"` outside an incident. Returns `{"series": {"svc.atm.p95_ms": [["HH:MM:SS", v], ...],
  "svc.atm.timeout_pct": [...], "cpu.N.busy": [...] (three hottest survivors)}, "summary": {key: {"from", "to", "max"}},
  "horizon_s": 600}`. T3 actions are refused (403); invalid parameters return 422.
- Decision-card options now carry `prediction` (same shape as above) for every non-blocked option, including
  `opt_none`; blocked options keep `prediction: null`. The field existed in 1.0.0 and was always null before.
- Only `openapi.json` changed (route description). No type changes: `npm run gen:types` output is identical
  apart from the version string.
- Breaking for B: no.

## 1.2.0 · 2026-10-17 · additive, not breaking

- Scenario `S4` ("Night shift, four alarms one cause") accepted by `POST /api/sim/start`.
- Fault `runaway_batch` (`params: {"process": "$RECN1"}`) accepted by `POST /api/sim/inject`: the batch starts and loops
  above the servers' priority on its CPU and writes its log to its volume.
- New situation template `runaway_batch_cascade` (situation `template` is a free string; no type change). Its title is
  recomputed as alarms join: "CPU 3 saturated: 4 alarms, one cause"; the incident title follows it.
- Health snapshots now include one `type: "volume"` component per disk (`id: "vol:$DATA03"`, metrics `fill_pct`,
  `start_pct`, `alarm_pct`); the type already existed in 1.0.0. Telemetry adds `disk.<volume>.fill_pct` values.
- New signal kinds (free strings): `disk_fill_high`, `disk_fill_rising`, `process_restarts`.
- New catalog entry `dsap.disk_space` (T0, read-only): `DSAP $DATA03, SHORT`.
- Breaking for B: no. `npm run gen:types` adds `"S4"` and `"runaway_batch"` to the literal unions.

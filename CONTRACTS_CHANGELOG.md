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

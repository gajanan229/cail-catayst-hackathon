# Redesign coverage of the Baton MVP

The approved v3 direction replaces the original dark three-column layout. Colors, typography hierarchy and information placement follow the user's later design instruction. Functional scope still follows `BATON_MVP_SPEC.md`; contracts remain 1.0.0. No Engine-owned source or contract is modified.

## Where the P0 features live

| MVP feature | Redesigned location / behavior | Verification |
| --- | --- | --- |
| System, SIM clock/speed/pause, persona, read-only, incident, N-1 | Persistent top bar, incident link and N-1 evidence; Director retains full clock/scenario controls | Browser golden path, safety and route checks |
| Service health and expected ranges | Overview → Service health; ATM/POS rows, server/queue/timeout facts, selected-service chart, time-window controls, source drawer | Diagnostic browser test, real telemetry integration |
| CPU strip, N-1 analysis, TMF thresholds | Overview processor strip; Processors tab has per-component explanations and audit thresholds. N-1 risk opens the backend calculation, including worst survivor and per-CPU results | Diagnostic keyboard navigation and source drawer |
| Server class table | Servers tab, with canonical IDs, backend health, running/max, queued, average response and source inspection | Diagnostic browser test |
| Event river / situation collapse / quarantined text | Events tab or workbench Event stream; filterable episodes, live counts, source/manual links and incident counter | Mock scenario and diagnostic test |
| xterm, raw output, ghost typing and manual catalog commands | Persistent light command workbench; Expand provides the full area. It stays mounted while switching workbench tabs, preserving output and typing order | Terminal queue tests; manual-command browser test |
| Streamed Baton cards | Current unresolved check or latest response in the assistant pane; View all cards opens the complete ordered, actionable history | Golden path, question/answer and history browser tests |
| Full trace and per-step details | Assistant's collapsed Agent trace; Incident Room → Steps, scoped to the incident thread | Trace browser inspection, snapshot/event tests |
| Incident timeline and filters | Incident Room left column, also workbench Activity | Golden path |
| Ranked hypotheses and evidence | Incident Room → Diagnosis / Evidence; evidence includes read-only command results | Golden path switches through investigation tabs |
| Expert guidance and provenance | Incident Room → Playbook; relevant source in recovery preview; citations remain clickable | Playbook and cited-answer tests |
| Recovery options, blocked T3, effects, risks, undo, policy Why | Incident Room decision column; assistant Review plan & approvals leads there | Golden path, destructive-request refusal |
| Human approvals and parameter edits | Existing shared command, plan and decision controls retain exact command previews, live backend validation, reason codes and actor stamps | Preview/edit test, two-person golden path, mock governance unit tests |
| Partial approvals remain visible | Persistent progress above incident decisions, inline option progress and assistant progress | Priya → Sam golden path |
| Undo proposals and two-person undo approval | Incident Room undo stack; explicit policy-check dialog; pending undo approvals have their own confirmation/rejection controls | Undo proposal in mock golden path; two-person undo in live test |
| Recovery verification and action markers | Incident Room fixed chart strip and verification card; normal band comes from backend telemetry | Golden path and real backend verification |
| Postmortem | Incident Room → Postmortem; generated sections retain source links | Golden path opens the generated document after recovery |
| Knowledge review, edit, scoped calendar and rejection | Knowledge Studio review queue and editor; source and reviewer provenance retained | Golden claim confirmation/edit, browser route checks |
| Knowledge search and ranking debug | Knowledge Studio search tab; provenance, full item drawer and optional score table | Existing API-backed search, cited source test |
| Trust Ledger and promotions | All catalog entries, role matrix, counters, distinct approvers, reasoned grant/revoke drawer; T3 locked | Golden L2 promotion |
| Audit and chain verification | Audit table, filters and chain result; entry/hash opens raw payload, actor, policy/model provenance and both hashes | Golden verification and raw entry inspection |
| P0 Eval | Evaluation results, accuracy/safety tiles, expected vs actual table; synthetic fixture scores explicitly labeled | Route smoke; values come from backend endpoint |
| Director | Scenario/profile/seed, Start/Reset, three faults, clock, replay, read-only; Ctrl+Shift+D | Scenario golden path and retained control implementation |
| Offline mock mode / generated types | Recorded envelope/REST/card fixtures, interactive approval gates, SIM phases; generated REST/WS/card types unchanged | Schema validator, unit tests, mock acceptance |

All twelve card renderers remain available: Text, Situation, Command, Plan, Hypotheses, Evidence, Expert, Decision, Verification, Escalation, Postmortem and Claim review. The redesign reuses the existing governed action components rather than implementing a second approval path for those cards.

## Scope and limits

- UI decisions are presentation only. Validity, scores, policy, approver eligibility and execution stay with the backend. Every real mutation sends the acting persona.
- Mock transport is explicitly labeled and uses recorded values with interactive operator gates. It is a rehearsal, not a source of production policy.
- The full Engine models-on gate remains subject to the pre-existing `B-REQ-4` invalid/null command-card blocker. The manual crawl fallback and Engine evaluation completeness remain as documented in the status files; the redesign does not manufacture results.
- P1 topology, what-if predictions and explain overlays are not added during the blocked G3 gate.

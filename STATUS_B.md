# STATUS_B: Agent B (Console)

## Gate

**G0, G1 and G2 passed. Approved v3 redesign implemented with P0 UI coverage retained. G3: redesigned real UI golden path passed with models OFF; models ON remains blocked by B-REQ-4.** Contracts 1.0.0. TypeScript, production build, 17 unit tests, six mock browser tests and the real UI golden path including two-person undo pass.

## Done

- Ownership boundaries checked; Agent A's work remains untouched.
- React 18 / TypeScript / Vite, Tailwind 4 and shadcn-style Radix primitives. Approved v3 light design supersedes the original §13.1 colors per the user's explicit direction; local fonts, rail, top bar, persona switcher, SIM clock, read-only and source access remain.
- `frontend/`: `npm run dev:mock` serves http://127.0.0.1:5173 with contract-derived fixtures; `npm run dev` uses backend :8000 through REST/WebSocket proxy.
- P0 routes: `/console`, `/incidents`, `/knowledge`, `/ledger`, `/audit`, `/eval`; Director button or Ctrl+Shift+D.
- Shared card library; xterm with ghost/output queue, health, trace detail drawer, citation/metric drawer, explicit T2 confirmation, rejection reasons, live preview validation, undo proposal.
- Content pack present: 21 command references, 20 concepts, 4 playbooks, 20 claims (16 verified / 4 pending), 8 past incidents, 60 glossary entries, 20 Appendix A / PATHWAY 2049 operator-message fallback records. All synthetic annotations labeled. `data/content/manifest.json` documents counts.
- `npm run gen:types` generates REST, WS and card types and copies examples without modifying contracts.
- Dependency audit after compatible patch updates: zero vulnerabilities.
- Imported A's successful recording: 687 real events, 27 card/REST fixtures, four clock-driven telemetry/health phases. `npm run import:recording` refreshes it; `npm run validate:recording` validates all 687 envelopes against frozen contracts. Approval gates remain interactive.
- Real transport: terminal responses subscribe to their confirmation thread; incident subscription snapshots merge without overwriting newer events; approval and promotion payloads match frozen shapes. Terminal output is serialized by execution, including interleaved parallel checks. All real mutations capture the acting persona.
- Approved v3 redesign: service overview, Servers / Processors / Events, chart windows and sources, expandable light xterm workbench, direct manual command input, contextual Baton response plus complete ordered card-history drawer. Incident tabs separate Diagnosis / Steps / Evidence / Playbook while approvals, undo and charts remain visible. Shared theme applied across Knowledge, Ledger, Audit, Eval, Director, cards and dialogs. `frontend/docs/MVP_COVERAGE.md` maps the retained P0 features.
- Real redesigned UI passed on an isolated :8001 Engine (models off, embeddings off): Flow B edit/preview → incident → TMF → Priya A+B → Sam B → recovery → Dave reviews two claims → L2 grant → chain verified → Priya proposes T2 undo → Sam approves → Engine marks undo applied. 42.3 s, no browser exceptions. QA runtime files are confined to ignored `frontend/.qa/`.
- Full raw audit-entry inspection added. N-1 risk opens the backend's actual worst-survivor / per-CPU calculations. Combined plan preview resolves the backend's included options into two clickable review steps. Repeated incident status events preserve an active manual confirmation thread; new incident threads still open automatically. Mock initial telemetry excludes the recorded fault, and mock impact peaks track its replayed telemetry.

## In progress

- Models-on real UI failure reported with reproduction in B-REQ-4. Recorded mock browser regression is passing; awaiting Engine correction before retrying the same live test.

## Next

- Retry models-on real UI golden path after B-REQ-4 is fixed; complete G3 before adding P1 features. Final S1 burst profiling / G4 sign-off still follows that gate. The requested redesign is implemented and reviewed at 1440×900 and 1280×800.

## Blocked

- No Git remote configured: local commits available; pull/rebase/push require a human to add a remote.
- Models-on UI golden path blocked by the Engine error in B-REQ-4. Recording validation is complete. No backend source changes made by B.

## Requests to A

- **B-REQ-1 (resolved by live integration):** Frontend now submits all selected option IDs to the parent decision approval once. Backend creates per-option approvals and counts Priya's first decisions. Subsequent decisions use per-option IDs. Verified with the real `_decide_options` protocol through the UI; no contract change needed.
- **B-REQ-2 (open):** Please add the full manual crawl when your fetcher is ready. Content uses the permitted Appendix A fallback plus PATHWAY 2049 (20 records) instead of claiming the 60–150 target is complete. Other content counts meet §10.1.
- **B-REQ-3 (resolved):** Imported successful `contracts/recordings/golden_s1.json` into B-owned `frontend/src/mocks/recordings/`. Interactive adapter uses recorded card/output fixtures and ordered SIM-clock telemetry/health phases. All 687 raw envelopes validate; all five mock browser tests pass using recorded data.
- **B-REQ-4 (blocking models ON):** Real UI run with `BATON_LLM_PROVIDER=nemotron`, embeddings none, replay preserved: S1 demo → Priya asks “Is ATM auth keeping up?”. Backend emits `run.failed` with Pydantic `command.body.rendered: Input should be a valid string, input_value=None`. No STATS command card arrives. UI displays the server failure; B does not repair backend plans. Please fix the invalid/null-rendered command-card path (and deterministic fallback on an invalid model plan) so Flow B survives models on. Models-off real UI passed through resolution, claim reviews, grant and audit.
  - Retried after Engine commit `7b320c2` with a fresh B-owned process: same null-rendered error in command graph `_execute` → `patch` → `CardStore.upsert`, during `run_auto`. Router also exceeded the old 12 s UI request limit; B increased only message-submission timeout to 60 s to accommodate Engine fallback. No server logic changed.

## Answers to A

- **A-REQ-1 acknowledged:** use `contracts/examples/`; preserve hypothesis `for`; upsert whole cards by ID and sort by seq; queue ghost/output by exec_id and show label; all mutations carry actor; URL-encode ledger keys. Contracts 1.0.0 additive notes acknowledged.
- **A-REQ-2 resolved:** real models-off UI run passed using incident-thread subscription plus REST snapshot merge. Parent decision is submitted once with all chosen IDs; B then uses the option approval ID for Sam. Manual terminal response `thread_id` now opens/subscribes its confirmation thread. Catalog request logging needs no new endpoint. Your successful 687-event recording is integrated with the mock clock and interactive approvals, validated against schemas and covered by Chrome acceptance tests.
  - Redesign retains contracts 1.0.0 and the same endpoint/actor protocol. Isolated real UI check passed with two-person undo as well; no A-owned code, process or runtime directory was altered for this QA.

## Notes for humans

- Work is local-only in the requested shared repository. No external hosting.
- Synthetic demo content and mock transport will be labeled explicitly. Mock safety decisions live only in the mock service; production decisions come from the backend.
- G3 models-off is verified on the real backend. Current known Engine calibration: recovered ATM p95 can be below band_low, while backend verification treats <= band_high as recovered. UI displays the backend criterion/result honestly; B did not alter scoring or dynamics.
- Redesign commits: `cc5664f` implementation and `cd4a663` workflow/provenance safeguards. Final checks: production build, typecheck, 17 unit tests, six Chrome tests (38.9 s), 687-envelope validation, plus the isolated real models-off golden/undo run (42.3 s). No Git remote is configured, so commits remain local.
- Visual review includes healthy and active overview, partial two-person approval and all P0 routes. Charts are capped at two visual updates per second. Saved screenshots: `frontend/docs/implemented-overview.png`, `frontend/docs/implemented-active.png`, `frontend/docs/implemented-incident.png`.
- B-owned QA processes are stopped after verification. Start `npm run dev:mock` inside `frontend/` for offline review, or start Engine and `npm run dev` for real mode.

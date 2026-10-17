# STATUS_B: Agent B (Console)

## Gate

**G0, G1 and G2 passed. G3: real UI golden path passed with models OFF; models ON blocked by B-REQ-4. Recorded transport integration complete.** Contracts 1.0.0. TypeScript, production build, 15 unit tests and all five mock browser tests pass.

## Done

- Ownership boundaries checked; Agent A's work remains untouched.
- React 18 / TypeScript / Vite, Tailwind 4 and shadcn-style Radix primitives. All §13.1 tokens, locally bundled fonts, rail, top bar, persona switcher, SIM clock, read-only switch.
- `frontend/`: `npm run dev:mock` serves http://127.0.0.1:5173 with contract-derived fixtures; `npm run dev` uses backend :8000 through REST/WebSocket proxy.
- P0 routes: `/console`, `/incidents`, `/knowledge`, `/ledger`, `/audit`, `/eval`; Director button or Ctrl+Shift+D.
- Shared card library; xterm with ghost/output queue, health, trace detail drawer, citation/metric drawer, explicit T2 confirmation, rejection reasons, live preview validation, undo proposal.
- Content pack present: 21 command references, 20 concepts, 4 playbooks, 20 claims (16 verified / 4 pending), 8 past incidents, 60 glossary entries, 20 Appendix A / PATHWAY 2049 operator-message fallback records. All synthetic annotations labeled. `data/content/manifest.json` documents counts.
- `npm run gen:types` generates REST, WS and card types and copies examples without modifying contracts.
- Dependency audit after compatible patch updates: zero vulnerabilities.
- Imported A's successful recording: 687 real events, 27 card/REST fixtures, four clock-driven telemetry/health phases. `npm run import:recording` refreshes it; `npm run validate:recording` validates all 687 envelopes against frozen contracts. Approval gates remain interactive.
- Real transport: terminal responses subscribe to their confirmation thread; incident subscription snapshots merge without overwriting newer events; approval and promotion payloads match frozen shapes. Terminal output is serialized by execution, including interleaved parallel checks. All real mutations capture the acting persona.

## In progress

- Real UI (`e2e/live.spec.ts`, `BATON_LIVE=1`) passed with `BATON_LLM_PROVIDER=none` and embeddings off: Flow B edit/preview → fault → TMF approval → decision gate → Priya A+B → Sam B → verified recovery → Dave confirms/edits two claims → L2 grant → audit chain verification. 52.4 s, no browser exceptions.
- Models-on real UI failure reported with reproduction in B-REQ-4. Recorded mock browser regression is passing; awaiting Engine correction before retrying the same live test.

## Next

- Retry models-on real UI golden path after B-REQ-4 is fixed; complete G3 before adding P1 features. Continue the §13.8 visual review at 1440×900.

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

## Notes for humans

- Work is local-only in the requested shared repository. No external hosting.
- Synthetic demo content and mock transport will be labeled explicitly. Mock safety decisions live only in the mock service; production decisions come from the backend.
- G3 models-off is verified on the real backend. Current known Engine calibration: recovered ATM p95 can be below band_low, while backend verification treats <= band_high as recovered. UI displays the backend criterion/result honestly; B did not alter scoring or dynamics.
- Local commits: `9530238` frontend and `0a56fd1` content / browser acceptance. Chrome mock golden path, safety refusal and compact layout all pass. Screenshots are in ignored `frontend/test-results/`.
- B-owned QA servers currently use :8000 (Nemotron, embeddings off) and :5174 (real UI); mock preview is :5173. They will be stopped after QA to free the ports.

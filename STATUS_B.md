# STATUS_B: Agent B (Console)

## Gate

**G0 passed. G1/G2 implementation complete, browser verification in progress.** Contracts 1.0.0 generated, TypeScript passes, production build passes. Real backend golden path (G3) not yet verified.

## Done

- Ownership boundaries checked; Agent A's work remains untouched.
- React 18 / TypeScript / Vite, Tailwind 4 and shadcn-style Radix primitives. All §13.1 tokens, locally bundled fonts, rail, top bar, persona switcher, SIM clock, read-only switch.
- `frontend/`: `npm run dev:mock` serves http://127.0.0.1:5173 with contract-derived fixtures; `npm run dev` uses backend :8000 through REST/WebSocket proxy.
- P0 routes: `/console`, `/incidents`, `/knowledge`, `/ledger`, `/audit`, `/eval`; Director button or Ctrl+Shift+D.
- Shared card library; xterm with ghost/output queue, health, trace detail drawer, citation/metric drawer, explicit T2 confirmation, rejection reasons, live preview validation, undo proposal.
- Content pack present: 21 command references, 20 concepts, 4 playbooks, 20 claims (16 verified / 4 pending), 8 past incidents, 60 glossary entries, 19 Appendix A operator-message fallback records. All synthetic annotations labeled. `data/content/manifest.json` documents counts.
- `npm run gen:types` generates REST, WS and card types and copies examples without modifying contracts.
- Dependency audit after compatible patch updates: zero vulnerabilities.

## In progress

- Browser QA at 1440×900 and 1280×800, mock golden path and safety checks; scope/content and realtime tests.

## Next

- Commit checked G0/G1 work; complete G2 checks, then switch to real backend as Engine endpoints become available.

## Blocked

- No Git remote configured: local commits available; pull/rebase/push require a human to add a remote.

## Requests to A

- **B-REQ-1 (open):** Decision example has null `body.approval_id` and null option `approval_id`. UI submits to `/api/approvals/{id}/decide` per selected option. Please attach per-option approval IDs when options are emitted (or specify the intended initiation route). Needed so “Approve selected” concretely creates/advances A and B approvals without UI business logic. Mock transport currently pre-creates two approval records.
- **B-REQ-2 (open):** Please add the full manual crawl when your fetcher is ready. Content uses the permitted Appendix A fallback (19 records) instead of claiming the 60–150 target is complete. Other content counts meet §10.1.

## Answers to A

- **A-REQ-1 acknowledged:** use `contracts/examples/`; preserve hypothesis `for`; upsert whole cards by ID and sort by seq; queue ghost/output by exec_id and show label; all mutations carry actor; URL-encode ledger keys. Contracts 1.0.0 additive notes acknowledged.

## Notes for humans

- Work is local-only in the requested shared repository. No external hosting.
- Synthetic demo content and mock transport will be labeled explicitly. Mock safety decisions live only in the mock service; production decisions come from the backend.
- G3 will only be marked passed after the real backend golden path is exercised.

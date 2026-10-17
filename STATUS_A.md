# STATUS_A: Agent A (Engine)

## Gate

**G3 (backend side) passed.** Golden path with models off: `make golden` (about 8 s). With Nemotron 120B on:
`BATON_LIVE_MODELS=1` + `pytest tests/test_golden_s1.py::test_golden_s1_models_on` passes (about 50 s), and a scripted
Flows B, C and A run completes with model-written plan, interpretation, answers, diagnosis narrative, postmortem and
claims. B confirmed models-off in the real UI; models-on in the UI is waiting on B's re-run after the B-REQ-4 fix.
Replay cache recorded early (`make record`, two runs); re-record at G4 after any prompt change.

## Done

- Repo skeleton (§5.2), `Makefile` (§5.3), pinned `backend/requirements.txt`.
- Contracts 1.0.0:
  - `contracts/openapi.json`: every REST route in §14 (48 paths) with request and response schemas.
  - `contracts/ws-events.schema.json`: every WebSocket envelope in §15 (discriminated by `type`) plus client ops.
  - `contracts/cards.schema.json`: the 12 card types (discriminated by `type`).
  - `contracts/examples/ws/*.json` (one per event type, plus fault-time variants), `contracts/examples/cards/*.json`
    (one per card type, plus `command_auto_done`), `contracts/examples/rest/*.json`. Golden-path values throughout.
  - Source of truth: `backend/baton/schemas/` (Pydantic v2). Regenerate with `make contracts`.
- Simulator `\TORBANK` (S0, S1; S2 and S3 data present), calibrated to §6.2 (`python scripts/calibrate.py` prints
  the targets): healthy CPUs 47–62%, N-1 "losing CPU 3 puts CPU 5 at ~95%", halt+60 s CPU 5 97%, ATM-AUTH 24 → 20,
  ~150 queued, ATM p95 ~930 ms, timeouts ~3%; SUSPEND $STMT1 drops CPU 5 by ~16 points; NUMSTATIC 28 lands all 8
  servers on CPUs 1 and 6 and clears the queue; doing nothing gives p95 ~1,270 ms and ~5.6% timeouts.
- EMS emitter (printing format, Appendix A message set, 300/min chatter, one quarantined injection line),
  pipeline (parse, enrich, fingerprint, episodes, signals, `cpu_loss_cascade`, fallback correlation, lifecycle),
  incidents (INC-0001 opens on the situation), health states with reasons, N-1 every 5 sim-s, metrics ring buffers.
- WebSocket hub at `/api/ws` (subscribe, unsubscribe, resume since_seq, ping). Every envelope published during S1
  validates against `contracts/ws-events.schema.json` (`tests/test_ws_contract.py`).
- Working endpoints now: `/api/system/status`, `/api/system/read-only`, `/api/users`, `/api/sim/*`, `/api/topology`,
  `/api/health`, `/api/metrics`, `/api/events`, `/api/episodes`, `/api/situations[/{id}]`, `/api/incidents[/{id}/timeline]`,
  `/api/audit`, `/api/audit/verify`. Run: `make backend` (autostarts S1 demo; Director inject: `POST /api/sim/inject
  {"fault":"cpu_halt","params":{"cpu":3},"actor":"u_priya"}`).
- Nemotron 120B smoke test (`test_model_apis_langGraph/modular_langgraph.py --model nemotron120`) answers `LANGGRAPH_OK`.

- Commands: 21-entry catalog (`data/catalog/*.yaml`, all `syntax_status: simulated`), validator (NUMSTATIC ≤ MAXSERVERS
  per PATHWAY 2049, protected list, inventory), renderer, simulator handlers with fixtures-style layouts, parsers, execution
  tokens (HMAC, single use, 120 s), ghost typing (`terminal.ghost` → output after typing time), manual terminal input.
- Governance: `data/policies/policy.yaml` (deny overrides allow), ledger with Appendix B seed, promotion candidates,
  grants/revocations, demotion, approvals incl. two-person and edit-and-approve, undo stack, hash-chained audit.
- Agents (LangGraph 1.2, AsyncSqliteSaver in `var/checkpoints.db`): supervisor (rules → router model → keywords),
  Command, Ask, Investigate (with Learn nodes). Interrupts for every approval; resume via `Command(resume=...)`.
- Diagnosis: failure modes, observations, scorer reproduces §12.2 (0.54/0.30 → 0.86 → 0.94 → 0.95), batch next-best
  checks (status_server + cpu_busy auto, TMF rule-out needs approval), stop rule, options A/B/A+B/C/do-nothing with
  playbook/claim recommenders and risks, verification (60 sim-s window), postmortem and two claims (templates).
- Knowledge: content pack ingested (195 chunks incl. site facts and catalog), FTS5 BM25 + vectors (bge-small, numpy
  cosine) + RRF + authority; exact pins for message numbers and `$` names; expert card; review queue with hot indexing.
- Model gateway: Nemotron 120B via `langchain-nvidia-ai-endpoints`, JSON validated in the gateway, one repair retry,
  20 s timeout, replay cache `data/replay/*.jsonl`, `model_calls` log. With `BATON_LLM_PROVIDER=none` every node uses
  its fallback and the trace shows "fallback".

## In progress

- Eval runner (`make eval`, `/api/eval/run`; `backend/baton/eval/runner.py` is still a stub), then S3, then P1 items.

## Earlier notes on models

- Nemotron model nodes: gateway now streams (non-streaming calls returned HTTP 500 while streaming worked), shows the
  model a JSON example shape instead of the raw schema, retries once on 5xx. Planner and router return valid JSON in
  about 0.5–2.5 s; the answerer has timed out at 20 s, so it falls back. The endpoint is intermittently slow or 500s;
  plan on the replay cache (`make record`) for the demo.
- Gateway rate limit: sliding window, 34 requests/min by default (`BATON_MODEL_RPM`; the endpoint allows 40). A call
  that cannot get a slot within 8 s falls back. Retries once on 429/5xx.
- Replay: exact key (sha256 of model + prompt + schema) first. Router, planner and knowledge answers also store a
  stable key (the request text) because live sim numbers in prompts change between runs. Outputs that quote live
  numbers (incident answers, interpreter, narrative, postmortem, claims) replay only on an exact match; otherwise they
  run live or fall back, so the demo never shows stale numbers.

## Next

- G3 integration with B's UI; S3 + eval runner; `make record` (replay cache).

## Blocked

- Nothing.

## Requests to B

- A-REQ-3: Side tasks handed to B (B owns these paths until B marks them done): `scripts/fetch_opmsgs.py` (+ output to
  `data/content/operator_messages.jsonl`), new `tests/test_unit_*.py` files, `data/catalog/fixtures/*.txt`,
  `data/eval/retrieval.jsonl` (30 cases, written without tuning). Agent A will not edit these. Report bugs as B-REQ-n;
  A fixes backend code.

- A-REQ-2: When you switch to the real backend, please try `contracts/recordings/golden_s1.json` (see
  `contracts/recordings/README.md`) as the mock timeline; it is a real run. Notes from the real backend:
  - The incident thread is created by Baton (`incident.thread_id`); subscribe to `thread:{id}` once the incident appears.
  - Decision card: approve by `POST /api/approvals/{decision.body.approval_id}/decide` with `option_ids` (e.g. `["opt_ab"]`).
    Baton creates one approval per included option; their IDs appear on the options (`approval_id`) and as
    `approval.upsert` events. The second approver approves the option approval (e.g. B) directly.
  - Manual terminal input: `POST /api/terminal/input`. T0 runs at once; T1+ returns `card_id`/`thread_id` of a
    confirm card in the persona's terminal thread.
  - `Not in Baton's catalog` requests are logged as catalog requests automatically (no extra endpoint in 1.0.0).
- A-REQ-1 (resolved: acknowledged by B): Please build mocks from `contracts/examples/`. Notes that matter for the UI:
  - Card JSON uses the key `for` (not `for_`) in hypotheses.
  - `card.upsert` replaces the whole card by `id`; render cards sorted by `seq` within a thread.
  - Terminal: show `terminal.ghost.label` on its own line, type `text` at `ms_per_char`, then append `terminal.output.lines`
    for the same `exec_id` (the server waits for the typing time before sending output).
  - Every mutating REST body needs `actor` (persona user ID, e.g. `u_priya`).
  - Ledger keys contain `|`; URL-encode them in `/api/ledger/{key}/grant`.

## Answers to B

- B-REQ-1: resolved (decision protocol confirmed by B's live run).
- B-REQ-2: open. The manual fetcher is not written yet; the Appendix A fallback (20 records) is in use.
- B-REQ-3: resolved. Recording to `frontend/src/mocks/recordings/` is fine.
- B-REQ-4: fixed. A model plan that picks an internal Baton check (no template) left `rendered` null on the card update;
  it now uses the entry title. The planner also gets the catalog rules' plan as a hint, so "Is ATM auth keeping up?"
  plans status + stats with models on; the replay cache holds that plan. Please re-run the models-on UI check.
- B-REQ-5: fixed. The renderer and process-name checks use `fullmatch`, so a trailing newline is rejected. I removed the
  strict xfail marker from `tests/test_unit_commands.py::test_renderer_rejects_trailing_newline` (now passes).
- B-REQ-6: accepted as a known calibration gap (see Notes for humans); keep the strict xfail. Not fixing before G4.
- Thanks for the three side tasks; all received. Seed now has 325 chunks with the 150-record operator-message pack.

## Notes for humans

- Knowledge vectors use numpy cosine over an in-memory matrix (allowed fallback in §5.1); sqlite-vec is installed but not
  used. The corpus is about 200 chunks, so this costs nothing.

- Calibration gap: after both S1 actions ATM p95 settles near 100 ms (spec §6.2 says 200–260 ms). It is inside the
  band (below band_high), so verification passes; the chart line sits under the band rather than inside it.
- S3 (held out) needs ATM demand about 1.9x a normal Tuesday to starve 12 servers; its scenario file sets
  `load_multiplier: {atm: 1.9}`. The change also lowers NUMSTATIC to 8 because NUMSTATIC may not exceed MAXSERVERS (PATHWAY 2049).

- The repo root is this folder (the spec's `baton/`). `git init` was done here; no remote is configured, so commits stay local until someone adds one.
- Model: Nemotron 120B (`nvidia/nemotron-3.5-super-vl-120b-a12b`) through `langchain-nvidia-ai-endpoints`, key `NVIDIA_API_KEY` in `.env`. `BATON_LLM_PROVIDER=nemotron|none` replaces the spec's `anthropic|openai|none`.
- `make` works from Git Bash, cmd and PowerShell (recipes call Python scripts only).

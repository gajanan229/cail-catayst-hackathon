# STATUS_A: Agent A (Engine)

## Gate

**G0 passed** (contracts 1.0.0 frozen). Working toward G1.

## Done

- Repo skeleton (§5.2), `Makefile` (§5.3), pinned `backend/requirements.txt`.
- Contracts 1.0.0:
  - `contracts/openapi.json`: every REST route in §14 (48 paths) with request and response schemas.
  - `contracts/ws-events.schema.json`: every WebSocket envelope in §15 (discriminated by `type`) plus client ops.
  - `contracts/cards.schema.json`: the 12 card types (discriminated by `type`).
  - `contracts/examples/ws/*.json` (one per event type, plus fault-time variants), `contracts/examples/cards/*.json`
    (one per card type, plus `command_auto_done`), `contracts/examples/rest/*.json`. Golden-path values throughout.
  - Source of truth: `backend/baton/schemas/` (Pydantic v2). Regenerate with `make contracts`.
- Nemotron 120B smoke test (`test_model_apis_langGraph/modular_langgraph.py --model nemotron120`) answers `LANGGRAPH_OK`.

## In progress

- Simulator core (S0, S1), EMS emitter, pipeline, situations, health, N-1, WebSocket hub (G1).

## Next

- Catalog, validator, governance, Command and Investigate graphs on deterministic paths, `make golden` (G2).

## Blocked

- Nothing.

## Requests to B

- A-REQ-1: Please build mocks from `contracts/examples/`. Notes that matter for the UI:
  - Card JSON uses the key `for` (not `for_`) in hypotheses.
  - `card.upsert` replaces the whole card by `id`; render cards sorted by `seq` within a thread.
  - Terminal: show `terminal.ghost.label` on its own line, type `text` at `ms_per_char`, then append `terminal.output.lines`
    for the same `exec_id` (the server waits for the typing time before sending output).
  - Every mutating REST body needs `actor` (persona user ID, e.g. `u_priya`).
  - Ledger keys contain `|`; URL-encode them in `/api/ledger/{key}/grant`.

## Answers to B

- (none yet)

## Notes for humans

- The repo root is this folder (the spec's `baton/`). `git init` was done here; no remote is configured, so commits stay local until someone adds one.
- Model: Nemotron 120B (`nvidia/nemotron-3.5-super-vl-120b-a12b`) through `langchain-nvidia-ai-endpoints`, key `NVIDIA_API_KEY` in `.env`. `BATON_LLM_PROVIDER=nemotron|none` replaces the spec's `anthropic|openai|none`.
- `make` works from Git Bash, cmd and PowerShell (recipes call Python scripts only).

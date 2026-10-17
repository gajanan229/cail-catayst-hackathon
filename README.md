# Baton

AI operations co-pilot for HPE NonStop, running against a simulated node `\TORBANK`.
Specs: `BATON_MVP_SPEC.md` (source of truth) and `docs/BATON_PRODUCT_SPEC.md`.

<!-- BEGIN AGENT A SECTIONS (backend) -->

## Backend: setup

Requirements: Python 3.12, GNU make (Windows: `choco install make`), Node 20+ for the frontend.

```powershell
py -3.12 -m venv .venv            # once
make setup                         # pip install -r backend/requirements.txt (+ frontend npm install if present)
make seed                          # build var/ (SQLite, knowledge indexes, embeddings cache) from data/
make dev                           # backend :8000 + frontend :5173
```

CPU-only PyTorch keeps the install small: `.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu` before `make setup`.

## Backend: make targets

| Target | What it does |
| --- | --- |
| `make setup` | Install backend (and frontend) dependencies |
| `make seed` | Build `var/` from `data/`: database, ledger seed, knowledge indexes |
| `make dev` | Backend on http://localhost:8000 (API docs at `/docs`) and frontend on http://localhost:5173 |
| `make backend` | Backend only |
| `make reset` | Reset the simulator and runtime tables (under 5 s); uses the running server if there is one |
| `make test` | All unit tests |
| `make golden` | Headless S1 acceptance test (`tests/test_golden_s1.py`, models off) |
| `make eval` | Command (40), safety (12), diagnosis (S1, S3) and retrieval (30) suites; results on the Eval page |
| `make record` | Two golden runs (Flows B, C, A) with Nemotron and `BATON_REPLAY=record` to fill `data/replay/` |
| `make record-ws` | Record a real golden run into frontend mock fixture format (`scripts/record_ws.py`) |
| `make contracts` | Regenerate `contracts/` from the Pydantic models |

## Backend: environment variables

Put secrets in the project-root `.env` (never committed).

| Variable | Values | Default | Notes |
| --- | --- | --- | --- |
| `BATON_LLM_PROVIDER` | `nemotron`, `none` | `none` | `nemotron` = NVIDIA Nemotron 120B via `langchain-nvidia-ai-endpoints` (see `test_model_apis_langGraph/`) |
| `NVIDIA_API_KEY` | secret | unset | Required for `nemotron` |
| `BATON_MODEL_FAST` | model ID | `nvidia/nemotron-3.5-super-vl-120b-a12b` | Router, interpreter, diagnostician, scribe |
| `BATON_MODEL_STRONG` | model ID | `nvidia/nemotron-3.5-super-vl-120b-a12b` | Planner, answerer, curator |
| `BATON_NVIDIA_BASE_URL` | URL | `https://integrate.api.nvidia.com/v1` | |
| `BATON_NEMOTRON_THINKING` | `0`, `1` | `0` | Enable Nemotron reasoning mode (slower) |
| `BATON_REPLAY` | `off`, `record`, `replay` | `replay` | Replay cache in `data/replay/*.jsonl` |
| `BATON_RERANK` | `0`, `1` | `0` | Cross-encoder reranker (P1); off by default, it lowered recall in eval |
| `BATON_MODEL_RPM` | integer | `34` | Client-side request cap per minute (the NVIDIA endpoint allows 40) |
| `BATON_LIVE_MODELS` | `0`, `1` | `0` | Tests only: `1` runs the models-on golden test |
| `BATON_EMBEDDINGS` | `local`, `none` | `local` | `none` = BM25 only |
| `BATON_SEED` | integer | `42` | |
| `BATON_DB` | path | `var/baton.db` | |

## Backend: golden path

`make reset && make dev`, open http://localhost:5173, persona Priya, Director → S1 demo profile → Start → "CPU 3 halt".
Headless: `make golden`.

## Backend: troubleshooting

- `make` not found on Windows: `choco install make`, or run the commands in the Makefile directly with `.venv\Scripts\python.exe`.
- Nemotron slow or failing: set `BATON_LLM_PROVIDER=none`; every model step has a deterministic fallback and the trace shows "fallback".
- Embedding model cannot download: `BATON_EMBEDDINGS=none` (BM25 only), or pre-build `var/emb_cache/` with `make seed` on a connected machine.

<!-- END AGENT A SECTIONS -->

<!-- BEGIN AGENT B SECTIONS (frontend) -->

## Frontend: setup and run

Node 20.19+ or 22.12+ is required (development verified with Node 24). From the repository root:

```powershell
cd frontend
npm ci
npm run gen:types       # after contracts/VERSION changes
npm run dev            # http://127.0.0.1:5173; backend REST + WebSocket proxied to :8000
```

For a complete offline rehearsal without the backend:

```powershell
cd frontend
npm run dev:mock
```

`dev:mock` loads `.env.mock` (`VITE_MOCK=1`). The status rail explicitly labels mock mode. All fonts and runtime assets are bundled locally; no font CDN is used. Initial installation requires npm access. `VITE_API_URL` may point to another backend origin; by default the development proxy keeps requests on the same origin. For deployment, the static build needs a same-origin `/api` HTTP/WebSocket reverse proxy.

## Frontend: routes and controls

| Route | Purpose |
| --- | --- |
| `/console` | Overview with Service health / Servers / Processors / Events tabs; expandable command workbench and contextual Baton panel |
| `/incidents` | Timeline; Diagnosis / Steps / Evidence / Playbook tabs; decisions, approvals, undo, recovery charts and Postmortem |
| `/knowledge` | Expert review queue, verified claims and cited search with ranking detail |
| `/ledger` | Command/role autonomy matrix, promotion review, grant and revoke |
| `/audit` | Actor/action log, incident filter and SHA-256 chain verification |
| `/eval` | Latest backend results; mock mode clearly labels contract example scores |

Open **Director** from the rail or with **Ctrl+Shift+D**. S1 demo → Start → CPU 3 halt begins the mock golden path. In Incident Room approve the TMF check, then select A+B. Priya's approval runs A and leaves B awaiting a second person. Switch the top-bar persona to Sam, confirm B, and watch verification. Switch to Dave to review claims and grant the L2 promotion. The acting persona is sent as `actor` on every mutation.

The approved redesign uses a light service overview and a professional command workspace. Click **Expand** for more command/output space; switch the workbench to Event stream or Activity without losing terminal history. Diagnostic tabs support arrow keys, Home and End. The Baton pane shows the current human task or latest response; **View all cards** retains the full ordered card history and its actions. **Review plan & approvals** opens the complete Incident Room. Trace steps, metric sources and audit payloads open for inspection. [MVP coverage](frontend/docs/MVP_COVERAGE.md) maps every P0 area to its location and checks.

The mock clock drives telemetry at the selected speed. The mock golden path includes explicit approval gates and a 60-simulated-second verification window. Only the S1 CPU 3 fault is implemented in the interactive mock; other faults require the real backend. The mock audit chain is computed and checked locally rather than displaying a fabricated verification result. Model replay controls are separate from the mock transport.

Telemetry, health reasons, command output and incident cards come from Agent A's successful 687-event recording. The interactive adapter retains human approval gates and replays recorded telemetry phases on the mock SIM clock. After Engine records a new golden run, use `npm run import:recording` to copy it from `contracts/recordings/golden_s1.json`, then `npm run validate:recording` to check every envelope against the frozen schema. Neither command modifies contracts.

## Frontend: checks and content

```powershell
cd frontend
npm run typecheck
npm test
npm run build
npm run validate:recording
npm run test:e2e        # installed Chrome; mock server reused or launched automatically
```

For a real backend already running on :8000, run `$env:BATON_LIVE='1'; npm run test:e2e` in PowerShell. The live test uses :5174 and performs scenario reset, approvals, claim reviews and a promotion on the simulator. Close that shell or remove `Env:BATON_LIVE` to return to mock tests.

Playwright tests in `e2e/` cover the guarded golden path, unsafe-request refusal, parameter editing, cited teaching, keyboard diagnostics, manual commands, retained terminal output, trace/playbook inspection, undo proposals, audit payloads, local fonts and the 1280×800 layout. The live test also exercises two-person undo after recovery. Primary visual review is at 1440×900. Screenshots/traces are written to ignored `frontend/test-results/`.

For isolated integration QA, `BATON_PROXY_TARGET` can point Vite to another local Engine port (default `http://127.0.0.1:8000`). The ordinary setup is unchanged; this setting applies to both REST and WebSocket proxying.

Generated types and copied fixtures live in `frontend/src/api/generated/` and `frontend/src/mocks/fixtures/`; edit contracts only through Agent A. `npm run gen:types` is deterministic for the current contract version. Synthetic knowledge seeds are in `data/content/`, with provenance and counts in its README and manifest. The operator-message collection uses the permitted Appendix A fallback plus PATHWAY 2049; it does not claim a full manual crawl.

## Frontend: troubleshooting

- **Port 5173 already in use:** stop the existing frontend before switching mock/real modes, or use `npm run dev -- --port 5174` for a separate live preview.
- **Backend unavailable:** the console keeps last-known telemetry visible, marks connection loss and disables approvals while disconnected. Start `make backend`, then retry. Unavailable REST sections report an error without replacing real data with mocks.
- **Second approval won't run:** the second persona must be distinct and satisfy the backend's Senior/Expert requirement. The first approval stays visible.
- **Editing parameters:** wait for the backend preview before confirming. Validation errors keep the button disabled.
- **Read-only mode:** T1/T2 approval buttons show the reason and remain disabled; read-only checks can still run.
- **Browser tests cannot launch Chrome:** install Google Chrome or change `channel` in `e2e/playwright.config.ts` to an installed Playwright browser. Tests do not require a hosted service.
- **Contracts changed:** read `CONTRACTS_CHANGELOG.md`, run `npm run gen:types`, then type-check and test.

<!-- END AGENT B SECTIONS -->

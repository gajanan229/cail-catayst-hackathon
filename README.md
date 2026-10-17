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
| `make eval` | Command, safety and diagnosis suites; results on the Eval page |
| `make record` | Two golden runs with `BATON_REPLAY=record` to fill `data/replay/` |
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
<!-- END AGENT B SECTIONS -->

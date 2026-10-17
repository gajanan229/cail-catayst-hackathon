# Baton make targets (MVP spec §5.3). Recipes delegate to Python so they work from Git Bash, cmd or PowerShell.
ifeq ($(OS),Windows_NT)
PY ?= .venv/Scripts/python.exe
else
PY ?= .venv/bin/python
endif

.PHONY: setup seed dev backend reset test golden eval record contracts record-ws

setup:
	$(PY) -m pip install -r backend/requirements.txt
	$(PY) scripts/setup_frontend.py

seed:
	$(PY) scripts/seed.py

dev:
	$(PY) scripts/dev.py

backend:
	$(PY) scripts/dev.py --backend-only

reset:
	$(PY) scripts/reset.py

test:
	$(PY) -m pytest -q tests

golden:
	$(PY) -m pytest -q tests/test_golden_s1.py

eval:
	$(PY) scripts/run_eval.py

record:
	$(PY) scripts/record.py

record-ws:
	$(PY) scripts/record_ws.py

contracts:
	$(PY) scripts/gen_contracts.py

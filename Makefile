SHELL := /usr/bin/env bash

.PHONY: deps fmt fmt-check lint test openapi-validate compose-up compose-down dev inotify-check inotify-apply conformance conformance-ts conformance-py conformance-compare conformance-mutate conformance-symbols

PYTHON ?= python3
CONFORMANCE_DIR ?= implementation_plan/conformance
CONFORMANCE_OUT ?= conformance
CONFORMANCE_THRESHOLD ?= 100

# Install dev dependencies into the active environment.
deps:
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -r requirements-dev.txt
	$(PYTHON) -m pip install -e .

fmt:
	$(PYTHON) -m ruff format .

fmt-check:
	$(PYTHON) -m ruff format --check .

lint:
	$(PYTHON) -m ruff check .

test:
	PYTHONPATH=$(PWD)/src $(PYTHON) -m pytest -q

conformance: conformance-symbols conformance-ts conformance-py conformance-compare

conformance-symbols:
	$(PYTHON) $(CONFORMANCE_DIR)/symbol_audit.py --check

conformance-ts:
	cd swissknife && npx tsx test/conformance/ts-conformance-runner.cli.ts --vectors ../$(CONFORMANCE_DIR)/vectors --out ../$(CONFORMANCE_OUT)/ts-results.json

conformance-py:
	PYTHONPATH=$(PWD)/external/ipfs_datasets $(PYTHON) external/ipfs_datasets/ipfs_datasets_py/logic/conformance/py_reference_runner.py --vectors $(CONFORMANCE_DIR)/vectors --out $(CONFORMANCE_OUT)/py-results.json

conformance-compare:
	node $(CONFORMANCE_DIR)/compare.mjs --python $(CONFORMANCE_OUT)/py-results.json --ts $(CONFORMANCE_OUT)/ts-results.json --out-dir $(CONFORMANCE_OUT) --threshold $(CONFORMANCE_THRESHOLD)

conformance-mutate:
	node $(CONFORMANCE_DIR)/mutate.mjs --vectors $(CONFORMANCE_DIR)/vectors --out $(CONFORMANCE_OUT)/mutated-vectors.json

openapi-validate:
	$(PYTHON) scripts/validate_openapi.py spec/openapi.yaml

compose-up:
	docker compose up -d

compose-logs:
	docker compose logs -f --tail=200

compose-down:
	docker compose down

# Run the backend server
dev:
	$(PYTHON) -m handsfree.server

# Diagnose inotify usage/limits (no root required)
inotify-check:
	bash scripts/inotify_doctor.sh check

# Apply persistent inotify limits (requires sudo/root)
inotify-apply:
	bash scripts/inotify_doctor.sh apply

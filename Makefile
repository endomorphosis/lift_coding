SHELL := /usr/bin/env bash

.PHONY: deps fmt fmt-check lint test openapi-validate compose-up compose-down dev inotify-check inotify-apply conformance conformance-ts conformance-py conformance-compare conformance-mutate conformance-symbols conformance-ergo conformance-ergo-entailment conformance-ergo-entailment-crosslang conformance-ergo-output-parse-crosslang conformance-modal-codec-ir-crosslang conformance-modal-decompiler-crosslang conformance-deontic-parser-utils-crosslang conformance-deontic-parser-elements-crosslang conformance-modal-compiler-family-token-crosslang conformance-deontic-bridge-document-id-crosslang conformance-deontic-bridge-normalized-text-crosslang conformance-deontic-bridge-citation-crosslang conformance-deontic-bridge-decoded-text-crosslang conformance-deontic-bridge-guidance-crosslang conformance-deontic-bridge-list-of-dicts-crosslang conformance-deontic-bridge-target-names-crosslang conformance-deontic-bridge-fill-empty-crosslang conformance-deontic-bridge-rate-crosslang conformance-deontic-bridge-guidance-target-gap-crosslang conformance-deontic-bridge-guidance-normalization-crosslang conformance-deontic-bridge-guidance-row-match-crosslang conformance-deontic-bridge-guidance-evidence-rows-crosslang conformance-deontic-bridge-guidance-frame-selection-crosslang

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

conformance: conformance-symbols conformance-ts conformance-py conformance-compare conformance-ergo conformance-ergo-entailment conformance-ergo-entailment-crosslang conformance-ergo-output-parse-crosslang conformance-modal-codec-ir-crosslang conformance-modal-decompiler-crosslang conformance-deontic-parser-utils-crosslang conformance-deontic-parser-elements-crosslang conformance-modal-compiler-family-token-crosslang conformance-deontic-bridge-document-id-crosslang conformance-deontic-bridge-normalized-text-crosslang conformance-deontic-bridge-citation-crosslang conformance-deontic-bridge-decoded-text-crosslang conformance-deontic-bridge-guidance-crosslang conformance-deontic-bridge-list-of-dicts-crosslang conformance-deontic-bridge-target-names-crosslang conformance-deontic-bridge-fill-empty-crosslang conformance-deontic-bridge-rate-crosslang conformance-deontic-bridge-guidance-target-gap-crosslang conformance-deontic-bridge-guidance-normalization-crosslang conformance-deontic-bridge-guidance-row-match-crosslang conformance-deontic-bridge-guidance-evidence-rows-crosslang conformance-deontic-bridge-guidance-frame-selection-crosslang

conformance-symbols:
	$(PYTHON) $(CONFORMANCE_DIR)/symbol_audit.py --check

conformance-ts:
	cd swissknife && npx tsx test/conformance/ts-conformance-runner.cli.ts --vectors ../$(CONFORMANCE_DIR)/vectors --out ../$(CONFORMANCE_OUT)/ts-results.json

conformance-py:
	PYTHONPATH=$(PWD)/external/ipfs_datasets $(PYTHON) external/ipfs_datasets/ipfs_datasets_py/logic/conformance/py_reference_runner.py --vectors $(CONFORMANCE_DIR)/vectors --out $(CONFORMANCE_OUT)/py-results.json

conformance-compare:
	node $(CONFORMANCE_DIR)/compare.mjs --python $(CONFORMANCE_OUT)/py-results.json --ts $(CONFORMANCE_OUT)/ts-results.json --out-dir $(CONFORMANCE_OUT) --threshold $(CONFORMANCE_THRESHOLD)

conformance-ergo:
	cd swissknife && npx jest test/conformance/ergoai-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-ergo-entailment:
	cd swissknife && npx jest test/conformance/ergoai-entailment-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-ergo-entailment-crosslang:
	cd swissknife && npx jest test/conformance/ergoai-entailment-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-ergo-output-parse-crosslang:
	cd swissknife && npx jest test/conformance/ergoai-output-parse-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-modal-codec-ir-crosslang:
	cd swissknife && npx jest test/conformance/modal-codec-ir-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-modal-decompiler-crosslang:
	cd swissknife && npx jest test/conformance/modal-decompiler-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-parser-utils-crosslang:
	cd swissknife && npx jest test/conformance/deontic-parser-utils-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-parser-elements-crosslang:
	cd swissknife && npx jest test/conformance/deontic-parser-elements-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-modal-compiler-family-token-crosslang:
	cd swissknife && npx jest test/conformance/modal-compiler-family-token-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-bridge-document-id-crosslang:
	cd swissknife && npx jest test/conformance/deontic-bridge-document-id-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-bridge-normalized-text-crosslang:
	cd swissknife && npx jest test/conformance/deontic-bridge-normalized-text-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-bridge-citation-crosslang:
	cd swissknife && npx jest test/conformance/deontic-bridge-citation-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-bridge-decoded-text-crosslang:
	cd swissknife && npx jest test/conformance/deontic-bridge-decoded-text-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-bridge-guidance-crosslang:
	cd swissknife && npx jest test/conformance/deontic-bridge-guidance-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-bridge-list-of-dicts-crosslang:
	cd swissknife && npx jest test/conformance/deontic-bridge-list-of-dicts-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-bridge-target-names-crosslang:
	cd swissknife && npx jest test/conformance/deontic-bridge-target-names-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-bridge-fill-empty-crosslang:
	cd swissknife && npx jest test/conformance/deontic-bridge-fill-empty-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-bridge-rate-crosslang:
	cd swissknife && npx jest test/conformance/deontic-bridge-rate-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-bridge-guidance-target-gap-crosslang:
	cd swissknife && npx jest test/conformance/deontic-bridge-guidance-target-gap-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-bridge-guidance-normalization-crosslang:
	cd swissknife && npx jest test/conformance/deontic-bridge-guidance-normalization-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-bridge-guidance-row-match-crosslang:
	cd swissknife && npx jest test/conformance/deontic-bridge-guidance-row-match-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-bridge-guidance-evidence-rows-crosslang:
	cd swissknife && npx jest test/conformance/deontic-bridge-guidance-evidence-rows-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-bridge-guidance-frame-selection-crosslang:
	cd swissknife && npx jest test/conformance/deontic-bridge-guidance-frame-selection-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

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

SHELL := /usr/bin/env bash

.PHONY: deps fmt fmt-check lint test test-ci openapi-validate compose-up compose-down dev inotify-check inotify-apply conformance conformance-crosslang conformance-ts conformance-symbol-coverage conformance-py conformance-compare conformance-mutate conformance-symbols conformance-mutation-gate conformance-differential-fuzz conformance-ci conformance-self-containment conformance-self-containment-strict conformance-port239-host-native conformance-substance conformance-behavioral-certificate conformance-temporal-native conformance-ergo conformance-ergo-entailment conformance-ergo-entailment-crosslang conformance-ergo-output-parse-crosslang conformance-modal-codec-ir-crosslang conformance-modal-codec-guidance-crosslang conformance-modal-codec-citation-crosslang conformance-modal-decompiler-crosslang conformance-modal-decompiler-citation-crosslang conformance-deontic-parser-utils-crosslang conformance-deontic-parser-elements-crosslang conformance-modal-compiler-family-token-crosslang conformance-modal-compiler-serialization-crosslang conformance-deontic-bridge-document-id-crosslang conformance-deontic-bridge-normalized-text-crosslang conformance-deontic-bridge-citation-crosslang conformance-deontic-bridge-decoded-text-crosslang conformance-deontic-bridge-guidance-crosslang conformance-deontic-bridge-list-of-dicts-crosslang conformance-deontic-bridge-target-names-crosslang conformance-deontic-bridge-fill-empty-crosslang conformance-deontic-bridge-rate-crosslang conformance-deontic-bridge-guidance-target-gap-crosslang conformance-deontic-bridge-guidance-normalization-crosslang conformance-deontic-bridge-guidance-row-match-crosslang conformance-deontic-bridge-guidance-evidence-rows-crosslang conformance-deontic-bridge-guidance-frame-selection-crosslang conformance-deontic-bridge-json-guidance-crosslang conformance-deontic-bridge-guidance-route-crosslang
.PHONY: conformance-modal-codec-temporal-operator-crosslang conformance-modal-codec-guidance-summary-crosslang conformance-modal-codec-stable-embedding-crosslang conformance-modal-decompiler-temporal-operator-crosslang conformance-modal-compiler-ambiguity-policy-crosslang conformance-modal-compiler-formula-ambiguity-crosslang conformance-modal-compiler-regex-compile-crosslang conformance-deontic-formula-builder-crosslang conformance-deontic-bridge-frame-graph-crosslang conformance-bridge-frame-graph-crosslang conformance-multiview-merge-crosslang conformance-browser-purity conformance-tdfol-native-crosslang conformance-zkp-real-browser conformance-groth16-semantic-circuit conformance-python-deprecation

ifeq ($(wildcard .venv/bin/python),.venv/bin/python)
PYTHON ?= .venv/bin/python
else
PYTHON ?= python3
endif
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
	PYTHONPATH=$(PWD)/src:$(PWD)/external/ipfs_accelerate:$(PWD)/external/ipfs_kit:$(PWD)/external/ipfs_datasets $(PYTHON) -m pytest -q

# CI-required suite: skip monorepo board/fixture/interop tests that need full
# local agent trees, nested submodule fixtures, or optional external checkouts.
# MCP++ smoke remains a separate CI step (with deps like psutil).
test-ci:
	PYTHONPATH=$(PWD)/src:$(PWD)/external/ipfs_accelerate:$(PWD)/external/ipfs_kit:$(PWD)/external/ipfs_datasets $(PYTHON) -m pytest -q \
		--ignore=tests/test_hallucinate_multimodal_control_todo_queue.py \
		--ignore=tests/test_virtual_ai_os_todo_queue.py \
		--ignore=tests/test_virtual_ai_os_launch_readiness_gate.py \
		--ignore=tests/test_virtual_ai_os_capability_registry.py \
		--ignore=tests/test_virtual_ai_os_swissknife_integration.py \
		--ignore=tests/test_virtual_ai_os_component_contracts.py \
		--ignore=tests/test_virtual_ai_os_end_to_end.py \
		--ignore=tests/test_virtual_ai_os_end_to_end_harness.py \
		--ignore=tests/test_virtual_ai_os_playwright_replay_harness.py \
		--ignore=tests/test_virtual_ai_os_runtime_placement.py \
		--ignore=tests/test_meta_glasses_display_todo_queue.py \
		--ignore=tests/test_meta_glasses_mobile_orb_bridge.py \
		--ignore=tests/test_meta_glasses_display_widget_actions.py \
		--ignore=tests/test_meta_glasses_io_mcpplusplus_contract.py \
		--ignore=tests/test_meta_glasses_io_mocks.py \
		--ignore=tests/test_meta_glasses_multimodal_io_transport_contract.py \
		--ignore=tests/test_display_webapp_widget_readiness.py \
		--ignore=tests/test_mcplusplus_profile_h_inventory.py \
		--ignore=tests/test_mcplusplus_profile_h_spec.py \
		--ignore=tests/test_implementation_daemon_worktree_dependencies.py \
		--ignore=tests/test_implementation_daemon_merge_lock_retry.py \
		--ignore=tests/test_supervisor_objective_task_janitor.py \
		--ignore=tests/test_reconciliation_guardrail_refresh.py \
		--ignore=tests/test_swissknife_lane_worktrees.py \
		--ignore=tests/test_proof_backed_test_reuse_supervisor.py \
		--ignore=tests/commands/test_router.py \
		--ignore=tests/integration/test_external_meta_wearables_dat_android_external_ipfs_accelerate_interop.py \
		--ignore=tests/integration/test_external_meta_wearables_dat_android_external_ipfs_datasets_interop.py \
		--ignore=tests/integration/test_external_meta_wearables_dat_android_external_ipfs_kit_interop.py \
		--ignore=tests/integration/test_swissknife_external_meta_wearables_dat_android_interop.py \
		--ignore=tests/integration/test_swissknife_external_meta_wearables_dat_ios_interop.py \
		--ignore=tests/integration/test_swissknife_external_ipfs_accelerate_interop.py \
		--ignore=tests/integration/test_swissknife_external_ipfs_datasets_interop.py \
		--ignore=tests/integration/test_swissknife_mcp_plus_plus_interop.py \
		--ignore=tests/integration/test_swissknife_mobile_interop.py \
		--ignore=tests/integration/test_hallucinate_app_mobile_interop.py \
		--ignore=tests/integration/test_orb_dynamic_renderer.py \
		--ignore=tests/integration/test_e2e_connectivity.py \
		--ignore=tests/integration/test_desktop_app_integrations.py \
		--ignore=tests/integration/test_glasses_control_plane.py \
		--ignore=tests/mcplusplus_profile_h \
		--ignore=tests/unit/logic/ui_ux_ir

conformance: conformance-symbols conformance-ts conformance-symbol-coverage conformance-mutation-gate conformance-differential-fuzz conformance-port239-host-native conformance-substance conformance-behavioral-certificate conformance-temporal-native conformance-ergo conformance-ergo-entailment conformance-ergo-entailment-crosslang conformance-ergo-output-parse-crosslang conformance-modal-codec-ir-crosslang conformance-modal-codec-guidance-crosslang conformance-modal-codec-citation-crosslang conformance-modal-decompiler-crosslang conformance-modal-decompiler-citation-crosslang conformance-deontic-parser-utils-crosslang conformance-deontic-parser-elements-crosslang conformance-modal-compiler-family-token-crosslang conformance-modal-compiler-serialization-crosslang conformance-deontic-bridge-document-id-crosslang conformance-deontic-bridge-normalized-text-crosslang conformance-deontic-bridge-citation-crosslang conformance-deontic-bridge-decoded-text-crosslang conformance-deontic-bridge-guidance-crosslang conformance-deontic-bridge-list-of-dicts-crosslang conformance-deontic-bridge-target-names-crosslang conformance-deontic-bridge-fill-empty-crosslang conformance-deontic-bridge-rate-crosslang conformance-deontic-bridge-guidance-target-gap-crosslang conformance-deontic-bridge-guidance-normalization-crosslang conformance-deontic-bridge-guidance-row-match-crosslang conformance-deontic-bridge-guidance-evidence-rows-crosslang conformance-deontic-bridge-guidance-frame-selection-crosslang conformance-deontic-bridge-json-guidance-crosslang conformance-deontic-bridge-guidance-route-crosslang
conformance: conformance-modal-codec-temporal-operator-crosslang conformance-modal-decompiler-temporal-operator-crosslang
conformance: conformance-modal-codec-guidance-summary-crosslang
conformance: conformance-modal-codec-stable-embedding-crosslang
conformance: conformance-modal-compiler-ambiguity-policy-crosslang
conformance: conformance-modal-compiler-formula-ambiguity-crosslang
conformance: conformance-modal-compiler-regex-compile-crosslang
conformance: conformance-deontic-formula-builder-crosslang
conformance: conformance-deontic-bridge-frame-graph-crosslang
conformance: conformance-bridge-frame-graph-crosslang
conformance: conformance-multiview-merge-crosslang
conformance: conformance-browser-purity
conformance: conformance-tdfol-native-crosslang
conformance: conformance-zkp-real-browser
conformance: conformance-groth16-semantic-circuit
conformance: conformance-python-deprecation

# CI Logic Conformance gate: core harness + py/ts compare. Full make
# conformance (jest matrix, self-containment, deprecation) remains local.
conformance-ci: conformance-symbols conformance-ts conformance-symbol-coverage conformance-mutation-gate conformance-differential-fuzz conformance-port239-host-native conformance-substance conformance-py conformance-compare

conformance-crosslang: conformance-ts conformance-py conformance-compare conformance-self-containment

conformance-symbols:
	$(PYTHON) $(CONFORMANCE_DIR)/symbol_audit.py --check

conformance-ts:
	rm -rf $(CONFORMANCE_OUT)/v8-coverage
	mkdir -p $(CONFORMANCE_OUT)/v8-coverage
	cd swissknife && NODE_V8_COVERAGE=$(PWD)/$(CONFORMANCE_OUT)/v8-coverage npx tsx test/conformance/ts-conformance-runner.cli.ts --vectors ../$(CONFORMANCE_DIR)/vectors --out ../$(CONFORMANCE_OUT)/ts-results.json

conformance-symbol-coverage:
	node $(CONFORMANCE_DIR)/coverage_reconciliation.mjs --symbol-map $(CONFORMANCE_DIR)/symbol-map.json --evidence-map $(CONFORMANCE_DIR)/symbol-evidence.json --ts-results $(CONFORMANCE_OUT)/ts-results.json --vectors $(CONFORMANCE_DIR)/vectors --v8-coverage-dir $(CONFORMANCE_OUT)/v8-coverage --out $(CONFORMANCE_OUT)/ts-coverage-reconciliation.json

conformance-py:
	PYTHONPATH=$(PWD)/external/ipfs_datasets $(PYTHON) external/ipfs_datasets/ipfs_datasets_py/logic/conformance/py_reference_runner.py --vectors $(CONFORMANCE_DIR)/vectors --out $(CONFORMANCE_OUT)/py-results.json --require-engines z3_runtime,tdfol_core,dcec_prover

conformance-compare: conformance-ts conformance-py
	node $(CONFORMANCE_DIR)/compare.mjs --python $(CONFORMANCE_OUT)/py-results.json --ts $(CONFORMANCE_OUT)/ts-results.json --vectors $(CONFORMANCE_DIR)/vectors --out-dir $(CONFORMANCE_OUT) --threshold $(CONFORMANCE_THRESHOLD)

conformance-temporal-native:
	cd swissknife && npx jest test/mcp-plus-plus/mcp-remote-deontic-engine.test.ts test/mcp-plus-plus/wasm-prover-sprint10.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-browser-purity:
	cd swissknife && npx jest test/mcp-plus-plus/wasm-prover-browser-purity.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-zkp-real-browser:
	node $(CONFORMANCE_DIR)/zkp_real_backend_gate.mjs --root $(PWD) --out-dir $(CONFORMANCE_OUT) --fail-on-gap

conformance-groth16-semantic-circuit:
	cd swissknife && npx jest test/mcp-plus-plus/wasm-prover-browser-groth16-semantic.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-python-deprecation:
	node $(CONFORMANCE_DIR)/python_deprecation_gate.mjs --root $(PWD) --out-dir $(CONFORMANCE_OUT) --fail-on-gap

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

conformance-modal-codec-guidance-crosslang:
	cd swissknife && npx jest test/conformance/modal-codec-guidance-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-modal-codec-citation-crosslang:
	cd swissknife && npx jest test/conformance/modal-codec-citation-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-modal-codec-temporal-operator-crosslang:
	cd swissknife && npx jest test/conformance/modal-codec-temporal-operator-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-modal-codec-guidance-summary-crosslang:
	cd swissknife && npx jest test/conformance/modal-codec-guidance-summary-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-modal-codec-stable-embedding-crosslang:
	cd swissknife && npx jest test/conformance/modal-codec-stable-embedding-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-modal-decompiler-crosslang:
	cd swissknife && npx jest test/conformance/modal-decompiler-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-modal-decompiler-citation-crosslang:
	cd swissknife && npx jest test/conformance/modal-decompiler-citation-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-modal-decompiler-temporal-operator-crosslang:
	cd swissknife && npx jest test/conformance/modal-decompiler-temporal-operator-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-parser-utils-crosslang:
	cd swissknife && npx jest test/conformance/deontic-parser-utils-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-parser-elements-crosslang:
	cd swissknife && npx jest test/conformance/deontic-parser-elements-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-formula-builder-crosslang:
	cd swissknife && npx jest test/conformance/deontic-formula-builder-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-tdfol-native-crosslang:
	cd swissknife && npx jest test/conformance/tdfol-native-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-modal-compiler-family-token-crosslang:
	cd swissknife && npx jest test/conformance/modal-compiler-family-token-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-modal-compiler-serialization-crosslang:
	cd swissknife && npx jest test/conformance/modal-compiler-serialization-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-modal-compiler-ambiguity-policy-crosslang:
	cd swissknife && npx jest test/conformance/modal-compiler-ambiguity-policy-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-modal-compiler-formula-ambiguity-crosslang:
	cd swissknife && npx jest test/conformance/modal-compiler-formula-ambiguity-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-modal-compiler-regex-compile-crosslang:
	cd swissknife && npx jest test/conformance/modal-compiler-regex-compile-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

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

conformance-deontic-bridge-json-guidance-crosslang:
	cd swissknife && npx jest test/conformance/deontic-bridge-json-guidance-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-bridge-guidance-route-crosslang:
	cd swissknife && npx jest test/conformance/deontic-bridge-guidance-route-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-deontic-bridge-frame-graph-crosslang:
	cd swissknife && npx jest test/conformance/deontic-bridge-frame-graph-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-bridge-frame-graph-crosslang:
	cd swissknife && npx jest test/conformance/bridge-frame-graph-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-multiview-merge-crosslang:
	cd swissknife && npx jest test/conformance/multiview-merge-crosslang-conformance.test.ts --config config/jest/jest.config.cjs --runInBand

conformance-mutate:
	node $(CONFORMANCE_DIR)/mutate.mjs --vectors $(CONFORMANCE_DIR)/vectors --out $(CONFORMANCE_OUT)/mutated-vectors.json

conformance-mutation-gate:
	node $(CONFORMANCE_DIR)/mutation_gate.mjs --root $(PWD) --vectors $(CONFORMANCE_DIR)/vectors --out-dir $(CONFORMANCE_OUT)

conformance-differential-fuzz:
	node $(CONFORMANCE_DIR)/differential_fuzz.mjs --root $(PWD) --out-dir $(CONFORMANCE_OUT) --cases-per-engine 20 --seed 1337

conformance-self-containment: conformance-py
	cd swissknife && SWISSKNIFE_CONFORMANCE_STRICT_SELF_CONTAINMENT=1 npx tsx test/conformance/ts-conformance-runner.cli.ts --live-z3 --strict-self-containment --vectors ../$(CONFORMANCE_DIR)/vectors --out ../$(CONFORMANCE_OUT)/ts-results-self-contained.json
	node $(CONFORMANCE_DIR)/compare.mjs --strict-self-containment --python $(CONFORMANCE_OUT)/py-results.json --ts $(CONFORMANCE_OUT)/ts-results-self-contained.json --vectors $(CONFORMANCE_DIR)/vectors --out-dir $(CONFORMANCE_OUT)/self-contained
	node $(CONFORMANCE_DIR)/self_containment_gate.mjs --strict --out-dir $(CONFORMANCE_OUT) --ts-results $(CONFORMANCE_OUT)/ts-results-self-contained.json --report $(CONFORMANCE_OUT)/self-contained/report.json --py-results $(CONFORMANCE_OUT)/py-results.json

conformance-self-containment-strict:
	node $(CONFORMANCE_DIR)/self_containment_gate.mjs --out-dir $(CONFORMANCE_OUT) --ts-results $(CONFORMANCE_OUT)/ts-results.json --report $(CONFORMANCE_OUT)/report.json --strict

conformance-port239-host-native:
	node $(CONFORMANCE_DIR)/port239_host_native_gate.mjs --out-dir $(CONFORMANCE_OUT) --symbol-map $(CONFORMANCE_DIR)/symbol-map.json

conformance-substance:
	node $(CONFORMANCE_DIR)/substance_gate.mjs --audit implementation_plan/port-audit/port-substance.json --substance-map $(CONFORMANCE_DIR)/substance-map.json --evidence-map $(CONFORMANCE_DIR)/symbol-evidence.json --out $(CONFORMANCE_OUT)/port-substance-gate.json

# Behavioral certificate needs compare report.json/py-results, self-containment
# gate, and the PORT-239/substance classification artifacts.
conformance-behavioral-certificate: conformance-compare conformance-self-containment conformance-mutation-gate conformance-differential-fuzz conformance-port239-host-native conformance-substance
	node $(CONFORMANCE_DIR)/behavioral_certificate.mjs --out-dir $(CONFORMANCE_OUT) --parity-threshold $(CONFORMANCE_THRESHOLD)

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

# IPFS Accelerate Comprehensive Gap And Improvement Plan (Current State, 2026-06-30)

Status: Post-serving-hardening refresh
Scope: external/ipfs_accelerate/ipfs_accelerate_py model server, containerizer, API endpoint multiplexer, Kubernetes backend, and agent orchestrator, with explicit ipfs_datasets_py and ipfs_kit_py call contracts

## 1. Executive Summary

The submodule is in substantially better shape than earlier snapshots: canonical inference routing, lifecycle failure-path coverage, model usage linkage, orchestrator workflow provenance, container provenance fallback, backend-manager routing observability, and Kubernetes failure diagnostics are now implemented and test-gated.

No open high-priority serving gaps remain in the current runtime slices; the remaining work is primarily contract expansion and CI automation rather than core runtime correctness.

## 2. Confirmed Current State (Implemented)

Implemented and validated by current tests:
1. HF model server inference routes execute through backend manager and emit persistence/provenance side effects.
2. HF model load/unload routes flow through model manager lifecycle and emit datasets events.
3. Failure paths now emit datasets/provenance events for:
- inference_failed
- model_load_failed
- model_unload_failed
4. Worker/backend-manager preferred type normalization supports string aliases.
5. Kubernetes backend now includes structured failure diagnostics metadata and contract tests.

Representative validation suites:
1. external/ipfs_accelerate/test/test_hf_model_server_endpoint_contract.py
2. external/ipfs_accelerate/test/api/test_serving_call_matrix_enforcement.py
3. external/ipfs_accelerate/test/test_kubernetes_backend.py
4. external/ipfs_accelerate/test/api/test_serving_readiness_contracts.py

## 3. Gap Register (Current)

### P0: Release-Blocking Integration Gaps

No open P0 gaps remain in the current serving/usage linkage path. Model usage linkage is now wired from HF inference completion into model manager state and datasets provenance.

### P1: High-Priority Hardening Gaps

#### P1-1. Orchestrator workflow event provenance is now emitted consistently

Where:
1. external/ipfs_accelerate/ipfs_accelerate_py/p2p_tasks/orchestrator.py

Implemented:
1. _log_workflow_event(...) now calls datasets log_event and track_provenance.
2. Regression coverage added in external/ipfs_accelerate/test/api/test_task_orchestrator_lineage.py.

#### P1-2. Container provenance fallback is now consistent without provenance logger

Where:
1. external/ipfs_accelerate/ipfs_accelerate_py/docker_executor.py
2. external/ipfs_accelerate/ipfs_accelerate_py/container_backends/kubernetes/kubernetes.py

Implemented:
1. DockerExecutor and KubernetesBackend now call datasets_manager.track_provenance(...) when provenance_logger is unavailable or fails.
2. Regression coverage added in external/ipfs_accelerate/test/test_docker_executor_persistence_contract.py and external/ipfs_accelerate/test/test_kubernetes_backend.py.

#### P1-3. Backend manager routing failure observability is now explicit

Implemented:
1. `_execute_via_backend_manager()` emits `workflow_task_failed_backend_routing` on backend-manager exceptions.
2. `_execute_task_payload()` emits the same event before fail-closed strict errors.
3. Regression coverage added in `external/ipfs_accelerate/test/api/test_task_worker_backend_manager_required.py`.

### P2: Medium Priority Quality and Coverage Gaps

#### P2-1. Call-matrix coverage for model usage-link event contract is now implemented

Where:
1. external/ipfs_accelerate/test/api/test_serving_call_matrix_enforcement.py

Implemented:
1. Successful inference now drives model usage linkage emission through `ModelManager.mark_model_used(...)`.
2. The call-matrix suite asserts payload keys: model_id, run_id, inference_cid, and the datasets usage-link event.

#### P2-2. Call-matrix now enforces strict backend-routing failure observability

Where:
1. external/ipfs_accelerate/test/api/test_serving_call_matrix_enforcement.py

Implemented:
1. Strict worker backend-manager routing failures are now asserted to emit `workflow_task_failed_backend_routing` for both audit and provenance paths.
2. Readiness evidence now includes the worker routing-failure observability gate.

#### P2-3. Workflow dispatch contract tests enforce provenance parity

#### P2-4. CI contract gate automation is now in place for serving readiness/call-matrix suites

Where:
1. external/ipfs_accelerate/.github/workflows/serving-contract-gates.yml
2. external/ipfs_accelerate/scripts/validation/run_serving_contract_gates.sh

Implemented:
1. Added a dedicated CI workflow that runs on push/PR path changes and on manual dispatch.
2. Added a reusable script that runs readiness + call-matrix + strict worker backend-manager routing suites.
3. Local execution of the new script is green (`17 passed`).

Where:
1. external/ipfs_accelerate/test/api/test_task_orchestrator_lineage.py
2. external/ipfs_accelerate/test/api/test_serving_readiness_contracts.py

Implemented:
1. Workflow dispatch and completion lineage coverage now asserts both log_event and track_provenance.

## 4. Required ipfs_accelerate_py -> ipfs_datasets_py / ipfs_kit_py Call Matrix

## 4.1 Inference Success

Required call sequence:
1. InferenceBackendManager.execute_task(...)
2. IPFSKitStorage.store(input payload) -> input_cid
3. IPFSKitStorage.store(output payload) -> output_cid
4. DatasetsManager.log_event("inference_completed", payload)
5. DatasetsManager.track_provenance("inference", payload) -> provenance_cid
6. ModelManager.mark_model_used(model_id, inference_cid=output_cid, run_id=run_id)
7. DatasetsManager.log_event("model_inference_linked", usage_payload)
8. DatasetsManager.track_provenance("model_usage", usage_payload)

## 4.2 Inference Failure

Required call sequence:
1. IPFSKitStorage.store(failure payload) (best effort)
2. DatasetsManager.log_event("inference_failed", payload)
3. DatasetsManager.track_provenance("inference_failed", payload)

## 4.3 Model Load

Required call sequence:
1. ModelManager.add_model_with_ipfs_storage(...)
2. IPFSKitStorage.store(model/config/tokenizer/artifact)
3. DatasetsManager.log_event("model_loaded", payload)
4. DatasetsManager.track_provenance("model_load", payload)

## 4.4 Model Unload

Required call sequence:
1. ModelManager.remove_model(model_id)
2. DatasetsManager.log_event("model_unloaded", payload)
3. DatasetsManager.track_provenance("model_unload", payload)

## 4.5 Model Lifecycle Failures

Required call sequence:
1. DatasetsManager.log_event("model_load_failed" or "model_unload_failed", payload)
2. DatasetsManager.track_provenance("model_load_failed" or "model_unload_failed", payload)

## 4.6 Container Execution Success/Failure (Docker and Kubernetes)

Required call sequence:
1. Optional IPFSKitStorage.retrieve(model_artifact_cid)
2. Execute container/job
3. IPFSKitStorage.store(execution artifact payload) -> output_cid
4. DatasetsManager.log_event("container_execution_completed" or "container_execution_failed", payload)
5. Provenance source order:
- ProvenanceLogger.log_transformation(...)
- fallback DatasetsManager.track_provenance(...)

## 4.7 Orchestrator Workflow Events

Required call sequence:
1. DatasetsManager.log_event("workflow_dispatched", payload)
2. DatasetsManager.track_provenance("workflow_dispatched", payload)
3. Worker emits completion/failure:
- DatasetsManager.log_event("workflow_task_completed" or "workflow_task_failed", payload)
- DatasetsManager.track_provenance(same operation, payload)

## 5. Phased Improvement Plan

## Phase A (P1, 1-2 days): Worker/Orchestrator Observability Integrity

Status: Completed (2026-06-30)

Tasks:
1. Fix the undefined symbol path in `p2p_tasks/worker.py::_emit_backend_routing_failure` where `manager.track_provenance(event_type, payload)` references `event_type` out of scope.
2. Replace that call with deterministic provenance operations for routing failures (`workflow_task_failed_backend_routing`) and optional-routing degraded warnings.
3. Add dedicated test assertions for optional backend-manager fallback observability (non-strict routing).

Acceptance Criteria:
1. No undefined-name path exists in routing-failure observability code.
2. Strict failures emit ERROR audit + provenance under `workflow_task_failed_backend_routing`.
3. Optional fallback emits WARN audit + provenance under a distinct degraded event name.
4. Tests pass:
- external/ipfs_accelerate/test/api/test_task_worker_backend_manager_required.py
- external/ipfs_accelerate/test/api/test_task_worker_backend_manager_routing.py
- external/ipfs_accelerate/test/api/test_serving_call_matrix_enforcement.py

Validation evidence:
1. Focused suite run is green after implementation (`15 passed`):
- `external/ipfs_accelerate/test/api/test_task_worker_backend_manager_required.py`
- `external/ipfs_accelerate/test/api/test_task_worker_backend_manager_routing.py`
- `external/ipfs_accelerate/test/api/test_serving_call_matrix_enforcement.py`

## Phase B (P1, 1-2 days): Model Lifecycle API Surface Completeness

Status: Completed (2026-06-30)

Tasks:
1. Extend model lifecycle response schemas to include persistence/provenance metadata (`artifact_cid`, `model_cid`, `config_cid`, `tokenizer_cid`, `provenance_cid` where available).
2. Ensure `/models/load` and `/models/unload` responses expose the same canonical lineage fields emitted in datasets events.
3. Add response contract tests for lifecycle metadata fields.

Acceptance Criteria:
1. Lifecycle endpoint responses expose storage/provenance identifiers rather than only free-form messages.
2. Response fields match emitted datasets payload semantics.
3. Tests pass:
- external/ipfs_accelerate/test/test_hf_model_server_endpoint_contract.py
- external/ipfs_accelerate/test/api/test_serving_call_matrix_enforcement.py

Validation evidence:
1. Lifecycle schemas now include `artifact_cid`, `model_cid`, `config_cid`, `tokenizer_cid`, `provenance_cid`.
2. `/models/load` and `/models/unload` now return lineage identifiers aligned with datasets lifecycle payloads.
3. Focused suite run is green after implementation (`25 passed`):
- `external/ipfs_accelerate/test/test_hf_model_server_endpoint_contract.py`
- `external/ipfs_accelerate/test/api/test_serving_call_matrix_enforcement.py`
- `external/ipfs_accelerate/test/api/test_serving_readiness_contracts.py`

## Phase C (P2, 2-3 days): Container Artifact Materialization Policy Hardening

Status: Completed (2026-06-30)

Tasks:
1. Add explicit artifact materialization policy controls for Docker/Kubernetes (`optional`, `required`).
2. For `required`, fail execution fast when `model_artifact_cid` retrieval fails.
3. For `optional`, emit deterministic degraded events and provenance records that include retrieval error details.
4. Add parity tests for Docker and Kubernetes policy behavior.

Acceptance Criteria:
1. Artifact retrieval behavior is deterministic and policy-driven in both backends.
2. Missing artifact retrieval cannot silently proceed under strict policy.
3. Degraded execution paths remain observable under optional policy.
4. Tests pass:
- external/ipfs_accelerate/test/test_docker_executor_persistence_contract.py
- external/ipfs_accelerate/test/test_kubernetes_backend.py
- external/ipfs_accelerate/test/api/test_serving_call_matrix_enforcement.py

Validation evidence:
1. Added `model_artifact_policy` to Docker and Kubernetes execution configs.
2. `required` policy now fails fast on retrieval failure in both backends.
3. `optional` policy now emits deterministic degraded observability events/provenance.
4. Focused suite run is green after implementation (`32 passed`):
- `external/ipfs_accelerate/test/test_docker_executor_persistence_contract.py`
- `external/ipfs_accelerate/test/test_kubernetes_backend.py`
- `external/ipfs_accelerate/test/api/test_serving_call_matrix_enforcement.py`
- `external/ipfs_accelerate/test/api/test_serving_readiness_contracts.py`

## Phase D (P2, 1-2 days): End-To-End Call Chain Contract Expansion

Tasks:
1. Add one end-to-end serving contract test covering call order across backend manager, storage, datasets audit, and provenance linkage.
2. Gate ordering for core inference success path: `execute_task -> store -> log_event -> track_provenance -> mark_model_used`.
3. Add failure-path ordering assertions for inference and model lifecycle failures.

Acceptance Criteria:
1. Ordering regressions are caught by CI before merge.
2. The call chain is validated with deterministic fakes/mocks rather than brittle timing assumptions.
3. Tests pass in existing serving contract workflow:
- external/ipfs_accelerate/.github/workflows/serving-contract-gates.yml

## 6. Immediate Low-Risk Quick Wins

1. Patch `p2p_tasks/worker.py::_emit_backend_routing_failure` to remove out-of-scope `event_type` reference.
2. Add `artifact_cid` and provenance-identifying fields to load/unload response schemas.
3. Add policy flag plumbing for artifact retrieval strictness in Docker/Kubernetes execution configs.
4. Add one focused E2E call-order test for inference success.

## 7. Definition Of Done

Done when all are true:
1. Every canonical path (inference, model lifecycle, container execution, workflow orchestration) emits both audit and provenance records, including failures.
2. Model manager usage metadata is updated by live inference and queryable via normalized event contracts.
3. Container backends enforce policy-driven artifact materialization semantics with deterministic observability.
4. API lifecycle responses expose storage/provenance lineage identifiers needed by downstream consumers.
5. Call-matrix and E2E ordering tests enforce these contracts and readiness artifacts reflect them.

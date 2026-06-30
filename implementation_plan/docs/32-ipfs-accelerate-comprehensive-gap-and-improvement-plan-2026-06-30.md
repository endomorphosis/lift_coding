# IPFS Accelerate Comprehensive Gap And Improvement Plan (2026-06-30)

Status: Updated from current workspace state after readiness contracts, benchmarks, and release evidence were added
Scope: `external/ipfs_accelerate/ipfs_accelerate_py` model server, containerizer, API endpoint multiplexer, Kubernetes cluster manager, and agent orchestrator, with explicit contract calls into `ipfs_kit_py` and `ipfs_datasets_py`

## 1. Executive Summary

`ipfs_accelerate_py` now has passing readiness and benchmark gates and a machine-readable readiness report, but there are still important productization gaps before this can be treated as fully hardened production serving infrastructure.

What is now validated:
- Readiness contracts pass for backend-manager recording, model registry roundtrip, capability registry durability, container envelope parity, and worker/orchestrator lineage.
- Benchmark contracts pass for backend throughput, persistence latency, failover reselection latency, and backlog drain latency.
- A single release evidence artifact exists.

Primary unresolved themes:
- Canonical runtime surface freeze and non-canonical tree exclusion are not fully completed.
- Cross-library call order and execution record schema are not yet published as an enforced contract artifact.
- Model registry lineage/version and run-linkage fields are still incomplete.
- Kubernetes model artifact fetch/mount and event parity with Docker are still partial.
- Backend routing metadata exposure is still missing protocol/hardware placement depth.

## 2. Current Baseline (Confirmed)

Canonical subsystem surfaces in active use:
- Model server/service: `unified_inference_service.py`, `hf_model_server/server.py`
- API endpoint multiplexer: `inference_backend_manager.py`
- Containerizer: `docker_executor.py`
- Kubernetes backend: `container_backends/kubernetes/kubernetes.py`
- Agent orchestration: `p2p_tasks/orchestrator.py`, `p2p_tasks/worker.py`
- Model registry: `model_manager.py`

Validation surfaces now present:
- Readiness contracts: `external/ipfs_accelerate/test/api/test_serving_readiness_contracts.py`
- Benchmark contracts: `external/ipfs_accelerate/test/api/test_serving_benchmark_contracts.py`
- Evidence artifact: `implementation_plan/docs/31-ipfs-accelerate-model-serving-readiness-report.json`

## 3. Subsystem Gap Analysis And Required Improvements

### 3.1 Model Server

Current strengths:
- Service-level result recorder exists and can persist input/output and provenance metadata.
- Backend-manager finalize seam exists and can attach execution metadata.

Remaining gaps:
- Not all serving ingress paths are provably forced through one canonical completion path.
- Lifecycle event coverage for model load/start/failure is not yet uniformly enforced.

Required improvements:
1. Route every inference completion through `InferenceBackendManager.finalize_inference_result(...)`.
2. Enforce required storage/audit/provenance fields in the server response envelope.
3. Add explicit failure-path storage/provenance behavior parity with success paths.

### 3.2 Containerizer (Docker)

Current strengths:
- Docker execution persistence and provenance hooks are implemented.
- Result envelope includes `output_cid` and `provenance_cid`.

Remaining gaps:
- Artifact materialization by CID before execution is not guaranteed for all container workflows.
- Container output schema parity contract with Kubernetes is only partially formalized.

Required improvements:
1. Add/require model artifact prefetch via CID (`IPFSKitStorage.retrieve(...)`) when model CID is provided.
2. Standardize one shared execution envelope type for Docker and Kubernetes.
3. Ensure failure logs and error metadata are persisted identically to success artifacts.

### 3.3 API Endpoint Multiplexer

Current strengths:
- Durable backend registry persistence/rehydration exists.
- Stale pruning and selection reason recording exist.
- Executable `execute_task(...)` path exists.

Remaining gaps:
- Run records still do not always include full protocol and hardware placement metadata.
- Debug/status surfaces are not yet guaranteed to expose full routing context.

Required improvements:
1. Extend run metadata to include `protocol`, `hardware_type`, `placement_node`, and endpoint identity.
2. Expose routing metadata through one stable debugging/reporting API.
3. Add contract test coverage asserting full routing metadata presence.

### 3.4 Kubernetes Cluster Manager

Current strengths:
- Minimal backend exists with spec generation, submission, polling, and result collection.
- Docker-compatible envelope fields are present.

Remaining gaps:
- Model artifact fetch/mount strategy is still TODO.
- Event/audit/provenance integration parity with Docker is not complete.

Required improvements:
1. Implement model artifact pull/mount from CID-backed storage before execution.
2. Add datasets audit/provenance hooks equivalent to Docker executor semantics.
3. Expand status/event capture to include job placement and failure reasons in canonical envelope metadata.

### 3.5 Agent Orchestrator

Current strengths:
- Inference routing through backend-manager path is implemented.
- Fail-closed policy exists for strict lineage/persistence requirements.
- Capability registry persistence and placement scoring are implemented.

Remaining gaps:
- Local/mesh task completion metadata normalization can still diverge by failure mode.
- Workflow event/audit enforcement is currently best-effort in optional integration paths.

Required improvements:
1. Enforce one normalized task-result lineage envelope for success/failure/cancel.
2. Make workflow dispatch/completion/failure event logging required when datasets integration is enabled.
3. Add guardrails so proxy/mesh paths cannot skip canonical finalization semantics.

### 3.6 Model Manager And Registry Metadata

Current strengths:
- CID fields for model/config/tokenizer are implemented.
- Artifact store/reconcile/restore flow exists.
- Audit/provenance hooks for registration/load are present.

Remaining gaps:
- Model revision/version lineage fields are still missing.
- Last-used and inference run linkage fields are still missing.

Required improvements:
1. Add revision lineage fields (`parent_model_id`, `revision_id`, `revision_created_at`).
2. Add usage linkage fields (`last_used_at`, `last_run_id`, `inference_count`).
3. Add tests proving linkage updates on inference completion.

## 4. Required Cross-Library Call Contract (Authoritative)

## 4.1 Inference Completion Path

Owner: model server + backend manager

Required call order:
1. Optional input persistence: `IPFSKitStorage.store(input_payload, filename=...) -> input_cid`
2. Output persistence: `IPFSKitStorage.store(output_payload, filename=...) -> output_cid`
3. Audit event: `DatasetsManager.log_event("inference_completed"|"inference_failed", payload, ...)`
4. Provenance event: `DatasetsManager.track_provenance("inference", payload)`
5. Finalize response metadata via `InferenceBackendManager.finalize_inference_result(...)`

Required payload keys:
- `run_id`, `task`, `model`, `model_cid`, `backend_id`, `backend_type`, `endpoint`
- `protocol`, `hardware_type`, `placement_node`
- `input_cid`, `output_cid`, `provenance_cid`
- `status`, `duration_ms`, `error` (when failed)

## 4.2 Model Registration And Restore Path

Owner: model manager

Required call order:
1. Store artifacts: `IPFSKitStorage.store(model/config/tokenizer)`
2. Log registration: `DatasetsManager.log_event("model_registered", payload, ...)`
3. Track provenance: `DatasetsManager.track_provenance("model_registration", payload)`
4. Persist metadata fields and revision linkage in registry
5. Restore by CID when requested: `IPFSKitStorage.retrieve(cid)`

Required payload keys:
- `model_id`, `model_name`, `model_version`, `revision_id`, `parent_model_id`
- `model_cid`, `config_cid`, `tokenizer_cid`
- `created_at`, `source_uri`, `storage_backend`, `provenance_cid`

## 4.3 Container Execution Path (Docker + Kubernetes)

Owner: docker executor + kubernetes backend

Required call order:
1. Optional model materialization: `IPFSKitStorage.retrieve(model_cid)`
2. Execute workload
3. Persist outputs/logs: `IPFSKitStorage.store(stdout/stderr/artifacts)`
4. Log event: `DatasetsManager.log_event("container_execution_completed"|"container_execution_failed", payload, ...)`
5. Track provenance: `ProvenanceLogger.log_transformation(...)` or datasets provenance equivalent

Required payload keys:
- `execution_id`, `image`, `command`, `namespace`/`node_name`
- `stdout_cid`, `stderr_cid`, `output_cid`, `provenance_cid`
- `exit_code`, `status`, `execution_time_ms`

## 4.4 Orchestrator Task Lifecycle Path

Owner: orchestrator + worker

Required call order:
1. Claim task and attach lineage (`workflow_id`, `task_id`, `model_id`, policies)
2. Route execution through backend manager for inference types
3. Finalize result through canonical storage/provenance seam
4. Persist workflow/task audit and provenance events

Required payload keys:
- `workflow_id`, `task_id`, `backend_id`, `model_id`
- `output_cid`, `provenance_cid`, `status`, `error`
- `peer_id`, `orchestrator_id`, `dispatch_ts`, `completion_ts`

## 5. Implementation Roadmap (Remaining Work Only)

### Phase R1: Canonical Surface Freeze And Contract Publication (1-2 days)
1. Complete Milestone A items in the board.
2. Publish one integration contract doc containing required envelope schema and call order.
3. Add a hygiene test blocking canonical runtime imports from legacy/backup trees.

### Phase R2: Metadata Completeness Hardening (2-3 days)
1. Complete Milestone C1 lineage/version and usage-linkage fields.
2. Complete Milestone D2 full routing metadata coverage.
3. Add contract tests for new required metadata keys.

### Phase R3: Kubernetes And Container Parity Completion (3-5 days)
1. Complete Milestone E1 artifact fetch/mount and event/error parity items.
2. Complete Milestone E2 shared envelope + persistence parity behavior.
3. Add parity contracts asserting identical metadata behavior across Docker/Kubernetes.

### Phase R4: Final Contract Enforcement And CI Wiring (2-3 days)
1. Make readiness and benchmark suites mandatory CI gates.
2. Ensure evidence report generation is automated and attached to release notes/CI artifacts.
3. Add regression gates for call-contract drift across model server/container/orchestrator paths.

## 6. Acceptance Criteria (Go/No-Go)

No-go if any are true:
- Any canonical inference path can return without `output_cid` and provenance metadata.
- Kubernetes execution path cannot materialize model artifacts by CID when required.
- Backend/run records do not include backend identity plus protocol/hardware placement metadata.
- Model registry cannot map model revisions and inference linkage.

Go when all are true:
- Cross-library call contract is documented, enforced, and test-backed.
- Docker and Kubernetes exhibit metadata and persistence parity.
- Orchestrated and direct inference paths both produce canonical lineage records.
- Readiness report is regenerated automatically with passing contract and benchmark gates.

## 7. Suggested Immediate Next 5 Tasks

1. Complete Milestone A1/A2/A3 in the board with one contract spec document.
2. Implement model revision + usage-linkage fields in `model_manager.py` and tests.
3. Implement Kubernetes model artifact materialization via CID and parity event hooks.
4. Extend backend manager run metadata with protocol/hardware placement and add contract tests.
5. Wire readiness report generation into CI so H3 is automated, not manual.

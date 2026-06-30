# IPFS Accelerate Model Serving Task Board

Status: In Progress
Scope: `external/ipfs_accelerate/ipfs_accelerate_py` model server, containerizer, API endpoint multiplexer, Kubernetes cluster manager, and agent orchestration, with explicit integration contracts to `ipfs_datasets_py` and `ipfs_kit_py`

## Milestone A: Canonical Runtime And Surface Freeze

### A1. Lock canonical serving entrypoints
- [ ] Declare `hf_model_server/server.py` and `unified_inference_service.py` as the authoritative model-serving runtime
- [ ] Declare `inference_backend_manager.py` as the authoritative endpoint multiplexer
- [ ] Declare `docker_executor.py` as the authoritative local containerizer
- [ ] Declare `p2p_tasks/orchestrator.py` and `workflow_manager.py` as the authoritative orchestration path
- [ ] Mark `ipfs_accelerate_py_legacy.py`, `backup/`, `archive/`, `reorganization_backup*`, and mirrored nested submodules as non-canonical

Definition of done:
- Contributors have one runtime path per subsystem
- Backup and mirrored trees are excluded from production planning and release gates

### A2. Publish serving integration contract
- [ ] Standardize one execution record shape for model registration, model load, inference start, inference completion, inference failure, workflow dispatch, and container completion
- [ ] Standardize required fields for model artifact metadata, inference run metadata, backend registry entries, and orchestration lineage
- [ ] Document required call order into `ipfs_kit_py` and `ipfs_datasets_py`

Definition of done:
- Contract is written down and referenced by tests
- No ambiguity remains around required persistence and provenance side effects

### A3. Cross-library call matrix
- [ ] Model server calls `InferenceBackendManager.finalize_inference_result(...)` for every completed inference
- [ ] Model server and service layer call `IPFSKitStorage.store(...)` for inference outputs before completion metadata is finalized
- [ ] Model server and service layer call `DatasetsManager.log_event(...)` and `DatasetsManager.track_provenance(...)` for model load and inference lifecycle events
- [ ] Containerizer calls `IPFSKitStorage.retrieve(...)` to materialize model artifacts by CID before execution
- [ ] Containerizer calls `IPFSKitStorage.store(...)` for stdout/stderr/artifacts on completion
- [ ] Backend manager records backend selection metadata and result finalization metadata for every task
- [ ] Orchestrator routes execution only through `InferenceBackendManager.execute_task(...)`
- [ ] Model manager keeps model metadata, artifact CIDs, and usage linkage in sync with `DatasetsManager`

Definition of done:
- Every subsystem has an explicit required call sequence into `ipfs_kit_py` and `ipfs_datasets_py`
- Implementation slices can be validated independently against the call matrix

## Milestone B: Inference Result Persistence And Provenance

### B1. Add canonical inference completion persistence hook
- [ ] Persist inference outputs via `IPFSKitStorage.store(...)`
- [ ] Optionally persist large or reusable inputs via `IPFSKitStorage.store(...)`
- [ ] Emit `output_cid` and `input_cid` in canonical response metadata
- [ ] Record inference success/failure audit events via `DatasetsManager.log_event(...)`
- [ ] Record inference provenance via `DatasetsManager.track_provenance(...)`

Progress note:
- First slice implemented in `ipfs_accelerate_py/mcp/tools/inference.py` with focused contract coverage in `ipfs_accelerate_py/mcp/tests/test_inference_persistence_contract.py`.
- Second slice implemented in `ipfs_accelerate_py/unified_inference_service.py` and `ipfs_accelerate_py/inference_backend_manager.py`, adding a canonical service-level result recorder and backend-manager completion seam with focused coverage in `external/ipfs_accelerate/test/test_unified_inference.py`.
- Third slice implemented in `ipfs_accelerate_py/inference_backend_manager.py`, adding an executable `execute_task(...)` path that selects a backend, invokes it, records metrics, and finalizes the result through the canonical persistence/provenance recorder.
- Fourth slice implemented in `ipfs_accelerate_py/api_backends/hf_tgi.py`, adding a production-facing `run_inference(...)` adapter entrypoint with focused normalization coverage in `external/ipfs_accelerate/test/test_hf_tgi_run_inference_contract.py`.
- Fifth slice implemented in `ipfs_accelerate_py/api_backends/hf_tei.py`, adding a production-facing embedding `run_inference(...)` adapter entrypoint plus optional-NumPy fallback behavior, with focused coverage in `external/ipfs_accelerate/test/test_hf_tei_run_inference_contract.py` and `external/ipfs_accelerate/test/test_unified_inference.py`.

Definition of done:
- No canonical inference path completes without stored output CID and provenance metadata

### B2. Add container execution persistence hook
- [x] Persist material container outputs via `IPFSKitStorage`
- [x] Record execution metadata including image, node, timing, and output CID
- [x] Record success/failure provenance for Docker-backed inference runs

Progress note:
- Container execution persistence is now implemented in `ipfs_accelerate_py/docker_executor.py` with optional `IPFSKitStorage`, `DatasetsManager`, and provenance logger hooks, and is covered by `external/ipfs_accelerate/test/test_docker_executor_persistence_contract.py`. Kubernetes now mirrors the same result envelope fields in `ipfs_accelerate_py/container_backends/kubernetes/kubernetes.py`.

Definition of done:
- Docker execution produces the same lineage guarantees as direct inference execution

## Milestone C: Model Registry And Artifact Lineage

### C1. Extend model metadata schema
- [x] Add `model_cid` field
- [x] Add `config_cid` field
- [x] Add `tokenizer_cid` field
- [ ] Add lineage/version fields for model revisions
- [ ] Add last-used and inference-run linkage fields

Definition of done:
- Model registry can answer where artifacts live and what inference runs used them

### C2. Add artifact registration flow
- [x] Persist model artifacts through `IPFSKitStorage`
- [x] Reconcile local model metadata with stored CIDs
- [x] Record audit and provenance events for model registration/load
- [x] Add restore path from CID-backed artifacts to runnable local assets

Progress note:
- Milestone C first slice implemented in `ipfs_accelerate_py/model_manager.py`, adding CID-backed artifact fields, an `IPFSKitStorage`-powered registration flow for model/config/tokenizer assets, a CID restore helper for local reconstruction, audit/provenance hooks for registration and access, and JSON persistence coverage in `external/ipfs_accelerate/test/test_model_manager_ipfs_storage_contract.py`.

Definition of done:
- Model registration is content-addressed, auditable, and recoverable

## Milestone D: Backend Registry And API Multiplexer Durability

### D1. Persist backend registry state
- [x] Add durable storage for `BackendInfo` records
- [x] Persist backend capabilities, endpoint URL, status, last seen, and selection metadata
- [x] Rehydrate backend registry on restart
- [x] Prune stale backend entries deterministically

Progress note:
- Milestone D first slice implemented in `ipfs_accelerate_py/inference_backend_manager.py`, adding a JSON-backed registry snapshot, rehydration on startup, persisted backend selection metadata, and deterministic stale-backend pruning with focused coverage in `external/ipfs_accelerate/test/test_unified_inference.py`.

Definition of done:
- Endpoint multiplexer has restart-safe service catalog state

### D2. Add routing decision metadata
- [x] Record backend selection reason for each inference run
- [ ] Record backend ID, backend type, endpoint, protocol, and hardware placement
- [ ] Expose this metadata in run records and debugging surfaces

Progress note:
- Milestone D now also includes persisted backend selection-reason metadata in `ipfs_accelerate_py/inference_backend_manager.py`, surfaced through status reports and covered by `external/ipfs_accelerate/test/test_unified_inference.py`.

Definition of done:
- Backend routing is explainable and queryable after the fact

## Milestone E: Kubernetes Cluster Manager Implementation

### E1. Implement minimal Kubernetes backend
- [x] Replace empty `container_backends/kubernetes/kubernetes.py` with a real implementation
- [x] Add deployment/job spec generation
- [ ] Add model artifact fetch or mount strategy
- [x] Add execution status polling and result collection
- [ ] Add event/error reporting into the same metadata envelope used by Docker

Progress note:
- Milestone E first slice implemented in `ipfs_accelerate_py/container_backends/kubernetes/kubernetes.py`, adding a minimal Kubernetes job backend with spec generation, simulated fallback execution, status polling, result collection, and a Docker-compatible result envelope. Covered by `external/ipfs_accelerate/test/test_kubernetes_backend.py`.

Definition of done:
- Kubernetes is either implemented as a real backend or explicitly marked unsupported for release

### E2. Add Docker/Kubernetes execution parity
- [ ] Define a common execution result envelope shared by Docker and Kubernetes
- [ ] Persist outputs, logs, and provenance identically across both backends
- [ ] Ensure orchestrator can target either backend through the same contract

Definition of done:
- Execution-plane differences do not change persistence or metadata behavior

## Milestone F: Orchestrator And Workflow Enforcement

### F1. Bind orchestrator to backend manager as the only dispatch seam
- [x] Route orchestrated execution through `InferenceBackendManager`
- [x] Prevent direct task completion paths from bypassing storage/provenance hooks
- [x] Carry model ID, task type, persistence policy, and provenance policy on task payloads

Progress note:
- Worker dispatch now attempts canonical backend-manager execution for inference task types in `ipfs_accelerate_py/p2p_tasks/worker.py` via `InferenceBackendManager.execute_task(...)` with safe handler fallback when no backend-manager route is available.
- Orchestrator proxy submissions in `ipfs_accelerate_py/p2p_tasks/orchestrator.py` now carry `_lineage` metadata (`workflow_id`, `task_id`, `model_id`, `persistence_policy`, `provenance_policy`) into queued local payloads.
- Focused coverage added in `external/ipfs_accelerate/test/api/test_task_worker_backend_manager_routing.py` and `external/ipfs_accelerate/test/api/test_task_orchestrator_lineage.py`.

Definition of done:
- Orchestrated work cannot bypass canonical persistence/indexing behavior

### F2. Persist task and workflow lineage
- [x] Add `workflow_id`, `task_id`, `backend_id`, `model_id`, `output_cid`, and `provenance_cid` to task result metadata
- [x] Persist failure lineage for interrupted or failed distributed tasks
- [x] Record workflow-level audit events for submission, dispatch, completion, and failure

Progress note:
- `ipfs_accelerate_py/p2p_tasks/worker.py` now enforces fail-closed routing for inference tasks when backend-manager dispatch is required by strict routing or lineage policy, preventing silent fallback bypasses.
- Worker completion paths now persist lineage metadata on failed tasks and failed mesh acknowledgements using structured failure results.
- `ipfs_accelerate_py/p2p_tasks/orchestrator.py` logs workflow dispatch events for proxy-submitted tasks, while worker completion paths emit workflow completion/failure audit/provenance events when datasets integration is available.
- Coverage: `external/ipfs_accelerate/test/api/test_task_orchestrator_lineage.py`, `external/ipfs_accelerate/test/api/test_task_worker_backend_manager_routing.py`, and `external/ipfs_accelerate/test/api/test_task_worker_backend_manager_required.py`.

Definition of done:
- Workflow and task records are auditable and traceable to stored outputs

## Milestone G: Peer Capability And Cluster Metadata

### G1. Add durable capability advertisement registry
- [x] Persist peer/node capability metadata
- [x] Track supported tasks, hardware types, loaded models, and available container images
- [x] Use registry data to improve placement decisions in backend manager and orchestrator

Progress note:
- Added persistent peer capability registry module at `ipfs_accelerate_py/p2p_tasks/capability_registry.py` with JSON durability under `~/.cache/ipfs_accelerate/peer_capability_registry.json`.
- Orchestrator now refreshes registry records from peer `status(detail=True)` responses and uses registry scoring to prioritize peer claim order in `ipfs_accelerate_py/p2p_tasks/orchestrator.py`.
- Backend manager now carries capability-registry path context in routing selection reasons via `ipfs_accelerate_py/inference_backend_manager.py`.
- Coverage: `external/ipfs_accelerate/test/api/test_peer_capability_registry.py` and `external/ipfs_accelerate/test/api/test_task_orchestrator_capability_routing.py`.

Definition of done:
- Scheduling decisions can use persisted cluster capabilities rather than transient runtime guesses

## Milestone H: Test Gates, Benchmarks, And Readiness Evidence

### H1. Add contract suites for serving/storage lineage
- [x] Inference result persistence contract suite
- [x] Model artifact registry contract suite
- [x] Backend registry durability suite
- [x] Docker/Kubernetes parity suite
- [x] Orchestrator lineage suite

Progress note:
- Added a single explicit readiness gate at `external/ipfs_accelerate/test/api/test_serving_readiness_contracts.py` that covers backend-manager result recording, model registry roundtrip persistence, peer capability registry durability, Docker/Kubernetes envelope parity, and orchestrator/worker lineage routing.

Definition of done:
- CI blocks release on serving/storage contract drift

### H2. Add performance and failover gates
- [x] Benchmark inference throughput by backend type
- [x] Benchmark persistence latency for results and artifacts
- [x] Benchmark backend failover/reselection time
- [x] Benchmark orchestration backlog drain time

Progress note:
- Added `external/ipfs_accelerate/test/api/test_serving_benchmark_contracts.py` to measure backend-manager throughput, model persistence latency, backend reselection time, and task-queue backlog drain time against the canonical serving seams.

Definition of done:
- Performance regressions and failover regressions are measurable and gated

### H3. Generate release evidence artifact
- [x] Produce a single readiness report covering contract status, benchmark results, and go/no-go state
- [x] Include storage/indexing coverage for inference and model artifacts
- [x] Attach release evidence to CI or release notes

Progress note:
- Generated the machine-readable readiness report at `implementation_plan/docs/31-ipfs-accelerate-model-serving-readiness-report.json`.

Definition of done:
- Release readiness is evidenced by one machine-readable artifact

## Recommended Execution Order

1. Milestone A
2. Milestone B
3. Milestone C
4. Milestone D
5. Milestone E
6. Milestone F
7. Milestone G
8. Milestone H

## Verification Matrix To Run After Each Milestone

- targeted tests for the touched subsystem under `external/ipfs_accelerate/test/` or `external/ipfs_accelerate/ipfs_accelerate_py/mcp/tests/`
- focused import or smoke checks for:
  - `ipfs_accelerate_py/unified_inference_service.py`
  - `ipfs_accelerate_py/inference_backend_manager.py`
  - `ipfs_accelerate_py/model_manager.py`
  - `ipfs_accelerate_py/docker_executor.py`
  - `ipfs_accelerate_py/p2p_tasks/orchestrator.py`
- contract suites added in Milestone H as they come online

## Tracking Notes

- Keep this board as the single source of truth for `ipfs_accelerate_py` serving-readiness rollout.
- Add PR links, assignees, and validation evidence under each completed task as work begins.
- Do not treat malformed legacy tests or mirrored nested submodules as release evidence.
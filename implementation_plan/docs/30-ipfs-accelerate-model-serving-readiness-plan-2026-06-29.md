# IPFS Accelerate Model Serving Readiness Improvement Plan (2026-06-29)

Status: Investigated in current workspace and grounded in current `external/ipfs_accelerate` code state
Scope: `external/ipfs_accelerate/ipfs_accelerate_py` model server, containerizer, API endpoint multiplexer, Kubernetes cluster manager, and agent orchestration, with explicit integration contracts to `ipfs_datasets_py` and `ipfs_kit_py`

## 1. Executive Summary

`ipfs_accelerate_py` has strong building blocks for inference, storage wrappers, and orchestration, but it is not yet operating as one canonical end-to-end model serving platform.

Current strengths:
- A real FastAPI model server exists in `ipfs_accelerate_py/hf_model_server/server.py`.
- A production-oriented Docker execution layer exists in `ipfs_accelerate_py/docker_executor.py`.
- A runtime backend registry and routing layer exists in `ipfs_accelerate_py/inference_backend_manager.py`.
- A task orchestration layer exists in `ipfs_accelerate_py/p2p_tasks/orchestrator.py`.
- Storage and provenance wrappers already exist through `ipfs_accelerate_py/ipfs_kit_integration.py` and `ipfs_accelerate_py/datasets_integration/manager.py`.

Primary remaining risk themes:
- No canonical persistence contract from inference execution to distributed storage and metadata indexes.
- Kubernetes backend is effectively unimplemented.
- Backend multiplexing and orchestration state are mostly runtime-only and do not persist capability, lineage, or placement decisions.
- Model metadata exists, but model artifacts, inference results, and provenance are not uniformly linked.
- Submodule contains heavy backup/test clutter that increases drift and makes canonical path selection ambiguous.

## 2. Canonical Runtime Surfaces

These are the files that should drive the plan, rather than backups or mirrored copies:

- Model server:
  - `external/ipfs_accelerate/ipfs_accelerate_py/hf_model_server/server.py`
  - `external/ipfs_accelerate/ipfs_accelerate_py/unified_inference_service.py`
- API endpoint multiplexer:
  - `external/ipfs_accelerate/ipfs_accelerate_py/inference_backend_manager.py`
  - `external/ipfs_accelerate/ipfs_accelerate_py/embeddings_router.py`
- Containerizer:
  - `external/ipfs_accelerate/ipfs_accelerate_py/docker_executor.py`
  - `external/ipfs_accelerate/ipfs_accelerate_py/container_backends/containers.py`
- Kubernetes cluster manager:
  - `external/ipfs_accelerate/ipfs_accelerate_py/container_backends/kubernetes/kubernetes.py`
  - `external/ipfs_accelerate/ipfs_accelerate_py/common/kubernetes_cache.py`
- Agent/task orchestrator:
  - `external/ipfs_accelerate/ipfs_accelerate_py/p2p_tasks/orchestrator.py`
  - `external/ipfs_accelerate/ipfs_accelerate_py/workflow_manager.py`
  - `external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/`
- Model metadata and storage integration:
  - `external/ipfs_accelerate/ipfs_accelerate_py/model_manager.py`
  - `external/ipfs_accelerate/ipfs_accelerate_py/ipfs_kit_integration.py`
  - `external/ipfs_accelerate/ipfs_accelerate_py/datasets_integration/manager.py`

Do not drive implementation from these surfaces except for migration/deletion planning:
- `ipfs_accelerate_py_legacy.py`
- `backup/`, `archive/`, `reorganization_backup*`
- malformed or legacy test scripts under `external/ipfs_accelerate/test/` that are syntactically corrupted or not import-clean
- mirrored copies of sibling submodules nested inside `external/ipfs_accelerate/ipfs_datasets_py/` and `external/ipfs_accelerate/ipfs_kit_py/`

## 3. Confirmed Baseline (What Exists Today)

Observed in code:
- `HFModelServer` supports health, readiness, auth, rate limiting, request queueing, and skill discovery.
- `InferenceBackendManager` can register backends, track health, and select backends for tasks.
- `UnifiedInferenceService` can register local HF, API, CLI, and libp2p inference backends into one manager.
- `DockerExecutor` provides container build/run primitives with security and resource controls.
- `TaskOrchestrator` can scale workers and handle mesh draining for p2p task execution.
- `WorkflowManager` persists workflows/tasks in DuckDB and exposes workflow/task metadata.
- `IPFSKitStorage` already exposes content-addressed store/retrieve/list semantics with local fallback.
- `DatasetsManager` already exposes audit logging, provenance tracking, dataset loading, and workflow submission wrappers.
- `ModelManager` already has local/DuckDB metadata storage and optional datasets/storage integration initialization.

What is notably absent from the canonical path:
- A single required write path that stores inference results, stores model artifacts, and records lineage/index metadata every time.
- A real Kubernetes cluster manager implementation.
- A persistent backend/endpoint registry that survives restart and is queryable.
- A canonical model registry entry linking model metadata to stored artifact CIDs and inference run CIDs.

## 4. Gap Analysis (Ordered by Severity)

### Critical

1. No canonical inference result persistence contract.
- `unified_inference_service.py` and `inference_backend_manager.py` manage runtime execution and registration, but do not themselves persist inference outputs through `IPFSKitStorage` or index them via `DatasetsManager`.
- Some MCP inference tooling logs provenance, but canonical service/backend code does not enforce it.
- Result: inference is not reproducible, auditable, or queryable as a distributed artifact.

2. Kubernetes cluster manager is missing.
- `container_backends/kubernetes/kubernetes.py` is empty.
- Result: “Kubernetes support” is currently a placeholder, not an implementation.

3. No canonical model artifact registry.
- `model_manager.py` stores model metadata locally/DuckDB, but the plan-relevant path does not require model artifacts, repository snapshots, or weights to be stored in `ipfs_kit_py` and indexed in `ipfs_datasets_py`.
- Result: model files and metadata can drift apart.

### High

4. API endpoint multiplexer is runtime-only.
- `InferenceBackendManager` maintains in-memory `BackendInfo`, metrics, status, and routing tables, but has no durable backend registry or restart-safe endpoint state.
- Result: no durable service catalog, no restart continuity, no optimization history.

5. Orchestrator does not own inference lineage.
- `TaskOrchestrator` and `WorkflowManager` can manage work and workers, but do not establish a required handoff contract to the backend manager plus storage/index layers.
- Result: scheduled tasks can execute without producing canonical run records.

6. Storage/provenance integrations are wrappers, not policy.
- `DatasetsManager` and `IPFSKitStorage` exist as optional integrations.
- Result: inference callers can bypass them entirely, leading to inconsistent metadata coverage.

7. Containerizer lacks distributed artifact lifecycle integration.
- `DockerExecutor` can run containers, but does not canonically:
  - load model artifacts by CID
  - persist generated outputs by CID
  - update model/inference metadata after container completion
- Result: container execution is isolated from the model and dataset registries.

### Medium

8. Peer and backend capabilities are not durably advertised.
- P2P and libp2p inference exist, but capability advertisement and placement metadata are not persisted as a canonical registry.
- Result: scheduling cannot reliably reason about cluster-wide model/task capability.

9. Tests around API multiplexing appear broken or low-signal.
- Example multiplexing tests under `external/ipfs_accelerate/test/` are syntactically corrupted and should not be trusted as release gates.
- Result: current test surface does not prove multiplexer correctness.

10. Canonical server selection is ambiguous.
- There are multiple server and MCP-related variants across active, backup, and mirrored trees.
- Result: contributors can patch the wrong surface and increase drift.

### Low

11. Observability exists but is fragmented.
- Health, metrics, workflow persistence, and some audit hooks exist, but are not unified into one model-serving readiness report.
- Result: operational readiness cannot be judged from one artifact.

## 5. Required Cross-Library Call Contract

## 5.1 `ipfs_accelerate_py` to `ipfs_kit_py` (artifact persistence)

Use `IPFSKitStorage` as the canonical persistence seam for model files, container outputs, and inference results.

Required calls:
1. `IPFSKitStorage.store(model_artifact_bytes_or_path, name=...)`
2. `IPFSKitStorage.store(inference_output_bytes_or_json, name=...)`
3. `IPFSKitStorage.retrieve(cid)` for model restore/replay
4. `IPFSKitStorage.list_files(prefix)` for registry reconciliation and maintenance

Required stored artifact classes:
- model weights / model snapshots
- tokenizer/config bundles
- container execution outputs
- inference result payloads
- optional logs and traces for failed executions

Required response contract expected by callers:
- `success`
- `cid`
- `storage_path` or materialized path when applicable
- `backend`
- `using_fallback`
- `metadata`

## 5.2 `ipfs_accelerate_py` to `ipfs_datasets_py` (metadata index + provenance)

Use `DatasetsManager` as the canonical seam for audit, provenance, and metadata indexing of model-serving operations.

Required calls by operation type:

Model registration or model load:
1. `manager.log_event("model_registered" | "model_loaded", payload)`
2. `manager.track_provenance("model_registration" | "model_load", payload)`

Inference execution:
1. `manager.log_event("inference_started", payload)`
2. `manager.log_event("inference_completed", payload)` or `manager.log_event("inference_failed", payload)`
3. `manager.track_provenance("inference", payload)` where payload includes input CID, output CID, model CID, backend ID, latency, and hardware placement

Workflow or orchestration submission:
1. `manager.log_event("workflow_submitted" | "task_dispatched", payload)`
2. `manager.submit_workflow(...)` only when p2p/distributed scheduling is intended

Required metadata keys for model registry entries:
- `model_id`
- `model_name`
- `model_version`
- `model_cid`
- `config_cid`
- `tokenizer_cid`
- `backend_capabilities`
- `hardware_requirements`
- `created_at`
- `source_url`

Required metadata keys for inference run entries:
- `run_id`
- `workflow_id` or `task_id`
- `model_id`
- `model_cid`
- `input_cid`
- `output_cid`
- `backend_id`
- `backend_type`
- `container_image` when applicable
- `node_id` or `peer_id`
- `latency_ms`
- `status`
- `created_at`

## 5.3 Recommended ownership split

- `ipfs_accelerate_py`:
  - backend routing
  - model serving
  - container execution
  - workflow orchestration
  - enforcement of persistence/indexing contract
- `ipfs_kit_py`:
  - content-addressed artifact storage and retrieval
  - filesystem/backend abstraction for distributed files
- `ipfs_datasets_py`:
  - audit logs
  - provenance records
  - metadata indexes and query surfaces
  - optional p2p workflow scheduler integration

## 6. Subsystem Gap Remediation Plan

This section converts the investigation findings into a concrete worklist. The intent is to remove ambiguity about which subsystem owns which side effect.

### 6.1 Model server gaps

Observed state:
- `hf_model_server/server.py` provides a usable FastAPI runtime, but it does not own the persistence/provenance contract itself.
- Request handling is focused on serving, auth, rate limiting, and queuing, not on durable result lineage.

Required improvements:
- Ensure every inference completion path calls the canonical result recorder in `unified_inference_service.py` or `inference_backend_manager.py`.
- Store inference outputs via `IPFSKitStorage.store(...)` before responding or as part of the completion callback.
- Record `input_cid`, `output_cid`, `model_cid`, `backend_id`, `backend_type`, `latency_ms`, and `status` through `DatasetsManager.log_event(...)` and `DatasetsManager.track_provenance(...)`.
- Emit a unified response envelope from the server that can carry storage/provenance metadata without requiring downstream callers to infer it.

### 6.2 Containerizer gaps

Observed state:
- `docker_executor.py` can run containers, but it is not yet the canonical place where container outputs are captured, persisted, and indexed.

Required improvements:
- Add an execution-result persistence hook that stores stdout/stderr/artifacts through `IPFSKitStorage`.
- Record container metadata such as image, command, environment, node, runtime duration, and exit code in `DatasetsManager`.
- Support model-artifact fetch by CID so a container can materialize a model bundle from `ModelManager` or `IPFSKitStorage` before execution.
- Return a normalized execution envelope that includes the output CID and provenance CID.

### 6.3 API endpoint multiplexer gaps

Observed state:
- `inference_backend_manager.py` can register and select backends, but registry durability and routing history are still runtime-centric.

Required improvements:
- Persist backend registry state, including endpoint, backend type, capabilities, health, and last-seen timestamps.
- Record backend selection reasons and selected backend metadata for every task.
- Make the result-finalization callback mandatory for canonical execution paths.
- Provide a registry snapshot API that can be reconstructed after restart.

### 6.4 Kubernetes cluster manager gaps

Observed state:
- `container_backends/kubernetes/kubernetes.py` is empty.

Required improvements:
- Implement a minimal backend that can submit a job, poll status, and collect results.
- Define a Kubernetes execution envelope that matches Docker result metadata.
- Add model-artifact retrieval from CID-backed storage so jobs can mount or download inputs deterministically.
- Persist job submission, node placement, and output CID/provenance CID on completion.

### 6.5 Agent orchestrator gaps

Observed state:
- `p2p_tasks/orchestrator.py` can scale workers and drain peer tasks, but lineage is still handled indirectly.

Required improvements:
- Route all orchestrated execution through `InferenceBackendManager.execute_task(...)` so no task bypasses storage/provenance hooks.
- Add workflow/task lineage metadata: `workflow_id`, `task_id`, `backend_id`, `model_id`, `output_cid`, and `provenance_cid`.
- Persist failure lineage for interrupted tasks and peer handoffs.
- Make the orchestrator own the “claim -> execute -> finalize -> index” lifecycle, not just worker scaling.

## 7. Priority Implementation Sequence

1. Finish canonical inference persistence at the server/backend-manager layer.
2. Implement model artifact fetch/store paths for container execution.
3. Persist backend registry state and routing metadata.
4. Implement the Kubernetes backend using the same execution envelope as Docker.
5. Bind orchestrator/workflow records to the canonical execution path.
6. Add contract tests for each storage/provenance boundary.

## 8. Acceptance Criteria

The stack is ready for release planning only when all of the following are true:
- A model can be registered, stored by CID, and restored from CID-backed assets.
- Every inference completion path emits a stored output CID and a provenance record.
- Docker and Kubernetes return the same result envelope shape.
- Backend routing decisions are durable and queryable.
- Orchestrated tasks cannot bypass storage or provenance hooks.
- The readiness report can be generated from tests and benchmark artifacts without manual reconciliation.

## 6. Comprehensive Improvement Roadmap

## Phase 0: Canonical Surface Freeze (1-2 days)

Deliverables:
- Publish one canonical runtime map for:
  - model server
  - backend manager
  - Docker executor
  - Kubernetes manager
  - orchestrator
- Mark legacy, backup, mirrored, and malformed test surfaces as non-canonical.
- Add a top-level architecture note naming the only supported runtime entrypoints.

Definition of done:
- Contributors can identify one canonical implementation path for each serving subsystem.

## Phase 1: Persistence and Metadata Contract (2-4 days)

Deliverables:
- Add one shared execution record builder for inference/model/container/workflow events.
- Require every completed inference to:
  - store output via `IPFSKitStorage`
  - record provenance via `DatasetsManager`
  - emit audit events for success/failure
- Require every materialized model registration/load to:
  - store or reconcile artifact CIDs
  - update model registry metadata

Definition of done:
- No canonical inference path can complete without producing a storage CID and metadata/provenance record.

## Phase 2: Model Registry Hardening (2-4 days)

Deliverables:
- Extend `ModelManager` schema to persist:
  - `model_cid`
  - config/tokenizer artifact CIDs
  - model lineage/version fields
  - last-used timestamps
  - inference run references or counts
- Add reconciliation between local metadata store and distributed artifact store.
- Add restore path from CIDs back to runnable model assets.

Definition of done:
- Model registry can answer: what model version ran, where its artifacts live, and which inference runs used it.

## Phase 3: Backend Multiplexer and Endpoint Registry (2-4 days)

Deliverables:
- Persist `BackendInfo` and endpoint capability metadata in DuckDB or another canonical store.
- Track:
  - backend health history
  - last-seen timestamps
  - supported tasks/models
  - endpoint URL/image/peer identity
- Add restart-safe backend rehydration and stale-backend pruning.

Definition of done:
- Endpoint multiplexer has a durable service catalog rather than ephemeral in-memory state only.

## Phase 4: Container and Kubernetes Execution Plane (4-7 days)

Deliverables:
- Keep `DockerExecutor` as canonical local containerizer.
- Add post-execution hooks to persist outputs and update metadata/provenance.
- Implement `container_backends/kubernetes/kubernetes.py` from scratch with:
  - job/deployment spec generation
  - model artifact mount/fetch strategy
  - output persistence handoff
  - status polling and event capture
- Add a common execution result envelope shared by Docker and Kubernetes backends.

Definition of done:
- Containerized executions on Docker and Kubernetes both produce identical storage and metadata side effects.

## Phase 5: Orchestrator and Workflow Integration (3-5 days)

Deliverables:
- Bind `TaskOrchestrator` and `WorkflowManager` to the backend manager as the only execution dispatch seam.
- Require orchestrated tasks to carry:
  - requested model
  - expected task type
  - persistence policy
  - provenance policy
- Add workflow task result persistence and failure lineage.

Definition of done:
- Scheduled or p2p-dispatched work cannot bypass inference result persistence or metadata indexing.

## Phase 6: Peer Capability and Cluster Metadata (3-5 days)

Deliverables:
- Add capability advertisement records for peers/nodes/backends.
- Persist model-serving capabilities by node:
  - tasks supported
  - hardware type
  - loaded models
  - container image availability
- Use this registry to improve placement in orchestrator/backend routing.

Definition of done:
- Cluster manager and orchestrator can make evidence-based placement decisions.

## Phase 7: CI, Benchmarks, and Readiness Evidence (3-6 days)

Deliverables:
- Add contract suites for:
  - inference result persistence
  - model registry artifact linking
  - endpoint registry persistence
  - Docker/Kubernetes execution envelopes
  - orchestrator-to-storage lineage
- Add performance gates for:
  - inference throughput
  - persistence latency
  - endpoint failover latency
  - orchestration backlog drain time
- Generate one release evidence artifact summarizing:
  - contract gate results
  - benchmark results
  - go/no-go status

Definition of done:
- Release readiness is proven by artifact-backed contract and performance gates.

## 7. Test Plan Additions (Must Add)

1. Inference result persistence contract test:
- assert successful inference stores output via `IPFSKitStorage` and returns `output_cid`.

2. Model registry artifact linking test:
- assert registered model metadata includes model/config/tokenizer CIDs.

3. Backend registry durability test:
- assert `InferenceBackendManager` survives restart with preserved backend metadata.

4. Container execution lineage test:
- assert Docker execution persists result CID and metadata event on completion/failure.

5. Kubernetes execution parity test:
- assert Kubernetes result envelope matches Docker result envelope.

6. Orchestrator dispatch lineage test:
- assert orchestrated tasks produce workflow/task/run linkage and stored output CIDs.

7. Peer capability registry test:
- assert node capability advertisement affects backend selection.

8. Legacy surface hygiene test:
- assert canonical server/runtime imports do not depend on backup or mirrored trees.

## 8. Operational Readiness Checklist

- One canonical model-serving runtime map published.
- Model artifacts stored and recoverable by CID.
- Inference results stored and queryable by CID.
- Model registry links to artifact CIDs and inference lineage.
- Backend/service catalog persisted across restart.
- Kubernetes backend implemented or explicitly disabled in release scope.
- Orchestrator placement uses persisted capability metadata.
- Release evidence artifact generated with contract + throughput + failover results.

## 9. Immediate Next Actions

1. Freeze canonical runtime surfaces and explicitly exclude backup/mirrored trees from the plan.
2. Implement the shared persistence/provenance contract layer between inference completion and storage/index updates.
3. Extend `ModelManager` schema with artifact CID and lineage fields.
4. Replace the empty Kubernetes backend with a real minimal implementation or gate it off as unsupported.
5. Add durable backend registry storage for the endpoint multiplexer.

## 10. Concrete Integration Call Map

## 10.1 Model server completion path

Primary emitter:
- `HFModelServer` response completion hook or shared inference completion service

Required call order:
1. store input payload when configured: `IPFSKitStorage.store(...) -> input_cid`
2. store inference output: `IPFSKitStorage.store(...) -> output_cid`
3. log audit event: `DatasetsManager.log_event("inference_completed", payload)`
4. record provenance: `DatasetsManager.track_provenance("inference", payload)`
5. update model usage metadata: `ModelManager` usage counters / run linkage

## 10.2 Backend manager routing path

Primary decision surface:
- `InferenceBackendManager.select_backend_for_task(...)`

Required improvement:
- selection should emit backend decision metadata into the run record before execution:
  - `backend_id`
  - `backend_type`
  - `endpoint`
  - `hardware`
  - `selection_reason`

## 10.3 Container execution path

Primary execution surfaces:
- `DockerExecutor.execute_container(...)`
- future Kubernetes backend execute/apply path

Required improvement:
- both must emit a common execution result envelope containing:
  - `success`
  - `exit_code`
  - `stdout/stderr` or log references
  - `container_image`
  - `node_id`
  - `started_at/completed_at`
  - `output_cid`
  - `provenance_cid`

## 10.4 Model manager registration path

Primary entry:
- `ModelManager`

Required improvement:
- when model files are materialized or reconciled:
  1. store artifact(s) via `IPFSKitStorage`
  2. store provenance/audit via `DatasetsManager`
  3. persist CID fields in model metadata store
  4. expose lookup by model ID and artifact CID

## 10.5 Orchestrator/workflow path

Primary entries:
- `TaskOrchestrator`
- `WorkflowManager`

Required improvement:
- every task execution record should include:
  - `workflow_id`
  - `task_id`
  - `backend_id`
  - `model_id`
  - `output_cid`
  - `status`
  - `provenance_cid`

## 11. Go/No-Go Criteria

No-go if any of the following remain true:
- Kubernetes backend still advertised but unimplemented.
- Canonical inference path can return without storing outputs or recording provenance.
- Model registry still lacks artifact CID linkage.
- Endpoint multiplexer state is lost on restart with no reconciliation.
- Orchestrated tasks can complete without persistent run metadata.

Go when all are true:
- canonical inference/store/index contract is enforced
- model artifacts and inference outputs are CID-addressed
- backend catalog and orchestration lineage are persisted
- Docker/Kubernetes execution parity is covered by tests
- one evidence artifact summarizes contracts, benchmarks, and readiness state

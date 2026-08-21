#!/usr/bin/env python3
"""Render the sealed LogicGovernedSemanticWorkFabric operator board.

This module is declarative.  It does not admit work or mutate an authority.
The generated Markdown remains the legacy configured-board launch projection;
PlanRevisionStore admission is a product gate implemented by this board.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from typing import Iterable


BOARD_NAMESPACE = "logic-governed-semantic-work-fabric-v0.1"
ROOT_GOAL = "LGSWF-G000"
PLANNING_BASE = "d99a0204e3936ad40a68c8a457b85dc353ee9eff"
ACCELERATOR_BASE = "ea11293bb996f052d620eae989f5377a956764b1"
DATASETS_BASE = "ac82107e246b30e35a2bbdcf75e01370d22350c6"
PLAN_REVISION = "urn:lgswf:plan-revision:r000"
SEMANTIC_BOOTSTRAP = "unavailable:urn:lgswf:evidence:semantic-scan-bootstrap-failures@1"


@dataclass(frozen=True)
class Task:
    task_id: str
    title: str
    goal: str
    dependencies: tuple[str, ...]
    owner: str
    outputs: tuple[str, ...]
    objective: str
    validation: tuple[str, ...]
    resource: str = "cpu-medium"
    stage: str = "implementation"
    status: str = "todo"
    schedulable: bool = True
    completion: str = "auto"


def t(
    task_id: str,
    title: str,
    goal: str,
    dependencies: Iterable[str],
    owner: str,
    outputs: Iterable[str],
    objective: str,
    validation: Iterable[str],
    *,
    resource: str = "cpu-medium",
    stage: str = "implementation",
    status: str = "todo",
    schedulable: bool = True,
    completion: str = "auto",
) -> Task:
    return Task(
        task_id, title, goal, tuple(dependencies), owner, tuple(outputs),
        objective, tuple(validation), resource, stage, status, schedulable,
        completion,
    )


TASKS = (
    t("LGSWF-000", "Seal the dependency-ordered operator board", "LGSWF-G100", (), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/control/board-bootstrap.json",), "Freeze stable task and goal identities, exact observed source heads, authority boundaries, protected control files, and the first immutable plan revision.", ("python scripts/validate_logic_governed_semantic_work_fabric_board.py --check-all",), resource="coordinator", stage="control", status="completed", schedulable=False, completion="manual"),
    t("LGSWF-001", "Inventory exact revisions, dirty overlays, and every intervening change", "LGSWF-G100", ("LGSWF-000",), "lift_coding", ("artifacts/logic_governed_semantic_work_fabric/inventory/revision-ledger.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-001.json"), "Verify checked heads and trees, preserve dirty-overlay identities, enumerate and digest every locally known intervening revision range, and classify later code as candidate evidence rather than current authority.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/inventory/revision-ledger.json",), resource="io-analysis", stage="inventory"),
    t("LGSWF-002", "Inventory datasets semantic authorities and absent requested surfaces", "LGSWF-G100", ("LGSWF-000",), "ipfs_datasets_py", ("artifacts/logic_governed_semantic_work_fabric/inventory/datasets-authority.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-002.json"), "Inspect canonical semantic index, state, capsules, freshness, bindings, contracts, invalidation, proof selection, verification, governor, formalization, backends, families, and record adversarial-assurance and incremental-sealing absence at the checked head.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/inventory/datasets-authority.json",), resource="io-analysis", stage="inventory"),
    t("LGSWF-003", "Inventory accelerator operational authorities and actual runtime wiring", "LGSWF-G100", ("LGSWF-000",), "ipfs_accelerate_py", ("artifacts/logic_governed_semantic_work_fabric/inventory/accelerator-authority.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-003.json"), "Locate the landed goal, task, plan-revision, conflict, resource, proof, claim, daemon, merge, event, rescue, and entrypoint implementations; distinguish library capability from configured-launch wiring and compatibility shims.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/inventory/accelerator-authority.json",), resource="io-analysis", stage="inventory"),
    t("LGSWF-004", "Audit package DAG, compatibility facades, and predecessor incidents", "LGSWF-G100", ("LGSWF-000",), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/inventory/package-dag-and-predecessors.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-004.json"), "Classify canonical, consumer, facade, projection, legacy, duplicate, experimental, obsolete, and unresolved surfaces; preserve PCCE r2-r5 evidence and its empty-context, contradictory-review-schema, and task-CID-alias failures.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/inventory/package-dag-and-predecessors.json",), resource="io-analysis", stage="inventory"),
    t("LGSWF-005", "Freeze the authority map and cross-package integration interfaces", "LGSWF-G100", ("LGSWF-001", "LGSWF-002", "LGSWF-003", "LGSWF-004"), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/contracts/authority-map.json", "artifacts/logic_governed_semantic_work_fabric/contracts/interface-freeze.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-005.json"), "Freeze exact mappings between datasets semantic artifacts and accelerator references without creating duplicate semantic records or upward package imports.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/contracts/authority-map.json", "python -m json.tool artifacts/logic_governed_semantic_work_fabric/contracts/interface-freeze.json"), resource="cpu-small", stage="contract-freeze"),
    t("LGSWF-006", "Repair deterministic semantic scanning bootstrap defects", "LGSWF-G100", ("LGSWF-005",), "ipfs_datasets_py", ("external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/semantic_index/index.py", "external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/semantic_index/python_analysis.py", "external/ipfs_datasets/tests/unit/logic/software_contracts/semantic_index/test_lgswf_bootstrap.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-006.json"), "Repair only the observed empty-namespace and duplicate named-argument scan failures, retain deterministic identities, and prove scans of both checked repositories complete or yield a typed bounded no-go.", ("python -m pytest -q external/ipfs_datasets/tests/unit/logic/software_contracts/semantic_index/test_lgswf_bootstrap.py",), resource="cpu-large", stage="semantic-bootstrap"),
    t("LGSWF-007", "Remove datasets-to-accelerator semantic authority inversions", "LGSWF-G100", ("LGSWF-005",), "ipfs_datasets_py", ("external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/counterexamples/contracts.py", "external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/domain_adapters.py", "external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/source_adapters.py", "external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/tactician/proof_plan.py", "external/ipfs_datasets/tests/unit/logic/software_verification/test_accelerator_dependency_boundary.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-007.json"), "Invert or isolate the checked upward imports, especially CounterexampleEnvelope identity, behind datasets-owned leaf contracts without changing semantic meaning.", ("python -m pytest -q external/ipfs_datasets/tests/unit/logic/software_verification/test_accelerator_dependency_boundary.py",), resource="cpu-medium", stage="dependency-repair"),
    t("LGSWF-008", "Reconcile missing accelerator semantic-state surfaces and predecessor launch defects", "LGSWF-G100", ("LGSWF-005",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/integrations/datasets_semantic_authority.py", "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/configured_board_scheduler.py", "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py", "external/ipfs_accelerate/test/agent_supervisor/test_lgswf_bootstrap_runtime.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-008.json"), "Disposition all 1,245 intervening commits, port only reviewed compatible reference contracts where necessary, bind the sibling datasets checkout, and repair the three preserved PCCE bootstrap failures without advancing authority silently.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/test_lgswf_bootstrap_runtime.py",), resource="cpu-large", stage="runtime-bootstrap"),
    t("LGSWF-009", "Build canonical semantic roots, accepted PlanRevision r1, and exact task bindings", "LGSWF-G100", ("LGSWF-006", "LGSWF-007", "LGSWF-008"), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/bindings/canonical-roots.json", "artifacts/logic_governed_semantic_work_fabric/bindings/task-bindings-r1.json", "artifacts/logic_governed_semantic_work_fabric/plans/plan-revision-r1.json", "artifacts/logic_governed_semantic_work_fabric/gates/epic-a.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-009.json"), "Rescan the accepted trees with datasets authority, open or create the active plan only through PlanRevisionStore, materialize per-task exact symbol/capsule/contract/obligation bindings, and fail closed if roots cannot be verified.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/bindings/canonical-roots.json", "python -m json.tool artifacts/logic_governed_semantic_work_fabric/plans/plan-revision-r1.json"), resource="cpu-large", stage="epic-gate"),

    t("LGSWF-010", "Define SupervisorWorldSnapshot@1 reference-only contracts", "LGSWF-G200", ("LGSWF-009",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/core/world_snapshot_contracts.py", "external/ipfs_accelerate/test/agent_supervisor/core/test_world_snapshot_contracts.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-010.json"), "Define a content-addressed accelerator-owned operational overlay that references separately verified semantic, plan, objective, claim, resource, capability, merge, policy, completion, gap, epoch, fence, and event authorities and embeds none of the prohibited payloads.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/core/test_world_snapshot_contracts.py",)),
    t("LGSWF-011", "Assemble fail-closed snapshots and the read-only SupervisorWorldView", "LGSWF-G200", ("LGSWF-010",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/world_snapshot_builder.py", "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/world_view.py", "external/ipfs_accelerate/test/agent_supervisor/runtime/test_world_snapshot_runtime.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-011.json"), "Construct snapshots from independent authorities, classify current/stale/unavailable/inconsistent/quarantined components, require repository/tree/plan/population/semantic/policy agreement, and expose mutation-free goal/task/conflict/resource/evidence/refill queries.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/runtime/test_world_snapshot_runtime.py",)),
    t("LGSWF-014", "Qualify Epic B operational world-state overlay", "LGSWF-G200", ("LGSWF-011",), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/gates/epic-b.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-014.json"), "Verify canonical serialization, component freshness matrices, fail-closed consistency, authority isolation, and read-only behavior before unblocking semantic bindings.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/gates/epic-b.json",), stage="epic-gate"),

    t("LGSWF-020", "Implement SemanticWorkBinding@1 and explicit goal completion contracts", "LGSWF-G300", ("LGSWF-014",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/semantic_work_binding.py", "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/goal_completion.py", "external/ipfs_accelerate/test/agent_supervisor/planning/test_work_binding.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-020.json"), "Reference exact datasets semantic artifacts for goals, subgoals, and tasks and require observable state, semantic properties, current tests/proofs, accepted children, resolved counterexamples/gaps, review, tree, and root for completion.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/planning/test_work_binding.py",)),
    t("LGSWF-021", "Separate task execution, verification, merge, refresh, and acceptance with provisional roots", "LGSWF-G300", ("LGSWF-020",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/provisional_semantic_binding.py", "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/goal_completion.py", "external/ipfs_accelerate/test/agent_supervisor/runtime/test_provisional_acceptance.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-021.json"), "Bind provisional semantic roots to worktree attempts, keep them noncanonical, distinguish every task lifecycle gate, and reserve task acceptance for a fenced supervisor after merge and canonical refresh.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/runtime/test_provisional_acceptance.py",)),
    t("LGSWF-024", "Qualify Epic C semantic work bindings", "LGSWF-G300", ("LGSWF-021",), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/gates/epic-c.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-024.json"), "Prove no capsule content is copied, stale bindings fail closed, raw-source fallback is datasets-governed, and completion never follows task status alone.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/gates/epic-c.json",), stage="epic-gate"),

    t("LGSWF-030", "Compose SemanticWorkGraph@1 without collapsing edge authorities", "LGSWF-G400", ("LGSWF-024",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/semantic_work_graph.py", "external/ipfs_accelerate/test/agent_supervisor/analysis/test_semantic_work_graph.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-030.json"), "Compose goal, plan, semantic, code/data/interface/schema, contract/proof/validation/policy/merge/lifecycle, scope, invalidation, conflict, supersession, generation, block, and unlock edges with typed authority, evidence, roots, revision, certainty, and invalidation.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/analysis/test_semantic_work_graph.py",)),
    t("LGSWF-031", "Extend the dedicated conflict graph and fixed-point scheduling metrics", "LGSWF-G400", ("LGSWF-030",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/core/conflict_graph.py", "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/semantic_conflicts.py", "external/ipfs_accelerate/test/agent_supervisor/analysis/test_semantic_conflict_graph.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-031.json"), "Separate dependency from conflict, prefer exact symbol/interface/schema/effect scopes, conservatively fall back for opacity, and compute durable integer depth, critical path, unlock, blocking, cost, uncertainty, merge risk, bottleneck, and locality values.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/analysis/test_semantic_conflict_graph.py",)),
    t("LGSWF-034", "Qualify Epic D composite and conflict graphs", "LGSWF-G400", ("LGSWF-031",), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/gates/epic-d.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-034.json"), "Verify all required edge classes, evidence lineage, conservative unknown handling, disjoint-reader/writer cases, hidden semantic conflicts, deterministic identities, and no binary floats.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/gates/epic-d.json",), stage="epic-gate"),

    t("LGSWF-040", "Implement deterministic readiness and conflict-free frontier selection", "LGSWF-G500", ("LGSWF-034",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/parallel_frontier.py", "external/ipfs_accelerate/test/agent_supervisor/planning/test_parallel_frontier.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-040.json"), "Enforce every readiness condition and choose a conflict-free antichain under resources using deterministic bounded integer scoring; model proposals remain non-authoritative.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/planning/test_parallel_frontier.py",)),
    t("LGSWF-041", "Implement auditable frontier policy, fairness, and congestion adjustments", "LGSWF-G500", ("LGSWF-040",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/frontier_policy.py", "external/ipfs_accelerate/test/agent_supervisor/planning/test_frontier_policy.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-041.json"), "Score completion, critical-path and unlock value, locality, age/fairness against resource/provider/conflict/uncertainty/retry/merge costs with stable tie-breaking and bounded search.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/planning/test_frontier_policy.py",)),
    t("LGSWF-042", "Integrate safe split, coalesce, rewire, and speculative plan deltas", "LGSWF-G500", ("LGSWF-041",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/plan_revision_contracts.py", "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/configured_board_scheduler.py", "external/ipfs_accelerate/test/agent_supervisor/planning/test_adaptive_frontier.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-042.json"), "Use existing PlanDelta lifecycle rules to improve parallelism without in-place mutation of started history; bound speculative work to isolated, cancellable, non-authoritative evidence.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/planning/test_adaptive_frontier.py",)),
    t("LGSWF-045", "Qualify Epic E safe parallel-frontier planning", "LGSWF-G500", ("LGSWF-042",), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/gates/epic-e.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-045.json"), "Prove identical snapshots and policies yield identical frontiers, unsafe work is rejected with typed reasons, fairness is bounded, and split/coalesce preserves completion coverage.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/gates/epic-e.json",), stage="epic-gate"),

    t("LGSWF-050", "Extend ResourceScheduler with leased multidimensional hard reservations", "LGSWF-G600", ("LGSWF-045",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/resource_scheduler.py", "external/ipfs_accelerate/test/agent_supervisor/runtime/test_fabric_resource_scheduler.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-050.json"), "Extend rather than replace resource contracts across CPU, RAM, GPU, disk, network, subprocess, worktree, model tokens, provider, prover, license/key, merge, and persistence dimensions with leased task/attempt/supervisor/daemon binding and fenced reclaim.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/runtime/test_fabric_resource_scheduler.py",)),
    t("LGSWF-051", "Add receipt-derived estimates, single-flight reuse, and locality placement", "LGSWF-G600", ("LGSWF-050",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/work_cache.py", "external/ipfs_accelerate/test/agent_supervisor/runtime/test_work_cache.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-051.json"), "Keep predictions separate from observations and coordinate reuse of scans, semantic blocks, capsules, ContextPacks, sessions, prefixes, tests, proofs, environments, dependencies, and worktree objects without duplicate computation.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/runtime/test_work_cache.py",)),
    t("LGSWF-052", "Apply stage-specific backpressure, safe preemption, and cancellation", "LGSWF-G600", ("LGSWF-051",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/resource_scheduler.py", "external/ipfs_accelerate/test/agent_supervisor/runtime/test_fabric_backpressure.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-052.json"), "Decouple analysis, context, inference, proof translation/solver/kernel, validation, merge, and persistence pressure; preempt only stale/low-priority/idempotent or compensated work.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/runtime/test_fabric_backpressure.py",)),
    t("LGSWF-054", "Qualify Epic F resource-aware scheduling", "LGSWF-G600", ("LGSWF-052",), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/gates/epic-f.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-054.json"), "Prove hard resources never overcommit, all reservations release or reclaim safely, independent saturated stages do not globally stall, and predictions never overwrite receipts.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/gates/epic-f.json",), stage="epic-gate"),

    t("LGSWF-060", "Advertise supervisor capabilities and capability-based roles", "LGSWF-G700", ("LGSWF-054",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/supervisor_fabric.py", "external/ipfs_accelerate/test/agent_supervisor/runtime/test_supervisor_capabilities.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-060.json"), "Extend the sealed multi-supervisor runner with non-authoritative capability observations for identity, scope, revision, epoch, stages, resources, providers, provers, worktrees, merge, persistence, load, health, heartbeat, and expiry.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/runtime/test_supervisor_capabilities.py",)),
    t("LGSWF-061", "Enforce fenced coordination shards and coordinator failover", "LGSWF-G700", ("LGSWF-060",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/merge/lease_coordination.py", "external/ipfs_accelerate/test/agent_supervisor/merge/test_fabric_coordination.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-061.json"), "Permit one fenced writer per mutable shard, proposal-only peers, later-epoch failover, and rejection of every stale coordinator commit.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/merge/test_fabric_coordination.py",)),
    t("LGSWF-062", "Partition work, govern stealing, and provide exactly-once logical acceptance", "LGSWF-G700", ("LGSWF-061",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/supervisor_fabric.py", "external/ipfs_accelerate/test/agent_supervisor/runtime/test_supervisor_partitioning.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-062.json"), "Partition by semantic/repository/goal/resource/provider/worktree/merge/duration with explicit cross edges; steal only eligible fenced work and accept one result per task, plan, tree, semantic root, and idempotency key.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/runtime/test_supervisor_partitioning.py",)),
    t("LGSWF-064", "Qualify Epic G multi-supervisor coordination", "LGSWF-G700", ("LGSWF-062",), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/gates/epic-g.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-064.json"), "Prove process at-least-once execution cannot create duplicate accepted effects, hidden in-memory dependencies are absent, and stale/partitioned authorities fail closed.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/gates/epic-g.json",), stage="epic-gate"),

    t("LGSWF-070", "Extend one canonical daemon work-packet contract", "LGSWF-G800", ("LGSWF-064",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/work_packet.py", "external/ipfs_accelerate/test/agent_supervisor/todo_daemon/test_work_packet.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-070.json"), "Bind every required goal/plan/repository/semantic/symbol/capsule/source/contract/proof/context/scope/resource/provider/model/validation/completion/lease/fence/attempt/idempotency/checkpoint/cancellation/output field without introducing a parallel packet format.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/todo_daemon/test_work_packet.py",)),
    t("LGSWF-071", "Implement explicit daemon lifecycle, checkpoints, and typed stale stops", "LGSWF-G800", ("LGSWF-070",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/checkpoint_protocol.py", "external/ipfs_accelerate/test/agent_supervisor/todo_daemon/test_checkpoint_protocol.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-071.json"), "Represent offered through accepted plus all side paths; record bounded attempt checkpoints without equating them to completion; stop immediately on changed plan/root/lease/fence/scope/cancellation or prior acceptance.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/todo_daemon/test_checkpoint_protocol.py",)),
    t("LGSWF-072", "Wire governed packets and checkpoints into existing daemon and multi-runner", "LGSWF-G800", ("LGSWF-071",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py", "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/multi_supervisor_runner.py", "external/ipfs_accelerate/test/agent_supervisor/todo_daemon/test_governed_daemon_runtime.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-072.json"), "Make active PlanRevisionStore, shared coordination, resource admission, packet identity, checkpoint recovery, and stale fencing non-optional for fabric mode while retaining sealed launcher protections.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/todo_daemon/test_governed_daemon_runtime.py",)),
    t("LGSWF-073", "Qualify Epic H daemon protocol", "LGSWF-G800", ("LGSWF-072",), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/gates/epic-h.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-073.json"), "Prove checkpoint integrity, resume binding, stale stops, side-path taxonomy, scope enforcement, and supervisor-only acceptance.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/gates/epic-h.json",), stage="epic-gate"),

    t("LGSWF-080", "Implement evidence-backed refill proposals and bounded trigger policy", "LGSWF-G900", ("LGSWF-073",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/refill_contracts.py", "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/backlog_refinery.py", "external/ipfs_accelerate/test/agent_supervisor/planning/test_semantic_refill.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-080.json"), "Use every specified semantic, proof, assurance, merge, failure, provider, resource, granularity, progress, steering, and external-change trigger and include evidence, impacts, validation, uncertainty, dedupe, fallback, and review.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/planning/test_semantic_refill.py",)),
    t("LGSWF-081", "Enforce immutable revision safety, refill bounds, dedupe, and deterministic plan doctor", "LGSWF-G900", ("LGSWF-080",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/plan_doctor.py", "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/plan_revision_store.py", "external/ipfs_accelerate/test/agent_supervisor/planning/test_fabric_plan_doctor.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-081.json"), "Bound successor/revision/task/subgoal/key/retry/provider/token/frequency/no-progress amplification, preserve all started history, and diagnose every required plan-health defect without direct plan mutation.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/planning/test_fabric_plan_doctor.py",)),
    t("LGSWF-084", "Qualify Epic I adaptive plan revision and refill", "LGSWF-G900", ("LGSWF-081",), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/gates/epic-i.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-084.json"), "Prove accepted history is immutable, semantically equivalent refill cannot multiply, completion criteria cannot weaken, and all doctor changes remain proposals.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/gates/epic-i.json",), stage="epic-gate"),

    t("LGSWF-090", "Connect pre-execution and provisional-patch semantic refresh", "LGSWF-G1000", ("LGSWF-084",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/integrations/semantic_refresh.py", "external/ipfs_accelerate/test/agent_supervisor/integrations/test_semantic_refresh.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-090.json"), "Resolve and verify datasets views, freshness, source fallback, selected tests/proofs, and ContextPack before execution; on patch scan changed symbols, calculate invalidation, update provisional obligations, reject scope escapes, and replan verification.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/integrations/test_semantic_refresh.py",)),
    t("LGSWF-091", "Gate merge and refresh canonical semantic state after acceptance", "LGSWF-G1000", ("LGSWF-090",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/merge/semantic_reconciliation.py", "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/merge/merge_queue.py", "external/ipfs_accelerate/test/agent_supervisor/merge/test_semantic_reconciliation.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-091.json"), "Before merge verify predicted effects/contracts/selected tests/proofs/governor/assurance and seal; after queue acceptance rescan canonical tree, compare deltas, invalidate dependents, update snapshot, reevaluate goals, and revise until settled.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/merge/test_semantic_reconciliation.py",)),
    t("LGSWF-094", "Qualify Epic J closed-loop semantic refresh", "LGSWF-G1000", ("LGSWF-091",), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/gates/epic-j.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-094.json"), "Prove workers cannot publish canonical roots, predicted/observed deltas reconcile, every invalidation propagates, and accepted tree/root identity remains exact.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/gates/epic-j.json",), stage="epic-gate"),

    t("LGSWF-100", "Implement the bounded global convergence loop and successful fixed point", "LGSWF-G1100", ("LGSWF-094",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/convergence.py", "external/ipfs_accelerate/test/agent_supervisor/runtime/test_convergence.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-100.json"), "Observe, plan, reserve, dispatch, checkpoint, verify, merge, refresh, evaluate, revise, and repeat until every specified parent/child/task/evidence/invalidation/proof/gap/tree/root/plan/claim/merge/receipt condition is current.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/runtime/test_convergence.py",)),
    t("LGSWF-101", "Represent bounded non-success terminals without false completion", "LGSWF-G1100", ("LGSWF-100",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/goal_completion.py", "external/ipfs_accelerate/test/agent_supervisor/objectives/test_fabric_terminal_states.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-101.json"), "Expose blocked external/resource/provider/semantic/verification/review/exhaustion/no-progress/policy/quarantine/cancellation terminals with immutable evidence and never report them as success.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/objectives/test_fabric_terminal_states.py",)),
    t("LGSWF-103", "Qualify Epic K convergence", "LGSWF-G1100", ("LGSWF-101",), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/gates/epic-k.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-103.json"), "Prove fixed-point sufficiency, bounded no-progress/exhaustion behavior, restart continuation, no premature completion, and honest terminal classification.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/gates/epic-k.json",), stage="epic-gate"),

    t("LGSWF-110", "Emit content-addressed scheduling decision receipts and metrics", "LGSWF-G1200", ("LGSWF-103",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/scheduling_observability.py", "external/ipfs_accelerate/test/agent_supervisor/runtime/test_scheduling_observability.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-110.json"), "Record every required snapshot/candidate/rejection/conflict/frontier/resource/assignment/priority/path/unlock/cache/fairness/provider/policy/claim fact and all requested concurrency, reuse, cost, failure, refill, and no-progress metrics.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/runtime/test_scheduling_observability.py",)),
    t("LGSWF-111", "Expose machine-readable fabric status through the highest-level entrypoint", "LGSWF-G1200", ("LGSWF-110",), "ipfs_accelerate_py", ("external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/entrypoints/supervisor_fabric.py", "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/entrypoints/__init__.py", "external/ipfs_accelerate/test/agent_supervisor/entrypoints/test_supervisor_fabric.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-111.json"), "Provide stable machine output and provenance through existing entrypoints without adding a GUI or granting read APIs mutation authority.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/entrypoints/test_supervisor_fabric.py",)),
    t("LGSWF-113", "Qualify Epic L observability", "LGSWF-G1200", ("LGSWF-111",), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/gates/epic-l.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-113.json"), "Validate receipt content identities, exact decision explanations, integer/fixed-point durability, metric definitions, restart continuity, and entrypoint schema.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/gates/epic-l.json",), stage="epic-gate"),

    t("LGSWF-120", "Build deterministic three-supervisor ten-daemon qualification fixture", "LGSWF-G1300", ("LGSWF-113",), "ipfs_accelerate_py", ("external/ipfs_accelerate/test/agent_supervisor/fabric/fixtures.py", "external/ipfs_accelerate/test/agent_supervisor/fabric/test_fixture_topology.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-120.json"), "Create multiple resource classes, independent and conflicting branches, multilevel goals, proof/validation work, merge pressure, and refill triggers with restartable durable state.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/fabric/test_fixture_topology.py",), resource="cpu-large", stage="qualification"),
    t("LGSWF-121", "Qualify claims, conflicts, epochs, failover, stealing, and partition faults", "LGSWF-G1300", ("LGSWF-120",), "ipfs_accelerate_py", ("external/ipfs_accelerate/test/agent_supervisor/fabric/test_coordination_faults.py", "artifacts/logic_governed_semantic_work_fabric/qualification/coordination-faults.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-121.json"), "Run deterministic cases 1-9 and 15-16 including concurrent independence, writer exclusion, compatible reads, stale plan/root fencing, duplicate claims, later epoch, old-coordinator rejection, checkpoint resume, eligible stealing, and partition rejection.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/fabric/test_coordination_faults.py",), resource="cpu-large", stage="fault-injection"),
    t("LGSWF-122", "Qualify effects, backpressure, semantic invalidation, proof failure, and bounded refill faults", "LGSWF-G1300", ("LGSWF-120",), "ipfs_accelerate_py", ("external/ipfs_accelerate/test/agent_supervisor/fabric/test_resource_semantic_faults.py", "artifacts/logic_governed_semantic_work_fabric/qualification/resource-semantic-faults.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-122.json"), "Run deterministic cases 10-14 and 17-25 covering compensation, independent pressure, hidden dependency, invalidation, successor proof work, bounded recurring failure, refill dedupe, immutable history, safe split/coalesce, and current-evidence completion.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/fabric/test_resource_semantic_faults.py",), resource="cpu-large", stage="fault-injection"),
    t("LGSWF-123", "Run the complete fail-closed adversarial matrix", "LGSWF-G1300", ("LGSWF-120",), "ipfs_accelerate_py", ("external/ipfs_accelerate/test/agent_supervisor/fabric/test_adversarial_matrix.py", "artifacts/logic_governed_semantic_work_fabric/qualification/adversarial-matrix.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-123.json"), "Inject every forged/stale/wrong-scope/tree/plan/fence/effect/policy/test/proof/model/receipt/replay/checkpoint/split-brain/impossible-telemetry case and require all critical paths to fail closed.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/fabric/test_adversarial_matrix.py",), resource="cpu-large", stage="adversarial"),
    t("LGSWF-125", "Prove restart reconstruction without process dictionaries", "LGSWF-G1300", ("LGSWF-120",), "ipfs_accelerate_py", ("external/ipfs_accelerate/test/agent_supervisor/fabric/test_restart_reconstruction.py", "artifacts/logic_governed_semantic_work_fabric/qualification/restart-reconstruction.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-125.json"), "Kill and restart coordinators, supervisors, and daemons at every lifecycle stage and reconstruct solely from durable authoritative records with stale leases fenced.", ("python -m pytest -q external/ipfs_accelerate/test/agent_supervisor/fabric/test_restart_reconstruction.py",), resource="cpu-large", stage="fault-injection"),
    t("LGSWF-126", "Qualify Epic M multi-supervisor and daemon faults", "LGSWF-G1300", ("LGSWF-121", "LGSWF-122", "LGSWF-123", "LGSWF-125"), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/gates/epic-m.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-126.json"), "Aggregate raw deterministic receipts without hiding failed attempts and issue pass, bounded no-go, or external-block disposition for every required case.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/gates/epic-m.json",), stage="epic-gate"),

    t("LGSWF-130", "Freeze benchmark corpus and configurations A through D", "LGSWF-G1400", ("LGSWF-126",), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/benchmark/corpus.json", "external/ipfs_accelerate/scripts/benchmarks/logic_governed_semantic_work_fabric.py", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-130.json"), "Freeze independent, fan-out/fan-in, long-path, shared-schema, proof/model/merge-heavy, bottleneck, failure, invalidation, and refill workloads plus serial, dependency-only, conflict-aware, and complete-fabric policies.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/benchmark/corpus.json",), resource="cpu-medium", stage="benchmark"),
    t("LGSWF-131", "Run serial and dependency-only benchmark baselines", "LGSWF-G1400", ("LGSWF-130",), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/benchmark/raw/config-a.json", "artifacts/logic_governed_semantic_work_fabric/benchmark/raw/config-b.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-131.json"), "Execute configurations A and B against the exact frozen release/workload/environment and retain observed values separately from estimates.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/benchmark/raw/config-a.json", "python -m json.tool artifacts/logic_governed_semantic_work_fabric/benchmark/raw/config-b.json"), resource="benchmark-large", stage="benchmark"),
    t("LGSWF-132", "Run conflict-aware and complete-fabric benchmarks", "LGSWF-G1400", ("LGSWF-130",), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/benchmark/raw/config-c.json", "artifacts/logic_governed_semantic_work_fabric/benchmark/raw/config-d.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-132.json"), "Execute configurations C and D under identical bindings, retain every failure/throttle/conflict/revision/recovery receipt, and never fabricate target attainment.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/benchmark/raw/config-c.json", "python -m json.tool artifacts/logic_governed_semantic_work_fabric/benchmark/raw/config-d.json"), resource="benchmark-large", stage="benchmark"),
    t("LGSWF-134", "Analyze parallelism, reuse, resource efficiency, cost, and overhead", "LGSWF-G1400", ("LGSWF-131", "LGSWF-132"), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/benchmark/performance-report.json", "artifacts/logic_governed_semantic_work_fabric/benchmark/resource-efficiency-report.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-134.json"), "Report every requested measure and target honestly, distinguish theoretical DAG width from achieved concurrency, and bind conclusions only to the exact corpus, policies, providers, release, and environment.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/benchmark/performance-report.json", "python -m json.tool artifacts/logic_governed_semantic_work_fabric/benchmark/resource-efficiency-report.json"), resource="cpu-medium", stage="analysis"),
    t("LGSWF-135", "Qualify Epic N benchmark evidence", "LGSWF-G1400", ("LGSWF-134",), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/gates/epic-n.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-135.json"), "Verify corpus immutability, run comparability, raw receipt integrity, metric calculations, target truthfulness, and bounded scheduling/refill overhead.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/gates/epic-n.json",), stage="epic-gate"),

    t("LGSWF-140", "Assemble the content-addressed qualification release", "LGSWF-G1500", ("LGSWF-135",), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/release/manifest.json", "artifacts/logic_governed_semantic_work_fabric/release/artifact-index.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-140.json"), "Assemble exact revisions, all schemas, inventories, authority map, tests, faults, corpus, raw results, reports, findings, limitations, migration, rollback, and decision into one verifiable release.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/release/manifest.json",), stage="release"),
    t("LGSWF-141", "Complete security findings, migration guidance, and rollback procedures", "LGSWF-G1500", ("LGSWF-140",), "cross-repository", ("docs/architecture/LOGIC_GOVERNED_SEMANTIC_WORK_FABRIC_SECURITY.md", "docs/architecture/LOGIC_GOVERNED_SEMANTIC_WORK_FABRIC_MIGRATION.md", "artifacts/logic_governed_semantic_work_fabric/release/security-findings.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-141.json"), "Document trust boundaries, unresolved risks, compatible migration from legacy boards, disable/rollback and compensation paths, and protected-branch non-authority.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/release/security-findings.json",), stage="release"),
    t("LGSWF-142", "Compute an evidence-bounded qualification level and go/no-go", "LGSWF-G1500", ("LGSWF-141",), "cross-repository", ("scripts/validate_logic_governed_semantic_work_fabric_release.py", "artifacts/logic_governed_semantic_work_fabric/release/qualification-decision.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-142.json"), "Deterministically choose no higher than research_demo, internal_alpha, internal_pilot, supervised_external_pilot, or production_candidate from current evidence and emit an explicit continuous-operation recommendation.", ("python scripts/validate_logic_governed_semantic_work_fabric_release.py --check-all",), stage="release"),
    t("LGSWF-144", "Publish the required 24-section final supervisor report", "LGSWF-G1500", ("LGSWF-142",), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/release/final-supervisor-report.json", "docs/architecture/LOGIC_GOVERNED_SEMANTIC_WORK_FABRIC_QUALIFICATION.md", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-144.json"), "Report all required revisions, inventory, authority, board, reuse, designs, protocols, results, reuse, overhead, security, limitations, level, and recommendation; use the scoped final claim only when its predicates are evidenced.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/release/final-supervisor-report.json",), stage="release"),
    t("LGSWF-145", "Seal Epic O and the parent fixed-point decision", "LGSWF-G1500", ("LGSWF-144",), "cross-repository", ("artifacts/logic_governed_semantic_work_fabric/gates/epic-o.json", "artifacts/logic_governed_semantic_work_fabric/release/release-seal.json", "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-145.json"), "Verify every parent completion predicate and either seal a bounded qualified release or preserve an explicit no-go/non-success terminal with all failed attempts and unresolved obligations.", ("python -m json.tool artifacts/logic_governed_semantic_work_fabric/release/release-seal.json",), stage="epic-gate"),
)


GOALS = (
    ("LGSWF-G000", "LogicGovernedSemanticWorkFabric", "", "Implement and qualify the continuous logic-governed semantic work fabric; completion requires current evidence for every required child, no mandatory unresolved work, settled claims/merge queue, matching tree and semantic root, and verified release receipts."),
    ("LGSWF-G100", "A — inventory and contract freeze", "", "Freeze exact revisions, implementation classifications, authority map, package DAG, interfaces, semantic roots, and accepted plan bindings."),
    ("LGSWF-G200", "B — operational world-state overlay", "LGSWF-G100", "Deliver a reference-only schedulable snapshot and mutation-free view from separately verified authorities."),
    ("LGSWF-G300", "C — semantic goal and task bindings", "LGSWF-G200", "Bind goals, subgoals, tasks, completion, worktrees, and acceptance to canonical semantic evidence."),
    ("LGSWF-G400", "D — composite work and conflict graphs", "LGSWF-G300", "Compose typed dependency and conflict evidence with deterministic scheduling metrics."),
    ("LGSWF-G500", "E — safe parallel frontier", "LGSWF-G400", "Select the largest useful deterministic conflict-free ready frontier and safely revise granularity."),
    ("LGSWF-G600", "F — resource-aware scheduling", "LGSWF-G500", "Reserve, estimate, reuse, backpressure, preempt, and release multidimensional resources safely."),
    ("LGSWF-G700", "G — multi-supervisor coordination", "LGSWF-G600", "Coordinate capability-based supervisors with fenced shards, safe partitioning, stealing, and exactly-once acceptance."),
    ("LGSWF-G800", "H — daemon packets and checkpoints", "LGSWF-G700", "Bind one canonical packet and explicit lifecycle/checkpoint/stale-stop protocol into existing daemons."),
    ("LGSWF-G900", "I — adaptive revision and refill", "LGSWF-G800", "Revise future work immutably through bounded evidence-backed deltas and deterministic diagnosis."),
    ("LGSWF-G1000", "J — closed-loop semantic refresh", "LGSWF-G900", "Use datasets authority before/during/after work and refresh canonical state only after accepted merge."),
    ("LGSWF-G1100", "K — fixed-point convergence", "LGSWF-G1000", "Converge to evidence-backed success or an explicit bounded non-success terminal."),
    ("LGSWF-G1200", "L — scheduling observability", "LGSWF-G1100", "Explain and measure every scheduling cycle through content-addressed machine-readable evidence."),
    ("LGSWF-G1300", "M — fault qualification", "LGSWF-G1200", "Pass or honestly disposition all deterministic multi-supervisor, daemon, and adversarial cases."),
    ("LGSWF-G1400", "N — parallelism and efficiency benchmark", "LGSWF-G1300", "Compare configurations A-D on a frozen corpus and report actual parallelism, reuse, cost, and overhead."),
    ("LGSWF-G1500", "O — release qualification", "LGSWF-G1400", "Publish a content-addressed release, bounded qualification level, and explicit continuous-operation go/no-go."),
)


def _csv(values: Iterable[str]) -> str:
    return ", ".join(values)


def _resource_vector(resource: str) -> str:
    vectors = {
        "coordinator": {"cpu_concurrency": 1, "ram_mib": 512, "worktree_slots": 0, "model_input_tokens": 0, "provider_concurrency": 0, "merge_slots": 0},
        "io-analysis": {"cpu_concurrency": 1, "ram_mib": 2048, "worktree_slots": 1, "model_input_tokens": 24000, "provider_concurrency": 1, "merge_slots": 1},
        "cpu-small": {"cpu_concurrency": 1, "ram_mib": 2048, "worktree_slots": 1, "model_input_tokens": 32000, "provider_concurrency": 1, "merge_slots": 1},
        "cpu-medium": {"cpu_concurrency": 2, "ram_mib": 4096, "worktree_slots": 1, "model_input_tokens": 48000, "provider_concurrency": 1, "merge_slots": 1},
        "cpu-large": {"cpu_concurrency": 4, "ram_mib": 8192, "worktree_slots": 1, "model_input_tokens": 64000, "provider_concurrency": 1, "merge_slots": 1},
        "benchmark-large": {"cpu_concurrency": 8, "ram_mib": 16384, "worktree_slots": 2, "model_input_tokens": 64000, "provider_concurrency": 2, "merge_slots": 1},
    }
    base = dict(vectors.get(resource, vectors["cpu-medium"]))
    base.update({"gpu_memory_mib": 0, "disk_mib": 4096, "network": "denied-unless-packet-authorizes", "subprocesses": max(1, int(base["cpu_concurrency"])), "prover_concurrency": 1, "persistence_mib_per_second": 64})
    return json.dumps(base, sort_keys=True, separators=(",", ":"))


def render_todo() -> str:
    lines = [
        "# LogicGovernedSemanticWorkFabric supervisor task board",
        "",
        "This dependency-ordered Markdown is the sealed bootstrap projection consumed by the checked ipfs_accelerate_py configured-board launcher. The accepted PlanRevisionStore projection becomes authoritative after LGSWF-009; started history is never rewritten.",
        "",
        "## Execution order",
        "",
        "`A → B → C → D → E → F → G → H → I → J → K → L → M → N → O`. Only tasks whose dependencies are accepted and whose exact bindings remain current may run. LGSWF-001 through LGSWF-004 are the only initial parallel frontier.",
        "",
        "## Global execution contract",
        "",
        "Every schedulable task uses an isolated worktree, exact claim/lease/fence/idempotency binding, declared reads/writes/effects, pre-change checks, the smallest coherent patch, provisional semantic rescan, focused and affected validation, checkpoint/result receipts, admitted merge, canonical post-merge refresh, and goal reevaluation. Overlapping writes require a dependency plus merge/conflict contract. Models and daemons cannot approve their own work. Failed attempts and partial effects remain durable.",
        "",
    ]
    for task in TASKS:
        bootstrap = task.task_id in {f"LGSWF-{n:03d}" for n in range(1, 9)}
        binding = "raw-source-required; exact Git tree and bootstrap failure evidence" if bootstrap else f"artifacts/logic_governed_semantic_work_fabric/bindings/task-bindings-r1.json#{task.task_id}"
        base = PLANNING_BASE if task.owner in {"cross-repository", "lift_coding"} else DATASETS_BASE if task.owner == "ipfs_datasets_py" else ACCELERATOR_BASE
        allowed = _csv(task.outputs)
        validations = " ; ".join(task.validation)
        completion_contract = f"{task.objective} The declared outputs must exist at their recorded identities; every validation and selected proof must be current; merge and canonical semantic refresh must succeed where mutation occurs; an independent fenced supervisor must accept the result. Worker completion or task status alone is insufficient."
        lines.extend([
            f"## {task.task_id} {task.title}", "",
            f"- Stable task ID: {task.task_id}",
            f"- Status: {task.status}",
            f"- Completion: {task.completion}",
            f"- Is schedulable: {'true' if task.schedulable else 'false'}",
            f"- Review only: {'true' if not task.schedulable else 'false'}",
            f"- Parent goal ID: {ROOT_GOAL}",
            f"- Subgoal ID: {task.goal}",
            f"- Goal id: {task.goal}",
            f"- Owning repository: {task.owner}",
            f"- Owned paths: {allowed}",
            f"- Base revision: {base}",
            f"- Base semantic-state root: {SEMANTIC_BOOTSTRAP if task.task_id != 'LGSWF-000' else 'not-applicable:operator-board-seal'}",
            f"- Base plan revision: {PLAN_REVISION}",
            f"- Objective: {task.objective}",
            f"- Depends on: {_csv(task.dependencies)}",
            f"- Read scope: checked source at {base}; docs/architecture/LOGIC_GOVERNED_SEMANTIC_WORK_FABRIC_PLAN.md; {binding}",
            f"- Write scope: {allowed}",
            "- External effect scope: local isolated worktree, local subprocess validation, local content-addressed evidence, and admitted local merge only; network/provider/prover effects require the packet reservation and policy",
            f"- Relevant symbol IDs: {binding}",
            f"- Capsule CIDs: {binding}",
            f"- Contract and obligation CIDs: {binding}",
            f"- Resource demand: {_resource_vector(task.resource)}",
            f"- Model-route class: {'none-operator-seal' if not task.schedulable else 'ordered-grok-implement-codex-review-' + task.stage}",
            "- Permitted effects: read declared scope; mutate only owned paths in the leased worktree; run declared validation; emit immutable evidence; request admitted merge",
            "- Prohibited effects: mutate canonical datasets semantic truth; edit protected board or policy; overlap an active writer; publish provisional roots; weaken tests/contracts/proofs; self-approve; contact network or external systems without explicit packet authority; merge protected branches",
            f"- Completion contract: {completion_contract}",
            f"- Validation requirements: {validations}",
            "- Proof requirements: datasets-selected proof obligations and invalidation closure must be current; where no formal proof is selected, record the verified empty selection and limitations; simulated or model-claimed proof is non-authoritative",
            "- Lease requirements: one task claim, one isolated-worktree mutation lease, current plan/tree/semantic fence, bounded resource reservation, merge lease for mutation, heartbeat, idempotency key, and later fencing token after any reclaim",
            "- Rollback or compensation: discard an unmerged task worktree; revert only the admitted task commit after merge; restore the preceding accepted plan/world pointer by new fenced revision; invalidate descendants; record partial effects and execute declared compensation before retry",
            f"- Required evidence: exact before/after revisions and trees; claim/lease/fence/reservation; changed paths and symbols; provisional/canonical semantic deltas; validation and proof receipts; merge result; completion decision; receipt at artifacts/logic_governed_semantic_work_fabric/receipts/{task.task_id}.json",
            f"- Final result identity: {'urn:lgswf:board-seal:r000' if task.task_id == 'LGSWF-000' else 'pending:content-addressed-result:' + task.task_id}",
            "- Priority: P0",
            f"- Track: {task.goal.lower()}-{task.stage}",
            f"- Outputs: {allowed}",
            f"- Validation: {validations}",
            f"- Board namespace: {BOARD_NAMESPACE}",
            f"- Bundle: lgswf/{task.goal.lower()}/{task.task_id.lower()}",
            f"- Parallel lane: {task.task_id.lower()}",
            f"- Resource class: {task.resource}",
            f"- Resource stage: {task.stage}",
            f"- Estimated tokens: {0 if not task.schedulable else 48000}",
            f"- Implementation timeout seconds: {0 if not task.schedulable else 5400}",
            f"- Predicted files: {allowed}",
            f"- Allowed paths: {allowed}",
            "- Interfaces: authority-map@1, SemanticWorkBinding@1-or-bootstrap-fallback, PlanRevisionContracts@1, task-identity@1",
            "- Allow concurrent with: only dependency-ready tasks with validator-proven disjoint write/effect scopes and admitted conflict contract",
            "- Conflict policy: exact symbol scope when available; otherwise file or repository serialization; unknown conflicts fail closed",
            "- Preconditions: exact base/plan/tree/root or typed bootstrap fallback; dependencies accepted; fresh claim; admitted resources; no active conflicting writer",
            "- Effects: bounded owned-path mutation and immutable evidence; no undeclared canonical or external effects",
            "- Evidence subset: authority roots, source evidence, relevant capsules/contracts/obligations, validation/proof selection, claim/resource/merge receipts",
            "- Symbolic first: true",
            "- LLM context budget bytes: 196608",
            f"- Acceptance: {completion_contract}",
            f"- Embedding query: {task.objective}",
            "", 
        ])
    return "\n".join(lines).rstrip() + "\n"


def render_objectives() -> str:
    by_goal = {goal_id: [task.task_id for task in TASKS if task.goal == goal_id] for goal_id, *_ in GOALS}
    children = {goal_id: [] for goal_id, *_ in GOALS}
    for goal_id, _title, dependency, _objective in GOALS[1:]:
        children[ROOT_GOAL].append(goal_id)
    lines = ["# LogicGovernedSemanticWorkFabric objective heap", "", "Task completion is necessary but never sufficient for goal completion. Every goal requires current evidence bound to the accepted tree, semantic-state root, and plan revision.", ""]
    for goal_id, title, dependency, objective in GOALS:
        producing = [task.task_id for task in TASKS] if goal_id == ROOT_GOAL else by_goal[goal_id]
        evidence = "artifacts/logic_governed_semantic_work_fabric/release/final-supervisor-report.json" if goal_id == ROOT_GOAL else f"artifacts/logic_governed_semantic_work_fabric/gates/epic-{chr(96 + int(goal_id[7:]) // 100) if goal_id != ROOT_GOAL else 'root'}.json"
        lines.extend([
            f"## {goal_id} {title}", "",
            "- Status: active",
            f"- Parent: {'' if goal_id == ROOT_GOAL else ROOT_GOAL}",
            f"- Depends on: {dependency}",
            "- Fib priority: 1",
            "- Priority: P0",
            f"- Track: {BOARD_NAMESPACE}",
            f"- Bundle: lgswf/{goal_id.lower()}",
            f"- Parallel lane: {goal_id.lower()}",
            "- Resource class: coordinator",
            f"- Goal: {objective}",
            f"- Producing tasks: {_csv(producing)}",
            f"- Evidence: {evidence}",
            "- Evidence criteria: Current content-addressed receipts must prove the observable completion contract against the exact accepted repository tree, datasets semantic-state root, active plan revision, settled claims, settled merge queue, resolved mandatory invalidations/proofs/counterexamples/gaps, and any required human approval.",
            "- Evidence source policy: Exact Git/tree identities, verified datasets artifacts, PlanRevisionStore state, immutable execution/validation/proof/merge receipts, and independent supervisor acceptance are authoritative; filenames, prose, model output, process exit, and completed task labels alone are not.",
            f"- Outputs: {evidence}",
            f"- Predicted files: {evidence}",
            "- Validation: python scripts/validate_logic_governed_semantic_work_fabric_board.py --check-all",
            "- Acceptance: All producing tasks and child goals satisfy their explicit contracts with current evidence, and no bounded non-success terminal is misreported as completion.",
            "- Gap task: Propose the smallest evidence-backed immutable plan delta that closes a real uncovered completion predicate without weakening it.",
            f"- Subgoals: {_csv(children.get(goal_id, ())) if goal_id == ROOT_GOAL else ''}",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def projection() -> dict[str, object]:
    task_ids = [task.task_id for task in TASKS]
    payload = {
        "schema": "ipfs_accelerate_py.agent_supervisor.logic-governed-semantic-work-fabric.task-board@1",
        "board_namespace": BOARD_NAMESPACE,
        "planning_base": PLANNING_BASE,
        "accelerator_base": ACCELERATOR_BASE,
        "datasets_base": DATASETS_BASE,
        "base_plan_revision": PLAN_REVISION,
        "base_semantic_state_root": SEMANTIC_BOOTSTRAP,
        "task_count": len(TASKS),
        "goal_count": len(GOALS),
        "completed_task_ids": [task.task_id for task in TASKS if task.status == "completed"],
        "initial_ready_task_ids": ["LGSWF-001", "LGSWF-002", "LGSWF-003", "LGSWF-004"],
        "terminal_task_id": "LGSWF-145",
        "tasks": [
            {
                "task_id": task.task_id,
                "goal_id": task.goal,
                "dependencies": list(task.dependencies),
                "owner": task.owner,
                "owned_paths": list(task.outputs),
                "status": task.status,
                "schedulable": task.schedulable,
            }
            for task in TASKS
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["projection_id"] = "sha256:" + hashlib.sha256(canonical).hexdigest()
    return payload


def dependency_projection() -> dict[str, object]:
    payload = {
        "schema": "ipfs_accelerate_py.agent_supervisor.logic-governed-semantic-work-fabric.dependency-graph@1",
        "board_namespace": BOARD_NAMESPACE,
        "nodes": [task.task_id for task in TASKS],
        "edges": [{"source": dependency, "target": task.task_id, "kind": "task_dependency"} for task in TASKS for dependency in task.dependencies],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["graph_id"] = "sha256:" + hashlib.sha256(canonical).hexdigest()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit", choices=("todo", "objectives", "projection", "dependencies"), required=True)
    args = parser.parse_args()
    if args.emit == "todo":
        print(render_todo(), end="")
    elif args.emit == "objectives":
        print(render_objectives(), end="")
    elif args.emit == "projection":
        print(json.dumps(projection(), indent=2, sort_keys=True))
    else:
        print(json.dumps(dependency_projection(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

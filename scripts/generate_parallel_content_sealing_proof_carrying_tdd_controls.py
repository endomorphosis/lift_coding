#!/usr/bin/env python3
"""Generate the protected PCTDD control program from one reviewed source."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "parallel-content-sealing-proof-carrying-tdd-v1"
PLAN_REVISION = "PCTDD-PLAN-V1.1"
PREDECESSOR_PLAN_REVISION = "PCTDD-PLAN-V1"
STORE_GENERATION = "pctdd-v1-g6"
RUNTIME_ROOT = "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g6"
QUACK_ENDPOINT = "quack:127.0.0.1:42778"
BRANCH = "agent/parallel-content-sealing-proof-carrying-tdd-v1"
INVENTORY = ROOT / "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory"
PLAN = ROOT / "docs/architecture/PARALLEL_CONTENT_SEALING_PROOF_CARRYING_TDD_PLAN.md"
OBJECTIVES = ROOT / "docs/architecture/parallel_content_sealing_proof_carrying_tdd.objectives.md"
BOARD = ROOT / "docs/architecture/parallel_content_sealing_proof_carrying_tdd.todo.md"
CONFIG = ROOT / "config/agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json"
BENCHMARK = ROOT / "config/parallel_content_sealing_proof_carrying_tdd_benchmark.json"
SEAL = ROOT / "config/parallel_content_sealing_proof_carrying_tdd_dependencies.seal.json"
VALIDATION_PROFILES = ROOT / "config/parallel_content_sealing_proof_carrying_tdd_validation_profiles.json"
VALIDATION_DISPATCHER = "scripts/run_parallel_content_sealing_proof_carrying_tdd_validation.py"
CONTROL_TEST = "test/api/parallel_content_sealing/test_pctdd_g6_control_amendment.py"
G5_MIGRATION_INVENTORY = INVENTORY / "g5_migration_inventory.json"
CONTROL_MANIFEST = ROOT / "config/parallel_content_sealing_proof_carrying_tdd_control_manifest.json"
G5_DATABASE = ROOT / "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g5/control.duckdb"
G5_BOOTSTRAP_RECEIPT = ROOT / "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g5/evidence/bootstrap/pctdd-bootstrap.json"


TASK_TITLES = (
    "Freeze program controls, baseline, seals, and scheduler",
    "Inventory current CID, SHA, canonicalization, and seal paths",
    "Inventory current pytest proof-reuse identity and DI paths",
    "Inventory ZK, signing, key, and proof claim boundaries",
    "Instrument the current cold and warm critical path",
    "Define prepared canonical block and batch contracts",
    "Implement source-object identity bridging",
    "Implement persistent verified hash memo contracts in datasets",
    "Implement the kit hash-memo store",
    "Implement file chunk manifests and auxiliary change-detection profiles",
    "Implement parallel canonicalization and hash scheduling",
    "Implement optional native/Rust batch hashing qualification",
    "Implement verified batch immutable block storage",
    "Implement parallel Merkle leaf/level/category construction",
    "Implement Merkle branch memoization and proof-forest delta updates",
    "Define prepared full-checkpoint and delta-seal contracts",
    "Implement parallel full-checkpoint preparation",
    "Implement parallel delta-seal preparation",
    "Implement parallel proof/certificate verification",
    "Shorten and harden the serial commit boundary",
    "Qualify parallel sealing for concurrency, crash, and corruption",
    "Define fixture-definition closure contracts",
    "Implement fixture-definition closure extraction",
    "Define fixture-instance and injected-dependency contracts",
    "Implement reviewed dependency-injection commitment adapters",
    "Define and implement TestExecutionKeyV2",
    "Define composite phase receipt and statement contracts",
    "Integrate setup-bound execution-key assembly into pytest",
    "Implement guarded post-setup, pre-call reuse",
    "Implement narrowly gated pre-setup whole-item reuse",
    "Extend xdist controller/worker proof-reuse coordination",
    "Implement fixture- and proof-aware xdist scheduling",
    "Integrate current signed runner attestations",
    "Define aggregate test-batch and leaf contracts",
    "Define aggregate test-pass statement and public inputs",
    "Implement aggregate ZK circuit/backend adapter",
    "Implement proof batch coordinator and asynchronous pipeline",
    "Implement fixture-cohort and selected-test proof-forest units",
    "Integrate datasets semantic-state test/proof selection",
    "Add optional direct-execution proof profiles",
    "Implement FastTddLoopController@1",
    "Integrate the fast loop with incremental verification and repair",
    "Integrate context compression and proof-carrying procedure compilation",
    "Add CLI, control-service, and diagnostics surfaces",
    "Activate shadow_hash",
    "Activate shadow_reuse and shadow_proof",
    "Activate protected",
    "Activate required self-hosting",
    "Run the end-to-end acceptance matrix",
    "Run hashing and seal benchmarks",
    "Run pytest, proof, and TDD-loop benchmarks",
    "Run adversarial, privacy, and trust qualification",
    "Perform the required-mode self-hosted capstone",
    "Publish current-tree release, migration, and limitation report",
)
TASKS = {f"PCTDD-{n:03d}": title for n, title in enumerate(TASK_TITLES)}

# One exact, uniquely owned test artifact is part of every task's declared
# output.  The profile dispatcher runs this path directly; it never guesses a
# test from prose or a broad directory.
TASK_TEST_STEMS = (
    "g6_control_amendment", "cid_sha_canonicalization_inventory",
    "pytest_identity_inventory", "proof_claim_inventory", "cold_warm_critical_path",
    "prepared_canonical_block", "source_object_identity", "hash_memo_contracts",
    "hash_memo_store", "file_chunk_manifest", "parallel_hash_scheduler",
    "native_hash_qualification", "batch_immutable_block_storage",
    "parallel_merkle_construction", "merkle_branch_memo", "prepared_seal_contracts",
    "parallel_full_checkpoint", "parallel_delta_seal", "parallel_proof_verification",
    "serial_commit_boundary", "parallel_seal_fault_qualification",
    "fixture_definition_contracts", "fixture_definition_extraction",
    "fixture_instance_contracts", "dependency_commitment_adapters",
    "test_execution_key_v2", "composite_phase_receipt", "setup_bound_execution_key",
    "post_setup_call_reuse", "pre_setup_item_reuse", "xdist_reuse_coordination",
    "fixture_proof_aware_xdist", "signed_runner_attestations", "aggregate_test_batch",
    "aggregate_test_pass_statement", "aggregate_zk_adapter", "proof_batch_pipeline",
    "test_proof_forest_units", "semantic_state_selection", "direct_execution_profiles",
    "fast_tdd_controller", "fast_tdd_repair", "tdd_procedure_compilation",
    "fast_tdd_control_surfaces", "shadow_hash", "shadow_reuse_proof", "protected_rollout",
    "required_self_hosting", "end_to_end_acceptance", "hash_seal_benchmarks",
    "pytest_proof_tdd_benchmarks", "adversarial_privacy_trust", "required_capstone",
    "release_migration_limitations",
)

# The final sentence is emitted into both the worker directive and acceptance
# criterion.  Keeping this closed tuple makes every task instruction specific
# and makes accidental generic/prose-only tasks detectable in tests.
TASK_ASSERTIONS = (
    "the V1.1 amendment, g5 migration record, g6 paths, profiles, seal and dry-run agree",
    "every current source-to-CID and seal-publication path is inventoried without changing identity",
    "collection, fixture timing, DI, runtime trace and xdist publication boundaries are mapped",
    "real, simulated, signed, aggregate, direct and incremental evidence remain distinctly classified",
    "cold and warm stages report timing and byte counters without changing behavior",
    "prepared canonical blocks preserve existing canonical bytes and CIDs under golden vectors",
    "Git blobs remain memo keys and dirty metadata remains candidate-only",
    "datasets-owned hash memo schemas bind every authority-relevant profile and invalidator",
    "kit stores and verifies memo bytes while never deciding semantic reuse",
    "raw full-stream CIDs remain distinct from ordered chunk-manifest CIDs",
    "bounded independent hashing is deterministic across completion order and fallback paths",
    "native hashing is byte-identical or returns a typed unavailable result without installation",
    "concurrent immutable puts rehash bytes before reference and cannot publish a root",
    "parallel leaves, levels and categories reproduce the normative serial root exactly",
    "only admitted unchanged branches are reused and uncertainty forces full reconstruction",
    "prepared full and delta contracts have no current-root advancement authority",
    "full preparation freshly verifies every required unit while parallelizing immutable work",
    "delta preparation recomputes every affected path and checks every transition invariant",
    "proof, signature, receipt and integrity checks are bounded and deterministically aggregated",
    "the prepared-seal consumer preserves WAL order, byte rehash, parent CAS and generation fencing",
    "differential roots, crashes, corruption, cancellation and concurrent writers fail closed",
    "fixture closure schemas bind transitive definitions, conftests, hooks, policies and finalizers",
    "collection extracts and memoizes exact fixture closures without executing fixture bodies",
    "fixture instances and injected dependencies use closed reuse and privacy vocabularies",
    "only reviewed adapters commit supported values and all opaque dependencies execute fully",
    "TestExecutionKeyV2 binds every fixture, environment, toolchain, trust and completeness identity",
    "composite phase receipts preserve TestPassStatementV1 and reject incomplete or dishonest phases",
    "the exact V2 key is assembled after setup and before call with normal execution fallback",
    "an admitted call certificate reuses only call while current setup and teardown execute exactly once",
    "whole-item reuse is limited to explicitly pure or replay-safe teardown-compatible populations",
    "workers return bounded intents and only the controller may publish accepted reuse evidence",
    "fixture affinity and proof cost improve placement without omitting tests or merging resource pools",
    "runner signatures bind V2/composite evidence to verifier-selected key, issuer, epoch and policy",
    "aggregate leaves bind the exact selected population, ordering, count, cohorts and trust roots",
    "aggregate public inputs enforce completeness and never upgrade the claim of receipt leaves",
    "only an admitted real backend and key may prove; otherwise production proving is typed unavailable",
    "receipt batches prove asynchronously and incomplete or self-verified batches remain non-authoritative",
    "fixture cohorts and selection roots update only affected proof-forest branches",
    "the fast loop consumes the datasets selector and broadens execution on incomplete dependency data",
    "direct execution profiles remain optional, explicit and limited to qualified deterministic kernels",
    "FastTddLoopController composes frozen source through serial publication with exact evidence",
    "deterministic and symbolic repair routes precede any typed minimal-context model residual",
    "accepted edit-test-proof trajectories become separately verified reusable procedure candidates",
    "typed CLI and service operations call existing authorities and emit deterministic JSON",
    "shadow hashing records exact serial parity and cannot influence authority",
    "shadow reuse and proof predictions still execute the existing authoritative path",
    "protected mode admits only measured exact reuse with complete fallback and reviewed policy",
    "required mode rejects completion without the complete pre/post root and publication chain",
    "the positive and negative end-to-end matrices survive restart, conflict and a related second edit",
    "preregistered cold, warm, full and delta workloads report bytes, resources, roots and commit time",
    "selected pytest and proof loops report phase reuse, batching, forest, publication and model costs",
    "forgery, staleness, poisoning, omission, leakage and self-selection attacks remain rejected",
    "the supervisor itself delivers one bounded improvement through the required evidence chain",
    "current-tree release evidence reports exact results, typed limitations, migration and rollback",
)

W1_RESCUE_CANDIDATES = {
    "PCTDD-001": "e623dd43dbc8f8feb503dd8dea2a6afb4bbd26c0",
    "PCTDD-002": "25b2a4e0fd1ab354a0db5317ec8ea49ce0319a61",
    "PCTDD-003": "37ccf1a42d7bbf0a6cad0a20a7671ddc0cbffac6",
    "PCTDD-004": "2b37146f4f2f354ced02ca5327d0a7d21344f044",
}

PCTDD_004_COMPONENT_COMMIT = "48edb688ac31bc3d05fdd5c8efd7e50ab14b755e"
PCTDD_004_COMPONENT_PARENT = "cfbd381ee6196e818ecd59a438386a60b5d71bd7"

PCTDD_002_EXCLUDED_BASELINE_FAILURES = (
    {
        "node_id": "external/ipfs_accelerate/test/api/test_proof_reuse_locator_first_collection.py::test_plugin_collection_attaches_seed_in_read_mode",
        "observed_outcome": "failed_only_in_combined_predecessor_process",
        "reason_code": "pytest_global_class_identity_collision",
        "treatment": "run the complete locator module in an isolated pytest process; do not count the excluded combined-process observation as acceptance",
        "authoritative_acceptance": False,
    },
    {
        "node_id": "external/ipfs_kit/tests/test_proof_reuse_bootstrap.py::test_direct_node_pickup_with_entry_point_autoload_modes[root-fallback]",
        "observed_outcome": "failed_preexisting_baseline",
        "reason_code": "kit_root_fallback_predecessor_failure",
        "treatment": "exclude only this exact historical node; require repair before protected promotion",
        "authoritative_acceptance": False,
    },
    {
        "node_id": "external/ipfs_kit/tests/test_proof_reuse_bootstrap.py::test_verified_hit_skips_before_fixtures_without_ipfs_or_daemon_touch",
        "observed_outcome": "failed_preexisting_baseline",
        "reason_code": "legacy_skip_semantics_conflict",
        "treatment": "exclude only this exact legacy node; composite-phase work must replace rather than bless skip semantics",
        "authoritative_acceptance": False,
    },
)

TASK_EXTRA_OUTPUTS: dict[int, tuple[str, ...]] = {
    0: (CONTROL_MANIFEST.relative_to(ROOT).as_posix(),),
    49: (
        "benchmarks/agent_supervisor/parallel_content_sealing/pctdd_049_hash_seal_results.json",
    ),
    50: (
        "benchmarks/agent_supervisor/proof_carrying_tdd/pctdd_050_pytest_proof_tdd_results.json",
    ),
    52: (
        "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/fast_tdd/capstone_self_hosting.py",
        "artifacts/parallel_content_sealing_proof_carrying_tdd/capstone/PCTDD-052.json",
    ),
    53: (
        "artifacts/parallel_content_sealing_proof_carrying_tdd/PCTDD-053.release.json",
        "docs/architecture/PARALLEL_CONTENT_SEALING_PROOF_CARRYING_TDD_RELEASE.md",
    ),
}

GOALS: tuple[tuple[str, str, str | None], ...] = (
    ("PCTDD-G000", "Deliver and self-host parallel content sealing and proof-carrying TDD", None),
    ("PCTDD-G010", "Freeze authorities, claims, baselines, and controls", "PCTDD-G000"),
    ("PCTDD-G011", "Inventory current hashing, pytest, proof, and storage paths", "PCTDD-G010"),
    ("PCTDD-G012", "Freeze cold/warm critical-path benchmarks", "PCTDD-G010"),
    ("PCTDD-G013", "Seal identity, trust, and evidence-class boundaries", "PCTDD-G010"),
    ("PCTDD-G020", "Build parallel incremental content preparation", "PCTDD-G000"),
    ("PCTDD-G021", "Canonicalize once and persist verified hash memos", "PCTDD-G020"),
    ("PCTDD-G022", "Add chunk manifests and affected-branch Merkle updates", "PCTDD-G020"),
    ("PCTDD-G023", "Separate parallel seal preparation from serial publication", "PCTDD-G020"),
    ("PCTDD-G030", "Build fixture-aware exact pytest reuse", "PCTDD-G000"),
    ("PCTDD-G031", "Build fixture-definition and fixture-instance identities", "PCTDD-G030"),
    ("PCTDD-G032", "Build staged execution keys and composite phase receipts", "PCTDD-G030"),
    ("PCTDD-G033", "Add pre-setup and post-setup reuse with xdist coordination", "PCTDD-G030"),
    ("PCTDD-G040", "Build batched proof and ZK certification", "PCTDD-G000"),
    ("PCTDD-G041", "Integrate signed runner attestations", "PCTDD-G040"),
    ("PCTDD-G042", "Build aggregate selected-test proof statements and circuits", "PCTDD-G040"),
    ("PCTDD-G043", "Pipeline proof batching and incremental proof-forest sealing", "PCTDD-G040"),
    ("PCTDD-G050", "Integrate the fast TDD loop with supervisor intelligence", "PCTDD-G000"),
    ("PCTDD-G051", "Compose selection, proof reuse, Tactician/Hammer, and repair", "PCTDD-G050"),
    ("PCTDD-G052", "Compile successful TDD trajectories into procedures", "PCTDD-G050"),
    ("PCTDD-G053", "Enforce progressive dogfooding and cognitive-cost accounting", "PCTDD-G050"),
    ("PCTDD-G060", "Qualify security, performance, recovery, and release", "PCTDD-G000"),
    ("PCTDD-G061", "Run adversarial, corruption, concurrency, and privacy gates", "PCTDD-G060"),
    ("PCTDD-G062", "Benchmark, self-host, and publish current-tree release evidence", "PCTDD-G060"),
)


def dependencies() -> dict[str, tuple[str, ...]]:
    d: dict[str, tuple[str, ...]] = {task: () for task in TASKS}
    for n in range(1, 5): d[f"PCTDD-{n:03d}"] = ("PCTDD-000",)
    d.update({
        "PCTDD-005": ("PCTDD-001",), "PCTDD-006": ("PCTDD-001",),
        "PCTDD-007": ("PCTDD-001", "PCTDD-003"), "PCTDD-021": ("PCTDD-002",),
        "PCTDD-023": ("PCTDD-002",), "PCTDD-033": ("PCTDD-002", "PCTDD-003"),
        "PCTDD-008": ("PCTDD-007",), "PCTDD-009": ("PCTDD-005", "PCTDD-006"),
        "PCTDD-010": ("PCTDD-004", "PCTDD-005", "PCTDD-006", "PCTDD-007"),
        "PCTDD-022": ("PCTDD-002", "PCTDD-021"), "PCTDD-024": ("PCTDD-002", "PCTDD-023"),
        "PCTDD-026": ("PCTDD-002", "PCTDD-003", "PCTDD-023"),
        "PCTDD-034": ("PCTDD-026", "PCTDD-033"),
        "PCTDD-011": ("PCTDD-010",), "PCTDD-012": ("PCTDD-005", "PCTDD-008", "PCTDD-010"),
        "PCTDD-013": ("PCTDD-005", "PCTDD-010"), "PCTDD-025": ("PCTDD-021", "PCTDD-023"),
        "PCTDD-032": ("PCTDD-003", "PCTDD-025", "PCTDD-026"),
        "PCTDD-014": ("PCTDD-008", "PCTDD-013"), "PCTDD-015": ("PCTDD-005", "PCTDD-007", "PCTDD-013"),
        "PCTDD-018": ("PCTDD-003", "PCTDD-032"), "PCTDD-027": ("PCTDD-022", "PCTDD-024", "PCTDD-025"),
        "PCTDD-030": ("PCTDD-002", "PCTDD-025", "PCTDD-026"),
        "PCTDD-035": ("PCTDD-003", "PCTDD-034"),
        "PCTDD-016": ("PCTDD-012", "PCTDD-013", "PCTDD-015", "PCTDD-018"),
        "PCTDD-017": ("PCTDD-014", "PCTDD-015", "PCTDD-018"),
        "PCTDD-028": ("PCTDD-027", "PCTDD-032"), "PCTDD-029": ("PCTDD-027", "PCTDD-032"),
        "PCTDD-031": ("PCTDD-004", "PCTDD-022", "PCTDD-030"),
        "PCTDD-036": ("PCTDD-032", "PCTDD-033", "PCTDD-034", "PCTDD-035"),
        "PCTDD-019": ("PCTDD-016", "PCTDD-017", "PCTDD-018"),
        "PCTDD-037": ("PCTDD-014", "PCTDD-036"),
        "PCTDD-038": ("PCTDD-001", "PCTDD-002", "PCTDD-007", "PCTDD-021", "PCTDD-025"),
        "PCTDD-039": ("PCTDD-035",), "PCTDD-020": ("PCTDD-014", "PCTDD-018", "PCTDD-019"),
        "PCTDD-040": ("PCTDD-019", "PCTDD-027", "PCTDD-028", "PCTDD-029", "PCTDD-031", "PCTDD-036", "PCTDD-037", "PCTDD-038"),
        "PCTDD-041": ("PCTDD-040",), "PCTDD-042": ("PCTDD-040", "PCTDD-041"),
        "PCTDD-043": ("PCTDD-036", "PCTDD-040"), "PCTDD-044": ("PCTDD-020", "PCTDD-040"),
        "PCTDD-045": ("PCTDD-028", "PCTDD-036", "PCTDD-044"), "PCTDD-046": ("PCTDD-045",),
        "PCTDD-047": ("PCTDD-046",), "PCTDD-048": ("PCTDD-047",),
        "PCTDD-049": ("PCTDD-020", "PCTDD-048"), "PCTDD-050": ("PCTDD-036", "PCTDD-040", "PCTDD-048"),
        "PCTDD-051": ("PCTDD-048", "PCTDD-049", "PCTDD-050"),
        "PCTDD-052": ("PCTDD-042", "PCTDD-047", "PCTDD-051"),
        "PCTDD-053": ("PCTDD-049", "PCTDD-050", "PCTDD-051", "PCTDD-052"),
    })
    return d


DEPENDENCIES = dependencies()


def goal_for(n: int) -> str:
    if n == 0: return "PCTDD-G010"
    if n in (1, 2): return "PCTDD-G011"
    if n == 3: return "PCTDD-G013"
    if n == 4: return "PCTDD-G012"
    if 5 <= n <= 10: return "PCTDD-G021"
    if 11 <= n <= 14: return "PCTDD-G022"
    if 15 <= n <= 20: return "PCTDD-G023"
    if 21 <= n <= 24: return "PCTDD-G031"
    if 25 <= n <= 27: return "PCTDD-G032"
    if 28 <= n <= 31: return "PCTDD-G033"
    if n == 32: return "PCTDD-G041"
    if 33 <= n <= 35: return "PCTDD-G042"
    if 36 <= n <= 39: return "PCTDD-G043"
    if n in (40, 41): return "PCTDD-G051"
    if n == 42: return "PCTDD-G052"
    if 43 <= n <= 47: return "PCTDD-G053"
    if n in (48, 51): return "PCTDD-G061"
    return "PCTDD-G062"


def owner_for(n: int) -> str:
    if n in {5, 7, 9, 15, 21, 23, 25, 26, 33, 34}:
        return "endomorphosis/ipfs_datasets_py"
    if n in {8, 12, 14, 37}:
        return "endomorphosis/ipfs_kit_py"
    if n in {0, 1, 2, 3, 20, 48, 49, 50, 51, 52, 53}:
        return "cross-repository"
    return "endomorphosis/ipfs_accelerate_py"


def test_target_for(n: int, owner: str | None = None) -> str:
    owner = owner or owner_for(n)
    stem = TASK_TEST_STEMS[n]
    if n == 0:
        return CONTROL_TEST
    if n in {1, 4, 20, 48, 49}:
        if n == 4:
            return "external/ipfs_accelerate/test/api/parallel_content_sealing/test_cold_warm_critical_path.py"
        return f"external/ipfs_accelerate/test/api/parallel_content_sealing/test_pctdd_{n:03d}_{stem}.py"
    if n in {2, 3, 50, 51, 52, 53}:
        return f"external/ipfs_accelerate/test/api/proof_carrying_tdd/test_pctdd_{n:03d}_{stem}.py"
    if owner.endswith("ipfs_datasets_py"):
        return f"external/ipfs_datasets/tests/unit/logic/zkp/pctdd/test_pctdd_{n:03d}_{stem}.py"
    if owner.endswith("ipfs_kit_py"):
        return f"external/ipfs_kit/tests/proof_seal/test_pctdd_{n:03d}_{stem}.py"
    if 21 <= n <= 36 or n in {40, 41, 42, 43, 45, 46, 47}:
        return f"external/ipfs_accelerate/test/api/proof_carrying_tdd/test_pctdd_{n:03d}_{stem}.py"
    return f"external/ipfs_accelerate/test/api/parallel_content_sealing/test_pctdd_{n:03d}_{stem}.py"


def outputs_for(n: int, owner: str | None = None) -> tuple[str, ...]:
    task_id = f"PCTDD-{n:03d}"
    return (
        f"artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/{task_id}.json",
        test_target_for(n, owner),
        *TASK_EXTRA_OUTPUTS.get(n, ()),
    )


def task_directive(n: int) -> str:
    task_id = f"PCTDD-{n:03d}"
    return (
        f"Execute {task_id} through the existing repository authorities and prove that "
        f"{TASK_ASSERTIONS[n]}. Produce {test_target_for(n)} and the unique task receipt; "
        "do not widen identity, proof, storage, execution, scheduler, or publication authority."
    )


def validation_command_for(n: int) -> str:
    return f"python {VALIDATION_DISPATCHER} --task PCTDD-{n:03d}"


def _pytest_profile_command(
    *targets: str,
    evidence_policy: str,
    timeout_seconds: int = 3600,
) -> dict[str, Any]:
    return {
        "argv": ["python", "-m", "pytest", "-q", *targets, "--tb=short"],
        "cwd": ".",
        "timeout_seconds": timeout_seconds,
        "evidence_policy": evidence_policy,
    }


def _baseline_profile_commands(n: int, owner: str) -> list[dict[str, Any]]:
    accelerator_baseline = (
        "external/ipfs_accelerate/test/api/test_agent_supervisor_content_identity_bridge.py",
        "external/ipfs_accelerate/test/api/incremental_sealing/test_trust.py",
    )
    datasets_baseline = (
        "external/ipfs_datasets/tests/unit/logic/software_contracts/test_content_identity.py",
        "external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_statement.py",
    )
    kit_baseline = (
        "external/ipfs_kit/tests/test_proof_certificate_store.py",
        "external/ipfs_kit/tests/test_semantic_state_root_cas.py",
    )
    if n == 1:
        return [
            _pytest_profile_command(
                "external/ipfs_datasets/tests/unit/utils/test_cid_utils.py",
                "external/ipfs_datasets/tests/unit/logic/software_contracts/test_content_identity.py",
                "external/ipfs_datasets/tests/unit/logic/ir_core/test_identity.py",
                "external/ipfs_accelerate/test/api/test_agent_supervisor_content_identity_bridge.py",
                "external/ipfs_accelerate/test/api/test_agent_supervisor_multiformats_identity.py",
                "external/ipfs_kit/tests/test_proof_certificate_store.py",
                "external/ipfs_kit/tests/test_semantic_state_root_cas.py",
                evidence_policy="protected_baseline_regression",
            )
        ]
    if n == 2:
        accelerator_without_locator = (
            "external/ipfs_accelerate/test/api/test_pytest_proof_reuse_item_identity.py",
            "external/ipfs_accelerate/test/api/test_pytest_proof_reuse_plugin.py",
            "external/ipfs_accelerate/test/api/test_pytest_proof_reuse_lookup.py",
            "external/ipfs_accelerate/test/api/test_pytest_proof_reuse_receipt.py",
            "external/ipfs_accelerate/test/api/test_pytest_proof_reuse_xdist.py",
            "external/ipfs_accelerate/test/api/test_proof_reuse_runtime_composition.py",
            "external/ipfs_accelerate/test/api/test_proof_reuse_default_runtime_services.py",
            "external/ipfs_accelerate/test/api/test_proof_reuse_default_identity_services.py",
            "external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_identity.py",
            "external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_identity_vectors.py",
        )
        kit_green_nodes = (
            "external/ipfs_kit/tests/test_proof_reuse_bootstrap.py::test_pyproject_declares_shared_pytest_entry_point",
            "external/ipfs_kit/tests/test_proof_reuse_bootstrap.py::test_direct_node_pickup_with_entry_point_autoload_modes[entry-point]",
            "external/ipfs_kit/tests/test_proof_reuse_bootstrap.py::test_missing_shared_plugin_executes_normally",
            "external/ipfs_kit/tests/test_proof_reuse_bootstrap.py::test_missing_store_and_multiformats_execute_normally",
            "external/ipfs_kit/tests/test_proof_reuse_bootstrap.py::test_explicit_off_mode_executes_normally",
            "external/ipfs_kit/tests/test_proof_reuse_bootstrap.py::test_coverage_execution_remains_available",
        )
        return [
            _pytest_profile_command(
                *accelerator_without_locator,
                evidence_policy="protected_baseline_regression",
            ),
            _pytest_profile_command(
                "external/ipfs_accelerate/test/api/test_proof_reuse_locator_first_collection.py",
                evidence_policy="isolated_predecessor_regression",
            ),
            _pytest_profile_command(
                *kit_green_nodes,
                evidence_policy="explicit_green_predecessor_nodes",
            ),
        ]
    if n == 3:
        return [
            _pytest_profile_command(
                "external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_statement.py",
                "external/ipfs_datasets/tests/unit/logic/zkp/test_test_execution_certificate.py",
                "external/ipfs_datasets/tests/unit_tests/logic/zkp/test_zkp_module.py",
                "external/ipfs_accelerate/test/api/test_proof_reuse_runner_pass_attestation.py",
                "external/ipfs_accelerate/test/api/incremental_sealing/test_trust.py",
                "external/ipfs_accelerate/test/api/incremental_sealing/test_backends.py",
                "external/ipfs_accelerate/test/api/incremental_sealing/test_provers.py",
                evidence_policy="protected_baseline_regression",
            )
        ]
    if owner == "cross-repository":
        return [
            _pytest_profile_command(
                *accelerator_baseline,
                evidence_policy="protected_baseline_regression",
            ),
            _pytest_profile_command(
                *datasets_baseline,
                evidence_policy="protected_baseline_regression",
            ),
            _pytest_profile_command(
                *kit_baseline,
                evidence_policy="protected_baseline_regression",
            ),
        ]
    if owner.endswith("ipfs_datasets_py"):
        targets = datasets_baseline
    elif owner.endswith("ipfs_kit_py"):
        targets = kit_baseline
    else:
        targets = accelerator_baseline
    return [
        _pytest_profile_command(
            *targets,
            evidence_policy="protected_baseline_regression",
        )
    ]


def validation_profiles() -> dict[str, Any]:
    profiles: dict[str, Any] = {}
    for n, task_id in enumerate(TASKS):
        target = test_target_for(n)
        required = _pytest_profile_command(
            target,
            evidence_policy="required_acceptance",
            timeout_seconds=900 if n == 0 else 3600,
        )
        if n == 0:
            commands = [
                required,
                {
                    "argv": ["python", "scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py", "--check-all"],
                    "cwd": ".",
                    "timeout_seconds": 900,
                    "evidence_policy": "operator_validator",
                },
                {
                    "argv": ["python", "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py", "--check-all"],
                    "cwd": ".",
                    "timeout_seconds": 900,
                    "evidence_policy": "operator_validator",
                },
            ]
        else:
            commands = [required, *_baseline_profile_commands(n, owner_for(n))]
        profiles[task_id] = {
            "task_id": task_id,
            "profile_id": f"pctdd-validation/{PLAN_REVISION}/{task_id}@1",
            "shell": False,
            "required_test_target": target,
            "required_acceptance": {
                "controller_owned_independent_validation": True,
                "machine_readable_pytest_phase_evidence": True,
                "disallowed_outcomes": [
                    "failed", "skipped", "xfail", "xpass", "error", "rerun",
                ],
                "worker_authored_test_is_sufficient_alone": False,
            },
            "known_baseline_exclusions": (
                list(PCTDD_002_EXCLUDED_BASELINE_FAILURES) if n == 2 else []
            ),
            "commands": commands,
        }
    return {
        "schema": "pctdd/task-validation-profiles@1",
        "plan_revision": PLAN_REVISION,
        "dispatcher": VALIDATION_DISPATCHER,
        "execution": "argv-only subprocess with shell=False",
        "profiles": profiles,
    }


def g5_migration_inventory() -> dict[str, Any]:
    receipt_only = {
        task_id: {
            "outer_commit": commit,
            "classification": "receipt-observation-only",
            "outer_changed_paths": [
                f"artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/{task_id}.json"
            ],
            "component_commits": {},
            "admitted": False,
            "application_policy": "never cherry-pick the stale outer receipt commit; independently implement or recover component changes and issue fresh g6 evidence",
        }
        for task_id, commit in W1_RESCUE_CANDIDATES.items()
        if task_id != "PCTDD-004"
    }
    receipt_only["PCTDD-004"] = {
        "outer_commit": W1_RESCUE_CANDIDATES["PCTDD-004"],
        "classification": "component-reuse-candidate-only",
        "outer_changed_paths": [
            "artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/PCTDD-004.json",
            "external/ipfs_accelerate",
        ],
        "component_commits": {
            "external/ipfs_accelerate": {
                "commit": PCTDD_004_COMPONENT_COMMIT,
                "prior_gitlink": PCTDD_004_COMPONENT_PARENT,
                "changed_paths": [
                    "ipfs_accelerate_py/agent_supervisor/proof/incremental_sealing/critical_path.py",
                    "test/api/parallel_content_sealing/test_cold_warm_critical_path.py",
                ],
            }
        },
        "admitted": False,
        "application_policy": "never adopt the outer gitlink; cherry-pick or adapt only the nested component diff onto the current supervisor-fix descendant and run fresh g6 validation",
    }
    return {
        "schema": "pctdd/control-generation-migration@1",
        "program_id": NAMESPACE,
        "predecessor": {
            "store_generation": "pctdd-v1-g5",
            "plan_revision": PREDECESSOR_PLAN_REVISION,
            "plan_root_cid": "baguqeeraqwk4z47whu652pvidcaxeyjkp6dmeuxhevmjhkpjehxdpmstsukq",
            "pctdd_000_completion_receipt_cid": "baguqeeray2wlpjlflnaxx7jpynquwhpenm7hk6pwwkxsmxwzr6eopltnccua",
            "bootstrap_event_watermark": 103,
            "source_head": "c488d97ed5665b5744d983fc4a294989df519361",
            "source_tree": "e3fda4eaaecf14a56815f586df05feb94f093979",
            "frozen_database_sha256": "e7aa5935d452f2df2bff462467799a57994771a8971cd20528d56284bd4ec5a5",
            "frozen_database_path": G5_DATABASE.relative_to(ROOT).as_posix(),
            "bootstrap_receipt_sha256": "6c65b2ad424683c110867c8842e46b256af93dc7116f35f2c102a857b6893616",
            "bootstrap_receipt_path": G5_BOOTSTRAP_RECEIPT.relative_to(ROOT).as_posix(),
            "preserved_failed_validation_rescue_branch_count": 29,
        },
        "successor": {
            "store_generation": STORE_GENERATION,
            "plan_revision": PLAN_REVISION,
            "runtime_root": RUNTIME_ROOT,
            "quack_endpoint": QUACK_ENDPOINT,
        },
        "migration_policy": {
            "g5_is_immutable_history": True,
            "copy_task_status_or_acceptance": False,
            "copy_attempt_failures": False,
            "rescue_candidates_are_authority": False,
            "require_fresh_g6_materialization": True,
            "require_independent_g6_validation": True,
            "no_secrets_recorded": True,
        },
        "w1_rescue_candidates": receipt_only,
    }


def scope_for(n: int, owner: str) -> str:
    if n == 0:
        return ", ".join(sorted(PROTECTED_ARTIFACTS))
    if n == 4:
        return (
            "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/"
            "proof/incremental_sealing/critical_path.py, "
            + test_target_for(n, owner)
        )
    if owner.endswith("ipfs_datasets_py"):
        return f"external/ipfs_datasets/ipfs_datasets_py/logic/zkp/pctdd, {test_target_for(n, owner)}"
    if owner.endswith("ipfs_kit_py"):
        return f"external/ipfs_kit/ipfs_kit_py/proof_seal, {test_target_for(n, owner)}"
    if owner == "cross-repository":
        # Never grant an ancestor directory that contains PCTDD-000's sealed
        # operator receipt. Cross-repository workers receive only their exact
        # output manifest, just like the task-store ownership gate.
        return ", ".join(outputs_for(n, owner))
    if 21 <= n <= 32:
        return f"external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse, {test_target_for(n, owner)}"
    if n <= 20 or n in {37, 38, 39}:
        return f"external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/incremental_sealing, {test_target_for(n, owner)}"
    base = f"external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor, {test_target_for(n, owner)}"
    extras = TASK_EXTRA_OUTPUTS.get(n, ())
    return ", ".join((base, *extras))


def predicted_files_for(
    n: int,
    owner: str | None = None,
) -> tuple[str, ...]:
    """Return the stable task-owned write envelope understood by the daemon.

    ``Outputs`` remains the unique exact artifact manifest used by completion
    and output-presence gates.  ``Predicted files`` is the daemon-recognized
    write-scope field and must also include those exact outputs so provider
    and proposal fences see one coherent envelope. Existing source directories
    in ``scope_for`` are authority scopes, not promises to create a new
    directory artifact; output-presence gates continue to use ``Outputs``.
    """

    owner = owner or owner_for(n)
    scope_paths = tuple(
        path.strip()
        for path in scope_for(n, owner).split(",")
        if path.strip()
    )
    return tuple(dict.fromkeys((*outputs_for(n, owner), *scope_paths)))


def rollout_for(n: int) -> str:
    if n <= 43: return "bootstrap"
    if n == 44: return "shadow_hash"
    if n == 45: return "shadow_reuse, shadow_proof"
    if n in {46, 47}: return "protected"
    return "required"


def required_evidence(n: int) -> str:
    core = "exact source commit/tree/gitlinks; changed paths; independent tests; proof/claim class; receipt CID; limitations; verifier admission"
    if n >= 48:
        return core + "; pre_semantic_state_root; pre_proof_seal_root; source_snapshot; overlay_token; hash_preparation_receipt; selected_test_proof_manifest; fixture_test_execution_key_receipts; phase_disposition_receipts; aggregate_proof_or_evidence_tier_receipt; proof_forest_delta; prepared_seal_cid; seal_publication_receipt; post_semantic_state_root; post_proof_seal_root; expected_generation; resulting_generation; rollout_mode_required"
    return core


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""): h.update(block)
    return "sha256:" + h.hexdigest()


def public_origin(origin: str) -> str:
    """Return a source locator only when it cannot expose URL credentials."""

    if not origin or any(ord(character) < 32 or ord(character) == 127 for character in origin):
        raise ValueError("git origin must be a non-empty, single-line public locator")
    if "://" not in origin:
        # Local paths and Git's conventional ``git@example:path`` SSH syntax do
        # not contain URL password/user-info fields. Preserve them verbatim.
        return origin
    parsed = urlsplit(origin)
    if parsed.password is not None or (
        parsed.scheme.lower() in {"http", "https"} and parsed.username is not None
    ):
        raise ValueError("git origin URL contains credentials and cannot be sealed")
    return origin


def theorem_prover_capabilities() -> dict[str, dict[str, Any]]:
    accelerator = ROOT / "external/ipfs_accelerate"
    if str(accelerator) not in sys.path:
        sys.path.insert(0, str(accelerator))
    from ipfs_accelerate_py.agent_supervisor.validation.validation_runtime import (
        build_validation_environment,
    )

    environment = build_validation_environment(os.environ)
    environment["ELAN_NO_UPDATE_CHECK"] = "1"
    result: dict[str, dict[str, Any]] = {}
    for name, command in {
        "lean": ("lean", "--version"),
        "cvc5": ("cvc5", "--version"),
        "coq": ("coqc", "--version"),
    }.items():
        executable = shutil.which(command[0], path=environment.get("PATH", ""))
        installer_discovered = shutil.which(command[0]) is not None
        available = False
        version = ""
        if executable:
            completed = subprocess.run(
                [executable, *command[1:]],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
                timeout=20,
            )
            version_text = (completed.stdout or completed.stderr).strip()
            version = version_text.splitlines()[0] if version_text else ""
            available = completed.returncode == 0
        result[name] = {
            "name": name,
            "available": available,
            "version": version,
            "required": False,
            "classification": (
                "sealed_formal_toolchain_available"
                if available
                else (
                    "installed_unqualified_user_mutable"
                    if installer_discovered
                    else "typed_optional_unavailable_at_capture"
                )
            ),
            "installer_discovered": installer_discovered,
            "provisioning": "ipfs_datasets_py managed theorem-prover installer",
            "admission_note": (
                "installed user-writable shims are discovery evidence only; "
                "supervisor execution requires the current immutable formal-toolchain deployment"
            ),
        }
    return result


def installed_distribution_version(distribution: str) -> str:
    """Capture one installed distribution version or fail before sealing."""

    try:
        version = importlib.metadata.version(distribution).strip()
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError(
            f"required distribution is unavailable while sealing: {distribution}"
        ) from exc
    if not version:
        raise RuntimeError(
            f"required distribution has no version while sealing: {distribution}"
        )
    return version


def duckdb_extension_capability(
    name: str,
    *,
    required_for_launch: bool,
) -> dict[str, Any]:
    """Probe an already-installed DuckDB extension without installing it."""

    result: dict[str, Any] = {
        "name": name,
        "available": False,
        "loaded": False,
        "version": "",
        "extension_directory": "",
        "install_path": "",
        "install_sha256": "",
        "required_for_launch": required_for_launch,
        "error": "",
    }
    try:
        import duckdb

        connection = duckdb.connect(":memory:")
        try:
            # LOAD is deliberately local-only.  Never use INSTALL here: the
            # dependency seal records current capability rather than mutating
            # the toolchain while measuring it.
            connection.execute(f"LOAD {name}")
            row = connection.execute(
                "SELECT extension_version, installed, loaded, install_mode, "
                "installed_from, install_path FROM duckdb_extensions() "
                "WHERE extension_name = ?",
                [name],
            ).fetchone()
            if row:
                install_path = Path(str(row[5] or "")).resolve()
                extension_directory = (
                    install_path.parents[2]
                    if install_path.is_file() and len(install_path.parents) >= 3
                    else None
                )
                result.update(
                    {
                        "version": str(row[0] or ""),
                        "available": bool(row[1]),
                        "loaded": bool(row[2]),
                        "install_mode": str(row[3] or ""),
                        "installed_from": str(row[4] or ""),
                        "install_path": str(install_path) if install_path.is_file() else "",
                        "extension_directory": (
                            str(extension_directory)
                            if extension_directory is not None
                            else ""
                        ),
                        "install_sha256": (
                            sha256(install_path) if install_path.is_file() else ""
                        ),
                    }
                )
            else:
                result["available"] = True
                result["loaded"] = True
        finally:
            connection.close()
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def write(path: Path, value: str | dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = value if isinstance(value, str) else json.dumps(value, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")


def render_plan() -> str:
    waves = [
        "W0 PCTDD-000", "W1 PCTDD-001|002|003|004", "W2 PCTDD-005|006|007|021|023|033",
        "W3 PCTDD-008|009|010|022|024|026|034", "W4 PCTDD-011|012|013|025|032",
        "W5 PCTDD-014|015|018|027|030|035", "W6 PCTDD-016|017|028|029|031|036",
        "W7 PCTDD-019|037|038|039", "W8 PCTDD-020|040", "W9 PCTDD-041|042|043",
        "W10 PCTDD-044", "W11 PCTDD-045", "W12 PCTDD-046", "W13 PCTDD-047",
        "W14 PCTDD-048", "W15 PCTDD-049|050", "W16 PCTDD-051", "W17 PCTDD-052", "W18 PCTDD-053",
    ]
    return f"""# Parallel Content Sealing and Proof-Carrying TDD — {PLAN_REVISION}

Status: sealed bootstrap control amendment. Namespace: `{NAMESPACE}`.

## V1.1 control amendment and generation migration

This revision amends `{PREDECESSOR_PLAN_REVISION}` after g5 exposed a
control-plane defect: non-executable validation prose was materialized as a
command and repeated database claims could outlive the intended attempt cap.
The g5 database, event watermark, accepted PCTDD-000 receipt, failures, and 29
rescue branches remain immutable history. Nothing in g5 is reopened or
silently promoted. The successor is a fresh `{STORE_GENERATION}` authority at
`{RUNTIME_ROOT}`, served by `{QUACK_ENDPOINT}`.

Every task names one protected validation profile through a task-bound
dispatcher. Profiles contain argv arrays only and execute with `shell=False`.
Prose, shell operators, unresolved aliases, mismatched task IDs, incomplete
profile coverage, and profile drift fail before provider dispatch. Recorded W1
rescue commits are exact-reuse candidates only and require independent g6
source/profile/policy validation before admission.

## Outcome and invariant

Build and self-host a fail-closed fast TDD route across the existing accelerator, datasets, and kit authorities. The normative order is: verified exact content reuse; parallel immutable hash/seal preparation; exact datasets-owned semantic selection; fixture-aware execution-key construction; current setup; verified call reuse or current call; current teardown; signed receipt; asynchronous aggregate ZK certification; incremental proof-forest update; serial seal publication; deterministic repair/procedure reuse; minimal-context LLM only for a typed residual.

Parallel work may prepare immutable candidates and independently verify hashes, signatures, proofs, leaves, branches, and blocks. Final ordered WAL append, persisted-byte rehash, generation fence, expected-parent CAS, and current-root publication remain serial, controller-owned, and fail closed.

## Claim boundaries

- A CID establishes exact byte identity under its versioned canonicalization/multicodec/multihash profile, not execution or semantics. A Git blob OID is a verified memo lookup key only; filesystem metadata is candidate-only. A chunk manifest does not replace the raw full-stream CID.
- A signed execution receipt is an allowlisted issuer assertion under verifier-selected policy/key/epoch/revocation state, not independent execution proof.
- An aggregate ZK proof establishes only that the committed admitted receipt set satisfies the selected circuit. It does not prove CPython execution and cannot exceed or upgrade its leaf evidence.
- A direct execution proof establishes only the declared machine/program/committed inputs and outputs.
- An incremental seal commits an accepted parent plus complete valid changed/reused units. `TestPassStatementV1` remains unchanged; composite and aggregate successors are versioned.
- Simulated, mock, structural, or integrity-only proof paths are never production admission. Unknown dependency completeness broadens execution and proving.

## Authority reconciliation

`ipfs_datasets_py` owns deterministic semantic/proof schemas, selection, fixture/test identities, statement meaning, and commitment codecs. `ipfs_kit_py` owns verified immutable storage, hash/branch candidate records, proof forest persistence, WAL, recovery, and root CAS without deciding semantic admission. `ipfs_accelerate_py` owns source freezing, scheduling, pytest/xdist execution, receipt admission, proof batching, fast-loop composition, repair/context/procedure integration, and operational acceptance. Existing IncrementalProofSealer, proof-reuse plugin, semantic-state selector, signed runner attestations, TestPass statements, proof store/WAL/CAS, verification planner, Tactician/Hammer, semantic compression, and procedure compiler are predecessors to extend—not duplicate.

The operational task authority is DuckDB through one authenticated loopback Quack owner. DuckLake is a rebuildable, non-authoritative history/analytics projection that cannot schedule, admit, complete, or block a task. Markdown is sealed bootstrap intent only; PCTDD-000 becomes complete solely through evidence-gated DuckDB CAS.

## Technical workstreams

1. Canonicalize once into `PreparedCanonicalBlock@1`, rehash wherever trust crosses, memoize exact source/profile mappings, preserve raw SHA/CID, and add separate chunk manifests.
2. Bound filesystem readers, canonicalizers, hashers, verifiers, provers, store writers, and Merkle reducers. Preserve completion-order-independent output.
3. Build full/delta prepared seals and affected-branch Merkle updates without publication authority; shorten the existing serial sealer commit.
4. Derive collection seed, fixture-definition closure, reviewed fixture-instance commitment, `TestExecutionKeyV2`, and final trace. Opaque or incomplete adapters force full execution.
5. Make post-setup/pre-call reuse primary while running current teardown/finalizers. Pre-setup reuse stays narrowly pure/replay-safe. Never label proof reuse as pytest skip.
6. Bind composite phase receipts to signed runner policy; batch selected populations into aggregate statements/proofs asynchronously; keep direct CPython proof optional.
7. Compose exact selection, receipts, forest delta, seal, repair, compressed residual context, and proof-carrying procedure compilation in `FastTddLoopController@1`.

## Rollout and waves

The closed rollout is `bootstrap -> shadow_hash -> shadow_reuse -> shadow_proof -> protected -> required`. Promotion requires zero identity divergence, false phase reuse, stale reuse, selection false-negative regression, simulated admission, self-authority, unauthorized publication, lost update, escaped critical mutation, or secret/witness leak. Missing performance targets produce non-promotion, never weakened safety.

```text
{os.linesep.join(waves)}
```

Each worker receives a unique lease/fence/worktree, exact task CID and tree, bounded allowed paths/resources/context, verifier-owned acceptance, and one unique receipt. Shared exports, registries, plugin hooks, schemas, gitlinks, scheduler controls, and release evidence serialize through the current merge authority.

## Verification and benchmarks

Identity tests require serial/parallel/native byte and root equality, strict decoding, profile separation, and Git/chunk identity boundaries. Memo/Merkle tests cover corruption, dirty overlays, mode/type changes, full fallback, stale parents/snapshots, concurrent writers, crash phases, and recovery. Pytest tests cover closure invalidation, privacy-safe adapters, setup/call/teardown truth, xdist controller authority, signatures, aggregate completeness, cancellation, malicious workers, and import safety.

Preregistered hash workloads cover small/mixed/large files, clean and dirty states, 1/10/50% deltas, cold/warm memo, full/delta seal, bounded 1/2/4/8/16 workers, local and reproducible slow I/O. TDD workloads cover all fixture/reuse/proof classes. Supervisor metrics count model calls/tokens/context and exact avoidance causes. Targets are >=90% fewer warm unchanged bytes, >=50% faster 1% delta preparation, >=30% faster warm selected loops, >=25% fewer repeat general-model repairs, and >=30% smaller median model context, all subordinate to zero-regression floors.

## Terminal and rollback

Required completion means every mandatory task has accepted or explicitly permitted typed terminal evidence, validators pass, identities match, the required-mode capstone has complete pre/post roots and publication receipt, and final roots verify transitively. No unavailable prover/key ceremony/performance result may be fabricated. Rollback disables policy promotion, invalidates successor evidence, restores full hashing/execution/reproof fallback, and uses existing WAL/CAS recovery without rewriting predecessor history.
"""


def render_objectives() -> str:
    children: dict[str, list[str]] = {gid: [] for gid, _, _ in GOALS}
    parents = {gid: parent for gid, _title, parent in GOALS}
    for gid, _, parent in GOALS:
        if parent: children[parent].append(gid)

    def descends_from(candidate: str, ancestor: str) -> bool:
        current: str | None = candidate
        while current is not None:
            if current == ancestor:
                return True
            current = parents[current]
        return False

    lines = [f"# PCTDD objective hierarchy\n\nNamespace: `{NAMESPACE}`. Revision: `{PLAN_REVISION}` (amending `{PREDECESSOR_PLAN_REVISION}`). DuckDB/Quack becomes live authority after evidence-gated materialization; this file is non-authoritative bootstrap intent.\n"]
    for gid, title, parent in GOALS:
        producing = [
            task
            for task in TASKS
            if descends_from(goal_for(int(task[-3:])), gid)
        ]
        lines += [f"## {gid} {title}", "", "- Status: active", f"- Parent goal: {parent or 'none'}", "- Depends on: none", "- Priority: P0", f"- Track: {gid.lower()}", f"- Goal: {title} while preserving exact identity, claim, storage, execution, and publication authorities.", f"- Producing tasks: {', '.join(producing) if producing else 'derived through child goals'}", f"- Evidence: artifacts/parallel_content_sealing_proof_carrying_tdd/goals/{gid}.json", "- Acceptance: All producing tasks and child goals have independently admitted current-tree evidence or an explicitly permitted typed terminal, with no weakened safety floor.", ""]
    return "\n".join(lines)


def render_board() -> str:
    lines = [f"""# PCTDD supervisor task board

Namespace: `{NAMESPACE}`. Revision: `{PLAN_REVISION}` (fresh `{STORE_GENERATION}`, preserving g5 as immutable predecessor history). This is a sealed bootstrap projection; DuckDB through Quack owns live status. Markdown is non-authoritative and is not completion authority. PCTDD-000 remains `todo` here and is completed only by an evidence-gated task-store transaction.

## Execution invariants

- Preserve exact canonical profiles and extend existing authorities only. Simulated proof is never admitted as production; an aggregate claim cannot exceed leaf evidence.
- Final ordered WAL and generation-bearing current-root CAS are serial and fail closed. Workers prepare immutable candidates and never publish authority.
- Workers cannot edit protected controls, approve their own output, select acceptance policy, or mark completion.
"""]
    for n, (task, title) in enumerate(TASKS.items()):
        owner = owner_for(n)
        scope = ", ".join(predicted_files_for(n, owner))
        test_target = test_target_for(n, owner)
        output = ", ".join(outputs_for(n, owner))
        deps = ", ".join(DEPENDENCIES[task]) or "none"
        operator = n == 0
        completion = "operator_evidence" if operator else "independent_evidence_and_review"
        schedulable = str(not operator).lower()
        lane = "operator" if operator else f"pctdd-lane-{n % 4}"
        protected = ", ".join(sorted(PROTECTED_ARTIFACTS)) if operator else "all scheduler protected_paths; no worker edits"
        no_model = "operator inventory, deterministic validators, source seals, and scheduler dry-run" if operator else "exact reuse -> deterministic analysis/tests/proofs -> symbolic repair -> procedure reuse"
        validation = validation_command_for(n)
        rescue = W1_RESCUE_CANDIDATES.get(task, "none")
        rescue_policy = (
            f"{rescue}; exact-reuse candidate only; independently revalidate against exact g6 source/profile/policy"
            if rescue != "none" else "none"
        )
        if operator:
            acceptance = (
                f"Execute sealed profile pctdd-validation/{PLAN_REVISION}/{task}@1 including {test_target}, both protected validators, canonical configured-board preflight, and implementation dry-run at one exact clean HEAD/tree; then record their digests in the staged operator-seal receipt before the DuckDB CAS may complete PCTDD-000."
            )
        else:
            acceptance = (
                f"A grok-only worker supplies the patch and {test_target}; the controller-owned validation authority independently executes sealed profile pctdd-validation/{PLAN_REVISION}/{task}@1, admits the exact output manifest, and verifies protected baseline regressions before the task-completion CAS. The implementation model cannot fall back to the completion authority or approve its own output. The worker-authored test alone is never sufficient; required acceptance has machine-readable pytest phase evidence with zero failed, skipped, xfail, xpass, error, or rerun outcomes. Verify that {TASK_ASSERTIONS[n]}; record typed unavailable cases without changing claim meaning or self-approving."
            )
        if n == 47:
            acceptance += (
                " This protected transition must install and independently validate the schema-aware required-mode completion gate; it does not fabricate a required-mode evidence chain for itself."
            )
        elif n >= 48:
            acceptance += (
                " Completion is rejected unless the PCTDD-047 schema-aware gate independently admits the complete required-mode pre/post-root and serial-publication evidence chain."
            )
        lines += [f"## {task} {title}", "", "- Status: todo", f"- Completion mode: {completion}", f"- Is schedulable: {schedulable}", f"- Operator only: {str(operator).lower()}", "- Priority: P0", f"- Track: {goal_for(n)}", f"- Depends on: {deps}", f"- Bundle: pctdd/{goal_for(n).lower()}/{task.lower()}", f"- Parallel lane: {lane}", "- Resource class: cpu-medium; explicit prover/hash/store reservations when required", "- Timeout seconds: 21600", "- Provider role: operator-only" if operator else "- Provider role: grok-only", f"- Owning repository: {owner}", f"- Directive: {task_directive(n)}", f"- Exact inputs: {PLAN_REVISION}; exact source forest; predecessor APIs; dependency seal; dependency receipts: {deps}", f"- Predecessor rescue candidate: {rescue_policy}", f"- Outputs: {output}", f"- Predicted files: {scope}", f"- Predicted symbols: {title.replace(' ', '')}; versioned @1/@2 contracts only where the task introduces them", "- Interfaces: existing datasets semantic/proof contracts; kit immutable store/WAL/CAS; accelerator execution/scheduler/admission; adapters only", "- Preconditions: Exact clean leased worktree; current parent receipts; complete source/environment/policy/toolchain binding; no self-approval", f"- Declared effects: Modify only {scope}; emit immutable receipt; request reviewed merge through existing authority", f"- Validation profile: pctdd-validation/{PLAN_REVISION}/{task}@1", f"- Validation: {validation}", f"- Required evidence: {required_evidence(n)}", f"- Acceptance criteria: {acceptance}", "- Conflict policy: Serialize shared schemas, exports, registries, plugin hooks, gitlinks, WAL/CAS, and release artifacts through the current merge queue; rebase and revalidate after any overlap.", "- LLM context budget bytes: 24000", "- Context policy: send only affected source, contracts, counterexample, and current receipts", f"- No-model route: {no_model}", "- Model fallback: none for implementation; provider unavailability is a typed, non-consuming retry or external capability terminal, and no model output can approve completion", f"- Rollout mode: {rollout_for(n)}", f"- Protected paths: {protected}", "- Known limitations: Production ZK/key ceremony and optional native/direct-execution profiles may be typed unavailable; unknown dependency or fixture semantics force full fallback.", f"- Goal id: {goal_for(n)}", f"- Board namespace: {NAMESPACE}", ""]
    return "\n".join(lines)


PROTECTED_ARTIFACTS = (
    "docs/architecture/PARALLEL_CONTENT_SEALING_PROOF_CARRYING_TDD_PLAN.md",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd.objectives.md",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd.todo.md",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/repository_baseline.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/authority_matrix.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/overlap_gap_matrix.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/hash_identity_inventory.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/hashing_critical_path.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/pytest_identity_inventory.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/fixture_adapter_inventory.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/proof_claim_matrix.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/zkp_backend_inventory.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/storage_recovery_inventory.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/benchmark_preregistration.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/g5_migration_inventory.json",
    "config/parallel_content_sealing_proof_carrying_tdd_dependencies.seal.json",
    "config/agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json",
    "config/parallel_content_sealing_proof_carrying_tdd_benchmark.json",
    "config/parallel_content_sealing_proof_carrying_tdd_validation_profiles.json",
    "config/parallel_content_sealing_proof_carrying_tdd_control_manifest.json",
    "artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/PCTDD-000.json",
    "scripts/generate_parallel_content_sealing_proof_carrying_tdd_controls.py",
    "scripts/run_parallel_content_sealing_proof_carrying_tdd_validation.py",
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py",
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py",
    "scripts/materialize_parallel_content_sealing_proof_carrying_tdd_program.py",
    "scripts/ops/agent_supervisor/parallel_content_sealing_proof_carrying_tdd.py",
    "test/api/parallel_content_sealing/test_pctdd_g6_control_amendment.py",
)


def source_record(name: str, relative: str) -> dict[str, Any]:
    repo = ROOT / relative
    head = git("rev-parse", "HEAD", cwd=repo)
    tree = git("rev-parse", "HEAD^{tree}", cwd=repo)
    gitlink_fields = git("ls-tree", "HEAD", relative).split()
    gitlink = gitlink_fields[2] if len(gitlink_fields) >= 3 else ""
    status = git("status", "--porcelain=v1", "--untracked-files=all", cwd=repo)
    return {
        "name": name,
        "path": relative,
        "origin": public_origin(git("remote", "get-url", "origin", cwd=repo)),
        "head": head,
        "tree": tree,
        "gitlink": gitlink,
        "gitlink_matches_nested_head": gitlink == head,
        "dirty": bool(status),
        "status_sha256": "sha256:" + hashlib.sha256(status.encode("utf-8")).hexdigest(),
        "authority": True,
    }


def render_config() -> dict[str, Any]:
    base = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    return {
        "schema": "ipfs_accelerate_py.agent_supervisor.parallel-content-sealing-proof-carrying-tdd.scheduler_config@1",
        "program_identifier": NAMESPACE, "board_namespace": NAMESPACE, "accepted_plan_revision_alias": PLAN_REVISION,
        "taskboard_path": BOARD.relative_to(ROOT).as_posix(), "objectives_path": OBJECTIVES.relative_to(ROOT).as_posix(), "plan_path": PLAN.relative_to(ROOT).as_posix(),
        "validator_path": "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py", "dependency_validator_path": "scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py", "materializer_path": "scripts/materialize_parallel_content_sealing_proof_carrying_tdd_program.py", "validation_profile_path": VALIDATION_PROFILES.relative_to(ROOT).as_posix(), "validation_dispatcher_path": VALIDATION_DISPATCHER,
        "task_prefix": "PCTDD-", "goal_prefix": "PCTDD-G", "root_goal_id": "PCTDD-G000", "merge_target_branch": BRANCH,
        "control_amendment": {"revision": PLAN_REVISION, "amends": PREDECESSOR_PLAN_REVISION, "reason": "replace unresolved validation prose and isolate retry-bounded g6 authority", "migration_inventory": G5_MIGRATION_INVENTORY.relative_to(ROOT).as_posix(), "fresh_materialization_required": True, "copy_predecessor_acceptance": False},
        "source_binding": {"accelerator_required_ancestor": base, "accelerator_planning_revision": base, "accelerator_planning_tree": tree, "accelerator_required_branch": BRANCH, "bootstrap_task_source": "duckdb", "ipfs_accelerate_submodule_path": "external/ipfs_accelerate", "ipfs_accelerate_planning_revision": git("rev-parse", "HEAD", cwd=ROOT / "external/ipfs_accelerate"), "ipfs_accelerate_planning_tree": git("rev-parse", "HEAD^{tree}", cwd=ROOT / "external/ipfs_accelerate"), "ipfs_datasets_submodule_path": "external/ipfs_datasets", "ipfs_datasets_planning_revision": git("rev-parse", "HEAD", cwd=ROOT / "external/ipfs_datasets"), "ipfs_datasets_planning_tree": git("rev-parse", "HEAD^{tree}", cwd=ROOT / "external/ipfs_datasets"), "ipfs_kit_submodule_path": "external/ipfs_kit", "ipfs_kit_planning_revision": git("rev-parse", "HEAD", cwd=ROOT / "external/ipfs_kit"), "ipfs_kit_planning_tree": git("rev-parse", "HEAD^{tree}", cwd=ROOT / "external/ipfs_kit"), "require_initialized_gitlinks": True, "require_superproject_gitlink_equals_nested_head": True, "require_clean_nested_worktree_at_task_start": True, "require_origin_main_as_ancestor": False, "record_recursive_repository_forest_at_launch": True, "changed_revision_requires_fresh_inventory_and_baseline": True, "planning_revision_is_runtime_completion_evidence": False},
        "initial_projection": {"task_count": 54, "task_dependency_count": sum(map(len, DEPENDENCIES.values())), "completed_task_ids": [], "ready_task_ids": [], "post_operator_completed_task_ids": ["PCTDD-000"], "post_operator_ready_task_ids": [f"PCTDD-{n:03d}" for n in range(1, 5)], "blocked_task_ids": [], "terminal_task_id": "PCTDD-053", "goal_count": 24, "root_goal_id": "PCTDD-G000"},
        "database_program": {"authority_mode": "quack", "task_source_kind": "duckdb", "endpoint_secret_handle": "env://IPFS_ACCELERATE_AGENT_QUACK_TOKEN", "quack_endpoint": QUACK_ENDPOINT, "store_id": f"{RUNTIME_ROOT}/control.duckdb", "store_generation": STORE_GENERATION, "schema_revision": "1", "event_store_path": f"{RUNTIME_ROOT}/events", "runtime_registry_path": f"{RUNTIME_ROOT}/registry", "worktree_root": f"{RUNTIME_ROOT}/worktrees", "export_profile": "pctdd-v1", "failover_policy": "fail_closed", "explicit_legacy": False, "predecessor_store_generation": "pctdd-v1-g5", "predecessor_is_read_only_history": True},
        "operational_control_plane": {"name": "DuckDB + Quack + non-authoritative DuckLake", "duckdb_role": "authoritative transactional goals/tasks/CAS/fences/receipts/events", "quack_role": "authenticated exclusive loopback state owner", "ducklake_role": "rebuildable analytics/history projection", "direct_multi_process_duckdb_file_open_permitted": False, "automatic_file_fallback_permitted": False, "outage_policy": "fail_closed", "markdown_is_bootstrap_only": True},
        "ducklake_projection_program": {"mode": "enabled_non_authoritative", "authority": False, "may_grant_authority": False, "scheduling_prerequisite": False, "acceptance_prerequisite": False, "completion_prerequisite": False, "catalog_path": f"{RUNTIME_ROOT}/ducklake/catalog.duckdb", "data_path": f"{RUNTIME_ROOT}/ducklake/data", "logical_datasets": ["bootstrap_history", "g5_migration_history"], "outage_policy": "typed unavailable and replayable; never block DuckDB authority"},
        "max_lanes": 4, "strict_task_sharding": True, "idle_lane_work_stealing": "", "exit_when_all_tracks_terminal": False, "objective_refill_enabled": False, "codebase_refill_enabled": False, "objective_goal_refinement_enabled": False, "retry_budget_guardrail_enabled": True, "dependency_guardrail_enabled": True, "reconciliation_guardrail_enabled": True,
        "poll_interval_seconds": 5, "daemon_interval_seconds": 20, "check_interval_seconds": 20, "stale_seconds": 1800, "watchdog_startup_grace_seconds": 600, "max_restarts": 3, "max_task_attempts": 2, "implementation_retry_budget": 1, "validation_retry_budget": 2, "merge_retry_budget": 2, "implementation_timeout_seconds": 7200, "implementation_max_timeout_seconds": 21600, "implementation_log_stall_seconds": 1200,
        "worktree_submodule_paths": ["external/ipfs_accelerate", "external/ipfs_datasets", "external/ipfs_kit"], "protected_paths": list(PROTECTED_ARTIFACTS),
        "runtime_paths": {"root": RUNTIME_ROOT, "state": f"{RUNTIME_ROOT}/state", "worktrees": f"{RUNTIME_ROOT}/worktrees", "merge_queue": f"{RUNTIME_ROOT}/merge-queue", "logs": f"{RUNTIME_ROOT}/logs", "evidence": f"{RUNTIME_ROOT}/evidence", "quack_owner": f"{RUNTIME_ROOT}/quack-owner", "generated_runtime_artifacts_are_completion_authority": False},
        "lanes": [{"index": n, "name": f"pctdd-lane-{n}", "strict_shard_remainder": n, "initial_focus": focus} for n, focus in enumerate(("content-identities", "pytest-fixtures", "proof-batching", "integration-qualification"))],
        "provider": {"provider_id": "grok_cli", "model_id": "grok-4.6", "implementation_fallback_authorized": False, "completion_authority": "controller_owned_sealed_validation_and_database_cas", "max_concurrency": 4, "secrets_from_environment_only": True, "secrets_in_argv_prompts_logs_or_receipts": False},
        "resource_budgets": {"filesystem_readers": 4, "canonicalization_workers": 4, "sha_cid_workers": 4, "proof_verifiers": 2, "prover_workers": 1, "immutable_store_writers": 2, "merkle_reducers": 4, "test_workers": 4},
        "safety_floors": {"identity_divergence": 0, "false_test_phase_reuse": 0, "stale_authoritative_reuse": 0, "selection_false_negative_regressions": 0, "simulated_proof_admissions": 0, "model_created_proof_authority_completion": 0, "unauthorized_root_publications": 0, "lost_concurrent_updates": 0, "escaped_critical_seeded_defects": 0, "secret_witness_leaks": 0},
        "rollout_gates": ["bootstrap", "shadow_hash", "shadow_reuse", "shadow_proof", "protected", "required"], "benchmark_freeze": "config/parallel_content_sealing_proof_carrying_tdd_benchmark.json", "required_evidence_per_task": "board.required_evidence", "current_tree_revalidation_before_launch": True,
    }


def benchmark_config() -> dict[str, Any]:
    return {"schema": "pctdd/benchmark-preregistration@1", "status": "frozen_before_implementation", "revision": PLAN_REVISION, "safety_floors": render_config()["safety_floors"], "hash_seal_workloads": {"layouts": ["many_small", "mixed_repository", "few_large"], "changes": ["clean", "1_percent", "10_percent", "50_percent", "dirty_overlay"], "cache": ["cold_memo", "warm_memo"], "seal": ["full_checkpoint", "delta_seal"], "workers": [1, 2, 4, 8, 16], "storage": ["local_ssd", "reproducible_slow_io"]}, "pytest_tdd_workloads": ["no_fixture", "pure", "module_session", "parameterized", "temp_filesystem", "transactional_db", "clock_rng", "service_simulation", "opaque_dynamic", "teardown_finalizer", "xdist", "slow_fast_calls", "proof_hit_miss", "changed_fixture", "changed_plugin_conftest", "changed_environment"], "metrics": ["wall_time", "cpu_time", "peak_rss", "files_opened", "bytes_read", "bytes_hashed", "memo_hits_rejections", "root_equality", "phase_times", "selection_recall", "mutation_escapes", "proof_batch_cost", "wal_cas_time", "model_calls_tokens_context", "calls_avoided_by_reuse_procedure_repair"], "targets": {"warm_bytes_reread_reduction_percent": 90, "warm_1_percent_delta_prepare_reduction_percent": 50, "warm_selected_loop_reduction_percent": 30, "repeat_general_llm_call_reduction_percent": 25, "median_model_context_reduction_percent": 30}, "anti_gaming": "No hidden failures, uncounted work, skipped validation, oracle leakage, or denominator exclusions."}


def inventories() -> dict[str, dict[str, Any]]:
    sources = [source_record("ipfs_accelerate_py", "external/ipfs_accelerate"), source_record("ipfs_datasets_py", "external/ipfs_datasets"), source_record("ipfs_kit_py", "external/ipfs_kit")]
    return {
        "repository_baseline.json": {"schema": "pctdd/repository-baseline@2", "captured_utc": "2026-08-29T08:21:45Z", "planning_root": str(ROOT), "control_generation_input_head": git("rev-parse", "HEAD"), "control_generation_input_tree": git("rev-parse", "HEAD^{tree}"), "branch": git("branch", "--show-current"), "sources": sources, "all_governed_sources_clean_and_gitlink_exact": all(not item["dirty"] and item["gitlink_matches_nested_head"] for item in sources), "dirty_user_tree_preserved": True, "original_user_tree_evidence": {"captured_utc": "2026-08-28", "root_status_sha256": "f0a737302e4455c55e60edc28403da4f339e9b64811cc0b0dcf0c87e2d9629b3", "root_diff_sha256": "72f6c22550da009960d570f8b5128077c9160ef2d4ae2d5cc75498ab69e08fb7", "root_untracked_list_sha256": "c20615c1a314943dca33d6d1764014096ebbd9632a5404b55992a97883a2a8ac", "accelerate_status_sha256": "c261a97a9d4d91da96af386077e5cdf9c1532273614a73911d8c07a063913798", "datasets_status_sha256": "a1b4619c21ab5c19d90aa666b48d10d7f5034a2abe2ce57e0f854892429d9c83"}, "evidence_note": "The fresh g6 observation records actual source dirtiness and exact outer gitlinks; original user-tree hashes remain preserved without copying user content."},
        "authority_matrix.json": {"schema": "pctdd/authority-matrix@1", "canonical_semantic_and_statement_authority": "ipfs_datasets_py", "verified_storage_wal_cas_authority": "ipfs_kit_py", "execution_scheduling_admission_authority": "ipfs_accelerate_py", "task_transaction_authority": "DuckDB via exclusive authenticated Quack owner", "analytics_projection": "DuckLake non-authoritative", "markdown": "non-authoritative bootstrap", "forbidden_duplicates": ["proof system", "canonical profile", "CID system", "pytest runner", "test selector", "proof cache", "block store", "WAL", "current-root store", "agent framework", "scheduler", "worktree system", "provider router", "merge engine"]},
        "overlap_gap_matrix.json": {"schema": "pctdd/overlap-gap@1", "entries": [{"capability": "IncrementalProofSealer full/delta/WAL/CAS", "owner": "ipfs_accelerate_py + ipfs_kit_py", "classification": "available_with_caveats", "successor": "prepared-seal consumer adapter"}, {"capability": "pytest proof reuse/DI/xdist controller publication", "owner": "ipfs_accelerate_py", "classification": "available_with_caveats", "successor": "fixture-staged V2 identity/composite phases"}, {"capability": "semantic selection", "owner": "ipfs_datasets_py consumed by accelerate", "classification": "available", "successor": "adapter only"}, {"capability": "verified persistent hash memo", "owner": "datasets contract + kit store", "classification": "partial", "successor": "versioned records/store"}, {"capability": "aggregate selected-test ZK", "owner": "datasets statement + accelerate backend", "classification": "missing", "successor": "versioned aggregate statement; typed unavailable without admitted production key"}, {"capability": "FastTddLoopController", "owner": "ipfs_accelerate_py", "classification": "partial", "successor": "compose current authorities"}]},
        "hash_identity_inventory.json": {"schema": "pctdd/hash-identity@1", "rules": ["CID is exact byte identity under a versioned profile", "Git blob OID is memo lookup key only", "filesystem metadata nominates a candidate only", "chunk manifest does not replace raw full-stream CID", "ordinary SHA-256 of one stream is not composed from independent chunk hashes"], "preserve": ["canonical bytes", "codec", "multicodec", "multihash", "CID version", "multibase", "ordering", "normalization"]},
        "hashing_critical_path.json": {"schema": "pctdd/hashing-critical-path@1", "current_path": ["source discovery", "canonical serialization", "SHA/CID", "proof verification", "Merkle", "immutable store", "serial WAL/CAS"], "observed_gaps": ["duplicate serialization/hashing requires task instrumentation", "unverified metadata cannot authorize reuse", "parallel immutable preparation absent or partial"], "candidate_methods": ["hashlib.file_digest", "readinto reusable buffer", "safe mmap", "threaded independent SHA", "process canonicalization", "optional qualified native batch"]},
        "pytest_identity_inventory.json": {"schema": "pctdd/pytest-identity@1", "authority_paths": ["external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/plugin.py", "external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/receipt.py", "external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/runner_pass_attestation.py"], "current": ["locator-first seed", "runtime trace", "DI lookup/store/provider/issuer", "controller-owned xdist publication"], "gap": "exact fixture-instance key becomes safely authoritative only after current setup; add pre-call V2 key and honest composite phase receipt"},
        "fixture_adapter_inventory.json": {"schema": "pctdd/fixture-adapter-inventory@1", "closed_reuse_classes": ["pure", "deterministic_snapshot", "transactional", "idempotent_external", "effectful_replayable", "effectful_nonreplayable", "opaque"], "default": "opaque", "initial_review_candidates": ["immutable scalar", "frozen canonical record", "path-independent temp directory root", "transaction baseline", "clock", "RNG", "service image/config/corpus", "explicit environment projection"], "secret_rule": "commit provider identity/version/epoch/policy, never secret bytes"},
        "proof_claim_matrix.json": {"schema": "pctdd/proof-claim-matrix@1", "IntegrityCommitment": {"establishes": "exact bytes/digest/CID/Merkle inclusion", "does_not": "execution or semantics"}, "SignedExecutionReceipt": {"establishes": "trusted issuer assertion under explicit verifier policy", "does_not": "independent faithful execution"}, "ReceiptAggregationZkProof": {"establishes": "committed admitted receipt population satisfies circuit", "does_not": "CPython execution and cannot exceed leaf evidence"}, "DirectExecutionProof": {"establishes": "declared machine/program/inputs executed", "does_not": "broader correctness"}, "IncrementalCommitSeal": {"establishes": "accepted parent plus complete valid changed/reused units", "does_not": "arbitrary repository correctness"}, "legacy": "TestPassStatementV1 remains unchanged", "production": "simulated or structural proof cannot be admitted"},
        "zkp_backend_inventory.json": {"schema": "pctdd/zkp-backend-inventory@1", "groth16_binary": {"classification": "real_backend_binary_present_unqualified", "sha256": "sha256:7cd14f8810fda8c16bf8a3b3ad02fda67b3c85ff0fc05883e21825781e33ce15", "production_admitted": False, "reason": "presence and key bytes do not establish ceremony/allowlist/current public-input binding"}, "provekit": {"classification": "adapter_source_present", "production_admitted": False}, "simulated": {"classification": "simulated", "production_admitted": False}, "direct_cpython": {"classification": "research_only", "production_admitted": False}, "ordinary_inner_loop": "signed receipts permitted by explicit policy; ZK asynchronous"},
        "storage_recovery_inventory.json": {"schema": "pctdd/storage-recovery@1", "existing": ["immutable proof-seal persistence", "ordered WAL", "current-pointer compare-and-swap", "stale-parent rejection", "crash recovery"], "authority": "kit stores/verifies bytes; accelerate admits proof/test meaning", "required_invariant": "parallel immutable preparation has no publication authority; final ordered WAL and generation-bearing current-root CAS remain serial and fail closed"},
        "benchmark_preregistration.json": benchmark_config(),
        "g5_migration_inventory.json": g5_migration_inventory(),
    }


def render_control_manifest() -> dict[str, Any]:
    excluded = {
        CONTROL_MANIFEST.relative_to(ROOT).as_posix(),
        SEAL.relative_to(ROOT).as_posix(),
    }
    artifacts = {
        path: sha256(ROOT / path)
        for path in sorted(PROTECTED_ARTIFACTS)
        if path not in excluded and (ROOT / path).is_file()
    }
    return {
        "schema": "pctdd/operator-control-manifest@1",
        "program_id": NAMESPACE,
        "plan_revision": PLAN_REVISION,
        "task_id": "PCTDD-000",
        "completion_authority": "DatabaseTaskSource evidence plus compare-and-set after staged seal-controls",
        "completion_prerequisites": [
            "required-acceptance pytest phase receipt",
            "dependency validator valid=true",
            "board validator valid=true",
            "configured-board preflight valid=true",
            "configured-board implementation dry-run success",
            "one exact clean source HEAD/tree for every prerequisite",
        ],
        "ordinary_worker_may_modify": False,
        "manifest_is_completion_receipt": False,
        "dependency_seal_must_hash_this_manifest": True,
        "protected_control_hashes_before_manifest_and_seal": artifacts,
    }


def render_seal() -> dict[str, Any]:
    artifacts = {
        path: sha256(ROOT / path)
        for path in REQUIRED_HASHED
        if (ROOT / path).is_file()
    }
    python = Path(sys.executable).resolve()
    capabilities: dict[str, Any] = {
        "quack": duckdb_extension_capability(
            "quack", required_for_launch=True
        ),
        "ducklake": duckdb_extension_capability(
            "ducklake", required_for_launch=False
        ),
        **theorem_prover_capabilities(),
    }
    return {
        "schema": "pctdd/dependency-source-seal@1",
        "status": "sealed",
        "board_namespace": NAMESPACE,
        "plan_revision": PLAN_REVISION,
        "amends_plan_revision": PREDECESSOR_PLAN_REVISION,
        "store_generation": STORE_GENERATION,
        "predecessor_generation": "pctdd-v1-g5",
        "migration_inventory": G5_MIGRATION_INVENTORY.relative_to(ROOT).as_posix(),
        "artifacts": artifacts,
        "sources": [
            source_record("ipfs_accelerate_py", "external/ipfs_accelerate"),
            source_record("ipfs_datasets_py", "external/ipfs_datasets"),
            source_record("ipfs_kit_py", "external/ipfs_kit"),
        ],
        "environment": {
            "python": {
                "name": "python",
                "executable": str(python),
                "version": platform.python_version(),
                "sha256": sha256(python),
            },
            "pytest_version": installed_distribution_version("pytest"),
            "pytest_xdist_version": installed_distribution_version("pytest-xdist"),
            "duckdb_version": installed_distribution_version("duckdb"),
            "capabilities": capabilities,
        },
        "proof_backends": inventories()["zkp_backend_inventory.json"],
    }


REQUIRED_HASHED = (
    "docs/architecture/PARALLEL_CONTENT_SEALING_PROOF_CARRYING_TDD_PLAN.md",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd.objectives.md",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd.todo.md",
    *(f"docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/{name}" for name in ("repository_baseline.json", "authority_matrix.json", "overlap_gap_matrix.json", "hash_identity_inventory.json", "hashing_critical_path.json", "pytest_identity_inventory.json", "fixture_adapter_inventory.json", "proof_claim_matrix.json", "zkp_backend_inventory.json", "storage_recovery_inventory.json", "benchmark_preregistration.json", "g5_migration_inventory.json")),
    "config/agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json",
    "config/parallel_content_sealing_proof_carrying_tdd_benchmark.json",
    "config/parallel_content_sealing_proof_carrying_tdd_validation_profiles.json",
    "config/parallel_content_sealing_proof_carrying_tdd_control_manifest.json",
    "artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/PCTDD-000.json",
    "scripts/generate_parallel_content_sealing_proof_carrying_tdd_controls.py",
    "scripts/run_parallel_content_sealing_proof_carrying_tdd_validation.py",
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py",
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py",
    "scripts/materialize_parallel_content_sealing_proof_carrying_tdd_program.py",
    "scripts/ops/agent_supervisor/parallel_content_sealing_proof_carrying_tdd.py",
    "test/api/parallel_content_sealing/test_pctdd_g6_control_amendment.py",
)


def main() -> int:
    if len(TASKS) != 54 or len(GOALS) != 24 or len(TASK_TEST_STEMS) != 54 or len(TASK_ASSERTIONS) != 54: raise SystemExit("sealed cardinality changed")
    governed_sources = [
        source_record("ipfs_accelerate_py", "external/ipfs_accelerate"),
        source_record("ipfs_datasets_py", "external/ipfs_datasets"),
        source_record("ipfs_kit_py", "external/ipfs_kit"),
    ]
    unsafe = [
        item["path"]
        for item in governed_sources
        if item["dirty"] or not item["gitlink_matches_nested_head"]
    ]
    if unsafe:
        raise RuntimeError(
            "refusing to generate from dirty or gitlink-mismatched governed sources: "
            + ", ".join(unsafe)
        )
    write(PLAN, render_plan()); write(OBJECTIVES, render_objectives()); write(BOARD, render_board())
    write(CONFIG, render_config()); write(BENCHMARK, benchmark_config())
    write(VALIDATION_PROFILES, validation_profiles())
    for name, value in inventories().items(): write(INVENTORY / name, value)
    for path, title in ((ROOT / "test/api/parallel_content_sealing/README.md", "Parallel content sealing API qualification"), (ROOT / "test/api/proof_carrying_tdd/README.md", "Proof-carrying TDD API qualification"), (ROOT / "benchmarks/agent_supervisor/parallel_content_sealing/README.md", "Parallel content sealing benchmarks"), (ROOT / "benchmarks/agent_supervisor/proof_carrying_tdd/README.md", "Proof-carrying TDD benchmarks")):
        write(path, f"# {title}\n\nProtected bootstrap placeholder. Implementation and measured results are owned by the corresponding PCTDD worker tasks; no result is inferred from this directory.\n")
    write(ROOT / "artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/PCTDD-000.json", {"schema": "pctdd/operator-control-receipt@1", "task_id": "PCTDD-000", "board_namespace": NAMESPACE, "plan_revision": PLAN_REVISION, "amends_plan_revision": PREDECESSOR_PLAN_REVISION, "store_generation": STORE_GENERATION, "predecessor_generation": "pctdd-v1-g5", "migration_inventory": G5_MIGRATION_INVENTORY.relative_to(ROOT).as_posix(), "status": "sealed_pending_evidence_gated_database_completion", "markdown_non_authoritative": True, "completion_authority": "DatabaseTaskSource.record_evidence plus compare_and_set_status through the DuckDB/Quack control plane", "dependency_seal": SEAL.relative_to(ROOT).as_posix(), "claim": "This tracked receipt identifies the V1.1/g6 operator control package; it does not itself complete the task or promote any g5 result."})
    write(CONTROL_MANIFEST, render_control_manifest())
    write(SEAL, render_seal())
    print(json.dumps({"namespace": NAMESPACE, "tasks": len(TASKS), "goals": len(GOALS), "dependencies": sum(map(len, DEPENDENCIES.values())), "sealed_artifacts": len(render_seal()["artifacts"])}, sort_keys=True))
    return 0


if __name__ == "__main__": raise SystemExit(main())

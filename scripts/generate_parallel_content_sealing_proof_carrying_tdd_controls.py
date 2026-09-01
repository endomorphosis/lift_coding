#!/usr/bin/env python3
"""Generate the protected PCTDD control program from one reviewed source."""

from __future__ import annotations

import argparse
import functools
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "parallel-content-sealing-proof-carrying-tdd-v1"
PLAN_REVISION = "PCTDD-PLAN-V1.1"
PREDECESSOR_PLAN_REVISION = "PCTDD-PLAN-V1"
HISTORICAL_STORE_GENERATION = "pctdd-v1-g6"
HISTORICAL_RUNTIME_ROOT = (
    "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g6"
)
G7_STORE_GENERATION = "pctdd-v1-g7"
G7_RUNTIME_ROOT = (
    "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g7"
)
G8_STORE_GENERATION = "pctdd-v1-g8"
G8_RUNTIME_ROOT = (
    "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g8"
)
STORE_GENERATION = "pctdd-v1-g9"
RUNTIME_ROOT = "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g9"
QUACK_ENDPOINT = "quack:127.0.0.1:27278"
SOURCE_MIGRATION_REVISION = "PCTDD-SOURCE-G7"
PROVIDER_ROUTE_MIGRATION_REVISION = "PCTDD-SOURCE-PROVIDER-G8"
DESCENDANT_SOURCE_MIGRATION_REVISION = "PCTDD-DESCENDANT-SOURCE-G9"
G7_CONTROL_SOURCE_ANCHOR_HEAD = "c8917d039e3f4598a7d29643c621e341318197da"
G7_CONTROL_SOURCE_ANCHOR_TREE = "c3e061b62caa3ad0c35c7e167242694a8fec171c"
CONTROL_SOURCE_ANCHOR_HEAD = "3be981e55320fba49c4b8395086cea65c8ac571e"
CONTROL_SOURCE_ANCHOR_TREE = "74e3f2aa0f738b442fbc275a78039223fb11ec34"
BRANCH = "agent/parallel-content-sealing-proof-carrying-tdd-v1-g9"
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
G6_SOURCE_MIGRATION_INVENTORY = INVENTORY / "g6_source_migration_inventory.json"
G7_PROVIDER_ROUTE_MIGRATION_INVENTORY = (
    INVENTORY / "g7_provider_route_migration_inventory.json"
)
G8_TO_G9_DESCENDANT_SOURCE_INVENTORY = (
    INVENTORY / "g8_to_g9_descendant_source_inventory.json"
)
G8_RESOLVED_GUARDRAIL_ARCHIVE = INVENTORY / "g8_resolved_guardrail_archive.json"
CONTROL_MANIFEST = ROOT / "config/parallel_content_sealing_proof_carrying_tdd_control_manifest.json"
G5_DATABASE = ROOT / "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g5/control.duckdb"
G5_BOOTSTRAP_RECEIPT = ROOT / "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g5/evidence/bootstrap/pctdd-bootstrap.json"
G6_DATABASE = ROOT / HISTORICAL_RUNTIME_ROOT / "control.duckdb"
G6_BOOTSTRAP_RECEIPT = (
    ROOT / HISTORICAL_RUNTIME_ROOT / "evidence/bootstrap/pctdd-bootstrap.json"
)
G6_STOPPED_STATUS = (
    ROOT / HISTORICAL_RUNTIME_ROOT / "quack-owner/quack-state-server.status.json"
)
G7_DATABASE = ROOT / G7_RUNTIME_ROOT / "control.duckdb"
G7_GENERATION_RECEIPT = ROOT / G7_RUNTIME_ROOT / "source-migration-receipt.json"
G7_STOPPED_STATUS = (
    ROOT / G7_RUNTIME_ROOT / "quack-owner/quack-state-server.status.json"
)
G8_DATABASE = ROOT / G8_RUNTIME_ROOT / "control.duckdb"
G8_GENERATION_RECEIPT = (
    ROOT / G8_RUNTIME_ROOT / "source-provider-route-migration-receipt.json"
)
G8_STOPPED_STATUS = (
    ROOT / G8_RUNTIME_ROOT / "quack-owner/quack-state-server.status.json"
)
SOURCE_MIGRATION_MODULE = "scripts/pctdd_g7_source_binding_successor.py"
SOURCE_MIGRATION_TEST = (
    "test/api/parallel_content_sealing/test_pctdd_g7_source_binding_successor.py"
)
PROVIDER_ROUTE_MIGRATION_MODULE = "scripts/pctdd_g8_provider_route_successor.py"
PROVIDER_ROUTE_MIGRATION_TEST = (
    "test/api/parallel_content_sealing/test_pctdd_g8_provider_route_successor.py"
)
DESCENDANT_SOURCE_MIGRATION_MODULE = "scripts/pctdd_g9_descendant_source_successor.py"
DESCENDANT_SOURCE_MIGRATION_TEST = (
    "test/api/parallel_content_sealing/test_pctdd_g9_descendant_source_successor.py"
)
ORPHAN_RECOVERY_REGRESSION_TEST = (
    "test/api/parallel_content_sealing/test_pctdd_g9_orphan_recovery_regressions.py"
)
QUACK_LIFECYCLE_CONTROL_TEST = (
    "test/api/parallel_content_sealing/test_pctdd_quack_lifecycle_wrapper.py"
)
QUACK_ENSURE_SERVICE_TEMPLATE = (
    "config/parallel_content_sealing_proof_carrying_tdd_ensure.service.in"
)
QUACK_USER_SYSTEMD_CONTROL = (
    "scripts/ops/agent_supervisor/"
    "parallel_content_sealing_proof_carrying_tdd_user_systemd.py"
)
QUACK_USER_SYSTEMD_CONTROL_TEST = (
    "test/api/parallel_content_sealing/test_pctdd_user_systemd_ensure.py"
)
SOURCE_MIGRATION_CONTROL_PATHS = (
    "artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/PCTDD-000.json",
    "config/agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json",
    "config/parallel_content_sealing_proof_carrying_tdd_control_manifest.json",
    "config/parallel_content_sealing_proof_carrying_tdd_dependencies.seal.json",
    "docs/architecture/PARALLEL_CONTENT_SEALING_PROOF_CARRYING_TDD_PLAN.md",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/g6_source_migration_inventory.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/repository_baseline.json",
    "external/ipfs_accelerate",
    "scripts/generate_parallel_content_sealing_proof_carrying_tdd_controls.py",
    "scripts/materialize_parallel_content_sealing_proof_carrying_tdd_program.py",
    "scripts/ops/agent_supervisor/parallel_content_sealing_proof_carrying_tdd.py",
    SOURCE_MIGRATION_MODULE,
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py",
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py",
    CONTROL_TEST,
    SOURCE_MIGRATION_TEST,
    QUACK_LIFECYCLE_CONTROL_TEST,
)
PROVIDER_ROUTE = {
    "primary_provider_id": "grok_cli",
    "primary_model_id": "grok-4.6",
    "fallback_provider_id": "codex",
    "fallback_model_id": "gpt-5.6-terra",
    "fallback_trigger": "primary_quota_exhausted",
    "fallback_reasoning_effort": "medium",
    "implementation_fallback_authorized": True,
}
G7_PRE_EFFECT_LOG_PATHS = {
    "PCTDD-001": (
        f"{G7_RUNTIME_ROOT}/state/lane-0/"
        "pctdd_lane_0_database_portal_attempts/327e6d38324c1e4e6469994b/"
        "implementation-logs/pctdd-001-attempt-1.log"
    ),
    "PCTDD-029": (
        f"{G7_RUNTIME_ROOT}/state/lane-1/"
        "pctdd_lane_1_database_portal_attempts/55209a7479fa7b02bd88d64a/"
        "implementation-logs/pctdd-029-attempt-1.log"
    ),
}
PROVIDER_ROUTE_MIGRATION_CONTROL_PATHS = (
    "artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/PCTDD-000.json",
    "config/agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json",
    "config/parallel_content_sealing_proof_carrying_tdd_control_manifest.json",
    "config/parallel_content_sealing_proof_carrying_tdd_dependencies.seal.json",
    "docs/architecture/PARALLEL_CONTENT_SEALING_PROOF_CARRYING_TDD_PLAN.md",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/g7_provider_route_migration_inventory.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/repository_baseline.json",
    "external/ipfs_accelerate",
    "scripts/generate_parallel_content_sealing_proof_carrying_tdd_controls.py",
    "scripts/materialize_parallel_content_sealing_proof_carrying_tdd_program.py",
    PROVIDER_ROUTE_MIGRATION_MODULE,
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py",
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py",
    CONTROL_TEST,
    PROVIDER_ROUTE_MIGRATION_TEST,
)
DESCENDANT_SOURCE_MIGRATION_CONTROL_PATHS = tuple(
    sorted(
        set(PROVIDER_ROUTE_MIGRATION_CONTROL_PATHS)
        | {
            "docs/architecture/parallel_content_sealing_proof_carrying_tdd.objectives.md",
            "docs/architecture/parallel_content_sealing_proof_carrying_tdd.todo.md",
            "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/g8_to_g9_descendant_source_inventory.json",
            "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/g8_resolved_guardrail_archive.json",
            "config/parallel_content_sealing_proof_carrying_tdd_benchmark.json",
            "config/parallel_content_sealing_proof_carrying_tdd_validation_profiles.json",
            "scripts/ops/agent_supervisor/parallel_content_sealing_proof_carrying_tdd.py",
            DESCENDANT_SOURCE_MIGRATION_MODULE,
            DESCENDANT_SOURCE_MIGRATION_TEST,
            ORPHAN_RECOVERY_REGRESSION_TEST,
            VALIDATION_DISPATCHER,
            SOURCE_MIGRATION_MODULE,
            SOURCE_MIGRATION_TEST,
            QUACK_LIFECYCLE_CONTROL_TEST,
            QUACK_ENSURE_SERVICE_TEMPLATE,
            QUACK_USER_SYSTEMD_CONTROL,
            QUACK_USER_SYSTEMD_CONTROL_TEST,
            "external/ipfs_datasets",
            "external/ipfs_kit",
        }
    )
)
PCTDD_DUCKDB_EXTENSION_DIRECTORY_ENV = (
    "IPFS_ACCELERATE_PCTDD_DUCKDB_EXTENSION_DIRECTORY"
)


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
            "store_generation": HISTORICAL_STORE_GENERATION,
            "plan_revision": PLAN_REVISION,
            "runtime_root": HISTORICAL_RUNTIME_ROOT,
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


def _source_migration_module() -> Any:
    path = ROOT / SOURCE_MIGRATION_MODULE
    spec = importlib.util.spec_from_file_location(
        "pctdd_g7_source_binding_successor_inventory", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the protected g7 source-migration module")
    accelerator = str(ROOT / "external/ipfs_accelerate")
    if accelerator not in sys.path:
        sys.path.insert(0, accelerator)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _g6_coordination_stores(
    captured: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    settlements: dict[int, dict[str, Any]] = {
        0: {
            "task_alias": "PCTDD-001",
            "task_cid": "baguqeera3ce62yl3w5ar5ygfoh76tmjzzojm5qfhvirjjjuqeserigpa2cra",
            "control_revision": 15,
            "attempt_id": "attempt:6743f55697cf4fc281712cf77a8f6fec",
            "claim_id": "claim:e468be9408284fa0a03724ee067a11d9",
            "lease_id": "lease:5516aa2e9ef649f099419ce77eafc7c3",
            "owner_session_id": "embedded-store:aa8373fcda60e36bd6300fc27e6b2a6c",
            "fencing_token": 6,
            "fence_epoch": 6,
            "dispatch_outcome": "started",
            "dispatch_body": {"resumed_from": "deferred"},
            "automatic_retry_admitted": False,
            "old_result_reusable": False,
        },
        1: {
            "task_alias": "PCTDD-029",
            "task_cid": "baguqeera2s4tz4myfd7egggeqdj3swxcxfrgws236z7rb7idmmn5jegnbgva",
            "control_revision": 5,
            "attempt_id": "attempt:a365561afbac46f680b27f7e0cf5527e",
            "claim_id": "claim:b4288022fe5c45b68988018384405bce",
            "lease_id": "lease:d827fd4a0c9a4d019483a5e680e14d51",
            "owner_session_id": "embedded-store:44dc846d44d5a59744347de494f628bd",
            "fencing_token": 2,
            "fence_epoch": 2,
            "dispatch_outcome": "deferred",
            "dispatch_body": {"exception_type": "DatabasePortalBridgeDeferred"},
            "automatic_retry_admitted": False,
            "old_result_reusable": False,
        },
    }
    if [int(record.get("lane", -1)) for record in captured] != [0, 1, 2, 3]:
        raise RuntimeError("fenced g6 capture returned an unexpected lane population")
    records: list[dict[str, Any]] = []
    for lane, value in enumerate(captured):
        record = dict(value)
        if lane in settlements:
            record["settlement"] = settlements[lane]
        records.append(record)
    return records


@functools.lru_cache(maxsize=1)
def g6_source_migration_inventory() -> dict[str, Any]:
    """Return the accepted g6->g7 inventory byte-for-byte from g7 history."""

    relative = G6_SOURCE_MIGRATION_INVENTORY.relative_to(ROOT).as_posix()
    result = subprocess.run(
        ["git", "show", f"{CONTROL_SOURCE_ANCHOR_HEAD}:{relative}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("cannot read the accepted historical g6 migration inventory")
    try:
        value = json.loads(result.stdout)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError("historical g6 migration inventory is malformed") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema")
        != "pctdd/g6-source-binding-migration-inventory@1"
        or value.get("historical_task_definitions_preserved") is not True
    ):
        raise RuntimeError("historical g6 migration inventory claim differs")
    return value


def _provider_route_migration_module() -> Any:
    path = ROOT / PROVIDER_ROUTE_MIGRATION_MODULE
    spec = importlib.util.spec_from_file_location(
        "pctdd_g8_provider_route_successor_inventory", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the protected g8 provider-route module")
    accelerator = str(ROOT / "external/ipfs_accelerate")
    scripts = str(ROOT / "scripts")
    for entry in (accelerator, scripts):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@functools.lru_cache(maxsize=1)
def g7_provider_route_migration_inventory() -> dict[str, Any]:
    """Read the accepted g7->g8 inventory from the immutable g9 anchor."""

    relative = G7_PROVIDER_ROUTE_MIGRATION_INVENTORY.relative_to(ROOT).as_posix()
    result = subprocess.run(
        ["git", "show", f"{CONTROL_SOURCE_ANCHOR_HEAD}:{relative}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("cannot read accepted historical g7 provider-route inventory")
    try:
        value = json.loads(result.stdout)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError("historical g7 provider-route inventory is malformed") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema") != "pctdd/g7-provider-route-migration-inventory@1"
        or value.get("historical_completed_task_definitions_preserved") is not True
    ):
        raise RuntimeError("historical g7 provider-route inventory claim differs")
    return value


def _descendant_source_migration_module() -> Any:
    path = ROOT / DESCENDANT_SOURCE_MIGRATION_MODULE
    spec = importlib.util.spec_from_file_location(
        "pctdd_g9_descendant_source_successor_inventory", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load protected g9 descendant-source module")
    for entry in (str(ROOT / "external/ipfs_accelerate"), str(ROOT / "scripts")):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@functools.lru_cache(maxsize=1)
def g8_to_g9_descendant_source_inventory() -> dict[str, Any]:
    try:
        value = json.loads(G8_TO_G9_DESCENDANT_SOURCE_INVENTORY.read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("g8 to g9 descendant-source inventory is unavailable") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema") != "pctdd/g8-to-g9-descendant-source-inventory@1"
        or value.get("capture_status")
        not in {"pending_stopped_g8_capture", "sealed_stopped_g8_capture"}
    ):
        raise RuntimeError("g8 to g9 descendant-source inventory claim differs")
    return value


def resolved_guardrail_archive() -> dict[str, Any]:
    try:
        value = json.loads(G8_RESOLVED_GUARDRAIL_ARCHIVE.read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("resolved g8 guardrail archive is unavailable") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema") != "pctdd/resolved-generated-guardrail-archive@1"
        or value.get("all_resolved") is not True
        or value.get("source_board_task_ids") != ["PCTDD-054", "PCTDD-055", "PCTDD-056"]
    ):
        raise RuntimeError("resolved g8 guardrail archive claim differs")
    return value


def descendant_source_policy() -> dict[str, Any]:
    inventory = g8_to_g9_descendant_source_inventory()
    policy = {
        "schema": "pctdd/descendant-source-successor-materialization@1",
        "migration_revision": DESCENDANT_SOURCE_MIGRATION_REVISION,
        "prior_store_generation": G8_STORE_GENERATION,
        "target_store_generation": STORE_GENERATION,
        "prior_runtime_root": G8_RUNTIME_ROOT,
        "target_runtime_root": RUNTIME_ROOT,
        "target_quack_endpoint": QUACK_ENDPOINT,
        "receipt_marker": "descendant-source-migration-receipt.json",
        "capture_status": inventory["capture_status"],
        "stopped_predecessor_capture": inventory.get("stopped_predecessor_capture"),
        "control_source_anchor_head": CONTROL_SOURCE_ANCHOR_HEAD,
        "control_source_anchor_tree": CONTROL_SOURCE_ANCHOR_TREE,
        "operator_control_paths": list(DESCENDANT_SOURCE_MIGRATION_CONTROL_PATHS),
        "governed_gitlinks": {
            relative: git("rev-parse", "HEAD", cwd=ROOT / relative)
            for relative in (
                "external/ipfs_accelerate",
                "external/ipfs_datasets",
                "external/ipfs_kit",
            )
        },
        "expected_task_aliases": [f"PCTDD-{index:03d}" for index in range(54)],
        "generated_guardrail_policy": {
            "markdown_is_bootstrap_only": True,
            "discovery_and_event_evidence_preserved": True,
            "generated_task_projection": "disabled_for_sealed_board",
            "retry_budget_guardrail_enabled": False,
            "dependency_guardrail_enabled": False,
            "reconciliation_guardrail_enabled": False,
        },
        "copy_policy": {
            "copied": ["authoritative_control_store", "coordination_history"],
            "not_copied": [
                "execution_observation", "provider_attempt_store", "ducklake",
                "read_replica", "logs", "owner_runtime", "worktrees", "merge_state",
            ],
            "publication": "private_stage_hash_verify_no_overwrite_marker_last",
            "g8_remains_read_only_history": True,
        },
        "orphan_terminal_recovery": {
            "schema": "pctdd/orphan-terminal-migration-recovery-policy@1",
            "candidate_task_aliases": ["PCTDD-001", "PCTDD-031", "PCTDD-034"],
            "receipt_marker": (
                "descendant-source-orphan-terminal-recovery-receipt.json"
            ),
            "prepared_receipt": (
                ".descendant-source-orphan-terminal-recovery-prepared.json"
            ),
            "validation_dispatcher": VALIDATION_DISPATCHER,
            "validation_profile_path": VALIDATION_PROFILES.relative_to(ROOT).as_posix(),
            "validation_profiles": {
                alias: f"pctdd-validation/{PLAN_REVISION}/{alias}@1"
                for alias in ("PCTDD-001", "PCTDD-031", "PCTDD-034")
            },
            "prior_store_generation": G8_STORE_GENERATION,
            "target_store_generation": STORE_GENERATION,
            "timeout_seconds": 21_600,
            "one_shot": True,
            "requires_exact_source_binding": True,
            "requires_exact_stopped_capture": True,
            "requires_offline_owner_fence": True,
            "green_transition": "blocked_to_completed",
            "non_green_transition": "blocked_to_retrying",
            "coordination_completion_required": True,
        },
    }
    _descendant_source_migration_module().validate_pending_policy(
        {"descendant_source_successor_materialization": policy}
    )
    return policy


def capture_g9_inputs() -> dict[str, Any]:
    """Capture stopped g8 only on the explicit operator finalization pass."""

    existing = g8_to_g9_descendant_source_inventory()
    if existing.get("capture_status") == "sealed_stopped_g8_capture":
        # A crash after the inventory write but before all derived controls
        # were regenerated is recoverable without reopening the predecessor.
        if existing.get("migration_admitted") is not True or not isinstance(
            existing.get("stopped_predecessor_capture"), dict
        ):
            raise RuntimeError("sealed g9 capture inventory is incomplete")
        return existing
    module = _descendant_source_migration_module()
    capture = module.capture_stopped_descendant_authority(
        root=ROOT,
        control_path=G8_DATABASE.relative_to(ROOT).as_posix(),
        generation_receipt_path=G8_GENERATION_RECEIPT.relative_to(ROOT).as_posix(),
        status_path=G8_STOPPED_STATUS.relative_to(ROOT).as_posix(),
        coordination_paths=[
            f"{G8_RUNTIME_ROOT}/state/lane-{lane}/quack-lane-coordination.duckdb"
            for lane in range(4)
        ],
        guardrail_archive_path=G8_RESOLVED_GUARDRAIL_ARCHIVE.relative_to(ROOT).as_posix(),
    )
    value = {
        "schema": "pctdd/g8-to-g9-descendant-source-inventory@1",
        "program_id": NAMESPACE,
        "capture_status": "sealed_stopped_g8_capture",
        "migration_admitted": True,
        "historical_completed_task_definitions_preserved": True,
        "historical_completions_revalidated_for_integrity_not_reissued": True,
        "resolved_guardrail_archive": G8_RESOLVED_GUARDRAIL_ARCHIVE.relative_to(ROOT).as_posix(),
        "stopped_predecessor_capture": capture,
        "final_capture_command": (
            "python scripts/generate_parallel_content_sealing_proof_carrying_tdd_controls.py "
            "--capture-g9-inputs"
        ),
        "operator_note": (
            "Exact stopped g8 anchors captured under the canonical offline owner fence; "
            "commit regenerated controls at one clean descendant source before migration."
        ),
    }
    write(G8_TO_G9_DESCENDANT_SOURCE_INVENTORY, value)
    g8_to_g9_descendant_source_inventory.cache_clear()
    return value


def scope_for(n: int, owner: str) -> str:
    if n == 0:
        # The accepted V1.1 task definition remains byte-for-byte historical.
        # New g7 operator controls are protected by the scheduler/manifest,
        # not retroactively inserted into PCTDD-000's task body.
        return ", ".join(sorted(V11_TASKBOARD_PROTECTED_ARTIFACTS))
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


def _datasets_on_path() -> None:
    datasets = ROOT / "external/ipfs_datasets"
    if str(datasets) not in sys.path:
        sys.path.insert(0, str(datasets))


def probe_managed_theorem_prover(
    name: str,
    argv: tuple[str, ...],
    *,
    install: bool,
) -> dict[str, Any]:
    """Resolve Lean/CVC5/Coq through the ipfs_datasets_py lazy installer.

    Capture may install missing default-on tools.  Validation only discovers
    already-managed executables and never downloads.
    """

    _datasets_on_path()
    from ipfs_datasets_py.logic.external_provers.lazy_installer import (
        ensure_prover_executable,
        find_executable,
    )

    discovered = find_executable(argv[0])
    executable = (
        ensure_prover_executable(
            name,
            reason=f"PCTDD {name} theorem-prover via ipfs_datasets_py lazy installer",
        )
        if install
        else discovered
    )
    available = False
    version = ""
    error = ""
    install_path = ""
    if executable:
        install_path = str(Path(executable).resolve())
        command_environment = os.environ.copy()
        command_environment["ELAN_NO_UPDATE_CHECK"] = "1"
        command_environment["PATH"] = os.pathsep.join(
            [str(Path(executable).parent), command_environment.get("PATH", "")]
        )
        try:
            completed = subprocess.run(
                [executable, *argv[1:]],
                cwd=ROOT,
                env=command_environment,
                text=True,
                capture_output=True,
                check=False,
                timeout=20,
            )
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        else:
            version_text = (completed.stdout or completed.stderr).strip()
            version = version_text.splitlines()[0] if version_text else ""
            available = completed.returncode == 0
            if not available:
                error = f"exit {completed.returncode}: {version_text[:300]}"
    return {
        "name": name,
        "available": available,
        "version": version,
        "required": False,
        "classification": (
            "ipfs_datasets_py_lazy_installer_available"
            if available
            else (
                "installed_unqualified_user_mutable"
                if bool(discovered)
                else "typed_optional_unavailable_at_capture"
            )
        ),
        "installer_discovered": bool(discovered or executable),
        "install_path": install_path,
        "error": error,
        "provisioning": "ipfs_datasets_py managed theorem-prover installer",
        "admission_note": (
            "ipfs_datasets_py lazy installer is the provisioning authority; "
            "managed Lean/CVC5/Coq executables are admitted when they run"
        ),
    }


def theorem_prover_capabilities() -> dict[str, dict[str, Any]]:
    return {
        name: probe_managed_theorem_prover(name, command, install=True)
        for name, command in {
            "lean": ("lean", "--version"),
            "cvc5": ("cvc5", "--version"),
            "coq": ("coqc", "--version"),
        }.items()
    }


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

        extension_directory = str(
            os.environ.get(PCTDD_DUCKDB_EXTENSION_DIRECTORY_ENV) or ""
        ).strip()
        config = {
            "autoinstall_known_extensions": "false",
            "autoload_known_extensions": "false",
        }
        if extension_directory:
            candidate = Path(extension_directory).resolve(strict=True)
            if not candidate.is_dir():
                raise RuntimeError("sealed DuckDB extension directory is not a directory")
            config["extension_directory"] = str(candidate)
        connection = duckdb.connect(":memory:", config=config)
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
silently promoted. The successor is a fresh `{HISTORICAL_STORE_GENERATION}`
authority at `{HISTORICAL_RUNTIME_ROOT}`, served by `{QUACK_ENDPOINT}`.

## G7 exact source-binding successor

The stopped g6 authority has accepted historical work that must neither be
reopened nor represented as current-source execution. `PCTDD-SOURCE-G7`
therefore creates `{G7_STORE_GENERATION}` under `{G7_RUNTIME_ROOT}` from an exact,
sealed g6 prefix. It preserves the 14 accepted completions and V1.1 task/goal
definitions, independently rehashes their rows and evidence, appends one
operator source-binding revision, and explicitly retires only the two sealed
stranded attempts. Execution observations, read replicas, DuckLake data,
owner material, logs, worktrees, and merge/runtime state are not copied.
Publication is private-stage, no-overwrite, and marker-last. DuckLake remains
non-authoritative. Future assignments bind the current sealed source through
the scheduler execution/worktree contract; historical task rows are not
generically rematerialized or rewritten. The stopped predecessor snapshot is
captured under the canonical state-owner fence. The managed g7 owner retries
known stopped/dead startup failures at most eight times with bounded 1–10
second backoff; persistent or unknown-liveness failures remain typed and
fail closed.

## G8 exact source and ordered provider-route successor

The stopped g7 authority proved automatic Quack recovery in a live fault
injection, then exposed an independent external-capacity terminal: Grok Build
returned an exact HTTP 402 balance-exhausted envelope while the sealed task
definitions prohibited an implementation fallback. `{PROVIDER_ROUTE_MIGRATION_REVISION}`
therefore creates `{G8_STORE_GENERATION}` under `{G8_RUNTIME_ROOT}` from the exact
stopped g7 prefix. It preserves every accepted completion and completed task
definition, revises only incomplete task provider roles from `grok-only` to
the canonical `grok-implement` primary role, and binds the reviewed ordered
route `grok_cli/grok-4.6 -> codex/gpt-5.6-terra` only for
`primary_quota_exhausted` at medium reasoning effort. Provider output cannot
approve completion, validation, merge, proof, or publication.

Only PCTDD-001 and PCTDD-029 are re-armed. Their exact stopped task receipts,
claims, attempts, context-only phase histories, deferred provider dispatches,
and byte-hashed 402 logs prove that no provider/effect result was admitted.
The migration expires the one still-active claim, preserves the already
released claim, consumes one bounded unknown-outcome rearm, and resets their
ordinary attempt counters. All other blocked/completed/history records remain
unchanged. Publication again uses a private stage, hash verification,
no-overwrite links, and a final marker; g7 remains immutable history.

## G9 descendant-source and sealed-board successor

The stopped g8 authority later accumulated three resolved, generated
reconciliation guardrails (`PCTDD-054` through `PCTDD-056`) in its Markdown
bootstrap projection even though durable task/history state remained the
authority. `{DESCENDANT_SOURCE_MIGRATION_REVISION}` creates
`{STORE_GENERATION}` under `{RUNTIME_ROOT}` from an exactly stopped and fenced
g8 prefix. The active board is restored to exactly `PCTDD-000` through
`PCTDD-053`; the exact removed Markdown blocks and discovery evidence are
archived by hash without deleting their Git or g8 state/event history.

The successor preserves all 54 task CIDs, statuses, revisions, definitions,
completion receipts, and the complete event prefix. It appends only one
operator plan revision and one operator evidence node binding the reviewed
descendant source, current governed gitlinks, archive, and guardrail policy.
Dependency, retry-budget, and reconciliation task-producing guardrails are
disabled for this sealed board; their diagnostics remain state/event-only.
Capture requires no active claim, attempt, lease, listener, or WAL. Publication
copies only immutable control and coordination histories into a private stage,
rehashes them, and links the generation marker last. The tracked pending
package deliberately contains no fabricated stopped-store hashes; an operator
must first commit this package, stop/fence g8, run the explicit capture pass,
commit regenerated controls, and only then migrate g9.

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

Namespace: `{NAMESPACE}`. Revision: `{PLAN_REVISION}` (fresh `{HISTORICAL_STORE_GENERATION}`, preserving g5 as immutable predecessor history). This is a sealed bootstrap projection; DuckDB through Quack owns live status. Markdown is non-authoritative and is not completion authority. PCTDD-000 remains `todo` here and is completed only by an evidence-gated task-store transaction.

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
        protected = ", ".join(sorted(V11_TASKBOARD_PROTECTED_ARTIFACTS)) if operator else "all scheduler protected_paths; no worker edits"
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


V11_TASKBOARD_PROTECTED_ARTIFACTS = (
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

# Successor controls are operator-owned without changing the already accepted
# V1.1 task definitions above.
PROTECTED_ARTIFACTS = (
    *V11_TASKBOARD_PROTECTED_ARTIFACTS,
    G6_SOURCE_MIGRATION_INVENTORY.relative_to(ROOT).as_posix(),
    G7_PROVIDER_ROUTE_MIGRATION_INVENTORY.relative_to(ROOT).as_posix(),
    SOURCE_MIGRATION_MODULE,
    SOURCE_MIGRATION_TEST,
    PROVIDER_ROUTE_MIGRATION_MODULE,
    PROVIDER_ROUTE_MIGRATION_TEST,
    G8_TO_G9_DESCENDANT_SOURCE_INVENTORY.relative_to(ROOT).as_posix(),
    G8_RESOLVED_GUARDRAIL_ARCHIVE.relative_to(ROOT).as_posix(),
    DESCENDANT_SOURCE_MIGRATION_MODULE,
    DESCENDANT_SOURCE_MIGRATION_TEST,
    ORPHAN_RECOVERY_REGRESSION_TEST,
    QUACK_LIFECYCLE_CONTROL_TEST,
    QUACK_ENSURE_SERVICE_TEMPLATE,
    QUACK_USER_SYSTEMD_CONTROL,
    QUACK_USER_SYSTEMD_CONTROL_TEST,
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
    # The reviewed source is the immutable descendant anchor.  The final
    # marker-last g9 receipt, not a self-referential tracked file, binds the
    # eventual clean successor HEAD/tree and exact governed gitlinks.
    base = CONTROL_SOURCE_ANCHOR_HEAD
    tree = CONTROL_SOURCE_ANCHOR_TREE
    source_migration = g6_source_migration_inventory()[
        "source_binding_successor_materialization"
    ]
    provider_route_migration = g7_provider_route_migration_inventory()[
        "source_provider_route_successor_materialization"
    ]
    descendant_migration = descendant_source_policy()
    return {
        "schema": "ipfs_accelerate_py.agent_supervisor.parallel-content-sealing-proof-carrying-tdd.scheduler_config@1",
        "program_identifier": NAMESPACE, "board_namespace": NAMESPACE, "accepted_plan_revision_alias": PLAN_REVISION,
        "taskboard_path": BOARD.relative_to(ROOT).as_posix(), "objectives_path": OBJECTIVES.relative_to(ROOT).as_posix(), "plan_path": PLAN.relative_to(ROOT).as_posix(),
        "validator_path": "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py", "dependency_validator_path": "scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py", "materializer_path": "scripts/materialize_parallel_content_sealing_proof_carrying_tdd_program.py", "validation_profile_path": VALIDATION_PROFILES.relative_to(ROOT).as_posix(), "validation_dispatcher_path": VALIDATION_DISPATCHER,
        "task_prefix": "PCTDD-", "goal_prefix": "PCTDD-G", "root_goal_id": "PCTDD-G000", "merge_target_branch": BRANCH,
        "control_amendment": {"revision": PLAN_REVISION, "amends": PREDECESSOR_PLAN_REVISION, "reason": "preserve accepted g5-g8 task/history authority while binding one exact g9 descendant source and preventing generated tasks from mutating the sealed bootstrap board", "migration_inventory": G5_MIGRATION_INVENTORY.relative_to(ROOT).as_posix(), "historical_g6_plan_and_task_definitions_preserved": True, "source_migration_inventory": G6_SOURCE_MIGRATION_INVENTORY.relative_to(ROOT).as_posix(), "provider_route_migration_inventory": G7_PROVIDER_ROUTE_MIGRATION_INVENTORY.relative_to(ROOT).as_posix(), "descendant_source_migration_inventory": G8_TO_G9_DESCENDANT_SOURCE_INVENTORY.relative_to(ROOT).as_posix(), "resolved_guardrail_archive": G8_RESOLVED_GUARDRAIL_ARCHIVE.relative_to(ROOT).as_posix(), "fresh_materialization_required": False, "copy_predecessor_acceptance": True, "historical_completion_reissuance": False},
        "source_binding": {"accelerator_required_ancestor": base, "accelerator_planning_revision": base, "accelerator_planning_tree": tree, "accelerator_required_branch": BRANCH, "bootstrap_task_source": "duckdb", "ipfs_accelerate_submodule_path": "external/ipfs_accelerate", "ipfs_accelerate_planning_revision": git("rev-parse", "HEAD", cwd=ROOT / "external/ipfs_accelerate"), "ipfs_accelerate_planning_tree": git("rev-parse", "HEAD^{tree}", cwd=ROOT / "external/ipfs_accelerate"), "ipfs_datasets_submodule_path": "external/ipfs_datasets", "ipfs_datasets_planning_revision": git("rev-parse", "HEAD", cwd=ROOT / "external/ipfs_datasets"), "ipfs_datasets_planning_tree": git("rev-parse", "HEAD^{tree}", cwd=ROOT / "external/ipfs_datasets"), "ipfs_kit_submodule_path": "external/ipfs_kit", "ipfs_kit_planning_revision": git("rev-parse", "HEAD", cwd=ROOT / "external/ipfs_kit"), "ipfs_kit_planning_tree": git("rev-parse", "HEAD^{tree}", cwd=ROOT / "external/ipfs_kit"), "require_initialized_gitlinks": True, "require_superproject_gitlink_equals_nested_head": True, "require_clean_nested_worktree_at_task_start": True, "require_origin_main_as_ancestor": False, "record_recursive_repository_forest_at_launch": True, "changed_revision_requires_fresh_inventory_and_baseline": True, "planning_revision_is_runtime_completion_evidence": False},
        "source_binding_successor_materialization": source_migration,
        "source_provider_route_successor_materialization": provider_route_migration,
        "descendant_source_successor_materialization": descendant_migration,
        "initial_projection": {"task_count": 54, "task_dependency_count": sum(map(len, DEPENDENCIES.values())), "completed_task_ids": [], "ready_task_ids": [], "post_operator_completed_task_ids": ["PCTDD-000"], "post_operator_ready_task_ids": [f"PCTDD-{n:03d}" for n in range(1, 5)], "blocked_task_ids": [], "terminal_task_id": "PCTDD-053", "goal_count": 24, "root_goal_id": "PCTDD-G000"},
        "database_program": {"authority_mode": "quack", "task_source_kind": "duckdb", "endpoint_secret_handle": "env://IPFS_ACCELERATE_AGENT_QUACK_TOKEN", "quack_endpoint": QUACK_ENDPOINT, "store_id": f"{RUNTIME_ROOT}/control.duckdb", "store_generation": STORE_GENERATION, "schema_revision": "1", "event_store_path": f"{RUNTIME_ROOT}/events", "runtime_registry_path": f"{RUNTIME_ROOT}/registry", "worktree_root": f"{RUNTIME_ROOT}/worktrees", "export_profile": "pctdd-v1", "failover_policy": "fail_closed", "explicit_legacy": False, "owner_management": {"mode": "managed_local", "owner_state_dir": str((ROOT / RUNTIME_ROOT / "quack-owner").resolve()), "startup_timeout_seconds": 120.0, "health_check_interval_seconds": 5.0, "max_restart_attempts": 8, "initial_backoff_seconds": 1.0, "max_backoff_seconds": 10.0, "termination_grace_seconds": 40.0}, "predecessor_store_generation": G8_STORE_GENERATION, "predecessor_is_read_only_history": True, "historical_store_generations": ["pctdd-v1-g5", HISTORICAL_STORE_GENERATION, G7_STORE_GENERATION, G8_STORE_GENERATION]},
        "operational_control_plane": {"name": "DuckDB + Quack + non-authoritative DuckLake", "duckdb_role": "authoritative transactional goals/tasks/CAS/fences/receipts/events", "quack_role": "authenticated exclusive loopback state owner", "ducklake_role": "rebuildable analytics/history projection", "direct_multi_process_duckdb_file_open_permitted": False, "automatic_file_fallback_permitted": False, "outage_policy": "fail_closed", "markdown_is_bootstrap_only": True, "generated_guardrail_reporting": "state_and_events_only_for_this_sealed_board"},
        "ducklake_projection_program": {"mode": "enabled_non_authoritative", "authority": False, "may_grant_authority": False, "scheduling_prerequisite": False, "acceptance_prerequisite": False, "completion_prerequisite": False, "catalog_path": f"{RUNTIME_ROOT}/ducklake/catalog.duckdb", "data_path": f"{RUNTIME_ROOT}/ducklake/data", "logical_datasets": ["bootstrap_history", "g5_migration_history", "g6_source_migration_history", "g7_provider_route_migration_history", "g8_descendant_source_migration_history"], "outage_policy": "typed unavailable and replayable; never block DuckDB authority"},
        "max_lanes": 4, "strict_task_sharding": True, "idle_lane_work_stealing": "", "exit_when_all_tracks_terminal": False, "objective_refill_enabled": False, "codebase_refill_enabled": False, "objective_goal_refinement_enabled": False, "retry_budget_guardrail_enabled": False, "dependency_guardrail_enabled": False, "reconciliation_guardrail_enabled": False,
        "poll_interval_seconds": 5, "daemon_interval_seconds": 20, "check_interval_seconds": 20, "stale_seconds": 1800, "watchdog_startup_grace_seconds": 600, "max_restarts": 3, "max_task_attempts": 2, "implementation_retry_budget": 1, "validation_retry_budget": 2, "merge_retry_budget": 2, "implementation_timeout_seconds": 7200, "implementation_max_timeout_seconds": 21600, "implementation_log_stall_seconds": 1200,
        "worktree_submodule_paths": ["external/ipfs_accelerate", "external/ipfs_datasets", "external/ipfs_kit"], "protected_paths": list(PROTECTED_ARTIFACTS),
        "runtime_paths": {"root": RUNTIME_ROOT, "state": f"{RUNTIME_ROOT}/state", "worktrees": f"{RUNTIME_ROOT}/worktrees", "merge_queue": f"{RUNTIME_ROOT}/merge-queue", "logs": f"{RUNTIME_ROOT}/logs", "evidence": f"{RUNTIME_ROOT}/evidence", "quack_owner": f"{RUNTIME_ROOT}/quack-owner", "generated_runtime_artifacts_are_completion_authority": False},
        "lanes": [{"index": n, "name": f"pctdd-lane-{n}", "strict_shard_remainder": n, "initial_focus": focus} for n, focus in enumerate(("content-identities", "pytest-fixtures", "proof-batching", "integration-qualification"))],
        "provider": {
            **PROVIDER_ROUTE,
            "completion_authority": "controller_owned_sealed_validation_and_database_cas",
            "max_concurrency": 4,
            "secrets_from_environment_only": True,
            "secrets_in_argv_prompts_logs_or_receipts": False,
        },
        "resource_budgets": {"filesystem_readers": 4, "canonicalization_workers": 4, "sha_cid_workers": 4, "proof_verifiers": 2, "prover_workers": 1, "immutable_store_writers": 2, "merkle_reducers": 4, "test_workers": 4},
        "safety_floors": {"identity_divergence": 0, "false_test_phase_reuse": 0, "stale_authoritative_reuse": 0, "selection_false_negative_regressions": 0, "simulated_proof_admissions": 0, "model_created_proof_authority_completion": 0, "unauthorized_root_publications": 0, "lost_concurrent_updates": 0, "escaped_critical_seeded_defects": 0, "secret_witness_leaks": 0},
        "rollout_gates": ["bootstrap", "shadow_hash", "shadow_reuse", "shadow_proof", "protected", "required"], "benchmark_freeze": "config/parallel_content_sealing_proof_carrying_tdd_benchmark.json", "required_evidence_per_task": "board.required_evidence", "current_tree_revalidation_before_launch": True,
    }


def benchmark_config() -> dict[str, Any]:
    return {"schema": "pctdd/benchmark-preregistration@1", "status": "frozen_before_implementation", "revision": PLAN_REVISION, "safety_floors": render_config()["safety_floors"], "hash_seal_workloads": {"layouts": ["many_small", "mixed_repository", "few_large"], "changes": ["clean", "1_percent", "10_percent", "50_percent", "dirty_overlay"], "cache": ["cold_memo", "warm_memo"], "seal": ["full_checkpoint", "delta_seal"], "workers": [1, 2, 4, 8, 16], "storage": ["local_ssd", "reproducible_slow_io"]}, "pytest_tdd_workloads": ["no_fixture", "pure", "module_session", "parameterized", "temp_filesystem", "transactional_db", "clock_rng", "service_simulation", "opaque_dynamic", "teardown_finalizer", "xdist", "slow_fast_calls", "proof_hit_miss", "changed_fixture", "changed_plugin_conftest", "changed_environment"], "metrics": ["wall_time", "cpu_time", "peak_rss", "files_opened", "bytes_read", "bytes_hashed", "memo_hits_rejections", "root_equality", "phase_times", "selection_recall", "mutation_escapes", "proof_batch_cost", "wal_cas_time", "model_calls_tokens_context", "calls_avoided_by_reuse_procedure_repair"], "targets": {"warm_bytes_reread_reduction_percent": 90, "warm_1_percent_delta_prepare_reduction_percent": 50, "warm_selected_loop_reduction_percent": 30, "repeat_general_llm_call_reduction_percent": 25, "median_model_context_reduction_percent": 30}, "anti_gaming": "No hidden failures, uncounted work, skipped validation, oracle leakage, or denominator exclusions."}


def inventories() -> dict[str, dict[str, Any]]:
    sources = [source_record("ipfs_accelerate_py", "external/ipfs_accelerate"), source_record("ipfs_datasets_py", "external/ipfs_datasets"), source_record("ipfs_kit_py", "external/ipfs_kit")]
    return {
        "repository_baseline.json": {"schema": "pctdd/repository-baseline@3", "captured_utc": "2026-08-30T17:02:36Z", "planning_root": str(ROOT), "control_generation_input_head": CONTROL_SOURCE_ANCHOR_HEAD, "control_generation_input_tree": CONTROL_SOURCE_ANCHOR_TREE, "branch": BRANCH, "sources": sources, "all_governed_sources_clean_and_gitlink_exact": all(not item["dirty"] and item["gitlink_matches_nested_head"] for item in sources), "dirty_user_tree_preserved": True, "original_user_tree_evidence": {"captured_utc": "2026-08-28", "root_status_sha256": "f0a737302e4455c55e60edc28403da4f339e9b64811cc0b0dcf0c87e2d9629b3", "root_diff_sha256": "72f6c22550da009960d570f8b5128077c9160ef2d4ae2d5cc75498ab69e08fb7", "root_untracked_list_sha256": "c20615c1a314943dca33d6d1764014096ebbd9632a5404b55992a97883a2a8ac", "accelerate_status_sha256": "c261a97a9d4d91da96af386077e5cdf9c1532273614a73911d8c07a063913798", "datasets_status_sha256": "a1b4619c21ab5c19d90aa666b48d10d7f5034a2abe2ce57e0f854892429d9c83"}, "evidence_note": "The reviewed fail-closed supervisor-recovery anchor and exact governed gitlinks seed the pending g9 package; only the final clean-source marker-last receipt admits migration without rewriting accepted task or completion history."},
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
        "g6_source_migration_inventory.json": g6_source_migration_inventory(),
        "g7_provider_route_migration_inventory.json": g7_provider_route_migration_inventory(),
        "g8_to_g9_descendant_source_inventory.json": g8_to_g9_descendant_source_inventory(),
        "g8_resolved_guardrail_archive.json": resolved_guardrail_archive(),
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
        "historical_completion_reissued": False,
        "historical_plan_and_task_definitions_preserved": True,
        "source_binding_migration_revision": SOURCE_MIGRATION_REVISION,
        "source_binding_migration_inventory": G6_SOURCE_MIGRATION_INVENTORY.relative_to(ROOT).as_posix(),
        "source_binding_migration_module": SOURCE_MIGRATION_MODULE,
        "source_provider_route_migration_revision": PROVIDER_ROUTE_MIGRATION_REVISION,
        "source_provider_route_migration_inventory": G7_PROVIDER_ROUTE_MIGRATION_INVENTORY.relative_to(ROOT).as_posix(),
        "source_provider_route_migration_module": PROVIDER_ROUTE_MIGRATION_MODULE,
        "descendant_source_migration_revision": DESCENDANT_SOURCE_MIGRATION_REVISION,
        "descendant_source_migration_inventory": G8_TO_G9_DESCENDANT_SOURCE_INVENTORY.relative_to(ROOT).as_posix(),
        "descendant_source_migration_module": DESCENDANT_SOURCE_MIGRATION_MODULE,
        "resolved_guardrail_archive": G8_RESOLVED_GUARDRAIL_ARCHIVE.relative_to(ROOT).as_posix(),
        "completion_prerequisites": [
            "required-acceptance pytest phase receipt",
            "dependency validator valid=true",
            "board validator valid=true",
            "configured-board preflight valid=true",
            "configured-board implementation dry-run success",
            "one exact clean source HEAD/tree for every prerequisite",
        ],
        "successor_materialization_prerequisites": [
            "accepted g6 to g7 source-binding migration remains byte-identical history",
            "exact stopped g7 store, coordination prefix, and owner status",
            "historical completion and definition row hashes unchanged",
            "exact quota-blocked attempts settled without provider-result reuse",
            "exact queue disposition reconciled and any existing backoff cleared for PCTDD-001 and PCTDD-029",
            "reviewed Grok hard-quota to Codex fallback route is content-bound",
            "exact stopped g8 authority with no active claim, attempt, lease, listener, or WAL",
            "canonical 54-task projection with resolved PCTDD-054..056 evidence archived outside the active board",
            "all three Markdown-producing guardrails disabled for this sealed bootstrap board",
            "private staged g9 publication with final marker last",
            "current clean source and governed gitlinks revalidated before publication",
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
        "predecessor_generation": G8_STORE_GENERATION,
        "historical_generations": [
            "pctdd-v1-g5",
            HISTORICAL_STORE_GENERATION,
            G7_STORE_GENERATION,
            G8_STORE_GENERATION,
        ],
        "migration_inventory": G8_TO_G9_DESCENDANT_SOURCE_INVENTORY.relative_to(ROOT).as_posix(),
        "resolved_guardrail_archive": G8_RESOLVED_GUARDRAIL_ARCHIVE.relative_to(ROOT).as_posix(),
        "historical_g7_provider_route_migration_inventory": G7_PROVIDER_ROUTE_MIGRATION_INVENTORY.relative_to(ROOT).as_posix(),
        "historical_g6_source_migration_inventory": G6_SOURCE_MIGRATION_INVENTORY.relative_to(ROOT).as_posix(),
        "historical_g5_migration_inventory": G5_MIGRATION_INVENTORY.relative_to(ROOT).as_posix(),
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
    *(f"docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/{name}" for name in ("repository_baseline.json", "authority_matrix.json", "overlap_gap_matrix.json", "hash_identity_inventory.json", "hashing_critical_path.json", "pytest_identity_inventory.json", "fixture_adapter_inventory.json", "proof_claim_matrix.json", "zkp_backend_inventory.json", "storage_recovery_inventory.json", "benchmark_preregistration.json", "g5_migration_inventory.json", "g6_source_migration_inventory.json", "g7_provider_route_migration_inventory.json", "g8_to_g9_descendant_source_inventory.json", "g8_resolved_guardrail_archive.json")),
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
    SOURCE_MIGRATION_MODULE,
    PROVIDER_ROUTE_MIGRATION_MODULE,
    DESCENDANT_SOURCE_MIGRATION_MODULE,
    "test/api/parallel_content_sealing/test_pctdd_g6_control_amendment.py",
    SOURCE_MIGRATION_TEST,
    PROVIDER_ROUTE_MIGRATION_TEST,
    DESCENDANT_SOURCE_MIGRATION_TEST,
    ORPHAN_RECOVERY_REGRESSION_TEST,
    QUACK_LIFECYCLE_CONTROL_TEST,
    QUACK_ENSURE_SERVICE_TEMPLATE,
    QUACK_USER_SYSTEMD_CONTROL,
    QUACK_USER_SYSTEMD_CONTROL_TEST,
)


def operator_control_receipt() -> dict[str, Any]:
    return {
        "schema": "pctdd/operator-control-receipt@1",
        "task_id": "PCTDD-000",
        "board_namespace": NAMESPACE,
        "plan_revision": PLAN_REVISION,
        "amends_plan_revision": PREDECESSOR_PLAN_REVISION,
        "store_generation": STORE_GENERATION,
        "predecessor_generation": G8_STORE_GENERATION,
        "migration_revision": DESCENDANT_SOURCE_MIGRATION_REVISION,
        "migration_inventory": G8_TO_G9_DESCENDANT_SOURCE_INVENTORY.relative_to(ROOT).as_posix(),
        "resolved_guardrail_archive": G8_RESOLVED_GUARDRAIL_ARCHIVE.relative_to(ROOT).as_posix(),
        "historical_provider_route_migration_revision": PROVIDER_ROUTE_MIGRATION_REVISION,
        "historical_g7_provider_route_migration_inventory": G7_PROVIDER_ROUTE_MIGRATION_INVENTORY.relative_to(ROOT).as_posix(),
        "historical_source_migration_revision": SOURCE_MIGRATION_REVISION,
        "historical_g6_source_migration_inventory": G6_SOURCE_MIGRATION_INVENTORY.relative_to(ROOT).as_posix(),
        "historical_g5_migration_inventory": G5_MIGRATION_INVENTORY.relative_to(ROOT).as_posix(),
        "status": "sealed_pending_runtime_descendant_source_migration",
        "markdown_non_authoritative": True,
        "historical_completion_reissued": False,
        "historical_plan_and_task_definitions_preserved": True,
        "completion_authority": (
            "The existing g7 DatabaseTaskSource completions remain historical; "
            "only operator descendant-source migration evidence and the "
            "marker-last g9 receipt authorize the current control-plane source."
        ),
        "dependency_seal": SEAL.relative_to(ROOT).as_posix(),
        "claim": (
            "This tracked receipt identifies the V1.1/g9 descendant-source "
            "successor package. It neither re-completes PCTDD-000 nor "
            "upgrades any historical completion into current-source execution "
            "evidence."
        ),
    }


def _serialized(value: str | dict[str, Any]) -> bytes:
    text = value if isinstance(value, str) else json.dumps(value, indent=2, sort_keys=True) + "\n"
    return text.encode("utf-8")


def _preseal_outputs() -> dict[Path, str | dict[str, Any]]:
    outputs: dict[Path, str | dict[str, Any]] = {
        PLAN: render_plan(),
        OBJECTIVES: render_objectives(),
        BOARD: render_board(),
        CONFIG: render_config(),
        BENCHMARK: benchmark_config(),
        VALIDATION_PROFILES: validation_profiles(),
        ROOT / "artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/PCTDD-000.json": operator_control_receipt(),
    }
    for name, value in inventories().items():
        outputs[INVENTORY / name] = value
    placeholders = (
        (ROOT / "test/api/parallel_content_sealing/README.md", "Parallel content sealing API qualification"),
        (ROOT / "test/api/proof_carrying_tdd/README.md", "Proof-carrying TDD API qualification"),
        (ROOT / "benchmarks/agent_supervisor/parallel_content_sealing/README.md", "Parallel content sealing benchmarks"),
        (ROOT / "benchmarks/agent_supervisor/proof_carrying_tdd/README.md", "Proof-carrying TDD benchmarks"),
    )
    for path, title in placeholders:
        outputs[path] = (
            f"# {title}\n\nProtected bootstrap placeholder. Implementation and measured "
            "results are owned by the corresponding PCTDD worker tasks; no result "
            "is inferred from this directory.\n"
        )
    return outputs


def _assert_governed_sources_safe() -> None:
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


def _assert_clean_descendant_capture_source() -> None:
    """Require a committed reviewed g9 package before the one-shot live capture."""

    current = git("rev-parse", "HEAD")
    if current == CONTROL_SOURCE_ANCHOR_HEAD:
        raise RuntimeError("g9 stopped-store capture requires a committed descendant package")
    if git("status", "--porcelain=v1", "--untracked-files=all"):
        raise RuntimeError("g9 stopped-store capture requires a clean outer worktree")
    git("merge-base", "--is-ancestor", CONTROL_SOURCE_ANCHOR_HEAD, current)
    changed: set[str] = set()
    for line in git(
        "diff", "--name-status", "--no-renames", CONTROL_SOURCE_ANCHOR_HEAD, current, "--"
    ).splitlines():
        fields = line.split("\t")
        if len(fields) != 2 or fields[0] not in {"A", "M"}:
            raise RuntimeError(f"g9 capture source has a non-control delta: {line}")
        changed.add(fields[1])
    allowed = set(DESCENDANT_SOURCE_MIGRATION_CONTROL_PATHS)
    if not changed or not changed.issubset(allowed):
        raise RuntimeError(
            "g9 capture source changes paths outside its reviewed control allowlist: "
            + ", ".join(sorted(changed - allowed))
        )


def _check_generated() -> tuple[str, ...]:
    mismatches: list[str] = []
    for path, value in _preseal_outputs().items():
        expected = _serialized(value)
        if not path.is_file() or path.read_bytes() != expected:
            mismatches.append(path.relative_to(ROOT).as_posix())
    if mismatches:
        return tuple(sorted(mismatches))
    expected_manifest = _serialized(render_control_manifest())
    if not CONTROL_MANIFEST.is_file() or CONTROL_MANIFEST.read_bytes() != expected_manifest:
        mismatches.append(CONTROL_MANIFEST.relative_to(ROOT).as_posix())
        return tuple(sorted(mismatches))
    expected_seal = _serialized(render_seal())
    if not SEAL.is_file() or SEAL.read_bytes() != expected_seal:
        mismatches.append(SEAL.relative_to(ROOT).as_posix())
    return tuple(sorted(mismatches))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail unless every tracked generated control is byte-identical",
    )
    parser.add_argument(
        "--capture-g9-inputs",
        action="store_true",
        help=(
            "under the canonical offline owner fence, capture exact stopped g8 "
            "anchors and regenerate the final g9 controls"
        ),
    )
    arguments = parser.parse_args()
    if arguments.check and arguments.capture_g9_inputs:
        raise SystemExit("--check and --capture-g9-inputs are mutually exclusive")
    if len(TASKS) != 54 or len(GOALS) != 24 or len(TASK_TEST_STEMS) != 54 or len(TASK_ASSERTIONS) != 54:
        raise SystemExit("sealed cardinality changed")
    _assert_governed_sources_safe()
    if arguments.capture_g9_inputs:
        _assert_clean_descendant_capture_source()
        capture_g9_inputs()
    if arguments.check:
        mismatches = _check_generated()
        print(
            json.dumps(
                {
                    "namespace": NAMESPACE,
                    "mode": "check",
                    "valid": not mismatches,
                    "mismatches": list(mismatches),
                },
                sort_keys=True,
            )
        )
        return 0 if not mismatches else 1
    for path, value in _preseal_outputs().items():
        write(path, value)
    write(CONTROL_MANIFEST, render_control_manifest())
    write(SEAL, render_seal())
    print(json.dumps({"namespace": NAMESPACE, "mode": "capture-g9-inputs" if arguments.capture_g9_inputs else "generate", "capture_status": g8_to_g9_descendant_source_inventory()["capture_status"], "tasks": len(TASKS), "goals": len(GOALS), "dependencies": sum(map(len, DEPENDENCIES.values())), "sealed_artifacts": len(render_seal()["artifacts"])}, sort_keys=True))
    return 0


if __name__ == "__main__": raise SystemExit(main())

#!/usr/bin/env python3
"""Fail-closed preflight for the proof-backed test-reuse program."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEL_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
for key, value in {
    "IPFS_ACCELERATE_DUCKDB_ONLY": "1",
    "IPFS_ACCEL_SKIP_CORE": "1",
    "IPFS_KIT_DISABLE": "1",
    "IPFS_DATASETS_AUTO_INSTALL": "false",
    "IPFS_AUTO_INSTALL": "false",
    "IPFS_DATASETS_PY_MINIMAL_IMPORTS": "1",
    "IPFS_TEST_PROOF_REUSE_MODE": "off",
    "PYTHONDONTWRITEBYTECODE": "1",
}.items():
    os.environ.setdefault(key, value)
if str(ACCEL_ROOT) not in sys.path:
    sys.path.insert(0, str(ACCEL_ROOT))

from ipfs_accelerate_py.agent_supervisor.objectives.objective_graph import (  # noqa: E402
    materialize_task_dependency_dag,
    parse_goal_heap,
)
from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (  # noqa: E402
    parse_task_file,
)


PLAN_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "docs"
    / "46-proof-backed-test-reuse-plan-2026-07-31.md"
)
OBJECTIVE_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "docs"
    / "46-proof-backed-test-reuse.objectives.md"
)
TODO_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "docs"
    / "46-proof-backed-test-reuse.todo.md"
)
CONFIG_PATH = REPO_ROOT / "config" / "proof_backed_test_reuse_supervisor.json"

EXPECTED_GOAL_IDS = frozenset(
    {
        "PTR-G000",
        "PTR-G010",
        "PTR-G020",
        "PTR-G030",
        "PTR-G040",
        "PTR-G050",
        "PTR-G060",
        "PTR-G070",
        "PTR-G080",
        "PTR-G090",
        "PTR-G100",
        "PTR-G110",
        "PTR-G120",
        "PTR-G130",
        "PTR-G140",
    }
)
EXPECTED_TASK_IDS = frozenset(
    {
        "PTR-000",
        "PTR-001",
        "PTR-002",
        "PTR-003",
        "PTR-010",
        "PTR-011",
        "PTR-012",
        "PTR-020",
        "PTR-021",
        "PTR-022",
        "PTR-030",
        "PTR-031",
        "PTR-040",
        "PTR-041",
        "PTR-042",
        "PTR-043",
        "PTR-050",
        "PTR-051",
        "PTR-052",
        "PTR-053",
        "PTR-060",
        "PTR-061",
        "PTR-070",
        "PTR-080",
        "PTR-081",
        "PTR-090",
        "PTR-091",
        "PTR-092",
        "PTR-093",
        "PTR-100",
        "PTR-101",
        "PTR-102",
        "PTR-108",
        "PTR-109",
        "PTR-110",
        "PTR-111",
        "PTR-112",
        "PTR-120",
        "PTR-121",
        "PTR-122",
        "PTR-130",
        "PTR-131",
        "PTR-132",
        "PTR-133",
        "PTR-134",
        "PTR-135",
        "PTR-136",
        "PTR-137",
        "PTR-138",
        "PTR-139",
        "PTR-140",
        "PTR-141",
        "PTR-142",
        "PTR-143",
        "PTR-144",
        "PTR-145",
        "PTR-146",
        "PTR-147",
        "PTR-148",
        "PTR-149",
        "PTR-150",
        "PTR-151",
        "PTR-152",
        "PTR-153",
        "PTR-154",
        "PTR-155",
        "PTR-160",
        "PTR-161",
        "PTR-162",
        "PTR-163",
        "PTR-164",
        "PTR-165",
        "PTR-166",
        "PTR-167",
        "PTR-168",
        "PTR-169",
        "PTR-170",
    }
)
SEALED_INITIAL_READY = frozenset({"PTR-001", "PTR-002", "PTR-003"})
COMPLETION_EXTENSION_TASK_IDS = frozenset(
    {
        "PTR-108",
        "PTR-109",
        "PTR-110",
        "PTR-111",
        "PTR-112",
        "PTR-120",
        "PTR-121",
        "PTR-122",
        "PTR-130",
    }
)
COMPLETION_EXTENSION_WAVE_ONE = frozenset(
    {"PTR-108", "PTR-109", "PTR-110"}
)
RUNTIME_REPAIR_TASK_IDS = frozenset(
    {
        "PTR-131",
        "PTR-132",
        "PTR-133",
        "PTR-134",
        "PTR-135",
        "PTR-136",
        "PTR-137",
        "PTR-138",
        "PTR-139",
        "PTR-140",
        "PTR-141",
        "PTR-142",
    }
)
RUNTIME_REPAIR_WAVE_ONE = frozenset({"PTR-131", "PTR-132", "PTR-133"})
RUNTIME_BOOTSTRAP_WAVE = frozenset({"PTR-139", "PTR-140", "PTR-141"})
PRODUCTION_ACTIVATION_TASK_IDS = frozenset(
    {
        "PTR-143",
        "PTR-144",
        "PTR-145",
        "PTR-146",
        "PTR-147",
        "PTR-148",
        "PTR-149",
    }
)
PRODUCTION_ACTIVATION_WAVE_ONE = frozenset({"PTR-143", "PTR-144"})
PRODUCTION_ACTIVATION_PARALLEL_WAVE = frozenset(
    {"PTR-144", "PTR-145", "PTR-146"}
)
PRODUCTION_CORRECTION_TASK_IDS = frozenset(
    {"PTR-150", "PTR-151", "PTR-152", "PTR-153", "PTR-154", "PTR-155"}
)
PRODUCTION_CORRECTION_WAVE_ONE = frozenset({"PTR-150", "PTR-151"})
PROOF_MATERIAL_CONTEXT_WAVE = frozenset({"PTR-153", "PTR-154"})
REVIEWED_PRODUCTION_ACTIVATION_TASK_IDS = frozenset(
    PRODUCTION_ACTIVATION_TASK_IDS | PRODUCTION_CORRECTION_TASK_IDS
)
AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS = frozenset(
    {
        "PTR-160",
        "PTR-161",
        "PTR-162",
        "PTR-163",
        "PTR-164",
        "PTR-165",
        "PTR-166",
        "PTR-167",
        "PTR-168",
        "PTR-169",
        "PTR-170",
    }
)
AUTHENTICATED_RECEIPT_WAVE_A = frozenset({"PTR-160", "PTR-161", "PTR-162"})
# PTR-160 is retained as completed evidence while the two repository bootstrap
# owners are explicitly reopened behind PTR-170. Keep this distinct from Wave
# A: the latter is historical repository-width evidence, while this set is the
# claimable v8 control-plane frontier.
AUTHENTICATED_RECEIPT_REOPENED_READY = frozenset({"PTR-170"})
AUTHENTICATED_RECEIPT_BOOTSTRAP_FRONTIER = frozenset({"PTR-161", "PTR-162"})
AUTHENTICATED_RECEIPT_WAVE_B = frozenset({"PTR-163", "PTR-165"})
AUTHENTICATED_RECEIPT_RUNTIME_JOIN_TASK_ID = "PTR-164"
AUTHENTICITY_JOIN_TASK_ID = "PTR-166"
OUTPUT_REPLAY_JOIN_TASK_ID = "PTR-167"
ZERO_CONFIG_E2E_JOIN_TASK_ID = "PTR-168"
AUTHENTICATED_HANDOFF_TASK_ID = "PTR-169"
G140_ACTIONABLE_RETRY_EVIDENCE_ID = "ptr/actionable-retry-evidence@1"
GOAL_STATES = frozenset(
    {
        "active",
        "provisionally_complete",
        "verified_complete",
        "analysis_inconclusive",
        "blocked",
        "reopened",
    }
)
TASK_STATES = frozenset({"todo", "in_progress", "blocked", "completed"})
REQUIRED_GOAL_FIELDS = (
    "status",
    "parent",
    "depends_on",
    "fib_priority",
    "track",
    "priority",
    "bundle",
    "goal",
    "evidence",
    "outputs",
    "validation",
    "acceptance",
    "gap_task",
    "refinement",
    "embedding_query",
    "ast_query",
)
REQUIRED_TASK_FIELDS = (
    "status",
    "completion",
    "is schedulable",
    "review only",
    "priority",
    "track",
    "depends on",
    "goal id",
    "outputs",
    "validation",
    "board namespace",
    "bundle",
    "parallel lane",
    "resource class",
    "implementation timeout seconds",
    "predicted files",
    "predicted symbols",
    "interfaces",
    "submodules",
    "generated artifacts",
    "conflict policy",
    "symbolic first",
    "llm context budget bytes",
    "provider role",
    "context budget tokens",
    "preconditions",
    "effects",
    "evidence subset",
    "acceptance",
)
REQUIRED_DIRECT_TASK_DEPENDENCIES = {
    "PTR-090": frozenset({"PTR-061", "PTR-070", "PTR-081"}),
    "PTR-100": frozenset({"PTR-091", "PTR-092", "PTR-093"}),
    "PTR-102": frozenset({"PTR-091", "PTR-092", "PTR-093", "PTR-101"}),
    "PTR-108": frozenset({"PTR-040", "PTR-041", "PTR-042"}),
    "PTR-109": frozenset({"PTR-080"}),
    "PTR-110": frozenset({"PTR-102"}),
    "PTR-111": frozenset({"PTR-102", "PTR-108"}),
    "PTR-112": frozenset({"PTR-102", "PTR-109"}),
    "PTR-120": frozenset({"PTR-110", "PTR-111", "PTR-112"}),
    "PTR-121": frozenset({"PTR-110", "PTR-111", "PTR-112"}),
    "PTR-122": frozenset({"PTR-102", "PTR-110", "PTR-111", "PTR-112"}),
    "PTR-130": frozenset({"PTR-120", "PTR-121", "PTR-122"}),
    "PTR-131": frozenset({"PTR-130"}),
    "PTR-132": frozenset({"PTR-130"}),
    "PTR-133": frozenset({"PTR-130"}),
    "PTR-134": frozenset({"PTR-131"}),
    "PTR-135": frozenset({"PTR-131"}),
    "PTR-136": frozenset({"PTR-134", "PTR-135"}),
    "PTR-137": frozenset({"PTR-132"}),
    "PTR-138": frozenset({"PTR-136", "PTR-137"}),
    "PTR-139": frozenset({"PTR-138"}),
    "PTR-140": frozenset({"PTR-137", "PTR-138"}),
    "PTR-141": frozenset({"PTR-133", "PTR-138"}),
    "PTR-142": frozenset({"PTR-139", "PTR-140", "PTR-141"}),
    "PTR-143": frozenset({"PTR-142"}),
    "PTR-144": frozenset({"PTR-142"}),
    "PTR-145": frozenset({"PTR-143"}),
    "PTR-146": frozenset({"PTR-143"}),
    "PTR-147": frozenset({"PTR-144", "PTR-145", "PTR-146"}),
    "PTR-148": frozenset({"PTR-147"}),
    "PTR-149": frozenset({"PTR-155"}),
    "PTR-150": frozenset({"PTR-148"}),
    "PTR-151": frozenset({"PTR-148"}),
    "PTR-152": frozenset({"PTR-150", "PTR-151"}),
    "PTR-153": frozenset({"PTR-152"}),
    "PTR-154": frozenset({"PTR-152"}),
    "PTR-155": frozenset({"PTR-153", "PTR-154"}),
    "PTR-160": frozenset({"PTR-149"}),
    "PTR-161": frozenset({"PTR-149", "PTR-170"}),
    "PTR-162": frozenset({"PTR-149", "PTR-170"}),
    "PTR-163": frozenset({"PTR-160", "PTR-161"}),
    "PTR-164": frozenset({"PTR-160", "PTR-163"}),
    "PTR-165": frozenset({"PTR-161", "PTR-162"}),
    "PTR-166": frozenset({"PTR-163", "PTR-164"}),
    "PTR-167": frozenset({"PTR-165", "PTR-166"}),
    "PTR-168": frozenset({"PTR-161", "PTR-162", "PTR-166", "PTR-167"}),
    "PTR-169": frozenset({"PTR-168"}),
    "PTR-170": frozenset({"PTR-149"}),
}
REQUIRED_DATASETS_TASKS = frozenset(
    {
        "PTR-040",
        "PTR-041",
        "PTR-042",
        "PTR-070",
        "PTR-108",
        "PTR-132",
        "PTR-137",
        "PTR-140",
        "PTR-144",
        "PTR-151",
        "PTR-161",
        "PTR-163",
    }
)
REQUIRED_ACCELERATOR_TASKS = frozenset(
    {
        "PTR-131",
        "PTR-134",
        "PTR-135",
        "PTR-136",
        "PTR-138",
        "PTR-139",
        "PTR-142",
        "PTR-143",
        "PTR-145",
        "PTR-146",
        "PTR-147",
        "PTR-148",
        "PTR-149",
        "PTR-150",
        "PTR-152",
        "PTR-153",
        "PTR-154",
        "PTR-155",
        "PTR-160",
        "PTR-164",
        "PTR-166",
        "PTR-168",
        "PTR-169",
        "PTR-170",
    }
)
REQUIRED_KIT_TASKS = frozenset(
    {"PTR-080", "PTR-081", "PTR-109", "PTR-133", "PTR-141", "PTR-162"}
)
REQUIRED_RUNTIME_TASK_PATHS = {
    "PTR-131": frozenset(
        {
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/activation_contracts.py",
        }
    ),
    "PTR-132": frozenset(
        {
            "external/ipfs_datasets/setup.py",
            "external/ipfs_datasets/tests/unit/test_setup_side_effect_defaults.py",
        }
    ),
    "PTR-133": frozenset(
        {"external/ipfs_kit/ipfs_kit_py/proof_certificate_store.py"}
    ),
    "PTR-134": frozenset(
        {
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/default_identity_services.py",
        }
    ),
    "PTR-135": frozenset(
        {
            "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/"
            "proof/test_candidate_context_store.py",
        }
    ),
    "PTR-136": frozenset(
        {
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/runtime_revalidation.py",
        }
    ),
    "PTR-137": frozenset(
        {
            "external/ipfs_datasets/ipfs_datasets_py/logic/zkp/"
            "test_certificate_issuer.py",
        }
    ),
    "PTR-138": frozenset(
        {
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/plugin.py",
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/services.py",
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/xdist.py",
        }
    ),
    "PTR-139": frozenset(
        {
            "external/ipfs_accelerate/conftest.py",
            "external/ipfs_accelerate/requirements.txt",
            "external/ipfs_accelerate/setup.py",
            "external/ipfs_accelerate/pyproject.toml",
            "external/ipfs_accelerate/ipfs_accelerate_py/__init__.py",
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/lazy_dependencies.py",
        }
    ),
    "PTR-140": frozenset(
        {
            "external/ipfs_datasets/tests/conftest.py",
            "external/ipfs_datasets/requirements.txt",
            "external/ipfs_datasets/setup.py",
            "external/ipfs_datasets/pyproject.toml",
            "external/ipfs_datasets/ipfs_datasets_py/__init__.py",
            "external/ipfs_datasets/ipfs_datasets_py/pytest_proof_reuse.py",
        }
    ),
    "PTR-141": frozenset(
        {
            "external/ipfs_kit/conftest.py",
            "external/ipfs_kit/requirements.txt",
            "external/ipfs_kit/setup.py",
            "external/ipfs_kit/pyproject.toml",
            "external/ipfs_kit/ipfs_kit_py/__init__.py",
            "external/ipfs_kit/ipfs_kit_py/pytest_proof_reuse.py",
        }
    ),
    "PTR-142": frozenset(
        {
            "external/ipfs_accelerate/test/api/"
            "test_proof_reuse_runtime_activation_e2e.py",
            "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/"
            "validation/proof_test_reuse_current_tree_gate.py",
        }
    ),
    "PTR-143": frozenset(
        {
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/collection_seed.py",
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/default_identity_services.py",
        }
    ),
    "PTR-144": frozenset(
        {
            "external/ipfs_datasets/ipfs_datasets_py/logic/zkp/"
            "test_pass_groth16_provider.py",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/src/circuit.rs",
        }
    ),
    "PTR-145": frozenset(
        {
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/current_context_provider.py",
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/runtime_revalidation.py",
        }
    ),
    "PTR-146": frozenset(
        {
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/runtime_trace_lifecycle.py",
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/candidate_publication.py",
        }
    ),
    "PTR-147": frozenset(
        {
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/services.py",
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/publication.py",
        }
    ),
    "PTR-148": frozenset(
        {
            "external/ipfs_accelerate/test/api/"
            "test_proof_reuse_runtime_activation_e2e.py",
            "external/ipfs_accelerate/test/api/"
            "test_proof_reuse_subprocess_benchmark.py",
        }
    ),
    "PTR-149": frozenset(
        {
            "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/"
            "validation/proof_test_reuse_current_tree_gate.py",
            "external/ipfs_accelerate/test/api/"
            "test_proof_reuse_runtime_activation_report.py",
        }
    ),
    "PTR-150": frozenset(
        {
            "external/ipfs_accelerate/setup.py",
            "external/ipfs_accelerate/pyproject.toml",
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/provisioning_cli.py",
            "external/ipfs_accelerate/test/api/"
            "test_proof_reuse_setup_provisioning.py",
            "external/ipfs_accelerate/docs/guides/"
            "TEST_PROOF_REUSE_DEPENDENCY_PROVISIONING.md",
        }
    ),
    "PTR-151": frozenset(
        {
            "external/ipfs_datasets/MANIFEST.in",
            "external/ipfs_datasets/pyproject.toml",
            "external/ipfs_datasets/setup.py",
            "external/ipfs_datasets/ipfs_datasets_py.egg-info/SOURCES.txt",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/Cargo.toml",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/build.rs",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/build.sh",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/RUST_SETUP.md",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/src/main.rs",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/bin/linux-aarch64/groth16",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/bin/linux-aarch64/release-manifest.json",
            "external/ipfs_datasets/tests/unit_tests/logic/zkp/"
            "test_groth16_native_release.py",
        }
    ),
    "PTR-152": frozenset(
        {
            "external/ipfs_accelerate/docs/guides/"
            "TEST_PROOF_REUSE_DEPENDENCY_PROVISIONING.md",
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/publication.py",
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/lazy_dependencies.py",
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/reporting.py",
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/services.py",
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/xdist.py",
            "external/ipfs_accelerate/test/api/"
            "test_proof_reuse_controller_issuance.py",
            "external/ipfs_accelerate/test/api/"
            "test_proof_reuse_lazy_provisioning.py",
            "external/ipfs_accelerate/test/api/"
            "test_proof_reuse_runtime_activation_report.py",
            "external/ipfs_accelerate/test/api/"
            "test_proof_reuse_default_runtime_services.py",
            "external/ipfs_accelerate/test/api/"
            "test_pytest_proof_reuse_xdist.py",
            "external/ipfs_accelerate/test/api/"
            "test_proof_reuse_accelerator_zero_config.py",
        }
    ),
    "PTR-153": frozenset(
        {
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/services.py",
            "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/"
            "integrations/ipfs_datasets_test_certificate_provider.py",
            "external/ipfs_accelerate/test/api/"
            "test_proof_reuse_issued_material_retention.py",
            "external/ipfs_accelerate/test/api/"
            "test_agent_supervisor_ipfs_datasets_test_certificate_provider.py",
        }
    ),
    "PTR-154": frozenset(
        {
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/candidate_publication.py",
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/receipt.py",
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/xdist.py",
            "external/ipfs_accelerate/test/api/"
            "test_proof_reuse_candidate_publication_context.py",
            "external/ipfs_accelerate/test/api/"
            "test_pytest_proof_reuse_xdist.py",
        }
    ),
    "PTR-155": frozenset(
        {
            "external/ipfs_accelerate/ipfs_accelerate_py/testing/"
            "proof_reuse/publication.py",
            "external/ipfs_accelerate/test/api/"
            "test_proof_reuse_controller_issuance.py",
            "external/ipfs_accelerate/test/api/"
            "test_proof_reuse_v4_publication_integration.py",
        }
    ),
    "PTR-161": frozenset(
        {
            "external/ipfs_datasets/conftest.py",
            "external/ipfs_datasets/tests/conftest.py",
            "external/ipfs_datasets/ipfs_datasets_py/__init__.py",
            "external/ipfs_datasets/ipfs_datasets_py/pytest_proof_reuse.py",
            "external/ipfs_datasets/pyproject.toml",
            "external/ipfs_datasets/setup.py",
            "external/ipfs_datasets/requirements.txt",
            "external/ipfs_datasets/tests/unit/test_proof_reuse_bootstrap.py",
            "external/ipfs_datasets/tests/unit/test_pytest_proof_reuse_shim.py",
            "external/ipfs_datasets/tests/unit/test_proof_reuse_zero_config.py",
            "external/ipfs_datasets/tests/unit/"
            "test_proof_reuse_optional_plugin_startup.py",
            "external/ipfs_datasets/tests/unit/"
            "test_proof_reuse_isolated_bootstrap_subprocess.py",
            "external/ipfs_datasets/tests/unit/"
            "test_setup_side_effect_defaults.py",
        }
    ),
    "PTR-162": frozenset(
        {
            "external/ipfs_kit/conftest.py",
            "external/ipfs_kit/ipfs_kit_py/__init__.py",
            "external/ipfs_kit/ipfs_kit_py/pytest_proof_reuse.py",
            "external/ipfs_kit/ipfs_kit_py/proof_certificate_store.py",
            "external/ipfs_kit/ipfs_kit_py/test_reuse_capabilities.py",
            "external/ipfs_kit/ipfs_kit_py/content_addressed_artifact_store.py",
            "external/ipfs_kit/pyproject.toml",
            "external/ipfs_kit/setup.py",
            "external/ipfs_kit/requirements.txt",
            "external/ipfs_kit/tests/test_proof_reuse_bootstrap.py",
            "external/ipfs_kit/tests/test_pytest_proof_reuse_shim.py",
            "external/ipfs_kit/tests/test_proof_reuse_zero_config.py",
            "external/ipfs_kit/tests/test_proof_reuse_optional_plugin_startup.py",
            "external/ipfs_kit/tests/"
            "test_proof_reuse_isolated_bootstrap_subprocess.py",
            "external/ipfs_kit/tests/test_proof_certificate_store.py",
            "external/ipfs_kit/tests/test_reuse_capabilities.py",
            "external/ipfs_kit/tests/test_content_addressed_artifact_store.py",
            "external/ipfs_kit/tests/test_candidate_context_artifact_store.py",
        }
    ),
    "PTR-163": frozenset(
        {
            "external/ipfs_datasets/MANIFEST.in",
            "external/ipfs_datasets/pyproject.toml",
            "external/ipfs_datasets/setup.py",
            "external/ipfs_datasets/ipfs_datasets_py.egg-info/SOURCES.txt",
            "external/ipfs_datasets/ipfs_datasets_py/logic/zkp/statements/"
            "test_pass.py",
            "external/ipfs_datasets/ipfs_datasets_py/logic/zkp/provekit/"
            "test_pass_circuit.py",
            "external/ipfs_datasets/ipfs_datasets_py/logic/zkp/"
            "test_execution_certificate.py",
            "external/ipfs_datasets/ipfs_datasets_py/logic/zkp/"
            "test_certificate_assurance.py",
            "external/ipfs_datasets/ipfs_datasets_py/logic/zkp/"
            "test_certificate_issuer.py",
            "external/ipfs_datasets/ipfs_datasets_py/logic/zkp/"
            "test_pass_groth16_provider.py",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/Cargo.toml",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/Cargo.lock",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/build.rs",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/build.sh",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/RUST_SETUP.md",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/WIRE_FORMAT.md",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/src/circuit.rs",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/src/domain.rs",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/src/lib.rs",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/src/main.rs",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/src/prover.rs",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/src/setup.rs",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/src/verifier.rs",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/schemas/witness_v1.schema.json",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/schemas/proof_v1.schema.json",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/bin/linux-aarch64/groth16",
            "external/ipfs_datasets/ipfs_datasets_py/processors/"
            "groth16_backend/bin/linux-aarch64/release-manifest.json",
            "external/ipfs_datasets/tests/unit/logic/zkp/"
            "test_test_pass_statement.py",
            "external/ipfs_datasets/tests/unit/logic/zkp/"
            "test_test_execution_certificate.py",
            "external/ipfs_datasets/tests/unit/logic/zkp/"
            "test_test_pass_cid_profile.py",
            "external/ipfs_datasets/tests/unit/logic/zkp/"
            "test_test_certificate_assurance.py",
            "external/ipfs_datasets/tests/unit/logic/zkp/"
            "test_test_certificate_issuer.py",
            "external/ipfs_datasets/tests/unit/logic/zkp/"
            "test_deferred_test_certificate_request.py",
            "external/ipfs_datasets/tests/unit/logic/zkp/"
            "test_test_pass_groth16_provider.py",
            "external/ipfs_datasets/tests/unit_tests/logic/zkp/"
            "groth16_wire_vectors.json",
            "external/ipfs_datasets/tests/unit_tests/logic/zkp/"
            "test_groth16_wire_schemas.py",
            "external/ipfs_datasets/tests/unit_tests/logic/zkp/"
            "test_groth16_wire_vectors.py",
            "external/ipfs_datasets/tests/unit_tests/logic/zkp/"
            "test_groth16_native_release.py",
        }
    ),
    "PTR-170": frozenset(
        {
            "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/"
            "todo_daemon/implementation_daemon.py",
            "external/ipfs_accelerate/test/api/"
            "test_agent_supervisor_implementation_failure_review.py",
            "external/ipfs_accelerate/test/api/"
            "test_agent_supervisor_context_delta.py",
            "external/ipfs_accelerate/test/api/"
            "test_agent_supervisor_todo_daemon_port.py",
        }
    ),
}
EXACT_RUNTIME_TASK_PATH_IDS = frozenset(
    {"PTR-161", "PTR-162", "PTR-163", "PTR-170"}
)
EXPECTED_HISTORICAL_MISSING_ARTIFACT_OWNERS = {
    "external/ipfs_datasets/ipfs_datasets_py/logic/zkp/"
    "test_certificate_assurance.py": "PTR-163",
    "external/ipfs_datasets/ipfs_datasets_py/logic/zkp/"
    "test_certificate_issuer.py": "PTR-163",
    "external/ipfs_datasets/ipfs_datasets_py/logic/zkp/"
    "test_pass_groth16_provider.py": "PTR-163",
    "external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/"
    "bin/linux-aarch64/release-manifest.json": "PTR-163",
    "external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/"
    "build.rs": "PTR-163",
    "external/ipfs_datasets/ipfs_datasets_py/pytest_proof_reuse.py": "PTR-161",
    "external/ipfs_datasets/tests/unit/logic/zkp/"
    "test_deferred_test_certificate_request.py": "PTR-163",
    "external/ipfs_datasets/tests/unit/logic/zkp/"
    "test_test_certificate_assurance.py": "PTR-163",
    "external/ipfs_datasets/tests/unit/logic/zkp/"
    "test_test_certificate_issuer.py": "PTR-163",
    "external/ipfs_datasets/tests/unit/logic/zkp/"
    "test_test_pass_cid_profile.py": "PTR-163",
    "external/ipfs_datasets/tests/unit/logic/zkp/"
    "test_test_pass_groth16_provider.py": "PTR-163",
    "external/ipfs_datasets/tests/unit/test_proof_reuse_bootstrap.py": "PTR-161",
    "external/ipfs_datasets/tests/unit/test_proof_reuse_zero_config.py": "PTR-161",
    "external/ipfs_datasets/tests/unit/test_pytest_proof_reuse_shim.py": "PTR-161",
    "external/ipfs_datasets/tests/unit/"
    "test_setup_side_effect_defaults.py": "PTR-161",
    "external/ipfs_datasets/tests/unit_tests/logic/zkp/"
    "test_groth16_native_release.py": "PTR-163",
    "external/ipfs_kit/conftest.py": "PTR-162",
    "external/ipfs_kit/ipfs_kit_py/"
    "content_addressed_artifact_store.py": "PTR-162",
    "external/ipfs_kit/ipfs_kit_py/proof_certificate_store.py": "PTR-162",
    "external/ipfs_kit/ipfs_kit_py/pytest_proof_reuse.py": "PTR-162",
    "external/ipfs_kit/ipfs_kit_py/test_reuse_capabilities.py": "PTR-162",
    "external/ipfs_kit/tests/"
    "test_candidate_context_artifact_store.py": "PTR-162",
    "external/ipfs_kit/tests/test_content_addressed_artifact_store.py": "PTR-162",
    "external/ipfs_kit/tests/test_proof_certificate_store.py": "PTR-162",
    "external/ipfs_kit/tests/test_proof_reuse_bootstrap.py": "PTR-162",
    "external/ipfs_kit/tests/test_proof_reuse_zero_config.py": "PTR-162",
    "external/ipfs_kit/tests/test_pytest_proof_reuse_shim.py": "PTR-162",
    "external/ipfs_kit/tests/test_reuse_capabilities.py": "PTR-162",
}
EXPECTED_PROTECTED_PATHS = frozenset(
    {
        "implementation_plan/docs/46-proof-backed-test-reuse-plan-2026-07-31.md",
        "implementation_plan/docs/46-proof-backed-test-reuse.objectives.md",
        "implementation_plan/docs/46-proof-backed-test-reuse.todo.md",
        "config/proof_backed_test_reuse_supervisor.json",
        "scripts/validate_proof_backed_test_reuse_board.py",
        "scripts/proof_backed_test_reuse_supervisor.py",
    }
)
EXPECTED_SUBMODULES = (
    "external/ipfs_accelerate",
    "external/ipfs_datasets",
    "external/ipfs_kit",
)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _csv(value: object) -> tuple[str, ...]:
    text = str(value or "")
    return tuple(item.strip() for item in text.split(",") if item.strip())


def _semicolon_terms(value: object) -> tuple[str, ...]:
    text = str(value or "")
    return tuple(item.strip() for item in text.split(";") if item.strip())


def _safe_relative_paths(values: Iterable[str], *, field: str) -> list[str]:
    errors: list[str] = []
    for raw in values:
        value = str(raw).strip().replace("\\", "/")
        path = PurePosixPath(value)
        if (
            not value
            or "\x00" in value
            or ";" in value
            or path.is_absolute()
            or ".." in path.parts
            or path.as_posix() in {".", ".."}
            or (path.parts and path.parts[0].endswith(":"))
        ):
            errors.append(f"{field} contains unsafe path {raw!r}")
    return errors


def _cycle_nodes(edges: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    visiting: set[str] = set()
    visited: set[str] = set()
    cycle: set[str] = set()

    def visit(node: str, lineage: tuple[str, ...]) -> None:
        if node in visited:
            return
        if node in visiting:
            if node in lineage:
                cycle.update(lineage[lineage.index(node) :])
            cycle.add(node)
            return
        visiting.add(node)
        for dependency in edges.get(node, ()):
            visit(dependency, (*lineage, node))
        visiting.remove(node)
        visited.add(node)

    for item in sorted(edges):
        visit(item, ())
    return tuple(sorted(cycle))


def _ancestors(node: str, edges: dict[str, tuple[str, ...]]) -> frozenset[str]:
    result: set[str] = set()
    stack = list(edges.get(node, ()))
    while stack:
        dependency = stack.pop()
        if dependency in result:
            continue
        result.add(dependency)
        stack.extend(edges.get(dependency, ()))
    return frozenset(result)


def _bool_text(value: object) -> bool | None:
    normalized = str(value or "").strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    return None


VALIDATION_PATH_TARGET_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"((?:external|implementation_plan|config|scripts|tests|test)/"
    r"[A-Za-z0-9_@%+=:,./-]+)"
)


def _validation_path_targets(command: object) -> frozenset[str]:
    """Extract exact workspace-relative artifact targets without running a shell."""

    targets: set[str] = set()
    for match in VALIDATION_PATH_TARGET_PATTERN.finditer(str(command or "")):
        target = match.group(1).split("::", 1)[0].rstrip(",;)]}")
        if not _safe_relative_paths((target,), field="validation target"):
            targets.add(PurePosixPath(target).as_posix())
    return frozenset(targets)


def validate(
    objective_path: Path,
    todo_path: Path,
    config_path: Path,
    plan_path: Path,
) -> dict[str, object]:
    errors: list[str] = []
    for label, path in (
        ("plan", plan_path),
        ("objective", objective_path),
        ("task board", todo_path),
        ("configuration", config_path),
    ):
        if not path.is_file():
            errors.append(f"{label} file is missing: {path}")
    if errors:
        return {
            "schema": "ipfs_accelerate_py/proof-backed-test-reuse-preflight@1",
            "valid": False,
            "errors": errors,
        }

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {
            "schema": "ipfs_accelerate_py/proof-backed-test-reuse-preflight@1",
            "valid": False,
            "errors": [f"configuration is not valid JSON: {exc}"],
        }

    expected_config = {
        "profileId": "proof-backed-test-reuse-v1",
        "integrationBranch": "agent/proof-backed-test-reuse",
        "taskPrefix": "## PTR-",
        "boardNamespace": "proof-backed-test-reuse-v1",
        "defaultStateRootSuffix": (
            "ipfs_accelerate_py/proof-backed-test-reuse-v8"
        ),
    }
    for field, expected in expected_config.items():
        if config.get(field) != expected:
            errors.append(
                f"configuration {field} must be {expected!r}, got "
                f"{config.get(field)!r}"
            )
    parallel = config.get("parallelRuntime")
    if not isinstance(parallel, dict):
        errors.append("configuration parallelRuntime must be an object")
        parallel = {}
    if parallel.get("laneCount") != 3:
        errors.append("parallelRuntime.laneCount must be 3")
    if parallel.get("strictTaskSharding") is not True:
        errors.append("parallelRuntime.strictTaskSharding must be true")
    runtime_providers = tuple(parallel.get("providers") or ())
    if runtime_providers != ("grok-codex",) * 3:
        errors.append(
            "parallelRuntime.providers must configure three Grok-primary, "
            "Codex-fallback lanes"
        )
    canonical_provider_roles = tuple(
        parallel.get("canonicalTaskProviderRolesByShard") or ()
    )
    if canonical_provider_roles != (
        "codex-implement",
        "grok-implement",
        "codex-implement",
    ):
        errors.append(
            "canonicalTaskProviderRolesByShard must retain the sealed task "
            "identity roles"
        )
    if parallel.get("canonicalTaskProviderRolesByShardPurpose") != (
        "historical_task_identity_only"
    ):
        errors.append(
            "canonical task provider roles must be documented as historical "
            "task identity metadata"
        )
    runtime_execution_roles = tuple(
        parallel.get("runtimeExecutionProviderRolesByShard") or ()
    )
    if runtime_execution_roles != ("grok-implement",) * 3:
        errors.append(
            "runtimeExecutionProviderRolesByShard must configure Grok-first "
            "execution on all three lanes"
        )
    semantic_merge_resolver = parallel.get("semanticMergeResolver")
    if semantic_merge_resolver != {
        "provider": "grok-codex",
        "routingAuthority": "ipfs_accelerate_py.llm_router",
        "fallbackTrigger": "grok_quota_auth_or_unavailable",
        "inheritedCommandPolicy": "override_with_managed_provider_chain",
    }:
        errors.append(
            "semanticMergeResolver must use the llm_router-owned Grok-primary, "
            "side-effect-safe Codex fallback chain"
        )
    provider_policy = config.get("providerPolicy")
    expected_provider_policy = {
        "primary": {"provider": "grok", "model": "grok-4.5"},
        "fallback": {
            "provider": "codex",
            "model": "gpt-5.6-terra",
            "modelReasoningEffort": "high",
        },
        "routingAuthority": "ipfs_accelerate_py.llm_router",
        "fallbackTrigger": "grok_quota_auth_or_unavailable",
        "primaryUnavailableAction": "use_codex_fallback",
        "nonQuotaFailureAction": "fallback_on_auth_or_launch_else_propagate",
        "appliesTo": ["implementation", "semantic_merge_resolver"],
        "fallbackAllowedOn": [
            "grok_quota_exhausted",
            "authentication_failure",
            "launch_failure",
        ],
        "fallbackRequires": [
            "side_effects_started=false",
            "workspace_unchanged=true",
        ],
        "fallbackForbiddenOn": [
            "timeout",
            "transport_failure",
            "generic_nonzero_exit",
            "malformed_output",
            "task_failure",
            "side_effects_started",
        ],
    }
    if provider_policy != expected_provider_policy:
        errors.append(
            "providerPolicy must retain llm_router-owned Grok 4.5 primary "
            "and Terra high fallback only for quota, authentication, or launch "
            "unavailability before side effects for both "
            "implementation and semantic merge resolution"
        )
    if parallel.get("objectiveRefillEnabled") is not False:
        errors.append("objective refill must be disabled for the sealed board")
    if parallel.get("codebaseRefillEnabled") is not False:
        errors.append("codebase refill must be disabled for the sealed board")
    preflight_config = config.get("preflight")
    if not isinstance(preflight_config, dict):
        errors.append("configuration preflight must be an object")
        preflight_config = {}
    if preflight_config.get("requireInitialConflictFreeWidth") != 1:
        errors.append(
            "preflight.requireInitialConflictFreeWidth must match the reviewed "
            "one-task actionable-retry-evidence frontier"
        )
    if tuple(parallel.get("worktreeSubmodulePaths") or ()) != EXPECTED_SUBMODULES:
        errors.append(
            "worktreeSubmodulePaths must contain exactly the three outer "
            "IPFS Python repositories"
        )
    protected_paths = frozenset(parallel.get("protectedPaths") or ())
    if protected_paths != EXPECTED_PROTECTED_PATHS:
        errors.append(
            "protectedPaths mismatch: expected "
            f"{sorted(EXPECTED_PROTECTED_PATHS)}, got {sorted(protected_paths)}"
        )
    optional_capabilities = config.get("optionalCapabilities")
    if not isinstance(optional_capabilities, dict) or optional_capabilities.get(
        "launchGate"
    ) is not False:
        errors.append("optional proof infrastructure must not be a launch gate")
    lazy_dependencies = config.get("lazyDependencyPolicy")
    expected_lazy_dependencies = {
        "activation": "first_requested_proof_reuse_capability",
        "manifestParityRequired": [
            "requirements.txt",
            "setup.py",
            "pyproject.toml",
        ],
        "scopedImportsRequired": True,
        "boundedAllowlistedInstaller": True,
        "automaticWhenPackageAutoInstallPolicyAllows": True,
        "offAndImplementationValidationMayInstall": False,
        "installerFailureAction": "typed_unavailable_and_run_test",
        "datasetsNativeGroth16BuildRequiresExplicitOptIn": True,
        "datasetsNltkDownloadRequiresExplicitOptIn": True,
    }
    if lazy_dependencies != expected_lazy_dependencies:
        errors.append(
            "configuration lazyDependencyPolicy must retain scoped, bounded, "
            "fail-open first-use installation and datasets setup safety"
        )
    expected_runner_attestation_profile = {
        "schema": "RunnerPassAttestationV1",
        "signatureAlgorithm": "ed25519",
        "signatureDomain": "ipfs-test-pass-attestation/v1\0",
        "signatureInput": "domain-bytes||sha2-256(unsigned-envelope-bytes)",
        "unsignedEnvelope": {
            "canonicalization": "strict-dag-cbor",
            "cidVersion": 1,
            "multicodec": "dag-cbor",
            "multihash": "sha2-256",
        },
        "publicKeyMaterial": {
            "byteEncoding": (
                "varint(ed25519-pub)||32-byte-ed25519-public-key"
            ),
            "cidVersion": 1,
            "multicodec": "raw",
            "multihash": "sha2-256",
            "multibase": "base32-lower",
        },
        "trustPolicy": {
            "authority": "locally-pinned-trust-policy-cid",
            "cidVersion": 1,
            "multicodec": "dag-cbor",
            "multihash": "sha2-256",
            "multibase": "base32-lower",
            "trustOnFirstUse": False,
        },
        "usage": "pytest-pass-only",
        "checks": {
            "keyEpochRequired": True,
            "validityWindowRequired": True,
            "rotationRequired": True,
            "revocationRequired": True,
        },
    }
    if config.get("runnerAttestationProfile") != (
        expected_runner_attestation_profile
    ):
        errors.append(
            "runnerAttestationProfile must seal the exact authenticated v1 "
            "Ed25519/DAG-CBOR/CID/key/trust/usage/epoch policy"
        )
    objective_projection = config.get("objectiveProjection")
    if not isinstance(objective_projection, dict):
        errors.append("configuration objectiveProjection must be an object")
        objective_projection = {}
    if objective_projection.get("mode") != "reviewed_bounded_closeout":
        errors.append(
            "objectiveProjection.mode must be reviewed_bounded_closeout"
        )
    if objective_projection.get("reviewRevision") != (
        "authenticated-receipt-current-tree-repair-v8"
    ):
        errors.append(
            "objectiveProjection.reviewRevision must identify the reviewed "
            "authenticated-receipt current-tree repair"
        )
    if frozenset(objective_projection.get("implementationTaskIds") or ()) != (
        AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS
    ):
        errors.append(
            "objectiveProjection implementation task inventory mismatch"
        )
    if frozenset(
        objective_projection.get("initialClaimableTaskIds") or ()
    ) != AUTHENTICATED_RECEIPT_REOPENED_READY:
        errors.append(
            "objectiveProjection initial claimable task inventory mismatch"
        )
    if objective_projection.get("authorityWriter") != "outer_controller_only":
        errors.append(
            "objective completion authority writer must be the outer controller"
        )
    if objective_projection.get("workerLaneReconciliationEnabled") is not False:
        errors.append("worker-lane objective reconciliation must remain disabled")
    if objective_projection.get("autonomousGapGenerationEnabled") is not False:
        errors.append("autonomous objective-gap generation must remain disabled")
    if objective_projection.get("artifactLocation") != "state_root":
        errors.append("objective completion artifacts must live under state root")
    if objective_projection.get("reconciliationPhases") != 3:
        errors.append("objective closeout must declare exactly three phases")
    if objective_projection.get("closeoutControllerTaskId") != "PTR-121":
        errors.append("objective closeout controller task must be PTR-121")
    if objective_projection.get("operatorHandoffTaskId") != AUTHENTICATED_HANDOFF_TASK_ID:
        errors.append("objective operator handoff task must be PTR-169")
    if tuple(objective_projection.get("authenticatedReceiptWaveATaskIds") or ()) != (
        "PTR-160",
        "PTR-161",
        "PTR-162",
    ):
        errors.append("objective authenticated-receipt wave A inventory mismatch")
    if tuple(objective_projection.get("authenticatedReceiptWaveBTaskIds") or ()) != (
        "PTR-163",
        "PTR-165",
    ):
        errors.append(
            "objective authenticated-receipt wave B inventory mismatch"
        )
    if objective_projection.get("authenticatedReceiptRuntimeJoinTaskId") != (
        AUTHENTICATED_RECEIPT_RUNTIME_JOIN_TASK_ID
    ):
        errors.append("objective authenticated-receipt runtime join must be PTR-164")
    if objective_projection.get("authenticatedCurrentTreeHandoffTaskId") != (
        AUTHENTICATED_HANDOFF_TASK_ID
    ):
        errors.append("objective authenticated current-tree handoff must be PTR-169")
    stale_projection_fields = sorted(
        field
        for field in (
            "proofMaterialAndContextWaveTaskIds",
            "exactV4PublicationJoinTaskId",
        )
        if field in objective_projection
    )
    if stale_projection_fields:
        errors.append(
            "objectiveProjection retains stale pre-v8 fields: "
            f"{stale_projection_fields}"
        )
    if objective_projection.get("sealedTaskCount") != 77:
        errors.append("objective sealed task count must be 77")
    if objective_projection.get("authenticityJoinTaskId") != AUTHENTICITY_JOIN_TASK_ID:
        errors.append("objective authenticity join task must be PTR-166")
    if objective_projection.get("outputReplayJoinTaskId") != OUTPUT_REPLAY_JOIN_TASK_ID:
        errors.append("objective output replay join task must be PTR-167")
    if objective_projection.get("zeroConfigE2EJoinTaskId") != ZERO_CONFIG_E2E_JOIN_TASK_ID:
        errors.append("objective zero-config e2e join task must be PTR-168")
    proof_policy = config.get("proofPolicy") or {}
    if (
        proof_policy.get("statement") != "TestPassStatementV5"
        or proof_policy.get("signedRunnerAttestationRequired") is not True
        or proof_policy.get("runnerPublicKeyMulticodecCidRequired") is not True
        or proof_policy.get("runnerKeyEpochRotationAndRevocationRequired") is not True
        or proof_policy.get("legacyHashOnlyStatementCanSkip") is not False
    ):
        errors.append("proofPolicy must require authenticated TestPassStatementV5 authority")
    projection_path_fields = (
        "gatePathSuffix",
        "evidencePathSuffix",
        "lifecycleProjectionPathSuffix",
        "candidateObjectivePathSuffix",
        "supervisorHealthInputPathSuffix",
        "statusPathSuffix",
    )
    projection_paths = tuple(
        str(objective_projection.get(field) or "")
        for field in projection_path_fields
    )
    errors.extend(
        _safe_relative_paths(
            projection_paths,
            field="objectiveProjection state-root paths",
        )
    )
    if len(set(projection_paths)) != len(projection_paths):
        errors.append("objectiveProjection state-root paths must be unique")
    common_environment = parallel.get("commonEnvironment") or {}
    if common_environment.get("IPFS_TEST_PROOF_REUSE_MODE") != "off":
        errors.append("implementation validation must force proof reuse off")

    objective_text = objective_path.read_text(encoding="utf-8")
    raw_goal_headers = re.findall(
        r"^## (PTR-G\d{3})\s+\S.*$", objective_text, flags=re.MULTILINE
    )
    goals = parse_goal_heap(objective_text)
    goal_ids = [goal.goal_id for goal in goals]
    goal_id_set = set(goal_ids)
    if len(raw_goal_headers) != len(goals):
        errors.append(
            "objective header/parser count mismatch: "
            f"headers={len(raw_goal_headers)} parsed={len(goals)}"
        )
    if len(goal_ids) != len(goal_id_set):
        duplicate_ids = sorted(
            item for item in goal_id_set if goal_ids.count(item) > 1
        )
        errors.append(f"duplicate goal ids: {duplicate_ids}")
    if goal_id_set != EXPECTED_GOAL_IDS:
        errors.append(
            "goal inventory mismatch: missing="
            f"{sorted(EXPECTED_GOAL_IDS - goal_id_set)} extra="
            f"{sorted(goal_id_set - EXPECTED_GOAL_IDS)}"
        )

    goal_parent_edges: dict[str, tuple[str, ...]] = {}
    goal_dependency_edges: dict[str, tuple[str, ...]] = {}
    for goal in goals:
        if not re.fullmatch(r"PTR-G\d{3}", goal.goal_id):
            errors.append(f"invalid goal id: {goal.goal_id}")
        missing = [name for name in REQUIRED_GOAL_FIELDS if name not in goal.fields]
        if missing:
            errors.append(f"{goal.goal_id} missing fields: {missing}")
        status = str(goal.fields.get("status") or "").strip()
        if status not in GOAL_STATES:
            errors.append(f"{goal.goal_id} has noncanonical status {status!r}")
        parent = str(goal.fields.get("parent") or "").strip()
        parents = (parent,) if parent else ()
        goal_parent_edges[goal.goal_id] = parents
        if parent and parent not in goal_id_set:
            errors.append(f"{goal.goal_id} has unknown parent {parent!r}")
        dependencies = _csv(goal.fields.get("depends_on"))
        goal_dependency_edges[goal.goal_id] = dependencies
        for dependency in dependencies:
            if dependency not in goal_id_set:
                errors.append(
                    f"{goal.goal_id} has unknown goal dependency {dependency!r}"
                )
        try:
            fib_priority = int(str(goal.fields.get("fib_priority") or ""))
            if fib_priority < 1:
                raise ValueError
        except ValueError:
            errors.append(f"{goal.goal_id} has invalid fib priority")
        outputs = _csv(goal.fields.get("outputs"))
        if not outputs:
            errors.append(f"{goal.goal_id} has no outputs")
        errors.extend(
            f"{goal.goal_id}: {item}"
            for item in _safe_relative_paths(outputs, field="outputs")
        )
        for name in (
            "goal",
            "evidence",
            "validation",
            "acceptance",
            "gap_task",
            "refinement",
            "embedding_query",
            "ast_query",
        ):
            if not str(goal.fields.get(name) or "").strip():
                errors.append(f"{goal.goal_id} has empty {name}")
        required_evidence = _csv(goal.fields.get("evidence"))
        acceptance_criteria = _semicolon_terms(
            goal.fields.get("acceptance_criteria")
        )
        if acceptance_criteria != required_evidence:
            errors.append(
                f"{goal.goal_id} machine acceptance criteria must exactly "
                "match Evidence in order: expected "
                f"{list(required_evidence)}, got {list(acceptance_criteria)}"
            )
        if (
            goal.goal_id == "PTR-G140"
            and G140_ACTIONABLE_RETRY_EVIDENCE_ID not in required_evidence
        ):
            errors.append(
                "PTR-G140 must require ptr/actionable-retry-evidence@1"
            )
    parent_cycles = _cycle_nodes(goal_parent_edges)
    if parent_cycles:
        errors.append(f"goal parent cycle: {list(parent_cycles)}")
    dependency_cycles = _cycle_nodes(goal_dependency_edges)
    if dependency_cycles:
        errors.append(f"goal dependency cycle: {list(dependency_cycles)}")
    roots = sorted(
        goal_id for goal_id, parents in goal_parent_edges.items() if not parents
    )
    if roots != ["PTR-G000"]:
        errors.append(f"expected only PTR-G000 as root, got {roots}")

    todo_text = todo_path.read_text(encoding="utf-8")
    raw_task_headers = re.findall(
        r"^## (PTR-\d{3})\s+\S.*$", todo_text, flags=re.MULTILINE
    )
    ambiguous_headers = re.findall(
        r"^## (PTR-(?!G\d{3}\b|\d{3}\b)\S+).*$",
        todo_text,
        flags=re.MULTILINE,
    )
    if ambiguous_headers:
        errors.append(f"ambiguous PTR headings: {ambiguous_headers}")
    tasks = parse_task_file(todo_path, "## PTR-")
    task_ids = [task.task_id for task in tasks]
    task_id_set = set(task_ids)
    if len(raw_task_headers) != len(tasks):
        errors.append(
            "task header/parser count mismatch: "
            f"headers={len(raw_task_headers)} parsed={len(tasks)}"
        )
    if len(task_ids) != len(task_id_set):
        duplicate_ids = sorted(
            item for item in task_id_set if task_ids.count(item) > 1
        )
        errors.append(f"duplicate task ids: {duplicate_ids}")
    if task_id_set != EXPECTED_TASK_IDS:
        errors.append(
            "task inventory mismatch: missing="
            f"{sorted(EXPECTED_TASK_IDS - task_id_set)} extra="
            f"{sorted(task_id_set - EXPECTED_TASK_IDS)}"
        )

    task_by_id = {task.task_id: task for task in tasks}
    task_edges: dict[str, tuple[str, ...]] = {}
    predicted_by_task: dict[str, frozenset[str]] = {}
    submodules_by_task: dict[str, frozenset[str]] = {}
    task_records: list[dict[str, object]] = []
    canonical_task_cids: list[str] = []
    for task in tasks:
        if not re.fullmatch(r"PTR-\d{3}", task.task_id):
            errors.append(f"invalid task id: {task.task_id}")
        missing = [
            name for name in REQUIRED_TASK_FIELDS if name not in task.metadata
        ]
        if missing:
            errors.append(f"{task.task_id} missing fields: {missing}")
        if task.status not in TASK_STATES:
            errors.append(
                f"{task.task_id} has noncanonical normalized status "
                f"{task.status!r}"
            )
        if task.priority not in {"P0", "P1", "P2", "P3"}:
            errors.append(f"{task.task_id} has invalid priority {task.priority!r}")
        goal_id = str(task.metadata.get("goal id") or "").strip()
        if goal_id not in goal_id_set:
            errors.append(f"{task.task_id} has unknown goal id {goal_id!r}")
        dependencies = tuple(task.depends_on)
        task_edges[task.task_id] = tuple(
            dependency for dependency in dependencies if dependency in task_id_set
        )
        for dependency in dependencies:
            if dependency == task.task_id:
                errors.append(f"{task.task_id} depends on itself")
            elif dependency not in task_id_set:
                errors.append(
                    f"{task.task_id} has unknown dependency {dependency!r}"
                )
        if not task.outputs:
            errors.append(f"{task.task_id} has no outputs")
        errors.extend(
            f"{task.task_id}: {item}"
            for item in _safe_relative_paths(task.outputs, field="outputs")
        )
        predicted_files = _csv(task.metadata.get("predicted files"))
        predicted_by_task[task.task_id] = frozenset(predicted_files)
        if not predicted_files:
            errors.append(f"{task.task_id} has no predicted files")
        errors.extend(
            f"{task.task_id}: {item}"
            for item in _safe_relative_paths(
                predicted_files, field="predicted files"
            )
        )
        if set(task.outputs) != set(predicted_files):
            errors.append(
                f"{task.task_id} outputs and predicted files must match exactly"
            )
        required_runtime_paths = REQUIRED_RUNTIME_TASK_PATHS.get(
            task.task_id, frozenset()
        )
        missing_runtime_paths = sorted(
            required_runtime_paths.difference(predicted_files)
        )
        if missing_runtime_paths:
            errors.append(
                f"{task.task_id} missing reviewed runtime repair paths: "
                f"{missing_runtime_paths}"
            )
        if task.task_id in EXACT_RUNTIME_TASK_PATH_IDS and frozenset(
            predicted_files
        ) != required_runtime_paths:
            unexpected_runtime_paths = sorted(
                set(predicted_files).difference(required_runtime_paths)
            )
            errors.append(
                f"{task.task_id} reviewed runtime paths must be exact: "
                f"missing={missing_runtime_paths}, "
                f"unexpected={unexpected_runtime_paths}"
            )
        validation_text = str(task.metadata.get("validation") or "").strip()
        if not task.validation or not validation_text:
            errors.append(f"{task.task_id} has no validation command")
        elif not validation_text.startswith("IPFS_TEST_PROOF_REUSE_MODE=off "):
            errors.append(
                f"{task.task_id} validation does not force proof reuse off"
            )
        if not task.acceptance:
            errors.append(f"{task.task_id} has empty acceptance")
        if task.board_namespace != "proof-backed-test-reuse-v1":
            errors.append(
                f"{task.task_id} has unexpected board namespace "
                f"{task.board_namespace!r}"
            )
        # This field describes whether the task is executable work, not its
        # current lifecycle state. Completion updates must not rewrite the
        # task contract or canonical execution role.
        expected_schedulable = task.task_id != "PTR-000"
        schedulable = _bool_text(task.metadata.get("is schedulable"))
        if schedulable is None or schedulable != expected_schedulable:
            errors.append(
                f"{task.task_id} is schedulable must be "
                f"{str(expected_schedulable).lower()}"
            )
        if _bool_text(task.metadata.get("review only")) is not False:
            errors.append(f"{task.task_id} review only must be false")
        if _bool_text(task.metadata.get("symbolic first")) is not True:
            errors.append(f"{task.task_id} symbolic first must be true")
        if str(task.metadata.get("allow concurrent with") or "").strip():
            errors.append(
                f"{task.task_id} must not override dependency/file conflicts"
            )
        try:
            timeout = int(
                str(task.metadata.get("implementation timeout seconds") or "")
            )
            if timeout < 300 or timeout > 10800:
                raise ValueError
        except ValueError:
            errors.append(f"{task.task_id} has invalid implementation timeout")
        try:
            context_budget = int(
                str(task.metadata.get("llm context budget bytes") or "")
            )
            if context_budget < 4096 or context_budget > 65536:
                raise ValueError
        except ValueError:
            errors.append(f"{task.task_id} has invalid LLM context budget")
        provider_role = str(task.metadata.get("provider role") or "").strip()
        try:
            context_budget_tokens = int(
                str(task.metadata.get("context budget tokens") or "")
            )
            if task.task_id == "PTR-000":
                if context_budget_tokens != 0:
                    raise ValueError
            elif context_budget_tokens < 1024 or context_budget_tokens > 16384:
                raise ValueError
        except ValueError:
            errors.append(f"{task.task_id} has invalid context budget tokens")
        if task.task_id == "PTR-000":
            if provider_role != "operator-only":
                errors.append("PTR-000 provider role must be operator-only")
        elif lane_count := int(parallel.get("laneCount") or 0):
            shard_index = int(task.task_id.rsplit("-", 1)[1]) % lane_count
            role_source = (
                runtime_execution_roles
                if task.task_id in AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS
                else canonical_provider_roles
            )
            expected_role = str(role_source[shard_index]) if shard_index < len(role_source) else ""
            if provider_role != expected_role:
                errors.append(
                    f"{task.task_id} provider role {provider_role!r} does not "
                    f"match sealed shard {shard_index} role {expected_role!r}"
                )
        submodules = frozenset(_csv(task.metadata.get("submodules")))
        submodules_by_task[task.task_id] = submodules
        if not submodules.issubset(EXPECTED_SUBMODULES):
            errors.append(
                f"{task.task_id} has unexpected submodules {sorted(submodules)}"
            )
        if task.task_id in (
            RUNTIME_REPAIR_TASK_IDS
            | PRODUCTION_ACTIVATION_TASK_IDS
            | PRODUCTION_CORRECTION_TASK_IDS
        ) and len(submodules) != 1:
            errors.append(
                f"{task.task_id} reviewed repair task must own exactly one "
                f"repository resource, got {sorted(submodules)}"
            )
        if task.task_id in REQUIRED_ACCELERATOR_TASKS and (
            "external/ipfs_accelerate" not in submodules
        ):
            errors.append(f"{task.task_id} must declare external/ipfs_accelerate")
        if task.task_id in REQUIRED_DATASETS_TASKS and (
            "external/ipfs_datasets" not in submodules
        ):
            errors.append(f"{task.task_id} must declare external/ipfs_datasets")
        if task.task_id in REQUIRED_KIT_TASKS and (
            "external/ipfs_kit" not in submodules
        ):
            errors.append(f"{task.task_id} must declare external/ipfs_kit")
        canonical_task_cids.append(str(task.canonical_task_cid or ""))
        task_records.append(
            {
                "task_id": task.task_id,
                "title": task.title,
                "status": task.status,
                "goal_id": goal_id,
                "depends_on": list(task.depends_on),
                "outputs": list(task.outputs),
                "acceptance": task.acceptance,
                "board_namespace": task.board_namespace,
                "canonical_task_cid": task.canonical_task_cid,
            }
        )

    if not all(canonical_task_cids):
        errors.append("one or more canonical task CIDs are empty")
    if len(canonical_task_cids) != len(set(canonical_task_cids)):
        errors.append("canonical task CIDs are not unique")
    task_cycles = _cycle_nodes(task_edges)
    if task_cycles:
        errors.append(f"task dependency cycle: {list(task_cycles)}")
    for task_id, required_dependencies in REQUIRED_DIRECT_TASK_DEPENDENCIES.items():
        missing_dependencies = sorted(
            required_dependencies.difference(task_edges.get(task_id, ()))
        )
        if missing_dependencies:
            errors.append(
                f"{task_id} missing required direct dependencies: "
                f"{missing_dependencies}"
            )
        if task_id in (
            RUNTIME_REPAIR_TASK_IDS
            | PRODUCTION_ACTIVATION_TASK_IDS
            | PRODUCTION_CORRECTION_TASK_IDS
            | AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS
        ) and frozenset(
            task_edges.get(task_id, ())
        ) != required_dependencies:
            errors.append(
                f"{task_id} reviewed-repair dependencies must be exact: "
                f"expected {sorted(required_dependencies)}, got "
                f"{sorted(task_edges.get(task_id, ()))}"
            )

    completed_ids = {
        task.task_id for task in tasks if task.status == "completed"
    }
    claimable_task_ids = {
        task.task_id
        for task in tasks
        if task.status == "todo"
        and set(task.depends_on).issubset(completed_ids)
    }
    configured_initial_ready = frozenset(
        str(task_id)
        for task_id in (
            parallel.get("initialClaimableTaskIds") or ()
        )
    )
    if configured_initial_ready != AUTHENTICATED_RECEIPT_REOPENED_READY:
        errors.append(
            "configured initial claimable tasks mismatch: expected "
            f"{sorted(AUTHENTICATED_RECEIPT_REOPENED_READY)}, got "
            f"{sorted(configured_initial_ready)}"
        )
    if completed_ids == {"PTR-000"}:
        if claimable_task_ids != SEALED_INITIAL_READY:
            errors.append(
                "historical sealed initial claimable tasks mismatch: expected "
                f"{sorted(SEALED_INITIAL_READY)}, got "
                f"{sorted(claimable_task_ids)}"
            )
    else:
        if "PTR-000" not in completed_ids:
            errors.append("progressed board must retain PTR-000 completion")
        for task_id in sorted(completed_ids):
            missing_completed_dependencies = sorted(
                set(task_edges.get(task_id, ())).difference(completed_ids)
            )
            if missing_completed_dependencies:
                errors.append(
                    f"{task_id} completed before dependencies "
                    f"{missing_completed_dependencies}"
                )
    base_task_ids = (
        EXPECTED_TASK_IDS
        - COMPLETION_EXTENSION_TASK_IDS
        - RUNTIME_REPAIR_TASK_IDS
        - PRODUCTION_ACTIVATION_TASK_IDS
        - PRODUCTION_CORRECTION_TASK_IDS
        - AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS
    )
    completion_extension_unstarted = all(
        task_by_id[task_id].status == "todo"
        for task_id in COMPLETION_EXTENSION_TASK_IDS
    )
    if base_task_ids.issubset(completed_ids) and completion_extension_unstarted:
        if claimable_task_ids != COMPLETION_EXTENSION_WAVE_ONE:
            errors.append(
                "historical objective-completion expansion claimable tasks "
                f"must be {sorted(COMPLETION_EXTENSION_WAVE_ONE)}, got "
                f"{sorted(claimable_task_ids)}"
            )
    pre_repair_task_ids = (
        EXPECTED_TASK_IDS
        - RUNTIME_REPAIR_TASK_IDS
        - PRODUCTION_ACTIVATION_TASK_IDS
        - PRODUCTION_CORRECTION_TASK_IDS
        - AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS
    )
    runtime_repair_unstarted = all(
        task_by_id[task_id].status == "todo"
        for task_id in RUNTIME_REPAIR_TASK_IDS
    )
    if pre_repair_task_ids.issubset(completed_ids) and runtime_repair_unstarted:
        if claimable_task_ids != RUNTIME_REPAIR_WAVE_ONE:
            errors.append(
                "reviewed runtime-activation repair claimable tasks must be "
                f"{sorted(RUNTIME_REPAIR_WAVE_ONE)}, got "
                f"{sorted(claimable_task_ids)}"
            )
    pre_production_activation_task_ids = (
        EXPECTED_TASK_IDS
        - PRODUCTION_ACTIVATION_TASK_IDS
        - PRODUCTION_CORRECTION_TASK_IDS
        - AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS
    )
    production_activation_unstarted = all(
        task_by_id[task_id].status == "todo"
        for task_id in PRODUCTION_ACTIVATION_TASK_IDS
    )
    if (
        pre_production_activation_task_ids.issubset(completed_ids)
        and production_activation_unstarted
        and claimable_task_ids != PRODUCTION_ACTIVATION_WAVE_ONE
    ):
        errors.append(
            "reviewed production-runtime activation claimable tasks must be "
            f"{sorted(PRODUCTION_ACTIVATION_WAVE_ONE)}, got "
            f"{sorted(claimable_task_ids)}"
        )
    pre_production_correction_task_ids = (
        EXPECTED_TASK_IDS
        - PRODUCTION_CORRECTION_TASK_IDS
        - AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS
        - {"PTR-149"}
    )
    production_correction_unstarted = all(
        task_by_id[task_id].status == "todo"
        for task_id in PRODUCTION_CORRECTION_TASK_IDS | {"PTR-149"}
    )
    if (
        pre_production_correction_task_ids.issubset(completed_ids)
        and production_correction_unstarted
        and claimable_task_ids != PRODUCTION_CORRECTION_WAVE_ONE
    ):
        errors.append(
            "reviewed current-v4 correction claimable tasks must be "
            f"{sorted(PRODUCTION_CORRECTION_WAVE_ONE)}, got "
            f"{sorted(claimable_task_ids)}"
        )
    pre_authenticated_correction_task_ids = (
        EXPECTED_TASK_IDS - AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS
    )
    authenticated_correction_unstarted = all(
        task_by_id[task_id].status == "todo"
        for task_id in AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS
    )
    if (
        pre_authenticated_correction_task_ids.issubset(completed_ids)
        and authenticated_correction_unstarted
        and claimable_task_ids != frozenset({"PTR-160", "PTR-170"})
    ):
        errors.append(
            "fresh v8 authenticated-receipt seed tasks must be "
            f"{['PTR-160', 'PTR-170']}, got "
            f"{sorted(claimable_task_ids)}"
        )
    authenticated_reopened_frontier = (
        task_by_id["PTR-160"].status == "completed"
        and all(
            task_by_id[task_id].status == "todo"
            for task_id in (
                AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS - {"PTR-160"}
            )
        )
    )
    if (
        pre_authenticated_correction_task_ids.issubset(completed_ids)
        and authenticated_reopened_frontier
        and claimable_task_ids != AUTHENTICATED_RECEIPT_REOPENED_READY
    ):
        errors.append(
            "reopened authenticated-receipt correction claimable tasks must be "
            f"{sorted(AUTHENTICATED_RECEIPT_REOPENED_READY)}, got "
            f"{sorted(claimable_task_ids)}"
        )
    lane_count = int(parallel.get("laneCount") or 0)
    sealed_initial_shards = {
        int(task_id.rsplit("-", 1)[1]) % lane_count
        for task_id in SEALED_INITIAL_READY
    } if lane_count > 0 else set()
    if sealed_initial_shards != {0, 1, 2}:
        errors.append(
            f"sealed initial tasks do not cover all three numeric shards: "
            f"{sorted(sealed_initial_shards)}"
        )
    completion_extension_wave_shards = {
        int(task_id.rsplit("-", 1)[1]) % lane_count
        for task_id in COMPLETION_EXTENSION_WAVE_ONE
    } if lane_count > 0 else set()
    if completion_extension_wave_shards != {0, 1, 2}:
        errors.append(
            "historical objective-completion expansion wave does not cover "
            "all three numeric shards: "
            f"{sorted(completion_extension_wave_shards)}"
        )
    expected_completion_extension_wave_resources = {
        "PTR-108": frozenset({"external/ipfs_datasets"}),
        "PTR-109": frozenset({"external/ipfs_kit"}),
        "PTR-110": frozenset({"external/ipfs_accelerate"}),
    }
    completion_extension_wave_resources = {
        task_id: submodules_by_task.get(task_id, frozenset())
        for task_id in sorted(COMPLETION_EXTENSION_WAVE_ONE)
    }
    if completion_extension_wave_resources != (
        expected_completion_extension_wave_resources
    ):
        errors.append(
            "historical objective-completion expansion wave must own one distinct "
            "configured repository resource per task: expected "
            f"{expected_completion_extension_wave_resources}, got "
            f"{completion_extension_wave_resources}"
        )
    completion_extension_resource_width = len(
        set().union(*completion_extension_wave_resources.values())
    )
    if completion_extension_resource_width != 3:
        errors.append(
            "historical objective-completion expansion wave must retain "
            "repository resource width 3, got "
            f"{completion_extension_resource_width}"
        )

    runtime_repair_wave_shards = {
        int(task_id.rsplit("-", 1)[1]) % lane_count
        for task_id in RUNTIME_REPAIR_WAVE_ONE
    } if lane_count > 0 else set()
    runtime_bootstrap_wave_shards = {
        int(task_id.rsplit("-", 1)[1]) % lane_count
        for task_id in RUNTIME_BOOTSTRAP_WAVE
    } if lane_count > 0 else set()
    for label, shards in (
        ("runtime repair first wave", runtime_repair_wave_shards),
        ("runtime repository-bootstrap wave", runtime_bootstrap_wave_shards),
    ):
        if shards != {0, 1, 2}:
            errors.append(
                f"{label} does not cover all three numeric shards: "
                f"{sorted(shards)}"
            )
    expected_runtime_repair_wave_resources = {
        "PTR-131": frozenset({"external/ipfs_accelerate"}),
        "PTR-132": frozenset({"external/ipfs_datasets"}),
        "PTR-133": frozenset({"external/ipfs_kit"}),
    }
    expected_runtime_bootstrap_wave_resources = {
        "PTR-139": frozenset({"external/ipfs_accelerate"}),
        "PTR-140": frozenset({"external/ipfs_datasets"}),
        "PTR-141": frozenset({"external/ipfs_kit"}),
    }
    runtime_repair_wave_resources = {
        task_id: submodules_by_task.get(task_id, frozenset())
        for task_id in sorted(RUNTIME_REPAIR_WAVE_ONE)
    }
    runtime_bootstrap_wave_resources = {
        task_id: submodules_by_task.get(task_id, frozenset())
        for task_id in sorted(RUNTIME_BOOTSTRAP_WAVE)
    }
    for label, actual, expected in (
        (
            "runtime repair first wave",
            runtime_repair_wave_resources,
            expected_runtime_repair_wave_resources,
        ),
        (
            "runtime repository-bootstrap wave",
            runtime_bootstrap_wave_resources,
            expected_runtime_bootstrap_wave_resources,
        ),
    ):
        if actual != expected:
            errors.append(
                f"{label} must own one distinct configured repository "
                f"resource per task: expected {expected}, got {actual}"
            )
        resource_width = len(set().union(*actual.values()))
        if resource_width != 3:
            errors.append(
                f"{label} must retain repository resource width 3, got "
                f"{resource_width}"
            )
    simulated_bootstrap_completed = (
        pre_repair_task_ids
        | (RUNTIME_REPAIR_TASK_IDS - RUNTIME_BOOTSTRAP_WAVE - {"PTR-142"})
    )
    simulated_bootstrap_claimable = {
        task_id
        for task_id in RUNTIME_REPAIR_TASK_IDS
        if task_id not in simulated_bootstrap_completed
        and set(task_edges.get(task_id, ())).issubset(
            simulated_bootstrap_completed
        )
    }
    if simulated_bootstrap_claimable != RUNTIME_BOOTSTRAP_WAVE:
        errors.append(
            "runtime repository-bootstrap dependency wave must be exactly "
            f"{sorted(RUNTIME_BOOTSTRAP_WAVE)}, got "
            f"{sorted(simulated_bootstrap_claimable)}"
        )

    production_wave_one_shards = {
        int(task_id.rsplit("-", 1)[1]) % lane_count
        for task_id in PRODUCTION_ACTIVATION_WAVE_ONE
    } if lane_count > 0 else set()
    if production_wave_one_shards != {0, 2}:
        errors.append(
            "production-activation first wave must cover numeric shards 0 and 2, "
            f"got {sorted(production_wave_one_shards)}"
        )
    expected_production_wave_one_resources = {
        "PTR-143": frozenset({"external/ipfs_accelerate"}),
        "PTR-144": frozenset({"external/ipfs_datasets"}),
    }
    production_wave_one_resources = {
        task_id: submodules_by_task.get(task_id, frozenset())
        for task_id in sorted(PRODUCTION_ACTIVATION_WAVE_ONE)
    }
    if production_wave_one_resources != expected_production_wave_one_resources:
        errors.append(
            "production-activation first wave must own independent accelerator "
            "and datasets resources: expected "
            f"{expected_production_wave_one_resources}, got "
            f"{production_wave_one_resources}"
        )

    simulated_production_completed = (
        pre_production_activation_task_ids | {"PTR-143"}
    )
    simulated_production_claimable = {
        task_id
        for task_id in PRODUCTION_ACTIVATION_TASK_IDS
        if task_id not in simulated_production_completed
        and set(task_edges.get(task_id, ())).issubset(
            simulated_production_completed
        )
    }
    if simulated_production_claimable != PRODUCTION_ACTIVATION_PARALLEL_WAVE:
        errors.append(
            "production-activation post-locator dependency wave must be exactly "
            f"{sorted(PRODUCTION_ACTIVATION_PARALLEL_WAVE)}, got "
            f"{sorted(simulated_production_claimable)}"
        )
    production_parallel_shards = {
        int(task_id.rsplit("-", 1)[1]) % lane_count
        for task_id in PRODUCTION_ACTIVATION_PARALLEL_WAVE
    } if lane_count > 0 else set()
    if production_parallel_shards != {0, 1, 2}:
        errors.append(
            "production-activation post-locator wave must cover all numeric "
            f"shards, got {sorted(production_parallel_shards)}"
        )
    for left in sorted(PRODUCTION_ACTIVATION_PARALLEL_WAVE):
        for right in sorted(PRODUCTION_ACTIVATION_PARALLEL_WAVE):
            if left >= right:
                continue
            overlap = sorted(predicted_by_task[left] & predicted_by_task[right])
            if overlap:
                errors.append(
                    "production-activation post-locator tasks must have disjoint "
                    f"predicted files: {left}/{right} overlap {overlap}"
                )

    production_correction_wave_shards = {
        int(task_id.rsplit("-", 1)[1]) % lane_count
        for task_id in PRODUCTION_CORRECTION_WAVE_ONE
    } if lane_count > 0 else set()
    if production_correction_wave_shards != {0, 1}:
        errors.append(
            "current-v4 correction first wave must cover numeric shards 0 and 1, "
            f"got {sorted(production_correction_wave_shards)}"
        )
    expected_production_correction_wave_resources = {
        "PTR-150": frozenset({"external/ipfs_accelerate"}),
        "PTR-151": frozenset({"external/ipfs_datasets"}),
    }
    production_correction_wave_resources = {
        task_id: submodules_by_task.get(task_id, frozenset())
        for task_id in sorted(PRODUCTION_CORRECTION_WAVE_ONE)
    }
    if production_correction_wave_resources != (
        expected_production_correction_wave_resources
    ):
        errors.append(
            "current-v4 correction first wave must own independent accelerator "
            "and datasets resources: expected "
            f"{expected_production_correction_wave_resources}, got "
            f"{production_correction_wave_resources}"
        )
    production_correction_resource_width = len(
        set().union(*production_correction_wave_resources.values())
    )
    if production_correction_resource_width != 2:
        errors.append(
            "current-v4 correction first wave must retain repository resource "
            f"width 2, got {production_correction_resource_width}"
        )
    correction_wave_overlap = sorted(
        predicted_by_task["PTR-150"] & predicted_by_task["PTR-151"]
    )
    if correction_wave_overlap:
        errors.append(
            "current-v4 correction first-wave predicted files must be disjoint, "
            f"got {correction_wave_overlap}"
        )

    simulated_correction_wave_completed = (
        pre_production_correction_task_ids | PRODUCTION_CORRECTION_WAVE_ONE
    )
    simulated_correction_join_claimable = {
        task_id
        for task_id in PRODUCTION_CORRECTION_TASK_IDS | {"PTR-149"}
        if task_id not in simulated_correction_wave_completed
        and set(task_edges.get(task_id, ())).issubset(
            simulated_correction_wave_completed
        )
    }
    if simulated_correction_join_claimable != {"PTR-152"}:
        errors.append(
            "current-v4 correction join must make only PTR-152 claimable, got "
            f"{sorted(simulated_correction_join_claimable)}"
        )
    simulated_correction_join_completed = (
        simulated_correction_wave_completed | {"PTR-152"}
    )
    simulated_material_context_claimable = {
        task_id
        for task_id in PRODUCTION_CORRECTION_TASK_IDS | {"PTR-149"}
        if task_id not in simulated_correction_join_completed
        and set(task_edges.get(task_id, ())).issubset(
            simulated_correction_join_completed
        )
    }
    if simulated_material_context_claimable != PROOF_MATERIAL_CONTEXT_WAVE:
        errors.append(
            "current-v4 authority join must make the proof-material/context "
            f"wave claimable, got {sorted(simulated_material_context_claimable)}"
        )
    material_context_shards = {
        int(task_id.rsplit("-", 1)[1]) % lane_count
        for task_id in PROOF_MATERIAL_CONTEXT_WAVE
    } if lane_count > 0 else set()
    if material_context_shards != {0, 1}:
        errors.append(
            "proof-material/context wave must cover numeric shards 0 and 1, "
            f"got {sorted(material_context_shards)}"
        )
    material_context_overlap = sorted(
        predicted_by_task["PTR-153"] & predicted_by_task["PTR-154"]
    )
    if material_context_overlap:
        errors.append(
            "proof-material/context wave predicted files must be disjoint, got "
            f"{material_context_overlap}"
        )
    simulated_material_context_completed = (
        simulated_correction_join_completed | PROOF_MATERIAL_CONTEXT_WAVE
    )
    simulated_publication_join_claimable = {
        task_id
        for task_id in PRODUCTION_CORRECTION_TASK_IDS | {"PTR-149"}
        if task_id not in simulated_material_context_completed
        and set(task_edges.get(task_id, ())).issubset(
            simulated_material_context_completed
        )
    }
    if simulated_publication_join_claimable != {"PTR-155"}:
        errors.append(
            "proof-material/context wave must make only PTR-155 claimable, got "
            f"{sorted(simulated_publication_join_claimable)}"
        )
    simulated_publication_join_completed = (
        simulated_material_context_completed | {"PTR-155"}
    )
    simulated_handoff_claimable = {
        task_id
        for task_id in PRODUCTION_CORRECTION_TASK_IDS | {"PTR-149"}
        if task_id not in simulated_publication_join_completed
        and set(task_edges.get(task_id, ())).issubset(
            simulated_publication_join_completed
        )
    }
    if simulated_handoff_claimable != {"PTR-149"}:
        errors.append(
            "exact-v4 publication join must make only PTR-149 claimable, got "
            f"{sorted(simulated_handoff_claimable)}"
        )

    authenticated_wave_a_shards = {
        int(task_id.rsplit("-", 1)[1]) % lane_count
        for task_id in AUTHENTICATED_RECEIPT_WAVE_A
    } if lane_count > 0 else set()
    if authenticated_wave_a_shards != {0, 1, 2}:
        errors.append(
            "authenticated-receipt wave A must cover all numeric shards, got "
            f"{sorted(authenticated_wave_a_shards)}"
        )
    expected_authenticated_wave_a_resources = {
        "PTR-160": frozenset({"external/ipfs_accelerate"}),
        "PTR-161": frozenset({"external/ipfs_datasets"}),
        "PTR-162": frozenset({"external/ipfs_kit"}),
    }
    authenticated_wave_a_resources = {
        task_id: submodules_by_task.get(task_id, frozenset())
        for task_id in sorted(AUTHENTICATED_RECEIPT_WAVE_A)
    }
    if authenticated_wave_a_resources != expected_authenticated_wave_a_resources:
        errors.append(
            "authenticated-receipt wave A must own accelerator, datasets and kit "
            f"independently: got {authenticated_wave_a_resources}"
        )
    authenticated_wave_a_resource_width = len(
        set().union(*authenticated_wave_a_resources.values())
    )
    if authenticated_wave_a_resource_width != 3:
        errors.append(
            "authenticated-receipt wave A must retain repository resource "
            f"width 3, got {authenticated_wave_a_resource_width}"
        )
    for left in sorted(AUTHENTICATED_RECEIPT_WAVE_A):
        for right in sorted(AUTHENTICATED_RECEIPT_WAVE_A):
            if left < right and predicted_by_task[left] & predicted_by_task[right]:
                errors.append(
                    "authenticated-receipt wave-A predicted files overlap: "
                    f"{left}/{right}"
                )

    pre_authenticated_ids = EXPECTED_TASK_IDS - AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS
    simulated_v8_initial_completed = pre_authenticated_ids | {"PTR-160"}
    simulated_v8_initial_claimable = {
        task_id
        for task_id in AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS
        if task_id not in simulated_v8_initial_completed
        and set(task_edges.get(task_id, ())).issubset(
            simulated_v8_initial_completed
        )
    }
    if simulated_v8_initial_claimable != AUTHENTICATED_RECEIPT_REOPENED_READY:
        errors.append(
            "v8 repair must make only actionable retry evidence claimable, got "
            f"{sorted(simulated_v8_initial_claimable)}"
        )
    simulated_retry_repair_completed = (
        simulated_v8_initial_completed | AUTHENTICATED_RECEIPT_REOPENED_READY
    )
    simulated_bootstrap_frontier = {
        task_id
        for task_id in AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS
        if task_id not in simulated_retry_repair_completed
        and set(task_edges.get(task_id, ())).issubset(
            simulated_retry_repair_completed
        )
    }
    if simulated_bootstrap_frontier != AUTHENTICATED_RECEIPT_BOOTSTRAP_FRONTIER:
        errors.append(
            "PTR-170 must make only the reopened bootstrap frontier claimable, "
            f"got {sorted(simulated_bootstrap_frontier)}"
        )
    simulated_authenticated_wave_a_completed = (
        simulated_retry_repair_completed | AUTHENTICATED_RECEIPT_BOOTSTRAP_FRONTIER
    )
    simulated_authenticated_wave_b = {
        task_id
        for task_id in AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS
        if task_id not in simulated_authenticated_wave_a_completed
        and set(task_edges.get(task_id, ())).issubset(
            simulated_authenticated_wave_a_completed
        )
    }
    if simulated_authenticated_wave_b != AUTHENTICATED_RECEIPT_WAVE_B:
        errors.append(
            "authenticated-receipt wave B must be exactly "
            f"{sorted(AUTHENTICATED_RECEIPT_WAVE_B)}, got "
            f"{sorted(simulated_authenticated_wave_b)}"
        )
    authenticated_wave_b_shards = {
        int(task_id.rsplit("-", 1)[1]) % lane_count
        for task_id in AUTHENTICATED_RECEIPT_WAVE_B
    } if lane_count > 0 else set()
    if authenticated_wave_b_shards != {0, 1}:
        errors.append(
            "authenticated-receipt wave B must cover numeric shards 0 and 1, got "
            f"{sorted(authenticated_wave_b_shards)}"
        )
    expected_authenticated_wave_b_submodules = {
        "PTR-163": frozenset({"external/ipfs_datasets"}),
        "PTR-165": frozenset(),
    }
    authenticated_wave_b_submodules = {
        task_id: submodules_by_task.get(task_id, frozenset())
        for task_id in sorted(AUTHENTICATED_RECEIPT_WAVE_B)
    }
    if authenticated_wave_b_submodules != expected_authenticated_wave_b_submodules:
        errors.append(
            "authenticated-receipt wave B must independently own datasets and "
            f"the outer superproject: got {authenticated_wave_b_submodules}"
        )
    authenticated_wave_b_resources = {
        task_id: resources or frozenset({"<outer-superproject>"})
        for task_id, resources in authenticated_wave_b_submodules.items()
    }
    authenticated_wave_b_resource_width = len(
        set().union(*authenticated_wave_b_resources.values())
    )
    if authenticated_wave_b_resource_width != 2:
        errors.append(
            "authenticated-receipt wave B must retain scheduling resource "
            f"width 2, got {authenticated_wave_b_resource_width}"
        )
    wave_b_overlap = sorted(
        predicted_by_task["PTR-163"] & predicted_by_task["PTR-165"]
    )
    if wave_b_overlap:
        errors.append(
            "authenticated-receipt wave-B predicted files must be disjoint, got "
            f"{wave_b_overlap}"
        )

    simulated_wave_b_completed = (
        simulated_authenticated_wave_a_completed | AUTHENTICATED_RECEIPT_WAVE_B
    )
    simulated_runtime_join_claimable = {
        task_id
        for task_id in AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS
        if task_id not in simulated_wave_b_completed
        and set(task_edges.get(task_id, ())).issubset(simulated_wave_b_completed)
    }
    if simulated_runtime_join_claimable != {
        AUTHENTICATED_RECEIPT_RUNTIME_JOIN_TASK_ID
    }:
        errors.append(
            "authenticated-receipt wave B must make only the PTR-164 runtime "
            f"join claimable, got {sorted(simulated_runtime_join_claimable)}"
        )
    authenticated_runtime_join_shard = (
        int(AUTHENTICATED_RECEIPT_RUNTIME_JOIN_TASK_ID.rsplit("-", 1)[1])
        % lane_count
        if lane_count > 0
        else None
    )
    if authenticated_runtime_join_shard != 2:
        errors.append(
            "authenticated-receipt runtime join must use numeric shard 2, got "
            f"{authenticated_runtime_join_shard}"
        )
    authenticated_runtime_join_submodules = submodules_by_task.get(
        AUTHENTICATED_RECEIPT_RUNTIME_JOIN_TASK_ID, frozenset()
    )
    if authenticated_runtime_join_submodules != frozenset(
        {"external/ipfs_accelerate"}
    ):
        errors.append(
            "authenticated-receipt runtime join must own the accelerator, got "
            f"{sorted(authenticated_runtime_join_submodules)}"
        )

    simulated_stage = set(
        simulated_wave_b_completed
        | {AUTHENTICATED_RECEIPT_RUNTIME_JOIN_TASK_ID}
    )
    for expected_task_id in (
        AUTHENTICITY_JOIN_TASK_ID,
        OUTPUT_REPLAY_JOIN_TASK_ID,
        ZERO_CONFIG_E2E_JOIN_TASK_ID,
        AUTHENTICATED_HANDOFF_TASK_ID,
    ):
        claimable = {
            task_id
            for task_id in AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS
            if task_id not in simulated_stage
            and set(task_edges.get(task_id, ())).issubset(simulated_stage)
        }
        if claimable != {expected_task_id}:
            errors.append(
                f"authenticated-receipt DAG must make only {expected_task_id} "
                f"claimable, got {sorted(claimable)}"
            )
        simulated_stage.add(expected_task_id)

    historical_completed_tasks = tuple(
        task
        for task in tasks
        if task.task_id not in AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS
        and task.status == "completed"
    )
    historical_missing_output_set = {
        path
        for task in historical_completed_tasks
        for path in task.outputs
        if not (REPO_ROOT / path).exists()
    }
    historical_validation_target_set = {
        path
        for task in historical_completed_tasks
        for path in _validation_path_targets(task.metadata.get("validation"))
    }
    historical_missing_validation_target_set = {
        path
        for path in historical_validation_target_set
        if not (REPO_ROOT / path).exists()
    }
    historical_missing_artifact_set = (
        historical_missing_output_set | historical_missing_validation_target_set
    )
    expected_historical_missing_artifact_set = set(
        EXPECTED_HISTORICAL_MISSING_ARTIFACT_OWNERS
    )
    resolved_historical_artifacts = sorted(
        expected_historical_missing_artifact_set - historical_missing_artifact_set
    )
    unexpected_historical_missing_artifacts = sorted(
        historical_missing_artifact_set - expected_historical_missing_artifact_set
    )
    # The literal ledger records the only reviewed historical gaps and their
    # immutable correction owners; it is not a requirement that those paths
    # remain absent forever.  A path disappearing from the live missing set is
    # expected progress.  Only a newly observed gap outside the sealed ledger
    # is baseline drift.
    if unexpected_historical_missing_artifacts:
        errors.append(
            "historical missing output/validation artifact baseline drift: "
            f"unexpected-missing={unexpected_historical_missing_artifacts}"
        )
    ownership_audit_paths = (
        expected_historical_missing_artifact_set
        | set(unexpected_historical_missing_artifacts)
    )
    correction_owners_by_path = {
        path: tuple(
            sorted(
                task_id
                for task_id in AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS
                if path in predicted_by_task[task_id]
            )
        )
        for path in sorted(ownership_audit_paths)
    }
    exact_owner_assignment_mismatches = {
        path: {
            "expected_owner_task_id": expected_owner,
            "actual_owner_task_ids": list(correction_owners_by_path.get(path, ())),
        }
        for path, expected_owner in sorted(
            EXPECTED_HISTORICAL_MISSING_ARTIFACT_OWNERS.items()
        )
        if correction_owners_by_path.get(path, ()) != (expected_owner,)
    }
    if exact_owner_assignment_mismatches:
        errors.append(
            "historical artifact correction ownership must match the sealed "
            "exact path-to-owner map: "
            + json.dumps(exact_owner_assignment_mismatches, sort_keys=True)
        )
    uncovered_historical_artifacts = sorted(
        path
        for path, owners in correction_owners_by_path.items()
        if not owners
    )
    multi_owned_historical_artifacts = {
        path: list(owners)
        for path, owners in correction_owners_by_path.items()
        if len(owners) > 1
    }
    if uncovered_historical_artifacts:
        errors.append(
            "historical missing output/validation artifacts lack an exact "
            f"correction owner: {uncovered_historical_artifacts}"
        )
    if multi_owned_historical_artifacts:
        errors.append(
            "historical missing output/validation artifacts have multiple "
            "correction owners: "
            + json.dumps(multi_owned_historical_artifacts, sort_keys=True)
        )
    historical_artifact_quarantine = {
        path: {
            "owner_task_id": expected_owner,
            "owner_status": task_by_id[expected_owner].status,
            "observed_owner_task_ids": list(
                correction_owners_by_path.get(path, ())
            ),
            "sources": sorted(
                source
                for source, source_paths in (
                    ("output", historical_missing_output_set),
                    (
                        "validation_target",
                        historical_missing_validation_target_set,
                    ),
                )
                if path in source_paths
            ),
        }
        for path, expected_owner in sorted(
            EXPECTED_HISTORICAL_MISSING_ARTIFACT_OWNERS.items()
        )
        if path in historical_missing_artifact_set
    }
    completed_owner_missing_artifacts = {
        path: record["owner_task_id"]
        for path, record in historical_artifact_quarantine.items()
        if record["owner_status"] == "completed"
    }
    if completed_owner_missing_artifacts:
        errors.append(
            "completed correction owners still have quarantined historical "
            "artifacts missing from the reachable tree: "
            + json.dumps(completed_owner_missing_artifacts, sort_keys=True)
        )

    historical_missing_outputs = sorted(historical_missing_output_set)
    historical_missing_validation_targets = sorted(
        historical_missing_validation_target_set
    )
    historical_missing_validation_only = sorted(
        historical_missing_validation_target_set - historical_missing_output_set
    )
    historical_missing_artifacts = sorted(historical_missing_artifact_set)

    unordered_conflicts: list[dict[str, object]] = []
    task_ancestors = {
        task_id: _ancestors(task_id, task_edges) for task_id in task_ids
    }
    for index, left in enumerate(sorted(task_ids)):
        for right in sorted(task_ids)[index + 1 :]:
            if left in task_ancestors[right] or right in task_ancestors[left]:
                continue
            overlap = sorted(predicted_by_task[left] & predicted_by_task[right])
            if overlap:
                unordered_conflicts.append(
                    {"left": left, "right": right, "paths": overlap}
                )
    if unordered_conflicts:
        errors.append(
            "unordered tasks have predicted-file conflicts: "
            + json.dumps(unordered_conflicts, sort_keys=True)
        )

    dependency_graph = materialize_task_dependency_dag(task_records)
    if dependency_graph.invalid_task_cids:
        errors.append(
            "typed dependency graph has invalid task CIDs: "
            f"{list(dependency_graph.invalid_task_cids)}"
        )
    if dependency_graph.repair_evidence:
        errors.append(
            "typed dependency graph requires repair: "
            + json.dumps(
                [item.to_dict() for item in dependency_graph.repair_evidence],
                sort_keys=True,
            )
        )

    return {
        "schema": "ipfs_accelerate_py/proof-backed-test-reuse-preflight@1",
        "valid": not errors,
        "errors": errors,
        "plan_path": str(plan_path),
        "plan_sha256": _sha256(plan_path),
        "objective_path": str(objective_path),
        "objective_sha256": _sha256(objective_path),
        "goal_count": len(goals),
        "root_goal_ids": roots,
        "todo_path": str(todo_path),
        "todo_sha256": _sha256(todo_path),
        "task_count": len(tasks),
        "completed_task_count": len(completed_ids),
        "initial_ready_task_ids": sorted(
            AUTHENTICATED_RECEIPT_REOPENED_READY
        ),
        "initial_ready_shards": sorted(
            {
                int(task_id.rsplit("-", 1)[1]) % lane_count
                for task_id in AUTHENTICATED_RECEIPT_REOPENED_READY
            }
            if lane_count > 0
            else set()
        ),
        "sealed_initial_ready_task_ids": sorted(SEALED_INITIAL_READY),
        "sealed_initial_ready_shards": sorted(sealed_initial_shards),
        "reviewed_extension_task_ids": sorted(COMPLETION_EXTENSION_TASK_IDS),
        "reviewed_extension_wave_one_task_ids": sorted(
            COMPLETION_EXTENSION_WAVE_ONE
        ),
        "reviewed_extension_wave_one_shards": sorted(
            completion_extension_wave_shards
        ),
        "reviewed_extension_wave_one_submodules": {
            task_id: sorted(resources)
            for task_id, resources in completion_extension_wave_resources.items()
        },
        "reviewed_extension_wave_one_resource_width": (
            completion_extension_resource_width
        ),
        "reviewed_runtime_repair_task_ids": sorted(RUNTIME_REPAIR_TASK_IDS),
        "reviewed_runtime_repair_wave_one_task_ids": sorted(
            RUNTIME_REPAIR_WAVE_ONE
        ),
        "reviewed_runtime_repair_wave_one_shards": sorted(
            runtime_repair_wave_shards
        ),
        "reviewed_runtime_repair_wave_one_submodules": {
            task_id: sorted(resources)
            for task_id, resources in runtime_repair_wave_resources.items()
        },
        "reviewed_runtime_bootstrap_wave_task_ids": sorted(
            RUNTIME_BOOTSTRAP_WAVE
        ),
        "reviewed_runtime_bootstrap_wave_shards": sorted(
            runtime_bootstrap_wave_shards
        ),
        "reviewed_runtime_bootstrap_wave_submodules": {
            task_id: sorted(resources)
            for task_id, resources in runtime_bootstrap_wave_resources.items()
        },
        "reviewed_production_activation_task_ids": sorted(
            REVIEWED_PRODUCTION_ACTIVATION_TASK_IDS
        ),
        "historical_production_activation_task_ids": sorted(
            PRODUCTION_ACTIVATION_TASK_IDS
        ),
        "reviewed_production_activation_wave_one_task_ids": sorted(
            PRODUCTION_ACTIVATION_WAVE_ONE
        ),
        "reviewed_production_activation_wave_one_shards": sorted(
            production_wave_one_shards
        ),
        "reviewed_production_activation_wave_one_submodules": {
            task_id: sorted(resources)
            for task_id, resources in production_wave_one_resources.items()
        },
        "reviewed_production_activation_parallel_wave_task_ids": sorted(
            PRODUCTION_ACTIVATION_PARALLEL_WAVE
        ),
        "reviewed_production_activation_parallel_wave_shards": sorted(
            production_parallel_shards
        ),
        "reviewed_production_correction_task_ids": sorted(
            PRODUCTION_CORRECTION_TASK_IDS
        ),
        "reviewed_production_correction_wave_one_task_ids": sorted(
            PRODUCTION_CORRECTION_WAVE_ONE
        ),
        "reviewed_production_correction_wave_one_shards": sorted(
            production_correction_wave_shards
        ),
        "reviewed_production_correction_wave_one_submodules": {
            task_id: sorted(resources)
            for task_id, resources in production_correction_wave_resources.items()
        },
        "reviewed_production_correction_wave_one_resource_width": (
            production_correction_resource_width
        ),
        "reviewed_production_correction_join_task_id": "PTR-152",
        "reviewed_proof_material_context_wave_task_ids": sorted(
            PROOF_MATERIAL_CONTEXT_WAVE
        ),
        "reviewed_proof_material_context_wave_shards": sorted(
            material_context_shards
        ),
        "reviewed_exact_v4_publication_join_task_id": "PTR-155",
        "reviewed_operator_handoff_task_id": "PTR-149",
        "authenticated_receipt_correction_task_ids": sorted(
            AUTHENTICATED_RECEIPT_CORRECTION_TASK_IDS
        ),
        "authenticated_receipt_wave_a_task_ids": sorted(
            AUTHENTICATED_RECEIPT_WAVE_A
        ),
        "authenticated_receipt_wave_a_shards": sorted(
            authenticated_wave_a_shards
        ),
        "authenticated_receipt_wave_a_submodules": {
            task_id: sorted(resources)
            for task_id, resources in authenticated_wave_a_resources.items()
        },
        "authenticated_receipt_wave_a_resource_width": (
            authenticated_wave_a_resource_width
        ),
        "authenticated_receipt_actionable_retry_task_id": "PTR-170",
        "authenticated_receipt_actionable_retry_shard": (
            170 % lane_count if lane_count > 0 else None
        ),
        "authenticated_receipt_bootstrap_frontier_task_ids": sorted(
            AUTHENTICATED_RECEIPT_BOOTSTRAP_FRONTIER
        ),
        "authenticated_receipt_wave_b_task_ids": sorted(
            AUTHENTICATED_RECEIPT_WAVE_B
        ),
        "authenticated_receipt_wave_b_shards": sorted(
            authenticated_wave_b_shards
        ),
        "authenticated_receipt_wave_b_submodules": {
            task_id: sorted(resources)
            for task_id, resources in authenticated_wave_b_resources.items()
        },
        "authenticated_receipt_wave_b_resource_width": (
            authenticated_wave_b_resource_width
        ),
        "authenticated_receipt_runtime_join_task_id": (
            AUTHENTICATED_RECEIPT_RUNTIME_JOIN_TASK_ID
        ),
        "authenticated_receipt_runtime_join_shard": (
            authenticated_runtime_join_shard
        ),
        "authenticated_receipt_runtime_join_submodules": sorted(
            authenticated_runtime_join_submodules
        ),
        "authenticated_receipt_authenticity_join_task_id": (
            AUTHENTICITY_JOIN_TASK_ID
        ),
        "authenticated_receipt_output_replay_join_task_id": (
            OUTPUT_REPLAY_JOIN_TASK_ID
        ),
        "authenticated_receipt_zero_config_e2e_join_task_id": (
            ZERO_CONFIG_E2E_JOIN_TASK_ID
        ),
        "authenticated_receipt_handoff_task_id": AUTHENTICATED_HANDOFF_TASK_ID,
        "historical_missing_output_paths": historical_missing_outputs,
        "historical_missing_output_count": len(historical_missing_outputs),
        "historical_validation_target_paths": sorted(
            historical_validation_target_set
        ),
        "historical_validation_target_count": len(
            historical_validation_target_set
        ),
        "historical_missing_validation_target_paths": (
            historical_missing_validation_targets
        ),
        "historical_missing_validation_target_count": len(
            historical_missing_validation_targets
        ),
        "historical_missing_validation_only_paths": (
            historical_missing_validation_only
        ),
        "historical_missing_artifact_paths": historical_missing_artifacts,
        "historical_missing_artifact_count": len(historical_missing_artifacts),
        "expected_historical_missing_artifact_owners": dict(
            sorted(EXPECTED_HISTORICAL_MISSING_ARTIFACT_OWNERS.items())
        ),
        "resolved_historical_artifact_paths": resolved_historical_artifacts,
        # Retained for report consumers created before the ledger became
        # progression-aware.
        "expected_historical_artifacts_no_longer_missing": (
            resolved_historical_artifacts
        ),
        "unexpected_historical_missing_artifact_paths": (
            unexpected_historical_missing_artifacts
        ),
        "exact_historical_artifact_owner_assignment_mismatches": (
            exact_owner_assignment_mismatches
        ),
        "historical_missing_artifact_quarantine": (
            historical_artifact_quarantine
        ),
        "uncovered_historical_missing_artifact_paths": (
            uncovered_historical_artifacts
        ),
        "multi_owned_historical_missing_artifact_paths": (
            multi_owned_historical_artifacts
        ),
        "completed_owner_missing_historical_artifact_paths": (
            completed_owner_missing_artifacts
        ),
        "uncovered_historical_missing_output_paths": sorted(
            historical_missing_output_set.intersection(
                uncovered_historical_artifacts
            )
        ),
        "current_claimable_task_ids": sorted(claimable_task_ids),
        "current_claimable_shards": sorted(
            {
                int(task_id.rsplit("-", 1)[1]) % lane_count
                for task_id in claimable_task_ids
            }
            if lane_count > 0
            else set()
        ),
        "unordered_predicted_file_conflicts": unordered_conflicts,
        "dependency_graph_id": _canonical_sha256(dependency_graph.to_dict()),
        "configuration_path": str(config_path),
        "configuration_sha256": _sha256(config_path),
        "optional_proof_infrastructure_is_launch_gate": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-path", type=Path, default=PLAN_PATH)
    parser.add_argument("--objective-path", type=Path, default=OBJECTIVE_PATH)
    parser.add_argument("--todo-path", type=Path, default=TODO_PATH)
    parser.add_argument("--config-path", type=Path, default=CONFIG_PATH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate(
        args.objective_path.resolve(),
        args.todo_path.resolve(),
        args.config_path.resolve(),
        args.plan_path.resolve(),
    )
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    sys.stdout.write(payload)
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

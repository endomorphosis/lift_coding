"""FACP-008: unified claim inventory, defect corpus, and TCB fan-in gate.

Acceptance (taskboard):
- Corpus contains all roadmap seeds with expected disposition and mutation oracle.
- TCB names versions/assumptions.
- Every planned task traces to at least one inventory fact or normative requirement.

Discovery remains non-completion; source inventory reports are immutable inputs.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from facp_historical_git import (
    assert_historical_ancestor,
    blob_text,
    current_head,
    git_output,
    superproject_gitlink,
)

BASELINE = REPO_ROOT / "implementation_plan" / "formal_assurance_control_plane" / "baseline"
CLAIM_INVENTORY_PATH = BASELINE / "claim_inventory.json"
DEFECT_CORPUS_PATH = BASELINE / "defect_corpus.jsonl"
TCB_PATH = BASELINE / "trusted_computing_base.json"
TODO_PATH = REPO_ROOT / "implementation_plan" / "docs" / "49-formal-assurance-control-plane.todo.md"
SCHEDULER_PATH = REPO_ROOT / "config" / "formal_assurance_control_plane_scheduler.json"

CLAIM_SCHEMA = "facp/claim-inventory@1"
CORPUS_ENTRY_SCHEMA = "facp/defect-corpus-entry@1"
TCB_SCHEMA = "facp/tcb@1"
TASK_ID = "FACP-008"
GOAL_ID = "FACP-G010"
BUNDLE = "facp/inventory/fanin"

REQUIRED_EVIDENCE_SUBSET = {
    "canonical_claim_vocabulary",
    "exact_source_spans",
    "defect_families",
    "expected_counterexamples",
    "compatible_component_map",
    "formal_tool_capabilities_and_absence",
}

ROADMAP_FAMILIES = {
    "false_success",
    "mock_capability",
    "pseudo_cid",
    "import_effect",
    "browser_authority",
    "mutable_dependency",
    "stale_proof",
    "missing_recovery",
    "license_conflict",
    "hermetic_to_live",
    "secret_flow",
    "canonicalization_conflict",
    "total_assurance_ladder",
}

REQUIRED_INPUT_INVENTORIES = {
    "FACP-001": "reusable_primitives.json",
    "FACP-002": "accelerate_claims.json",
    "FACP-003": "datasets_claims.json",
    "FACP-004": "kit_evidence.json",
    "FACP-005": "swissknife_authority.json",
    "FACP-006": "mcplusplus_contracts.json",
    "FACP-007": "release_rights.json",
}

# Representative seeds that the roadmap/plan starting evidence and inventory
# wave must preserve through fan-in.
REQUIRED_ROADMAP_SEED_IDS = {
    # Accelerate (FACP-002)
    "seed:mock-worker-cuda-true",
    "seed:raw-sha256-as-cid",
    "seed:hardcoded-hwtest-true",
    "seed:mock-handler-real-label",
    # Datasets (FACP-003)
    "cx-ds-false-fallback-download-upload",
    "cx-ds-import-auto-install-default-on",
    "seed:datasets-mit-agpl-rights-conflict",
    # Kit honesty (FACP-004)
    "seed:kit-zero-live-qualified-backends-honest",
    # SwissKnife (FACP-005)
    "cx-sk-auth-default-granted-consent",
    # Release (FACP-007)
    "seed:accelerate-git-plus-main-mutable-deps",
    # Reuse ladders / recovery (FACP-001)
    "seed:ladder-accelerate-assurance-level",
    "seed:missing-lease-recovery-gap",
}

PLANNING_FOREST_PATHS = (
    "Mcp-Plus-Plus",
    "external/ipfs_accelerate",
    "external/ipfs_datasets",
    "external/ipfs_kit",
    "swissknife",
)

FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TASK_HEADING_RE = re.compile(r"^## (FACP-\d+) ", re.M)


def _gitlink_commit(path: str) -> str:
    return superproject_gitlink(REPO_ROOT, "HEAD", path)


def _planned_task_ids() -> set[str]:
    text = TODO_PATH.read_text(encoding="utf-8")
    return set(TASK_HEADING_RE.findall(text))


def _load_corpus() -> list[dict[str, Any]]:
    assert DEFECT_CORPUS_PATH.is_file(), f"missing defect corpus: {DEFECT_CORPUS_PATH}"
    entries: list[dict[str, Any]] = []
    for line_no, line in enumerate(
        DEFECT_CORPUS_PATH.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        payload = json.loads(line)
        assert isinstance(payload, dict), f"corpus line {line_no} is not an object"
        entries.append(payload)
    return entries


@pytest.fixture(scope="module")
def claim_inventory() -> dict[str, Any]:
    assert CLAIM_INVENTORY_PATH.is_file(), f"missing claim inventory: {CLAIM_INVENTORY_PATH}"
    payload = json.loads(CLAIM_INVENTORY_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.fixture(scope="module")
def defect_corpus() -> list[dict[str, Any]]:
    return _load_corpus()


@pytest.fixture(scope="module")
def tcb() -> dict[str, Any]:
    assert TCB_PATH.is_file(), f"missing TCB: {TCB_PATH}"
    payload = json.loads(TCB_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.fixture(scope="module")
def scheduler() -> dict[str, Any]:
    assert SCHEDULER_PATH.is_file(), f"missing scheduler config: {SCHEDULER_PATH}"
    payload = json.loads(SCHEDULER_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_claim_inventory_task_and_schema_binding(claim_inventory: dict[str, Any]) -> None:
    assert claim_inventory["schema"] == CLAIM_SCHEMA
    assert claim_inventory["schema_version"] == 1
    assert claim_inventory["task_id"] == TASK_ID
    assert claim_inventory["goal_id"] == GOAL_ID
    assert claim_inventory["bundle"] == BUNDLE
    assert claim_inventory["behavior_change"] is False
    assert claim_inventory["policy"]["discovery_is_not_completion"] is True
    assert claim_inventory["policy"]["source_reports_immutable"] is True
    assert set(claim_inventory["evidence_subset"]) >= REQUIRED_EVIDENCE_SUBSET


def test_source_binding_matches_scheduler_and_gitlinks(
    claim_inventory: dict[str, Any],
) -> None:
    binding = claim_inventory["source_binding"]
    controller_commit = binding["controller_commit"]
    assert_historical_ancestor(REPO_ROOT, controller_commit)
    assert binding["controller_tree"] == git_output(
        REPO_ROOT, "rev-parse", f"{controller_commit}^{{tree}}"
    )
    assert binding["scheduler_config"] == ("config/formal_assurance_control_plane_scheduler.json")

    forest = {entry["path"]: entry for entry in binding["planning_forest"]}
    assert set(forest) == set(PLANNING_FOREST_PATHS)

    historical_scheduler = json.loads(
        blob_text(REPO_ROOT, controller_commit, binding["scheduler_config"])
    )
    sb = historical_scheduler["source_binding"]
    expected = {
        "Mcp-Plus-Plus": sb["mcp_plus_plus_planning_revision"],
        "external/ipfs_accelerate": sb["accelerate_planning_revision"],
        "external/ipfs_datasets": sb["datasets_planning_revision"],
        "external/ipfs_kit": sb["kit_planning_revision"],
        "swissknife": sb["swissknife_planning_revision"],
    }
    for path, commit in expected.items():
        assert FULL_SHA_RE.match(commit)
        assert forest[path]["gitlink_commit"] == commit
        assert superproject_gitlink(REPO_ROOT, controller_commit, path) == commit
        current_gitlink = _gitlink_commit(path)
        assert current_head(REPO_ROOT / path) == current_gitlink
        assert_historical_ancestor(REPO_ROOT / path, commit, current_gitlink)

    inputs = {entry["task_id"]: entry for entry in binding["inventory_inputs"]}
    assert set(inputs) == set(REQUIRED_INPUT_INVENTORIES)
    for task_id, filename in REQUIRED_INPUT_INVENTORIES.items():
        path = inputs[task_id]["path"]
        assert path.endswith(filename)
        assert (REPO_ROOT / path).is_file()


def test_canonical_claim_vocabulary_is_closed(claim_inventory: dict[str, Any]) -> None:
    vocab = claim_inventory["canonical_claim_vocabulary"]
    dims = vocab["evidence_dimensions"]
    required_dims = {
        "origin",
        "integrity",
        "authority",
        "policy",
        "proof",
        "freshness",
        "effect",
        "environment",
        "review",
    }
    assert set(dims) == required_dims
    for name, values in dims.items():
        assert isinstance(values, list) and values, name
        assert len(values) == len(set(values)), name

    outcomes = vocab["closed_outcomes"]
    assert "Observed" in outcomes and "Verified" in outcomes and "Unavailable" in outcomes
    assert "success" not in {o.lower() for o in outcomes}

    predicates = set(vocab["promotion_predicates"])
    assert {
        "production_supported",
        "effect_successful",
        "proof_reusable",
        "receipt_authoritative",
        "release_admissible",
    } <= predicates

    assert set(vocab["roadmap_defect_families"]) >= ROADMAP_FAMILIES
    assert "reject_illegal_promotion" in set(vocab["expected_disposition_vocabulary"])


def test_compatible_component_map_covers_reusable_primitives(
    claim_inventory: dict[str, Any],
) -> None:
    components = claim_inventory["compatible_component_map"]
    assert isinstance(components, list) and len(components) >= 40
    required = {
        "component_id",
        "repository",
        "commit",
        "path",
        "symbol",
        "adoption_disposition",
        "total_assurance_ladder",
    }
    ladder_count = 0
    seen: set[str] = set()
    for component in components:
        missing = required - set(component)
        assert not missing, missing
        assert component["component_id"] not in seen
        seen.add(component["component_id"])
        assert FULL_SHA_RE.match(component["commit"])
        if component["total_assurance_ladder"]:
            ladder_count += 1
            assert component.get("fca_adaptation")
    assert ladder_count >= 4


def test_inventory_facts_have_source_spans_and_task_binding(
    claim_inventory: dict[str, Any],
) -> None:
    facts = claim_inventory["inventory_facts"]
    assert isinstance(facts, list) and len(facts) >= 50
    by_source_task = {task_id: 0 for task_id in REQUIRED_INPUT_INVENTORIES}
    seen: set[str] = set()
    for fact in facts:
        fact_id = fact["fact_id"]
        assert fact_id not in seen
        seen.add(fact_id)
        assert fact["kind"]
        assert fact["source_task"] in REQUIRED_INPUT_INVENTORIES
        assert fact["source_inventory"] == REQUIRED_INPUT_INVENTORIES[fact["source_task"]]
        assert fact["summary"]
        assert isinstance(fact["source_spans"], list)
        by_source_task[fact["source_task"]] += 1
        for span in fact["source_spans"]:
            assert "path" in span and span["path"]
    assert all(count >= 1 for count in by_source_task.values()), by_source_task


def test_every_planned_task_traces_to_inventory_fact_or_normative_requirement(
    claim_inventory: dict[str, Any],
) -> None:
    planned = _planned_task_ids()
    assert planned, "todo file produced no FACP tasks"
    assert "FACP-000" in planned and "FACP-060" in planned

    normative_ids = {n["requirement_id"] for n in claim_inventory["normative_requirements"]}
    assert normative_ids
    for requirement in claim_inventory["normative_requirements"]:
        assert requirement["statement"]
        assert requirement["source"]
        assert (REPO_ROOT / requirement["source"]).is_file()

    fact_ids = {f["fact_id"] for f in claim_inventory["inventory_facts"]}
    trace_rows = claim_inventory["task_traceability"]
    traced = {row["task_id"] for row in trace_rows}
    assert traced == planned, sorted(planned ^ traced)

    for row in trace_rows:
        refs = row["traces_to"]
        assert isinstance(refs, list) and refs, row["task_id"]
        for ref in refs:
            kind = ref["kind"]
            ref_id = ref["id"]
            assert kind in {"inventory_fact", "normative_requirement"}, (row["task_id"], kind)
            if kind == "inventory_fact":
                assert ref_id in fact_ids, (row["task_id"], ref_id)
            else:
                assert ref_id in normative_ids, (row["task_id"], ref_id)


def test_defect_corpus_contains_all_roadmap_seeds_with_disposition_and_oracle(
    defect_corpus: list[dict[str, Any]], claim_inventory: dict[str, Any]
) -> None:
    assert defect_corpus, "defect corpus is empty"
    assert claim_inventory["defect_corpus"]["seed_count"] == len(defect_corpus)

    seen: set[str] = set()
    families: set[str] = set()
    for entry in defect_corpus:
        assert entry["schema"] == CORPUS_ENTRY_SCHEMA
        assert entry["task_id"] == TASK_ID
        assert entry["goal_id"] == GOAL_ID
        seed_id = entry["seed_id"]
        assert seed_id not in seen, seed_id
        seen.add(seed_id)
        assert entry.get("roadmap_seed") is True
        assert entry["family"]
        families.add(entry["family"])
        disposition = entry.get("expected_disposition")
        oracle = entry.get("mutation_oracle")
        assert isinstance(disposition, str) and disposition.strip(), seed_id
        assert isinstance(oracle, str) and oracle.strip(), seed_id
        assert entry.get("source_task") in REQUIRED_INPUT_INVENTORIES
        assert entry.get("source_inventory") in REQUIRED_INPUT_INVENTORIES.values()
        spans = entry.get("source_spans")
        assert isinstance(spans, list)
        # Exact source spans are required for code-bound seeds; historical/path-only
        # receipts may carry path without line numbers.
        if spans:
            for span in spans:
                assert "path" in span and span["path"]

    missing_families = ROADMAP_FAMILIES - families
    assert not missing_families, sorted(missing_families)

    missing_seeds = REQUIRED_ROADMAP_SEED_IDS - seen
    assert not missing_seeds, sorted(missing_seeds)

    # Fan-in must not drop accelerate confirmed defect seeds.
    accelerate = json.loads((BASELINE / "accelerate_claims.json").read_text(encoding="utf-8"))
    accelerate_seeds = {
        defect["counterexample_seed"]["seed_id"] for defect in accelerate["confirmed_defects"]
    }
    assert accelerate_seeds <= seen, sorted(accelerate_seeds - seen)


def test_tcb_names_versions_and_assumptions(tcb: dict[str, Any]) -> None:
    assert tcb["schema"] == TCB_SCHEMA
    assert tcb["task_id"] == TASK_ID
    assert tcb["goal_id"] == GOAL_ID
    assert tcb["bundle"] == BUNDLE
    assert tcb["policy"]["missing_tool_is_typed_capability_gap"] is True
    assert tcb["policy"]["no_ad_hoc_installation"] is True
    assert tcb["policy"]["no_simulated_proof_for_absent_tools"] is True

    binding = tcb["source_binding"]
    controller_commit = binding["controller_commit"]
    assert_historical_ancestor(REPO_ROOT, controller_commit)
    assert binding["controller_tree"] == git_output(
        REPO_ROOT, "rev-parse", f"{controller_commit}^{{tree}}"
    )
    for entry in binding["planning_forest"]:
        path = entry["path"]
        assert superproject_gitlink(REPO_ROOT, controller_commit, path) == entry[
            "gitlink_commit"
        ]
        current_gitlink = _gitlink_commit(path)
        assert current_head(REPO_ROOT / path) == current_gitlink
        assert_historical_ancestor(REPO_ROOT / path, entry["gitlink_commit"], current_gitlink)

    components = tcb["components"]
    assert isinstance(components, list) and len(components) >= 10
    seen: set[str] = set()
    tool_components = []
    for component in components:
        component_id = component["component_id"]
        assert component_id not in seen
        seen.add(component_id)
        assert component["role"] or component.get("name")
        status = component["status"]
        assert status in {"present", "absent", "conditional"}
        assumptions = component.get("assumptions")
        assert isinstance(assumptions, list) and assumptions, component_id
        for assumption in assumptions:
            assert isinstance(assumption, str) and assumption.strip()
        if status == "present":
            version = component.get("version")
            assert version is not None and str(version).strip(), component_id
        else:
            # Absent tools still name a version slot (null) and typed gap disposition.
            assert component.get("version") in (None, "")
            assert component.get("capability") == "typed_capability_gap"
        if component_id.startswith("tool:"):
            tool_components.append(component)

    assert any(c["name"] == "lean4" for c in tool_components)
    lean = next(c for c in tool_components if c["name"] == "lean4")
    assert lean["status"] == "present"
    assert str(lean["version"]).startswith("4.")

    global_assumptions = tcb["assumptions"]
    assert isinstance(global_assumptions, list) and len(global_assumptions) >= 3

    absence = {entry["tool"] for entry in tcb["formal_tool_absence"]}
    capabilities = tcb["formal_tool_capabilities"]
    for tool, meta in capabilities.items():
        if meta["status"] == "absent":
            assert tool in absence
            entry = next(e for e in tcb["formal_tool_absence"] if e["tool"] == tool)
            assert entry["disposition"] == "typed_capability_gap"
            prohibited = set(entry["prohibited_compensation"])
            assert "simulated_proof" in prohibited
            assert "import_time_installation" in prohibited

    # Portfolio pins must match scheduler planning revisions.
    historical_scheduler = json.loads(
        blob_text(REPO_ROOT, controller_commit, binding["scheduler_config"])
    )
    sb = historical_scheduler["source_binding"]
    portfolio_versions = {
        c["path"]: c["version"] for c in components if c["component_id"].startswith("portfolio:")
    }
    assert portfolio_versions["external/ipfs_accelerate"] == sb["accelerate_planning_revision"]
    assert portfolio_versions["external/ipfs_datasets"] == sb["datasets_planning_revision"]
    assert portfolio_versions["external/ipfs_kit"] == sb["kit_planning_revision"]
    assert portfolio_versions["swissknife"] == sb["swissknife_planning_revision"]
    assert portfolio_versions["Mcp-Plus-Plus"] == sb["mcp_plus_plus_planning_revision"]

    allocation = tcb["allocation"]
    assert "Lean 4" in allocation["normative_claim_semantics"]
    assert "Rust" in allocation["executable_trusted_kernel"]


def test_fanin_acceptance_flags_are_true(
    claim_inventory: dict[str, Any], tcb: dict[str, Any]
) -> None:
    acceptance = claim_inventory["acceptance"]
    assert acceptance["corpus_contains_all_roadmap_seeds"] is True
    assert acceptance["every_seed_has_expected_disposition_and_mutation_oracle"] is True
    assert acceptance["tcb_names_versions_and_assumptions"] is True
    assert (
        acceptance["every_planned_task_traces_to_inventory_fact_or_normative_requirement"] is True
    )
    tcb_acceptance = tcb["acceptance"]
    assert tcb_acceptance["every_component_names_version_or_absence"] is True
    assert tcb_acceptance["every_component_names_assumptions"] is True
    assert tcb_acceptance["absent_tools_are_typed_gaps"] is True

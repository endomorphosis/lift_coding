#!/usr/bin/env python3
"""Fail-closed validator for the PCTDD control program.

Markdown is an operator-authored projection.  This validator proves structural
conformance only; task completion remains owned by the configured DuckDB/Quack
task authority and its independently admitted evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs/architecture/PARALLEL_CONTENT_SEALING_PROOF_CARRYING_TDD_PLAN.md"
OBJECTIVES_PATH = ROOT / "docs/architecture/parallel_content_sealing_proof_carrying_tdd.objectives.md"
BOARD_PATH = ROOT / "docs/architecture/parallel_content_sealing_proof_carrying_tdd.todo.md"
CONFIG_PATH = ROOT / "config/agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json"
PROFILE_PATH = ROOT / "config/parallel_content_sealing_proof_carrying_tdd_validation_profiles.json"
DISPATCHER_PATH = ROOT / "scripts/run_parallel_content_sealing_proof_carrying_tdd_validation.py"
MIGRATION_PATH = ROOT / "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/g5_migration_inventory.json"
RECEIPT_PATH = ROOT / "artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/PCTDD-000.json"
CONTROL_MANIFEST_PATH = ROOT / "config/parallel_content_sealing_proof_carrying_tdd_control_manifest.json"
NAMESPACE = "parallel-content-sealing-proof-carrying-tdd-v1"
PLAN_REVISION = "PCTDD-PLAN-V1.1"
STORE_GENERATION = "pctdd-v1-g6"
RUNTIME_ROOT = "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g6"

TASK_RE = re.compile(
    r"^##\s+(PCTDD-\d{3})\s*(?:[\u2014\u2013:\-]\s*)?(.+?)\s*$", re.MULTILINE
)
GOAL_RE = re.compile(
    r"^##\s+(PCTDD-G\d{3})\s*(?:[\u2014\u2013:\-]\s*)?(.+?)\s*$", re.MULTILINE
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
EXPECTED_TASK_IDS = tuple(f"PCTDD-{number:03d}" for number in range(54))
EXPECTED_TITLES = dict(zip(EXPECTED_TASK_IDS, TASK_TITLES, strict=True))
W1_RESCUE_CANDIDATES = {
    "PCTDD-001": "e623dd43dbc8f8feb503dd8dea2a6afb4bbd26c0",
    "PCTDD-002": "25b2a4e0fd1ab354a0db5317ec8ea49ce0319a61",
    "PCTDD-003": "37ccf1a42d7bbf0a6cad0a20a7671ddc0cbffac6",
    "PCTDD-004": "2b37146f4f2f354ced02ca5327d0a7d21344f044",
}
FROZEN_G5_RESCUE_BRANCH_PREFIX_COUNTS = {
    "refs/heads/rescue/pctdd-001-3c1c70df54d4-": 7,
    "refs/heads/rescue/pctdd-002-28ace0eab61e-": 7,
    "refs/heads/rescue/pctdd-003-783b342df728-": 8,
    "refs/heads/rescue/pctdd-004-1f308616e139-": 7,
}
PCTDD_004_COMPONENT_COMMIT = "48edb688ac31bc3d05fdd5c8efd7e50ab14b755e"
PCTDD_004_COMPONENT_PARENT = "cfbd381ee6196e818ecd59a438386a60b5d71bd7"

TASK_EXTRA_OUTPUTS = {
    "PCTDD-000": (CONTROL_MANIFEST_PATH.relative_to(ROOT).as_posix(),),
    "PCTDD-049": (
        "benchmarks/agent_supervisor/parallel_content_sealing/pctdd_049_hash_seal_results.json",
    ),
    "PCTDD-050": (
        "benchmarks/agent_supervisor/proof_carrying_tdd/pctdd_050_pytest_proof_tdd_results.json",
    ),
    "PCTDD-052": (
        "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/fast_tdd/capstone_self_hosting.py",
        "artifacts/parallel_content_sealing_proof_carrying_tdd/capstone/PCTDD-052.json",
    ),
    "PCTDD-053": (
        "artifacts/parallel_content_sealing_proof_carrying_tdd/PCTDD-053.release.json",
        "docs/architecture/PARALLEL_CONTENT_SEALING_PROOF_CARRYING_TDD_RELEASE.md",
    ),
}

GOAL_PARENTS: dict[str, str | None] = {
    "PCTDD-G000": None,
    "PCTDD-G010": "PCTDD-G000",
    "PCTDD-G011": "PCTDD-G010",
    "PCTDD-G012": "PCTDD-G010",
    "PCTDD-G013": "PCTDD-G010",
    "PCTDD-G020": "PCTDD-G000",
    "PCTDD-G021": "PCTDD-G020",
    "PCTDD-G022": "PCTDD-G020",
    "PCTDD-G023": "PCTDD-G020",
    "PCTDD-G030": "PCTDD-G000",
    "PCTDD-G031": "PCTDD-G030",
    "PCTDD-G032": "PCTDD-G030",
    "PCTDD-G033": "PCTDD-G030",
    "PCTDD-G040": "PCTDD-G000",
    "PCTDD-G041": "PCTDD-G040",
    "PCTDD-G042": "PCTDD-G040",
    "PCTDD-G043": "PCTDD-G040",
    "PCTDD-G050": "PCTDD-G000",
    "PCTDD-G051": "PCTDD-G050",
    "PCTDD-G052": "PCTDD-G050",
    "PCTDD-G053": "PCTDD-G050",
    "PCTDD-G060": "PCTDD-G000",
    "PCTDD-G061": "PCTDD-G060",
    "PCTDD-G062": "PCTDD-G060",
}

TASK_GOALS = {
    "PCTDD-000": "PCTDD-G010",
    "PCTDD-001": "PCTDD-G011", "PCTDD-002": "PCTDD-G011",
    "PCTDD-003": "PCTDD-G013", "PCTDD-004": "PCTDD-G012",
    **{f"PCTDD-{n:03d}": "PCTDD-G021" for n in range(5, 11)},
    **{f"PCTDD-{n:03d}": "PCTDD-G022" for n in range(11, 15)},
    **{f"PCTDD-{n:03d}": "PCTDD-G023" for n in range(15, 21)},
    **{f"PCTDD-{n:03d}": "PCTDD-G031" for n in range(21, 25)},
    **{f"PCTDD-{n:03d}": "PCTDD-G032" for n in range(25, 28)},
    **{f"PCTDD-{n:03d}": "PCTDD-G033" for n in range(28, 32)},
    "PCTDD-032": "PCTDD-G041",
    **{f"PCTDD-{n:03d}": "PCTDD-G042" for n in range(33, 36)},
    **{f"PCTDD-{n:03d}": "PCTDD-G043" for n in range(36, 40)},
    "PCTDD-040": "PCTDD-G051", "PCTDD-041": "PCTDD-G051",
    "PCTDD-042": "PCTDD-G052",
    **{f"PCTDD-{n:03d}": "PCTDD-G053" for n in range(43, 48)},
    "PCTDD-048": "PCTDD-G061", "PCTDD-051": "PCTDD-G061",
    "PCTDD-049": "PCTDD-G062", "PCTDD-050": "PCTDD-G062",
    "PCTDD-052": "PCTDD-G062", "PCTDD-053": "PCTDD-G062",
}

ALLOWED_STATUSES = {
    "todo", "queued", "proposed", "admitted", "ready", "leased",
    "in_progress", "running", "blocked", "completed", "accepted",
    "failed", "rejected", "quarantined", "cancelled",
}
TERMINAL_STATUSES = {"completed", "accepted", "failed", "rejected", "quarantined", "cancelled"}
ALLOWED_REPOSITORIES = {
    "endomorphosis/ipfs_accelerate_py",
    "endomorphosis/ipfs_datasets_py",
    "endomorphosis/ipfs_kit_py",
    "endomorphosis/lift_coding",
    "cross-repository",
}

PROTECTED_PATHS = {
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
}

REQUIRED_FIELD_GROUPS: tuple[tuple[str, ...], ...] = (
    ("status",), ("completion_mode", "completion"),
    ("is_schedulable", "schedulable"), ("operator_only",),
    ("priority",), ("track",), ("depends_on", "dependencies"),
    ("bundle",), ("parallel_lane", "lane"), ("resource_class",),
    ("timeout_seconds", "implementation_timeout_seconds", "timeout"),
    ("provider_role",), ("owning_repository",), ("directive",), ("exact_inputs", "inputs"),
    ("predecessor_rescue_candidate",),
    ("outputs",), ("predicted_files",),
    ("predicted_symbols", "symbols"), ("interfaces",),
    ("preconditions",), ("declared_effects", "allowed_effects"),
    ("validation_profile",), ("validation", "validation_command"), ("required_evidence",),
    ("acceptance_criteria", "acceptance"), ("conflict_policy",),
    ("llm_context_budget_bytes",), ("no_model_route",), ("model_fallback",),
    ("rollout_mode",), ("protected_paths",), ("known_limitations",),
    ("goal_id", "parent_goal"), ("board_namespace",),
)

REQUIRED_REQUIRED_MODE_EVIDENCE = (
    "pre_semantic_state_root", "pre_proof_seal_root", "source_snapshot",
    "overlay_token", "hash_preparation_receipt", "selected_test_proof_manifest",
    "fixture_test_execution_key_receipts", "phase_disposition_receipts",
    "proof_forest_delta",
    "prepared_seal_cid", "seal_publication_receipt", "post_semantic_state_root",
    "post_proof_seal_root",
    "rollout_mode_required",
)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)


def _load_validation_profiles() -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("pctdd_validation_dispatcher", DISPATCHER_PATH)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load protected validation dispatcher")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return dict(module.validate_profile_document(_load_json(PROFILE_PATH)))


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _clean(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "`'\"":
        return value[1:-1].strip()
    return value


def _parse_blocks(text: str, pattern: re.Pattern[str]) -> list[tuple[str, str, dict[str, str]]]:
    matches = list(pattern.finditer(text))
    blocks: list[tuple[str, str, dict[str, str]]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        fields: dict[str, str] = {}
        for raw in text[match.end():end].splitlines():
            line = raw.strip()
            if line.startswith("- ") and ":" in line:
                name, value = line[2:].split(":", 1)
            else:
                bold = re.match(r"^\*\*([^*]+):\*\*\s*(.*)$", line)
                if not bold:
                    continue
                name, value = bold.group(1), bold.group(2)
            key = _normalize_key(name)
            if key in fields:
                raise ValueError(f"{match.group(1)} duplicates field {key}")
            fields[key] = _clean(value)
        blocks.append((match.group(1), match.group(2).strip(), fields))
    return blocks


def _field(fields: dict[str, str], *names: str) -> str:
    for name in names:
        if name in fields:
            return fields[name]
    return ""


def _items(value: str) -> tuple[str, ...]:
    value = value.strip()
    if not value or value.lower() in {"none", "null", "[]", "n/a", "not_applicable"}:
        return ()
    if value.startswith("["):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, list):
            return tuple(str(item).strip().strip("`") for item in decoded if str(item).strip())
    return tuple(item.strip().strip("`") for item in re.split(r"\s*[,;]\s*", value) if item.strip())


def _boolean(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    return None


def _check_acyclic(dependencies: dict[str, tuple[str, ...]]) -> list[str]:
    errors: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str, trail: tuple[str, ...]) -> None:
        if task_id in visiting:
            errors.append("dependency cycle: " + " -> ".join((*trail, task_id)))
            return
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in dependencies.get(task_id, ()):
            visit(dependency, (*trail, task_id))
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in dependencies:
        visit(task_id, ())
    return sorted(set(errors))


def _contains_path(value: str, protected: str) -> bool:
    candidate = value.strip().strip("`").rstrip("/")
    target = protected.rstrip("/")
    return candidate == target or candidate.startswith(target + "/") or target.startswith(candidate + "/")


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _assert_phrase(corpus: str, alternatives: Iterable[str], label: str, errors: list[str]) -> None:
    if not any(re.search(pattern, corpus, re.IGNORECASE | re.DOTALL) for pattern in alternatives):
        errors.append(f"claim/control corpus missing invariant: {label}")


def validate() -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    required_files = (
        PLAN_PATH, OBJECTIVES_PATH, BOARD_PATH, CONFIG_PATH, PROFILE_PATH,
        DISPATCHER_PATH, MIGRATION_PATH, CONTROL_MANIFEST_PATH,
    )
    missing = [path.relative_to(ROOT).as_posix() for path in required_files if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing control artifacts: " + ", ".join(missing))

    plan = PLAN_PATH.read_text(encoding="utf-8")
    objectives = OBJECTIVES_PATH.read_text(encoding="utf-8")
    board = BOARD_PATH.read_text(encoding="utf-8")
    config = _load_json(CONFIG_PATH)
    if not isinstance(config, dict):
        raise ValueError("scheduler config must be a JSON object")
    try:
        profiles = _load_validation_profiles()
    except Exception as exc:
        profiles = {}
        errors.append(f"validation profiles rejected: {type(exc).__name__}: {exc}")

    tasks = _parse_blocks(board, TASK_RE)
    task_ids = tuple(task_id for task_id, _title, _fields in tasks)
    if task_ids != EXPECTED_TASK_IDS:
        errors.append("task headings must be exactly PCTDD-000 through PCTDD-053 in order")
    duplicates = sorted(task_id for task_id, count in Counter(task_ids).items() if count != 1)
    if duplicates:
        errors.append(f"duplicate task IDs: {duplicates}")
    if len(tasks) != 54:
        errors.append(f"task population is {len(tasks)}, expected 54")

    fields_by_task: dict[str, dict[str, str]] = {}
    outputs_owner: dict[str, str] = {}
    dependencies: dict[str, tuple[str, ...]] = {}
    rollout_rank: dict[str, int] = {}
    for task_id, title, fields in tasks:
        fields_by_task[task_id] = fields
        if title != EXPECTED_TITLES.get(task_id):
            errors.append(f"{task_id} title differs from the sealed directive")
        for group in REQUIRED_FIELD_GROUPS:
            if not any(_field(fields, name) for name in group):
                errors.append(f"{task_id} missing field ({' or '.join(group)})")
        if "predicted_paths" in fields:
            errors.append(
                f"{task_id} uses legacy Predicted paths; use daemon-recognized Predicted files"
            )
        status = _field(fields, "status").lower()
        if status not in ALLOWED_STATUSES:
            errors.append(f"{task_id} has non-closed status {status!r}")
        if _field(fields, "board_namespace") != NAMESPACE:
            errors.append(f"{task_id} board namespace differs")
        if _field(fields, "goal_id", "parent_goal") != TASK_GOALS.get(task_id):
            errors.append(f"{task_id} goal mapping differs")
        owner = _field(fields, "owning_repository")
        if owner not in ALLOWED_REPOSITORIES:
            errors.append(f"{task_id} has invalid owning repository {owner!r}")
        if task_id == "PCTDD-004" and owner != "endomorphosis/ipfs_accelerate_py":
            errors.append("PCTDD-004 must be owned by the accelerator instrumentation authority")

        dependency_values = _items(_field(fields, "depends_on", "dependencies"))
        dependencies[task_id] = dependency_values
        for dependency in dependency_values:
            if dependency not in EXPECTED_TASK_IDS:
                errors.append(f"{task_id} has unknown dependency {dependency}")

        task_outputs = _items(_field(fields, "outputs"))
        if not task_outputs:
            errors.append(f"{task_id} declares no exact output")
        expected_receipt = f"artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/{task_id}.json"
        if expected_receipt not in task_outputs:
            errors.append(f"{task_id} does not own its unique task receipt")
        profile = profiles.get(task_id, {})
        expected_test_target = str(profile.get("required_test_target") or "")
        if not expected_test_target:
            errors.append(f"{task_id} has no resolved validation-profile test target")
        expected_outputs = {
            expected_receipt,
            expected_test_target,
            *TASK_EXTRA_OUTPUTS.get(task_id, ()),
        }
        if expected_test_target and set(task_outputs) != expected_outputs:
            errors.append(
                f"{task_id} output manifest differs from its exact owned outputs"
            )
        for output in task_outputs:
            prior = outputs_owner.get(output)
            if prior and prior != task_id:
                errors.append(f"output {output} is owned by both {prior} and {task_id}")
            outputs_owner[output] = task_id

        predicted = _items(_field(fields, "predicted_files"))
        missing_predicted_outputs = sorted(set(task_outputs).difference(predicted))
        if missing_predicted_outputs:
            errors.append(
                f"{task_id} predicted files omit exact owned outputs: "
                f"{missing_predicted_outputs}"
            )
        if expected_test_target and expected_test_target not in predicted:
            errors.append(f"{task_id} predicted files omit its exact test target")
        for extra_output in TASK_EXTRA_OUTPUTS.get(task_id, ()):
            if extra_output not in predicted:
                errors.append(f"{task_id} predicted files omit owned output {extra_output}")
        if task_id == "PCTDD-004" and (
            "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/incremental_sealing/critical_path.py"
            not in predicted
        ):
            errors.append("PCTDD-004 scope omits the exact critical-path instrumentation module")
        write_scope = (
            *predicted,
            *_items(_field(fields, "allowed_paths")),
            *_items(_field(fields, "owned_paths")),
        )
        for path in write_scope:
            if path.startswith("external/ipfs_accelerate/") and owner not in {
                "endomorphosis/ipfs_accelerate_py", "cross-repository"
            }:
                errors.append(f"{task_id} crosses accelerate path authority")
            if path.startswith("external/ipfs_datasets/") and owner not in {
                "endomorphosis/ipfs_datasets_py", "cross-repository"
            }:
                errors.append(f"{task_id} crosses datasets path authority")
            if path.startswith("external/ipfs_kit/") and owner not in {
                "endomorphosis/ipfs_kit_py", "cross-repository"
            }:
                errors.append(f"{task_id} crosses kit path authority")
            if task_id != "PCTDD-000" and any(_contains_path(path, protected) for protected in PROTECTED_PATHS):
                errors.append(f"{task_id} predicts a write to protected control {path}")

        mode_tokens = {_normalize_text(item) for item in _items(_field(fields, "rollout_mode"))}
        if not mode_tokens:
            mode_tokens = {_normalize_text(_field(fields, "rollout_mode"))}
        if task_id <= "PCTDD-043":
            allowed_modes, rank = {"bootstrap"}, 0
        elif task_id == "PCTDD-044":
            allowed_modes, rank = {"shadow_hash"}, 1
        elif task_id == "PCTDD-045":
            allowed_modes, rank = {"shadow_reuse", "shadow_proof"}, 3
            if not {"shadow_reuse", "shadow_proof"}.issubset(mode_tokens):
                errors.append("PCTDD-045 must bind both shadow_reuse and shadow_proof")
        elif task_id in {"PCTDD-046", "PCTDD-047"}:
            allowed_modes, rank = {"protected"}, 4
        else:
            allowed_modes, rank = {"required"}, 5
        rollout_rank[task_id] = rank
        if not mode_tokens or not mode_tokens.issubset(allowed_modes):
            errors.append(f"{task_id} rollout mode {sorted(mode_tokens)} differs")

        evidence_normalized = _normalize_text(_field(fields, "required_evidence"))
        if rank == 5:
            for required in REQUIRED_REQUIRED_MODE_EVIDENCE:
                if required not in evidence_normalized:
                    errors.append(f"{task_id} required-mode evidence omits {required}")
            if not (
                "aggregate_proof" in evidence_normalized
                and "evidence_tier_receipt" in evidence_normalized
            ):
                errors.append(
                    f"{task_id} required-mode evidence omits aggregate proof/configured evidence-tier receipt"
                )
            if not (
                "expected" in evidence_normalized
                and "resulting" in evidence_normalized
                and "generation" in evidence_normalized
            ):
                errors.append(f"{task_id} required-mode evidence omits expected/resulting generations")

        completion = _normalize_text(_field(fields, "completion_mode", "completion"))
        if "markdown" in completion:
            errors.append(f"{task_id} permits Markdown-only completion")
        validation = _field(fields, "validation", "validation_command").strip()
        expected_validation = (
            "python scripts/run_parallel_content_sealing_proof_carrying_tdd_validation.py "
            f"--task {task_id}"
        )
        if validation != expected_validation:
            errors.append(
                f"{task_id} validation must be the exact task-bound protected dispatcher command"
            )
        expected_profile = f"pctdd-validation/{PLAN_REVISION}/{task_id}@1"
        if _field(fields, "validation_profile") != expected_profile:
            errors.append(f"{task_id} validation profile differs")
        provider_role = _field(fields, "provider_role")
        expected_role = "operator-only" if task_id == "PCTDD-000" else "grok-only"
        if provider_role != expected_role:
            errors.append(
                f"{task_id} provider role must be the exact current parser vocabulary {expected_role!r}"
            )
        context_budget = _field(fields, "llm_context_budget_bytes")
        if context_budget != "24000":
            errors.append(f"{task_id} llm_context_budget_bytes must be exactly 24000")
        directive = _field(fields, "directive")
        acceptance = _field(fields, "acceptance_criteria", "acceptance")
        if task_id not in directive or expected_test_target not in directive:
            errors.append(f"{task_id} directive is not task/target specific")
        if expected_profile not in acceptance or expected_test_target not in acceptance:
            errors.append(f"{task_id} acceptance is not profile/target specific")
        if task_id != "PCTDD-000" and not all(
            phrase in acceptance
            for phrase in (
                "controller-owned validation authority independently executes",
                "implementation model cannot fall back",
                "worker-authored test alone is never sufficient",
                "machine-readable pytest phase evidence",
                "protected baseline regressions",
            )
        ):
            errors.append(f"{task_id} lacks independent controller validation and broad baseline acceptance")
        if task_id == "PCTDD-047" and not all(
            phrase in acceptance
            for phrase in ("schema-aware required-mode completion gate", "does not fabricate")
        ):
            errors.append("PCTDD-047 must install, not prematurely claim, the required evidence gate")
        if task_id >= "PCTDD-048" and "PCTDD-047 schema-aware gate" not in acceptance:
            errors.append(f"{task_id} acceptance omits the PCTDD-047 required-mode gate")
        rescue = _field(fields, "predecessor_rescue_candidate")
        if task_id in W1_RESCUE_CANDIDATES:
            if not (
                "candidate only" in rescue
                and "independently revalidate" in rescue
                and W1_RESCUE_CANDIDATES[task_id] in rescue
            ):
                errors.append(f"{task_id} g5 rescue candidate policy differs")
        elif rescue.lower() != "none":
            errors.append(f"{task_id} unexpectedly names a predecessor rescue candidate")
        if status in TERMINAL_STATUSES and task_id != "PCTDD-000":
            errors.append(f"{task_id} implementation terminal cannot be asserted by the seed board")

    errors.extend(_check_acyclic(dependencies))
    if dependencies.get("PCTDD-000"):
        errors.append("PCTDD-000 must have no dependencies")
    for task_id in ("PCTDD-001", "PCTDD-002", "PCTDD-003", "PCTDD-004"):
        if "PCTDD-000" not in dependencies.get(task_id, ()):
            errors.append(f"{task_id} must depend on sealed PCTDD-000")
    for task_id, task_dependencies in dependencies.items():
        for dependency in task_dependencies:
            if rollout_rank.get(dependency, 0) > rollout_rank.get(task_id, 0):
                errors.append(f"{task_id} depends backward across rollout ordering on {dependency}")
    for before, after in (("PCTDD-044", "PCTDD-045"), ("PCTDD-045", "PCTDD-046"),
                          ("PCTDD-046", "PCTDD-047"), ("PCTDD-047", "PCTDD-048"),
                          ("PCTDD-051", "PCTDD-052"), ("PCTDD-052", "PCTDD-053")):
        if before not in dependencies.get(after, ()):
            errors.append(f"rollout gate {after} must directly depend on {before}")

    pctdd_000 = fields_by_task.get("PCTDD-000", {})
    if _field(pctdd_000, "status").lower() != "todo":
        errors.append("PCTDD-000 Markdown status must remain todo; only DuckDB/Quack may complete it")
    if _boolean(_field(pctdd_000, "operator_only")) is not True:
        errors.append("PCTDD-000 must be operator-only")
    if _boolean(_field(pctdd_000, "is_schedulable", "schedulable")) is not False:
        errors.append("PCTDD-000 must not be schedulable")
    if _normalize_text(_field(pctdd_000, "completion_mode", "completion")) != "operator_evidence":
        errors.append("PCTDD-000 completion mode must be operator_evidence")
    for task_id, fields in fields_by_task.items():
        if task_id != "PCTDD-000":
            if _boolean(_field(fields, "operator_only")) is not False:
                errors.append(f"{task_id} must be a worker task, not operator-only")
            if _boolean(_field(fields, "is_schedulable", "schedulable")) is not True:
                errors.append(f"{task_id} must be schedulable")
            if _field(fields, "status").lower() != "todo":
                errors.append(f"{task_id} seed status must remain todo in Markdown")

    goal_blocks = _parse_blocks(objectives, GOAL_RE)
    goal_ids = tuple(goal_id for goal_id, _title, _fields in goal_blocks)
    if goal_ids != tuple(GOAL_PARENTS):
        errors.append("goal headings/order differ from the sealed 24-goal hierarchy")
    duplicate_goals = sorted(goal for goal, count in Counter(goal_ids).items() if count != 1)
    if duplicate_goals:
        errors.append(f"duplicate goal IDs: {duplicate_goals}")
    for goal_id, _title, fields in goal_blocks:
        actual_parent = _field(fields, "parent_goal", "parent_goal_id", "parent")
        expected_parent = GOAL_PARENTS.get(goal_id)
        if expected_parent is None:
            if actual_parent.lower() not in {"", "none", "null", "root", "not_applicable"}:
                errors.append(f"{goal_id} root parent must be empty/none")
        elif actual_parent != expected_parent:
            errors.append(f"{goal_id} parent {actual_parent!r} != {expected_parent}")
        expected_producers = []
        for task_id in EXPECTED_TASK_IDS:
            current: str | None = TASK_GOALS[task_id]
            while current is not None and current != goal_id:
                current = GOAL_PARENTS[current]
            if current == goal_id:
                expected_producers.append(task_id)
        if _items(_field(fields, "producing_tasks")) != tuple(expected_producers):
            errors.append(f"{goal_id} producing tasks do not match descendant task ownership")

    expected_config_paths = {
        "board_namespace": NAMESPACE,
        "taskboard_path": BOARD_PATH.relative_to(ROOT).as_posix(),
        "objectives_path": OBJECTIVES_PATH.relative_to(ROOT).as_posix(),
        "plan_path": PLAN_PATH.relative_to(ROOT).as_posix(),
        "validator_path": "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py",
        "validation_profile_path": PROFILE_PATH.relative_to(ROOT).as_posix(),
        "validation_dispatcher_path": DISPATCHER_PATH.relative_to(ROOT).as_posix(),
    }
    for name, expected in expected_config_paths.items():
        if config.get(name) != expected:
            errors.append(f"scheduler config {name} differs from protected control")
    if config.get("task_prefix") != "PCTDD-":
        errors.append("scheduler config task_prefix differs")
    if config.get("accepted_plan_revision_alias") != PLAN_REVISION:
        errors.append("scheduler plan revision differs")
    if config.get("root_goal_id") not in {None, "PCTDD-G000"}:
        errors.append("scheduler root goal differs")

    configured_protected = {
        str(item).strip().rstrip("/") for item in (config.get("protected_paths") or [])
    }
    missing_protected = sorted(path for path in PROTECTED_PATHS if path.rstrip("/") not in configured_protected)
    if missing_protected:
        errors.append("scheduler protected paths omit: " + ", ".join(missing_protected))
    control_manifest = _load_json(CONTROL_MANIFEST_PATH)
    if not isinstance(control_manifest, dict):
        errors.append("PCTDD-000 control manifest must be an object")
    else:
        if (
            control_manifest.get("schema") != "pctdd/operator-control-manifest@1"
            or control_manifest.get("task_id") != "PCTDD-000"
            or control_manifest.get("dependency_seal_must_hash_this_manifest") is not True
            or control_manifest.get("manifest_is_completion_receipt") is not False
        ):
            errors.append("PCTDD-000 control manifest claim boundary differs")
        prerequisites = control_manifest.get("completion_prerequisites") or []
        for phrase in (
            "dependency validator valid=true",
            "board validator valid=true",
            "configured-board preflight valid=true",
            "configured-board implementation dry-run success",
        ):
            if phrase not in prerequisites:
                errors.append(f"PCTDD-000 control manifest omits prerequisite: {phrase}")
        manifest_hashes = control_manifest.get(
            "protected_control_hashes_before_manifest_and_seal"
        )
        expected_manifest_paths = PROTECTED_PATHS - {
            CONTROL_MANIFEST_PATH.relative_to(ROOT).as_posix(),
            "config/parallel_content_sealing_proof_carrying_tdd_dependencies.seal.json",
        }
        if not isinstance(manifest_hashes, dict) or set(manifest_hashes) != expected_manifest_paths:
            errors.append("PCTDD-000 control manifest protected path population differs")
        else:
            for relative, claimed in sorted(manifest_hashes.items()):
                path = ROOT / relative
                if not path.is_file() or claimed != _sha256_file(path):
                    errors.append(f"PCTDD-000 control manifest hash differs: {relative}")

    database = config.get("database_program") or config.get("task_store") or {}
    if database.get("authority_mode") != "quack" or database.get("task_source_kind") != "duckdb":
        errors.append("authoritative task store must be DuckDB with Quack state ownership")
    if database.get("failover_policy", "fail_closed") != "fail_closed":
        errors.append("task authority failover must be fail_closed")
    if database.get("store_generation") != STORE_GENERATION:
        errors.append("task authority must use the fresh g6 store generation")
    if database.get("quack_endpoint") != "quack:127.0.0.1:27278":
        errors.append("g6 Quack endpoint differs")
    expected_owner_management = {
        "mode": "managed_local",
        "owner_state_dir": str((ROOT / RUNTIME_ROOT / "quack-owner").resolve()),
        "startup_timeout_seconds": 120.0,
        "health_check_interval_seconds": 5.0,
        "max_restart_attempts": 3,
        "initial_backoff_seconds": 1.0,
        "max_backoff_seconds": 10.0,
        "termination_grace_seconds": 40.0,
    }
    if database.get("owner_management") != expected_owner_management:
        errors.append(
            "g6 Quack owner management must use the exact fenced managed-local policy"
        )
    for name in ("store_id", "event_store_path", "runtime_registry_path", "worktree_root"):
        if not str(database.get(name) or "").startswith(RUNTIME_ROOT + "/"):
            errors.append(f"database_program.{name} does not use the g6 runtime root")
    if database.get("predecessor_store_generation") != "pctdd-v1-g5" or database.get("predecessor_is_read_only_history") is not True:
        errors.append("g5 predecessor generation must remain explicit read-only history")
    projection = config.get("initial_projection") or {}
    if projection.get("completed_task_ids") != [] or projection.get("ready_task_ids") != []:
        errors.append("initial projection must leave PCTDD-000 todo and all worker tasks dependency-waiting")
    if projection.get("post_operator_completed_task_ids") != ["PCTDD-000"]:
        errors.append("post-operator projection must complete only PCTDD-000")
    if projection.get("post_operator_ready_task_ids") != [
        "PCTDD-001", "PCTDD-002", "PCTDD-003", "PCTDD-004"
    ]:
        errors.append("post-operator ready frontier differs")
    provider = config.get("provider") or {}
    if provider.get("implementation_fallback_authorized") is not False:
        errors.append("Codex implementation fallback must be explicitly unauthorized")
    if provider.get("provider_id") != "grok_cli" or provider.get("model_id") != "grok-4.6":
        errors.append("implementation provider must be the exact Grok-only route")
    if provider.get("completion_authority") != "controller_owned_sealed_validation_and_database_cas":
        errors.append("completion authority must remain controller-owned")
    if any(key.startswith("fallback_") for key in provider):
        errors.append("Grok-only PCTDD provider policy must not encode a fallback route")
    ducklake = config.get("ducklake_projection_program") or config.get("ducklake") or {}
    if ducklake.get("authority", ducklake.get("authoritative", False)) is not False:
        errors.append("DuckLake analytics/history projection must remain non-authoritative")
    if ducklake.get("scheduling_prerequisite", False) is not False:
        errors.append("DuckLake must not become a scheduling prerequisite")
    for name in ("catalog_path", "data_path"):
        if not str(ducklake.get(name) or "").startswith(RUNTIME_ROOT + "/ducklake/"):
            errors.append(f"DuckLake {name} does not use the g6 projection root")

    amendment = config.get("control_amendment") or {}
    if amendment.get("revision") != PLAN_REVISION or amendment.get("amends") != "PCTDD-PLAN-V1":
        errors.append("scheduler control amendment lineage differs")
    if amendment.get("migration_inventory") != MIGRATION_PATH.relative_to(ROOT).as_posix():
        errors.append("scheduler migration inventory binding differs")
    migration = _load_json(MIGRATION_PATH)
    predecessor = migration.get("predecessor") if isinstance(migration, dict) else {}
    successor = migration.get("successor") if isinstance(migration, dict) else {}
    if not isinstance(predecessor, dict) or predecessor.get("bootstrap_event_watermark") != 103:
        errors.append("g5 migration event watermark differs")
    expected_predecessor = {
        "store_generation": "pctdd-v1-g5",
        "plan_revision": "PCTDD-PLAN-V1",
        "plan_root_cid": "baguqeeraqwk4z47whu652pvidcaxeyjkp6dmeuxhevmjhkpjehxdpmstsukq",
        "pctdd_000_completion_receipt_cid": "baguqeeray2wlpjlflnaxx7jpynquwhpenm7hk6pwwkxsmxwzr6eopltnccua",
        "source_head": "c488d97ed5665b5744d983fc4a294989df519361",
        "source_tree": "e3fda4eaaecf14a56815f586df05feb94f093979",
        "frozen_database_sha256": "e7aa5935d452f2df2bff462467799a57994771a8971cd20528d56284bd4ec5a5",
        "bootstrap_receipt_sha256": "6c65b2ad424683c110867c8842e46b256af93dc7116f35f2c102a857b6893616",
        "preserved_failed_validation_rescue_branch_count": 29,
    }
    if isinstance(predecessor, dict):
        for name, expected in expected_predecessor.items():
            if predecessor.get(name) != expected:
                errors.append(f"g5 migration predecessor {name} differs")
    if not isinstance(successor, dict) or successor.get("store_generation") != STORE_GENERATION:
        errors.append("g5 migration successor generation differs")
    migration_candidates = migration.get("w1_rescue_candidates") if isinstance(migration, dict) else {}
    if not isinstance(migration_candidates, dict) or {
        task_id: str(record.get("outer_commit") or "")
        for task_id, record in migration_candidates.items()
        if isinstance(record, dict)
    } != W1_RESCUE_CANDIDATES:
        errors.append("g5 migration W1 rescue candidate refs differ")
    if isinstance(migration_candidates, dict):
        for task_id in ("PCTDD-001", "PCTDD-002", "PCTDD-003"):
            record = migration_candidates.get(task_id) or {}
            if record.get("classification") != "receipt-observation-only" or record.get("component_commits") != {}:
                errors.append(f"{task_id} migration must remain receipt-only history")
            if "never cherry-pick" not in str(record.get("application_policy") or ""):
                errors.append(f"{task_id} migration lacks stale outer-commit prohibition")
        pctdd_004 = migration_candidates.get("PCTDD-004") or {}
        component = (pctdd_004.get("component_commits") or {}).get("external/ipfs_accelerate") or {}
        if (
            pctdd_004.get("classification") != "component-reuse-candidate-only"
            or component.get("commit") != PCTDD_004_COMPONENT_COMMIT
            or component.get("prior_gitlink") != PCTDD_004_COMPONENT_PARENT
            or "never adopt the outer gitlink" not in str(pctdd_004.get("application_policy") or "")
        ):
            errors.append("PCTDD-004 migration is not component-safe")
    g5_db = ROOT / str(predecessor.get("frozen_database_path") or "")
    g5_receipt = ROOT / str(predecessor.get("bootstrap_receipt_path") or "")
    for label, path, expected in (
        ("g5 database", g5_db, str(predecessor.get("frozen_database_sha256") or "")),
        ("g5 bootstrap receipt", g5_receipt, str(predecessor.get("bootstrap_receipt_sha256") or "")),
    ):
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            errors.append(f"{label} bytes do not match migration inventory")
    rescue_refs = [
        line
        for line in _git("for-each-ref", "--format=%(refname)", "refs/heads/rescue").splitlines()
        if line.startswith("refs/heads/rescue/pctdd-")
    ]
    for prefix, expected_count in FROZEN_G5_RESCUE_BRANCH_PREFIX_COUNTS.items():
        actual_count = sum(ref.startswith(prefix) for ref in rescue_refs)
        if actual_count != expected_count:
            errors.append(
                "g5 PCTDD failed-validation rescue branch population differs "
                f"for {prefix}: expected {expected_count}, observed {actual_count}"
            )
    for task_id, commit in W1_RESCUE_CANDIDATES.items():
        if subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        ).returncode != 0:
            errors.append(f"{task_id} outer migration commit is unavailable")
    nested = ROOT / "external/ipfs_accelerate"
    for commit in (PCTDD_004_COMPONENT_COMMIT, PCTDD_004_COMPONENT_PARENT):
        if subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=nested,
            capture_output=True,
            check=False,
        ).returncode != 0:
            errors.append(f"PCTDD-004 nested migration commit unavailable: {commit}")
    outer_gitlink = _git("ls-tree", W1_RESCUE_CANDIDATES["PCTDD-004"], "external/ipfs_accelerate").split()
    if len(outer_gitlink) < 3 or outer_gitlink[2] != PCTDD_004_COMPONENT_COMMIT:
        errors.append("PCTDD-004 outer rescue commit does not bind the recorded component commit")
    outer_parent_gitlink = _git(
        "ls-tree",
        W1_RESCUE_CANDIDATES["PCTDD-004"] + "^",
        "external/ipfs_accelerate",
    ).split()
    if len(outer_parent_gitlink) < 3 or outer_parent_gitlink[2] != PCTDD_004_COMPONENT_PARENT:
        errors.append("PCTDD-004 outer parent does not bind the recorded prior gitlink")
    runtime_paths = config.get("runtime_paths") or {}
    if runtime_paths.get("root") != RUNTIME_ROOT:
        errors.append("runtime_paths.root must be the fresh g6 root")
    for name in ("state", "worktrees", "merge_queue", "logs", "evidence", "quack_owner"):
        if not str(runtime_paths.get(name) or "").startswith(RUNTIME_ROOT + "/"):
            errors.append(f"runtime_paths.{name} does not use the g6 root")

    safety = config.get("safety_floors") or {}
    floor_aliases = {
        "identity_divergence": ("identity_divergence",),
        "false_test_phase_reuse": ("false_test_phase_reuse",),
        "stale_authoritative_reuse": ("stale_authoritative_reuse",),
        "selection_false_negative_regressions": ("selection_false_negative_regressions",),
        "simulated_proof_admissions": ("simulated_proof_admissions",),
        "model_created_proof_authority_completion": (
            "model_created_proof_authority_completion", "model_created_authority_or_completion",
        ),
        "unauthorized_root_publications": ("unauthorized_root_publications",),
        "lost_concurrent_updates": ("lost_concurrent_updates",),
        "escaped_critical_seeded_defects": ("escaped_critical_seeded_defects",),
        "secret_witness_leaks": ("secret_witness_leaks", "secret_or_witness_leaks"),
    }
    for floor, aliases in sorted(floor_aliases.items()):
        values = [safety[name] for name in aliases if name in safety]
        if values != [0]:
            errors.append(f"safety floor {floor} must be explicitly zero exactly once")

    # A tracked receipt may be present on a later control revision, but the
    # Markdown board itself never becomes completion authority.
    if RECEIPT_PATH.is_file():
        receipt = _load_json(RECEIPT_PATH)
        if not isinstance(receipt, dict) or receipt.get("task_id") != "PCTDD-000":
            errors.append("PCTDD-000 receipt task binding differs")
        evidence = _normalize_text(json.dumps(receipt, sort_keys=True))
        if "markdown" in evidence and "non_authoritative" not in evidence:
            errors.append("PCTDD-000 receipt may not elevate Markdown to completion authority")

    corpus_parts = [plan, board, objectives]
    for relative in (
        "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/authority_matrix.json",
        "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/proof_claim_matrix.json",
        "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/hash_identity_inventory.json",
    ):
        path = ROOT / relative
        if path.is_file():
            corpus_parts.append(path.read_text(encoding="utf-8"))
        else:
            errors.append(f"missing protected claim artifact {relative}")
    corpus = "\n".join(corpus_parts)
    for alternatives, label in (
        ((re.escape(NAMESPACE),), "board namespace"),
        ((re.escape(PLAN_REVISION),), "plan revision"),
        ((r"CID.{0,100}exact (?:byte|bytes)", r"exact byte identity.{0,100}CID"), "CID is exact-byte identity"),
        ((r"Git (?:blob )?OID.{0,150}memo",), "Git OID is memo key only"),
        ((r"filesystem metadata.{0,150}candidate",), "filesystem metadata is candidate-only"),
        ((r"chunk manifest.{0,150}(?:does not|not).{0,40}raw",), "chunk manifest is not raw CID"),
        ((r"signed (?:execution )?receipt.{0,180}(?:assertion|issuer|trust)",), "signed receipt claim boundary"),
        ((r"aggregate (?:ZK|zero.knowledge).{0,250}(?:does not|not).{0,80}(?:CPython|execution)",), "aggregate proof does not upgrade leaves"),
        ((r"TestPassStatementV1.{0,180}(?:unchanged|not (?:widened|changed)|preserve)",), "TestPassStatementV1 unchanged"),
        ((r"simulated.{0,160}(?:not|never|cannot).{0,80}(?:production|admission|admitted)",), "simulated proof rejected from production"),
        ((r"(?:serial|ordered).{0,100}WAL.{0,180}(?:CAS|current.root)",), "serial WAL/root-CAS publication"),
        ((r"aggregate.{0,180}(?:does not|cannot|must not).{0,100}(?:exceed|upgrade).{0,80}(?:leaf|receipt)",), "aggregate claim cannot exceed leaf evidence"),
        ((r"Markdown.{0,100}(?:non.authoritative|not.{0,30}(?:completion|authority))",), "Markdown is non-authoritative"),
    ):
        _assert_phrase(corpus, alternatives, label, errors)

    status = "passed" if not errors else "failed"
    return {
        "schema": "pctdd/board-validation@1",
        "status": status,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "board_namespace": NAMESPACE,
        "plan_revision": PLAN_REVISION,
        "task_count": len(tasks),
        "goal_count": len(goal_blocks),
        "dependency_count": sum(len(value) for value in dependencies.values()),
        "source_head": _git("rev-parse", "HEAD"),
        "source_tree": _git("rev-parse", "HEAD^{tree}"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-all", action="store_true", help="validate every fail-closed gate")
    parser.parse_args()
    try:
        result = validate()
    except Exception as exc:  # fail closed while retaining machine-readable diagnostics
        result = {
            "schema": "pctdd/board-validation@1",
            "status": "failed",
            "valid": False,
            "errors": [f"{type(exc).__name__}: {exc}"],
            "warnings": [],
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("valid") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())

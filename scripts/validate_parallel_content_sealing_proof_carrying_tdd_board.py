#!/usr/bin/env python3
"""Fail-closed validator for the PCTDD control program.

Markdown is an operator-authored projection.  This validator proves structural
conformance only; task completion remains owned by the configured DuckDB/Quack
task authority and its independently admitted evidence.
"""

from __future__ import annotations

import argparse
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
RECEIPT_PATH = ROOT / "artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/PCTDD-000.json"
NAMESPACE = "parallel-content-sealing-proof-carrying-tdd-v1"
PLAN_REVISION = "PCTDD-PLAN-V1"

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
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/authority_matrix.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/proof_claim_matrix.json",
    "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/benchmark_preregistration.json",
    "config/parallel_content_sealing_proof_carrying_tdd_dependencies.seal.json",
    "config/agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json",
    "config/parallel_content_sealing_proof_carrying_tdd_benchmark.json",
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py",
    "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py",
    "scripts/materialize_parallel_content_sealing_proof_carrying_tdd_program.py",
    "scripts/ops/agent_supervisor/parallel_content_sealing_proof_carrying_tdd.py",
}

REQUIRED_FIELD_GROUPS: tuple[tuple[str, ...], ...] = (
    ("status",), ("completion_mode", "completion"),
    ("is_schedulable", "schedulable"), ("operator_only",),
    ("priority",), ("track",), ("depends_on", "dependencies"),
    ("bundle",), ("parallel_lane", "lane"), ("resource_class",),
    ("timeout_seconds", "implementation_timeout_seconds", "timeout"),
    ("provider_role",), ("owning_repository",), ("exact_inputs", "inputs"),
    ("outputs",), ("predicted_paths", "predicted_files"),
    ("predicted_symbols", "symbols"), ("interfaces",),
    ("preconditions",), ("declared_effects", "allowed_effects"),
    ("validation", "validation_command"), ("required_evidence",),
    ("acceptance_criteria", "acceptance"), ("conflict_policy",),
    ("context_budget",), ("no_model_route",), ("model_fallback",),
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


def _assert_phrase(corpus: str, alternatives: Iterable[str], label: str, errors: list[str]) -> None:
    if not any(re.search(pattern, corpus, re.IGNORECASE | re.DOTALL) for pattern in alternatives):
        errors.append(f"claim/control corpus missing invariant: {label}")


def validate() -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    required_files = (PLAN_PATH, OBJECTIVES_PATH, BOARD_PATH, CONFIG_PATH)
    missing = [path.relative_to(ROOT).as_posix() for path in required_files if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing control artifacts: " + ", ".join(missing))

    plan = PLAN_PATH.read_text(encoding="utf-8")
    objectives = OBJECTIVES_PATH.read_text(encoding="utf-8")
    board = BOARD_PATH.read_text(encoding="utf-8")
    config = _load_json(CONFIG_PATH)
    if not isinstance(config, dict):
        raise ValueError("scheduler config must be a JSON object")

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
        for output in task_outputs:
            prior = outputs_owner.get(output)
            if prior and prior != task_id:
                errors.append(f"output {output} is owned by both {prior} and {task_id}")
            outputs_owner[output] = task_id

        predicted = _items(_field(fields, "predicted_paths", "predicted_files"))
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
        elif task_id == "PCTDD-046":
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
        validation = _field(fields, "validation", "validation_command").strip().lower()
        if validation in {"", "true", "false", "none", "todo", "tbd", "echo pass"}:
            errors.append(f"{task_id} validation command is missing or non-operative")
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

    expected_config_paths = {
        "board_namespace": NAMESPACE,
        "taskboard_path": BOARD_PATH.relative_to(ROOT).as_posix(),
        "objectives_path": OBJECTIVES_PATH.relative_to(ROOT).as_posix(),
        "plan_path": PLAN_PATH.relative_to(ROOT).as_posix(),
        "validator_path": "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py",
    }
    for name, expected in expected_config_paths.items():
        if config.get(name) != expected:
            errors.append(f"scheduler config {name} differs from protected control")
    if config.get("task_prefix") != "PCTDD-":
        errors.append("scheduler config task_prefix differs")
    if config.get("root_goal_id") not in {None, "PCTDD-G000"}:
        errors.append("scheduler root goal differs")

    configured_protected = {
        str(item).strip().rstrip("/") for item in (config.get("protected_paths") or [])
    }
    missing_protected = sorted(path for path in PROTECTED_PATHS if path.rstrip("/") not in configured_protected)
    if missing_protected:
        errors.append("scheduler protected paths omit: " + ", ".join(missing_protected))

    database = config.get("database_program") or config.get("task_store") or {}
    if database.get("authority_mode") != "quack" or database.get("task_source_kind") != "duckdb":
        errors.append("authoritative task store must be DuckDB with Quack state ownership")
    if database.get("failover_policy", "fail_closed") != "fail_closed":
        errors.append("task authority failover must be fail_closed")
    ducklake = config.get("ducklake_projection_program") or config.get("ducklake") or {}
    if ducklake.get("authority", ducklake.get("authoritative", False)) is not False:
        errors.append("DuckLake analytics/history projection must remain non-authoritative")
    if ducklake.get("scheduling_prerequisite", False) is not False:
        errors.append("DuckLake must not become a scheduling prerequisite")

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

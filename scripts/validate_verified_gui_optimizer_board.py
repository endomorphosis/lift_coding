#!/usr/bin/env python3
"""Fail-closed validator for the sealed VerifiedGuiOptimizer work board.

The configured-board launcher executes this program as ``--check-all`` and
accepts the board only when stdout is one JSON object with ``valid: true``.
This validator deliberately uses only the Python standard library so that
control-plane validation does not import either product code or optional
provider dependencies.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import shlex
import subprocess
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path("config/verified_gui_optimizer_scheduler.json")
SCHEMA = (
    "ipfs_accelerate_py.agent_supervisor."
    "verified_gui_optimizer.scheduler_config@1"
)
BOARD_NAMESPACE = "verified-gui-optimizer-v1"
MERGE_BRANCH = "feature/verified-gui-optimizer"
TASK_PREFIX = "VGO-"
TARGET_SOURCE = "swissknife/web/js/apps/agent-supervisor.js"
RECOVERY_RECEIPT_PATH = Path(
    "implementation_plan/evidence/verified_gui_optimizer/recovery/"
    "provider_effect_task_revision_retry_amendment_20260812.json"
)
RECOVERY_RECEIPT_SHA256 = (
    "sha256:15219fc7346422ec83462131611b21c62780c7bcaab868ce04899fcf22ffb7bb"
)
RECOVERY_SEMANTIC_KEY_PREFIX = (
    "verified-gui-optimizer/provider-effect-retry-revision@1"
)

TASK_IDS = (
    "VGO-000",
    "VGO-001",
    "VGO-002",
    "VGO-003",
    "VGO-009",
    "VGO-010",
    "VGO-011",
    "VGO-012",
    "VGO-016",
    "VGO-020",
    "VGO-021",
    "VGO-023",
    "VGO-027",
    "VGO-030",
    "VGO-031",
    "VGO-032",
    "VGO-034",
    "VGO-040",
    "VGO-041",
    "VGO-043",
    "VGO-045",
    "VGO-050",
    "VGO-051",
    "VGO-053",
    "VGO-054",
    "VGO-060",
    "VGO-061",
    "VGO-062",
    "VGO-068",
    "VGO-070",
    "VGO-071",
    "VGO-072",
    "VGO-075",
    "VGO-080",
    "VGO-081",
    "VGO-083",
    "VGO-086",
    "VGO-090",
    "VGO-091",
    "VGO-093",
    "VGO-096",
    "VGO-099",
)
GOAL_IDS = (
    "VGO-G000",
    "VGO-G010",
    "VGO-G020",
    "VGO-G030",
    "VGO-G040",
    "VGO-G050",
    "VGO-G060",
    "VGO-G070",
    "VGO-G080",
    "VGO-G090",
    "VGO-G100",
    "VGO-G110",
)
EXPECTED_WAVES = (
    ("VGO-000",),
    ("VGO-001", "VGO-009"),
    ("VGO-002",),
    ("VGO-003", "VGO-010", "VGO-011"),
    ("VGO-012", "VGO-016"),
    ("VGO-020", "VGO-021", "VGO-023", "VGO-027"),
    ("VGO-030", "VGO-031", "VGO-032", "VGO-034"),
    ("VGO-040", "VGO-043", "VGO-045"),
    ("VGO-041", "VGO-050", "VGO-051", "VGO-061"),
    ("VGO-054", "VGO-062"),
    ("VGO-053",),
    ("VGO-060", "VGO-070", "VGO-071", "VGO-075"),
    ("VGO-068",),
    ("VGO-072",),
    ("VGO-083", "VGO-086"),
    ("VGO-080",),
    ("VGO-081",),
    ("VGO-090", "VGO-096"),
    ("VGO-091",),
    ("VGO-093",),
    ("VGO-099",),
)

TASK_REQUIRED_FIELDS = (
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
    "resource stage",
    "implementation timeout seconds",
    "predicted files",
    "interfaces",
    "conflict policy",
    "preconditions",
    "effects",
    "evidence subset",
    "acceptance",
)
GOAL_REQUIRED_FIELDS = (
    "status",
    "parent",
    "depends on",
    "fib priority",
    "priority",
    "track",
    "bundle",
    "direct child goals",
    "producing tasks",
    "goal",
    "evidence",
    "outputs",
    "validation",
    "acceptance",
    "conflict policy",
)

CONTROL_PATHS = frozenset(
    {
        "implementation_plan/docs/49-verified-gui-optimizer-plan-2026-08-11.md",
        "implementation_plan/docs/49-verified-gui-optimizer.objectives.md",
        "implementation_plan/docs/49-verified-gui-optimizer.todo.md",
        CONFIG_PATH.as_posix(),
        "scripts/validate_verified_gui_optimizer_board.py",
        "scripts/ops/agent_supervisor/implementation_supervisor_entry.py",
        "scripts/ops/verified_gui_optimizer_vgo001_oracle.py",
        "scripts/ops/verified_gui_optimizer_vgo009_oracle.py",
        "scripts/ops/verified_gui_optimizer_status.py",
        "implementation_plan/evidence/verified_gui_optimizer/provider_route/provider_fallback_policy_authorization_20260812.json",
        "implementation_plan/evidence/verified_gui_optimizer/provider_route/local_profile_lifecycle_root_pin_20260812.json",
        "implementation_plan/evidence/verified_gui_optimizer/provider_route/local_profile_lifecycle_witness_20260812.json",
        "implementation_plan/evidence/verified_gui_optimizer/recovery/provider_capsule_retry_amendment_20260812.json",
        "implementation_plan/evidence/verified_gui_optimizer/recovery/provider_capsule_immutability_retry_amendment_20260812.json",
        RECOVERY_RECEIPT_PATH.as_posix(),
    }
)
ALLOWED_OUTPUT_PREFIXES = (
    "swissknife/",
    "external/ipfs_datasets/",
    "external/ipfs_accelerate/",
    "implementation_plan/evidence/verified_gui_optimizer/",
)
ALLOWED_OUTPUT_FILES = frozenset(
    {
        "scripts/gui-opt",
        "scripts/gui_opt.py",
    }
)
PROHIBITED_DEPENDENCY_PATTERNS = (
    "semantic-index",
    "semantic_index",
    "proof-cache",
    "proof_cache",
    "formal_verification_cache",
    "model-routing",
    "model_routing",
    "model_router",
    "knowledge_graphs/adapters/code_evidence",
)
RECOVERY_TASK_REVISIONS = {
    "VGO-001": {
        "old_key": (
            "task/v1/"
            "02a08eba52aca07cbcedb9f30341517f746b1facc1eb89479a658d6e3949871f"
        ),
        "old_cid": (
            "baguqeeraakqi5ossvsqhzphnxhzqgqkrp52gwh5myhvysr42mwgw4okjq4pq"
        ),
        "new_key": (
            "task/v1/"
            "58ee568b77ceb6982901566ad475d04adb5bb49e60b05101ef7ec0d55cc7e5da"
        ),
        "new_cid": (
            "baguqeeraldxfnc3xz23jqkibkzvni5oqjlnvxne6mcyfcappp3ankxgh4xna"
        ),
        "contract_sha256": (
            "sha256:"
            "71828ac55853cf1fb68f1a0eef164e1a15ebfaecf8b3feac73f5847eaa766411"
        ),
        "contract_size": 14028,
        "display_attempt_count": 5,
        "revision_attempt_count": 5,
        "event_sequence": 742,
        "event_type": "implementation_retry_deferred",
        "event_id": (
            "sha256:"
            "8939c8efce77048fd79fe5b9e8d1d141ae23bea9ac0bfe6b49146435b9a8a2ac"
        ),
    },
    "VGO-009": {
        "old_key": (
            "task/v1/"
            "53d3044c4e2d0ae6b2c41a73b3bfd4bc3b14a6db75f704c9b9602520ba58c805"
        ),
        "old_cid": (
            "baguqeerakpjqitcofufonmwedjz3hp6uxq5rjjw3ox3qjsnzmassbosyzacq"
        ),
        "new_key": (
            "task/v1/"
            "9a7b6853646e476c7442902c016dba48be4294de539f20aaff86bca93a504660"
        ),
        "new_cid": (
            "baguqeeratj5wqu3enzdwy5ccsawac3n2jc7effg6kopsbkx7q26ksosqizqa"
        ),
        "contract_sha256": (
            "sha256:"
            "fabfd426ced4a317ae8b7eb3e10a7ef68deaecf7c68142a8c0289be79d2342e7"
        ),
        "contract_size": 12919,
        "display_attempt_count": 4,
        "revision_attempt_count": 4,
        "event_sequence": 906,
        "event_type": "implementation_finished",
        "event_id": (
            "sha256:"
            "0bfd46d60d78386fcc2acd8d6dcf9744db25d5fb97c50019ea690e9f29f61966"
        ),
    },
}


class DuplicateKeyError(ValueError):
    """Raised when the supposedly sealed JSON repeats a field."""


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_object_without_duplicates,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be an object")
    return value


def _split_csv(value: str) -> list[str]:
    normalized = str(value or "").strip()
    if normalized.lower() in {"", "-", "none", "n/a"}:
        return []
    return [
        item.strip().strip("`'\"")
        for item in normalized.split(",")
        if item.strip().strip("`'\"")
    ]


def _canonical_identity_json_bytes(value: Any) -> bytes:
    """Mirror task-identity DAG-JSON bytes without importing product code."""

    def check(item: Any) -> None:
        if item is None or isinstance(item, (str, bool, int)):
            return
        if isinstance(item, float):
            raise ValueError("task identity cannot contain floats")
        if isinstance(item, list):
            for child in item:
                check(child)
            return
        if isinstance(item, dict) and all(
            isinstance(key, str) for key in item
        ):
            for child in item.values():
                check(child)
            return
        raise ValueError(
            "unsupported task identity value: "
            f"{type(item).__name__}"
        )

    check(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _normalize_identity_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def _normalize_identity_path(value: Any) -> str:
    text = str(value or "").strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return re.sub(r"/+", "/", text).rstrip("/")


def _identity_sequence(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple)):
        return [item for item in value if item not in (None, "")]
    return [value]


def _task_identity_from_record(
    record: Mapping[str, Any],
    *,
    omit_semantic_key: bool,
) -> tuple[str, str]:
    """Recompute the daemon's semantic identity for one sealed board row."""

    metadata_value = record.get("metadata")
    metadata = (
        dict(metadata_value) if isinstance(metadata_value, Mapping) else {}
    )
    if omit_semantic_key:
        metadata.pop("semantic key", None)
    title = _normalize_identity_text(record.get("title", ""))
    outputs = sorted(
        {
            _normalize_identity_path(item)
            for item in _identity_sequence(metadata.get("outputs", ""))
            if _normalize_identity_path(item)
        }
    )
    acceptance = [
        _normalize_identity_text(item)
        for item in _identity_sequence(metadata.get("acceptance", ""))
        if _normalize_identity_text(item)
    ]
    evidence = sorted(
        {
            _normalize_identity_text(item)
            for item in _identity_sequence(
                metadata.get("missing evidence", "")
                or metadata.get("evidence", "")
            )
            if _normalize_identity_text(item)
        }
    )
    evidence_outputs = sorted(
        {
            _normalize_identity_path(item)
            for item in _identity_sequence(
                metadata.get("evidence outputs", "")
            )
            if _normalize_identity_path(item)
        }
    )
    goal = _normalize_identity_text(
        metadata.get("goal id", "")
        or metadata.get("goal packet key", "")
        or metadata.get("goal", "")
    )
    semantic_hint = _normalize_identity_text(
        metadata.get("semantic key", "")
        or metadata.get("bundle key", "")
        or metadata.get("work scope", "")
        or metadata.get("fingerprint", "")
    )
    semantic = {
        key: value
        for key, value in {
            "title": title,
            "outputs": outputs,
            "acceptance": acceptance,
            "evidence": evidence,
            "evidence_outputs": evidence_outputs,
            "goal": goal,
            "semantic_hint": semantic_hint,
        }.items()
        if value
    }
    material = {
        "schema": "ipfs_accelerate_py/agent-supervisor/task-identity@1",
        "semantic": semantic,
    }
    raw = _canonical_identity_json_bytes(material)
    digest = hashlib.sha256(raw).digest()
    fingerprint = digest.hex()
    cid_bytes = b"\x01\xa9\x02\x12\x20" + digest
    cid = (
        "b"
        + base64.b32encode(cid_bytes)
        .decode("ascii")
        .rstrip("=")
        .lower()
    )
    return f"task/v1/{fingerprint}", cid


def _task_contract_bytes(record: Mapping[str, Any], task_id: str) -> bytes:
    metadata_value = record.get("metadata")
    metadata = (
        dict(metadata_value) if isinstance(metadata_value, Mapping) else {}
    )
    metadata.pop("status", None)
    metadata.pop("semantic key", None)
    material = {
        "task_id": task_id,
        "title": str(record.get("title") or ""),
        "metadata": metadata,
    }
    return json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _exact_object(
    value: Any,
    *,
    expected_keys: set[str],
    label: str,
    errors: list[str],
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        errors.append(f"{label} must be an object")
        return {}
    actual = set(value)
    if actual != expected_keys:
        errors.append(
            f"{label} fields must equal {sorted(expected_keys)!r}, got "
            f"{sorted(actual)!r}"
        )
    return value


def _validate_recovery_amendment(
    receipt: Mapping[str, Any],
    receipt_raw: bytes,
    task_records: Mapping[str, Mapping[str, Any]],
    config: Mapping[str, Any],
    errors: list[str],
) -> None:
    """Bind the only authorized fresh revisions to frozen failure evidence."""

    receipt_digest = "sha256:" + hashlib.sha256(receipt_raw).hexdigest()
    if receipt_digest != RECOVERY_RECEIPT_SHA256:
        errors.append(
            "recovery receipt digest mismatch: "
            f"expected {RECOVERY_RECEIPT_SHA256}, got {receipt_digest}"
        )
    top = _exact_object(
        receipt,
        expected_keys={
            "schema",
            "board_namespace",
            "authorized_action",
            "authorization_basis",
            "authorized_at",
            "attempt_ledger_policy",
            "prior_amendment",
            "semantic_revision_policy",
            "pre_repair_source",
            "failed_attempts",
            "repair",
            "route_policy",
            "constraints",
        },
        label="recovery receipt",
        errors=errors,
    )
    exact_top = {
        "schema": (
            "verified-gui-optimizer/"
            "provider-effect-retry-revision-amendment@1"
        ),
        "board_namespace": BOARD_NAMESPACE,
        "authorized_action": (
            "add_receipt_bound_semantic_revision_to_exact_tasks"
        ),
        "authorization_basis": (
            "operator_directed_retry_after_verified_no_model_execution_"
            "control_plane_failures"
        ),
        "authorized_at": "2026-08-12T06:41:42Z",
        "attempt_ledger_policy": "append_only_no_refund",
    }
    for field, expected in exact_top.items():
        if top.get(field) != expected:
            errors.append(f"recovery receipt {field} is not sealed")

    prior = _exact_object(
        top.get("prior_amendment"),
        expected_keys={
            "path",
            "sha256",
            "authorized_action",
            "authorized_max_task_attempts",
        },
        label="recovery receipt prior_amendment",
        errors=errors,
    )
    prior_expected = {
        "path": (
            "implementation_plan/evidence/verified_gui_optimizer/recovery/"
            "provider_capsule_immutability_retry_amendment_20260812.json"
        ),
        "sha256": (
            "sha256:"
            "b1881c4070aff2f326440c04d59158872627f31eafb5c0f8f00b80e33a8e3b96"
        ),
        "authorized_action": "increase_max_task_attempts_from_4_to_5",
        "authorized_max_task_attempts": 5,
    }
    if dict(prior) != prior_expected:
        errors.append("recovery receipt prior_amendment is not sealed")
    prior_path = REPO_ROOT / str(prior.get("path") or "")
    try:
        prior_digest = "sha256:" + hashlib.sha256(prior_path.read_bytes()).hexdigest()
    except OSError as exc:
        errors.append(f"cannot read prior recovery amendment: {exc}")
    else:
        if prior_digest != prior_expected["sha256"]:
            errors.append("prior recovery amendment digest mismatch")

    policy = _exact_object(
        top.get("semantic_revision_policy"),
        expected_keys={
            "metadata_field",
            "value_template",
            "receipt_self_hash_embedded",
            "exact_task_ids",
            "fresh_revision_attempt_origin",
            "historical_task_revision_cids_preserved",
            "old_canonical_cid_attempt_ledgers_preserved",
            "display_attempt_projection_rebinds_to_new_revision",
            "runtime_state_mutation_authorized",
        },
        label="recovery receipt semantic_revision_policy",
        errors=errors,
    )
    expected_policy = {
        "metadata_field": "Semantic key",
        "value_template": (
            f"{RECOVERY_SEMANTIC_KEY_PREFIX}/"
            "{task_id}/receipt-sha256:{receipt_sha256}"
        ),
        "receipt_self_hash_embedded": False,
        "exact_task_ids": ["VGO-001", "VGO-009"],
        "fresh_revision_attempt_origin": 1,
        "historical_task_revision_cids_preserved": True,
        "old_canonical_cid_attempt_ledgers_preserved": True,
        "display_attempt_projection_rebinds_to_new_revision": True,
        "runtime_state_mutation_authorized": False,
    }
    if dict(policy) != expected_policy:
        errors.append("recovery receipt semantic_revision_policy is not sealed")

    pre_repair = _exact_object(
        top.get("pre_repair_source"),
        expected_keys={
            "superproject_head",
            "superproject_tree",
            "accelerator_commit",
            "accelerator_source_tree",
            "accepted_control_plane_capsule_id",
            "accepted_control_plane_archive_sha256",
            "accepted_control_plane_runner_sha256",
        },
        label="recovery receipt pre_repair_source",
        errors=errors,
    )
    expected_pre_repair = {
        "superproject_head": "fd06de85c78fdadb91fdbf92eb935d311e3b6b65",
        "superproject_tree": "32e21e55a05e0e26609d1ab27d10de312e60cf4e",
        "accelerator_commit": "08f5b81d66762bd03816a15d7617c4aa06ea6a4e",
        "accelerator_source_tree": "048626fcd4e2ccdda81ecf8b593d5f4ddca0eec1",
        "accepted_control_plane_capsule_id": (
            "sha256:e26cde672a309b7b9d69a51248ad05d69540458ec85a0d726e1059db7b1f7362"
        ),
        "accepted_control_plane_archive_sha256": (
            "sha256:c4faa75b212a3fa6e3285fedb8aefd31a504733ec4bb0c93f86d0b2a3e055e68"
        ),
        "accepted_control_plane_runner_sha256": (
            "sha256:e71396a5f13e3e21619afa2c850935c49944a20ed2a258aaa58718910eb8350d"
        ),
    }
    if dict(pre_repair) != expected_pre_repair:
        errors.append("recovery receipt pre_repair_source is not sealed")

    repair = _exact_object(
        top.get("repair"),
        expected_keys={
            "accelerator_commit",
            "accelerator_source_tree",
            "commit_patch_sha256",
            "grok_primary_lifecycle_repair",
            "sealed_prompt_rescue_repair",
            "revision_attempt_accounting_repair",
            "terra_route_and_rescue_test_result",
            "scheduler_revision_test_result",
            "daemon_semantic_revision_test_result",
            "independent_audit",
        },
        label="recovery receipt repair",
        errors=errors,
    )
    expected_repair = {
        "accelerator_commit": "53f42b67442d2ecb28508accc5f98a4fc3cc6e46",
        "accelerator_source_tree": "220152bb8a371a75ffeb04d080b332f062840a10",
        "commit_patch_sha256": (
            "sha256:d7b529b2200ca41099f5e1594aaebe5929d073bdb759432f480f6d2d39da62f9"
        ),
        "grok_primary_lifecycle_repair": (
            "docker_create_is_parsed_as_one_exact_container_id_then_docker_"
            "start_attach_interactive_is_the_provider_execution"
        ),
        "sealed_prompt_rescue_repair": (
            "provider_rescue_is_refused_for_prompt_commands_bound_to_"
            "noninheritable_passed_file_descriptors"
        ),
        "revision_attempt_accounting_repair": (
            "display_attempt_counts_are_scoped_to_the_matching_canonical_task_"
            "revision_while_legacy_identityless_counts_remain_conservative"
        ),
        "terra_route_and_rescue_test_result": (
            "79 passed, 1 real-Docker deselected"
        ),
        "scheduler_revision_test_result": "8 passed",
        "daemon_semantic_revision_test_result": "2 passed",
        "independent_audit": "go",
    }
    if dict(repair) != expected_repair:
        errors.append("recovery receipt repair tuple is not sealed")

    route = _exact_object(
        top.get("route_policy"),
        expected_keys={
            "route_id",
            "authorization_id",
            "primary_provider_id",
            "primary_model_id",
            "fallback_provider_id",
            "fallback_implementer_identity",
            "fallback_model_id",
            "fallback_reasoning_effort",
            "fallback_trigger",
        },
        label="recovery receipt route_policy",
        errors=errors,
    )
    expected_route = {
        "route_id": (
            "agent-supervisor-prompt-v3-grok45-terra56-high-auth-or-hard-quota-v1"
        ),
        "authorization_id": (
            "sha256:8a9c90a5837e88f8248566e65568410aba460549676490ab914a6e51e7d4d868"
        ),
        "primary_provider_id": "grok_cli",
        "primary_model_id": "grok-4.5",
        "fallback_provider_id": "codex",
        "fallback_implementer_identity": "codex",
        "fallback_model_id": "gpt-5.6-terra",
        "fallback_reasoning_effort": "high",
        "fallback_trigger": "primary_quota_or_auth_unavailable",
    }
    if dict(route) != expected_route:
        errors.append("recovery receipt route_policy is not sealed")

    constraints = _exact_object(
        top.get("constraints"),
        expected_keys={
            "max_task_attempts",
            "implementation_max_repair_rounds",
            "implementation_retry_budget",
            "validation_retry_budget",
            "merge_retry_budget",
            "historical_attempt_events_preserved",
            "manual_attempt_counter_mutation_forbidden",
            "runtime_state_or_counter_edit_forbidden",
            "generic_provider_fallback_remains_forbidden",
            "fallback_route",
        },
        label="recovery receipt constraints",
        errors=errors,
    )
    expected_constraints = {
        "max_task_attempts": 5,
        "implementation_max_repair_rounds": 3,
        "implementation_retry_budget": 3,
        "validation_retry_budget": 3,
        "merge_retry_budget": 3,
        "historical_attempt_events_preserved": True,
        "manual_attempt_counter_mutation_forbidden": True,
        "runtime_state_or_counter_edit_forbidden": True,
        "generic_provider_fallback_remains_forbidden": True,
        "fallback_route": (
            "grok-4.5_to_gpt-5.6-terra_high_only_on_auth_unavailable_or_"
            "verified_hard_quota"
        ),
    }
    if dict(constraints) != expected_constraints:
        errors.append("recovery receipt constraints are not sealed")
    for field in (
        "max_task_attempts",
        "implementation_retry_budget",
        "validation_retry_budget",
        "merge_retry_budget",
    ):
        if config.get(field) != expected_constraints[field]:
            errors.append(f"config.{field} conflicts with recovery receipt")

    attempts_value = top.get("failed_attempts")
    attempts = attempts_value if isinstance(attempts_value, list) else []
    if not isinstance(attempts_value, list):
        errors.append("recovery receipt failed_attempts must be a list")
    attempt_ids = [
        str(item.get("task_id") or "")
        for item in attempts
        if isinstance(item, Mapping)
    ]
    if attempt_ids != ["VGO-001", "VGO-009"] or len(attempts) != 2:
        errors.append("recovery receipt failed_attempts must be exact ordered tasks")
    attempts_by_id = {
        str(item.get("task_id") or ""): item
        for item in attempts
        if isinstance(item, Mapping)
    }
    attempt_keys = {
        "VGO-001": {
            "task_id", "canonical_task_key", "task_revision_cid",
            "task_contract_sha256_without_status_or_semantic_key",
            "task_contract_canonical_json_size_bytes", "display_attempt_count",
            "revision_attempt_count", "event_sequence", "event_type", "event_id",
            "previous_event_id", "event_snapshot_id", "event_stream_id",
            "finished_at", "reason", "attempt", "max_task_attempts",
            "implementation_max_repair_rounds", "backoff_seconds",
            "provider_dispatched", "attempt_consumed", "active_task_cleared",
            "display_counter_pinned", "attempt_5_protected_latch_observed",
            "attempt_5_provider_effect_observed",
            "attempt_5_provider_attempt_cas_change_observed",
        },
        "VGO-009": {
            "task_id", "canonical_task_key", "task_revision_cid",
            "task_contract_sha256_without_status_or_semantic_key",
            "task_contract_canonical_json_size_bytes", "display_attempt_count",
            "revision_attempt_count", "event_sequence", "event_type", "event_id",
            "previous_event_id", "event_snapshot_id", "event_stream_id",
            "finished_at", "attempt", "returncode", "provider_dispatched",
            "attempt_consumed", "baseline_commit", "branch", "workspace_path",
            "workspace_relative_path", "diagnostic_receipt_cid",
            "implementation_log_relative_path", "implementation_log_sha256",
            "implementation_log_mode", "implementation_log_size_bytes",
            "implementation_log_line_count", "docker_create_stdout",
            "docker_container_started", "docker_container_survived_cleanup",
            "primary_model_execution_observed", "fallback_model_execution_observed",
            "failure", "invocation_id", "logical_attempt_id", "worktree_id",
            "prompt_cid", "scope_cid", "provider_attempt_store",
        },
    }
    for task_id, expected in RECOVERY_TASK_REVISIONS.items():
        attempt = _exact_object(
            attempts_by_id.get(task_id),
            expected_keys=attempt_keys[task_id],
            label=f"recovery receipt failed_attempts[{task_id}]",
            errors=errors,
        )
        exact_attempt_fields = {
            "task_id": task_id,
            "canonical_task_key": expected["old_key"],
            "task_revision_cid": expected["old_cid"],
            "task_contract_sha256_without_status_or_semantic_key": (
                expected["contract_sha256"]
            ),
            "task_contract_canonical_json_size_bytes": expected["contract_size"],
            "display_attempt_count": expected["display_attempt_count"],
            "revision_attempt_count": expected["revision_attempt_count"],
            "event_sequence": expected["event_sequence"],
            "event_type": expected["event_type"],
            "event_id": expected["event_id"],
        }
        for field, value in exact_attempt_fields.items():
            if attempt.get(field) != value:
                errors.append(f"recovery receipt {task_id}.{field} is not sealed")

    vgo001 = attempts_by_id.get("VGO-001", {})
    expected_vgo001 = {
        "previous_event_id": (
            "sha256:e12b79a1af0420f882d5cfa1612c8d790d8735b6b4e566c6bc13d2025a1f7db0"
        ),
        "event_snapshot_id": (
            "event-log-snapshot:sha256:9b60460f15ed6afa9366e79e7b827a87d61005e11bf5b1b3c6259a7ee434e7e8"
        ),
        "event_stream_id": (
            "event-log:sha256:9b60460f15ed6afa9366e79e7b827a87d61005e11bf5b1b3c6259a7ee434e7e8"
        ),
        "finished_at": "2026-08-12T05:54:04.389270+00:00",
        "reason": "implementation_repair_round_budget_exhausted",
        "attempt": 5,
        "max_task_attempts": 5,
        "implementation_max_repair_rounds": 3,
        "backoff_seconds": 7200,
        "provider_dispatched": False,
        "attempt_consumed": False,
        "active_task_cleared": True,
        "display_counter_pinned": True,
        "attempt_5_protected_latch_observed": False,
        "attempt_5_provider_effect_observed": False,
        "attempt_5_provider_attempt_cas_change_observed": False,
    }
    for field, value in expected_vgo001.items():
        if vgo001.get(field) != value:
            errors.append(f"recovery receipt VGO-001.{field} is not sealed")

    vgo009 = attempts_by_id.get("VGO-009", {})
    expected_vgo009 = {
        "previous_event_id": (
            "sha256:89eaa06dfc1eb5e0448a2970458db0f1aae297b23768cbc51636e618b73ed83c"
        ),
        "event_snapshot_id": (
            "event-log-snapshot:sha256:a586191c627238a2978ec7f8674a950c833e70be303420b03c0dc0cca6b394ec"
        ),
        "event_stream_id": (
            "event-log:sha256:a586191c627238a2978ec7f8674a950c833e70be303420b03c0dc0cca6b394ec"
        ),
        "finished_at": "2026-08-12T05:54:55.941218+00:00",
        "attempt": 4,
        "returncode": 78,
        "provider_dispatched": True,
        "attempt_consumed": True,
        "baseline_commit": "fd06de85c78fdadb91fdbf92eb935d311e3b6b65",
        "branch": "implementation/vgo-009-53d3044c4e2d-attempt-4-1786514045",
        "workspace_path": (
            "/home/barberb/lift_coding/.worktrees/verified-gui-optimizer-control/"
            "data/agent_supervisor/verified_gui_optimizer/worktrees/"
            "workspace-75a13f8fed7b-68c891b9dc70"
        ),
        "workspace_relative_path": (
            "data/agent_supervisor/verified_gui_optimizer/worktrees/"
            "workspace-75a13f8fed7b-68c891b9dc70"
        ),
        "diagnostic_receipt_cid": (
            "baguqeerac6mvzkwph3dmbqtgu5blb4ys4xndnn3ru4f2na4pvn2klzij2t5a"
        ),
        "implementation_log_relative_path": (
            "data/agent_supervisor/verified_gui_optimizer/state/lane-3/"
            "implementation_logs/vgo-009-attempt-4.log"
        ),
        "implementation_log_sha256": (
            "sha256:dc446aa621e4f4d70ad3a160503ec90e7dad2fd6b235928e5489db49cff18656"
        ),
        "implementation_log_mode": "0600",
        "implementation_log_size_bytes": 7519,
        "implementation_log_line_count": 15,
        "docker_create_stdout": (
            "bfa8ff852c1f9c52c6c067bd1d8d2d1af6ccee19ba595f06d4e72e4d814c5d43"
        ),
        "docker_container_started": False,
        "docker_container_survived_cleanup": False,
        "primary_model_execution_observed": False,
        "fallback_model_execution_observed": False,
        "failure": (
            "docker_create_container_id_stdout_was_mistaken_for_attached_"
            "primary_provider_success"
        ),
        "invocation_id": (
            "baguqeerawcszsylibexr6j3wvvbejot5lx25kskvrxvtobhvqaexzpijn67a"
        ),
        "logical_attempt_id": (
            "baguqeerainkc65733xab44sastdwqt5z5rouif3zggu2dqriikrtcptskxyq"
        ),
        "worktree_id": (
            "baguqeera6jmdcsvt5r5xdqrzrkjrywtrjdcb5ky5mgpaekalro6gmg6psyoq"
        ),
        "prompt_cid": (
            "sha256:a940f2b56ba7098019c335aa3a9da879177da16670560fb38d51fccc820ef54c"
        ),
        "scope_cid": (
            "baguqeeragz5dmvcmmv376kqk2cwmzqnqa5zd3vdqjq6qdi6vwo7focjovbnq"
        ),
    }
    for field, value in expected_vgo009.items():
        if vgo009.get(field) != value:
            errors.append(f"recovery receipt VGO-009.{field} is not sealed")
    store = _exact_object(
        vgo009.get("provider_attempt_store"),
        expected_keys={
            "path", "identity", "directory_mode", "last_metadata_change_at",
            "entry_count", "json_count", "lock_count", "provider_effect_count",
            "provider_route_outcome_count", "sole_entry",
        },
        label="recovery receipt VGO-009.provider_attempt_store",
        errors=errors,
    )
    expected_store = {
        "path": (
            "/home/barberb/.local/state/ipfs_accelerate_py/provider-attempts/"
            "ddb61fab93e4775fc4af8a7dff7deeb845e2a03a4925cca66d69bd8006120676"
        ),
        "identity": (
            "sha256:6ff0cc35d4facbbf7c003569e6baa73e4aa0ef7fc73bfad5104e0bcd20ac4ab9"
        ),
        "directory_mode": "0700",
        "last_metadata_change_at": "2026-08-12T05:54:30.284968753+00:00",
        "entry_count": 1,
        "json_count": 0,
        "lock_count": 1,
        "provider_effect_count": 0,
        "provider_route_outcome_count": 0,
        "sole_entry": {
            "name": (
                "7cd6cbfbb2680ed950e2846f6209a243b9dded9efba495106c0b396fb54e48ff.lock"
            ),
            "mode": "0600",
            "size_bytes": 0,
        },
    }
    if dict(store) != expected_store:
        errors.append("recovery receipt VGO-009 provider attempt store is not sealed")

    expected_semantic_keys = {
        task_id: (
            f"{RECOVERY_SEMANTIC_KEY_PREFIX}/{task_id}/"
            f"receipt-sha256:{RECOVERY_RECEIPT_SHA256.removeprefix('sha256:')}"
        )
        for task_id in RECOVERY_TASK_REVISIONS
    }
    for task_id, record in task_records.items():
        metadata = record.get("metadata", {})
        semantic_key = (
            metadata.get("semantic key", "")
            if isinstance(metadata, Mapping)
            else ""
        )
        expected_semantic_key = expected_semantic_keys.get(task_id, "")
        if semantic_key != expected_semantic_key:
            if task_id in expected_semantic_keys:
                errors.append(f"{task_id}: recovery Semantic key is not sealed")
            elif semantic_key:
                errors.append(f"{task_id}: unauthorized Semantic key")
    for task_id, expected in RECOVERY_TASK_REVISIONS.items():
        record = task_records.get(task_id)
        if not isinstance(record, Mapping):
            continue
        contract_raw = _task_contract_bytes(record, task_id)
        contract_digest = "sha256:" + hashlib.sha256(contract_raw).hexdigest()
        if contract_digest != expected["contract_sha256"]:
            errors.append(f"{task_id}: task contract changed beyond Semantic key")
        if len(contract_raw) != expected["contract_size"]:
            errors.append(f"{task_id}: task contract canonical byte size changed")
        try:
            old_key, old_cid = _task_identity_from_record(
                record, omit_semantic_key=True
            )
            new_key, new_cid = _task_identity_from_record(
                record, omit_semantic_key=False
            )
        except ValueError as exc:
            errors.append(f"{task_id}: cannot recompute task identity: {exc}")
            continue
        if (old_key, old_cid) != (expected["old_key"], expected["old_cid"]):
            errors.append(f"{task_id}: prior canonical identity is not preserved")
        if (new_key, new_cid) != (expected["new_key"], expected["new_cid"]):
            errors.append(f"{task_id}: receipt-bound canonical identity is not sealed")
        if (new_key, new_cid) == (old_key, old_cid):
            errors.append(f"{task_id}: recovery must create a fresh task revision")


def _parse_markdown_records(
    path: Path,
    heading_pattern: re.Pattern[str],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    records: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    current_id = ""
    current_title = ""
    current_line = 0
    current_metadata: dict[str, str] = {}

    def flush() -> None:
        nonlocal current_id, current_title, current_line, current_metadata
        if not current_id:
            return
        if current_id in records:
            errors.append(f"{path}: duplicate heading {current_id}")
        else:
            records[current_id] = {
                "title": current_title,
                "line": current_line,
                "metadata": dict(current_metadata),
            }
        current_id = ""
        current_title = ""
        current_line = 0
        current_metadata = {}

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if line.startswith("## "):
            flush()
            match = heading_pattern.fullmatch(line)
            if match is not None:
                current_id = match.group("id")
                current_title = match.group("title").strip()
                current_line = line_number
            elif line.startswith("## VGO-"):
                errors.append(f"{path}:{line_number}: malformed VGO heading")
            continue
        if not current_id:
            continue
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, value = stripped[2:].split(":", 1)
        normalized_key = key.strip().lower()
        if normalized_key in current_metadata:
            errors.append(
                f"{path}:{line_number}: {current_id} repeats metadata "
                f"field {normalized_key!r}"
            )
        current_metadata[normalized_key] = value.strip()
    flush()
    return records, errors


def _safe_relative_path(value: str) -> bool:
    if not value or "\x00" in value or "\\" in value or "://" in value:
        return False
    if any(character in value for character in "*?[]{}"):
        return False
    path = PurePosixPath(value)
    return bool(
        not path.is_absolute()
        and value not in {".", ".."}
        and ".." not in path.parts
        and not (path.parts and path.parts[0].endswith(":"))
    )


def _allowed_output_path(value: str) -> bool:
    return _safe_relative_path(value) and (
        value in ALLOWED_OUTPUT_FILES
        or any(value.startswith(prefix) for prefix in ALLOWED_OUTPUT_PREFIXES)
    )


def _task_shard(task_id: str, lane_count: int = 4) -> int:
    """Match ImplementationDaemon._task_belongs_to_shard exactly."""

    digest = hashlib.sha256(task_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % lane_count


def _cycle_nodes(graph: Mapping[str, Iterable[str]]) -> set[str]:
    visiting: set[str] = set()
    visited: set[str] = set()
    cyclic: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            cyclic.add(node)
            return
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph.get(node, ()):
            if dependency in graph:
                visit(dependency)
                if dependency in cyclic:
                    cyclic.add(node)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)
    return cyclic


def _command_version(command: str) -> str:
    try:
        result = subprocess.run(
            [command, "--version"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _validate_config(config: Mapping[str, Any], errors: list[str]) -> None:
    exact_scalars = {
        "schema": SCHEMA,
        "taskboard_path": (
            "implementation_plan/docs/49-verified-gui-optimizer.todo.md"
        ),
        "objectives_path": (
            "implementation_plan/docs/49-verified-gui-optimizer.objectives.md"
        ),
        "plan_path": (
            "implementation_plan/docs/49-verified-gui-optimizer-plan-2026-08-11.md"
        ),
        "validator_path": "scripts/validate_verified_gui_optimizer_board.py",
        "task_prefix": TASK_PREFIX,
        "board_namespace": BOARD_NAMESPACE,
        "merge_target_branch": MERGE_BRANCH,
        "max_lanes": 4,
        "strict_task_sharding": True,
        "exit_when_all_tracks_terminal": True,
        "objective_refill_enabled": False,
        "codebase_refill_enabled": False,
        "retry_budget_guardrail_enabled": False,
        "dependency_guardrail_enabled": False,
        "reconciliation_guardrail_enabled": False,
        "poll_interval_seconds": 5,
        "daemon_interval_seconds": 30,
        "check_interval_seconds": 20,
        "stale_seconds": 900,
        "watchdog_startup_grace_seconds": 300,
        "max_restarts": 3,
        "max_task_attempts": 5,
        "implementation_retry_budget": 3,
        "validation_retry_budget": 3,
        "merge_retry_budget": 3,
        "implementation_timeout_seconds": 7200,
        "implementation_max_timeout_seconds": 14400,
        "implementation_log_stall_seconds": 600,
    }
    for field, expected in exact_scalars.items():
        if config.get(field) != expected:
            errors.append(
                f"config.{field} must equal {expected!r}, got "
                f"{config.get(field)!r}"
            )

    source = config.get("source_binding")
    expected_source = {
        "accelerator_required_ancestor": (
            "ce448eae6ab5706832d3ae88b041f9d38ac82ae8"
        ),
        "accelerator_required_branch": MERGE_BRANCH,
        "ipfs_accelerate_submodule_path": "external/ipfs_accelerate",
        "ipfs_accelerate_planning_revision": (
            "4784c932f87aafbd949714c05439836ab0f446a7"
        ),
        "ipfs_datasets_submodule_path": "external/ipfs_datasets",
        "ipfs_datasets_planning_revision": (
            "a2f5400b7cb89c8481819379a1b7b9959fe81d45"
        ),
        "swissknife_submodule_path": "swissknife",
        "swissknife_planning_revision": (
            "26f06277888b09a3e7c9b4a3b844001f1dbc0841"
        ),
    }
    if not isinstance(source, Mapping):
        errors.append("config.source_binding must be an object")
        source = {}
    for field, expected in expected_source.items():
        if source.get(field) != expected:
            errors.append(f"config.source_binding.{field} is not sealed")
    for field in (
        "require_initialized_gitlinks",
        "require_superproject_gitlink_equals_nested_head",
        "require_clean_nested_worktree_at_task_start",
        "record_recursive_repository_forest_at_launch",
        "changed_revision_requires_fresh_inventory_and_baseline",
    ):
        if source.get(field) is not True:
            errors.append(f"config.source_binding.{field} must be true")
    if source.get("planning_revision_is_runtime_completion_evidence") is not False:
        errors.append(
            "config.source_binding.planning_revision_is_runtime_completion_evidence "
            "must be false"
        )

    expected_submodules = [
        "external/ipfs_accelerate",
        "external/ipfs_datasets",
        "swissknife",
    ]
    if config.get("worktree_submodule_paths") != expected_submodules:
        errors.append("config.worktree_submodule_paths is not the sealed list")

    protected = config.get("protected_paths")
    if not isinstance(protected, list):
        errors.append("config.protected_paths must be a list")
    else:
        if len(protected) != len(set(protected)):
            errors.append("config.protected_paths contains duplicates")
        missing = sorted(CONTROL_PATHS - set(protected))
        if missing:
            errors.append(f"config.protected_paths omits {missing}")
        for value in protected:
            if not isinstance(value, str) or not _safe_relative_path(value):
                errors.append(f"unsafe protected path: {value!r}")

    runtime = config.get("runtime_paths")
    expected_runtime = {
        "root": "data/agent_supervisor/verified_gui_optimizer",
        "state": "data/agent_supervisor/verified_gui_optimizer/state",
        "worktrees": "data/agent_supervisor/verified_gui_optimizer/worktrees",
        "merge_queue": (
            "data/agent_supervisor/verified_gui_optimizer/merge-queue"
        ),
        "logs": "data/agent_supervisor/verified_gui_optimizer/logs",
    }
    if not isinstance(runtime, Mapping):
        errors.append("config.runtime_paths must be an object")
        runtime = {}
    for field, expected in expected_runtime.items():
        value = runtime.get(field)
        if value != expected:
            errors.append(f"config.runtime_paths.{field} is not sealed")
        if isinstance(value, str) and field != "root":
            root_parts = PurePosixPath(expected_runtime["root"]).parts
            if PurePosixPath(value).parts[: len(root_parts)] != root_parts:
                errors.append(f"config.runtime_paths.{field} escapes runtime root")
    if runtime.get("generated_runtime_artifacts_are_completion_authority") is not False:
        errors.append("generated runtime artifacts cannot be completion authority")

    lanes = config.get("lanes")
    if not isinstance(lanes, list) or len(lanes) != 4:
        errors.append("config.lanes must contain four entries")
    else:
        for index, lane in enumerate(lanes):
            if not isinstance(lane, Mapping):
                errors.append(f"config.lanes[{index}] must be an object")
                continue
            expected = {
                "index": index,
                "name": f"vgo-lane-{index}",
                "strict_shard_remainder": index,
            }
            for field, value in expected.items():
                if lane.get(field) != value:
                    errors.append(f"config.lanes[{index}].{field} is invalid")
            for task_id in lane.get("initial_task_ids", []):
                if task_id not in TASK_IDS or _task_shard(task_id) != index:
                    errors.append(
                        f"config.lanes[{index}] has a cross-shard initial task "
                        f"{task_id!r}"
                    )

    provider = config.get("provider")
    expected_provider = {
        "primary_provider_id": "grok_cli",
        "primary_model_id": "grok-4.5",
        "fallback_provider_id": "codex",
        "fallback_model_id": "gpt-5.6-terra",
        "fallback_trigger": "primary_quota_or_auth_unavailable",
        "fallback_reasoning_effort": "high",
        "route_authorization_path": (
            "implementation_plan/evidence/verified_gui_optimizer/"
            "provider_route/"
            "provider_fallback_policy_authorization_20260812.json"
        ),
        "max_concurrency": 4,
        "secrets_from_environment_only": True,
        "secrets_in_argv_prompts_logs_or_receipts": False,
    }
    if not isinstance(provider, Mapping):
        errors.append("config.provider must be an object")
        provider = {}
    for field, expected in expected_provider.items():
        if provider.get(field) != expected:
            errors.append(f"config.provider.{field} violates ordered policy")
    if "provider_id" in provider or "model_id" in provider:
        errors.append("ordered provider policy cannot mix legacy provider fields")

    dependency_policy = config.get("dependency_policy")
    if not isinstance(dependency_policy, Mapping):
        errors.append("config.dependency_policy must be an object")
    else:
        if dependency_policy.get("standalone_subsystem") is not True:
            errors.append("VerifiedGuiOptimizer must remain standalone")
        for field in (
            "semantic_index_dependency_allowed",
            "prior_semantic_capsule_dependency_allowed",
            "proof_cache_dependency_allowed",
            "model_routing_dependency_allowed",
        ):
            if dependency_policy.get(field) is not False:
                errors.append(f"config.dependency_policy.{field} must be false")

    toolchain = config.get("toolchain_policy")
    expected_toolchain = {
        "node_version": "v22.19.0",
        "npm_version": "10.8.2",
        "bin_path": (
            "data/agent_supervisor/verified_gui_optimizer/"
            "toolchain/node_modules/.bin"
        ),
        "swissknife_dependency_source": "swissknife/node_modules",
        "install_from_committed_lock_only": True,
    }
    if not isinstance(toolchain, Mapping):
        errors.append("config.toolchain_policy must be an object")
        toolchain = {}
    for field, expected in expected_toolchain.items():
        if toolchain.get(field) != expected:
            errors.append(f"config.toolchain_policy.{field} is not sealed")
    node_version = _command_version("node")
    npm_version = _command_version("npm")
    if node_version != expected_toolchain["node_version"]:
        errors.append(
            "active Node toolchain must be v22.19.0; prepend the sealed "
            "runtime toolchain bin to PATH"
        )
    if npm_version != expected_toolchain["npm_version"]:
        errors.append(
            "active npm toolchain must be 10.8.2; prepend the sealed "
            "runtime toolchain bin to PATH"
        )
    for relative in (
        "swissknife/node_modules/.bin/vitest",
        "swissknife/node_modules/.bin/playwright",
        "swissknife/node_modules/@ucans/ucans",
    ):
        if not (REPO_ROOT / relative).exists():
            errors.append(
                f"missing lock-provisioned shared SwissKnife dependency {relative}"
            )

    scope = config.get("scope_policy")
    if not isinstance(scope, Mapping):
        errors.append("config.scope_policy must be an object")
    else:
        if scope.get("selected_source") != TARGET_SOURCE:
            errors.append("config scope must bind the selected Agent Supervisor source")
        if scope.get("optimize_all_applications") is not False:
            errors.append("config scope cannot authorize all-application optimization")
        if scope.get("arbitrary_repository_code_execution_during_scan") is not False:
            errors.append("static scanning cannot execute arbitrary repository code")
        if scope.get("production_credentials_or_services_in_tests") is not False:
            errors.append("tests cannot use production credentials or services")

    initial = config.get("initial_projection")
    expected_initial = {
        "task_count": 42,
        "completed_task_ids": ["VGO-000"],
        "ready_task_ids": ["VGO-001", "VGO-002", "VGO-009"],
        "blocked_task_ids": [],
        "terminal_task_id": "VGO-099",
        "goal_count": 12,
        "root_goal_id": "VGO-G000",
    }
    if not isinstance(initial, Mapping):
        errors.append("config.initial_projection must be an object")
    else:
        for field, expected in expected_initial.items():
            if initial.get(field) != expected:
                errors.append(f"config.initial_projection.{field} is not sealed")

    raw_waves = config.get("waves")
    if not isinstance(raw_waves, list) or len(raw_waves) != len(EXPECTED_WAVES):
        errors.append("config.waves must contain the twenty-one sealed waves")
    else:
        seen: list[str] = []
        for index, (row, expected_ids) in enumerate(zip(raw_waves, EXPECTED_WAVES)):
            if not isinstance(row, Mapping):
                errors.append(f"config.waves[{index}] must be an object")
                continue
            if row.get("index") != index:
                errors.append(f"config.waves[{index}].index is invalid")
            task_ids = row.get("task_ids")
            if task_ids != list(expected_ids):
                errors.append(f"config.waves[{index}].task_ids is not sealed")
            if isinstance(task_ids, list):
                seen.extend(task_ids)
        if len(seen) != len(TASK_IDS) or set(seen) != set(TASK_IDS):
            errors.append("config waves do not cover every task exactly once")


def _validate_tasks(
    records: Mapping[str, Mapping[str, Any]],
    config: Mapping[str, Any],
    errors: list[str],
) -> None:
    if tuple(records) != TASK_IDS:
        errors.append(
            "task headings must be the exact ordered 42-ID sealed projection"
        )
    wave_by_task = {
        task_id: wave_index
        for wave_index, wave in enumerate(EXPECTED_WAVES)
        for task_id in wave
    }
    dependencies: dict[str, list[str]] = {}
    statuses: dict[str, str] = {}
    tasks_by_goal: dict[str, list[str]] = {goal_id: [] for goal_id in GOAL_IDS}
    predicted_owner_by_wave: dict[tuple[int, str], str] = {}
    for task_id, record in records.items():
        metadata = record["metadata"]
        title = str(record.get("title") or "").strip()
        if not title:
            errors.append(f"{task_id}: title must be nonempty")
        for field in TASK_REQUIRED_FIELDS:
            if field not in metadata:
                errors.append(f"{task_id}: missing metadata field {field!r}")
            elif field not in {"depends on"} and not metadata[field].strip():
                errors.append(f"{task_id}: metadata field {field!r} is empty")
        status = metadata.get("status", "").lower()
        statuses[task_id] = status
        expected_completion = "auto"
        expected_review_only = "false"
        if task_id == "VGO-000" and status != "completed":
            errors.append("VGO-000: status must remain completed")
        elif task_id != "VGO-000" and status not in {"pending", "completed"}:
            errors.append(
                f"{task_id}: status must be pending or completed, got {status!r}"
            )
        if metadata.get("completion", "").lower() != expected_completion:
            errors.append(f"{task_id}: completion must be {expected_completion}")
        no_change_completion = metadata.get(
            "no-change completion", "forbidden"
        ).strip().lower()
        if no_change_completion != "forbidden":
            errors.append(
                f"{task_id}: no-change completion must be forbidden on the "
                "sealed implementation board"
            )
        if metadata.get("is schedulable", "").lower() != "true":
            errors.append(f"{task_id}: Is schedulable must be true")
        if metadata.get("review only", "").lower() != expected_review_only:
            errors.append(
                f"{task_id}: Review only must be {expected_review_only}"
            )
        if metadata.get("board namespace") != BOARD_NAMESPACE:
            errors.append(f"{task_id}: board namespace mismatch")
        goal_id = metadata.get("goal id", "")
        if goal_id not in GOAL_IDS:
            errors.append(f"{task_id}: unknown Goal id {goal_id!r}")
        else:
            tasks_by_goal[goal_id].append(task_id)

        try:
            timeout = int(metadata.get("implementation timeout seconds", ""))
        except ValueError:
            timeout = 0
        max_timeout = int(config.get("implementation_max_timeout_seconds") or 0)
        if timeout < 1 or timeout > max_timeout:
            errors.append(
                f"{task_id}: Implementation timeout seconds must be in "
                f"[1, {max_timeout}]"
            )

        task_dependencies = _split_csv(metadata.get("depends on", ""))
        dependencies[task_id] = task_dependencies
        if task_id == "VGO-000" and task_dependencies:
            errors.append("VGO-000 must be the only dependency-free root task")
        if task_id != "VGO-000" and not task_dependencies:
            errors.append(f"{task_id}: non-root task must declare a dependency")
        for dependency in task_dependencies:
            if dependency not in TASK_IDS:
                errors.append(f"{task_id}: unknown dependency {dependency!r}")
                continue
            if dependency == task_id:
                errors.append(f"{task_id}: cannot depend on itself")
                continue
            if wave_by_task.get(dependency, 999) >= wave_by_task.get(task_id, -1):
                errors.append(
                    f"{task_id}: dependency {dependency} is not in an earlier wave"
                )

        outputs = _split_csv(metadata.get("outputs", ""))
        predicted = _split_csv(metadata.get("predicted files", ""))
        if not outputs:
            errors.append(f"{task_id}: Outputs must declare at least one path")
        if not predicted:
            errors.append(f"{task_id}: Predicted files must declare at least one path")
        for field_name, paths in (("Outputs", outputs), ("Predicted files", predicted)):
            if len(paths) != len(set(paths)):
                errors.append(f"{task_id}: {field_name} contains duplicate paths")
            for path in paths:
                control_seal_path = task_id == "VGO-000" and path in CONTROL_PATHS
                if not _allowed_output_path(path) and not control_seal_path:
                    errors.append(
                        f"{task_id}: {field_name} path is outside narrow roots: {path!r}"
                    )
                if path in CONTROL_PATHS and task_id != "VGO-000":
                    errors.append(
                        f"{task_id}: task cannot overwrite protected control path {path!r}"
                    )
        if not set(outputs).issubset(set(predicted)):
            errors.append(f"{task_id}: every Output must also be a Predicted file")
        for path in predicted:
            owner_key = (wave_by_task.get(task_id, -1), path)
            prior_owner = predicted_owner_by_wave.get(owner_key)
            if prior_owner is not None and prior_owner != task_id:
                errors.append(
                    f"{task_id}: Predicted file {path!r} is also owned by "
                    f"same-wave task {prior_owner}"
                )
            else:
                predicted_owner_by_wave[owner_key] = task_id

        dependency_fields = [
            metadata.get("outputs", ""),
            metadata.get("predicted files", ""),
            metadata.get("interfaces", ""),
            metadata.get("implementation dependencies", ""),
            metadata.get("reuse modules", ""),
        ]
        dependency_material = "\n".join(dependency_fields).lower()
        for pattern in PROHIBITED_DEPENDENCY_PATTERNS:
            if pattern in dependency_material:
                errors.append(
                    f"{task_id}: prohibited prior-module dependency {pattern!r}"
                )

        declared_lane = metadata.get("parallel lane", "")
        match = re.fullmatch(r"vgo-lane-([0-3])", declared_lane)
        if match is None:
            errors.append(
                f"{task_id}: Parallel lane must be one of vgo-lane-0..3"
            )
        elif int(match.group(1)) != _task_shard(task_id):
            errors.append(
                f"{task_id}: declared Parallel lane conflicts with stable hash shard"
            )

    cyclic = sorted(_cycle_nodes(dependencies))
    if cyclic:
        errors.append(f"task dependency graph is cyclic at {cyclic}")
    roots = sorted(task_id for task_id, deps in dependencies.items() if not deps)
    if roots != ["VGO-000"]:
        errors.append(f"task dependency roots must equal ['VGO-000'], got {roots}")
    if records and TARGET_SOURCE not in (
        REPO_ROOT
        / str(config.get("taskboard_path") or "")
    ).read_text(encoding="utf-8"):
        errors.append("taskboard must explicitly bind the selected Agent Supervisor source")

    # The implementation daemon commits status transitions into the sealed
    # taskboard.  A relaunch must admit that durable progress, while rejecting
    # forged completion that precedes any declared dependency.
    for task_id, status in statuses.items():
        if status != "completed":
            continue
        incomplete_dependencies = sorted(
            dependency
            for dependency in dependencies.get(task_id, [])
            if statuses.get(dependency) != "completed"
        )
        if incomplete_dependencies:
            errors.append(
                f"{task_id}: completed status is not dependency-closed; "
                f"pending dependencies {incomplete_dependencies}"
            )
    initial = config.get("initial_projection")
    initial_completed = (
        initial.get("completed_task_ids", [])
        if isinstance(initial, Mapping)
        else []
    )
    for task_id in initial_completed:
        if statuses.get(str(task_id)) != "completed":
            errors.append(
                f"config initial completed task {task_id!r} is not completed "
                "in the durable taskboard"
            )


def _validate_goals(
    records: Mapping[str, Mapping[str, Any]],
    task_records: Mapping[str, Mapping[str, Any]],
    errors: list[str],
) -> None:
    if tuple(records) != GOAL_IDS:
        errors.append("goal headings must be the exact ordered 12-ID goal heap")
    graph: dict[str, list[str]] = {}
    parents: dict[str, str] = {}
    direct_children: dict[str, list[str]] = {}
    producing_by_goal: dict[str, list[str]] = {}
    producing_mentions: set[str] = set()
    all_task_outputs = {
        path
        for task_record in task_records.values()
        for path in _split_csv(task_record["metadata"].get("outputs", ""))
    }

    def output_is_declared(output: str, declarations: Iterable[str]) -> bool:
        """Match exact files and directory prefixes explicitly ending in `/`."""

        for declaration in declarations:
            if output == declaration:
                return True
            if declaration.endswith("/") and output.startswith(declaration):
                return True
            if output.endswith("/") and declaration.startswith(output):
                return True
        return False

    def normalize_validation_path(
        cwd: PurePosixPath,
        raw: str,
    ) -> tuple[str, str | None]:
        if not raw or "\x00" in raw or "\\" in raw or "://" in raw:
            return "", "invalid validation path token"
        candidate = PurePosixPath(raw)
        if candidate.is_absolute():
            return "", "validation path must be repository-relative"
        parts = list(cwd.parts if str(cwd) != "." else ())
        for part in candidate.parts:
            if part in {"", "."}:
                continue
            if part == "..":
                if not parts:
                    return "", "validation path escapes the repository"
                parts.pop()
            else:
                parts.append(part)
        return "/".join(parts), None

    def referenced_validation_paths(
        command: str,
    ) -> tuple[set[str], list[str]]:
        """Extract paths from sealed atomic ``;`` / ``&&`` commands.

        A semicolon is an explicit scheduler command boundary, so each atom
        starts at the repository root. Within an atom, only a pure ``&&``
        chain is accepted and an optional ``cd`` must be its first segment.
        This mirrors the board's fail-closed validation-command grammar
        without importing mutable supervisor/product code.
        """

        paths: set[str] = set()
        path_errors: list[str] = []

        atoms: list[str] = []
        current: list[str] = []
        in_single_quote = False
        in_double_quote = False
        escaped = False

        def flush_atom() -> None:
            atom = "".join(current).strip()
            if atom:
                atoms.append(atom)
            else:
                path_errors.append("validation has an empty command atom")
            current.clear()

        for character in command.strip():
            if escaped:
                if character in {"\n", "\r"} and not in_single_quote:
                    path_errors.append(
                        "validation must not contain line continuation syntax"
                    )
                current.append(character)
                escaped = False
                continue
            if character == "\\" and not in_single_quote:
                current.append(character)
                escaped = True
                continue
            if character == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
                current.append(character)
                continue
            if character == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                current.append(character)
                continue
            if character == ";" and not in_single_quote and not in_double_quote:
                flush_atom()
                continue
            if character in {"\n", "\r"} and not in_single_quote:
                path_errors.append("validation must not contain shell newlines")
            current.append(character)
        flush_atom()
        if in_single_quote or in_double_quote or escaped:
            path_errors.append("validation contains unterminated shell quoting")

        for atom in atoms:
            try:
                lexer = shlex.shlex(
                    atom,
                    posix=True,
                    punctuation_chars=";&|()<>",
                )
                lexer.whitespace_split = True
                lexer.commenters = ""
                tokens = list(lexer)
            except ValueError as exc:
                path_errors.append(f"cannot parse validation command: {exc}")
                continue
            if (
                not tokens
                or tokens[0] == "&&"
                or tokens[-1] == "&&"
                or any(
                    token != "&&"
                    and any(character in token for character in ";&|()<>")
                    for token in tokens
                )
            ):
                path_errors.append("validation uses unsupported shell structure")
                continue
            segments: list[list[str]] = [[]]
            malformed = False
            for token in tokens:
                if token == "&&":
                    if not segments[-1]:
                        malformed = True
                        break
                    segments.append([])
                    continue
                segments[-1].append(token)
            if malformed or not segments[-1]:
                path_errors.append("validation has a malformed && chain")
                continue

            cwd = PurePosixPath(".")
            for index, segment in enumerate(segments):
                if segment[0] == "cd":
                    if index != 0 or len(segment) != 2:
                        path_errors.append(
                            "validation cd must be the first segment with one path"
                        )
                        continue
                    normalized, problem = normalize_validation_path(cwd, segment[1])
                    if problem:
                        path_errors.append(problem)
                    else:
                        cwd = PurePosixPath(normalized or ".")
                    continue
                for token in segment:
                    if (
                        token.startswith("-")
                        or "/" not in token
                        or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", token)
                        or any(character in token for character in "$*?[]{}")
                    ):
                        continue
                    normalized, problem = normalize_validation_path(cwd, token)
                    if problem:
                        path_errors.append(problem)
                    elif normalized:
                        paths.add(normalized)
        return paths, path_errors

    for goal_id, record in records.items():
        metadata = record["metadata"]
        if not str(record.get("title") or "").strip():
            errors.append(f"{goal_id}: title must be nonempty")
        for field in GOAL_REQUIRED_FIELDS:
            if field not in metadata:
                errors.append(f"{goal_id}: missing metadata field {field!r}")
            elif field not in {"parent", "depends on", "direct child goals", "producing tasks"} and not metadata[field].strip():
                errors.append(f"{goal_id}: metadata field {field!r} is empty")
        if metadata.get("status", "").lower() != "pending":
            errors.append(f"{goal_id}: status must be pending at launch")
        parent_values = _split_csv(metadata.get("parent", ""))
        if goal_id == "VGO-G000":
            if parent_values:
                errors.append("VGO-G000 must not have a parent")
            parents[goal_id] = ""
        else:
            if len(parent_values) != 1 or parent_values[0] not in GOAL_IDS:
                errors.append(f"{goal_id}: Parent must name one declared goal")
                parents[goal_id] = ""
            else:
                parents[goal_id] = parent_values[0]
        dependencies = _split_csv(metadata.get("depends on", ""))
        graph[goal_id] = dependencies
        for dependency in dependencies:
            if dependency not in GOAL_IDS:
                errors.append(f"{goal_id}: unknown goal dependency {dependency!r}")
            if dependency == goal_id:
                errors.append(f"{goal_id}: cannot depend on itself")
        children = _split_csv(metadata.get("direct child goals", ""))
        direct_children[goal_id] = children
        for child in children:
            if child not in GOAL_IDS:
                errors.append(f"{goal_id}: unknown direct child {child!r}")

        producing_tasks = _split_csv(metadata.get("producing tasks", ""))
        producing_by_goal[goal_id] = producing_tasks
        owned_outputs: set[str] = set()
        for task_id in producing_tasks:
            if task_id not in TASK_IDS:
                errors.append(f"{goal_id}: unknown producing task {task_id!r}")
            else:
                producing_mentions.add(task_id)
                task_record = task_records.get(task_id)
                if task_record is not None:
                    task_goal = task_record["metadata"].get("goal id", "")
                    if task_goal != goal_id:
                        errors.append(
                            f"{goal_id}: producing task {task_id} has primary "
                            f"Goal id {task_goal!r}"
                        )
                    owned_outputs.update(
                        _split_csv(task_record["metadata"].get("outputs", ""))
                    )

        goal_outputs = _split_csv(metadata.get("outputs", ""))
        if len(goal_outputs) != len(set(goal_outputs)):
            errors.append(f"{goal_id}: Outputs contains duplicate paths")
        for output in goal_outputs:
            if not _safe_relative_path(output):
                errors.append(f"{goal_id}: unsafe Output path {output!r}")
            elif not output_is_declared(output, owned_outputs):
                errors.append(
                    f"{goal_id}: Output {output!r} is not owned by a "
                    "declared producing task"
                )

        validation_paths, path_errors = referenced_validation_paths(
            metadata.get("validation", "")
        )
        for problem in path_errors:
            errors.append(f"{goal_id}: {problem}")
        for relative in sorted(validation_paths):
            if (
                relative not in CONTROL_PATHS
                and not output_is_declared(relative, all_task_outputs)
                and not (REPO_ROOT / relative).exists()
            ):
                errors.append(
                    f"{goal_id}: Validation references undeclared path "
                    f"{relative!r}"
                )

    for task_id, task_record in task_records.items():
        primary_goal = task_record["metadata"].get("goal id", "")
        if (
            primary_goal in records
            and task_id not in producing_by_goal.get(primary_goal, [])
        ):
            errors.append(
                f"{task_id}: primary Goal id {primary_goal} does not list the "
                "task in Producing tasks"
            )

    for goal_id, parent in parents.items():
        if not parent:
            continue
        if goal_id not in direct_children.get(parent, []):
            errors.append(
                f"{goal_id}: Parent {parent} does not list it as a direct child"
            )
    for parent, children in direct_children.items():
        for child in children:
            if parents.get(child) != parent:
                errors.append(
                    f"{parent}: direct child {child} has Parent {parents.get(child)!r}"
                )
    parent_graph = {
        goal_id: [parent] if parent else [] for goal_id, parent in parents.items()
    }
    cyclic = sorted(_cycle_nodes(parent_graph))
    if cyclic:
        errors.append(f"goal parent graph is cyclic at {cyclic}")
    dependency_cycles = sorted(_cycle_nodes(graph))
    if dependency_cycles:
        errors.append(f"goal dependency graph is cyclic at {dependency_cycles}")
    missing_task_mentions = sorted(set(task_records) - producing_mentions)
    if missing_task_mentions:
        errors.append(
            "goal heap Producing tasks omits declared tasks: "
            f"{missing_task_mentions}"
        )

    root_metadata = records.get("VGO-G000", {}).get("metadata", {})
    root_claims = "\n".join(
        (
            root_metadata.get("acceptance", ""),
            root_metadata.get("conflict policy", ""),
        )
    ).lower()
    for required_claim in (
        "exactly 15",
        "final receipt",
        "dependency audit",
        "integrity rather than truth",
        "proof cache",
    ):
        if required_claim not in root_claims:
            errors.append(
                f"VGO-G000: final acceptance boundary omits {required_claim!r}"
            )


def validate() -> dict[str, Any]:
    errors: list[str] = []
    config_file = REPO_ROOT / CONFIG_PATH
    try:
        config = _load_json(config_file)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "schema": "verified-gui-optimizer-board-validation@1",
            "valid": False,
            "errors": [f"cannot load scheduler config: {type(exc).__name__}: {exc}"],
            "summary": {"task_count": 0, "goal_count": 0, "wave_count": 0},
        }

    _validate_config(config, errors)
    required_paths = {
        CONFIG_PATH.as_posix(),
        RECOVERY_RECEIPT_PATH.as_posix(),
        str(config.get("taskboard_path") or ""),
        str(config.get("objectives_path") or ""),
        str(config.get("plan_path") or ""),
        str(config.get("validator_path") or ""),
        "scripts/ops/agent_supervisor/implementation_supervisor_entry.py",
        "scripts/ops/verified_gui_optimizer_status.py",
    }
    for relative in sorted(required_paths):
        if not relative or not _safe_relative_path(relative):
            errors.append(f"invalid required control path {relative!r}")
        elif not (REPO_ROOT / relative).is_file():
            errors.append(f"missing required control file {relative}")

    task_records: dict[str, dict[str, Any]] = {}
    goal_records: dict[str, dict[str, Any]] = {}
    task_path = REPO_ROOT / str(config.get("taskboard_path") or "")
    goal_path = REPO_ROOT / str(config.get("objectives_path") or "")
    plan_path = REPO_ROOT / str(config.get("plan_path") or "")
    if task_path.is_file():
        task_records, parse_errors = _parse_markdown_records(
            task_path,
            re.compile(
                r"^## (?P<id>VGO-[0-9]{3}) (?P<title>\S.*)$"
            ),
        )
        errors.extend(parse_errors)
        _validate_tasks(task_records, config, errors)
    recovery_receipt_file = REPO_ROOT / RECOVERY_RECEIPT_PATH
    if recovery_receipt_file.is_file():
        try:
            recovery_receipt_raw = recovery_receipt_file.read_bytes()
            recovery_receipt = json.loads(
                recovery_receipt_raw.decode("utf-8"),
                object_pairs_hook=_object_without_duplicates,
            )
            if not isinstance(recovery_receipt, dict):
                raise ValueError("root must be an object")
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            ValueError,
        ) as exc:
            errors.append(
                "cannot load recovery amendment: "
                f"{type(exc).__name__}: {exc}"
            )
        else:
            _validate_recovery_amendment(
                recovery_receipt,
                recovery_receipt_raw,
                task_records,
                config,
                errors,
            )
    if goal_path.is_file():
        goal_records, parse_errors = _parse_markdown_records(
            goal_path,
            re.compile(
                r"^## (?P<id>VGO-G[0-9]{3}) (?P<title>\S.*)$"
            ),
        )
        errors.extend(parse_errors)
        _validate_goals(goal_records, task_records, errors)
    if plan_path.is_file():
        plan_text = plan_path.read_text(encoding="utf-8")
        for required_text in (
            "VerifiedGuiOptimizer",
            "Agent Supervisor",
            TARGET_SOURCE,
            "formally verified",
            "heuristic",
            "human review",
        ):
            if required_text.lower() not in plan_text.lower():
                errors.append(f"plan is missing required scope/evidence text {required_text!r}")

    unique_errors = sorted(dict.fromkeys(errors))
    return {
        "schema": "verified-gui-optimizer-board-validation@1",
        "valid": not unique_errors,
        "errors": unique_errors,
        "summary": {
            "task_count": len(task_records),
            "goal_count": len(goal_records),
            "wave_count": len(config.get("waves", []))
            if isinstance(config.get("waves"), list)
            else 0,
            "strict_lane_count": int(config.get("max_lanes") or 0),
            "selected_source": TARGET_SOURCE,
            "refill_enabled": bool(
                config.get("objective_refill_enabled")
                or config.get("codebase_refill_enabled")
            ),
        },
    }


def main(argv: list[str]) -> int:
    if argv != ["--check-all"]:
        report = {
            "schema": "verified-gui-optimizer-board-validation@1",
            "valid": False,
            "errors": ["usage: validate_verified_gui_optimizer_board.py --check-all"],
            "summary": {"task_count": 0, "goal_count": 0, "wave_count": 0},
        }
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
        return 2
    try:
        report = validate()
    except Exception as exc:  # Fail closed while preserving the JSON-only contract.
        report = {
            "schema": "verified-gui-optimizer-board-validation@1",
            "valid": False,
            "errors": [f"validator exception: {type(exc).__name__}: {exc}"],
            "summary": {"task_count": 0, "goal_count": 0, "wave_count": 0},
        }
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report.get("valid") is True else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

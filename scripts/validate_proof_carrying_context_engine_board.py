#!/usr/bin/env python3
"""Validate and project the Proof-Carrying Context Engine v0.1 board.

The Markdown objective heap and todo board remain authoritative operator inputs.
This script emits bounded JSON projections for schedulers and reviewers; it
does not admit work, grant effects, or prove completion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEL_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
if str(ACCEL_ROOT) not in sys.path:
    sys.path.insert(0, str(ACCEL_ROOT))

from ipfs_accelerate_py.agent_supervisor.objectives.objective_graph import (  # noqa: E402
    parse_goal_heap,
)
from ipfs_accelerate_py.agent_supervisor.runtime.artifact_store import (  # noqa: E402
    write_bundle_index_artifact,
)
from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (  # noqa: E402
    ConfiguredBoardError,
    load_configured_board,
)
from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (  # noqa: E402
    parse_task_file,
    split_csv,
)


OBJECTIVE_PATH = REPO_ROOT / "docs/architecture/proof_carrying_context_engine_v0_1.objectives.md"
TODO_PATH = REPO_ROOT / "docs/architecture/proof_carrying_context_engine_v0_1.todo.md"
PLAN_PATH = REPO_ROOT / "docs/architecture/PROOF_CARRYING_CONTEXT_ENGINE_V0_1_PLAN.md"
CONFIG_PATH = REPO_ROOT / "config/proof_carrying_context_engine_v0_1_supervisor.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts/proof_carrying_context_engine/control"
HISTORICAL_R2_RECEIPT_PATH = (
    REPO_ROOT / "artifacts/proof_carrying_context_engine/receipts/PCCE-000.json"
)
HISTORICAL_R3_RECEIPT_PATH = (
    REPO_ROOT / "artifacts/proof_carrying_context_engine/receipts/PCCE-000-r3.json"
)
HISTORICAL_R4_RECEIPT_PATH = (
    REPO_ROOT / "artifacts/proof_carrying_context_engine/receipts/PCCE-000-r4.json"
)
ACTIVE_R5_RECEIPT_PATH = (
    REPO_ROOT / "artifacts/proof_carrying_context_engine/receipts/PCCE-000-r5.json"
)
R2_INCIDENT_PATH = (
    REPO_ROOT
    / "artifacts/proof_carrying_context_engine/control/incidents/scheduler-r2-provider-handoff.json"
)
R3_INCIDENT_PATH = (
    REPO_ROOT
    / "artifacts/proof_carrying_context_engine/control/incidents/scheduler-r3-provider-route.json"
)
PROFILE_G_BOOTSTRAP_RECEIPT_PATH = (
    REPO_ROOT
    / "artifacts/proof_carrying_context_engine/control/profile_g_bootstrap_receipt.json"
)
HISTORICAL_R2_ARTIFACT_IDENTITY = "urn:pcce:task-receipt:PCCE-000:v0.1-r2"
HISTORICAL_R3_ARTIFACT_IDENTITY = "urn:pcce:task-receipt:PCCE-000:v0.1-r3"
HISTORICAL_R4_ARTIFACT_IDENTITY = "urn:pcce:task-receipt:PCCE-000:v0.1-r4"
ACTIVE_R5_ARTIFACT_IDENTITY = "urn:pcce:task-receipt:PCCE-000:v0.1-r5"
R2_INCIDENT_IDENTITY = "urn:pcce:control-incident:scheduler-r2-provider-handoff"
R3_INCIDENT_IDENTITY = "urn:pcce:control-incident:scheduler-r3-provider-route"
HISTORICAL_R2_ADMISSION_COMMIT = "d498faad8b75321a6981d6dfb944bb589581b333"
HISTORICAL_R2_RECEIPT_BYTE_SHA256 = (
    "sha256:b3f51cd71ba6d31804047469aa03a198205b3e7a75e607929c07709a46f8d3e4"
)
HISTORICAL_R2_RECEIPT_GIT_BLOB = "fff24f12acbb1d3edf0206916d343d27e189128f"
HISTORICAL_R2_RECEIPT_CONTENT_ID = (
    "sha256:491f3edea7febc4306e297082f60ca1e46677c38d60427015302622dc912c029"
)
R2_INCIDENT_FILE_SHA256 = (
    "sha256:98c5c8c3b1f038962a55698524f10feee0fd29568e36b52c09ca020cc77dd141"
)
R2_INCIDENT_CONTENT_ID = (
    "sha256:2c3ff2b51de842d5349d5518a5240ed37780062702ba6aa68d39485202016215"
)
HISTORICAL_R3_RECEIPT_BYTE_SHA256 = (
    "sha256:f674da5a09d34e0592c21fd32dbb3886cc298d7b0edb4947ea152674c95a6685"
)
HISTORICAL_R3_RECEIPT_GIT_BLOB = "d788c2e1362152b9894556ebb709ad0f071e08fa"
HISTORICAL_R3_RECEIPT_CONTENT_ID = (
    "sha256:7a08c3f3cc34b405daa66220558d1ddc662ec80435b132610a2f4e1aa047ff49"
)
R3_INCIDENT_FILE_SHA256 = (
    "sha256:50b92024287422ca8b45eb4514aed11adb6508e874f790b405d16d8ec73fb09d"
)
R3_INCIDENT_GIT_BLOB = "e6d68b42c4a55b4f5dc238b66f22dbfc6396f3c4"
R3_INCIDENT_CONTENT_ID = (
    "sha256:6f06d9dd6cffe17484028f468618eb9000edd6de34adc550285a0bb603b52702"
)
HISTORICAL_R4_RECEIPT_BYTE_SHA256 = (
    "sha256:13d3a58418db67c3ee7d55ab3741e527a78bfc199dda0ca0ff12b05be5bf6e53"
)
HISTORICAL_R4_RECEIPT_GIT_BLOB = "f5632d592505d49d7297b3c68bae2949861a2838"
HISTORICAL_R4_RECEIPT_CONTENT_ID = (
    "sha256:f5fd281c7df68630ca36542c83e57d5c20c9eac428a3fc12f82414b9bc8c62ac"
)
R3_CONTROL_COMMIT = "95a04cbc18d8f4316415fe0aadf32c0747df50a6"
R3_CONTROL_TREE = "293c704f2bd6e588b89903f7ac9b6bb3aeb6b87e"
R3_INCIDENT_COMMIT = "5f962ac16768b16febbfc434c1fcd44c6c5bc8f9"
R4_CONTROL_COMMIT = "aaed3c3ce7625ba81a7c001a33883d22dbc3fe28"
R4_CONTROL_TREE = "e556658a3c9a6f72e4a6141e53926a21273c8b0d"
HISTORICAL_R3_ACCELERATOR_COMMIT = "50c0b8551397983f664fbaa6ac12c68ba0eda82c"
HISTORICAL_R3_ACCELERATOR_TREE = "a16781386689845c1162c85c0f5c899a673d48e6"
REJECTED_ACCELERATOR_COMMIT = "b0c85d48f0a1a3337a5aea2d2698e4c9e28fadf0"
REJECTED_ACCELERATOR_TREE = "490d17028d011b5cc966af8b3762df303f3abfb1"
FINAL_ACCELERATOR_COMMIT = "0837254e910221c17b3c8ac8a2a233658de976f1"
FINAL_ACCELERATOR_TREE = "6eaf101d471ea2ad1b0c948d2e648ea925b444fe"
REPLACEMENT_STATE_ROOT = Path(
    "/home/barberb/.local/state/ipfs_accelerate_py/proof-carrying-context-engine-v0.1"
)
TASK_PREFIX = "## PCCE-"
BOARD_NAMESPACE = "proof-carrying-context-engine-v0.1"
OBJECTIVE_ID = "PCCE-G000"
PLANNING_GENERATED_AT = "2026-08-14T00:00:00+00:00"

HISTORICAL_R2_PROJECTION_IDS = {
    "board_projection_id": "sha256:680932d46a903b5ceb305708b99ff351ff55b32259ddea515922406dcb3ee0ae",
    "dependency_graph_id": "sha256:83f4aade99e0dd44b503dcc6696707ed93c43b7a2b6769682f81f068f23bf25f",
    "bundle_index_id": "sha256:9ecaacfaf4e6f311666d72659f84fa12f92fa563474ef97108c6d3e20f0ac253",
}
HISTORICAL_R2_GITLINKS = {
    "accelerate": "c8e953be8696d47376442c73739eea14fad83113",
    "datasets": "ac82107e246b30e35a2bbdcf75e01370d22350c6",
    "kit": "6196017ca3df016c7159dce43af60f2a0d96a9ae",
    "mcp_plus_plus": "6965f89f066769f3b3ac7b5f753b1a0044562570",
}
R2_RAW_ARTIFACTS = {
    "logs-r2/pcce-a-inventory-accelerate.log": (24730, "sha256:5cd5ad2f53f9758202b00957a7821ba4bc553a60fa792a33e21ccb436a4cf066"),
    "logs-r2/pcce-a-inventory-datasets.log": (37095, "sha256:ec556cc7ce68412207e8f8ac3fd3bbd2177fc8361d05c18d7b945277e03b5a9c"),
    "logs-r2/pcce-a-inventory-kit.log": (12365, "sha256:cfee6541e0623eacfdba7289f2112d3cc204f99afd4eb0854f085d504f12d9c1"),
    "scheduler-r2/.bundle_lanes.duckdb.lock": (0, "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    "scheduler-r2/.coordination.duckdb.lock": (0, "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    "scheduler-r2/bundle_lanes.duckdb": (10760192, "sha256:c60ec7e70e7e140beadcd3080316ea3ec1aeb4e2bdc0a5995e10d86b43224a0e"),
    "scheduler-r2/bundle_lanes.json": (3543573, "sha256:d63f0605c1f1ca43ca16b27c572d52aeebf417a4632b384cbac37e0c300df087"),
    "scheduler-r2/coordination.duckdb": (15478784, "sha256:5d939da8f54eaa39df033a8e085b65f033fa8b3f9126deb23f9e65702999f992"),
    "scheduler-r2/pcce-a-inventory-accelerate/state/agent_pcce_a_inventory_accelerate_bundle_supervisor.pid": (8, "sha256:f16d806da35c4d9544a3b38310521beec4e6da603463a3be98bf285a3757215e"),
    "scheduler-r2/pcce-a-inventory-accelerate/state/agent_pcce_a_inventory_accelerate_runtime.todo.md": (258316, "sha256:a60be7d4108c988b35fdc7ae9ebc32e24ce1c9731cb2d1a91f109663d81c276e"),
    "scheduler-r2/pcce-a-inventory-accelerate/state/agent_pcce_a_inventory_accelerate_taskboard_input.json": (685, "sha256:6003ff7ae134bece37de3b1eff7c33172a1357da96a5e3f8bea0ba192da2e8f1"),
    "scheduler-r2/pcce-a-inventory-datasets/state/agent_pcce_a_inventory_datasets_bundle_supervisor.pid": (8, "sha256:4bad5fdff14c84d3abbe5d47e3be7ea15bf4dedb54fb2e70f71f529b2e0c2af9"),
    "scheduler-r2/pcce-a-inventory-datasets/state/agent_pcce_a_inventory_datasets_runtime.todo.md": (258316, "sha256:a60be7d4108c988b35fdc7ae9ebc32e24ce1c9731cb2d1a91f109663d81c276e"),
    "scheduler-r2/pcce-a-inventory-datasets/state/agent_pcce_a_inventory_datasets_taskboard_input.json": (679, "sha256:613df9f0b73be723d85f9283853ef41c0938cb01195ab81682284fcfd2c89d1f"),
    "scheduler-r2/pcce-a-inventory-kit/state/agent_pcce_a_inventory_kit_bundle_supervisor.pid": (8, "sha256:95cb5bb1a29b235dc5287151d1506bf090082bc1efd7ca84306a06e601aaef55"),
    "scheduler-r2/pcce-a-inventory-kit/state/agent_pcce_a_inventory_kit_runtime.todo.md": (258316, "sha256:a60be7d4108c988b35fdc7ae9ebc32e24ce1c9731cb2d1a91f109663d81c276e"),
    "scheduler-r2/pcce-a-inventory-kit/state/agent_pcce_a_inventory_kit_taskboard_input.json": (664, "sha256:f16a47ccb353710bd8edf5013fb05f962c4f770ae0c3468a82eda6bd8b569033"),
    "scheduler-r2/scheduler_decision_metrics.json": (163119, "sha256:866b88ff2b510098fb9a7d909a9a3c2ea8dd695d5849ff6463e4722d6b9ae24c"),
    "scheduler-r2/scheduler_metrics.json": (163119, "sha256:866b88ff2b510098fb9a7d909a9a3c2ea8dd695d5849ff6463e4722d6b9ae24c"),
}

EXPECTED_TASK_IDS = (
    ["PCCE-000"]
    + [f"PCCE-{value:03d}" for value in range(1, 20)]
    + [f"PCCE-{value:03d}" for value in range(20, 26)]
    + [f"PCCE-{value:03d}" for value in range(30, 36)]
    + [f"PCCE-{value:03d}" for value in range(40, 46)]
    + [f"PCCE-{value:03d}" for value in range(50, 58)]
    + [f"PCCE-{value:03d}" for value in range(60, 69)]
    + [f"PCCE-{value:03d}" for value in range(70, 77)]
    + ["PCCE-079"]
    + [f"PCCE-{value:03d}" for value in range(80, 84)]
)
EXPECTED_GOAL_IDS = ["PCCE-G000"] + [f"PCCE-G{value}" for value in range(100, 900, 100)]

REQUIRED_METADATA = {
    "status",
    "completion",
    "is schedulable",
    "review only",
    "owning repository",
    "owned paths",
    "objective",
    "depends on",
    "priority",
    "risk classification",
    "execution mode",
    "allowed effects",
    "prohibited effects",
    "acceptance criteria",
    "required tests",
    "required evidence",
    "rollback procedure",
    "assigned worktree",
    "final result cid or artifact identity",
    "goal id",
    "outputs",
    "validation",
    "board namespace",
    "bundle",
    "parallel lane",
    "resource class",
    "implementation timeout seconds",
    "predicted files",
    "conflict policy",
    "acceptance",
}

ALLOWED_TASK_STATUSES = {
    "todo",
    "queued",
    "proposed",
    "admitted",
    "ready",
    "in_progress",
    "running",
    "blocked",
    "completed",
    "failed",
    "rejected",
    "quarantined",
    "cancelled",
}
ALLOWED_REPOSITORIES = {
    "endomorphosis/ipfs_datasets_py",
    "endomorphosis/ipfs_kit_py",
    "endomorphosis/ipfs_accelerate_py",
    "endomorphosis/Mcp-Plus-Plus",
    "endomorphosis/lift_coding",
    "cross-repository",
}


def _git(*args: str, cwd: Path = REPO_ROOT) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _sha256_json(payload: Any) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _headings(path: Path, prefix: str) -> list[str]:
    result: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            result.append(line[3:].split(maxsplit=1)[0])
    return result


def _topological_order(task_ids: Iterable[str], edges: dict[str, list[str]]) -> list[str]:
    nodes = list(task_ids)
    followers: dict[str, list[str]] = defaultdict(list)
    indegree = {task_id: 0 for task_id in nodes}
    for task_id, dependencies in edges.items():
        for dependency in dependencies:
            followers[dependency].append(task_id)
            indegree[task_id] += 1
    ready = deque(sorted(task_id for task_id, count in indegree.items() if count == 0))
    ordered: list[str] = []
    while ready:
        task_id = ready.popleft()
        ordered.append(task_id)
        for follower in sorted(followers[task_id]):
            indegree[follower] -= 1
            if indegree[follower] == 0:
                ready.append(follower)
    return ordered


def _repository_identity(config: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    source_binding = dict(config.get("source_binding") or {})
    result: dict[str, Any] = {
        "planning_base_commit": str(
            source_binding.get("accelerator_required_ancestor") or ""
        ),
        "planning_branch": str(
            source_binding.get("accelerator_required_branch") or ""
        ),
        "admission_head_binding": "external-launch-receipt",
        "repositories": {},
    }
    for name, record in config["repositories"].items():
        relative = str(record["path"])
        path = REPO_ROOT / relative
        if not (path / ".git").exists():
            errors.append(f"uninitialized repository: {relative}")
            continue
        # Resolve the candidate control tree from the index.  This permits a
        # protected control revision to validate its staged gitlink before the
        # atomic superproject commit; after commit the same object is in HEAD.
        gitlink = _git("rev-parse", f":{relative}")
        head = _git("rev-parse", "HEAD", cwd=path)
        dirty = _git("status", "--porcelain=v1", "--untracked-files=all", cwd=path)
        if gitlink != head:
            errors.append(f"gitlink/head mismatch for {relative}: {gitlink} != {head}")
        if dirty:
            errors.append(f"dirty governed repository at validation: {relative}")
        result["repositories"][name] = {
            "path": relative,
            "gitlink": gitlink,
            "head": head,
            "initial_commit": str(record["initial_commit"]),
            "dirty": bool(dirty),
        }
    return result


def _metadata_bool(value: Any, *, default: bool = False) -> bool:
    normalized = str(value or "").strip().casefold()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    return default


def _bundle_index_projection(
    projected_tasks: list[dict[str, Any]],
    *,
    config: dict[str, Any],
    source_sha256: str,
) -> dict[str, Any]:
    """Project the reviewed Markdown board into canonical bundle-index input.

    The projection deliberately points every bundle at the same protected
    source board.  ``bundle_supervisor`` materializes only the leased execution
    slice into each lane's private runtime board, so no generated shard can
    become a competing source of task intent.
    """

    bundles: dict[str, dict[str, Any]] = {}
    priority_weights = {"P0": 100, "P1": 80, "P2": 60, "P3": 40}
    for task in projected_tasks:
        metadata = dict(task["metadata"])
        bundle_key = metadata.get("bundle", "").strip()
        if not bundle_key:
            continue
        predicted_files = list(task["predicted_files"])
        allowed_paths = split_csv(metadata.get("allowed paths", ""))
        schedulable = _metadata_bool(metadata.get("is schedulable"), default=True)
        review_only = _metadata_bool(metadata.get("review only"), default=False)
        priority = metadata.get("priority", "P2").strip().upper()
        task_payload = {
            "task_id": task["task_id"],
            "canonical_task_key": task["canonical_task_key"],
            "canonical_task_cid": task["canonical_task_cid"],
            "title": task["title"],
            "objective": metadata.get("objective", ""),
            "goal_id": task["goal_id"],
            "parent_goal_ids": [OBJECTIVE_ID],
            "board_namespace": BOARD_NAMESPACE,
            "status": task["status"],
            "is_schedulable": schedulable,
            "review_only": review_only,
            "depends_on": list(task["dependencies"]),
            "dependencies": list(task["dependencies"]),
            "dependency_task_ids": list(task["dependencies"]),
            "outputs": list(task["outputs"]),
            "files": predicted_files,
            "predicted_files": predicted_files,
            "predicted_paths": predicted_files,
            "allowed_paths": allowed_paths or predicted_files,
            "validation_commands": [metadata.get("validation", "")],
            "priority": priority,
            "objective_priority": priority_weights.get(priority, 20),
            "risk_classification": metadata.get("risk classification", ""),
            "execution_mode": metadata.get("execution mode", ""),
            "resource_class": metadata.get("resource class", "cpu-small"),
            "resource_stage": metadata.get("resource stage", "implementation"),
            "implementation_timeout_seconds": int(
                metadata.get("implementation timeout seconds", "0") or 0
            ),
            "max_attempts": int(config["max_task_attempts"]),
            "metadata": metadata,
        }
        bundle = bundles.setdefault(
            bundle_key,
            {
                "bundle_key": bundle_key,
                "shard_path": str(TODO_PATH.relative_to(REPO_ROOT)),
                "parallel_lane": metadata.get("parallel lane", bundle_key),
                "bundle_strategy": "reviewed-manual-task-slice-v1",
                "conflict_policy": metadata.get("conflict policy", ""),
                "execution_authority": "agent-supervisor/v1",
                "is_schedulable": False,
                "review_only": True,
                "tasks": [],
            },
        )
        bundle["tasks"].append(task_payload)
        bundle["is_schedulable"] = bool(bundle["is_schedulable"] or schedulable)
        bundle["review_only"] = bool(bundle["review_only"] and review_only)

    payload: dict[str, Any] = {
        "schema": "ipfs_accelerate_py.agent_supervisor.reviewed-bundle-index@1",
        "generated_at": PLANNING_GENERATED_AT,
        "source_todo": str(TODO_PATH.relative_to(REPO_ROOT)),
        "source_todo_sha256": source_sha256,
        "objective_id": OBJECTIVE_ID,
        "board_namespace": BOARD_NAMESPACE,
        "authoritative": False,
        "authority_note": (
            "The protected Markdown board remains authoritative; this is a "
            "queryable scheduler projection only."
        ),
        "bundles": dict(sorted(bundles.items())),
    }
    payload["projection_id"] = _sha256_json(payload)
    return payload


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json_object(path: Path, *, label: str, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"{label} is missing: {path.relative_to(REPO_ROOT)}")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{label} is unreadable: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{label} must be a JSON object")
        return None
    return payload


def _verify_content_id(
    payload: dict[str, Any], *, expected: str | None, label: str, errors: list[str]
) -> None:
    content_id = str(payload.get("content_id") or "")
    content_payload = dict(payload)
    content_payload.pop("content_id", None)
    calculated = _sha256_json(content_payload)
    if content_id != calculated:
        errors.append(f"{label} content_id does not match canonical content")
    if expected is not None and content_id != expected:
        errors.append(f"{label} content_id differs from its frozen identity")


def _expected_parser_report(goal_count: int) -> dict[str, Any]:
    return {
        "task_count": len(EXPECTED_TASK_IDS),
        "goal_count": goal_count,
        "unique_task_ids": True,
        "acyclic": True,
        "unique_terminal_task_id": "PCCE-083",
        "initial_ready_task_ids": [
            "PCCE-001",
            "PCCE-002",
            "PCCE-003",
            "PCCE-004",
        ],
    }


def _verify_historical_r2_receipt(*, goal_count: int, errors: list[str]) -> None:
    """Verify the admitted r2 receipt only against frozen r2 identities.

    This verifier intentionally does not compare r2 evidence with the current
    board, config, validator, projections, protected paths, or gitlinks.
    """

    receipt = _load_json_object(
        HISTORICAL_R2_RECEIPT_PATH, label="historical PCCE-000 r2 receipt", errors=errors
    )
    if receipt is None:
        return
    if HISTORICAL_R2_RECEIPT_PATH.stat().st_size != 4373:
        errors.append("historical PCCE-000 r2 receipt byte size changed")
    if _file_sha256(HISTORICAL_R2_RECEIPT_PATH) != HISTORICAL_R2_RECEIPT_BYTE_SHA256:
        errors.append("historical PCCE-000 r2 receipt bytes changed")
    if _git("hash-object", str(HISTORICAL_R2_RECEIPT_PATH)) != HISTORICAL_R2_RECEIPT_GIT_BLOB:
        errors.append("historical PCCE-000 r2 receipt Git blob changed")
    _verify_content_id(
        receipt,
        expected=HISTORICAL_R2_RECEIPT_CONTENT_ID,
        label="historical PCCE-000 r2 receipt",
        errors=errors,
    )
    fixed_expectations = {
        "schema": "proof-carrying-context-engine/task-receipt@1",
        "task_id": "PCCE-000",
        "objective_id": OBJECTIVE_ID,
        "board_namespace": BOARD_NAMESPACE,
        "status": "completed",
        "artifact_identity": HISTORICAL_R2_ARTIFACT_IDENTITY,
        "control_base": "b6f40c05e0884867eb8557f8882cd25cb760ca2f",
    }
    for field, expected in fixed_expectations.items():
        if receipt.get(field) != expected:
            errors.append(f"historical PCCE-000 r2 receipt {field} mismatch")

    evidence = receipt.get("evidence")
    if not isinstance(evidence, dict):
        errors.append("historical PCCE-000 r2 receipt evidence must be an object")
        return
    fixed_evidence = {
        **HISTORICAL_R2_PROJECTION_IDS,
        "objective_sha256": "sha256:bdd0b3e16ced4a1b54f991c8d983259a92bb892c67f21a19e8ccf46841086a3d",
        "todo_sha256": "sha256:a60be7d4108c988b35fdc7ae9ebc32e24ce1c9731cb2d1a91f109663d81c276e",
        "plan_sha256": "sha256:f75693f2d863b65de7886b004e65bfb0aa2b494fc9db493f0c17750d1bbe2ff5",
        "config_sha256": "sha256:21e4cba02c34ca186904c958742c0f7adf4e94a633cc73ab4ee4ae3e0a0b15ac",
        "validator_sha256": "sha256:5202ad1042ad35762a7cf8f8cc86a66f5f82b8cda230e764fd5cd31062e46536",
        "profile_g_bootstrap_sha256": "sha256:37ae92791a4a2705bf97c83cbdeb383b1dec97e8604daf4f138bbde9692f37f5",
        "repository_gitlinks": HISTORICAL_R2_GITLINKS,
        "task_ids": list(EXPECTED_TASK_IDS),
    }
    for field, expected in fixed_evidence.items():
        if evidence.get(field) != expected:
            errors.append(f"historical PCCE-000 r2 evidence mismatch: {field}")
    historical_protected_paths = [
        "artifacts/proof_carrying_context_engine/control/bundle_index.json",
        "artifacts/proof_carrying_context_engine/control/profile_g_bootstrap_receipt.json",
        "artifacts/proof_carrying_context_engine/control/task_board.json",
        "artifacts/proof_carrying_context_engine/control/task_dependency_graph.json",
        "artifacts/proof_carrying_context_engine/receipts/PCCE-000.json",
        "config/proof_carrying_context_engine_v0_1_supervisor.json",
        "docs/architecture/PROOF_CARRYING_CONTEXT_ENGINE_V0_1_PLAN.md",
        "docs/architecture/proof_carrying_context_engine_v0_1.objectives.md",
        "docs/architecture/proof_carrying_context_engine_v0_1.todo.md",
        "scripts/validate_proof_carrying_context_engine_board.py",
    ]
    if evidence.get("protected_paths") != historical_protected_paths:
        errors.append("historical PCCE-000 r2 protected-path evidence changed")
    if receipt.get("parser_report") != _expected_parser_report(goal_count):
        errors.append("historical PCCE-000 r2 parser_report changed")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", HISTORICAL_R2_ADMISSION_COMMIT, "HEAD"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode != 0:
        errors.append("historical r2 admission commit is not an ancestor of control HEAD")


def _verify_r2_incident(*, errors: list[str]) -> None:
    incident = _load_json_object(R2_INCIDENT_PATH, label="scheduler-r2 incident", errors=errors)
    if incident is None:
        return
    if _file_sha256(R2_INCIDENT_PATH) != R2_INCIDENT_FILE_SHA256:
        errors.append("scheduler-r2 incident bytes changed")
    _verify_content_id(
        incident,
        expected=R2_INCIDENT_CONTENT_ID,
        label="scheduler-r2 incident",
        errors=errors,
    )
    fixed = {
        "schema": "proof-carrying-context-engine/control-incident@1",
        "incident_id": R2_INCIDENT_IDENTITY,
        "status": "preserved_infrastructure_failure",
        "source_control_commit": HISTORICAL_R2_ADMISSION_COMMIT,
    }
    for field, expected in fixed.items():
        if incident.get(field) != expected:
            errors.append(f"scheduler-r2 incident {field} mismatch")
    source_receipt = incident.get("source_board_receipt")
    expected_source_receipt = {
        "admission_commit": HISTORICAL_R2_ADMISSION_COMMIT,
        "artifact_identity": HISTORICAL_R2_ARTIFACT_IDENTITY,
        "byte_sha256": HISTORICAL_R2_RECEIPT_BYTE_SHA256,
        "byte_size": 4373,
        "content_id": HISTORICAL_R2_RECEIPT_CONTENT_ID,
        "git_blob": HISTORICAL_R2_RECEIPT_GIT_BLOB,
        "path": str(HISTORICAL_R2_RECEIPT_PATH.relative_to(REPO_ROOT)),
        "preserved_byte_for_byte": True,
        "rehash_byte_sha256": HISTORICAL_R2_RECEIPT_BYTE_SHA256,
    }
    if source_receipt != expected_source_receipt:
        errors.append("scheduler-r2 incident source receipt binding mismatch")
    expected_incident_gitlinks = {
        "Mcp-Plus-Plus": HISTORICAL_R2_GITLINKS["mcp_plus_plus"],
        "ipfs_accelerate_py": HISTORICAL_R2_GITLINKS["accelerate"],
        "ipfs_datasets_py": HISTORICAL_R2_GITLINKS["datasets"],
        "ipfs_kit_py": HISTORICAL_R2_GITLINKS["kit"],
    }
    if incident.get("source_repository_gitlinks") != expected_incident_gitlinks:
        errors.append("scheduler-r2 incident source gitlinks mismatch")

    raw = incident.get("raw_artifacts")
    if not isinstance(raw, dict):
        errors.append("scheduler-r2 incident raw_artifacts must be an object")
    else:
        if raw.get("hash_algorithm") != "sha256" or raw.get("hash_passes") != 2:
            errors.append("scheduler-r2 incident raw hash policy mismatch")
        if raw.get("file_count") != len(R2_RAW_ARTIFACTS) or raw.get("all_hashes_stable") is not True:
            errors.append("scheduler-r2 incident raw hash summary mismatch")
        actual_raw: dict[str, tuple[int, str, str, bool]] = {}
        for record in raw.get("files") or []:
            if not isinstance(record, dict) or not str(record.get("path") or ""):
                errors.append("scheduler-r2 incident has an invalid raw-artifact record")
                continue
            actual_raw[str(record["path"])] = (
                int(record.get("size_bytes", -1)),
                str(record.get("sha256_pass_1") or ""),
                str(record.get("sha256_pass_2") or ""),
                record.get("stable") is True,
            )
        expected_raw = {
            path: (size, digest, digest, True)
            for path, (size, digest) in R2_RAW_ARTIFACTS.items()
        }
        if actual_raw != expected_raw:
            errors.append("scheduler-r2 incident preserved raw hashes mismatch")

    snapshot = incident.get("scheduler_snapshot")
    if not isinstance(snapshot, dict):
        errors.append("scheduler-r2 incident scheduler_snapshot must be an object")
    else:
        zero_fields = (
            "active_worker_count",
            "completed_count",
            "implementation_attempt_count",
            "provider_invocation_count",
            "started_count",
        )
        if any(snapshot.get(field) != 0 for field in zero_fields):
            errors.append("scheduler-r2 incident falsely records accepted execution")
        worker_evidence = snapshot.get("worker_evidence") or {}
        if worker_evidence.get("zero_r2_owned_workers_verified") is not True:
            errors.append("scheduler-r2 incident lacks zero-worker evidence")
    partial = incident.get("partial_effects") or {}
    for field in (
        "implementation_workspace_created",
        "source_repository_mutated",
        "submodule_gitlink_mutated",
        "provider_invoked",
        "patch_generated",
        "validation_run",
        "merge_attempted",
        "product_task_completed",
    ):
        if partial.get(field) is not False:
            errors.append(f"scheduler-r2 incident partial effect mismatch: {field}")
    retention = incident.get("retention") or {}
    for field in (
        "resume_scheduler_r2",
        "reuse_scheduler_r2_state",
        "reuse_claims_leases_or_fences",
        "reuse_receipts_as_product_evidence",
    ):
        if retention.get(field) is not False:
            errors.append(f"scheduler-r2 incident retention mismatch: {field}")


def _expected_r3_provider_route_repair() -> dict[str, Any]:
    return {
        "base_commit": "c8e953be8696d47376442c73739eea14fad83113",
        "commits": [
            {
                "commit": "99a329a34dc2625468de5138e12fdb90892076eb",
                "tree": "1f27da000b7b50167646a8dffb3214833a38e9d3",
                "purpose": "production provider argv handoff",
            },
            {
                "commit": "912ecf895717b68abc78545a4f5dfe7f88b69413",
                "tree": "a96edf1db206d6a7dd0eeed0fff1403a3aa0e6cb",
                "purpose": "governed production provider route",
            },
            {
                "commit": HISTORICAL_R3_ACCELERATOR_COMMIT,
                "tree": HISTORICAL_R3_ACCELERATOR_TREE,
                "purpose": "bounded bundle lane controls",
            },
        ],
        "final_commit": HISTORICAL_R3_ACCELERATOR_COMMIT,
        "final_tree": HISTORICAL_R3_ACCELERATOR_TREE,
        "changed_files": [
            {
                "path": "ipfs_accelerate_py/agent_supervisor/objectives/bundle_supervisor.py",
                "sha256": "sha256:d2b89e9330a28a29603bc165a2736003a731563cb95bf4510a35b570a260dc1e",
                "git_blob": "0dc3b1c645b0525b30f57e23b103a953a1178b4d",
            },
            {
                "path": "ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py",
                "sha256": "sha256:fe577ad6abecd444150a2aa510aa4ea95a8a676a771f188da95af7bab7221bf8",
                "git_blob": "c3e8600cf4e33de33100689f24c9cf3f2444d978",
            },
            {
                "path": "ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_supervisor.py",
                "sha256": "sha256:63fc57fee91cc28a982b312d7a81aec6559d8f819772603387be36f42e2b5f28",
                "git_blob": "c049f0c25cb08553f0f3db3d5accdd9ba75dc913",
            },
            {
                "path": "ipfs_accelerate_py/agent_supervisor/todo_daemon/status.py",
                "sha256": "sha256:64ac48f6ee11f061c0e004366a826e4811f37bde201e26294dde477818f9983a",
                "git_blob": "b07f8c9cade96e7b35390595b673502a346add5b",
            },
            {
                "path": "test/api/test_agent_supervisor_planner.py",
                "sha256": "sha256:9f9634626e685721e084055b018cc9079f65c40dcda25cfb9eda649536c64e33",
                "git_blob": "3dcdd09faf24080a3deaa247c454908daf153a7b",
            },
            {
                "path": "test/api/test_agent_supervisor_production_provider_cli.py",
                "sha256": "sha256:c106ed9946b3180f359550cccf530d98e8a5100f7175d7441144535160545251",
                "git_blob": "ce5f3c52ba49563f6ffd7114493ff3a2214545e5",
            },
        ],
        "implementation_gates": {
            "disposition": "passed_for_explicit_pcce_production_policy_route",
            "passed": 216,
            "failed": 0,
            "skipped": 0,
            "xfailed": 0,
            "groups": [
                {"name": "production_cli", "passed": 40},
                {"name": "production_route_security_reviewed_effect_context_slice", "passed": 66},
                {"name": "legacy_landed", "passed": 26},
                {"name": "authority_recovery_post_merge", "passed": 83},
                {"name": "timeout_envelope_planner", "passed": 1},
            ],
            "py_compile": "passed",
            "git_diff_check": "passed",
        },
        "independent_review": {
            "disposition": "pass_with_documented_baseline_exceptions",
            "scope": "exact explicit PCCE governed production-policy implement route",
            "passed": 240,
            "failed": 0,
            "warnings": 3,
            "groups": [
                {"name": "planner", "passed": 33, "warnings": 1},
                {"name": "authority_acceptance_post_merge_legacy", "passed": 101, "warnings": 1},
                {"name": "production_route_cli_security_reviewed_effect_context", "passed": 106, "warnings": 1},
            ],
            "static_findings": {
                "transitive_production_method_closure": {"methods": 48, "missing": 0},
                "canonical_post_merge_acceptance_funnels": 4,
                "legacy_direct_completion_sink_callers": 0,
                "capacity_evidence_redaction": "present",
                "lifecycle_cas": "fail_closed",
                "git_ancestry_binding": "sanitized",
                "worktree_clean_before_and_after": True,
                "git_diff_check": "passed",
            },
        },
        "baseline_limitations": [
            {
                "suite": "implementation_daemon_runner",
                "result": "collection_error",
                "return_code": 2,
                "collected": 0,
                "errors": 1,
                "uncollected_functions": 35,
                "cause": "missing later generic-fallback helper _configured_agent_implementation_route_plan",
                "scope": "not called by the typed PCCE production route",
            },
            {
                "suite": "implementation_supervisor_runner",
                "result": "baseline_failures",
                "passed": 25,
                "failed": 4,
                "cases": [
                    "plan-bound sparse repo_root",
                    "repeated objective-scan-exclude parser",
                    "missing manual_completion_authority_revalidation_only parser field",
                    "no-implement reconciliation worktree-root",
                ],
                "scope": "not exercised by the exact standard PCCE implement command",
            },
            {
                "suite": "default_provider_route",
                "result": "baseline_failures",
                "passed": 2,
                "failed": 21,
                "reproduced_at": "99a329a34dc2625468de5138e12fdb90892076eb",
                "cause": "untouched generic grok_cli_runner",
                "scope": "generic/default route is not qualified or used by the explicit PCCE production route",
            },
        ],
        "qualification_boundary": "explicit PCCE production-policy route only; no blanket full-suite, managed-identity, task-attempt, generic-fallback, or default-provider clearance",
    }


def _expected_r4_provider_route_repair() -> dict[str, Any]:
    return {
        "base_commit": HISTORICAL_R3_ACCELERATOR_COMMIT,
        "base_tree": HISTORICAL_R3_ACCELERATOR_TREE,
        "rejected_candidate": {
            "commit": REJECTED_ACCELERATOR_COMMIT,
            "tree": REJECTED_ACCELERATOR_TREE,
            "purpose": "defer nested Grok quota failures",
            "disposition": "no_go_cross_format_envelopes_wrongly_accepted",
            "accepted_as_final": False,
        },
        "commits": [
            {
                "commit": REJECTED_ACCELERATOR_COMMIT,
                "tree": REJECTED_ACCELERATOR_TREE,
                "purpose": "defer nested Grok quota failures",
            },
            {
                "commit": FINAL_ACCELERATOR_COMMIT,
                "tree": FINAL_ACCELERATOR_TREE,
                "purpose": "bind Grok quota envelopes to their declared format",
            },
        ],
        "final_commit": FINAL_ACCELERATOR_COMMIT,
        "final_tree": FINAL_ACCELERATOR_TREE,
        "changed_files": [
            {
                "path": "ipfs_accelerate_py/agent_supervisor/todo_daemon/legacy_landed_provider_cli.py",
                "sha256": "sha256:1eddea0eab9b176eedbf9e76e949b5c9677c9feb0da8bd3963577d64b71ad4e9",
                "git_blob": "0de3b9957277c5fc7476e9f7a68e3b034d280bd3",
            },
            {
                "path": "test/api/test_agent_supervisor_legacy_landed_review.py",
                "sha256": "sha256:dfae9673cbfa053a6dcbef151a636cb2ed344809a85e21c015c7697107324d5a",
                "git_blob": "ad04485d8f86662cffbc9a24637dcdf543d2e13c",
            },
            {
                "path": "test/api/test_agent_supervisor_native_grok_quota_signal.py",
                "sha256": "sha256:8f7274dde092bb59585ea80e32be0f4ea225652b45497b18bab33513626e372a",
                "git_blob": "7823c6e13f0316643031ff956ea37447a0a12f75",
            },
            {
                "path": "test/api/test_agent_supervisor_production_provider_cli.py",
                "sha256": "sha256:7650a91d64a9fbab6636c6a5376e15b6eb5d99520c2cd9c1a0f030226d282d7f",
                "git_blob": "b8e1e297ffc7724afc96bc0996ca9bd1421d617c",
            },
            {
                "path": "test/api/test_agent_supervisor_production_provider_security_regressions.py",
                "sha256": "sha256:b366754da4177e0b3ddb8ee48a1b4051aaa4cfea8d7bfe25861553115079d12e",
                "git_blob": "af0653482be7800953c67c2acd6858af02e6ea8a",
            },
        ],
        "implementation_gates": {
            "disposition": "passed",
            "passed": 149,
            "failed": 0,
            "scope": "quota classification, production provider CLI/security, and legacy landed review",
            "git_diff_check": "passed",
        },
        "independent_review": {
            "disposition": "final_pass_with_baseline_identical_exception",
            "changed_file_tests": {"passed": 98, "failed": 0},
            "broader_tests": {"passed": 59, "failed": 1},
            "sole_broader_failure": {
                "candidate_regression": False,
                "reproduced_at_exact_base_commit": HISTORICAL_R3_ACCELERATOR_COMMIT,
                "result": "identical",
            },
            "custom_negative_matrix": "passed",
            "authority_invariants": "passed",
            "candidate_regressions": 0,
        },
        "qualification_boundary": "provider quota-envelope parsing repair only; does not establish live Grok account capacity or authorize an r4 launch",
    }


def _verify_historical_r3_receipt(
    *,
    goal_count: int,
    errors: list[str],
) -> None:
    """Verify r3 only against its frozen bytes and historical identities."""

    receipt = _load_json_object(
        HISTORICAL_R3_RECEIPT_PATH,
        label="historical PCCE-000 r3 receipt",
        errors=errors,
    )
    if receipt is None:
        return
    if HISTORICAL_R3_RECEIPT_PATH.stat().st_size != 13083:
        errors.append("historical PCCE-000 r3 receipt byte size changed")
    if _file_sha256(HISTORICAL_R3_RECEIPT_PATH) != HISTORICAL_R3_RECEIPT_BYTE_SHA256:
        errors.append("historical PCCE-000 r3 receipt bytes changed")
    if _git("hash-object", str(HISTORICAL_R3_RECEIPT_PATH)) != HISTORICAL_R3_RECEIPT_GIT_BLOB:
        errors.append("historical PCCE-000 r3 receipt Git blob changed")
    _verify_content_id(
        receipt,
        expected=HISTORICAL_R3_RECEIPT_CONTENT_ID,
        label="historical PCCE-000 r3 receipt",
        errors=errors,
    )
    fixed = {
        "schema": "proof-carrying-context-engine/task-receipt@1",
        "task_id": "PCCE-000",
        "objective_id": OBJECTIVE_ID,
        "board_namespace": BOARD_NAMESPACE,
        "status": "completed",
        "artifact_identity": HISTORICAL_R3_ARTIFACT_IDENTITY,
        "control_base": "8abaa5af47743b0d3d3258adfbbb76d9898e1c70",
    }
    for field, expected in fixed.items():
        if receipt.get(field) != expected:
            errors.append(f"historical PCCE-000 r3 receipt {field} mismatch")
    if receipt.get("parser_report") != _expected_parser_report(goal_count):
        errors.append("historical PCCE-000 r3 parser_report changed")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", R3_CONTROL_COMMIT, "HEAD"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode != 0:
        errors.append("historical r3 control commit is not an ancestor of control HEAD")


def _verify_r3_incident(*, errors: list[str]) -> None:
    incident = _load_json_object(R3_INCIDENT_PATH, label="scheduler-r3 incident", errors=errors)
    if incident is None:
        return
    if R3_INCIDENT_PATH.stat().st_size != 111153:
        errors.append("scheduler-r3 incident byte size changed")
    if _file_sha256(R3_INCIDENT_PATH) != R3_INCIDENT_FILE_SHA256:
        errors.append("scheduler-r3 incident bytes changed")
    if _git("hash-object", str(R3_INCIDENT_PATH)) != R3_INCIDENT_GIT_BLOB:
        errors.append("scheduler-r3 incident Git blob changed")
    _verify_content_id(
        incident,
        expected=R3_INCIDENT_CONTENT_ID,
        label="scheduler-r3 incident",
        errors=errors,
    )
    fixed = {
        "schema": "proof-carrying-context-engine/control-incident@1",
        "incident_id": R3_INCIDENT_IDENTITY,
        "status": "preserved_infrastructure_failure",
        "source_control_commit": R3_CONTROL_COMMIT,
        "source_control_tree": R3_CONTROL_TREE,
    }
    for field, expected in fixed.items():
        if incident.get(field) != expected:
            errors.append(f"scheduler-r3 incident {field} mismatch")

    accounting = (incident.get("task_state_accounting") or {}).get("accounting_totals") or {}
    expected_accounting = {
        "outer_coordination_claims": 2,
        "outer_coordination_leases": 2,
        "outer_coordination_receipts": 2,
        "outer_cancelled_receipts": 2,
        "internal_provider_attempts": 6,
        "internal_failed_attempts": 6,
        "internal_attempts_by_task": {
            "PCCE-001": 3,
            "PCCE-002": 0,
            "PCCE-003": 3,
            "PCCE-004": 0,
        },
        "internal_retries": 4,
        "raw_model_commands": 0,
        "model_response_bytes": 0,
        "source_changes": 0,
        "commits": 0,
        "merges": 0,
        "validations_attempted": 0,
        "product_tasks_completed": 0,
    }
    if accounting != expected_accounting:
        errors.append("scheduler-r3 incident task accounting changed")
    partial = incident.get("partial_effects") or {}
    for field in (
        "source_repository_mutated",
        "submodule_source_mutated",
        "new_source_commit_created",
        "model_response_recorded",
        "patch_generated",
        "validation_run",
        "merge_attempted",
        "product_task_completed",
    ):
        if partial.get(field) is not False:
            errors.append(f"scheduler-r3 incident partial effect mismatch: {field}")
    stop = incident.get("stop_semantics") or {}
    if (
        stop.get("scheduler_restart_performed") is not False
        or stop.get("scheduler_resume_performed") is not False
        or stop.get("PCCE-002_started") is not False
        or stop.get("PCCE-004_started") is not False
    ):
        errors.append("scheduler-r3 incident stop semantics changed")
    diagnosis = incident.get("post_stop_diagnosis") or {}
    capacity = diagnosis.get("capacity_semantics") or {}
    if (
        capacity.get("budget_source")
        != "operator-admission-budget-not-provider-reported-quota"
        or capacity.get("healthy_snapshot_proved_account_capacity") is not False
    ):
        errors.append("scheduler-r3 incident capacity semantics changed")


def _verify_historical_r4_receipt(*, goal_count: int, errors: list[str]) -> None:
    """Verify the blocked r4 control receipt only against frozen evidence."""

    receipt = _load_json_object(
        HISTORICAL_R4_RECEIPT_PATH,
        label="historical PCCE-000 r4 receipt",
        errors=errors,
    )
    if receipt is None:
        return
    if HISTORICAL_R4_RECEIPT_PATH.stat().st_size != 11340:
        errors.append("historical PCCE-000 r4 receipt byte size changed")
    if _file_sha256(HISTORICAL_R4_RECEIPT_PATH) != HISTORICAL_R4_RECEIPT_BYTE_SHA256:
        errors.append("historical PCCE-000 r4 receipt bytes changed")
    if _git("hash-object", str(HISTORICAL_R4_RECEIPT_PATH)) != HISTORICAL_R4_RECEIPT_GIT_BLOB:
        errors.append("historical PCCE-000 r4 receipt Git blob changed")
    _verify_content_id(
        receipt,
        expected=HISTORICAL_R4_RECEIPT_CONTENT_ID,
        label="historical PCCE-000 r4 receipt",
        errors=errors,
    )
    fixed = {
        "schema": "proof-carrying-context-engine/task-receipt@1",
        "task_id": "PCCE-000",
        "objective_id": OBJECTIVE_ID,
        "board_namespace": BOARD_NAMESPACE,
        "status": "blocked_external_prerequisite",
        "artifact_identity": HISTORICAL_R4_ARTIFACT_IDENTITY,
        "control_base": R3_INCIDENT_COMMIT,
    }
    for field, expected in fixed.items():
        if receipt.get(field) != expected:
            errors.append(f"historical PCCE-000 r4 receipt {field} mismatch")
    if receipt.get("parser_report") != _expected_parser_report(goal_count):
        errors.append("historical PCCE-000 r4 parser_report changed")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", R4_CONTROL_COMMIT, "HEAD"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode != 0:
        errors.append("historical r4 control commit is not an ancestor of control HEAD")


def _expected_account_capacity_probe() -> dict[str, Any]:
    return {
        "gate_id": "fresh_exact_grok_account_capacity_gate",
        "mode": "production_adapter",
        "completed_no_later_than": "2026-08-14T19:11:43Z",
        "elapsed_seconds": 5.817397392,
        "provider": "grok_cli",
        "model": "grok-4.5",
        "adapter_gitlink": FINAL_ACCELERATOR_COMMIT,
        "production_adapter_function": "_grok_native_structured_output",
        "executable": {
            "command_path": "/home/barberb/.local/bin/grok",
            "resolved_path": "/home/barberb/.grok/downloads/grok-1.0.3-linux-aarch64",
            "version": "grok 1.0.3 (1a29d5bc12) [stable]",
            "sha256": "sha256:ed44950eab90573b6f475191f5791713a56943939b3b9a62e3f4e95edd14acd9",
        },
        "exit_code": 0,
        "usable_structured_success": True,
        "result_class": "live",
        "replayed": False,
        "simulated": False,
        "exact_argv_digest_retained": False,
        "admission_authority": False,
        "endpoint_receipt_cid": "baguqeerajjm5ujcdwpirsajmir5ueyol54rwr36jyszxlwk4vgpvbalfyodq",
        "response_sha256": "sha256:31bf75f4c0a97cc1f7b60df824fa390b3be9ba014f29b63c87c698ba63d9a9fd",
        "raw_response_retained_in_control_receipt": False,
        "credential_material_retained": False,
        "prompt": {
            "byte_size": 48,
            "sha256": "sha256:9fea71a71cf8c33fcc9c150cc830e4ac50232233acfe182c5937221bc6a9dc54",
            "raw_retained": False,
        },
        "canonical_schema": {
            "byte_size": 127,
            "sha256": "sha256:a9bb57e4f7f0dd09183bdf6cd6d0915c2d81b4bd37d4b27b48a2030ef34e5afe",
        },
        "operator_capacity_snapshot_used_as_account_evidence": False,
    }


def _expected_post_commit_probe_policy() -> dict[str, Any]:
    return {
        "max_ttl_seconds": 60,
        "required_time_order": (
            "started_at <= completed_at <= receipt_created_at <= launch_exec_at <= expires_at"
        ),
        "expiry_bound": "expires_at - completed_at <= ttl_seconds <= 60",
        "required_adapter_gitlink": FINAL_ACCELERATOR_COMMIT,
        "required_provider_policy": "grok-implement-codex-independent-review",
        "exact_bindings": [
            "argv_sha256",
            "executable_path",
            "executable_version",
            "executable_sha256",
            "adapter_gitlink",
            "provider",
            "model",
            "endpoint_receipt_cid",
            "response_sha256",
        ],
        "result_requirements": {
            "exit_code": 0,
            "usable_structured_success": True,
            "result_class": "live",
            "replayed": False,
            "simulated": False,
        },
        "enforced_at": [
            "external_launch_receipt_creation",
            "immediately_before_launch_exec",
        ],
    }


def _verify_active_r5_receipt(
    *,
    config: dict[str, Any],
    projection: dict[str, Any],
    graph: dict[str, Any],
    bundle_index: dict[str, Any],
    goal_count: int,
    errors: list[str],
) -> None:
    receipt = _load_json_object(ACTIVE_R5_RECEIPT_PATH, label="active PCCE-000 r5 receipt", errors=errors)
    if receipt is None:
        return
    if not PROFILE_G_BOOTSTRAP_RECEIPT_PATH.is_file():
        errors.append("Profile-G bootstrap receipt is missing")
        return
    _verify_content_id(receipt, expected=None, label="active PCCE-000 r5 receipt", errors=errors)
    fixed = {
        "schema": "proof-carrying-context-engine/task-receipt@1",
        "task_id": "PCCE-000",
        "objective_id": OBJECTIVE_ID,
        "board_namespace": BOARD_NAMESPACE,
        "status": "pending_external_launch_receipt",
        "artifact_identity": ACTIVE_R5_ARTIFACT_IDENTITY,
        "control_base": R4_CONTROL_COMMIT,
        "control_base_tree": R4_CONTROL_TREE,
    }
    for field, expected in fixed.items():
        if receipt.get(field) != expected:
            errors.append(f"active PCCE-000 r5 receipt {field} mismatch")
    expected_supersedes = {
        "artifact_identity": HISTORICAL_R4_ARTIFACT_IDENTITY,
        "path": str(HISTORICAL_R4_RECEIPT_PATH.relative_to(REPO_ROOT)),
        "content_id": HISTORICAL_R4_RECEIPT_CONTENT_ID,
        "byte_sha256": HISTORICAL_R4_RECEIPT_BYTE_SHA256,
        "git_blob": HISTORICAL_R4_RECEIPT_GIT_BLOB,
        "control_commit": R4_CONTROL_COMMIT,
        "control_tree": R4_CONTROL_TREE,
        "rewrite_allowed": False,
    }
    if receipt.get("supersedes") != expected_supersedes:
        errors.append("active PCCE-000 r5 supersession binding mismatch")

    evidence = receipt.get("evidence")
    if not isinstance(evidence, dict):
        errors.append("active PCCE-000 r5 receipt evidence must be an object")
        return
    repository_gitlinks = {
        name: str(record.get("gitlink") or "")
        for name, record in sorted(projection["repository_identity"]["repositories"].items())
    }
    expected_evidence = {
        "objective_sha256": projection["source"]["objective_sha256"],
        "todo_sha256": projection["source"]["todo_sha256"],
        "plan_sha256": _file_sha256(PLAN_PATH),
        "config_sha256": _file_sha256(CONFIG_PATH),
        "validator_sha256": _file_sha256(Path(__file__)),
        "profile_g_bootstrap_sha256": _file_sha256(PROFILE_G_BOOTSTRAP_RECEIPT_PATH),
        "board_projection_id": projection["projection_id"],
        "dependency_graph_id": graph["graph_id"],
        "bundle_index_id": bundle_index["projection_id"],
        "repository_gitlinks": repository_gitlinks,
        "protected_paths": sorted(str(item) for item in config["protected_paths"]),
        "task_set": {
            "task_count": len(EXPECTED_TASK_IDS),
            "ordered_task_ids_sha256": _sha256_json(list(EXPECTED_TASK_IDS)),
        },
        "provider_route_repair_ref": {
            "receipt_artifact_identity": HISTORICAL_R4_ARTIFACT_IDENTITY,
            "receipt_path": str(HISTORICAL_R4_RECEIPT_PATH.relative_to(REPO_ROOT)),
            "receipt_content_id": HISTORICAL_R4_RECEIPT_CONTENT_ID,
            "json_pointer": "/evidence/provider_route_repair",
            "final_commit": FINAL_ACCELERATOR_COMMIT,
            "final_tree": FINAL_ACCELERATOR_TREE,
        },
        "account_capacity_probe": _expected_account_capacity_probe(),
        "frozen_history": {
            "r2_receipt_byte_sha256": HISTORICAL_R2_RECEIPT_BYTE_SHA256,
            "r2_incident_file_sha256": R2_INCIDENT_FILE_SHA256,
            "r3_receipt_byte_sha256": HISTORICAL_R3_RECEIPT_BYTE_SHA256,
            "r3_incident_file_sha256": R3_INCIDENT_FILE_SHA256,
            "r4_receipt_byte_sha256": HISTORICAL_R4_RECEIPT_BYTE_SHA256,
            "r4_receipt_content_id": HISTORICAL_R4_RECEIPT_CONTENT_ID,
        },
    }
    for field, expected in expected_evidence.items():
        if evidence.get(field) != expected:
            errors.append(f"active PCCE-000 r5 evidence mismatch: {field}")
    if repository_gitlinks.get("accelerate") != FINAL_ACCELERATOR_COMMIT:
        errors.append("active PCCE-000 r5 accelerator gitlink is not the reviewed repair pin")
    if receipt.get("parser_report") != _expected_parser_report(goal_count):
        errors.append("active PCCE-000 r5 parser_report mismatch")

    expected_restart = {
        "generation": "r5",
        "scheduler_state_root": str(REPLACEMENT_STATE_ROOT / "scheduler-r5"),
        "worktree_root": str(REPLACEMENT_STATE_ROOT / "worktrees-r5"),
        "log_root": str(REPLACEMENT_STATE_ROOT / "logs-r5"),
        "external_launch_receipt_path": str(
            REPLACEMENT_STATE_ROOT / "scheduler-r5" / "control-launch-receipt.json"
        ),
        "fresh_claims_leases_fences_review_authority_and_receipts": True,
        "resume_scheduler_r2": False,
        "resume_scheduler_r3": False,
        "resume_scheduler_r4": False,
        "reuse_scheduler_r2_state": False,
        "reuse_scheduler_r3_state": False,
        "reuse_scheduler_r4_state": False,
        "reuse_scheduler_r2_claims_leases_fences_or_receipts": False,
        "reuse_scheduler_r3_claims_leases_fences_or_receipts": False,
        "reuse_scheduler_r4_claims_leases_fences_or_receipts": False,
        "preserve_scheduler_r2_forensics_read_only": True,
        "preserve_scheduler_r3_forensics_read_only": True,
        "preserve_scheduler_r4_forensics_read_only": True,
    }
    if receipt.get("restart_policy") != expected_restart:
        errors.append("active PCCE-000 r5 restart policy mismatch")
    expected_launch_gate = {
        "id": "fresh_exact_grok_account_capacity_gate",
        "required": True,
        "status": "passed",
        "evidence_source": (
            "fresh production-adapter structured probe (non-authoritative preparation evidence)"
        ),
        "capacity_semantics": "operator-admission-budget-not-provider-reported-quota",
        "capacity_snapshot_satisfies_gate": False,
        "probe_evidence_ref": "evidence.account_capacity_probe",
        "external_launch_receipt_path": str(
            REPLACEMENT_STATE_ROOT / "scheduler-r5" / "control-launch-receipt.json"
        ),
        "external_launch_receipt_created": False,
        "external_launch_receipt_creation_permitted": True,
        "live_launch_permitted": False,
        "control_probe_admission_authority": False,
        "external_launch_receipt_requires_second_fresh_exact_probe": True,
        "post_commit_probe_required_fields": [
            "started_at",
            "completed_at",
            "argv_sha256",
            "executable_identity",
            "live_not_replayed_or_simulated",
            "ttl_seconds",
            "expires_at",
        ],
        "post_commit_probe_policy": _expected_post_commit_probe_policy(),
        "product_task_completion_authority": False,
        "post_commit_receipt_must_bind": [
            "final_r5_control_commit",
            "final_r5_control_tree",
            "recursive_repository_gitlinks",
            "nested_repository_heads",
            "clean_worktree_evidence",
            "active_r5_receipt_content_id",
            "board_projection_id",
            "dependency_graph_id",
            "bundle_index_id",
            "operator_identity",
            "provider_policy",
            "control_preparation_probe_identity",
            "post_commit_fresh_exact_grok_probe",
            "fresh_operator_admission_capacity_snapshot_identity",
            "operator_admission_snapshot_not_provider_account_evidence",
            "dry_run_command_argv_sha256",
            "dry_run_result_identity",
            "scheduler_launch_argv_contract_version",
            "exact_scheduler_launch_argv_sha256",
            "fresh_review_authority",
            "scheduler_r5_paths",
            "single_lane_admission",
        ],
        "scheduler_process_identity_must_match_prebound_launch_argv": True,
    }
    if receipt.get("external_launch_gate") != expected_launch_gate:
        errors.append("active PCCE-000 r5 external launch gate mismatch")
    expected_decision = {
        "control_revision_commit_authorized": True,
        "accelerator_candidate_audit": "final_pass",
        "account_capacity_gate": "passed",
        "external_launch_receipt_creation_authorized": True,
        "external_launch_receipt_created": False,
        "live_launch_authorized": False,
        "launch_blocker": "external_launch_receipt",
        "qualification": "conditional_go_control_revision_only",
    }
    if receipt.get("control_decision") != expected_decision:
        errors.append("active PCCE-000 r5 control decision mismatch")


def _verify_control_revision_config(config: dict[str, Any], errors: list[str]) -> None:
    expected = {
        "active_revision": "r5",
        "active_receipt_path": str(ACTIVE_R5_RECEIPT_PATH.relative_to(REPO_ROOT)),
        "historical_receipt_paths": [
            str(HISTORICAL_R2_RECEIPT_PATH.relative_to(REPO_ROOT)),
            str(HISTORICAL_R3_RECEIPT_PATH.relative_to(REPO_ROOT)),
            str(HISTORICAL_R4_RECEIPT_PATH.relative_to(REPO_ROOT)),
        ],
        "preserved_incident_paths": [
            str(R2_INCIDENT_PATH.relative_to(REPO_ROOT)),
            str(R3_INCIDENT_PATH.relative_to(REPO_ROOT)),
        ],
        "historical_receipt_rewrite_allowed": False,
        "incident_rewrite_allowed": False,
        "status": "pending_external_launch_receipt",
        "blocking_prerequisite": "external_launch_receipt",
        "admission_head_binding": "external-launch-receipt-after-r5-control-commit",
        "external_launch_receipt_required": True,
        "external_launch_receipt_creation_permitted": True,
        "external_launch_receipt_must_bind_final_control_head": True,
    }
    if config.get("control_revision") != expected:
        errors.append("control_revision config mismatch")
    source = config.get("source_binding") or {}
    if source.get("ipfs_accelerate_planning_revision") != FINAL_ACCELERATOR_COMMIT:
        errors.append("accelerator planning revision is not the independently reviewed r4 repair pin")
    if (config.get("repositories") or {}).get("accelerate", {}).get("initial_commit") != "485edc0871c55b0e2ef21d83bece9fa12c2c8d84":
        errors.append("accelerator initial inventory identity must remain unchanged")
    recovery = config.get("recovery") or {}
    expected_recovery = {
        "replacement_generation": "r5",
        "replacement_scheduler_state_root": str(REPLACEMENT_STATE_ROOT / "scheduler-r5"),
        "replacement_worktree_root": str(REPLACEMENT_STATE_ROOT / "worktrees-r5"),
        "replacement_log_root": str(REPLACEMENT_STATE_ROOT / "logs-r5"),
        "external_launch_receipt_path": str(
            REPLACEMENT_STATE_ROOT / "scheduler-r5" / "control-launch-receipt.json"
        ),
        "launch_status": "pending_external_launch_receipt",
        "launch_permitted": False,
        "provider_capacity_gate_status": "passed",
        "required_prelaunch_gate": "external_launch_receipt",
        "reuse_scheduler_r2_state": False,
        "reuse_scheduler_r2_claims_leases_fences_or_receipts": False,
        "preserve_scheduler_r2_forensics_read_only": True,
        "reuse_scheduler_r3_state": False,
        "reuse_scheduler_r3_worktrees": False,
        "reuse_scheduler_r3_logs": False,
        "reuse_scheduler_r3_claims_leases_fences_or_receipts": False,
        "preserve_scheduler_r3_forensics_read_only": True,
        "reuse_scheduler_r4_state": False,
        "reuse_scheduler_r4_worktrees": False,
        "reuse_scheduler_r4_logs": False,
        "reuse_scheduler_r4_claims_leases_fences_or_receipts": False,
        "preserve_scheduler_r4_forensics_read_only": True,
    }
    for field, expected_value in expected_recovery.items():
        if recovery.get(field) != expected_value:
            errors.append(f"r5 recovery policy mismatch: {field}")
    bundle = config.get("bundle_scheduler") or {}
    launch_gate = bundle.get("launch_gate") or {}
    expected_launch_gate = {
        "id": "fresh_exact_grok_account_capacity_gate",
        "status": "passed",
        "required": True,
        "evidence_source": (
            "fresh production-adapter structured probe (non-authoritative preparation evidence)"
        ),
        "last_observed_provider_result": "usable_structured_success",
        "capacity_snapshot_satisfies_gate": False,
        "probe_completed_no_later_than": "2026-08-14T19:11:43Z",
        "external_launch_receipt_creation_permitted": True,
        "external_launch_receipt_created": False,
        "live_launch_permitted": False,
        "control_probe_admission_authority": False,
        "external_launch_receipt_requires_second_fresh_exact_probe": True,
        "post_commit_probe_required_fields": [
            "started_at",
            "completed_at",
            "argv_sha256",
            "executable_identity",
            "live_not_replayed_or_simulated",
            "ttl_seconds",
            "expires_at",
        ],
        "post_commit_probe_policy": _expected_post_commit_probe_policy(),
        "post_commit_receipt_must_bind": [
            "final_r5_control_commit",
            "final_r5_control_tree",
            "recursive_repository_gitlinks",
            "nested_repository_heads",
            "clean_worktree_evidence",
            "active_r5_receipt_content_id",
            "board_projection_id",
            "dependency_graph_id",
            "bundle_index_id",
            "operator_identity",
            "provider_policy",
            "control_preparation_probe_identity",
            "post_commit_fresh_exact_grok_probe",
            "fresh_operator_admission_capacity_snapshot_identity",
            "operator_admission_snapshot_not_provider_account_evidence",
            "dry_run_command_argv_sha256",
            "dry_run_result_identity",
            "scheduler_launch_argv_contract_version",
            "exact_scheduler_launch_argv_sha256",
            "fresh_review_authority",
            "scheduler_r5_paths",
            "single_lane_admission",
        ],
        "scheduler_process_identity_must_match_prebound_launch_argv": True,
    }
    if (
        bundle.get("provider_capacity_semantics")
        != "operator-admission-budget-not-provider-reported-quota"
        or bundle.get("provider_capacity_snapshot_is_account_capacity_evidence") is not False
        or launch_gate != expected_launch_gate
    ):
        errors.append("r5 provider-capacity launch gate mismatch")
    lanes = config.get("lanes") or []
    if (
        config.get("max_lanes") != 1
        or len(lanes) != 1
        or lanes[0].get("index") != 0
        or lanes[0].get("name") != "pcce-lane-0"
        or lanes[0].get("strict_shard_remainder") != 0
        or lanes[0].get("initial_focus") != "serialized-four-repository-inventory"
        or sorted(lanes[0].get("initial_task_ids") or [])
        != ["PCCE-001", "PCCE-002", "PCCE-003", "PCCE-004"]
        or (config.get("provider") or {}).get("max_concurrency") != 1
        or bundle.get("maximum_lane_count") != 1
        or bundle.get("max_cpu_proof_concurrency") != 1
        or bundle.get("max_model_concurrency") != 1
        or bundle.get("max_artifact_concurrency") != 1
    ):
        errors.append("r5 single-lane admission policy mismatch")


def validate(*, output_dir: Path, write: bool) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    try:
        configured_board = load_configured_board(CONFIG_PATH, repo_root=REPO_ROOT)
    except ConfiguredBoardError as exc:
        errors.append(f"configured-board profile is invalid: {exc}")
        configured_board = None
    tasks = parse_task_file(TODO_PATH, TASK_PREFIX)
    goals = parse_goal_heap(OBJECTIVE_PATH.read_text(encoding="utf-8"))

    task_headings = _headings(TODO_PATH, TASK_PREFIX)
    duplicate_tasks = sorted(task_id for task_id, count in Counter(task_headings).items() if count != 1)
    if duplicate_tasks:
        errors.append(f"duplicate task headings: {duplicate_tasks}")
    if task_headings != EXPECTED_TASK_IDS:
        errors.append("task population/order differs from the sealed PCCE v0.1 board")

    goal_headings = _headings(OBJECTIVE_PATH, "## PCCE-G")
    duplicate_goals = sorted(goal_id for goal_id, count in Counter(goal_headings).items() if count != 1)
    if duplicate_goals:
        errors.append(f"duplicate goal headings: {duplicate_goals}")
    if goal_headings != EXPECTED_GOAL_IDS:
        errors.append("goal population/order differs from PCCE-G000 plus Epic A-H")

    task_by_id = {task.task_id: task for task in tasks}
    goal_ids = {goal.goal_id for goal in goals}
    dependencies: dict[str, list[str]] = {}
    path_owners: dict[str, list[str]] = defaultdict(list)
    projected_tasks: list[dict[str, Any]] = []

    protected = set(config["protected_paths"])
    for task_id in EXPECTED_TASK_IDS:
        task = task_by_id.get(task_id)
        if task is None:
            errors.append(f"missing parsed task: {task_id}")
            continue
        metadata = {str(key).lower(): str(value) for key, value in task.metadata.items()}
        missing_fields = sorted(REQUIRED_METADATA.difference(metadata))
        if missing_fields:
            errors.append(f"{task_id} missing fields: {missing_fields}")
        if task.status not in ALLOWED_TASK_STATUSES:
            errors.append(f"{task_id} unsupported status: {task.status}")
        if task_id == "PCCE-000" and task.status != "completed":
            errors.append("PCCE-000 must remain completed after the control-plane seal")
        if task_id != "PCCE-000" and task.status == "completed" and not metadata.get(
            "final result cid or artifact identity", ""
        ).strip():
            errors.append(f"{task_id} is completed without a final artifact identity")
        if task.board_namespace != BOARD_NAMESPACE:
            errors.append(f"{task_id} has wrong board namespace: {task.board_namespace}")
        owner = metadata.get("owning repository", "")
        if owner not in ALLOWED_REPOSITORIES:
            errors.append(f"{task_id} has unsupported owning repository: {owner}")
        goal_id = metadata.get("goal id", "")
        if goal_id not in goal_ids:
            errors.append(f"{task_id} references unknown goal: {goal_id}")
        if not task.outputs:
            errors.append(f"{task_id} has no Outputs")
        predicted = split_csv(metadata.get("predicted files", ""))
        owned = split_csv(metadata.get("owned paths", ""))
        allowed = split_csv(metadata.get("allowed paths", ""))
        if not predicted:
            errors.append(f"{task_id} has no Predicted files")
        if set(task.outputs).difference(predicted):
            errors.append(f"{task_id} Outputs are not all repeated in Predicted files")
        if set(predicted).difference(owned):
            errors.append(f"{task_id} Predicted files are not all repeated in Owned paths")
        if allowed and set(predicted).difference(allowed):
            errors.append(f"{task_id} Predicted files are not all repeated in Allowed paths")
        if task_id != "PCCE-000" and protected.intersection(predicted):
            errors.append(f"{task_id} owns protected operator inputs: {sorted(protected.intersection(predicted))}")
        for path in predicted:
            path_owners[path].append(task_id)
        unknown_dependencies = sorted(set(task.depends_on).difference(task_by_id))
        if unknown_dependencies:
            errors.append(f"{task_id} has unknown dependencies: {unknown_dependencies}")
        if task_id in task.depends_on:
            errors.append(f"{task_id} depends on itself")
        dependencies[task_id] = list(task.depends_on)
        projected_tasks.append(
            {
                "task_id": task.task_id,
                "canonical_task_key": task.canonical_task_key,
                "canonical_task_cid": task.canonical_task_cid,
                "title": task.title,
                "status": task.status,
                "goal_id": goal_id,
                "owning_repository": owner,
                "dependencies": list(task.depends_on),
                "outputs": list(task.outputs),
                "predicted_files": predicted,
                "metadata": dict(sorted(metadata.items())),
            }
        )

    exact_path_conflicts = {
        path: owners
        for path, owners in sorted(path_owners.items())
        if len(owners) > 1 and owners != ["PCCE-000"]
    }
    if exact_path_conflicts:
        warnings.append(
            "serialized tasks share exact paths; dependency/conflict admission must prevent overlap: "
            + json.dumps(exact_path_conflicts, sort_keys=True)
        )

    ordered = _topological_order(EXPECTED_TASK_IDS, dependencies)
    if len(ordered) != len(EXPECTED_TASK_IDS):
        errors.append("task dependency graph contains a cycle")
    if ordered and ordered[-1] != "PCCE-083":
        errors.append("PCCE-083 must be the unique terminal task")

    identity = _repository_identity(config, errors)
    projection: dict[str, Any] = {
        "schema": "ipfs_accelerate_py.agent_supervisor.derived-task-board-projection@1",
        "authoritative": False,
        "authority_note": "The Markdown objective heap, todo board, leases, receipts, validations, and merge evidence remain authoritative.",
        "objective_id": OBJECTIVE_ID,
        "board_namespace": BOARD_NAMESPACE,
        "source": {
            "objective_path": str(OBJECTIVE_PATH.relative_to(REPO_ROOT)),
            "todo_path": str(TODO_PATH.relative_to(REPO_ROOT)),
            "config_path": str(CONFIG_PATH.relative_to(REPO_ROOT)),
            "objective_sha256": "sha256:" + hashlib.sha256(OBJECTIVE_PATH.read_bytes()).hexdigest(),
            "todo_sha256": "sha256:" + hashlib.sha256(TODO_PATH.read_bytes()).hexdigest(),
        },
        "repository_identity": identity,
        "task_count": len(projected_tasks),
        "tasks": projected_tasks,
        "dependency_edges": [
            {"from": dependency, "to": task_id}
            for task_id in EXPECTED_TASK_IDS
            for dependency in dependencies.get(task_id, [])
        ],
        "topological_order": ordered,
        "warnings": warnings,
    }
    projection["projection_id"] = _sha256_json(projection)
    graph = {
        "schema": "ipfs_accelerate_py.agent_supervisor.derived-task-dependency-graph@1",
        "objective_id": OBJECTIVE_ID,
        "board_projection_id": projection["projection_id"],
        "nodes": EXPECTED_TASK_IDS,
        "edges": projection["dependency_edges"],
        "topological_order": ordered,
    }
    graph["graph_id"] = _sha256_json(graph)
    bundle_index = _bundle_index_projection(
        projected_tasks,
        config=config,
        source_sha256=projection["source"]["todo_sha256"],
    )
    _verify_control_revision_config(config, errors)
    _verify_historical_r2_receipt(goal_count=len(goals), errors=errors)
    _verify_r2_incident(errors=errors)
    _verify_historical_r3_receipt(goal_count=len(goals), errors=errors)
    _verify_r3_incident(errors=errors)
    _verify_historical_r4_receipt(goal_count=len(goals), errors=errors)
    _verify_active_r5_receipt(
        config=config,
        projection=projection,
        graph=graph,
        bundle_index=bundle_index,
        goal_count=len(goals),
        errors=errors,
    )

    if write and not errors:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "task_board.json").write_text(
            json.dumps(projection, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (output_dir / "task_dependency_graph.json").write_text(
            json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        write_bundle_index_artifact(output_dir / "bundle_index.json", bundle_index)

    return {
        "valid": not errors,
        "schema": "ipfs_accelerate_py.agent_supervisor.board-validation-result@1",
        "objective_id": OBJECTIVE_ID,
        "board_namespace": BOARD_NAMESPACE,
        "task_count": len(projected_tasks),
        "goal_count": len(goals),
        "projection_id": projection["projection_id"],
        "graph_id": graph["graph_id"],
        "bundle_index_id": bundle_index["projection_id"],
        "configured_board_valid": configured_board is not None,
        "output_dir": str(output_dir),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-all", action="store_true", help="Validate the sealed full board")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--write", action="store_true", help="Update derived JSON/query projections after validation")
    parser.add_argument("--no-write", action="store_true", help="Deprecated explicit read-only validation flag")
    args = parser.parse_args()
    if args.write and args.no_write:
        parser.error("--write and --no-write are mutually exclusive")
    result = validate(output_dir=args.output_dir.resolve(), write=args.write)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

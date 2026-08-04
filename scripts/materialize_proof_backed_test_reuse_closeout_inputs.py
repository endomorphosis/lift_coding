#!/usr/bin/env python3
"""Honest closeout-input materialization probe for proof-backed test reuse.

This script collects *real* retained inputs for the PTR-110 → PTR-122 sequence
and writes a non-authoritative materialization report under the state-root
projection directory. It never:

* synthesizes managed-merge receipts
* invents operator approvals
* writes a final current-tree gate decision as if complete
* mutates protected board/objective/config files

It does:

* capture checkout identity and supervisor health
* run the board validator
* inventory merge-queue candidates (presence only)
* attempt forest materialization for the three package roots
* run ProofTestReuseTaskEvidenceCollector when identity fields are available
* re-run report-only closeout diagnosis and record remaining input groups
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEL_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
KIT_ROOT = REPO_ROOT / "external" / "ipfs_kit"
TODO_REL = "implementation_plan/docs/46-proof-backed-test-reuse.todo.md"
OBJECTIVE_REL = "implementation_plan/docs/46-proof-backed-test-reuse.objectives.md"
CONFIG_PATH = REPO_ROOT / "config" / "proof_backed_test_reuse_supervisor.json"
STATE_ROOT = Path(
    os.environ.get(
        "IPFS_ACCELERATE_PROOF_REUSE_STATE_ROOT",
        str(Path.home() / ".local" / "state" / "ipfs_accelerate_py" / "proof-backed-test-reuse-v1"),
    )
)
OUT_DIR = STATE_ROOT / "projection" / "completion" / "materialization"
MERGE_COMPLETED = STATE_ROOT / "merge-queue" / "completed"
VALIDATION_RECEIPT_DIR = STATE_ROOT / "projection" / "completion" / "validation_receipts"


def _run_json(command: list[str]) -> tuple[int, Any, str]:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    payload: Any
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {
            "stdout": result.stdout[-8000:],
            "stderr": result.stderr[-4000:],
        }
    return result.returncode, payload, result.stderr


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _checkout_identity() -> dict[str, Any]:
    dirty = bool(_git("status", "--porcelain"))
    return {
        "branch": _git("branch", "--show-current"),
        "commit": _git("rev-parse", "HEAD"),
        "tree": _git("rev-parse", "HEAD^{tree}"),
        "clean": not dirty,
        "dirty_detail": _git("status", "--short") if dirty else "",
        "accelerator": _git("-C", str(ACCEL_ROOT), "rev-parse", "HEAD"),
        "datasets": _git("-C", str(DATASETS_ROOT), "rev-parse", "HEAD"),
        "kit": _git("-C", str(KIT_ROOT), "rev-parse", "HEAD"),
    }


def _materialize_forest() -> dict[str, Any]:
    if str(ACCEL_ROOT) not in sys.path:
        sys.path.insert(0, str(ACCEL_ROOT))
    from ipfs_accelerate_py.agent_supervisor.repository_forest_manifest import (
        materialize_initial_four_repository_forest,
    )

    # Swissknife is optional for this three-package program; allow missing.
    swiss = REPO_ROOT / "swissknife"
    if not swiss.is_dir():
        swiss = REPO_ROOT
    try:
        result = materialize_initial_four_repository_forest(
            swissknife_root=swiss,
            accelerator_root=ACCEL_ROOT,
            kit_root=KIT_ROOT,
            datasets_root=DATASETS_ROOT,
            require_all_four=False,
            fail_on_missing_required=False,
        )
    except Exception as exc:  # probe only
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

    forest = getattr(result, "forest", None) or getattr(result, "repository_forest", None)
    payload: dict[str, Any] = {
        "ok": True,
        "result_type": type(result).__name__,
        "attrs": sorted(a for a in dir(result) if not a.startswith("_")),
    }
    # Best-effort extract common identity fields without inventing them.
    for name in (
        "forest_cid",
        "forest_id",
        "repository_forest_cid",
        "gitlink_state_cid",
        "gitlink_closure_cid",
        "portable_identity",
        "policy_cid",
        "manifest_cid",
    ):
        if hasattr(result, name):
            payload[name] = getattr(result, name)
        elif forest is not None and hasattr(forest, name):
            payload[name] = getattr(forest, name)
    if forest is not None and hasattr(forest, "to_dict"):
        try:
            payload["forest"] = forest.to_dict()
        except Exception as exc:
            payload["forest_to_dict_error"] = f"{type(exc).__name__}: {exc}"
    if hasattr(result, "to_dict"):
        try:
            payload["materialization"] = result.to_dict()
        except Exception as exc:
            payload["materialization_to_dict_error"] = f"{type(exc).__name__}: {exc}"

    # Normalize identity aliases used by task evidence collectors.
    forest_dict = payload.get("forest") if isinstance(payload.get("forest"), dict) else {}
    forest_cid = (
        payload.get("repository_forest_cid")
        or payload.get("forest_cid")
        or payload.get("forest_id")
        or forest_dict.get("forest_id")
    )
    gitlink = payload.get("gitlink_state_cid") or payload.get("gitlink_closure_cid")
    if not gitlink and isinstance(forest_dict.get("descriptors"), list):
        for desc in forest_dict["descriptors"]:
            if isinstance(desc, dict) and desc.get("gitlink_closure_cid"):
                gitlink = desc.get("gitlink_closure_cid")
                break
    if forest_cid:
        payload["repository_forest_cid"] = str(forest_cid)
    if gitlink:
        payload["gitlink_state_cid"] = str(gitlink)
    return payload


def _load_merge_records() -> list[dict[str, Any]]:
    """Load completed merge-queue rows and project collector-safe merge receipts.

    Raw daemon queue files contain floats and non-canonical nested metadata.
    The task-evidence collector seals merge rows with ``content_identity``, so
    only integer/string fields from the authoritative completion claim are kept.
    This does not invent new completion events — it re-expresses retained
    completed rows in the collector's expected shape.
    """

    if str(ACCEL_ROOT) not in sys.path:
        sys.path.insert(0, str(ACCEL_ROOT))
    from ipfs_accelerate_py.agent_supervisor.proof.formal_verification_contracts import (
        content_identity,
    )

    records: list[dict[str, Any]] = []
    if not MERGE_COMPLETED.is_dir():
        return records
    for path in sorted(MERGE_COMPLETED.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        task_id = str(raw.get("task_id") or "").strip()
        status = str(raw.get("status") or raw.get("state") or "").strip().lower()
        commit = str(
            raw.get("merged_commit_id") or raw.get("commit_sha") or raw.get("commit_id") or ""
        ).strip()
        task_cid = str(
            raw.get("task_cid")
            or raw.get("canonical_task_cid")
            or raw.get("canonical_task_id")
            or ""
        ).strip()
        if not task_id.startswith("PTR-") or status not in {"completed", "merged"}:
            continue
        if not commit or not task_cid:
            continue
        body = {
            "task_id": task_id,
            "canonical_task_cid": task_cid,
            "status": "completed",
            "commit_sha": commit,
            "source_path": str(path.name),
        }
        sealed = {
            **body,
            "merge_receipt_cid": content_identity(body),
        }
        records.append(sealed)
    return records


def _load_validation_receipts() -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    if not VALIDATION_RECEIPT_DIR.is_dir():
        return receipts
    for path in sorted(VALIDATION_RECEIPT_DIR.glob("PTR-*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(raw, dict) and raw.get("task_id"):
            receipts.append(raw)
    return receipts


def _attempt_task_evidence(
    *,
    board: MappingLike,
    checkout: dict[str, Any],
    forest: dict[str, Any],
    merge_records: list[dict[str, Any]],
    validation_receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    if str(ACCEL_ROOT) not in sys.path:
        sys.path.insert(0, str(ACCEL_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        parse_task_file,
    )
    from ipfs_accelerate_py.agent_supervisor.validation.proof_test_reuse_task_evidence import (
        ProofTestReuseTaskEvidenceCollector,
        ProofTestReuseTaskEvidenceError,
    )

    tasks = parse_task_file(REPO_ROOT / TODO_REL, "## PTR-")
    # Identity: only use real forest fields; otherwise report gap.
    forest_cid = str(forest.get("repository_forest_cid") or forest.get("forest_cid") or "")
    gitlink = str(forest.get("gitlink_state_cid") or "")
    if not forest_cid or not gitlink:
        return {
            "ok": False,
            "reason": "forest_identity_incomplete",
            "forest_keys": sorted(forest.keys()),
            "task_count": len(tasks),
            "merge_record_count": len(merge_records),
            "validation_receipt_count": len(validation_receipts),
        }

    dirty = not bool(checkout.get("clean"))
    dirty_overlay = "cid:dirty-overlay:none" if not dirty else "cid:dirty-overlay:present"
    # content-address dirty overlay if dirty using status text
    if dirty:
        digest = hashlib.sha256(str(checkout.get("dirty_detail") or "").encode("utf-8")).hexdigest()
        dirty_overlay = f"baguqeera{digest[:50]}"

    # Prefer identity snapshot written by the receipt retainer when present so
    # collector bindings match sealed receipts exactly.
    identity_snapshot_path = VALIDATION_RECEIPT_DIR / "identity_snapshot.json"
    if identity_snapshot_path.is_file():
        try:
            snap = json.loads(identity_snapshot_path.read_text(encoding="utf-8"))
            identity = snap.get("identity") if isinstance(snap, dict) else None
            if isinstance(identity, dict) and identity.get("repository_forest_cid"):
                forest_cid = str(identity.get("repository_forest_cid") or forest_cid)
                gitlink = str(identity.get("gitlink_state_cid") or gitlink)
                dirty = bool(identity.get("dirty"))
                dirty_overlay = str(identity.get("dirty_overlay_cid") or dirty_overlay)
                repository_id = str(
                    identity.get("repository_id") or "lift_coding/proof-backed-test-reuse"
                )
                repository_state_cid = str(
                    identity.get("repository_state_cid") or f"git-commit:{checkout['commit']}"
                )
                git_commit_id = str(identity.get("git_commit_id") or checkout["commit"])
                git_tree_id = str(identity.get("git_tree_id") or checkout["tree"])
            else:
                repository_id = "lift_coding/proof-backed-test-reuse"
                repository_state_cid = f"git-commit:{checkout['commit']}"
                git_commit_id = str(checkout["commit"])
                git_tree_id = str(checkout["tree"])
        except (OSError, json.JSONDecodeError):
            repository_id = "lift_coding/proof-backed-test-reuse"
            repository_state_cid = f"git-commit:{checkout['commit']}"
            git_commit_id = str(checkout["commit"])
            git_tree_id = str(checkout["tree"])
    else:
        repository_id = "lift_coding/proof-backed-test-reuse"
        repository_state_cid = f"git-commit:{checkout['commit']}"
        git_commit_id = str(checkout["commit"])
        git_tree_id = str(checkout["tree"])

    try:
        collector = ProofTestReuseTaskEvidenceCollector(
            repository_id=repository_id,
            repository_state_cid=repository_state_cid,
            git_commit_id=git_commit_id,
            git_tree_id=git_tree_id,
            gitlink_state_cid=gitlink,
            repository_forest_cid=forest_cid,
            dirty=dirty,
            dirty_overlay_cid=dirty_overlay,
            board_namespace="proof-backed-test-reuse-v1",
            freshness_seconds=3_600.0,
            ancestry_verifier=lambda ancestor, target: (
                bool(ancestor)
                and (
                    ancestor == target
                    or subprocess.run(
                        ["git", "merge-base", "--is-ancestor", ancestor, target],
                        cwd=REPO_ROOT,
                        check=False,
                        capture_output=True,
                    ).returncode
                    == 0
                )
            ),
        )
    except ProofTestReuseTaskEvidenceError as exc:
        return {
            "ok": False,
            "reason": "collector_construction_failed",
            "error": str(exc),
        }

    # Board validator payload is used as validated_board when it exposes valid=true.
    board_payload = dict(board) if isinstance(board, dict) else {}
    if board_payload.get("valid") is not True:
        # Some validators report errors=[] without valid=true; mark explicitly.
        board_payload = {
            **board_payload,
            "valid": not bool(board_payload.get("errors")),
            "board_namespace": "proof-backed-test-reuse-v1",
            "task_count": len(tasks),
            "task_ids": [t.task_id for t in tasks],
            "task_cids": {t.task_id: t.canonical_task_cid for t in tasks},
        }
    else:
        board_payload = {
            **board_payload,
            "board_namespace": board_payload.get("board_namespace") or "proof-backed-test-reuse-v1",
            "task_count": board_payload.get("task_count") or len(tasks),
            "task_ids": board_payload.get("task_ids") or [t.task_id for t in tasks],
            "task_cids": board_payload.get("task_cids")
            or {t.task_id: t.canonical_task_cid for t in tasks},
        }

    try:
        collection = collector.collect(
            validated_board=board_payload,
            task_records=tasks,
            merge_queue_records=merge_records,
            validation_receipts=validation_receipts,
        )
    except Exception as exc:  # probe
        return {
            "ok": False,
            "reason": "collect_raised",
            "error": f"{type(exc).__name__}: {exc}",
        }

    evidence = getattr(collection, "evidence", ()) or ()
    gaps = getattr(collection, "gaps", ()) or ()
    gap_kinds: dict[str, int] = {}
    for g in gaps:
        kind = str(
            getattr(g, "kind", None) or (g.get("kind") if isinstance(g, dict) else "unknown")
        )
        gap_kinds[kind] = gap_kinds.get(kind, 0) + 1
    return {
        "ok": True,
        "board_cid": getattr(collection, "board_cid", ""),
        "required_task_ids": list(getattr(collection, "required_task_ids", ()) or ()),
        "evidence_count": len(tuple(evidence)),
        "gap_count": len(tuple(gaps)),
        "gap_kinds": gap_kinds,
        "validation_receipt_count": len(validation_receipts),
        "gaps": [
            {
                "task_id": getattr(g, "task_id", None)
                or (g.get("task_id") if isinstance(g, dict) else None),
                "kind": str(
                    getattr(g, "kind", None) or (g.get("kind") if isinstance(g, dict) else "")
                ),
                "detail": str(
                    getattr(g, "detail", None) or (g.get("detail") if isinstance(g, dict) else "")
                )[:500],
            }
            for g in list(gaps)[:200]
        ],
        "evidence_task_ids": [
            getattr(item, "task_id", None)
            or (item.get("task_id") if isinstance(item, dict) else None)
            for item in list(evidence)[:200]
        ],
    }


# typing alias without importing Mapping at runtime in signature only
MappingLike = Any


def main() -> int:
    started = datetime.now(UTC).isoformat()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    checkout = _checkout_identity()
    _write(OUT_DIR / "checkout_identity.json", checkout)

    board_rc, board, board_err = _run_json(
        [sys.executable, str(REPO_ROOT / "scripts" / "validate_proof_backed_test_reuse_board.py")]
    )
    _write(
        OUT_DIR / "board_validation.json",
        {"returncode": board_rc, "result": board, "stderr_tail": board_err[-2000:]},
    )

    status_rc, status, status_err = _run_json(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "proof_backed_test_reuse_supervisor.py"),
            "status",
        ]
    )
    _write(
        OUT_DIR / "supervisor_status.json",
        {"returncode": status_rc, "result": status, "stderr_tail": status_err[-2000:]},
    )

    config_bytes = CONFIG_PATH.read_bytes()
    health_input = {
        "schema": "ipfs_accelerate_py/proof-backed-test-reuse-supervisor-health-input@1",
        "captured_at_unix_ns": time.time_ns(),
        "configuration_sha256": "sha256:" + hashlib.sha256(config_bytes).hexdigest(),
        "checkout": checkout,
        "status": status if isinstance(status, dict) else {},
        "materialization_authority": False,
    }
    _write(OUT_DIR / "supervisor_health_input.json", health_input)
    # Also place a copy next to completion artifacts for operator convenience.
    completion_dir = STATE_ROOT / "projection" / "completion"
    completion_dir.mkdir(parents=True, exist_ok=True)
    _write(completion_dir / "supervisor_health_input.json", health_input)

    forest = _materialize_forest()
    _write(OUT_DIR / "forest_materialization.json", forest)

    merge_records = _load_merge_records()
    merge_summary = {
        "count": len(merge_records),
        "task_ids": sorted(
            {
                str(r.get("task_id"))
                for r in merge_records
                if str(r.get("task_id") or "").startswith("PTR-")
            }
        ),
    }
    _write(OUT_DIR / "merge_records_summary.json", merge_summary)

    validation_receipts = _load_validation_receipts()
    _write(
        OUT_DIR / "validation_receipts_summary.json",
        {
            "count": len(validation_receipts),
            "task_ids": sorted(
                str(r.get("task_id"))
                for r in validation_receipts
                if str(r.get("task_id") or "").startswith("PTR-")
            ),
            "source_dir": str(VALIDATION_RECEIPT_DIR),
        },
    )

    # Prefer the agent-supervisor closeout materializer (merge projection +
    # optional git ancestry recovery) when the package is importable.
    task_evidence: dict[str, object]
    try:
        if str(ACCEL_ROOT) not in sys.path:
            sys.path.insert(0, str(ACCEL_ROOT))
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
            parse_task_file,
        )
        from ipfs_accelerate_py.agent_supervisor.validation.proof_test_reuse_closeout_materializer import (
            CloseoutMaterializerIdentity,
            load_json_rows,
            materialize_task_evidence,
            persist_materialization_report,
        )

        identity_snapshot_path = VALIDATION_RECEIPT_DIR / "identity_snapshot.json"
        identity_payload: dict[str, object] = {}
        if identity_snapshot_path.is_file():
            identity_payload = (
                json.loads(identity_snapshot_path.read_text(encoding="utf-8")).get("identity") or {}
            )
        forest_cid = str(
            identity_payload.get("repository_forest_cid")
            or forest.get("repository_forest_cid")
            or ""
        )
        gitlink = str(
            identity_payload.get("gitlink_state_cid") or forest.get("gitlink_state_cid") or ""
        )
        identity = CloseoutMaterializerIdentity(
            repository_id=str(
                identity_payload.get("repository_id") or "lift_coding/proof-backed-test-reuse"
            ),
            repository_state_cid=str(
                identity_payload.get("repository_state_cid") or f"git-commit:{checkout['commit']}"
            ),
            git_commit_id=str(identity_payload.get("git_commit_id") or checkout["commit"]),
            git_tree_id=str(identity_payload.get("git_tree_id") or checkout["tree"]),
            gitlink_state_cid=gitlink,
            repository_forest_cid=forest_cid,
            dirty=bool(identity_payload.get("dirty", not checkout.get("clean"))),
            dirty_overlay_cid=str(
                identity_payload.get("dirty_overlay_cid")
                or (
                    "cid:dirty-overlay:none"
                    if checkout.get("clean")
                    else "cid:dirty-overlay:present"
                )
            ),
        )
        tasks = parse_task_file(REPO_ROOT / TODO_REL, "## PTR-")
        board_payload = dict(board) if isinstance(board, dict) else {}
        board_payload = {
            **board_payload,
            "valid": not bool(board_payload.get("errors")),
            "board_namespace": "proof-backed-test-reuse-v1",
            "task_count": len(tasks),
            "task_ids": [t.task_id for t in tasks],
            "task_cids": {t.task_id: t.canonical_task_cid for t in tasks},
        }
        # Load raw merge rows (materializer projects them).
        raw_merges = load_json_rows(MERGE_COMPLETED)
        report = materialize_task_evidence(
            identity=identity,
            validated_board=board_payload,
            task_records=tasks,
            merge_queue_records=raw_merges,
            validation_receipts=validation_receipts,
            recover_missing_merges_from_git=True,
            repo_root=REPO_ROOT,
            freshness_seconds=3_600.0,
        )
        persist_materialization_report(report, output_dir=OUT_DIR)
        task_evidence = {
            "ok": True,
            "source": "proof_test_reuse_closeout_materializer",
            "evidence_count": report.evidence_count,
            "gap_count": report.gap_count,
            "gap_kinds": report.gap_kinds,
            "validation_receipt_count": report.validation_receipt_count,
            "merge_queue_projected_count": report.merge_queue_projected_count,
            "merge_recovered_from_git_count": report.merge_recovered_from_git_count,
            "evidence_task_ids": list(report.evidence_task_ids),
            "validation_missing_task_ids": list(report.validation_missing_task_ids),
            "completion_missing_task_ids": list(report.completion_missing_task_ids),
            "approval_required_task_ids": list(report.approval_required_task_ids),
            "next_actions": list(report.next_actions),
        }
    except Exception as exc:
        task_evidence = _attempt_task_evidence(
            board=board if isinstance(board, dict) else {},
            checkout=checkout,
            forest=forest,
            merge_records=merge_records,
            validation_receipts=validation_receipts,
        )
        task_evidence = {
            **task_evidence,
            "materializer_fallback_error": f"{type(exc).__name__}: {exc}",
        }
    _write(OUT_DIR / "task_evidence_probe.json", task_evidence)

    closeout_rc, closeout, closeout_err = _run_json(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "proof_backed_test_reuse_supervisor.py"),
            "closeout",
            "--report-only",
        ]
    )
    _write(
        OUT_DIR / "closeout_report_only.json",
        {
            "returncode": closeout_rc,
            "result": closeout,
            "stderr_tail": closeout_err[-2000:],
        },
    )

    remaining = []
    if isinstance(closeout, dict):
        inv = closeout.get("input_inventory") or {}
        if isinstance(inv, dict):
            remaining = [
                item.get("name")
                for item in inv.get("remaining_inputs") or []
                if isinstance(item, dict)
            ]

    summary = {
        "schema": "ipfs_accelerate_py/proof-backed-test-reuse-closeout-materialization-probe@1",
        "authority": False,
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "checkout": {
            "branch": checkout.get("branch"),
            "commit": checkout.get("commit"),
            "clean": checkout.get("clean"),
        },
        "board_returncode": board_rc,
        "board_completed_task_count": (
            board.get("completed_task_count") if isinstance(board, dict) else None
        ),
        "supervisor_work_complete": (
            status.get("work_complete") if isinstance(status, dict) else None
        ),
        "supervisor_healthy": (status.get("healthy") if isinstance(status, dict) else None),
        "forest_ok": bool(forest.get("ok")),
        "merge_record_count": len(merge_records),
        "validation_receipt_count": len(validation_receipts),
        "task_evidence_probe": {
            "ok": task_evidence.get("ok"),
            "reason": task_evidence.get("reason"),
            "evidence_count": task_evidence.get("evidence_count"),
            "gap_count": task_evidence.get("gap_count"),
            "gap_kinds": task_evidence.get("gap_kinds"),
        },
        "closeout_report_only_returncode": closeout_rc,
        "closeout_passed": (
            closeout.get("closeout_passed") if isinstance(closeout, dict) else None
        ),
        "remaining_input_groups": remaining,
        "output_directory": str(OUT_DIR),
        "notes": [
            "This probe is not completion authority.",
            "Missing managed-merge provenance and operator approvals cannot be synthesized.",
            "Gate/evidence artifacts are only written by authoritative PTR-110/111/120/122 materializers with complete inputs.",
        ],
    }
    _write(OUT_DIR / "materialization_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    # Non-zero if closeout still not ready — expected until operator inputs land.
    return 0 if summary.get("closeout_passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())

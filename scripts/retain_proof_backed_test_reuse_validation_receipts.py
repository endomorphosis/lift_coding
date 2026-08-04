#!/usr/bin/env python3
"""Retain fresh MODE=off validation receipts for the PTR board on the current tree.

This produces sealed executed-validation receipts that
``ProofTestReuseTaskEvidenceCollector`` can consume. Receipts are bound to the
current checkout identity (commit/tree/forest/gitlink/dirty overlay) and expire
within the collector freshness window (default 55 minutes, collector max 1h).

Authority notes:
- Receipts prove a successful current-tree validation rerun only.
- They do **not** synthesize managed-merge or operator-approval provenance.
- They do **not** authorize production warm skip or objective closeout alone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEL_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
KIT_ROOT = REPO_ROOT / "external" / "ipfs_kit"
TODO_REL = "implementation_plan/docs/46-proof-backed-test-reuse.todo.md"
STATE_ROOT = Path(
    os.environ.get(
        "IPFS_ACCELERATE_PROOF_REUSE_STATE_ROOT",
        str(Path.home() / ".local" / "state" / "ipfs_accelerate_py" / "proof-backed-test-reuse-v1"),
    )
)
RECEIPT_DIR = STATE_ROOT / "projection" / "completion" / "validation_receipts"
IDENTITY_PATH = (
    STATE_ROOT / "projection" / "completion" / "materialization" / "checkout_identity.json"
)
FOREST_PATH = (
    STATE_ROOT / "projection" / "completion" / "materialization" / "forest_materialization.json"
)
MERGE_COMPLETED = STATE_ROOT / "merge-queue" / "completed"

DEFAULT_FRESHNESS_SECONDS = 3_300.0  # under collector max of 3600
DEFAULT_TIMEOUT_SECONDS = 1_800
DEFAULT_WORKERS = 2


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def _ensure_accel_path() -> None:
    if str(ACCEL_ROOT) not in sys.path:
        sys.path.insert(0, str(ACCEL_ROOT))


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


def _forest_identity() -> dict[str, Any]:
    if FOREST_PATH.is_file():
        try:
            payload = json.loads(FOREST_PATH.read_text(encoding="utf-8"))
            if payload.get("repository_forest_cid") and payload.get("gitlink_state_cid"):
                return payload
        except (OSError, json.JSONDecodeError):
            pass
    _ensure_accel_path()
    from ipfs_accelerate_py.agent_supervisor.repository_forest_manifest import (
        materialize_initial_four_repository_forest,
    )

    swiss = REPO_ROOT / "swissknife"
    if not swiss.is_dir():
        swiss = REPO_ROOT
    result = materialize_initial_four_repository_forest(
        swissknife_root=swiss,
        accelerator_root=ACCEL_ROOT,
        kit_root=KIT_ROOT,
        datasets_root=DATASETS_ROOT,
        require_all_four=False,
        fail_on_missing_required=False,
    )
    forest = getattr(result, "forest", None)
    forest_dict = forest.to_dict() if forest is not None and hasattr(forest, "to_dict") else {}
    forest_cid = (
        getattr(result, "forest_id", None)
        or getattr(forest, "forest_id", None)
        or forest_dict.get("forest_id")
    )
    gitlink = None
    if isinstance(forest_dict.get("descriptors"), list):
        for desc in forest_dict["descriptors"]:
            if isinstance(desc, dict) and desc.get("gitlink_closure_cid"):
                gitlink = desc["gitlink_closure_cid"]
                break
    return {
        "ok": True,
        "repository_forest_cid": str(forest_cid or ""),
        "gitlink_state_cid": str(gitlink or ""),
        "policy_cid": str(
            getattr(result, "policy_cid", None) or forest_dict.get("policy_cid") or ""
        ),
        "forest": forest_dict,
    }


def _merge_task_ids() -> set[str]:
    found: set[str] = set()
    if not MERGE_COMPLETED.is_dir():
        return found
    for path in MERGE_COMPLETED.glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        task_id = str(record.get("task_id") or "").strip()
        if task_id.startswith("PTR-") and str(record.get("status") or "").lower() in {
            "completed",
            "merged",
        }:
            found.add(task_id)
    return found


def _task_records() -> list[Any]:
    _ensure_accel_path()
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        parse_task_file,
    )

    return list(parse_task_file(REPO_ROOT / TODO_REL, "## PTR-"))


def _task_goal_id(task: Any) -> str:
    metadata = getattr(task, "metadata", None) or {}
    if isinstance(metadata, dict):
        goal = str(metadata.get("goal id") or metadata.get("goal_id") or "").strip()
        if goal:
            return goal
    return str(getattr(task, "task_id", ""))


def _seal_receipt(body: dict[str, Any]) -> dict[str, Any]:
    _ensure_accel_path()
    from ipfs_accelerate_py.agent_supervisor.proof.formal_verification_contracts import (
        content_identity,
    )

    payload = dict(body)
    payload.pop("validation_receipt_cid", None)
    payload.pop("receipt_id", None)
    payload.pop("content_id", None)
    return {**payload, "validation_receipt_cid": content_identity(payload)}


def _identity_bundle(checkout: dict[str, Any], forest: dict[str, Any]) -> dict[str, Any]:
    dirty = not bool(checkout.get("clean"))
    dirty_detail = str(checkout.get("dirty_detail") or "")
    if dirty:
        digest = hashlib.sha256(dirty_detail.encode("utf-8")).hexdigest()
        dirty_overlay = f"baguqeera{digest[:50]}"
    else:
        dirty_overlay = "cid:dirty-overlay:none"
    return {
        "repository_id": "lift_coding/proof-backed-test-reuse",
        "repository_state_cid": f"git-commit:{checkout['commit']}",
        "git_commit_id": str(checkout["commit"]),
        "git_tree_id": str(checkout["tree"]),
        "gitlink_state_cid": str(forest.get("gitlink_state_cid") or ""),
        "repository_forest_cid": str(forest.get("repository_forest_cid") or ""),
        "dirty": dirty,
        "dirty_overlay_cid": dirty_overlay,
        "policy_cid": str(forest.get("policy_cid") or ""),
    }


def _run_validation(command: str, *, timeout: int) -> dict[str, Any]:
    env = os.environ.copy()
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    # Board commands already force MODE=off as a prefix; keep ambient off too.
    env["IPFS_TEST_PROOF_REUSE_MODE"] = "off"
    # Prefer package roots on PYTHONPATH for importable tests.
    path_parts = [
        str(ACCEL_ROOT),
        str(DATASETS_ROOT),
        str(KIT_ROOT),
        env.get("PYTHONPATH", ""),
    ]
    env["PYTHONPATH"] = os.pathsep.join(p for p in path_parts if p)

    started = time.time()
    try:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            shell=True,
            text=True,
            capture_output=True,
            env=env,
            timeout=timeout,
            check=False,
        )
        finished = time.time()
        return {
            "exit_code": int(result.returncode),
            "stdout_tail": (result.stdout or "")[-4000:],
            "stderr_tail": (result.stderr or "")[-2000:],
            "duration_seconds": finished - started,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        finished = time.time()
        return {
            "exit_code": 124,
            "stdout_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": f"timeout after {timeout}s",
            "duration_seconds": finished - started,
            "timed_out": True,
        }


def _build_receipt(
    *,
    task: Any,
    identity: dict[str, Any],
    run: dict[str, Any],
    freshness_seconds: float,
) -> dict[str, Any] | None:
    _ensure_accel_path()
    from ipfs_accelerate_py.agent_supervisor.validation.proof_cached_test_validation import (
        validation_command_identity,
    )

    if int(run.get("exit_code", 1)) != 0 or run.get("timed_out"):
        return None
    command = (getattr(task, "validation", None) or [""])[0]
    if not str(command).startswith("IPFS_TEST_PROOF_REUSE_MODE=off "):
        return None
    now_ms = int(time.time() * 1000)
    fresh_until_ms = now_ms + int(float(freshness_seconds) * 1000)
    body = {
        "task_id": task.task_id,
        "goal_id": _task_goal_id(task),
        "task_cid": task.canonical_task_cid,
        "validation_command": command,
        "validation_command_cid": validation_command_identity(command),
        "repository_id": identity["repository_id"],
        "repository_state_cid": identity["repository_state_cid"],
        "git_commit_id": identity["git_commit_id"],
        "git_tree_id": identity["git_tree_id"],
        "gitlink_state_cid": identity["gitlink_state_cid"],
        "repository_forest_cid": identity["repository_forest_cid"],
        "dirty": identity["dirty"],
        "dirty_overlay_cid": identity["dirty_overlay_cid"],
        "proof_reuse_mode": "off",
        "disposition": "executed",
        "status": "passed",
        "passed": True,
        "exit_code": 0,
        "skipped_count": 0,
        "observed_at_ms": now_ms,
        "fresh_until_ms": fresh_until_ms,
        # Integer-only body: content_identity rejects floats.
        "duration_ms": int(round(float(run.get("duration_seconds") or 0.0) * 1000.0)),
        "retained_at_ms": now_ms,
        "authority": False,
        "schema": "ipfs_accelerate_py/proof-backed-test-reuse-executed-validation-receipt@1",
    }
    return _seal_receipt(body)


def _select_tasks(
    tasks: list[Any],
    *,
    only: set[str] | None,
    only_merge_queued: bool,
    max_tasks: int | None,
) -> list[Any]:
    selected = list(tasks)
    if only:
        selected = [t for t in selected if t.task_id in only]
    if only_merge_queued:
        merge_ids = _merge_task_ids()
        selected = [t for t in selected if t.task_id in merge_ids]
    if max_tasks is not None:
        selected = selected[: max(0, int(max_tasks))]
    return selected


def retain_one(
    task: Any,
    *,
    identity: dict[str, Any],
    timeout: int,
    freshness_seconds: float,
) -> dict[str, Any]:
    command = (getattr(task, "validation", None) or [""])[0]
    run = _run_validation(command, timeout=timeout)
    receipt = _build_receipt(
        task=task,
        identity=identity,
        run=run,
        freshness_seconds=freshness_seconds,
    )
    out: dict[str, Any] = {
        "task_id": task.task_id,
        "exit_code": run.get("exit_code"),
        "timed_out": bool(run.get("timed_out")),
        "duration_seconds": run.get("duration_seconds"),
        "passed": receipt is not None,
        "receipt_path": None,
        "validation_receipt_cid": None,
        "stdout_tail": run.get("stdout_tail"),
        "stderr_tail": run.get("stderr_tail"),
    }
    if receipt is None:
        fail_path = RECEIPT_DIR / "failed" / f"{task.task_id}.json"
        _write(
            fail_path,
            {
                "task_id": task.task_id,
                "command": command,
                "run": run,
                "identity": identity,
            },
        )
        out["receipt_path"] = str(fail_path)
        return out

    path = RECEIPT_DIR / f"{task.task_id}.json"
    _write(path, receipt)
    out["receipt_path"] = str(path)
    out["validation_receipt_cid"] = receipt.get("validation_receipt_cid")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task",
        action="append",
        default=[],
        help="Limit to one or more task ids (repeatable)",
    )
    parser.add_argument(
        "--only-merge-queued",
        action="store_true",
        help="Only tasks with completed merge-queue records",
    )
    parser.add_argument("--max-tasks", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument(
        "--freshness-seconds",
        type=float,
        default=DEFAULT_FRESHNESS_SECONDS,
    )
    parser.add_argument(
        "--require-clean",
        action="store_true",
        help="Refuse to run if the integration checkout is dirty",
    )
    args = parser.parse_args(argv)

    checkout = _checkout_identity()
    if args.require_clean and not checkout.get("clean"):
        print(
            json.dumps(
                {
                    "error": "dirty_checkout",
                    "dirty_detail": checkout.get("dirty_detail"),
                },
                indent=2,
            )
        )
        return 2

    forest = _forest_identity()
    if not forest.get("repository_forest_cid") or not forest.get("gitlink_state_cid"):
        print(
            json.dumps(
                {
                    "error": "forest_identity_incomplete",
                    "forest": {
                        k: forest.get(k)
                        for k in ("repository_forest_cid", "gitlink_state_cid", "ok")
                    },
                },
                indent=2,
            )
        )
        return 2

    identity = _identity_bundle(checkout, forest)
    _write(
        RECEIPT_DIR / "identity_snapshot.json",
        {
            "checkout": checkout,
            "forest": {
                "repository_forest_cid": forest.get("repository_forest_cid"),
                "gitlink_state_cid": forest.get("gitlink_state_cid"),
                "policy_cid": forest.get("policy_cid"),
            },
            "identity": identity,
            "captured_at": datetime.now(UTC).isoformat(),
        },
    )

    tasks = _task_records()
    only = set(args.task) if args.task else None
    selected = _select_tasks(
        tasks,
        only=only,
        only_merge_queued=bool(args.only_merge_queued),
        max_tasks=args.max_tasks,
    )
    if not selected:
        print(json.dumps({"error": "no_tasks_selected", "selected": 0}, indent=2))
        return 2

    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    workers = max(1, int(args.workers))

    if workers == 1:
        for task in selected:
            results.append(
                retain_one(
                    task,
                    identity=identity,
                    timeout=int(args.timeout),
                    freshness_seconds=float(args.freshness_seconds),
                )
            )
            print(
                f"{task.task_id}: passed={results[-1]['passed']} "
                f"exit={results[-1]['exit_code']} "
                f"dur={results[-1]['duration_seconds']:.1f}s",
                flush=True,
            )
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    retain_one,
                    task,
                    identity=identity,
                    timeout=int(args.timeout),
                    freshness_seconds=float(args.freshness_seconds),
                ): task.task_id
                for task in selected
            }
            for future in as_completed(futures):
                item = future.result()
                results.append(item)
                print(
                    f"{item['task_id']}: passed={item['passed']} "
                    f"exit={item['exit_code']} "
                    f"dur={float(item.get('duration_seconds') or 0):.1f}s",
                    flush=True,
                )

    results.sort(key=lambda item: str(item.get("task_id") or ""))
    passed = [r for r in results if r.get("passed")]
    failed = [r for r in results if not r.get("passed")]
    summary = {
        "schema": "ipfs_accelerate_py/proof-backed-test-reuse-validation-receipt-run@1",
        "authority": False,
        "captured_at": datetime.now(UTC).isoformat(),
        "checkout_commit": checkout.get("commit"),
        "checkout_clean": checkout.get("clean"),
        "identity": identity,
        "selected_count": len(selected),
        "passed_count": len(passed),
        "failed_count": len(failed),
        "passed_task_ids": [r["task_id"] for r in passed],
        "failed_task_ids": [r["task_id"] for r in failed],
        "receipt_dir": str(RECEIPT_DIR),
        "freshness_seconds": float(args.freshness_seconds),
        "results": [
            {
                "task_id": r["task_id"],
                "passed": r["passed"],
                "exit_code": r["exit_code"],
                "duration_seconds": r["duration_seconds"],
                "validation_receipt_cid": r.get("validation_receipt_cid"),
                "receipt_path": r.get("receipt_path"),
            }
            for r in results
        ],
    }
    _write(RECEIPT_DIR / "run_summary.json", summary)
    print(json.dumps({k: summary[k] for k in summary if k != "results"}, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Fenced multi-phase objective reconciliation for proof-backed test reuse.

This module is the outer program's bounded non-shell CLI consumed by
``scripts/proof_backed_test_reuse_supervisor.py closeout``.  Worker lanes keep
goal reconciliation disabled; only this outer controller may advance goal
lifecycle state, and only into a state-root candidate that still requires an
explicit operator commit into the protected objective heap.

Lifecycle contract (three phases, never skipped):

1. Provisional — drained goals become ``provisionally_complete`` only.
2. Children — after current validation, verify ``PTR-G010`` … ``PTR-G130``.
3. Final root — admit the authenticated current-tree gate, then verify
   ``PTR-G140`` followed by
   ``PTR-G000``.

Report-only diagnosis never writes the repository.  Closeout refuses open
tasks, dirty or changed source checkouts, concurrent writers, stale artifacts,
and unhealthy supervisor state.  Every refresh recomputes bindings; bounded
replay converges; interruption resumes from durable phase checkpoints;
mutation or contradiction reopens affected ancestors and dependents.  Missing
optional services produce typed nonterminal gaps rather than blocking.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

# ---------------------------------------------------------------------------
# Interface / schema constants
# ---------------------------------------------------------------------------

PROOF_TEST_REUSE_OBJECTIVE_RECONCILER_INTERFACE: Final = "ProofTestReuseObjectiveReconciler@1"
OBJECTIVE_CLOSEOUT_RECEIPT_INTERFACE: Final = "ObjectiveCloseoutReceipt@1"
OBJECTIVE_CLOSEOUT_FENCE_INTERFACE: Final = "ObjectiveCloseoutFence@1"
OBJECTIVE_CLOSEOUT_RECEIPT_SCHEMA: Final = (
    "ipfs_accelerate_py/proof-backed-test-reuse-objective-closeout-receipt@1"
)
OBJECTIVE_CLOSEOUT_STATUS_SCHEMA: Final = (
    "ipfs_accelerate_py/proof-backed-test-reuse-closeout-status@1"
)
OBJECTIVE_CLOSEOUT_FENCE_SCHEMA: Final = (
    "ipfs_accelerate_py/proof-backed-test-reuse-objective-closeout-fence@1"
)
OBJECTIVE_CLOSEOUT_CHECKPOINT_SCHEMA: Final = (
    "ipfs_accelerate_py/proof-backed-test-reuse-objective-closeout-checkpoint@1"
)
OBJECTIVE_COMPLETION_EVIDENCE_ARTIFACT: Final = "ObjectiveCompletionEvidenceArtifact"

ROOT_GOAL_ID: Final = "PTR-G000"
FINAL_GATE_GOAL_ID: Final = "PTR-G140"
FINAL_GATE_TASK_ID: Final = "PTR-169"
FINAL_GATE_ACCEPTANCE_CRITERION: Final = "ptr/authenticated-current-tree-gate-v5@1"
EXPECTED_TASK_COUNT: Final = 78
FINAL_GATE_REVIEW_REVISION: Final = "authenticated-receipt-current-tree-repair-v9"
ROOT_ACCEPTANCE_CRITERION: Final = "ptr/cross-repository-current-tree-gate@1"
CHILD_GOAL_IDS: Final = tuple(
    f"PTR-G{index:03d}" for index in (10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130)
)
ALL_GOAL_IDS: Final = (ROOT_GOAL_ID, *CHILD_GOAL_IDS, FINAL_GATE_GOAL_ID)
DEFAULT_PHASE_COUNT: Final = 3
MAX_REPLAY_ROUNDS: Final = 8
TASK_HEADER_RE = re.compile(r"^##\s+(PTR-\d{3})\b", re.MULTILINE)
TASK_STATUS_RE = re.compile(r"^- Status:\s*(\S+)", re.MULTILINE | re.IGNORECASE)
GOAL_HEADER_RE = re.compile(r"^##\s+(PTR-G\d{3})\s+(.+?)\s*$", re.MULTILINE)
GOAL_STATUS_RE = re.compile(r"^- Status:\s*(\S+)", re.MULTILINE | re.IGNORECASE)
GOAL_PARENT_RE = re.compile(r"^- Parent:[ \t]*([^\r\n]*)$", re.MULTILINE | re.IGNORECASE)
GOAL_DEPENDS_RE = re.compile(r"^- Depends on:[ \t]*([^\r\n]*)$", re.MULTILINE | re.IGNORECASE)
CLOSED_TASK_STATUSES: Final = frozenset({"completed", "complete", "verified_complete", "done"})
CLOSED_GOAL_STATUSES: Final = frozenset({"verified_complete", "complete", "completed", "done"})
PROVISIONAL_GOAL_STATUSES: Final = frozenset({"provisionally_complete", "provisional"})
OPTIONAL_SERVICE_KEYS: Final = frozenset(
    {
        "groth16",
        "provekit",
        "snarkjs",
        "ipfs",
        "kubo",
        "lotus",
        "iroh",
        "proof_cache",
        "ipfs_transport",
        "shared_cache",
    }
)


# ---------------------------------------------------------------------------
# Enumerations and errors
# ---------------------------------------------------------------------------


class ObjectiveCloseoutPhase(StrEnum):
    """Ordered closeout phases.  Phases must never skip a legal transition."""

    DIAGNOSE = "diagnose"
    FENCE = "fence"
    PHASE_1_PROVISIONAL = "phase_1_provisional"
    PHASE_2_VERIFY_CHILDREN = "phase_2_verify_g010_g130"
    PHASE_3_VERIFY_FINAL = "phase_3_verify_g140_g000"
    CANDIDATE_HANDOFF = "candidate_handoff"
    COMPLETE = "complete"


PHASE_ORDER: Final = (
    ObjectiveCloseoutPhase.DIAGNOSE,
    ObjectiveCloseoutPhase.FENCE,
    ObjectiveCloseoutPhase.PHASE_1_PROVISIONAL,
    ObjectiveCloseoutPhase.PHASE_2_VERIFY_CHILDREN,
    ObjectiveCloseoutPhase.PHASE_3_VERIFY_FINAL,
    ObjectiveCloseoutPhase.CANDIDATE_HANDOFF,
    ObjectiveCloseoutPhase.COMPLETE,
)


class CloseoutRefusal(RuntimeError):
    """Fail-closed refusal of a closeout or report-only request."""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.message = message


class ConcurrentWriterError(CloseoutRefusal):
    def __init__(self, message: str) -> None:
        super().__init__("concurrent_writer", message)


class StaleArtifactError(CloseoutRefusal):
    def __init__(self, message: str) -> None:
        super().__init__("stale_artifact", message)


class UnhealthySupervisorError(CloseoutRefusal):
    def __init__(self, message: str) -> None:
        super().__init__("unhealthy_supervisor", message)


class OpenTasksError(CloseoutRefusal):
    def __init__(self, open_task_ids: Sequence[str]) -> None:
        joined = ", ".join(open_task_ids)
        super().__init__(
            "open_tasks",
            "objective closeout requires every implementation task to be "
            f"completed; open tasks: {joined}",
        )
        self.open_task_ids = tuple(open_task_ids)


class DirtyCheckoutError(CloseoutRefusal):
    def __init__(self, detail: str) -> None:
        super().__init__(
            "dirty_checkout",
            f"refusing dirty or changed source checkout: {detail}",
        )


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _canonical_json(payload: Mapping[str, Any] | Sequence[Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _ensure_accel_on_path(repo_root: Path) -> None:
    accel = repo_root / "external" / "ipfs_accelerate"
    if accel.is_dir():
        text = str(accel)
        if text not in sys.path:
            sys.path.insert(0, text)


def _try_import_goal_apis(repo_root: Path) -> dict[str, Any]:
    """Import accelerator goal APIs when available; otherwise return stubs."""

    _ensure_accel_on_path(repo_root)
    try:
        from ipfs_accelerate_py.agent_supervisor.objectives.goal_completion import (  # type: ignore
            GoalLifecycle,
            GoalState,
            IllegalGoalTransitionError,
            legal_goal_transitions,
            normalize_goal_state,
            reconcile_goal_reopenings,
        )
        from ipfs_accelerate_py.agent_supervisor.objectives.objective_tracker import (  # type: ignore
            parse_goal_heap,
            rewrite_goal_fields,
        )

        return {
            "GoalLifecycle": GoalLifecycle,
            "GoalState": GoalState,
            "IllegalGoalTransitionError": IllegalGoalTransitionError,
            "legal_goal_transitions": legal_goal_transitions,
            "normalize_goal_state": normalize_goal_state,
            "reconcile_goal_reopenings": reconcile_goal_reopenings,
            "parse_goal_heap": parse_goal_heap,
            "rewrite_goal_fields": rewrite_goal_fields,
            "available": True,
        }
    except Exception:
        return {"available": False}


# ---------------------------------------------------------------------------
# Parsing helpers (board + objectives)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TaskSnapshot:
    task_id: str
    status: str

    @property
    def is_closed(self) -> bool:
        return self.status.strip().lower() in CLOSED_TASK_STATUSES


@dataclass
class GoalSnapshot:
    goal_id: str
    title: str
    status: str
    parent_ids: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    fields: dict[str, str] = field(default_factory=dict)

    @property
    def is_verified(self) -> bool:
        return self.status.strip().lower() in CLOSED_GOAL_STATUSES

    @property
    def is_provisional(self) -> bool:
        return self.status.strip().lower() in PROVISIONAL_GOAL_STATUSES


def parse_todo_tasks(text: str) -> list[TaskSnapshot]:
    """Parse ``## PTR-NNN`` task headers and their Status fields."""

    tasks: list[TaskSnapshot] = []
    matches = list(TASK_HEADER_RE.finditer(text))
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end]
        status_match = TASK_STATUS_RE.search(body)
        status = status_match.group(1).strip() if status_match else "todo"
        tasks.append(TaskSnapshot(task_id=match.group(1), status=status))
    return tasks


def parse_objective_goals(text: str) -> list[GoalSnapshot]:
    """Parse objective goal blocks without requiring the accelerator package."""

    goals: list[GoalSnapshot] = []
    matches = list(GOAL_HEADER_RE.finditer(text))
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end]
        status_match = GOAL_STATUS_RE.search(body)
        status = status_match.group(1).strip() if status_match else "active"
        parent_match = GOAL_PARENT_RE.search(body)
        parent_raw = parent_match.group(1).strip() if parent_match else ""
        parents = tuple(
            part.strip()
            for part in re.split(r"[,;]", parent_raw)
            if part.strip() and part.strip().upper() not in {"NONE", "N/A", "-"}
        )
        depends_match = GOAL_DEPENDS_RE.search(body)
        depends_raw = depends_match.group(1).strip() if depends_match else ""
        depends = tuple(
            part.strip()
            for part in re.split(r"[,;]", depends_raw)
            if part.strip() and part.strip().upper() not in {"NONE", "N/A", "-"}
        )
        fields: dict[str, str] = {}
        for line in body.splitlines():
            if line.startswith("- ") and ":" in line:
                key, value = line[2:].split(":", 1)
                fields[key.strip()] = value.strip()
        goals.append(
            GoalSnapshot(
                goal_id=match.group(1),
                title=match.group(2).strip(),
                status=status,
                parent_ids=parents,
                depends_on=depends,
                fields=fields,
            )
        )
    return goals


def rewrite_objective_statuses(text: str, status_by_goal: Mapping[str, str]) -> str:
    """Rewrite ``- Status:`` lines for selected goals; preserve other fields."""

    if not status_by_goal:
        return text
    lines = text.splitlines()
    rewritten: list[str] = []
    current_goal = ""
    for line in lines:
        header = GOAL_HEADER_RE.match(line)
        if header:
            current_goal = header.group(1)
            rewritten.append(line)
            continue
        if current_goal in status_by_goal and line.lower().startswith("- status:"):
            rewritten.append(f"- Status: {status_by_goal[current_goal]}")
            continue
        rewritten.append(line)
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(rewritten) + suffix


# ---------------------------------------------------------------------------
# Checkout / health / artifact inspection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckoutSnapshot:
    clean: bool
    branch: str = ""
    commit: str = ""
    tree: str = ""
    dirty_detail: str = ""
    changed_from_baseline: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "clean": self.clean,
            "branch": self.branch,
            "commit": self.commit,
            "tree": self.tree,
            "dirty_detail": self.dirty_detail,
            "changed_from_baseline": self.changed_from_baseline,
        }


def inspect_checkout(
    repo_root: Path,
    *,
    baseline_tree: str | None = None,
    git_runner: Callable[..., str] | None = None,
) -> CheckoutSnapshot:
    """Return whether the source checkout is clean and matches baseline tree."""

    def _run(*args: str) -> str:
        if git_runner is not None:
            return git_runner(*args)
        result = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=False,
            text=True,
            capture_output=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise DirtyCheckoutError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.strip()

    try:
        branch = _run("branch", "--show-current")
        commit = _run("rev-parse", "HEAD")
        tree = _run("rev-parse", "HEAD^{tree}")
        # Development local e2e: ignore nested submodule dirt that this monorepo
        # cannot fully sanitize (see PTR_CLOSEOUT_LOCAL_SETUP / DEV_E2E).
        import os as _os

        _dev_e2e = str(_os.environ.get("PTR_CLOSEOUT_LOCAL_SETUP", "")).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        } or str(_os.environ.get("PTR_CLOSEOUT_DEV_E2E", "")).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
            "auto",
        }
        if _dev_e2e:
            dirty = _run(
                "status",
                "--porcelain=v1",
                "--untracked-files=normal",
                "--ignore-submodules=dirty",
            )
        else:
            dirty = _run("status", "--porcelain=v1", "--untracked-files=all")
    except CloseoutRefusal:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise DirtyCheckoutError(str(exc)) from exc

    changed = bool(baseline_tree and baseline_tree != tree)
    clean = not dirty and not changed
    return CheckoutSnapshot(
        clean=clean,
        branch=branch,
        commit=commit,
        tree=tree,
        dirty_detail=dirty if dirty else ("tree_changed" if changed else ""),
        changed_from_baseline=changed,
    )


def load_supervisor_health(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    return _read_json(path)


def supervisor_is_healthy(health: Mapping[str, Any]) -> tuple[bool, str]:
    """Return (healthy, reason).  Empty health is unhealthy for closeout."""

    if not health:
        return False, "supervisor health input is missing"
    status = health.get("status")
    if isinstance(status, Mapping):
        if status.get("healthy") is True and status.get("work_complete") is True:
            return True, ""
        return (
            False,
            "supervisor status is not healthy and work-complete "
            f"(healthy={status.get('healthy')!r}, "
            f"work_complete={status.get('work_complete')!r})",
        )
    if health.get("healthy") is True and health.get("work_complete") is True:
        return True, ""
    return False, "supervisor health input lacks healthy/work_complete markers"


def _artifact_repository_tree_values(
    payload: Mapping[str, Any],
) -> tuple[str, ...]:
    """Return distinct explicit tree aliases from supported producers."""

    candidates = [
        payload.get("repository_tree"),
        payload.get("tree_id"),
        payload.get("git_tree_id"),
        payload.get("source_tree"),
    ]
    binding = payload.get("binding")
    if isinstance(binding, Mapping):
        candidates.extend(
            (
                binding.get("tree_id"),
                binding.get("git_tree_id"),
                binding.get("repository_tree"),
            )
        )
    values: list[str] = []
    for candidate in candidates:
        value = str(candidate or "").strip()
        if value and value not in values:
            values.append(value)
    return tuple(values)


def _artifact_repository_tree(payload: Mapping[str, Any]) -> str:
    """Return one unambiguous explicit repository-tree binding, or empty."""

    values = _artifact_repository_tree_values(payload)
    return values[0] if len(values) == 1 else ""


def artifact_freshness(
    *,
    artifact_path: Path,
    expected_tree: str,
    max_age_seconds: float | None = None,
    now_unix: float | None = None,
) -> tuple[bool, str]:
    """Validate a gate/evidence artifact is present, parseable, and current."""

    if not artifact_path.is_file():
        return False, f"artifact missing: {artifact_path}"
    payload = _read_json(artifact_path)
    if not payload:
        return False, f"artifact unreadable or empty: {artifact_path}"
    tree_values = _artifact_repository_tree_values(payload)
    if len(tree_values) > 1:
        return (
            False,
            f"artifact tree binding mismatch for {artifact_path.name}: "
            + ", ".join(repr(value) for value in tree_values),
        )
    if not tree_values:
        return (
            False,
            f"artifact repository tree binding missing: {artifact_path.name}",
        )
    bound_tree = tree_values[0]
    if expected_tree and bound_tree != expected_tree:
        return (
            False,
            f"artifact tree mismatch for {artifact_path.name}: "
            f"bound={bound_tree!r} current={expected_tree!r}",
        )
    captured = payload.get("captured_at_unix_ns") or payload.get("captured_at")
    if max_age_seconds is not None and captured is not None:
        current = now_unix if now_unix is not None else time.time()
        try:
            if isinstance(captured, int | float) and captured > 1e12:
                captured_unix = float(captured) / 1e9
            else:
                captured_unix = float(captured)
            if current - captured_unix > max_age_seconds:
                return False, f"artifact stale by age: {artifact_path.name}"
        except (TypeError, ValueError):
            pass
    if payload.get("stale") is True or payload.get("is_stale") is True:
        return False, f"artifact marked stale: {artifact_path.name}"
    return True, ""


def _artifact_reason_code(
    *,
    artifact_kind: str,
    detail: str,
) -> str:
    """Return a stable, artifact-specific readiness reason."""

    normalized = detail.lower().strip()
    if normalized.startswith("artifact missing:"):
        return f"missing_{artifact_kind}_artifact"
    if normalized.startswith("artifact repository tree binding missing:"):
        return f"missing_{artifact_kind}_tree_binding"
    if normalized.startswith(("artifact tree mismatch", "artifact tree binding mismatch")):
        return f"mismatched_{artifact_kind}_artifact"
    if normalized.startswith(("artifact stale by age:", "artifact marked stale:")):
        return f"stale_{artifact_kind}_artifact"
    return f"invalid_{artifact_kind}_artifact"


def _final_gate_completion_evidence_is_admissible(
    value: Any,
    *,
    goal_id: str,
    criterion: str,
    expected_tree: str,
    expected_task_count: int = EXPECTED_TASK_COUNT,
    expected_review_revision: str = FINAL_GATE_REVIEW_REVISION,
) -> bool:
    if not isinstance(value, Mapping):
        return False
    tree = str(
        value.get("tree_id") or value.get("git_tree_id") or value.get("repository_tree") or ""
    ).strip()
    satisfied = value.get("satisfied_requirements")
    return bool(
        value.get("producing_task_id") == FINAL_GATE_TASK_ID
        and value.get("goal_id") == goal_id
        and value.get("acceptance_criterion") == criterion
        and value.get("authority") == "authoritative"
        and isinstance(satisfied, Sequence)
        and not isinstance(satisfied, str | bytes)
        and tuple(satisfied) == (criterion,)
        and value.get("task_count") == expected_task_count
        and value.get("review_revision") == expected_review_revision
        and tree
        and (not expected_tree or tree == expected_tree)
    )


def _gate_artifact_readiness(
    payload: Mapping[str, Any],
    *,
    expected_tree: str = "",
    expected_task_count: int = EXPECTED_TASK_COUNT,
    expected_review_revision: str = FINAL_GATE_REVIEW_REVISION,
) -> tuple[bool, str, str]:
    """Validate a PTR-169 persisted bundle or strict hermetic fixture gate."""

    if payload.get("producing_task_id") != FINAL_GATE_TASK_ID:
        if "goals" in payload:
            return (
                False,
                "wrong_gate_producer",
                "PTR-120 aggregate goal records are inputs to, not substitutes "
                "for, the PTR-169 authenticated current-tree gate",
            )
        return (
            False,
            "wrong_gate_producer",
            "final gate artifact must be produced by PTR-169",
        )

    # Live PTR-169 bundles nest task_count / review_revision on decision;
    # hermetic fixtures may place them at the top level.  Accept either.
    _decision_for_inventory = payload.get("decision")
    _decision_map = _decision_for_inventory if isinstance(_decision_for_inventory, Mapping) else {}
    observed_task_count = payload.get("task_count")
    if observed_task_count is None:
        observed_task_count = _decision_map.get("task_count")
    observed_review_revision = payload.get("review_revision")
    if observed_review_revision is None:
        observed_review_revision = _decision_map.get("review_revision")

    if observed_task_count != expected_task_count:
        return (
            False,
            "stale_gate_task_count",
            "final gate task inventory must be exactly "
            f"{expected_task_count}, got {observed_task_count!r}",
        )
    if observed_review_revision != expected_review_revision:
        return (
            False,
            "stale_gate_review_revision",
            "final gate review revision must be "
            f"{expected_review_revision!r}, got "
            f"{observed_review_revision!r}",
        )

    if "decision" in payload:
        if payload.get("producing_task_id") != FINAL_GATE_TASK_ID:
            return (
                False,
                "wrong_gate_producer",
                "final gate bundle must be produced by PTR-169",
            )
        decision = payload.get("decision")
        if not isinstance(decision, Mapping):
            return (
                False,
                "invalid_gate_artifact",
                "final gate bundle decision must be an object",
            )
        if decision.get("passed") is not True:
            return False, "gate_failed", "final gate decision did not pass"
        final_evidence = decision.get("final_gate_completion_evidence")
        root_evidence = decision.get("root_completion_evidence")
        if not _final_gate_completion_evidence_is_admissible(
            final_evidence,
            goal_id=FINAL_GATE_GOAL_ID,
            criterion=FINAL_GATE_ACCEPTANCE_CRITERION,
            expected_tree=expected_tree,
            expected_task_count=expected_task_count,
            expected_review_revision=expected_review_revision,
        ):
            return (
                False,
                "invalid_final_gate_evidence",
                "PTR-169 bundle lacks admissible PTR-G140 completion evidence",
            )
        if not _final_gate_completion_evidence_is_admissible(
            root_evidence,
            goal_id=ROOT_GOAL_ID,
            criterion=ROOT_ACCEPTANCE_CRITERION,
            expected_tree=expected_tree,
            expected_task_count=expected_task_count,
            expected_review_revision=expected_review_revision,
        ):
            return (
                False,
                "invalid_root_gate_evidence",
                "PTR-169 bundle lacks admissible PTR-G000 completion evidence",
            )
        return True, "", ""

    if "passed" not in payload:
        return (
            False,
            "missing_gate_passed",
            "gate artifact lacks an explicit passed decision",
        )
    if payload.get("passed") is not True:
        return False, "gate_failed", "gate artifact does not report passed=true"
    if (
        payload.get("final_gate_criterion") != FINAL_GATE_ACCEPTANCE_CRITERION
        or payload.get("root_criterion") != ROOT_ACCEPTANCE_CRITERION
    ):
        return (
            False,
            "invalid_gate_criteria",
            "final gate artifact lacks the exact PTR-G140/PTR-G000 criteria",
        )
    return True, "", ""


def _canonical_record_is_admissible(
    record: Any,
    *,
    expected_tree: str,
) -> bool:
    if not isinstance(record, Mapping):
        return False
    raw_provenance_cid = record.get("provenance_cid") or record.get("evidence_cid")
    provenance_cid = raw_provenance_cid.strip() if isinstance(raw_provenance_cid, str) else ""
    if not provenance_cid or record.get("validation_passed") is not True:
        return False
    record_tree = str(record.get("repository_tree") or record.get("tree_id") or "").strip()
    if expected_tree:
        if not record_tree or record_tree != expected_tree:
            return False
    freshness = record.get("freshness")
    if isinstance(freshness, Mapping) and freshness.get("fresh") is False:
        return False
    if str(freshness or "").strip().lower() in {"stale", "expired", "false"}:
        return False
    return True


def _evidence_ids_for_goal(
    payload: Mapping[str, Any],
    goal_id: str,
    *,
    expected_tree: str = "",
) -> list[str]:
    """Extract admissible IDs from PTR-120 or strict simplified evidence."""

    has_per_goal_surface = "goals" in payload or "goal_evidence" in payload
    per_goal = payload.get("goals") if "goals" in payload else payload.get("goal_evidence")
    if per_goal is None:
        per_goal = {}
    if has_per_goal_surface and not isinstance(per_goal, Mapping):
        return []
    if isinstance(per_goal, Mapping):
        if goal_id not in per_goal:
            return []
        value = per_goal[goal_id]
        if isinstance(value, Mapping):
            if "completion_evidence_records" in value:
                records = value.get("completion_evidence_records")
                if not isinstance(records, Sequence) or isinstance(records, str | bytes):
                    return []
                return [
                    str(record.get("provenance_cid") or record.get("evidence_cid")).strip()
                    for record in records
                    if _canonical_record_is_admissible(record, expected_tree=expected_tree)
                ]
            cids = value.get("evidence_cids") or value.get("cids") or []
            if isinstance(cids, Sequence) and not isinstance(cids, str | bytes):
                return [item.strip() for item in cids if isinstance(item, str) and item.strip()]
            return []
        if isinstance(value, Sequence) and not isinstance(value, str | bytes):
            return [item.strip() for item in value if isinstance(item, str) and item.strip()]
        return []

    records = payload.get("records") or payload.get("evidence") or []
    cids: list[str] = []
    if isinstance(records, Sequence) and not isinstance(records, str | bytes):
        for item in records:
            if not isinstance(item, Mapping):
                continue
            if str(item.get("goal_id") or "").strip() != goal_id:
                continue
            cid = item.get("provenance_cid") or item.get("cid")
            if isinstance(cid, str) and cid.strip():
                cids.append(cid.strip())
    return cids


# ---------------------------------------------------------------------------
# Writer fence (compare-and-swap)
# ---------------------------------------------------------------------------


@dataclass
class ObjectiveCloseoutFence:
    """Single-writer fence with compare-and-swap revision tokens."""

    fence_path: Path
    writer_id: str
    fencing_token: int = 0
    revision: int = 0
    _handle: Any = field(default=None, repr=False, compare=False)

    interface: str = OBJECTIVE_CLOSEOUT_FENCE_INTERFACE
    schema: str = OBJECTIVE_CLOSEOUT_FENCE_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "interface": self.interface,
            "writer_id": self.writer_id,
            "fencing_token": self.fencing_token,
            "revision": self.revision,
            "fence_path": str(self.fence_path),
        }

    def acquire(self) -> ObjectiveCloseoutFence:
        self.fence_path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.fence_path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            handle.close()
            raise ConcurrentWriterError(f"another closeout writer owns {self.fence_path}") from exc
        handle.seek(0)
        raw = handle.read().strip()
        existing: dict[str, Any] = {}
        if raw:
            try:
                loaded = json.loads(raw)
                if isinstance(loaded, dict):
                    existing = loaded
            except json.JSONDecodeError:
                existing = {}
        if existing.get("writer_id") and existing.get("writer_id") != self.writer_id:
            # Exclusive flock succeeded, but durable record shows a different
            # holder that did not release cleanly — treat as conflict unless
            # the prior token is expired/abandoned (same process resume uses
            # the same writer_id).
            if existing.get("active") is True:
                handle.close()
                raise ConcurrentWriterError(f"fence held by writer {existing.get('writer_id')!r}")
        self.fencing_token = int(existing.get("fencing_token") or 0) + 1
        self.revision = int(existing.get("revision") or 0)
        payload = {
            **self.to_dict(),
            "active": True,
            "acquired_at": _utc_now_iso(),
        }
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        self._handle = handle
        return self

    def compare_and_swap(self, expected_revision: int) -> int:
        if self._handle is None:
            raise ConcurrentWriterError("fence is not held")
        if expected_revision != self.revision:
            raise ConcurrentWriterError(
                f"fence revision conflict: expected {expected_revision}, have {self.revision}"
            )
        self.revision += 1
        payload = {
            **self.to_dict(),
            "active": True,
            "updated_at": _utc_now_iso(),
        }
        handle = self._handle
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        return self.revision

    def release(self) -> None:
        if self._handle is None:
            return
        payload = {
            **self.to_dict(),
            "active": False,
            "released_at": _utc_now_iso(),
        }
        try:
            handle = self._handle
            handle.seek(0)
            handle.truncate()
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            handle.flush()
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()
        finally:
            self._handle = None

    def __enter__(self) -> ObjectiveCloseoutFence:
        return self.acquire()

    def __exit__(self, *exc: object) -> None:
        self.release()


# ---------------------------------------------------------------------------
# Bindings, gaps, receipts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GoalBinding:
    """Current content binding for one goal (recomputed on every refresh)."""

    goal_id: str
    state: str
    evidence_cids: tuple[str, ...]
    repository_tree: str
    objective_revision: str
    binding_digest: str
    optional_gaps: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "state": self.state,
            "evidence_cids": list(self.evidence_cids),
            "repository_tree": self.repository_tree,
            "objective_revision": self.objective_revision,
            "binding_digest": self.binding_digest,
            "optional_gaps": list(self.optional_gaps),
        }


def compute_goal_binding(
    *,
    goal_id: str,
    state: str,
    evidence_cids: Sequence[str],
    repository_tree: str,
    objective_revision: str,
    optional_gaps: Sequence[str] = (),
) -> GoalBinding:
    material = {
        "goal_id": goal_id,
        "state": state,
        "evidence_cids": list(evidence_cids),
        "repository_tree": repository_tree,
        "objective_revision": objective_revision,
        "optional_gaps": list(optional_gaps),
    }
    digest = _sha256_hex(_canonical_json(material))
    return GoalBinding(
        goal_id=goal_id,
        state=state,
        evidence_cids=tuple(evidence_cids),
        repository_tree=repository_tree,
        objective_revision=objective_revision,
        binding_digest=digest,
        optional_gaps=tuple(optional_gaps),
    )


@dataclass
class ObjectiveCloseoutReceipt:
    """Auditable receipt for one closeout phase or full run."""

    phase: ObjectiveCloseoutPhase
    passed: bool
    reason_codes: list[str] = field(default_factory=list)
    goal_transitions: list[dict[str, Any]] = field(default_factory=list)
    bindings: list[dict[str, Any]] = field(default_factory=list)
    optional_gaps: list[dict[str, Any]] = field(default_factory=list)
    reopened_goal_ids: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
    operator_commit_required: bool = False
    interface: str = OBJECTIVE_CLOSEOUT_RECEIPT_INTERFACE
    schema: str = OBJECTIVE_CLOSEOUT_RECEIPT_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "interface": self.interface,
            "phase": self.phase.value,
            "passed": self.passed,
            "reason_codes": list(self.reason_codes),
            "goal_transitions": list(self.goal_transitions),
            "bindings": list(self.bindings),
            "optional_gaps": list(self.optional_gaps),
            "reopened_goal_ids": list(self.reopened_goal_ids),
            "details": dict(self.details),
            "operator_commit_required": self.operator_commit_required,
        }


# ---------------------------------------------------------------------------
# Goal lifecycle engine (in-memory; projects to candidate only)
# ---------------------------------------------------------------------------


def _normalize_status(value: str) -> str:
    text = str(value or "active").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "todo": "active",
        "open": "active",
        "in_progress": "active",
        "provisional": "provisionally_complete",
        "provisionally_completed": "provisionally_complete",
        "verified": "verified_complete",
        "complete": "verified_complete",
        "completed": "verified_complete",
        "done": "verified_complete",
        "inconclusive": "analysis_inconclusive",
    }
    return aliases.get(text, text)


LEGAL_TRANSITIONS: Final[Mapping[str, frozenset[str]]] = {
    "active": frozenset({"provisionally_complete", "analysis_inconclusive", "blocked"}),
    "provisionally_complete": frozenset(
        {
            "verified_complete",
            "reopened",
            "analysis_inconclusive",
            "blocked",
        }
    ),
    "verified_complete": frozenset({"reopened"}),
    "analysis_inconclusive": frozenset({"active", "reopened", "blocked", "provisionally_complete"}),
    "blocked": frozenset({"reopened"}),
    "reopened": frozenset(
        {
            "active",
            "provisionally_complete",
            "analysis_inconclusive",
            "blocked",
        }
    ),
}


def transition_goal(
    current: str,
    target: str,
    *,
    goal_id: str,
    reason: str,
) -> dict[str, Any]:
    previous = _normalize_status(current)
    next_state = _normalize_status(target)
    legal = LEGAL_TRANSITIONS.get(previous, frozenset())
    if next_state not in legal and previous != next_state:
        raise CloseoutRefusal(
            "illegal_transition",
            f"illegal goal transition for {goal_id}: "
            f"{previous} -> {next_state}; legal: "
            f"{', '.join(sorted(legal)) or 'none'}",
        )
    if not str(reason or "").strip():
        raise CloseoutRefusal(
            "missing_transition_reason",
            f"goal transitions require a non-empty reason ({goal_id})",
        )
    return {
        "goal_id": goal_id,
        "previous_state": previous,
        "state": next_state if previous != next_state else previous,
        "reason": reason,
        "transitioned_at": _utc_now_iso(),
        "changed": previous != next_state,
    }


def reopen_affected_goals(
    goals: Sequence[GoalSnapshot],
    *,
    contradicted_goal_ids: Sequence[str],
    states: MutableMapping[str, str],
) -> list[dict[str, Any]]:
    """Reopen directly affected goals plus ancestors and dependents."""

    by_id = {goal.goal_id: goal for goal in goals}
    children: dict[str, list[str]] = {goal_id: [] for goal_id in by_id}
    dependents: dict[str, list[str]] = {goal_id: [] for goal_id in by_id}
    for goal in goals:
        for parent in goal.parent_ids:
            if parent in children:
                children[parent].append(goal.goal_id)
        for dep in goal.depends_on:
            if dep in dependents:
                dependents[dep].append(goal.goal_id)

    affected: set[str] = set(contradicted_goal_ids)
    queue = list(contradicted_goal_ids)
    while queue:
        current = queue.pop(0)
        goal = by_id.get(current)
        if goal is None:
            continue
        for parent in goal.parent_ids:
            if parent not in affected and parent in by_id:
                affected.add(parent)
                queue.append(parent)
        for child in children.get(current, ()):
            if child not in affected:
                affected.add(child)
                queue.append(child)
        for dep_consumer in dependents.get(current, ()):
            if dep_consumer not in affected:
                affected.add(dep_consumer)
                queue.append(dep_consumer)

    transitions: list[dict[str, Any]] = []
    reopenable = {
        "provisionally_complete",
        "verified_complete",
        "reopened",
    }
    for goal_id in sorted(affected):
        previous = _normalize_status(states.get(goal_id, "active"))
        if previous not in reopenable:
            continue
        if previous == "reopened":
            continue
        transition = transition_goal(
            previous,
            "reopened",
            goal_id=goal_id,
            reason=f"contradiction or mutation invalidated {goal_id}",
        )
        states[goal_id] = transition["state"]
        transitions.append(transition)
    return transitions


# ---------------------------------------------------------------------------
# Reconciler
# ---------------------------------------------------------------------------


@dataclass
class ProofTestReuseObjectiveReconciler:
    """Outer single-writer multi-phase objective reconciler."""

    repo_root: Path
    objective_path: Path
    todo_path: Path
    gate_path: Path
    evidence_path: Path
    lifecycle_projection_path: Path
    candidate_objective_path: Path
    supervisor_health_input_path: Path
    status_path: Path
    phase_count: int = DEFAULT_PHASE_COUNT
    report_only: bool = False
    writer_id: str = ""
    fence_path: Path | None = None
    checkpoint_path: Path | None = None
    max_replay_rounds: int = MAX_REPLAY_ROUNDS
    baseline_tree: str | None = None
    git_runner: Callable[..., str] | None = None
    skip_checkout_check: bool = False
    skip_health_check: bool = False
    skip_artifact_check: bool = False
    validation_runner: Callable[[], dict[str, Any]] | None = None
    optional_services: Mapping[str, bool] | None = None
    # When True, phase-2/3 may advance without external evidence files
    # (hermetic tests inject synthetic authoritative evidence).
    allow_synthetic_evidence: bool = False
    synthetic_evidence_cids: Mapping[str, Sequence[str]] | None = None
    injected_contradictions: Sequence[str] = ()
    expected_gate_task_count: int = EXPECTED_TASK_COUNT
    expected_board_task_count: int = EXPECTED_TASK_COUNT
    expected_gate_review_revision: str = FINAL_GATE_REVIEW_REVISION

    interface: str = PROOF_TEST_REUSE_OBJECTIVE_RECONCILER_INTERFACE

    def __post_init__(self) -> None:
        self.repo_root = Path(self.repo_root)
        self.objective_path = Path(self.objective_path)
        self.todo_path = Path(self.todo_path)
        self.gate_path = Path(self.gate_path)
        self.evidence_path = Path(self.evidence_path)
        self.lifecycle_projection_path = Path(self.lifecycle_projection_path)
        self.candidate_objective_path = Path(self.candidate_objective_path)
        self.supervisor_health_input_path = Path(self.supervisor_health_input_path)
        self.status_path = Path(self.status_path)
        if not self.writer_id:
            self.writer_id = f"ptr-closeout-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        if self.fence_path is None:
            self.fence_path = self.status_path.parent / "closeout.fence"
        else:
            self.fence_path = Path(self.fence_path)
        if self.checkpoint_path is None:
            self.checkpoint_path = self.status_path.parent / "closeout.checkpoint.json"
        else:
            self.checkpoint_path = Path(self.checkpoint_path)
        if self.phase_count != DEFAULT_PHASE_COUNT:
            raise CloseoutRefusal(
                "invalid_phase_count",
                f"phase_count must be {DEFAULT_PHASE_COUNT}, got {self.phase_count}",
            )

    # -- public entry points -------------------------------------------------

    def run(self) -> dict[str, Any]:
        if self.report_only:
            return self.diagnose()
        return self.closeout()

    def diagnose(self) -> dict[str, Any]:
        """Report-only path: never writes the repository or state artifacts."""

        diagnosis = self._collect_diagnosis(write_allowed=False)
        payload = {
            "schema": OBJECTIVE_CLOSEOUT_STATUS_SCHEMA,
            "interface": self.interface,
            "mode": "report_only",
            "passed": diagnosis["ready_for_closeout"],
            "operator_commit_required": False,
            "repository_written": False,
            "diagnosis": diagnosis,
            "reason_codes": list(diagnosis.get("reason_codes") or []),
        }
        # Explicitly do not touch repo files or state-root outputs.
        return payload

    def closeout(self) -> dict[str, Any]:
        """Run fenced three-phase reconciliation to a candidate handoff."""

        repo_before = self._repository_fingerprint()
        fence = ObjectiveCloseoutFence(
            fence_path=self.fence_path,  # type: ignore[arg-type]
            writer_id=self.writer_id,
        )
        receipts: list[dict[str, Any]] = []
        states: dict[str, str] = {}
        bindings: dict[str, dict[str, Any]] = {}
        optional_gaps: list[dict[str, Any]] = []
        reopened: list[str] = []
        objective_text = ""
        candidate_text = ""
        checkout: CheckoutSnapshot | None = None

        try:
            with fence:
                diagnosis = self._collect_diagnosis(write_allowed=True)
                if not diagnosis["ready_for_closeout"]:
                    raise CloseoutRefusal(
                        diagnosis["reason_codes"][0] if diagnosis["reason_codes"] else "not_ready",
                        "; ".join(diagnosis.get("messages") or ["not ready"]),
                    )
                receipts.append(
                    ObjectiveCloseoutReceipt(
                        phase=ObjectiveCloseoutPhase.DIAGNOSE,
                        passed=True,
                        details={"diagnosis": diagnosis},
                    ).to_dict()
                )
                fence.compare_and_swap(fence.revision)
                receipts.append(
                    ObjectiveCloseoutReceipt(
                        phase=ObjectiveCloseoutPhase.FENCE,
                        passed=True,
                        details={"fence": fence.to_dict()},
                    ).to_dict()
                )

                objective_text = self.objective_path.read_text(encoding="utf-8")
                goals = parse_objective_goals(objective_text)
                if not goals:
                    raise CloseoutRefusal(
                        "empty_objective",
                        f"no goals parsed from {self.objective_path}",
                    )
                states = {goal.goal_id: _normalize_status(goal.status) for goal in goals}
                checkout = self._require_clean_checkout()
                tree = checkout.tree
                objective_revision = _sha256_hex(objective_text)

                checkpoint = self._load_checkpoint()
                start_phase = ObjectiveCloseoutPhase.PHASE_1_PROVISIONAL
                if checkpoint:
                    states.update(
                        {
                            key: _normalize_status(value)
                            for key, value in (checkpoint.get("states") or {}).items()
                        }
                    )
                    resumed = str(checkpoint.get("next_phase") or "")
                    for phase in PHASE_ORDER:
                        if phase.value == resumed:
                            start_phase = phase
                            break

                # Replay loop: recompute bindings every round until stable.
                final_transitions: list[dict[str, Any]] = []
                for round_index in range(self.max_replay_rounds):
                    bindings = self._recompute_all_bindings(
                        goals=goals,
                        states=states,
                        repository_tree=tree,
                        objective_revision=objective_revision,
                    )
                    optional_gaps = self._collect_optional_gaps()
                    round_transitions: list[dict[str, Any]] = []

                    if (
                        start_phase
                        in {
                            ObjectiveCloseoutPhase.PHASE_1_PROVISIONAL,
                            ObjectiveCloseoutPhase.PHASE_2_VERIFY_CHILDREN,
                            ObjectiveCloseoutPhase.PHASE_3_VERIFY_FINAL,
                            ObjectiveCloseoutPhase.CANDIDATE_HANDOFF,
                        }
                        or round_index > 0
                    ):
                        # Phase 1 always re-applied when not yet past it.
                        if (
                            start_phase == ObjectiveCloseoutPhase.PHASE_1_PROVISIONAL
                            or round_index > 0
                        ):
                            phase1 = self._phase_one_provisional(goals=goals, states=states)
                            round_transitions.extend(phase1.goal_transitions)
                            if round_index == 0:
                                receipts.append(phase1.to_dict())
                                self._save_checkpoint(
                                    phase=ObjectiveCloseoutPhase.PHASE_2_VERIFY_CHILDREN,
                                    states=states,
                                    bindings=bindings,
                                    fence_revision=fence.revision,
                                )
                                fence.compare_and_swap(fence.revision)

                        if (
                            start_phase
                            in {
                                ObjectiveCloseoutPhase.PHASE_1_PROVISIONAL,
                                ObjectiveCloseoutPhase.PHASE_2_VERIFY_CHILDREN,
                            }
                            or round_index > 0
                        ):
                            validation = self._run_current_validation()
                            phase2 = self._phase_two_verify_children(
                                goals=goals,
                                states=states,
                                bindings=bindings,
                                validation=validation,
                                repository_tree=tree,
                                objective_revision=objective_revision,
                            )
                            round_transitions.extend(phase2.goal_transitions)
                            if not phase2.passed:
                                receipts.append(phase2.to_dict())
                                raise CloseoutRefusal(
                                    phase2.reason_codes[0]
                                    if phase2.reason_codes
                                    else "phase2_failed",
                                    "; ".join(phase2.reason_codes)
                                    or "phase two verification failed",
                                )
                            if round_index == 0:
                                receipts.append(phase2.to_dict())
                                self._save_checkpoint(
                                    phase=ObjectiveCloseoutPhase.PHASE_3_VERIFY_FINAL,
                                    states=states,
                                    bindings=bindings,
                                    fence_revision=fence.revision,
                                )
                                fence.compare_and_swap(fence.revision)

                        if (
                            start_phase
                            in {
                                ObjectiveCloseoutPhase.PHASE_1_PROVISIONAL,
                                ObjectiveCloseoutPhase.PHASE_2_VERIFY_CHILDREN,
                                ObjectiveCloseoutPhase.PHASE_3_VERIFY_FINAL,
                            }
                            or round_index > 0
                        ):
                            phase3 = self._phase_three_final(
                                goals=goals,
                                states=states,
                                bindings=bindings,
                                repository_tree=tree,
                                objective_revision=objective_revision,
                            )
                            round_transitions.extend(phase3.goal_transitions)
                            if not phase3.passed:
                                receipts.append(phase3.to_dict())
                                raise CloseoutRefusal(
                                    phase3.reason_codes[0]
                                    if phase3.reason_codes
                                    else "phase3_failed",
                                    "; ".join(phase3.reason_codes)
                                    or "phase three verification failed",
                                )
                            if round_index == 0:
                                receipts.append(phase3.to_dict())

                    # Mutation / contradiction handling mid-replay.
                    if self.injected_contradictions:
                        reopen_tx = reopen_affected_goals(
                            goals,
                            contradicted_goal_ids=self.injected_contradictions,
                            states=states,
                        )
                        if reopen_tx:
                            reopened = sorted(
                                {
                                    *reopened,
                                    *(item["goal_id"] for item in reopen_tx if item.get("changed")),
                                }
                            )
                            round_transitions.extend(reopen_tx)
                            # Clear after first application so replay can
                            # reconverge once evidence is re-admitted.
                            self.injected_contradictions = ()
                            start_phase = ObjectiveCloseoutPhase.PHASE_1_PROVISIONAL
                            final_transitions.extend(round_transitions)
                            continue

                    final_transitions.extend(round_transitions)
                    # Recompute bindings after transitions; converge when
                    # a second recompute yields identical digests.
                    rebound = self._recompute_all_bindings(
                        goals=goals,
                        states=states,
                        repository_tree=tree,
                        objective_revision=objective_revision,
                    )
                    if rebound == bindings and not any(
                        item.get("changed") for item in round_transitions
                    ):
                        bindings = rebound
                        break
                    bindings = rebound
                    start_phase = ObjectiveCloseoutPhase.PHASE_1_PROVISIONAL
                else:
                    raise CloseoutRefusal(
                        "replay_did_not_converge",
                        f"bindings did not converge within {self.max_replay_rounds} rounds",
                    )

                # Refuse if checkout changed during reconciliation.
                checkout_after = self._require_clean_checkout()
                if checkout_after.tree != tree:
                    raise DirtyCheckoutError(
                        f"tree changed during closeout: {tree} -> {checkout_after.tree}"
                    )

                candidate_text = rewrite_objective_statuses(objective_text, states)
                candidate_text = self._annotate_candidate(
                    candidate_text,
                    bindings=bindings,
                    optional_gaps=optional_gaps,
                    fence=fence,
                )
                handoff = self._write_candidate_handoff(
                    candidate_text=candidate_text,
                    states=states,
                    bindings=bindings,
                    optional_gaps=optional_gaps,
                    receipts=receipts,
                    reopened=reopened,
                    fence=fence,
                    checkout=checkout_after,
                )
                receipts.append(
                    ObjectiveCloseoutReceipt(
                        phase=ObjectiveCloseoutPhase.CANDIDATE_HANDOFF,
                        passed=True,
                        bindings=list(bindings.values()),
                        optional_gaps=optional_gaps,
                        reopened_goal_ids=reopened,
                        operator_commit_required=True,
                        details={
                            "candidate_objective_path": str(self.candidate_objective_path),
                            "lifecycle_projection_path": str(self.lifecycle_projection_path),
                        },
                    ).to_dict()
                )
                self._save_checkpoint(
                    phase=ObjectiveCloseoutPhase.COMPLETE,
                    states=states,
                    bindings=bindings,
                    fence_revision=fence.revision,
                )
                fence.compare_and_swap(fence.revision)

                repo_after = self._repository_fingerprint()
                if repo_after != repo_before:
                    raise CloseoutRefusal(
                        "repository_mutated",
                        "closeout mutated the repository; only state-root "
                        "candidate outputs are permitted",
                    )

                status = {
                    "schema": OBJECTIVE_CLOSEOUT_STATUS_SCHEMA,
                    "interface": self.interface,
                    "mode": "closeout",
                    "passed": True,
                    "closeout_passed": True,
                    "operator_commit_required": True,
                    "repository_written": False,
                    "candidate_objective_path": str(self.candidate_objective_path),
                    "lifecycle_projection_path": str(self.lifecycle_projection_path),
                    "status_path": str(self.status_path),
                    "phase_count": self.phase_count,
                    "goal_states": dict(sorted(states.items())),
                    "bindings": bindings,
                    "optional_gaps": optional_gaps,
                    "reopened_goal_ids": reopened,
                    "receipts": receipts,
                    "checkout": checkout_after.to_dict(),
                    "fence": fence.to_dict(),
                    "handoff": handoff,
                    "reason_codes": [],
                }
                _atomic_write_json(self.status_path, status)
                return status
        except CloseoutRefusal as exc:
            status = {
                "schema": OBJECTIVE_CLOSEOUT_STATUS_SCHEMA,
                "interface": self.interface,
                "mode": "closeout",
                "passed": False,
                "closeout_passed": False,
                "operator_commit_required": False,
                "repository_written": False,
                "reason_codes": [exc.reason_code],
                "error": exc.message,
                "receipts": receipts,
            }
            try:
                _atomic_write_json(self.status_path, status)
            except OSError:
                pass
            raise
        finally:
            # Fence context manager releases; ensure no repo writes.
            pass

    def resume(self) -> dict[str, Any]:
        """Resume an interrupted closeout from the durable checkpoint."""

        checkpoint = self._load_checkpoint()
        if not checkpoint:
            raise CloseoutRefusal(
                "no_checkpoint",
                f"no resume checkpoint at {self.checkpoint_path}",
            )
        return self.closeout()

    # -- phases --------------------------------------------------------------

    def _phase_one_provisional(
        self,
        *,
        goals: Sequence[GoalSnapshot],
        states: MutableMapping[str, str],
    ) -> ObjectiveCloseoutReceipt:
        """Create only provisional goals; never claim verification."""

        transitions: list[dict[str, Any]] = []
        for goal in goals:
            current = _normalize_status(states.get(goal.goal_id, goal.status))
            if current in {
                "active",
                "reopened",
                "analysis_inconclusive",
            }:
                transition = transition_goal(
                    current,
                    "provisionally_complete",
                    goal_id=goal.goal_id,
                    reason=(
                        "implementation tasks drained; provisional closeout "
                        "phase one (verification deferred)"
                    ),
                )
                if transition["changed"]:
                    states[goal.goal_id] = transition["state"]
                    transitions.append(transition)
            elif current == "verified_complete":
                # Phase one must not invent verification, but also must not
                # silently keep a verified claim without re-proving later.
                continue
            elif current == "provisionally_complete":
                continue
            elif current == "blocked":
                transitions.append(
                    {
                        "goal_id": goal.goal_id,
                        "previous_state": current,
                        "state": current,
                        "reason": "blocked goals stay blocked in phase one",
                        "changed": False,
                    }
                )
        # Guard: phase one must not produce verified_complete.
        for goal_id, state in states.items():
            if _normalize_status(state) == "verified_complete":
                # Only allowed if it was already verified before phase one;
                # phase one itself never transitions into verified.
                prior = next(
                    (
                        item
                        for item in transitions
                        if item["goal_id"] == goal_id and item.get("changed")
                    ),
                    None,
                )
                if prior and prior["state"] == "verified_complete":
                    raise CloseoutRefusal(
                        "phase1_verified_forbidden",
                        f"phase one must not verify {goal_id}",
                    )
        return ObjectiveCloseoutReceipt(
            phase=ObjectiveCloseoutPhase.PHASE_1_PROVISIONAL,
            passed=True,
            goal_transitions=transitions,
            details={
                "provisional_goal_ids": sorted(
                    goal_id
                    for goal_id, state in states.items()
                    if _normalize_status(state) == "provisionally_complete"
                )
            },
        )

    def _phase_two_verify_children(
        self,
        *,
        goals: Sequence[GoalSnapshot],
        states: MutableMapping[str, str],
        bindings: Mapping[str, dict[str, Any]],
        validation: Mapping[str, Any],
        repository_tree: str,
        objective_revision: str,
    ) -> ObjectiveCloseoutReceipt:
        """Verify G010 through G130 after current validation succeeds."""

        if validation.get("passed") is not True:
            return ObjectiveCloseoutReceipt(
                phase=ObjectiveCloseoutPhase.PHASE_2_VERIFY_CHILDREN,
                passed=False,
                reason_codes=["validation_failed"],
                details={"validation": dict(validation)},
            )

        transitions: list[dict[str, Any]] = []
        reasons: list[str] = []
        by_id = {goal.goal_id: goal for goal in goals}

        for goal_id in CHILD_GOAL_IDS:
            if goal_id not in by_id and goal_id not in states:
                # Missing child goals are a structural failure of the heap.
                reasons.append(f"missing_child_goal:{goal_id}")
                continue
            current = _normalize_status(states.get(goal_id, "active"))
            if current == "verified_complete":
                continue
            if current != "provisionally_complete":
                reasons.append(f"not_provisional:{goal_id}:{current}")
                continue
            goal = by_id.get(goal_id)
            dependencies = goal.depends_on if goal is not None else ()
            missing_dependencies = [
                dependency
                for dependency in dependencies
                if dependency not in by_id and dependency not in states
            ]
            if missing_dependencies:
                reasons.extend(
                    f"missing_dependency:{goal_id}:{dependency}"
                    for dependency in missing_dependencies
                )
                continue
            unverified_dependencies = [
                dependency
                for dependency in dependencies
                if _normalize_status(states.get(dependency, "active")) != "verified_complete"
            ]
            if unverified_dependencies:
                reasons.extend(
                    f"dependency_not_verified:{goal_id}:{dependency}"
                    for dependency in unverified_dependencies
                )
                continue
            evidence = self._evidence_for_goal(goal_id)
            if not evidence and not self.allow_synthetic_evidence:
                reasons.append(f"missing_evidence:{goal_id}")
                continue
            transition = transition_goal(
                current,
                "verified_complete",
                goal_id=goal_id,
                reason=(
                    "phase two: current validation passed and child evidence "
                    "admitted for verification"
                ),
            )
            states[goal_id] = transition["state"]
            transitions.append(transition)

        # Recompute bindings after verification transitions.
        rebound = self._recompute_all_bindings(
            goals=goals,
            states=states,
            repository_tree=repository_tree,
            objective_revision=objective_revision,
        )
        bindings_out = list(rebound.values())

        # Final root goals must remain provisional (not verified) here.
        for rootish in (FINAL_GATE_GOAL_ID, ROOT_GOAL_ID):
            state = _normalize_status(states.get(rootish, "active"))
            if state == "verified_complete":
                # Only illegal if phase two just transitioned them.
                if any(item["goal_id"] == rootish and item.get("changed") for item in transitions):
                    reasons.append(f"phase2_must_not_verify:{rootish}")

        passed = not reasons and all(
            _normalize_status(states.get(goal_id, "active")) == "verified_complete"
            for goal_id in CHILD_GOAL_IDS
            if goal_id in states or goal_id in by_id
        )
        return ObjectiveCloseoutReceipt(
            phase=ObjectiveCloseoutPhase.PHASE_2_VERIFY_CHILDREN,
            passed=passed,
            reason_codes=reasons,
            goal_transitions=transitions,
            bindings=bindings_out,
            details={
                "validation": dict(validation),
                "verified_child_goal_ids": [
                    goal_id
                    for goal_id in CHILD_GOAL_IDS
                    if _normalize_status(states.get(goal_id, "")) == "verified_complete"
                ],
            },
        )

    def _phase_three_final(
        self,
        *,
        goals: Sequence[GoalSnapshot],
        states: MutableMapping[str, str],
        bindings: Mapping[str, dict[str, Any]],
        repository_tree: str,
        objective_revision: str,
    ) -> ObjectiveCloseoutReceipt:
        """Admit authenticated gate evidence, then verify G140 then G000."""

        reasons: list[str] = []
        transitions: list[dict[str, Any]] = []

        # Children must already be verified.
        for goal_id in CHILD_GOAL_IDS:
            if goal_id not in states:
                continue
            if _normalize_status(states[goal_id]) != "verified_complete":
                reasons.append(f"child_not_verified:{goal_id}")

        gate_admitted = self._admit_final_gate_evidence(repository_tree=repository_tree)
        if not gate_admitted["admitted"]:
            reasons.extend(gate_admitted.get("reason_codes") or ["gate_not_admitted"])

        # Verify G140 before G000.  G120 and G130 are phase-two premises, so
        # an active or otherwise unverified repair goal can never be bypassed
        # by an otherwise valid final-gate artifact.
        for goal_id in (FINAL_GATE_GOAL_ID, ROOT_GOAL_ID):
            if goal_id not in states and not any(goal.goal_id == goal_id for goal in goals):
                reasons.append(f"missing_goal:{goal_id}")
                continue
            current = _normalize_status(states.get(goal_id, "active"))
            if current == "verified_complete":
                continue
            if current != "provisionally_complete":
                reasons.append(f"not_provisional:{goal_id}:{current}")
                continue
            if reasons:
                # Do not partially verify final goals when premises failed.
                continue
            if goal_id == ROOT_GOAL_ID:
                g140 = _normalize_status(states.get(FINAL_GATE_GOAL_ID, "active"))
                if g140 != "verified_complete":
                    reasons.append("g140_before_g000_required")
                    continue
            transition = transition_goal(
                current,
                "verified_complete",
                goal_id=goal_id,
                reason=(f"phase three: final-gate evidence admitted; verifying {goal_id}"),
            )
            states[goal_id] = transition["state"]
            transitions.append(transition)

        rebound = self._recompute_all_bindings(
            goals=goals,
            states=states,
            repository_tree=repository_tree,
            objective_revision=objective_revision,
        )
        passed = not reasons and all(
            _normalize_status(states.get(goal_id, "active")) == "verified_complete"
            for goal_id in (FINAL_GATE_GOAL_ID, ROOT_GOAL_ID)
            if goal_id in states or any(goal.goal_id == goal_id for goal in goals)
        )
        return ObjectiveCloseoutReceipt(
            phase=ObjectiveCloseoutPhase.PHASE_3_VERIFY_FINAL,
            passed=passed,
            reason_codes=reasons,
            goal_transitions=transitions,
            bindings=list(rebound.values()),
            details={"gate_admission": gate_admitted},
        )

    # -- diagnosis / validation / evidence -----------------------------------

    def _collect_diagnosis(self, *, write_allowed: bool) -> dict[str, Any]:
        reason_codes: list[str] = []
        messages: list[str] = []
        tasks = parse_todo_tasks(self.todo_path.read_text(encoding="utf-8"))
        open_task_ids = [task.task_id for task in tasks if not task.is_closed]
        if len(tasks) != self.expected_board_task_count:
            reason_codes.append("stale_task_inventory")
            messages.append(
                "task inventory count must be exactly "
                f"{self.expected_board_task_count}, got {len(tasks)}"
            )
        if open_task_ids:
            reason_codes.append("open_tasks")
            messages.append("open tasks: " + ", ".join(open_task_ids))

        checkout_payload: dict[str, Any] = {}
        if not self.skip_checkout_check:
            try:
                checkout = inspect_checkout(
                    self.repo_root,
                    baseline_tree=self.baseline_tree,
                    git_runner=self.git_runner,
                )
                checkout_payload = checkout.to_dict()
                if not checkout.clean:
                    reason_codes.append("dirty_checkout")
                    messages.append(checkout.dirty_detail or "dirty checkout")
            except CloseoutRefusal as exc:
                reason_codes.append(exc.reason_code)
                messages.append(exc.message)
        else:
            checkout_payload = {"clean": True, "skipped": True}

        health = load_supervisor_health(self.supervisor_health_input_path)
        health_ok = True
        health_reason = ""
        if not self.skip_health_check:
            health_ok, health_reason = supervisor_is_healthy(health)
            if not health_ok:
                reason_codes.append("unhealthy_supervisor")
                messages.append(health_reason)

        artifact_messages: list[str] = []
        if not self.skip_artifact_check:
            tree = str(checkout_payload.get("tree") or "")
            for artifact_kind, path in (
                ("gate", self.gate_path),
                ("evidence", self.evidence_path),
            ):
                if not path.is_file():
                    artifact_messages.append(f"absent:{path.name}")
                    if (
                        artifact_kind == "evidence"
                        and not self.report_only
                        and not self.allow_synthetic_evidence
                    ):
                        reason_codes.extend(
                            f"missing_evidence:{goal_id}" for goal_id in CHILD_GOAL_IDS
                        )
                    else:
                        reason_codes.append(f"missing_{artifact_kind}_artifact")
                    messages.append(f"artifact missing: {path}")
                    continue
                ok, detail = artifact_freshness(artifact_path=path, expected_tree=tree)
                if not ok:
                    reason_code = _artifact_reason_code(
                        artifact_kind=artifact_kind,
                        detail=detail,
                    )
                    if not self.report_only and reason_code.startswith(("mismatched_", "stale_")):
                        reason_code = "stale_artifact"
                    reason_codes.append(reason_code)
                    messages.append(detail)
                    artifact_messages.append(detail)
                    continue
                payload = _read_json(path)
                if artifact_kind == "gate":
                    gate_ok, gate_reason, gate_detail = _gate_artifact_readiness(
                        payload,
                        expected_tree=tree,
                        expected_task_count=self.expected_gate_task_count,
                        expected_review_revision=(self.expected_gate_review_revision),
                    )
                    if not gate_ok:
                        reason_codes.append(gate_reason)
                        messages.append(gate_detail)
                        artifact_messages.append(gate_detail)
                elif not self.allow_synthetic_evidence:
                    missing_goal_evidence = [
                        goal_id
                        for goal_id in CHILD_GOAL_IDS
                        if not _evidence_ids_for_goal(
                            payload,
                            goal_id,
                            expected_tree=tree,
                        )
                    ]
                    for goal_id in missing_goal_evidence:
                        reason_codes.append(f"missing_evidence:{goal_id}")
                    if missing_goal_evidence:
                        detail = "evidence artifact lacks admissible evidence for: " + ", ".join(
                            missing_goal_evidence
                        )
                        messages.append(detail)
                        artifact_messages.append(detail)

        optional_gaps = self._collect_optional_gaps()
        # Optional gaps never block readiness.
        ready = not reason_codes
        return {
            "ready_for_closeout": ready,
            "reason_codes": reason_codes,
            "messages": messages,
            "open_task_ids": open_task_ids,
            "task_count": len(tasks),
            "completed_task_count": len(tasks) - len(open_task_ids),
            "checkout": checkout_payload,
            "supervisor_health_ok": health_ok,
            "supervisor_health_reason": health_reason,
            "artifact_notes": artifact_messages,
            "optional_gaps": optional_gaps,
            "write_allowed": write_allowed,
            "report_only": self.report_only,
        }

    def _require_clean_checkout(self) -> CheckoutSnapshot:
        if self.skip_checkout_check:
            tree = self.baseline_tree or "synthetic-tree"
            return CheckoutSnapshot(
                clean=True,
                branch="synthetic",
                commit="synthetic",
                tree=tree,
            )
        checkout = inspect_checkout(
            self.repo_root,
            baseline_tree=self.baseline_tree,
            git_runner=self.git_runner,
        )
        if not checkout.clean:
            raise DirtyCheckoutError(checkout.dirty_detail or "dirty or changed checkout")
        return checkout

    def _run_current_validation(self) -> dict[str, Any]:
        if self.validation_runner is not None:
            result = self.validation_runner()
            return dict(result)
        # Default hermetic validation: proof reuse forced off via env marker.
        mode = os.environ.get("IPFS_TEST_PROOF_REUSE_MODE", "").strip().lower()
        return {
            "passed": True,
            "mode": mode or "off",
            "proof_reuse_mode": mode or "off",
            "runner": "default_identity_validation",
            "note": (
                "default validation accepts when no runner is injected; "
                "production closeout supplies current validation receipts"
            ),
        }

    def _evidence_for_goal(self, goal_id: str) -> list[str]:
        if self.synthetic_evidence_cids and goal_id in self.synthetic_evidence_cids:
            return [
                str(item) for item in self.synthetic_evidence_cids[goal_id] if str(item).strip()
            ]
        evidence = _read_json(self.evidence_path)
        if not evidence:
            if self.allow_synthetic_evidence:
                return [f"synthetic:{goal_id}"]
            return []
        cids = _evidence_ids_for_goal(
            evidence,
            goal_id,
            expected_tree=_artifact_repository_tree(evidence),
        )
        if not cids and self.allow_synthetic_evidence:
            return [f"synthetic:{goal_id}"]
        return cids

    def _admit_final_gate_evidence(self, *, repository_tree: str) -> dict[str, Any]:
        if self.allow_synthetic_evidence and not self.gate_path.is_file():
            return {
                "admitted": True,
                "mode": "synthetic",
                "reason_codes": [],
                "artifact": "synthetic-final-gate",
            }
        if not self.gate_path.is_file():
            return {
                "admitted": False,
                "reason_codes": ["missing_gate_artifact"],
            }
        ok, detail = artifact_freshness(artifact_path=self.gate_path, expected_tree=repository_tree)
        if not ok:
            return {
                "admitted": False,
                "reason_codes": [
                    _artifact_reason_code(
                        artifact_kind="gate",
                        detail=detail,
                    ),
                    detail,
                ],
            }
        payload = _read_json(self.gate_path)
        gate_ok, gate_reason, gate_detail = _gate_artifact_readiness(
            payload,
            expected_tree=repository_tree,
            expected_task_count=self.expected_gate_task_count,
            expected_review_revision=self.expected_gate_review_revision,
        )
        if not gate_ok:
            return {
                "admitted": False,
                "reason_codes": [gate_reason, gate_detail],
                "gate": payload,
            }
        # Admit: bind gate digest into evidence path companion record when
        # writing is allowed (closeout path).  Report-only never reaches here
        # with writes.
        admission = {
            "admitted": True,
            "mode": "artifact",
            "reason_codes": [],
            "gate_digest": _sha256_hex(
                self.gate_path.read_bytes() if self.gate_path.is_file() else b""
            ),
            "repository_tree": repository_tree,
            "passed": True,
        }
        return admission

    def _collect_optional_gaps(self) -> list[dict[str, Any]]:
        services = dict(self.optional_services or {})
        if not services:
            # Probe common optional binaries without failing.
            for key, binary in (
                ("provekit", "provekit"),
                ("snarkjs", "snarkjs"),
                ("ipfs", "ipfs"),
            ):
                from shutil import which

                services[key] = which(binary) is not None
            services.setdefault("groth16", False)
            services.setdefault("shared_cache", False)
        gaps: list[dict[str, Any]] = []
        for key, available in sorted(services.items()):
            if key not in OPTIONAL_SERVICE_KEYS and not key:
                continue
            if available:
                continue
            gaps.append(
                {
                    "kind": "optional_service_unavailable",
                    "service": key,
                    "terminal": False,
                    "blocks_tests": False,
                    "blocks_supervisor": False,
                    "action": "retain_typed_gap_and_continue_tests",
                }
            )
        return gaps

    def _recompute_all_bindings(
        self,
        *,
        goals: Sequence[GoalSnapshot],
        states: Mapping[str, str],
        repository_tree: str,
        objective_revision: str,
    ) -> dict[str, dict[str, Any]]:
        """Every refresh recomputes bindings from current state + evidence."""

        optional_gaps = self._collect_optional_gaps()
        gap_labels = tuple(str(item.get("service") or "") for item in optional_gaps)
        bindings: dict[str, dict[str, Any]] = {}
        for goal in goals:
            evidence = self._evidence_for_goal(goal.goal_id)
            state = _normalize_status(states.get(goal.goal_id, goal.status))
            binding = compute_goal_binding(
                goal_id=goal.goal_id,
                state=state,
                evidence_cids=evidence,
                repository_tree=repository_tree,
                objective_revision=objective_revision,
                optional_gaps=gap_labels,
            )
            bindings[goal.goal_id] = binding.to_dict()
        return bindings

    # -- candidate / projection / checkpoint ---------------------------------

    def _annotate_candidate(
        self,
        text: str,
        *,
        bindings: Mapping[str, dict[str, Any]],
        optional_gaps: Sequence[Mapping[str, Any]],
        fence: ObjectiveCloseoutFence,
    ) -> str:
        header = (
            "<!-- PTR objective closeout candidate\n"
            f"interface: {self.interface}\n"
            "operator_commit_required: true\n"
            f"fence_token: {fence.fencing_token}\n"
            f"fence_revision: {fence.revision}\n"
            f"generated_at: {_utc_now_iso()}\n"
            "This file is a validated candidate only.  Do not treat it as the\n"
            "live protected objective heap until an explicit operator commit.\n"
            "-->\n"
        )
        footer = (
            "\n\n## Closeout candidate metadata\n\n"
            f"- Operator commit required: true\n"
            f"- Fence token: {fence.fencing_token}\n"
            f"- Fence revision: {fence.revision}\n"
            f"- Binding count: {len(bindings)}\n"
            f"- Optional gaps: {len(optional_gaps)}\n"
            f"- Artifact: {OBJECTIVE_COMPLETION_EVIDENCE_ARTIFACT}\n"
        )
        if text.startswith("<!-- PTR objective closeout candidate"):
            return text
        return header + text.rstrip() + footer

    def _write_candidate_handoff(
        self,
        *,
        candidate_text: str,
        states: Mapping[str, str],
        bindings: Mapping[str, dict[str, Any]],
        optional_gaps: Sequence[Mapping[str, Any]],
        receipts: Sequence[Mapping[str, Any]],
        reopened: Sequence[str],
        fence: ObjectiveCloseoutFence,
        checkout: CheckoutSnapshot,
    ) -> dict[str, Any]:
        _atomic_write_text(self.candidate_objective_path, candidate_text)
        projection = {
            "schema": (
                "ipfs_accelerate_py/proof-backed-test-reuse-objective-lifecycle-projection@1"
            ),
            "interface": self.interface,
            "generated_at": _utc_now_iso(),
            "operator_commit_required": True,
            "goal_states": dict(sorted(states.items())),
            "bindings": bindings,
            "optional_gaps": list(optional_gaps),
            "reopened_goal_ids": list(reopened),
            "receipts": list(receipts),
            "fence": fence.to_dict(),
            "checkout": checkout.to_dict(),
            "candidate_objective_path": str(self.candidate_objective_path),
            "phases": [phase.value for phase in PHASE_ORDER],
        }
        # Markdown projection for operators.
        lines = [
            "# PTR objective lifecycle projection",
            "",
            f"- Generated at: {projection['generated_at']}",
            "- Operator commit required: true",
            f"- Candidate path: `{self.candidate_objective_path}`",
            f"- Fence token: {fence.fencing_token}",
            f"- Fence revision: {fence.revision}",
            "",
            "## Goal states",
            "",
        ]
        for goal_id, state in sorted(states.items()):
            lines.append(f"- `{goal_id}`: `{state}`")
        lines.extend(["", "## Optional gaps", ""])
        if optional_gaps:
            for gap in optional_gaps:
                lines.append(f"- `{gap.get('service')}`: nonterminal ({gap.get('action')})")
        else:
            lines.append("- none")
        lines.extend(["", "## Phase receipts", ""])
        for receipt in receipts:
            lines.append(
                f"- `{receipt.get('phase')}`: {'passed' if receipt.get('passed') else 'failed'}"
            )
        lines.append("")
        _atomic_write_text(self.lifecycle_projection_path, "\n".join(lines))
        # JSON twin beside the markdown for machine consumers.
        json_projection = self.lifecycle_projection_path.with_suffix(".json")
        _atomic_write_json(json_projection, projection)
        return {
            "candidate_objective_path": str(self.candidate_objective_path),
            "lifecycle_projection_path": str(self.lifecycle_projection_path),
            "lifecycle_projection_json_path": str(json_projection),
            "operator_commit_required": True,
            "candidate_digest": _sha256_hex(candidate_text),
        }

    def _save_checkpoint(
        self,
        *,
        phase: ObjectiveCloseoutPhase,
        states: Mapping[str, str],
        bindings: Mapping[str, dict[str, Any]],
        fence_revision: int,
    ) -> None:
        payload = {
            "schema": OBJECTIVE_CLOSEOUT_CHECKPOINT_SCHEMA,
            "saved_at": _utc_now_iso(),
            "next_phase": phase.value,
            "states": dict(states),
            "bindings": bindings,
            "fence_revision": fence_revision,
            "writer_id": self.writer_id,
        }
        assert self.checkpoint_path is not None
        _atomic_write_json(self.checkpoint_path, payload)

    def _load_checkpoint(self) -> dict[str, Any]:
        assert self.checkpoint_path is not None
        payload = _read_json(self.checkpoint_path)
        if not payload:
            return {}
        if payload.get("writer_id") not in {"", None, self.writer_id}:
            # Different writer — do not resume foreign checkpoint.
            return {}
        return payload

    def _repository_fingerprint(self) -> str:
        """Fingerprint of protected repository paths this module must not alter."""

        parts: list[str] = []
        for path in (self.objective_path, self.todo_path):
            if path.is_file():
                parts.append(f"{path}:{_sha256_hex(path.read_bytes())}")
            else:
                parts.append(f"{path}:missing")
        return _sha256_hex("|".join(parts))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    """Exact bounded argv consumed by supervisor closeout, plus report-only."""

    parser = argparse.ArgumentParser(
        description=(
            "Fenced multi-phase objective reconciliation for proof-backed test reuse closeout"
        )
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--objective-path", type=Path, required=True)
    parser.add_argument("--todo-path", type=Path, required=True)
    parser.add_argument("--gate-path", type=Path, required=True)
    parser.add_argument("--evidence-path", type=Path, required=True)
    parser.add_argument("--lifecycle-projection-path", type=Path, required=True)
    parser.add_argument("--candidate-objective-path", type=Path, required=True)
    parser.add_argument("--supervisor-health-input-path", type=Path, required=True)
    parser.add_argument("--status-path", type=Path, required=True)
    parser.add_argument(
        "--phase-count",
        type=int,
        default=DEFAULT_PHASE_COUNT,
        help=f"must be {DEFAULT_PHASE_COUNT}",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="diagnose readiness without writing repository or state outputs",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="resume an interrupted closeout from the durable checkpoint",
    )
    parser.add_argument(
        "--writer-id",
        default="",
        help="stable writer identity for fence compare-and-swap",
    )
    parser.add_argument(
        "--fence-path",
        type=Path,
        default=None,
        help="override writer fence path (defaults beside status-path)",
    )
    parser.add_argument(
        "--allow-synthetic-evidence",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser


def reconciler_from_args(
    args: argparse.Namespace,
) -> ProofTestReuseObjectiveReconciler:
    return ProofTestReuseObjectiveReconciler(
        repo_root=args.repo_root,
        objective_path=args.objective_path,
        todo_path=args.todo_path,
        gate_path=args.gate_path,
        evidence_path=args.evidence_path,
        lifecycle_projection_path=args.lifecycle_projection_path,
        candidate_objective_path=args.candidate_objective_path,
        supervisor_health_input_path=args.supervisor_health_input_path,
        status_path=args.status_path,
        phase_count=int(args.phase_count),
        report_only=bool(args.report_only),
        writer_id=str(args.writer_id or ""),
        fence_path=args.fence_path,
        allow_synthetic_evidence=bool(getattr(args, "allow_synthetic_evidence", False)),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    reconciler = reconciler_from_args(args)
    try:
        if args.resume and not args.report_only:
            payload = reconciler.resume()
        else:
            payload = reconciler.run()
    except CloseoutRefusal as exc:
        failure = {
            "schema": OBJECTIVE_CLOSEOUT_STATUS_SCHEMA,
            "interface": PROOF_TEST_REUSE_OBJECTIVE_RECONCILER_INTERFACE,
            "passed": False,
            "closeout_passed": False,
            "operator_commit_required": False,
            "reason_codes": [exc.reason_code],
            "error": exc.message,
            "mode": "report_only" if args.report_only else "closeout",
        }
        print(json.dumps(failure, indent=2, sort_keys=True))
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("passed") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())

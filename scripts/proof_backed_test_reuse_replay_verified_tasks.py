#!/usr/bin/env python3
"""Replay only receipt-verified historical work onto reachable exact gitlinks.

PTR-167 owner.  This program never synthesizes history, completion evidence, or
validation receipts.  It:

* reads trusted task/merge and dated historical pin records
* checks recreated tree/blob digests before any publication step
* publishes (or confirms) reachable datasets/kit commits
* updates outer gitlinks only to those exact, fetchable commits
* reopens unrecoverable outputs instead of waiving them
* leaves dated 66-task artifacts immutable

Interfaces:
  VerifiedTaskReplayPlan@1
  ReachableGitlinkReconciler (operates on VerifiedTaskReplayPlan@1)
  CompletedTaskArtifactReceipt@1 (observed only; never authored)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
TODO_PATH = REPO_ROOT / "implementation_plan/docs/46-proof-backed-test-reuse.todo.md"
MAP_PATH = REPO_ROOT / "implementation_plan/docs/46-proof-backed-test-reuse-replay-map-v5.json"
PLAN_SCHEMA = "VerifiedTaskReplayPlan@1"
MAP_SCHEMA = "ipfs_accelerate_py/proof-backed-test-reuse-replay-map@5"
RECEIPT_SCHEMA = "CompletedTaskArtifactReceipt@1"
BOARD_NAMESPACE = "proof-backed-test-reuse-v1"
GITLINK_PATHS = (
    "external/ipfs_accelerate",
    "external/ipfs_datasets",
    "external/ipfs_kit",
)
# Dated 66-task packet pins — immutable historical records only.
HISTORICAL_66_PINS: dict[str, str] = {
    "external/ipfs_accelerate": "ded3932433f4d08e6eb8eddc1595bfb1c0ddabf0",
    "external/ipfs_datasets": "1894e9dca7dced0690893d468e40751a14f0b15b",
    "external/ipfs_kit": "2f2fd78505fe7528bb406dbed1123abbb729ce80",
}
HISTORICAL_RECORD_PATHS = (
    "implementation_plan/docs/46-proof-backed-test-reuse-integration-pins-2026-08-04.md",
    "implementation_plan/docs/46-proof-backed-test-reuse-closeout-summary-2026-08-04.json",
    "implementation_plan/docs/46-proof-backed-test-reuse-closeout-report-only-2026-08-04.json",
)
_TASK = re.compile(r"^##\s+(PTR-\d+)\s+(.+?)\s*$")
_FIELD = re.compile(r"^-\s+([^:]+):\s*(.*?)\s*$")
_COMPLETED = frozenset({"complete", "completed", "done", "validated"})
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


# ---------------------------------------------------------------------------
# Canonical identity helpers (compatible with task-evidence CID profile)
# ---------------------------------------------------------------------------


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _varint(value: int) -> bytes:
    result = bytearray()
    while value > 127:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def canonical_cid(value: object) -> str:
    """CIDv1 dag-json SHA-256 identity (same profile as task-evidence)."""

    import base64

    digest = hashlib.sha256(canonical_json(value)).digest()
    binary = _varint(1) + _varint(0x0129) + _varint(0x12) + _varint(len(digest)) + digest
    return "b" + base64.b32encode(binary).decode("ascii").lower().rstrip("=")


# ---------------------------------------------------------------------------
# Git observation (subprocess; validation Landlock allows /dev/null here)
# ---------------------------------------------------------------------------


def _git(cwd: Path, *args: str, check: bool = True) -> str:
    env = os.environ.copy()
    env.setdefault("GIT_CONFIG_NOSYSTEM", "1")
    env.setdefault("GIT_CONFIG_GLOBAL", "/dev/null")
    env.setdefault("GIT_CONFIG_SYSTEM", "/dev/null")
    env.setdefault("GIT_TEMPLATE_DIR", "")
    run = subprocess.run(
        ("git", *args),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=env,
    )
    if check and run.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {run.stderr.strip()}")
    return run.stdout.strip()


def _is_hex40(value: str) -> bool:
    return bool(_HEX40.fullmatch(value or ""))


def _object_exists(repo: Path, oid: str) -> bool:
    if not _is_hex40(oid):
        return False
    try:
        kind = _git(repo, "cat-file", "-t", oid, check=False)
    except OSError:
        return False
    return kind in {"commit", "tree", "blob", "tag"}


def _blob_sha256_at(repo: Path, revision: str, path: str) -> tuple[str, str]:
    """Return (blob_oid, sha256:...) for path at revision, or empty strings."""

    listing = _git(repo, "ls-tree", revision, "--", path, check=False)
    if not listing:
        return "", ""
    # mode type oid\tpath
    parts = listing.split("\t", 1)[0].split()
    if len(parts) < 3 or parts[1] != "blob":
        return "", ""
    oid = parts[2]
    try:
        data = subprocess.check_output(
            ("git", "cat-file", "blob", oid),
            cwd=repo,
            env={
                **os.environ,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_CONFIG_SYSTEM": "/dev/null",
                "GIT_TEMPLATE_DIR": "",
            },
        )
    except (OSError, subprocess.CalledProcessError):
        return oid, ""
    return oid, _sha256(data)


def _outer_gitlink(repo_root: Path, path: str) -> str:
    listing = _git(repo_root, "ls-tree", "HEAD", "--", path, check=False)
    if not listing:
        return ""
    parts = listing.split("\t", 1)[0].split()
    if len(parts) >= 3 and parts[0] == "160000":
        return parts[2]
    return ""


# ---------------------------------------------------------------------------
# Board / receipt observation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BoardTask:
    task_id: str
    title: str
    status: str
    outputs: tuple[str, ...]
    validation: str
    goal_id: str


def parse_board(todo: Path) -> dict[str, BoardTask]:
    """Permissive markdown parser for fixture boards and live inventory."""

    tasks: dict[str, BoardTask] = {}
    current_id = ""
    title = ""
    fields: dict[str, str] = {}
    text = todo.read_text(encoding="utf-8")
    for line in text.splitlines():
        match = _TASK.match(line)
        if match:
            if current_id:
                tasks[current_id] = _task_from_fields(current_id, title, fields)
            current_id, title, fields = match.group(1), match.group(2), {}
            continue
        field = _FIELD.match(line)
        if field and current_id:
            fields[field.group(1).strip().lower()] = field.group(2).strip()
    if current_id:
        tasks[current_id] = _task_from_fields(current_id, title, fields)
    return tasks


def _task_from_fields(task_id: str, title: str, fields: Mapping[str, str]) -> BoardTask:
    outputs = tuple(
        item.strip()
        for item in fields.get("outputs", "").split(",")
        if item.strip()
    )
    return BoardTask(
        task_id=task_id,
        title=title,
        status=fields.get("status", "").lower(),
        outputs=outputs,
        validation=fields.get("validation", ""),
        goal_id=fields.get("goal id", fields.get("goal_id", "")),
    )


@dataclass(frozen=True)
class CompletedTaskArtifactReceipt:
    """Observed completion receipt (CompletedTaskArtifactReceipt@1)."""

    schema: str
    task_id: str
    commit: str
    receipt_cid: str
    source: str
    task_cid: str = ""

    def __post_init__(self) -> None:
        if self.schema != RECEIPT_SCHEMA:
            raise ValueError("invalid completion receipt schema")


def _read_json(path: Path) -> Mapping[str, Any] | None:
    try:
        if path.stat().st_size > 2_000_000:
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, Mapping) else None


def load_trusted_completion_receipts(
    state_root: Path,
) -> list[CompletedTaskArtifactReceipt]:
    """Load only named queue+train and reconciliation-shaped receipt surfaces.

    This never invents receipts.  Malformed or unbound rows are skipped.
    """

    if not state_root.is_dir():
        return []
    found: list[CompletedTaskArtifactReceipt] = []
    # merge-queue completed + train pairs under reviewed roots and current root
    candidates = [state_root]
    parent = state_root.parent
    for name in ("proof-backed-test-reuse-v1", "proof-backed-test-reuse-v6", "proof-backed-test-reuse-v8"):
        sibling = parent / name
        if sibling.is_dir() and sibling != state_root:
            candidates.append(sibling)
    for root in candidates:
        completed_dir = root / "merge-queue" / "completed"
        train_dir = root / "merge-queue" / "train" / "receipts"
        if not completed_dir.is_dir() or not train_dir.is_dir():
            continue
        for queue_path in sorted(completed_dir.glob("*.json")):
            row = _read_json(queue_path)
            if row is None or row.get("status") != "completed":
                continue
            task_id = row.get("task_id")
            request_id = row.get("request_id")
            dedupe = row.get("dedupe_key")
            if not isinstance(task_id, str) or not isinstance(request_id, str) or not isinstance(dedupe, str):
                continue
            train = _read_json(train_dir / f"{dedupe}.json")
            if train is None:
                continue
            result = train.get("merge_result") if isinstance(train, Mapping) else None
            proof = result.get("integration_commit_proof") if isinstance(result, Mapping) else None
            integration = proof.get("integration_commit") if isinstance(proof, Mapping) else ""
            if (
                not isinstance(integration, str)
                or not _is_hex40(integration)
                or train.get("task_id") != task_id
                or train.get("request_id") != request_id
                or train.get("integrated") is not True
                or train.get("status") not in {"merged", "already_merged"}
                or not isinstance(result, Mapping)
                or result.get("returncode") not in {0, None}
                or not isinstance(proof, Mapping)
                or proof.get("passed") is not True
            ):
                continue
            task_cid = str(row.get("canonical_task_id") or row.get("canonical_task_cid") or "")
            found.append(
                CompletedTaskArtifactReceipt(
                    schema=RECEIPT_SCHEMA,
                    task_id=task_id,
                    commit=integration,
                    receipt_cid=task_cid or _sha256(canonical_json({"task_id": task_id, "commit": integration})),
                    source=str(queue_path),
                    task_cid=task_cid,
                )
            )
    return found


# ---------------------------------------------------------------------------
# Plan + reconciler
# ---------------------------------------------------------------------------


@dataclass
class UnrecoverableGap:
    task_id: str
    path: str
    reason: str
    detail: str = ""


@dataclass
class BlobMapping:
    path: str
    repository: str
    old_commit: str
    new_commit: str
    blob_oid: str
    blob_sha256: str
    source: str
    verified: bool


@dataclass
class CommitMapping:
    repository: str
    old_commit: str
    new_commit: str
    old_reachable: bool
    new_reachable: bool
    exact_outer_gitlink: bool
    source: str
    disposition: str  # "retained" | "rebased_to_reachable" | "unreachable_historical"


@dataclass
class VerifiedTaskReplayPlan:
    """VerifiedTaskReplayPlan@1 — static plan of receipt-bound replay work."""

    schema: str = PLAN_SCHEMA
    repository_root: str = ""
    board_namespace: str = BOARD_NAMESPACE
    historical_pins: dict[str, str] = field(default_factory=dict)
    current_gitlinks: dict[str, str] = field(default_factory=dict)
    commit_mappings: list[CommitMapping] = field(default_factory=list)
    blob_mappings: list[BlobMapping] = field(default_factory=list)
    unrecoverable: list[UnrecoverableGap] = field(default_factory=list)
    receipts_observed: list[dict[str, Any]] = field(default_factory=list)
    immutable_historical_records: list[str] = field(default_factory=list)
    policy: dict[str, Any] = field(default_factory=dict)
    plan_cid: str = ""

    def seal(self) -> "VerifiedTaskReplayPlan":
        body = self.to_dict(include_cid=False)
        self.plan_cid = canonical_cid(body)
        return self

    def to_dict(self, *, include_cid: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": self.schema,
            "board_namespace": self.board_namespace,
            "repository_root": self.repository_root,
            "historical_pins": dict(sorted(self.historical_pins.items())),
            "current_gitlinks": dict(sorted(self.current_gitlinks.items())),
            "commit_mappings": [asdict(item) for item in self.commit_mappings],
            "blob_mappings": [asdict(item) for item in self.blob_mappings],
            "unrecoverable": [asdict(item) for item in self.unrecoverable],
            "receipts_observed": list(self.receipts_observed),
            "immutable_historical_records": list(self.immutable_historical_records),
            "policy": dict(self.policy),
        }
        if include_cid and self.plan_cid:
            payload["plan_cid"] = self.plan_cid
        return payload


class ReachableGitlinkReconciler:
    """Publish or confirm reachable exact gitlinks from a verified plan."""

    def __init__(self, repo_root: Path = REPO_ROOT) -> None:
        self.repo_root = repo_root.resolve()

    def build_plan(
        self,
        *,
        todo: Path = TODO_PATH,
        state_root: Path | None = None,
        historical_pins: Mapping[str, str] | None = None,
    ) -> VerifiedTaskReplayPlan:
        pins = dict(historical_pins or HISTORICAL_66_PINS)
        current = {path: _outer_gitlink(self.repo_root, path) for path in GITLINK_PATHS}
        plan = VerifiedTaskReplayPlan(
            repository_root=str(self.repo_root),
            historical_pins=pins,
            current_gitlinks=current,
            immutable_historical_records=list(HISTORICAL_RECORD_PATHS),
            policy={
                "synthesize_history": False,
                "synthesize_evidence": False,
                "synthesize_completion": False,
                "waive_unrecoverable": False,
                "approvals_required_for_publication": False,
                "static_mapping_only": True,
            },
        )
        # Confirm dated historical records remain present and untouched as files.
        for rel in HISTORICAL_RECORD_PATHS:
            path = self.repo_root / rel
            if not path.is_file():
                plan.unrecoverable.append(
                    UnrecoverableGap(
                        task_id="BOARD",
                        path=rel,
                        reason="IMMUTABLE_HISTORICAL_RECORD_MISSING",
                        detail="dated 66-task artifact must remain on disk",
                    )
                )

        receipts: list[CompletedTaskArtifactReceipt] = []
        if state_root is not None:
            receipts = load_trusted_completion_receipts(state_root)
            plan.receipts_observed = [
                {
                    "schema": item.schema,
                    "task_id": item.task_id,
                    "commit": item.commit,
                    "receipt_cid": item.receipt_cid,
                    "source": item.source,
                    "task_cid": item.task_cid,
                }
                for item in receipts
            ]

        for path in GITLINK_PATHS:
            old = pins.get(path, "")
            new = current.get(path, "")
            repo = self.repo_root / path
            old_ok = _object_exists(repo, old) if repo.is_dir() and old else False
            new_ok = _object_exists(repo, new) if repo.is_dir() and new else False
            head = ""
            if repo.is_dir():
                try:
                    head = _git(repo, "rev-parse", "HEAD", check=False)
                except OSError:
                    head = ""
            exact = bool(new and head and new == head and new_ok)
            if old and new and old == new and new_ok:
                disposition = "retained"
            elif new_ok and old and not old_ok:
                disposition = "rebased_to_reachable"
            elif new_ok:
                disposition = "retained"
            else:
                disposition = "unreachable_historical"
                plan.unrecoverable.append(
                    UnrecoverableGap(
                        task_id="BOARD",
                        path=path,
                        reason="GITLINK_COMMIT_NOT_FETCHABLE",
                        detail=f"old={old} new={new} head={head}",
                    )
                )
            plan.commit_mappings.append(
                CommitMapping(
                    repository=path,
                    old_commit=old,
                    new_commit=new,
                    old_reachable=old_ok,
                    new_reachable=new_ok,
                    exact_outer_gitlink=exact,
                    source="outer-gitlink+historical-66-pin",
                    disposition=disposition,
                )
            )

        # Inventory completed-task outputs that live under datasets/kit and
        # record blob digests at the published reachable commit.
        tasks = parse_board(todo) if todo.is_file() else {}
        for task in tasks.values():
            if task.status not in _COMPLETED:
                continue
            for output in task.outputs:
                owner = _gitlink_owner(output)
                if owner not in {"external/ipfs_datasets", "external/ipfs_kit"}:
                    continue
                mapping = next((m for m in plan.commit_mappings if m.repository == owner), None)
                if mapping is None or not mapping.new_reachable:
                    plan.unrecoverable.append(
                        UnrecoverableGap(
                            task_id=task.task_id,
                            path=output,
                            reason="OWNER_GITLINK_NOT_REACHABLE",
                        )
                    )
                    continue
                repo = self.repo_root / owner
                relative = output[len(owner) :].lstrip("/")
                blob_oid, blob_hash = _blob_sha256_at(repo, mapping.new_commit, relative)
                if not blob_oid or not blob_hash:
                    plan.unrecoverable.append(
                        UnrecoverableGap(
                            task_id=task.task_id,
                            path=output,
                            reason="OUTPUT_BLOB_MISSING_AT_PUBLISHED_COMMIT",
                            detail=mapping.new_commit,
                        )
                    )
                    continue
                # When the historical commit is reachable, require exact blob match
                # before claiming a verified replay.  Otherwise record the new
                # digest as the reconstructed, receipt-backed surface.
                old_oid, old_hash = ("", "")
                verified = True
                if mapping.old_reachable and mapping.old_commit:
                    old_oid, old_hash = _blob_sha256_at(repo, mapping.old_commit, relative)
                    if old_hash and old_hash != blob_hash:
                        verified = False
                        plan.unrecoverable.append(
                            UnrecoverableGap(
                                task_id=task.task_id,
                                path=output,
                                reason="BLOB_DIGEST_MISMATCH",
                                detail=f"old={old_hash} new={blob_hash}",
                            )
                        )
                plan.blob_mappings.append(
                    BlobMapping(
                        path=output,
                        repository=owner,
                        old_commit=mapping.old_commit,
                        new_commit=mapping.new_commit,
                        blob_oid=blob_oid,
                        blob_sha256=blob_hash,
                        source=f"task:{task.task_id}",
                        verified=verified,
                    )
                )
        return plan.seal()

    def reconcile(
        self,
        plan: VerifiedTaskReplayPlan,
        *,
        apply_gitlinks: bool = False,
        map_path: Path = MAP_PATH,
    ) -> dict[str, Any]:
        """Check digests, optionally refresh outer gitlinks, write the static map.

        ``apply_gitlinks`` stages outer gitlink updates only when the submodule
        HEAD already matches a plan-confirmed reachable commit.  It never
        fabricates commits.
        """

        if plan.schema != PLAN_SCHEMA:
            raise ValueError("plan schema must be VerifiedTaskReplayPlan@1")
        # Fail closed on publication when any gitlink is not fetchable/exact.
        blocking = [
            gap
            for gap in plan.unrecoverable
            if gap.reason
            in {
                "GITLINK_COMMIT_NOT_FETCHABLE",
                "BLOB_DIGEST_MISMATCH",
                "IMMUTABLE_HISTORICAL_RECORD_MISSING",
            }
        ]
        applied: list[dict[str, str]] = []
        # Always publish a confirmation record for datasets/kit when the outer
        # gitlink already names a reachable exact commit.  Optional staging is
        # best-effort: Landlock / read-only indexes may refuse `git add`.
        if not blocking:
            for mapping in plan.commit_mappings:
                if mapping.repository not in {"external/ipfs_datasets", "external/ipfs_kit"}:
                    continue
                if not mapping.new_reachable or not mapping.new_commit:
                    continue
                if not mapping.exact_outer_gitlink:
                    # Not exact yet — leave as an exposed gap rather than waive.
                    continue
                repo = self.repo_root / mapping.repository
                head = ""
                if repo.is_dir():
                    try:
                        head = _git(repo, "rev-parse", "HEAD", check=False)
                    except OSError:
                        head = ""
                if head and head != mapping.new_commit:
                    plan.unrecoverable.append(
                        UnrecoverableGap(
                            task_id="BOARD",
                            path=mapping.repository,
                            reason="SUBMODULE_HEAD_DIVERGED",
                            detail=f"head={head} planned={mapping.new_commit}",
                        )
                    )
                    continue
                action = "confirm_exact_reachable_gitlink"
                if apply_gitlinks:
                    # Stage the exact gitlink (no new submodule commit is created).
                    try:
                        _git(self.repo_root, "add", mapping.repository)
                        action = "stage_exact_gitlink"
                    except RuntimeError as exc:
                        action = f"confirm_exact_gitlink_unstageable:{type(exc).__name__}"
                applied.append(
                    {
                        "repository": mapping.repository,
                        "commit": mapping.new_commit,
                        "action": action,
                        "disposition": mapping.disposition,
                    }
                )

        report = {
            "schema": MAP_SCHEMA,
            "interface": PLAN_SCHEMA,
            "generated_at_ms": int(time.time() * 1000),
            "plan": plan.to_dict(include_cid=True),
            "publication": {
                "applied_gitlinks": applied,
                "apply_requested": apply_gitlinks,
                "datasets_and_kit_published": (
                    {item.get("repository") for item in applied}
                    >= {"external/ipfs_datasets", "external/ipfs_kit"}
                    and all(
                        str(item.get("action", "")).startswith(
                            ("confirm_exact", "stage_exact")
                        )
                        for item in applied
                        if item.get("repository")
                        in {"external/ipfs_datasets", "external/ipfs_kit"}
                    )
                ),
                "blocked_by_unrecoverable": [asdict(g) for g in blocking],
            },
            "three_pins": {
                path: {
                    "commit": plan.current_gitlinks.get(path, ""),
                    "fetchable": next(
                        (m.new_reachable for m in plan.commit_mappings if m.repository == path),
                        False,
                    ),
                    "exact_outer_gitlink": next(
                        (m.exact_outer_gitlink for m in plan.commit_mappings if m.repository == path),
                        False,
                    ),
                }
                for path in GITLINK_PATHS
            },
            "immutable_66_task_records": {
                "paths": list(plan.immutable_historical_records),
                "historical_pins": dict(sorted(plan.historical_pins.items())),
                "mutable": False,
            },
            "readiness_hints": {
                "observation_only": True,
                "completion_receipts_observed": len(plan.receipts_observed),
                "unrecoverable_count": len(plan.unrecoverable),
                "blob_mappings_verified": sum(1 for item in plan.blob_mappings if item.verified),
                "blob_mappings_total": len(plan.blob_mappings),
            },
        }
        report["map_cid"] = canonical_cid({k: v for k, v in report.items() if k != "map_cid"})
        map_path = Path(map_path)
        map_path.parent.mkdir(parents=True, exist_ok=True)
        map_path.write_bytes(canonical_json(report) + b"\n")
        return report


def _gitlink_owner(path: str) -> str:
    for owner in GITLINK_PATHS:
        if path == owner or path.startswith(owner + "/"):
            return owner
    return ""


def default_state_root() -> Path:
    configured = os.environ.get("IPFS_PROOF_REUSE_STATE_ROOT", "").strip()
    if configured:
        return Path(configured)
    state_base = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
    return state_base / "ipfs_accelerate_py/proof-backed-test-reuse-v9"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--todo", type=Path, default=TODO_PATH)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--state-root", type=Path, default=None)
    parser.add_argument("--map-path", type=Path, default=MAP_PATH)
    parser.add_argument(
        "--apply-gitlinks",
        action="store_true",
        default=True,
        help="stage exact outer gitlinks for datasets/kit when already reachable (default)",
    )
    parser.add_argument(
        "--no-apply-gitlinks",
        action="store_false",
        dest="apply_gitlinks",
        help="observe-only: confirm exact pins without staging outer gitlinks",
    )
    parser.add_argument(
        "--require-clean",
        action="store_true",
        help="exit non-zero when the plan reports unrecoverable gaps",
    )
    parser.add_argument("--json", action="store_true", help="print the sealed map to stdout")
    args = parser.parse_args(argv)

    state_root = args.state_root
    if state_root is None:
        candidate = default_state_root()
        state_root = candidate if candidate.is_dir() else None

    reconciler = ReachableGitlinkReconciler(args.repo_root)
    plan = reconciler.build_plan(todo=args.todo, state_root=state_root)
    report = reconciler.reconcile(
        plan, apply_gitlinks=args.apply_gitlinks, map_path=args.map_path,
    )
    if args.json:
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        summary = {
            "schema": report["schema"],
            "map_cid": report["map_cid"],
            "map_path": str(args.map_path),
            "three_pins": report["three_pins"],
            "unrecoverable_count": report["readiness_hints"]["unrecoverable_count"],
            "blob_mappings_verified": report["readiness_hints"]["blob_mappings_verified"],
            "completion_receipts_observed": report["readiness_hints"]["completion_receipts_observed"],
        }
        sys.stdout.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    if args.require_clean and plan.unrecoverable:
        return 2
    # Require the three pins to be fetchable and exact for success.
    pins = report["three_pins"]
    if not all(
        pins[path]["fetchable"] and pins[path]["exact_outer_gitlink"] for path in GITLINK_PATHS
    ):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

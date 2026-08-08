#!/usr/bin/env python3
"""Fail-closed live-tree evidence audit for proof-backed test-reuse tasks.

This program deliberately *observes* receipts; it never creates task completion
or validation evidence.  Its only persistent output is a CID-addressed report
of what was observed in the configured state root.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
TODO_PATH = REPO_ROOT / "implementation_plan/docs/46-proof-backed-test-reuse.todo.md"
OBJECTIVE_PATH = REPO_ROOT / "implementation_plan/docs/46-proof-backed-test-reuse.objectives.md"
PLAN_PATH = REPO_ROOT / "implementation_plan/docs/46-proof-backed-test-reuse-plan-2026-07-31.md"
CONFIG_PATH = REPO_ROOT / "config/proof_backed_test_reuse_supervisor.json"
PREFLIGHT_SCHEMA = "ipfs_accelerate_py/proof-backed-test-reuse-preflight@1"
BOARD_NAMESPACE = "proof-backed-test-reuse-v1"
SEALED_TASK_COUNT = 78
REPORT_SCHEMA = "ipfs_accelerate_py/proof-backed-test-reuse-task-evidence@1"
RECEIPT_SCHEMA = "CompletedTaskArtifactReceipt@1"
GITLINK_SCHEMA = "ExactGitlinkEvidence@1"
_TASK = re.compile(r"^##\s+(PTR-\d+)\s+(.+?)\s*$")
_FIELD = re.compile(r"^-\s+([^:]+):\s*(.*?)\s*$")
_PATH = re.compile(r"(?<![A-Za-z0-9_./-])((?:external|implementation_plan|config|scripts|tests|test)/[A-Za-z0-9_@%+=:,./-]+)")
_COMPLETED = frozenset({"complete", "completed", "done", "validated"})


def canonical_json(value: object) -> bytes:
    return json.dumps(value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _varint(value: int) -> bytes:
    result = bytearray()
    while value > 127:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def canonical_cid(value: object) -> str:
    """Return a CIDv1 dag-json SHA-256 identity for canonical JSON bytes."""
    digest = hashlib.sha256(canonical_json(value)).digest()
    binary = _varint(1) + _varint(0x0129) + _varint(0x12) + _varint(len(digest)) + digest
    return "b" + base64.b32encode(binary).decode("ascii").lower().rstrip("=")


def _sha256(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _command(*args: str, cwd: Path = REPO_ROOT) -> tuple[int, str]:
    try:
        run = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    except OSError:
        return 127, ""
    return run.returncode, run.stdout.strip()


def _git_blob_sha256(revision: str, path: str, cwd: Path) -> str:
    """Hash the exact Git blob bytes, including binary generated artifacts."""
    try:
        run = subprocess.run(("git", "show", f"{revision}:{path}"), cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    except OSError:
        return ""
    return _sha256(run.stdout) if run.returncode == 0 else ""


def _safe_path(value: str) -> str | None:
    path = PurePosixPath(value.replace("\\", "/"))
    if not value or "\x00" in value or path.is_absolute() or ".." in path.parts or path.as_posix() in {".", ".."}:
        return None
    return path.as_posix()


def validation_targets(command: str) -> tuple[str, ...]:
    # A quoted import root (for example ``sys.path.insert(..., 'external/pkg')``)
    # is not a validation target.  Board validations name file targets, so require
    # a suffix while retaining non-Python test runners and manifests.
    return tuple(sorted({target for raw in _PATH.findall(command)
                         if (target := _safe_path(raw.split("::", 1)[0].rstrip(",;)]}")))
                         and PurePosixPath(target).suffix}))


@dataclass(frozen=True)
class Task:
    task_id: str
    title: str
    status: str
    dependencies: tuple[str, ...]
    outputs: tuple[str, ...]
    validation_command: str
    validation_targets: tuple[str, ...]
    goal_id: str
    canonical_task_key: str = ""
    canonical_task_cid: str = ""

    @property
    def task_cid(self) -> str:
        # The live board has a supervisor-issued identity.  Never replace it
        # with this compatibility projection when one is available.
        if self.canonical_task_cid:
            return self.canonical_task_cid
        return canonical_cid({
            "task_id": self.task_id, "status": self.status, "dependencies": self.dependencies,
            "outputs": self.outputs, "validation_command": self.validation_command, "goal_id": self.goal_id,
        })


@dataclass(frozen=True)
class ExactGitlinkEvidence:
    path: str
    expected_commit: str
    observed_commit: str
    exact: bool


@dataclass(frozen=True)
class CompletedTaskArtifactReceipt:
    """The minimum completion proof accepted by this independent auditor."""
    task_id: str
    commit: str
    receipt_cid: str
    source: str
    task_cid: str = ""


@dataclass(frozen=True)
class Gap:
    task_id: str
    kind: str
    detail: str


def parse_board(path: Path) -> dict[str, Task]:
    current: dict[str, Any] | None = None
    tasks: dict[str, Task] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        found = _TASK.match(line)
        if found:
            if current is not None:
                task = _make_task(current)
                tasks[task.task_id] = task
            current = {"task_id": found.group(1), "title": found.group(2), "fields": {}}
            continue
        if current is not None and (field := _FIELD.match(line)):
            current["fields"][field.group(1).strip().lower()] = field.group(2).strip()
    if current is not None:
        task = _make_task(current)
        tasks[task.task_id] = task
    return tasks


def _make_task(raw: Mapping[str, Any]) -> Task:
    fields = raw["fields"]
    csv = lambda name: tuple(item.strip() for item in fields.get(name, "").split(",") if item.strip())
    command = fields.get("validation", "")
    return Task(str(raw["task_id"]), str(raw["title"]), fields.get("status", "").lower(), csv("depends on"), csv("outputs"), command, validation_targets(command), fields.get("goal id", ""))


def _load_script_module(path: Path, name: str) -> Any:
    """Load one repository-owned helper without accepting a PATH shadow."""

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sealed_board(todo: Path) -> tuple[dict[str, Task], list[Gap], Mapping[str, Any]]:
    """Read the program board through its preflight and supervisor parser.

    This deliberately does not use the permissive markdown parser above.  The
    latter is retained only for isolated fixtures; using it for the sealed
    board would silently rederive task identities and permit altered boards.
    """

    gaps: list[Gap] = []
    try:
        validator = _load_script_module(
            REPO_ROOT / "scripts/validate_proof_backed_test_reuse_board.py",
            "_ptr_preflight_for_task_evidence",
        )
        preflight = validator.validate(OBJECTIVE_PATH, todo, CONFIG_PATH, PLAN_PATH)
    except Exception as exc:
        return {}, [Gap("BOARD", "BOARD_PREFLIGHT_UNAVAILABLE", type(exc).__name__)], {}
    if (
        not isinstance(preflight, Mapping)
        or preflight.get("schema") != PREFLIGHT_SCHEMA
        or preflight.get("valid") is not True
        or preflight.get("errors") != []
        or preflight.get("task_count") != SEALED_TASK_COUNT
    ):
        return {}, [Gap("BOARD", "BOARD_PREFLIGHT_INVALID", "sealed preflight did not validate the 78-task board")], {}
    try:
        accelerator = REPO_ROOT / "external/ipfs_accelerate"
        if str(accelerator) not in sys.path:
            sys.path.insert(0, str(accelerator))
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

        parsed = parse_task_file(todo, "## PTR-")
    except Exception as exc:
        return {}, [Gap("BOARD", "BOARD_PARSER_UNAVAILABLE", type(exc).__name__)], {}
    if len(parsed) != SEALED_TASK_COUNT:
        return {}, [Gap("BOARD", "BOARD_POPULATION_MISMATCH", str(len(parsed)))], {}
    tasks: dict[str, Task] = {}
    for item in parsed:
        task_id = str(getattr(item, "task_id", ""))
        metadata = getattr(item, "metadata", {})
        namespace = str(getattr(item, "board_namespace", ""))
        key = str(getattr(item, "canonical_task_key", ""))
        cid = str(getattr(item, "canonical_task_cid", ""))
        if not task_id or task_id in tasks or namespace != BOARD_NAMESPACE or not key or not cid:
            gaps.append(Gap(task_id or "BOARD", "BOARD_IDENTITY_INVALID", task_id or "missing task identity"))
            continue
        command = str(metadata.get("validation", ""))
        tasks[task_id] = Task(
            task_id, str(getattr(item, "title", "")), str(getattr(item, "status", "")).lower(),
            tuple(getattr(item, "depends_on", ())), tuple(getattr(item, "outputs", ())), command,
            validation_targets(command), str(metadata.get("goal id", "")), key, cid,
        )
    if len(tasks) != SEALED_TASK_COUNT:
        gaps.append(Gap("BOARD", "BOARD_POPULATION_MISMATCH", str(len(tasks))))
    quarantine = preflight.get("historical_missing_artifact_quarantine")
    if not isinstance(quarantine, Mapping):
        quarantine = {}
    return tasks, gaps, quarantine


class GitSnapshot:
    def __init__(self, root: Path) -> None:
        self.root = root
        _, self.commit = _command("git", "rev-parse", "HEAD", cwd=root)
        _, self.tree = _command("git", "rev-parse", "HEAD^{tree}", cwd=root)
        self.gitlinks: dict[str, str] = {}
        rc, listing = _command("git", "ls-tree", "-r", "HEAD", cwd=root)
        if rc == 0:
            for line in listing.splitlines():
                meta, _, name = line.partition("\t")
                bits = meta.split()
                if len(bits) == 3 and bits[1] == "commit":
                    self.gitlinks[name] = bits[2]

    @property
    def gitlink_state_cid(self) -> str:
        return canonical_cid(self.gitlinks)

    def inspect_path(self, value: str) -> tuple[dict[str, Any], Gap | None]:
        path = _safe_path(value)
        if path is None:
            return {"path": value, "present": False}, Gap("", "UNSAFE_PATH", repr(value))
        owner = max((item for item in self.gitlinks if path == item or path.startswith(item + "/")), key=len, default="")
        if not owner:
            rc, line = _command("git", "ls-tree", "HEAD", "--", path, cwd=self.root)
            present = rc == 0 and bool(line)
            blob = line.split()[2] if present and len(line.split()) >= 3 else ""
            return {"path": path, "owner": ".", "gitlink": self.commit, "expected_gitlink": self.commit, "exact_gitlink": True,
                    "present": present, "blob_oid": blob, "blob_sha256": _git_blob_sha256("HEAD", path, self.root) if present else ""}, None
        expected = self.gitlinks[owner]
        repo = self.root / owner
        _, observed = _command("git", "rev-parse", "HEAD", cwd=repo)
        evidence = ExactGitlinkEvidence(owner, expected, observed, observed == expected)
        relative = path[len(owner):].lstrip("/")
        rc, line = _command("git", "ls-tree", expected, "--", relative, cwd=repo)
        present = evidence.exact and rc == 0 and bool(line)
        blob = line.split()[2] if present and len(line.split()) >= 3 else ""
        return {"path": path, "owner": owner, "gitlink": asdict(evidence), "present": present,
                "blob_oid": blob, "blob_sha256": _git_blob_sha256(expected, relative, repo) if present else ""}, None

    def is_ancestor(self, commit: str) -> bool:
        return bool(commit) and _command("git", "merge-base", "--is-ancestor", commit, self.commit, cwd=self.root)[0] == 0


def _records(state_root: Path) -> Iterable[tuple[Path, Mapping[str, Any]]]:
    if not state_root.is_dir():
        return ()
    found: list[tuple[Path, Mapping[str, Any]]] = []
    for path in sorted(state_root.rglob("*.json")):
        # Reports are observations, never receipts, and must not authorize themselves.
        try:
            oversized = path.stat().st_size > 2_000_000
        except OSError:
            continue
        if "task-evidence" in path.parts or oversized:
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        values = value if isinstance(value, list) else [value]
        for record in values:
            if isinstance(record, Mapping):
                found.append((path, record))
    return found


def _completion_receipt(record: Mapping[str, Any], source: Path) -> CompletedTaskArtifactReceipt | None:
    task_id = record.get("task_id")
    cid = next((str(record[key]) for key in ("merge_receipt_cid", "completion_receipt_cid", "task_receipt_cid") if record.get(key)), "")
    commit = next((str(record[key]) for key in ("git_commit_id", "merged_commit_id", "merge_commit", "commit_sha", "commit") if record.get(key)), "")
    if not isinstance(task_id, str) or not cid or not commit:
        return None
    return CompletedTaskArtifactReceipt(task_id, commit, cid, str(source), str(record.get("task_cid", "")))


def _validation_receipt(record: Mapping[str, Any], source: Path) -> dict[str, Any] | None:
    if not isinstance(record.get("task_id"), str):
        return None
    cid = record.get("validation_receipt_cid")
    if not cid:
        return None
    result = dict(record)
    result["source"] = str(source)
    return result


def _read_json(path: Path) -> Mapping[str, Any] | None:
    """Read one bounded JSON object; a malformed authority artifact is a gap."""

    try:
        if path.stat().st_size > 2_000_000:
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, Mapping) else None


def _reviewed_roots(current_root: Path) -> tuple[dict[str, Path], list[Gap]]:
    """Resolve only the controller's mandatory reviewed siblings of the v9 root.

    ``IPFS_PROOF_REUSE_STATE_ROOT`` is the complete current root override.
    Reviewed v8/v6/v1 siblings are named directories of its parent, never
    discovered by recursive search under an isolated HOME.
    """

    parent = current_root.parent
    roots = {
        "v1": parent / "proof-backed-test-reuse-v1",
        "v6": parent / "proof-backed-test-reuse-v6",
        "v8": parent / "proof-backed-test-reuse-v8",
        "v9": current_root,
    }
    gaps = [Gap("BOARD", "STATE_ROOT_MISSING", f"{name}:{path.name}") for name, path in roots.items() if not path.is_dir()]
    return roots, gaps


def _verify_event_log(root_name: str, root: Path) -> list[Gap]:
    """Verify the sealed lane logs without treating their contents as a search tree."""

    gaps: list[Gap] = []
    for lane in range(3):
        directory = root / "state" / f"ptr_lane_{lane}"
        events = directory / f"ptr_lane_{lane}_events.jsonl"
        manifest_path = directory / f"ptr_lane_{lane}_events.jsonl.manifest.json"
        manifest = _read_json(manifest_path)
        label = f"{root_name}:ptr_lane_{lane}"
        if manifest is None or not events.is_file():
            gaps.append(Gap("BOARD", "STATE_ROOT_MANIFEST_MISSING", label))
            continue
        digest_body = dict(manifest)
        claimed_digest = digest_body.pop("manifest_digest", "")
        if (
            manifest.get("schema") != "ipfs_accelerate_py.agent_supervisor.event-log-manifest@2"
            or claimed_digest != _sha256(canonical_json(digest_body))
            or manifest.get("active_path") != events.name
            or not isinstance(manifest.get("stream_id"), str)
            or not isinstance(manifest.get("snapshot_id"), str)
        ):
            gaps.append(Gap("BOARD", "STATE_ROOT_MANIFEST_INVALID", label))
            continue
        files = manifest.get("files")
        entry = next((item for item in files if isinstance(item, Mapping) and item.get("path") == events.name), None) if isinstance(files, list) else None
        if entry is None:
            gaps.append(Gap("BOARD", "STATE_ROOT_MANIFEST_SEGMENT_MISSING", label))
            continue
        try:
            raw = events.read_bytes()
            lines = raw.splitlines()
        except OSError:
            gaps.append(Gap("BOARD", "STATE_ROOT_EVENT_LOG_UNREADABLE", label))
            continue
        if entry.get("size_bytes") != len(raw) or entry.get("event_count") != len(lines):
            gaps.append(Gap("BOARD", "STATE_ROOT_MANIFEST_SIZE_MISMATCH", label))
        if entry.get("sha256") and entry.get("sha256") != _sha256(raw):
            gaps.append(Gap("BOARD", "STATE_ROOT_MANIFEST_HASH_MISMATCH", label))
        previous = str(entry.get("start_previous_event_id", ""))
        expected_sequence = entry.get("first_sequence")
        for raw_line in lines:
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError:
                gaps.append(Gap("BOARD", "STATE_ROOT_EVENT_LOG_INVALID", label))
                break
            if not isinstance(event, Mapping) or not event.get("event_id") or event.get("previous_event_id", "") != previous:
                gaps.append(Gap("BOARD", "STATE_ROOT_EVENT_CHAIN_INVALID", label))
                break
            if expected_sequence is not None and event.get("sequence") != expected_sequence:
                gaps.append(Gap("BOARD", "STATE_ROOT_EVENT_SEQUENCE_INVALID", label))
                break
            if event.get("stream_id") != manifest["stream_id"] or event.get("snapshot_id") != manifest["snapshot_id"]:
                gaps.append(Gap("BOARD", "STATE_ROOT_EVENT_IDENTITY_INVALID", label))
                break
            previous = str(event["event_id"])
            if isinstance(expected_sequence, int):
                expected_sequence += 1
        if lines and previous != manifest.get("last_event_id"):
            gaps.append(Gap("BOARD", "STATE_ROOT_EVENT_TAIL_INVALID", label))
    return gaps


def _validation_command_cid(command: str) -> str:
    """Use the supervisor's command identity, not a local CID approximation."""

    accelerator = REPO_ROOT / "external/ipfs_accelerate"
    if str(accelerator) not in sys.path:
        sys.path.insert(0, str(accelerator))
    from ipfs_accelerate_py.agent_supervisor.validation.proof_cached_test_validation import validation_command_identity
    return str(validation_command_identity(command))


MEMBER_COMPLETION_SCHEMA = "ipfs_accelerate_py.agent_supervisor.member_completion_receipt@1"
RECONCILE_REASON = "implementation_branch_already_merged"


def _iter_lane_events(root: Path) -> Iterable[Mapping[str, Any]]:
    """Yield events from named lane logs only after the caller verified manifests."""

    for lane in range(3):
        events = root / "state" / f"ptr_lane_{lane}" / f"ptr_lane_{lane}_events.jsonl"
        if not events.is_file():
            continue
        try:
            lines = events.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, Mapping):
                yield event


def _member_completion_ok(event: Mapping[str, Any], task: Task) -> bool:
    """Accept only a succeeded nested member completion for the exact task triple."""

    todo = event.get("todo_update_result")
    if not isinstance(todo, Mapping):
        return False
    receipts = todo.get("completion_receipts")
    if not isinstance(receipts, list):
        return False
    for item in receipts:
        if not isinstance(item, Mapping):
            continue
        if (
            item.get("schema") == MEMBER_COMPLETION_SCHEMA
            and item.get("status") == "succeeded"
            and item.get("task_id") == task.task_id
            and item.get("canonical_task_cid") == task.canonical_task_cid
            and item.get("canonical_task_key") == task.canonical_task_key
            and item.get("board_namespace") == BOARD_NAMESPACE
        ):
            return True
    return False


def _reconciliation_receipts(
    roots: Mapping[str, Path], tasks: Mapping[str, Task], snapshot: GitSnapshot,
) -> tuple[dict[str, list[CompletedTaskArtifactReceipt]], list[Gap]]:
    """Authority from verified merge_reconciled events (not from failed/quarantined rows)."""

    receipts: dict[str, list[CompletedTaskArtifactReceipt]] = {}
    gaps: list[Gap] = []
    for name in ("v1", "v6", "v8"):
        root = roots.get(name)
        if root is None or not root.is_dir():
            continue
        for event in _iter_lane_events(root):
            if event.get("type") != "merge_reconciled":
                continue
            # Earlier failed or quarantined events neither authorize nor suppress later success.
            if event.get("resolved") is not True or event.get("reason") != RECONCILE_REASON:
                continue
            task_id = event.get("task_id")
            task = tasks.get(task_id) if isinstance(task_id, str) else None
            if task is None:
                continue
            completion_cids = event.get("completion_task_cids")
            persistence = event.get("completion_persistence")
            proof = event.get("integration_commit_proof")
            outputs = event.get("post_merge_declared_output_invariant")
            if not isinstance(completion_cids, Mapping) or not isinstance(persistence, Mapping) or not isinstance(proof, Mapping):
                gaps.append(Gap(task.task_id, "RECONCILIATION_RECEIPT_MALFORMED", name))
                continue
            integration = proof.get("integration_commit")
            if (
                completion_cids.get(task.task_id) != task.canonical_task_cid
                or persistence.get("passed") is not True
                or persistence.get("durable_update") is not True
                or proof.get("passed") is not True
                or not isinstance(integration, str)
                or not snapshot.is_ancestor(integration)
                or not isinstance(outputs, Mapping)
                or outputs.get("passed") is not True
                or not _member_completion_ok(event, task)
            ):
                gaps.append(Gap(task.task_id, "RECONCILIATION_RECEIPT_UNVERIFIED", name))
                continue
            receipts.setdefault(task.task_id, []).append(CompletedTaskArtifactReceipt(
                task.task_id, integration, task.canonical_task_cid,
                f"{name}/state/ptr_lane_*/events:merge_reconciled", task.canonical_task_cid,
            ))
    return receipts, gaps


def _authoritative_evidence(
    roots: Mapping[str, Path], tasks: Mapping[str, Task], snapshot: GitSnapshot,
) -> tuple[dict[str, list[CompletedTaskArtifactReceipt]], dict[str, list[dict[str, Any]]], list[Gap]]:
    """Load only named authority artifacts and authenticate their joins.

    In particular, a raw queue row or a recovery record cannot become a
    completion receipt by itself: it must pair with its train receipt and the
    exact board-issued key/CID tuple.
    """

    gaps: list[Gap] = []
    receipts: dict[str, list[CompletedTaskArtifactReceipt]] = {}
    validations: dict[str, list[dict[str, Any]]] = {}
    for name, root in roots.items():
        gaps.extend(_verify_event_log(name, root))
    v8 = roots["v8"]
    completed_dir = v8 / "merge-queue" / "completed"
    train_dir = v8 / "merge-queue" / "train" / "receipts"
    if not completed_dir.is_dir() or not train_dir.is_dir():
        gaps.append(Gap("BOARD", "STATE_ROOT_QUEUE_AUTHORITY_MISSING", str(v8)))
    else:
        for queue_path in sorted(completed_dir.glob("*.json")):
            row = _read_json(queue_path)
            if row is None:
                gaps.append(Gap("BOARD", "QUEUE_ROW_INVALID", queue_path.name))
                continue
            metadata = row.get("metadata")
            nested = metadata.get("task") if isinstance(metadata, Mapping) else None
            task_id = row.get("task_id")
            if (
                not isinstance(nested, Mapping)
                or metadata.get("schema") != "ipfs_accelerate_py/agent-supervisor/merge-candidate@3"
                or not isinstance(task_id, str)
                or task_id not in tasks
            ):
                gaps.append(Gap(str(task_id or "BOARD"), "QUEUE_ROW_UNAUTHENTICATED", queue_path.name))
                continue
            task = tasks[task_id]
            if (
                nested.get("board_namespace") != BOARD_NAMESPACE
                or nested.get("canonical_task_key") != task.canonical_task_key
                or nested.get("canonical_task_cid") != task.canonical_task_cid
                or row.get("canonical_task_key") != task.canonical_task_key
                or row.get("canonical_task_id") != task.canonical_task_cid
                or row.get("request_id") != queue_path.stem
            ):
                gaps.append(Gap(task_id, "QUEUE_TASK_IDENTITY_MISMATCH", queue_path.name))
                continue
            dedupe = row.get("dedupe_key")
            train_path = train_dir / f"{dedupe}.json"
            train = _read_json(train_path) if isinstance(dedupe, str) else None
            result = train.get("merge_result") if isinstance(train, Mapping) else None
            proof = result.get("integration_commit_proof") if isinstance(result, Mapping) else None
            handoff = result.get("integrated_handoff_proof") if isinstance(result, Mapping) else None
            integration_commit = proof.get("integration_commit") if isinstance(proof, Mapping) else ""
            status = train.get("status") if isinstance(train, Mapping) else ""
            merge_succeeded = (
                train.get("merged") is True
                or (status == "already_merged" and result.get("already_merged") is True
                    and isinstance(handoff, Mapping) and handoff.get("passed") is True)
            ) if isinstance(train, Mapping) and isinstance(result, Mapping) else False
            if not isinstance(train, Mapping) or not isinstance(result, Mapping) or not isinstance(proof, Mapping) or (
                train.get("request_id") != row["request_id"]
                or train.get("canonical_task_id") != task.canonical_task_key
                or train.get("task_id") != task_id
                or train.get("status") not in {"merged", "already_merged"}
                or train.get("integrated") is not True
                or not merge_succeeded
                or result.get("returncode") != 0
                or proof.get("passed") is not True
                or not isinstance(integration_commit, str)
                or not snapshot.is_ancestor(integration_commit)
            ):
                gaps.append(Gap(task_id, "MERGE_TRAIN_RECEIPT_UNVERIFIED", queue_path.name))
                continue
            receipts.setdefault(task_id, []).append(CompletedTaskArtifactReceipt(
                task_id, integration_commit, task.canonical_task_cid,
                f"v8/merge-queue/train/receipts/{train_path.name}", task.canonical_task_cid,
            ))
    # Historical validation is deliberately flat: failed/ subdirectories and
    # snapshots are non-authoritative and are never scanned.
    # Retained execution receipts were introduced in the reviewed v1
    # projection; v6 is required for reconciliation history, not as a second
    # validation-receipt store.
    for name in ("v1",):
        directory = roots[name] / "projection" / "completion" / "validation_receipts"
        if not directory.is_dir():
            gaps.append(Gap("BOARD", "STATE_ROOT_VALIDATION_AUTHORITY_MISSING", name))
            continue
        for path in sorted(directory.glob("PTR-*.json")):
            item = _read_json(path)
            if item is None:
                gaps.append(Gap("BOARD", "VALIDATION_RECEIPT_INVALID", path.name))
                continue
            task_id = item.get("task_id")
            task = tasks.get(task_id) if isinstance(task_id, str) else None
            if task is None:
                continue
            try:
                command_cid = _validation_command_cid(task.validation_command)
            except Exception:
                gaps.append(Gap(task.task_id, "VALIDATION_COMMAND_IDENTITY_UNAVAILABLE", path.name))
                continue
            immutable = dict(item)
            claimed = immutable.pop("validation_receipt_cid", "")
            expected = canonical_cid(immutable)
            if (
                item.get("schema") != "ipfs_accelerate_py/proof-backed-test-reuse-executed-validation-receipt@1"
                or claimed != expected
                or item.get("task_cid") != task.canonical_task_cid
                or item.get("goal_id") != task.goal_id
                or item.get("validation_command") != task.validation_command
                or item.get("validation_command_cid") != command_cid
            ):
                gaps.append(Gap(task.task_id, "VALIDATION_RECEIPT_IDENTITY_MISMATCH", path.name))
                continue
            value = dict(item)
            value["source"] = f"{name}/projection/completion/validation_receipts/{path.name}"
            validations.setdefault(task.task_id, []).append(value)
    recon, recon_gaps = _reconciliation_receipts(roots, tasks, snapshot)
    gaps.extend(recon_gaps)
    for task_id, values in recon.items():
        receipts.setdefault(task_id, []).extend(values)
    return receipts, validations, gaps


class ProofReuseTaskEvidenceValidator:
    def __init__(self, todo: Path, state_root: Path, repo_root: Path = REPO_ROOT, now_ms: int | None = None) -> None:
        self.todo = todo
        self.state_root = state_root
        self.snapshot = GitSnapshot(repo_root)
        self.now_ms = int(time.time() * 1000) if now_ms is None else now_ms

    def audit(self) -> dict[str, Any]:
        # A caller that supplies the repository's sealed taskboard gets the
        # full authority boundary.  Small fixture boards remain useful for
        # unit-testing the pure observation mechanics, but are never reached
        # by the CLI or the live program path.
        sealed = self.todo.resolve() == TODO_PATH.resolve()
        board_gaps: list[Gap] = []
        quarantine: Mapping[str, Any] = {}
        if sealed:
            tasks, board_gaps, quarantine = _sealed_board(self.todo)
        else:
            tasks = parse_board(self.todo)
        completed = {key: value for key, value in tasks.items() if value.status in _COMPLETED}
        if sealed:
            # The controller-selected root must exist as a real directory even
            # when HOME/XDG are isolated temporary trees for the provider.
            try:
                self.state_root = self.state_root.expanduser().resolve()
            except OSError:
                board_gaps.append(Gap("BOARD", "STATE_ROOT_MISSING", "current"))
            if not self.state_root.is_dir():
                board_gaps.append(Gap("BOARD", "STATE_ROOT_MISSING", "current"))
            roots, root_gaps = _reviewed_roots(self.state_root) if self.state_root.is_dir() else ({}, [])
            if root_gaps or any(g.kind == "STATE_ROOT_MISSING" for g in board_gaps):
                receipts, validations, evidence_gaps = {}, {}, []
            else:
                receipts, validations, evidence_gaps = _authoritative_evidence(roots, tasks, self.snapshot)
            gaps: list[Gap] = [*board_gaps, *root_gaps, *evidence_gaps]
        else:
            # Compatibility fixtures exercise generic observation behavior only;
            # this path is not reachable from the live CLI's sealed board.
            receipts = {}
            validations = {}
            for source, record in _records(self.state_root):
                if receipt := _completion_receipt(record, source):
                    receipts.setdefault(receipt.task_id, []).append(receipt)
                if receipt := _validation_receipt(record, source):
                    validations.setdefault(str(record["task_id"]), []).append(receipt)
            gaps = list(board_gaps)
        task_reports: list[dict[str, Any]] = []
        accepted: dict[str, CompletedTaskArtifactReceipt] = {}
        later_ownership: list[dict[str, Any]] = []
        for task_id, task in sorted(completed.items()):
            observed = []
            for target in dict.fromkeys((*task.outputs, *task.validation_targets)):
                item, unsafe = self.snapshot.inspect_path(target)
                item["role"] = "output" if target in task.outputs else "validation_target"
                observed.append(item)
                if unsafe:
                    gaps.append(Gap(task_id, unsafe.kind, unsafe.detail))
                elif not item["present"]:
                    kind = "OUTPUT_MISSING" if target in task.outputs else "VALIDATION_TARGET_MISSING"
                    if isinstance(item.get("gitlink"), dict) and not item["gitlink"]["exact"]:
                        kind = "GITLINK_PIN_MISMATCH"
                    # Prefer the sealed quarantine's explicit later owner over
                    # unrelated DAG edges when attributing a missing artifact.
                    owner_meta = quarantine.get(target) if isinstance(quarantine, Mapping) else None
                    if isinstance(owner_meta, Mapping) and owner_meta.get("owner_task_id"):
                        owner = str(owner_meta["owner_task_id"])
                        later_ownership.append({
                            "path": target,
                            "roles": list(owner_meta.get("sources") or [item["role"]]),
                            "owner_task_id": owner,
                            "owner_status": str(owner_meta.get("owner_status") or ""),
                        })
                        gaps.append(Gap(owner, kind, target))
                    else:
                        gaps.append(Gap(task_id, kind, target))
            candidates = receipts.get(task_id, [])
            usable = [
                candidate for candidate in candidates
                if self.snapshot.is_ancestor(candidate.commit)
                and (not candidate.task_cid or candidate.task_cid == task.task_cid)
            ]
            if usable:
                accepted[task_id] = sorted(usable, key=lambda item: item.commit)[-1]
            else:
                if candidates and any(not self.snapshot.is_ancestor(item.commit) for item in candidates):
                    gaps.append(Gap(task_id, "RECEIPT_COMMIT_NOT_ANCESTOR", ", ".join(item.commit for item in candidates)))
                if candidates and any(item.task_cid and item.task_cid != task.task_cid for item in candidates):
                    gaps.append(Gap(task_id, "RECEIPT_TASK_CID_MISMATCH", task.task_cid))
                gaps.append(Gap(task_id, "COMPLETION_RECEIPT_MISSING", "no ancestor-bound task/merge receipt"))
            valid_receipts = self._validations(task, validations.get(task_id, []), gaps)
            if not valid_receipts:
                gaps.append(Gap(task_id, "VALIDATION_RECEIPT_MISSING", "no fresh exact-command proof-reuse-off receipt"))
            task_reports.append({
                "task_id": task_id,
                "task_cid": task.task_cid,
                "outputs_and_targets": observed,
                "completion_receipt": asdict(accepted[task_id]) if task_id in accepted else None,
                "validation_receipt_sources": [item["source"] for item in valid_receipts],
            })
        # Record ancestry between completed tasks only when both sides have
        # accepted receipts.  Missing receipts are not re-labeled as ownership.
        dependency_order: list[dict[str, Any]] = []
        for task_id, task in sorted(completed.items()):
            for dependency in task.dependencies:
                if dependency not in completed:
                    continue
                if task_id not in accepted or dependency not in accepted:
                    continue
                item = {
                    "later_task": task_id,
                    "dependency": dependency,
                    "later_commit": accepted[task_id].commit,
                    "dependency_commit": accepted[dependency].commit,
                    "ordered": False,
                }
                item["ordered"] = (
                    self.snapshot.is_ancestor(str(item["dependency_commit"]))
                    and _command(
                        "git", "merge-base", "--is-ancestor",
                        str(item["dependency_commit"]), str(item["later_commit"]),
                        cwd=self.snapshot.root,
                    )[0] == 0
                )
                if not item["ordered"]:
                    gaps.append(Gap(task_id, "DEPENDENCY_OWNERSHIP_NOT_LATER", dependency))
                dependency_order.append(item)
        # Quarantine entries for pending owners (PTR-163 / PTR-171 / ...) keep
        # ready=false even when the completed-task scan itself is quiet.
        for path, meta in sorted((quarantine or {}).items(), key=lambda pair: pair[0]):
            if not isinstance(meta, Mapping):
                continue
            owner = str(meta.get("owner_task_id") or "")
            if not owner or owner in completed:
                continue
            later_ownership.append({
                "path": path,
                "roles": list(meta.get("sources") or []),
                "owner_task_id": owner,
                "owner_status": str(meta.get("owner_status") or ""),
            })
            if owner in tasks and not any(
                gap.task_id == owner and gap.detail == path for gap in gaps
            ):
                gaps.append(Gap(owner, "HISTORICAL_MISSING_ARTIFACT_PENDING", path))
        audit_valid = not any(
            gap.task_id == "BOARD" or gap.kind.startswith("STATE_ROOT_") or gap.kind.startswith("BOARD_")
            for gap in gaps
        )
        # Body-free Landlock boundary receipt: diagnostic only, never authority.
        boundary = {
            "schema": "ipfs_accelerate_py/proof-backed-test-reuse-validation-boundary@1",
            "proof_authoritative": False,
            "completion_authority": False,
            "mode": "landlock-abi-3-or-newer-inherited",
        }
        body = {
            "schema": REPORT_SCHEMA,
            "interface": "ProofReuseTaskEvidenceValidator@1",
            "repository": {
                "commit": self.snapshot.commit,
                "tree": self.snapshot.tree,
                "gitlinks": self.snapshot.gitlinks,
                "gitlink_state_cid": self.snapshot.gitlink_state_cid,
            },
            "completed_task_count": len(completed),
            "tasks": task_reports,
            "dependency_order": dependency_order,
            "later_ownership": sorted(
                { (item["path"], item["owner_task_id"]): item for item in later_ownership }.values(),
                key=lambda item: (item["path"], item["owner_task_id"]),
            ),
            "gaps": [asdict(gap) for gap in sorted(gaps, key=lambda item: (item.task_id, item.kind, item.detail))],
            "boundary": boundary,
            "audit_valid": audit_valid,
            "ready": audit_valid and not gaps,
            "observation_only": True,
        }
        body["report_cid"] = canonical_cid(body)
        return body

    def _validations(self, task: Task, candidates: list[dict[str, Any]], gaps: list[Gap]) -> list[dict[str, Any]]:
        valid: list[dict[str, Any]] = []
        for item in candidates:
            problems: list[str] = []
            if item.get("validation_command") != task.validation_command:
                problems.append("VALIDATION_COMMAND_MISMATCH")
            if (
                item.get("passed") is not True
                or item.get("proof_reuse_mode") != "off"
                or item.get("disposition") not in {None, "executed"}
                or item.get("exit_code") not in {None, 0}
                or item.get("skipped_count") not in {None, 0}
                or item.get("status") not in {None, "passed"}
            ):
                problems.append("VALIDATION_NOT_PROOF_REUSE_OFF")
            if not isinstance(item.get("fresh_until_ms"), int) or item["fresh_until_ms"] < self.now_ms:
                problems.append("VALIDATION_RECEIPT_STALE")
            if (
                item.get("git_commit_id") != self.snapshot.commit
                or item.get("git_tree_id") != self.snapshot.tree
                or item.get("gitlink_state_cid") != self.snapshot.gitlink_state_cid
                or (
                    "repository_state_cid" in item
                    and item.get("repository_state_cid") != f"git-commit:{self.snapshot.commit}"
                )
            ):
                problems.append("VALIDATION_PIN_MISMATCH")
            if "dirty_overlay_cid" in item and not isinstance(item.get("dirty_overlay_cid"), str):
                problems.append("VALIDATION_DIRTY_OVERLAY_INVALID")
            if problems:
                for problem in problems:
                    gaps.append(Gap(task.task_id, problem, item["source"]))
            else:
                valid.append(item)
        return valid


def default_state_root() -> Path:
    # Controller semantics: IPFS_PROOF_REUSE_STATE_ROOT is the complete current
    # root override (v9).  Otherwise XDG state plus the sealed v9 suffix.
    # The implementation provider receives no state-root capability; only the
    # validation allowlist may inject the controller-selected directory.
    configured = os.environ.get("IPFS_PROOF_REUSE_STATE_ROOT", "").strip()
    if configured:
        return Path(configured)
    state_base = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
    return state_base / "ipfs_accelerate_py/proof-backed-test-reuse-v9"


def write_report(report: Mapping[str, Any], state_root: Path) -> Path:
    directory = state_root / "projection" / "task-evidence"
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{report['report_cid']}.json"
    if destination.exists():
        # A CID filename is not evidence by itself.  Refuse to reuse a
        # corrupted or substituted file.
        try:
            persisted = json.loads(destination.read_text(encoding="utf-8"))
            claimed = persisted.pop("report_cid")
            if claimed != report["report_cid"] or canonical_cid(persisted) != claimed:
                raise ValueError("report CID mismatch")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError):
            raise RuntimeError(f"existing report is not the claimed canonical report: {destination}")
        return destination
    temporary = directory / f".{report['report_cid']}.{os.getpid()}.tmp"
    temporary.write_bytes(canonical_json(report) + b"\n")
    os.replace(temporary, destination)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--todo", type=Path, default=TODO_PATH)
    parser.add_argument("--state-root", type=Path, default=default_state_root())
    parser.add_argument("--output", type=Path, help="optional explicit report location (does not create evidence)")
    parser.add_argument("--no-write", action="store_true")
    expectation = parser.add_mutually_exclusive_group()
    expectation.add_argument("--expect-incomplete", action="store_true")
    expectation.add_argument("--require-ready", action="store_true")
    args = parser.parse_args(argv)
    state_root = args.state_root.expanduser()
    try:
        state_root = state_root.resolve()
    except OSError:
        pass
    report = ProofReuseTaskEvidenceValidator(args.todo.resolve(), state_root).audit()
    if not args.no_write and state_root.is_dir() and report.get("audit_valid"):
        write_report(report, state_root)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical_json(report) + b"\n")
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    if args.expect_incomplete:
        # An invalid audit (for example a missing reviewed root) is not an
        # acceptable proof of incompleteness.  It needs one real attributed
        # gap from a valid full-board observation.
        return 0 if report.get("audit_valid") and report["gaps"] and not report["ready"] else 3
    if args.require_ready:
        return 0 if report["ready"] else 2
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

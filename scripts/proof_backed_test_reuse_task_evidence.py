#!/usr/bin/env python3
"""Read-only, fail-closed audit of retained proof-reuse task evidence.

The trust boundary here is deliberately small: the sealed board, completed
merge-queue rows with their train receipts, retained flat validation receipts,
and canonical reconciliation event streams.  It never searches state trees for
JSON which merely resembles one of those records.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
TODO_PATH = REPO_ROOT / "implementation_plan/docs/46-proof-backed-test-reuse.todo.md"
OBJECTIVE_PATH = REPO_ROOT / "implementation_plan/docs/46-proof-backed-test-reuse.objectives.md"
CONFIG_PATH = REPO_ROOT / "config/proof_backed_test_reuse_supervisor.json"
PLAN_PATH = REPO_ROOT / "implementation_plan/docs/46-proof-backed-test-reuse-plan-2026-07-31.md"
REPORT_SCHEMA = "ipfs_accelerate_py/proof-backed-test-reuse-task-evidence@1"
PREFLIGHT_SCHEMA = "ipfs_accelerate_py/proof-backed-test-reuse-preflight@1"
BOARD_NAMESPACE = "proof-backed-test-reuse-v1"
RECEIPT_SCHEMA = "ipfs_accelerate_py/proof-backed-test-reuse-executed-validation-receipt@1"
EVENT_MANIFEST_SCHEMA = "ipfs_accelerate_py.agent_supervisor.event-log-manifest@2"
EVENT_RECEIPT_SCHEMA = "ipfs_accelerate_py.agent_supervisor.member_completion_receipt@1"
MERGE_CANDIDATE_SCHEMA = "ipfs_accelerate_py/agent-supervisor/merge-candidate@3"
LANES = (0, 1, 2)
COMPLETED = frozenset({"complete", "completed", "done", "validated"})


def canonical_json(value: object) -> bytes:
    return json.dumps(value, allow_nan=False, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _varint(value: int) -> bytes:
    result = bytearray()
    while value > 127:
        result.append((value & 127) | 128); value >>= 7
    result.append(value)
    return bytes(result)


def canonical_cid(value: object) -> str:
    digest = hashlib.sha256(canonical_json(value)).digest()
    raw = _varint(1) + _varint(0x0129) + _varint(0x12) + _varint(len(digest)) + digest
    return "b" + base64.b32encode(raw).decode().lower().rstrip("=")


def validation_command_identity(command: str) -> str:
    """Use the validation producer's exact command-only identity projection."""
    external = REPO_ROOT / "external" / "ipfs_accelerate"
    if str(external) not in sys.path:
        sys.path.insert(0, str(external))
    from ipfs_accelerate_py.agent_supervisor.validation.proof_cached_test_validation import (  # type: ignore
        validation_command_identity as producer_identity,
    )
    return producer_identity(command)


def sha256(value: object) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def _read_json(path: Path) -> Mapping[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, Mapping) else None


def _command(args: tuple[str, ...], cwd: Path) -> tuple[int, str]:
    try:
        run = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    except OSError:
        return 127, ""
    return run.returncode, run.stdout.strip()


@dataclass(frozen=True)
class TaskIdentity:
    task_id: str
    canonical_task_key: str
    canonical_task_cid: str
    goal_id: str
    status: str
    outputs: tuple[str, ...]
    validation: tuple[str, ...]


@dataclass(frozen=True)
class Board:
    tasks: Mapping[str, TaskIdentity]
    later_owners: Mapping[str, str]
    errors: tuple[str, ...] = ()


def _board_module() -> Any:
    spec = importlib.util.spec_from_file_location("ptr_board_gate", REPO_ROOT / "scripts/validate_proof_backed_test_reuse_board.py")
    if not spec or not spec.loader:
        raise RuntimeError("board gate cannot be loaded")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def load_validated_board(todo: Path = TODO_PATH) -> Board:
    """Call the independent board gate and retain parser-provided identities."""
    errors: list[str] = []
    try:
        gate = _board_module()
        result = gate.validate(OBJECTIVE_PATH, todo, CONFIG_PATH, PLAN_PATH)
    except Exception as exc:  # no parser-only fallback is permitted
        return Board({}, {}, (f"BOARD_GATE_UNAVAILABLE:{type(exc).__name__}",))
    if not isinstance(result, Mapping) or result.get("schema") != PREFLIGHT_SCHEMA or result.get("valid") is not True or result.get("errors") != [] or result.get("task_count") != 77:
        return Board({}, {}, ("BOARD_GATE_INVALID",))
    try:
        external = REPO_ROOT / "external/ipfs_accelerate"
        if str(external) not in sys.path: sys.path.insert(0, str(external))
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file
        parsed = parse_task_file(todo, "## PTR-")
    except Exception as exc:
        return Board({}, {}, (f"BOARD_PARSER_UNAVAILABLE:{type(exc).__name__}",))
    tasks: dict[str, TaskIdentity] = {}
    for item in parsed:
        metadata = getattr(item, "metadata", {})
        metadata = metadata if isinstance(metadata, Mapping) else {}
        task = TaskIdentity(str(getattr(item, "task_id", "")), str(getattr(item, "canonical_task_key", "")), str(getattr(item, "canonical_task_cid", "")), str(metadata.get("goal id", metadata.get("goal_id", ""))), str(getattr(item, "status", "")).lower(), tuple(str(x) for x in getattr(item, "outputs", ())), tuple(str(x) for x in getattr(item, "validation", ())))
        if not task.task_id or task.task_id in tasks or not task.canonical_task_key or not task.canonical_task_cid:
            errors.append("BOARD_TASK_IDENTITY_INVALID")
        tasks[task.task_id] = task
    if len(tasks) != 77 or len(parsed) != 77 or any(getattr(x, "board_namespace", "") != BOARD_NAMESPACE for x in parsed): errors.append("BOARD_PARSER_CONTRACT_INVALID")
    owners = getattr(gate, "EXPECTED_HISTORICAL_MISSING_ARTIFACT_OWNERS", {})
    return Board(tasks, dict(owners) if isinstance(owners, Mapping) else {}, tuple(sorted(set(errors))))


class GitSnapshot:
    def __init__(self, root: Path) -> None:
        self.root = root
        _, self.commit = _command(("git", "rev-parse", "HEAD"), root)
        _, self.tree = _command(("git", "rev-parse", "HEAD^{tree}"), root)
        _, status = _command(("git", "status", "--porcelain=v1"), root)
        self.dirty = bool(status)
        self.dirty_overlay_cid = canonical_cid({"status": status}) if self.dirty else "cid:dirty-overlay:none"
        self.repository_id = os.environ.get("IPFS_PROOF_REUSE_REPOSITORY_ID", "lift_coding/proof-backed-test-reuse")
        _, listing = _command(("git", "ls-tree", "-r", "HEAD"), root)
        self.gitlinks = {line.partition("\t")[2]: line.partition("\t")[0].split()[2] for line in listing.splitlines() if len(line.partition("\t")[0].split()) == 3 and line.partition("\t")[0].split()[0] == "160000"}
        self.gitlink_state_cid = canonical_cid(self.gitlinks)
        self.repository_state_cid = "git-commit:" + self.commit if self.commit else ""
        self.repository_forest_cid = canonical_cid({"commit": self.commit, "tree": self.tree, "gitlinks": self.gitlinks})

    def is_ancestor(self, commit: str) -> bool | None:
        if not self.commit or not commit: return None
        rc, _ = _command(("git", "merge-base", "--is-ancestor", commit, self.commit), self.root)
        return True if rc == 0 else False


def configured_root() -> Path:
    override = os.environ.get("IPFS_PROOF_REUSE_STATE_ROOT")
    if override: return Path(override)
    base = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
    return base / "ipfs_accelerate_py/proof-backed-test-reuse-v8"


def reviewed_roots(root: Path) -> dict[str, Path]:
    return {"v8": root, "v6": root.parent / "proof-backed-test-reuse-v6", "v1": root.parent / "proof-backed-test-reuse-v1"}


def _triple(value: Mapping[str, Any], task: TaskIdentity) -> bool:
    return value.get("task_id") == task.task_id and value.get("canonical_task_key") == task.canonical_task_key and value.get("canonical_task_cid", value.get("canonical_task_id")) == task.canonical_task_cid


def _proof_passed(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("passed") is True


class ProofReuseTaskEvidenceValidator:
    def __init__(self, todo: Path = TODO_PATH, state_root: Path | None = None, repo_root: Path = REPO_ROOT, now_ms: int | None = None, board_loader: Callable[[], Board] | None = None) -> None:
        self.todo, self.state_root, self.snapshot = todo, state_root or configured_root(), GitSnapshot(repo_root)
        self.now_ms = int(time.time() * 1000) if now_ms is None else now_ms
        self.board_loader = board_loader or (lambda: load_validated_board(todo))

    def _audit_events(self, roots: Mapping[str, Path], board: Board, audit_errors: list[str]) -> set[str]:
        accepted: set[str] = set()
        for label, root in roots.items():
            for lane in LANES:
                path = root / "state" / f"ptr_lane_{lane}" / f"ptr_lane_{lane}_events.jsonl"
                manifest_path = path.with_suffix(path.suffix + ".manifest.json")
                manifest = _read_json(manifest_path)
                if manifest is None:
                    audit_errors.append(f"EVENT_MANIFEST_MISSING:{label}:{lane}"); continue
                if manifest.get("schema") != EVENT_MANIFEST_SCHEMA or manifest.get("manifest_digest") != sha256({k:v for k,v in manifest.items() if k != "manifest_digest"}):
                    audit_errors.append(f"EVENT_MANIFEST_INVALID:{label}:{lane}"); continue
                files = manifest.get("files")
                if not isinstance(files, list) or not files:
                    audit_errors.append(f"EVENT_MANIFEST_POPULATION_INVALID:{label}:{lane}"); continue
                if manifest.get("active_path") != path.name:
                    audit_errors.append(f"EVENT_MANIFEST_ACTIVE_PATH_INVALID:{label}:{lane}"); continue
                previous, next_seq, stream, snapshot = "", manifest.get("earliest_sequence"), manifest.get("stream_id"), manifest.get("snapshot_id")
                if not isinstance(next_seq, int) or not isinstance(stream, str) or not isinstance(snapshot, str): audit_errors.append(f"EVENT_MANIFEST_IDENTITY_INVALID:{label}:{lane}"); continue
                names: set[str] = set()
                for segment in files:
                    if not isinstance(segment, Mapping) or segment.get("canonical_events") is not True or not isinstance(segment.get("path"), str) or "/" in segment["path"] or not segment["path"].startswith(f"ptr_lane_{lane}"):
                        audit_errors.append(f"EVENT_SEGMENT_INVALID:{label}:{lane}"); break
                    if segment["path"] in names or not isinstance(segment.get("first_sequence"), int) or segment["first_sequence"] != next_seq or segment.get("start_previous_event_id", "") != previous:
                        audit_errors.append(f"EVENT_SEGMENT_CHAIN_INVALID:{label}:{lane}"); break
                    names.add(segment["path"])
                    segment_path = path.parent / segment["path"]
                    try: raw = segment_path.read_bytes()
                    except OSError: audit_errors.append(f"EVENT_SEGMENT_MISSING:{label}:{lane}"); break
                    lines = [line for line in raw.splitlines() if line]
                    if segment.get("size_bytes") != len(raw) or segment.get("event_count") != len(lines) or (segment.get("sha256") and segment.get("sha256") != "sha256:" + hashlib.sha256(raw).hexdigest()): audit_errors.append(f"EVENT_SEGMENT_DIGEST_INVALID:{label}:{lane}"); break
                    for line in lines:
                        try: event = json.loads(line)
                        except json.JSONDecodeError: audit_errors.append(f"EVENT_JSON_INVALID:{label}:{lane}"); break
                        if not isinstance(event, Mapping) or event.get("sequence") != next_seq or event.get("previous_event_id", "") != previous or event.get("stream_id") != stream or event.get("snapshot_id") != snapshot or event.get("event_id") != sha256({k:v for k,v in event.items() if k != "event_id"}): audit_errors.append(f"EVENT_CHAIN_INVALID:{label}:{lane}"); break
                        previous, next_seq = str(event["event_id"]), next_seq + 1
                        task = board.tasks.get(str(event.get("task_id", "")))
                        if task and event.get("type") == "merge_reconciled" and event.get("resolved") is True and event.get("reason") == "implementation_branch_already_merged" and _triple(event, task):
                            cids = event.get("completion_task_cids")
                            receipt = event.get("completion_receipt", event.get("member_completion_receipt"))
                            proof = event.get("integration_commit_proof")
                            if isinstance(cids, Mapping) and cids.get(task.task_id) == task.canonical_task_cid and _proof_passed(proof) and _proof_passed(event.get("declared_output_proof", event.get("post_merge_declared_output_invariant"))) and event.get("durable_completion_persisted", event.get("completion_persisted")) is True and isinstance(receipt, Mapping) and receipt.get("schema") == EVENT_RECEIPT_SCHEMA and receipt.get("status") == "succeeded" and _triple(receipt, task) and self.snapshot.is_ancestor(str(proof.get("integration_commit", ""))) is True:
                                accepted.add(task.task_id)
                    if segment.get("last_sequence") != next_seq - 1:
                        audit_errors.append(f"EVENT_SEGMENT_TAIL_INVALID:{label}:{lane}"); break
                if path.name not in names:
                    audit_errors.append(f"EVENT_MANIFEST_ACTIVE_SEGMENT_MISSING:{label}:{lane}")
                if previous != manifest.get("last_event_id") or next_seq - 1 != manifest.get("latest_sequence"):
                    audit_errors.append(f"EVENT_MANIFEST_TAIL_INVALID:{label}:{lane}")
        return accepted

    def _queue_completion(self, roots: Mapping[str, Path], board: Board) -> set[str]:
        accepted: set[str] = set()
        for root in roots.values():
            directory = root / "merge-queue" / "completed"
            if not directory.is_dir(): continue
            for row_path in sorted(directory.glob("*.json")):
                row = _read_json(row_path)
                if not row or row.get("status") != "completed" or not isinstance(row.get("metadata"), Mapping) or row["metadata"].get("schema") != MERGE_CANDIDATE_SCHEMA: continue
                task = board.tasks.get(str(row.get("task_id", "")))
                request, dedupe = row.get("request_id"), row.get("dedupe_key")
                if not task or not isinstance(request, str) or not isinstance(dedupe, str) or not _triple(row, task): continue
                train_path = root / "merge-queue" / "train" / "receipts" / f"{dedupe}.json"
                train = _read_json(train_path)
                admission = train.get("distributed_publication_admission") if train else None
                train_request = admission.get("request_id") if isinstance(admission, Mapping) else (train.get("request_id") if train else None)
                if not train or train_path.stem != dedupe or train_request != request or train.get("canonical_task_id") != task.canonical_task_key: continue
                merge, proof = train.get("merge_result"), train.get("merge_result", {}).get("integration_commit_proof") if isinstance(train.get("merge_result"), Mapping) else None
                already_merged_ok = train.get("status") != "already_merged" or (isinstance(merge, Mapping) and _proof_passed(merge.get("integrated_handoff_proof")) and merge.get("already_merged") is True)
                if train.get("status") in {"merged", "already_merged"} and train.get("integrated") is True and isinstance(merge, Mapping) and merge.get("merged") is True and merge.get("returncode") == 0 and _proof_passed(proof) and _proof_passed(merge.get("post_merge_declared_output_invariant")) and already_merged_ok and self.snapshot.is_ancestor(str(proof.get("integration_commit", ""))) is True:
                    accepted.add(task.task_id)
        return accepted

    def _validation(self, task: TaskIdentity, root: Path) -> tuple[bool, str]:
        path = root / "projection" / "completion" / "validation_receipts" / f"{task.task_id}.json"
        receipt = _read_json(path)
        if receipt is None: return False, "VALIDATION_RECEIPT_MISSING"
        claim = receipt.get("validation_receipt_cid")
        if receipt.get("schema") != RECEIPT_SCHEMA or claim != canonical_cid({k:v for k,v in receipt.items() if k != "validation_receipt_cid"}): return False, "VALIDATION_RECEIPT_BODY_CID_MISMATCH"
        if any(isinstance(value, (Mapping, list)) for value in receipt.values()): return False, "VALIDATION_RECEIPT_NOT_FLAT"
        command = receipt.get("validation_command")
        if not isinstance(command, str) or receipt.get("validation_command_cid") != validation_command_identity(command): return False, "VALIDATION_COMMAND_CID_MISMATCH"
        command_ok = command in task.validation
        exact = receipt.get("task_id") == task.task_id and receipt.get("task_cid") == task.canonical_task_cid and receipt.get("goal_id") == task.goal_id
        result_ok = receipt.get("proof_reuse_mode") == "off" and receipt.get("disposition") == "executed" and receipt.get("passed") is True and receipt.get("status") == "passed" and receipt.get("exit_code") == 0 and receipt.get("skipped_count") == 0
        pin_ok = receipt.get("repository_id") == self.snapshot.repository_id and receipt.get("repository_state_cid") == self.snapshot.repository_state_cid and receipt.get("git_commit_id") == self.snapshot.commit and receipt.get("git_tree_id") == self.snapshot.tree and receipt.get("gitlink_state_cid") == self.snapshot.gitlink_state_cid and receipt.get("repository_forest_cid") == self.snapshot.repository_forest_cid and receipt.get("dirty") is self.snapshot.dirty and receipt.get("dirty_overlay_cid") == self.snapshot.dirty_overlay_cid
        fresh, observed = receipt.get("fresh_until_ms"), receipt.get("observed_at_ms")
        if not isinstance(fresh, int) or not isinstance(observed, int): return False, "VALIDATION_FRESHNESS_MISMATCH"
        if fresh < self.now_ms: return False, "VALIDATION_RECEIPT_STALE"
        if not command_ok: return False, "VALIDATION_COMMAND_MISMATCH"
        if not exact: return False, "VALIDATION_TASK_BINDING_MISMATCH"
        if not result_ok: return False, "VALIDATION_EXECUTION_MISMATCH"
        if not pin_ok: return False, "VALIDATION_PIN_MISMATCH"
        return True, ""

    def audit(self) -> dict[str, Any]:
        board = self.board_loader(); audit_errors = list(board.errors); roots = reviewed_roots(self.state_root)
        for label, root in roots.items():
            if not root.is_dir(): audit_errors.append(f"REVIEWED_ROOT_MISSING:{label}")
        accepted_events = self._audit_events(roots, board, audit_errors) if not audit_errors else set()
        accepted_queue = self._queue_completion(roots, board) if not audit_errors else set()
        gaps: list[dict[str, str]] = []
        for task in sorted(board.tasks.values(), key=lambda x: x.task_id):
            if task.status not in COMPLETED: continue
            if task.task_id not in accepted_events and task.task_id not in accepted_queue:
                gaps.append({"task_id":task.task_id,"canonical_task_key":task.canonical_task_key,"canonical_task_cid":task.canonical_task_cid,"kind":"COMPLETION_PROVENANCE_GAP","detail":"no bound queue/train or reconciled-event authority"})
            valid, kind = self._validation(task, roots["v1"])
            if not valid: gaps.append({"task_id":task.task_id,"canonical_task_key":task.canonical_task_key,"canonical_task_cid":task.canonical_task_cid,"kind":kind,"detail":"retained flat receipt"})
        for missing, owner in sorted(board.later_owners.items()):
            if not (self.snapshot.root / missing).exists():
                task = board.tasks.get(owner)
                if task: gaps.append({"task_id":task.task_id,"canonical_task_key":task.canonical_task_key,"canonical_task_cid":task.canonical_task_cid,"kind":"PENDING_LATER_OWNER","detail":missing})
        gaps.sort(key=lambda x:(x["task_id"],x["kind"],x["detail"]))
        audit_valid = not audit_errors
        body = {"schema":REPORT_SCHEMA,"audit_valid":audit_valid,"ready":audit_valid and not gaps,"board":{"task_count":len(board.tasks),"namespace":BOARD_NAMESPACE},"audit_errors":sorted(set(audit_errors)),"gaps":gaps,"observation_only":True}
        body["report_cid"] = canonical_cid(body)
        return body


def write_report(report: Mapping[str, Any], state_root: Path) -> Path:
    destination = state_root / "projection" / "task-evidence" / f"{report['report_cid']}.json"
    encoded = canonical_json(report) + b"\n"
    if destination.exists():
        try:
            existing_bytes = destination.read_bytes()
            existing = json.loads(existing_bytes)
            if (isinstance(existing, Mapping) and existing.get("report_cid") == report["report_cid"]
                    and canonical_cid({key: value for key, value in existing.items() if key != "report_cid"}) == report["report_cid"]
                    and existing_bytes == encoded):
                return destination
        except OSError: pass
        except (UnicodeDecodeError, json.JSONDecodeError): pass
        raise RuntimeError("existing CID-named report has different bytes")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp"); temporary.write_bytes(encoded); os.replace(temporary, destination)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--todo", type=Path, default=TODO_PATH); parser.add_argument("--state-root", type=Path, default=configured_root()); parser.add_argument("--no-write", action="store_true")
    mode = parser.add_mutually_exclusive_group(); mode.add_argument("--expect-incomplete", action="store_true"); mode.add_argument("--require-ready", action="store_true")
    args = parser.parse_args(argv); report = ProofReuseTaskEvidenceValidator(args.todo, args.state_root).audit()
    if not args.no_write:
        try: write_report(report, args.state_root)
        except RuntimeError as exc: report["audit_valid"] = False; report["ready"] = False; report["audit_errors"].append(str(exc))
    sys.stdout.write(json.dumps(report, sort_keys=True, indent=2) + "\n")
    if args.expect_incomplete: return 0 if report["audit_valid"] and not report["ready"] and report["gaps"] else 3
    return 0 if report["ready"] else 2


if __name__ == "__main__": raise SystemExit(main())

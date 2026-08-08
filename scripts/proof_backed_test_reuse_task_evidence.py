#!/usr/bin/env python3
"""Fail-closed, observation-only audit of v8 task completion evidence.

Only supervisor-produced queue/train/validation receipts and manifest-bound event
logs are inputs.  This tool intentionally does not repair, refresh, or infer
evidence: an absent or non-current receipt is reported as a typed gap.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
TODO_PATH = REPO_ROOT / "implementation_plan/docs/46-proof-backed-test-reuse.todo.md"
REPORT_SCHEMA = "ipfs_accelerate_py/proof-backed-test-reuse-task-evidence@2"
STATE_ROOT_ENV = "IPFS_PROOF_REUSE_STATE_ROOT"
SEALED_STATE_SUFFIX = Path("ipfs_accelerate_py/proof-backed-test-reuse-v8")
COMPLETION_SCHEMA = "ipfs_accelerate_py/agent-supervisor/merge-candidate@3"
VALIDATION_SCHEMAS = frozenset({
    "ipfs_accelerate_py/proof-reuse-validation-receipt@1",
    "ipfs_accelerate_py/agent-supervisor/validation-receipt@1",
})
EVENT_MANIFEST_SCHEMA = "ipfs_accelerate_py.agent_supervisor.event-log-manifest@2"
COMPLETED = frozenset({"complete", "completed", "done", "validated"})
HEX = re.compile(r"^[0-9a-f]{40,64}$")
CID = re.compile(r"^b[a-z2-7]{20,}$")
PATH = re.compile(r"(?<![A-Za-z0-9_./-])((?:external|implementation_plan|config|scripts|tests|test)/[A-Za-z0-9_@%+=:,./-]+)")


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
    digest = hashlib.sha256(canonical_json(value)).digest()
    raw = _varint(1) + _varint(0x129) + _varint(0x12) + _varint(len(digest)) + digest
    return "b" + base64.b32encode(raw).decode("ascii").lower().rstrip("=")


def _sha256(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _command(*args: str, cwd: Path) -> tuple[int, str]:
    try:
        run = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    except OSError:
        return 127, ""
    return run.returncode, run.stdout.strip()


def _safe_path(value: str) -> str | None:
    path = PurePosixPath(value.replace("\\", "/"))
    if not value or "\x00" in value or path.is_absolute() or ".." in path.parts or path.as_posix() in {".", ".."}:
        return None
    return path.as_posix()


def validation_targets(command: str) -> tuple[str, ...]:
    return tuple(sorted({target for raw in PATH.findall(command)
                         if (target := _safe_path(raw.split("::", 1)[0].rstrip(",;)]}")))
                         and PurePosixPath(target).suffix}))


def canonical_validation_command_cid(command: str) -> str:
    """The receipt command identity is separate from a task identity."""
    return canonical_cid({"schema": "ipfs_accelerate_py/validation-command@1", "command": command})


@dataclass(frozen=True)
class Task:
    task_id: str
    canonical_task_key: str
    canonical_task_cid: str
    status: str
    outputs: tuple[str, ...]
    validation_command: str
    validation_targets: tuple[str, ...]

    @property
    def identity(self) -> tuple[str, str, str]:
        return (self.task_id, self.canonical_task_key, self.canonical_task_cid)


@dataclass(frozen=True, order=True)
class Gap:
    task_id: str
    kind: str
    detail: str
    owner_attributed: bool = False

    def json(self) -> dict[str, Any]:
        return {"task_id": self.task_id, "kind": self.kind, "detail": self.detail,
                "owner_attributed": self.owner_attributed}


def _supervisor_tasks(path: Path) -> dict[str, Task]:
    """Use the supervisor parser; task identities are never locally derived."""
    accelerate = REPO_ROOT / "external/ipfs_accelerate"
    if str(accelerate) not in sys.path:
        sys.path.insert(0, str(accelerate))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    parsed = parse_task_file(path, "## PTR-")
    result: dict[str, Task] = {}
    for item in parsed:
        task_id = str(item.task_id)
        key = str(item.canonical_task_key)
        cid = str(item.canonical_task_cid)
        if not task_id or not key.startswith("task/") or not CID.fullmatch(cid) or task_id in result:
            raise ValueError("supervisor parser returned malformed or duplicate task identity")
        command = str(item.metadata.get("validation", ""))
        outputs = tuple(sorted(filter(None, (_safe_path(str(p)) for p in item.outputs))))
        result[task_id] = Task(task_id, key, cid, str(item.status).lower(), outputs, command, validation_targets(command))
    if not result:
        raise ValueError("board has no supervisor tasks")
    return result


def parse_board(path: Path) -> dict[str, Task]:
    return _supervisor_tasks(path)


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
                fields = meta.split()
                if len(fields) == 3 and fields[0] == "160000" and fields[1] == "commit":
                    self.gitlinks[name] = fields[2]

    @property
    def valid(self) -> bool:
        return bool(HEX.fullmatch(self.commit) and HEX.fullmatch(self.tree))

    @property
    def gitlink_state_cid(self) -> str:
        return canonical_cid({"gitlinks": dict(sorted(self.gitlinks.items()))})

    def is_ancestor(self, commit: str) -> bool:
        return bool(HEX.fullmatch(commit)) and _command("git", "merge-base", "--is-ancestor", commit, self.commit, cwd=self.root)[0] == 0

    def inspect_path(self, value: str) -> tuple[dict[str, Any], str | None]:
        path = _safe_path(value)
        if path is None:
            return {"path": value, "present": False}, "UNSAFE_PATH"
        owner = max((p for p in self.gitlinks if path == p or path.startswith(p + "/")), key=len, default="")
        repo, revision, relative = self.root, "HEAD", path
        expected = observed = self.commit
        if owner:
            expected = self.gitlinks[owner]
            repo = self.root / owner
            _, observed = _command("git", "rev-parse", "HEAD", cwd=repo)
            revision, relative = expected, path[len(owner):].lstrip("/")
        exact_checkout = expected == observed
        rc, line = _command("git", "ls-tree", revision, "--", relative, cwd=repo)
        fields = line.split() if rc == 0 else []
        blob = fields[2] if len(fields) >= 3 and fields[1] == "blob" else ""
        present = bool(blob) and exact_checkout
        blob_sha = ""
        checkout_sha = ""
        if present:
            try:
                shown = subprocess.run(("git", "show", f"{revision}:{relative}"), cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
                blob_sha = _sha256(shown.stdout) if shown.returncode == 0 else ""
                local = repo / relative
                checkout_sha = _sha256(local.read_bytes()) if local.is_file() else ""
            except OSError:
                pass
        return {"path": path, "owner": owner or ".", "expected_gitlink": expected,
                "observed_gitlink": observed, "checkout_exact": exact_checkout,
                "present": present, "blob_oid": blob, "blob_sha256": blob_sha,
                "checkout_sha256": checkout_sha, "digest_exact": bool(blob_sha and blob_sha == checkout_sha)}, None


def _read_json(path: Path) -> tuple[Mapping[str, Any] | None, str | None]:
    try:
        if path.is_symlink() or path.stat().st_size > 4_000_000:
            return None, "unsafe_or_oversize"
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, "malformed"
    return (value, None) if isinstance(value, Mapping) else (None, "not_object")


def _file_identity(path: Path, kind: str, record: Mapping[str, Any]) -> str | None:
    """Verify the identity convention of one explicitly-supported store.

    Train receipt filenames are merge-request dedupe keys, not hashes of their
    envelopes.  Validation receipt envelopes are content addressed.  Queue rows
    are request-id named and become authoritative only through the exact join.
    """
    stem = path.stem
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if kind == "train":
        return stem if re.fullmatch(r"[0-9a-f]{64}", stem) else None
    if kind == "validation" and CID.fullmatch(stem):
        value, error = _read_json(path)
        return stem if error is None and canonical_cid(value) == stem else None
    if kind == "queue" and re.fullmatch(r"[0-9a-f]{64}", stem):
        return stem if hashlib.sha256(raw).hexdigest() == stem else None
    # Queue completion rows have stable request-id names, so their embedded
    # dedupe key is the content identity and is checked by the train join.
    return _sha256(raw)


def _supported_paths(state_root: Path) -> Iterable[tuple[str, Path]]:
    """Yield a finite allow-list; no recursive general JSON discovery."""
    for path in sorted((state_root / "merge-queue" / "completed").glob("*.json")):
        yield "queue", path
    for path in sorted((state_root / "merge-queue" / "train" / "receipts").glob("*.json")):
        yield "train", path
    roots = [state_root / "state"]
    roots.extend(sorted((state_root / "state" / "preflight" / "reconciliation").glob("ptr_lane_*")))
    for root in roots:
        if root.name == "state":
            lanes = sorted(root.glob("ptr_lane_*"))
        else:
            lanes = [root]
        for lane in lanes:
            if not lane.is_dir():
                continue
            for path in sorted((lane / "validation" / "receipts").glob("*.json")):
                yield "validation", path


def _event_manifests(state_root: Path) -> Iterable[Path]:
    roots = [state_root / "state"] + sorted((state_root / "state" / "preflight" / "reconciliation").glob("ptr_lane_*"))
    for root in roots:
        lanes = sorted(root.glob("ptr_lane_*")) if root.name == "state" else [root]
        for lane in lanes:
            if lane.is_dir():
                yield from sorted(lane.glob("ptr_lane_*_events.jsonl.manifest.json"))
                yield from sorted(lane.glob("ptr_lane_*_supervisor_events.jsonl.manifest.json"))


def _verify_event_chain(manifest_path: Path) -> str | None:
    manifest, error = _read_json(manifest_path)
    if error or manifest is None or manifest.get("schema") != EVENT_MANIFEST_SCHEMA:
        return "EVENT_MANIFEST_MALFORMED"
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        return "EVENT_MANIFEST_MALFORMED"
    for item in files:
        if not isinstance(item, Mapping) or item.get("canonical_events") is not True or not isinstance(item.get("path"), str):
            return "EVENT_MANIFEST_MALFORMED"
        name = _safe_path(str(item["path"]))
        if name is None or "/" in name or not name.endswith(".jsonl"):
            return "EVENT_MANIFEST_MALFORMED"
        event_file = manifest_path.parent / name
        try:
            lines = event_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            return "EVENT_CHAIN_MISSING"
        if isinstance(item.get("event_count"), int) and item["event_count"] != len(lines):
            return "EVENT_CHAIN_TAMPERED"
        previous = str(item.get("start_previous_event_id", ""))
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                return "EVENT_CHAIN_TAMPERED"
            if not isinstance(event, Mapping) or event.get("previous_event_id", "") != previous:
                return "EVENT_CHAIN_TAMPERED"
            event_id = event.get("event_id")
            payload = dict(event)
            payload.pop("event_id", None)
            if not isinstance(event_id, str) or event_id != _sha256(canonical_json(payload)):
                return "EVENT_CHAIN_TAMPERED"
            previous = event_id
    return None


def _identity_matches(record: Mapping[str, Any], task: Task) -> bool:
    return (record.get("task_id"), record.get("canonical_task_key"),
            record.get("canonical_task_cid", record.get("canonical_task_id"))) == task.identity


def _completion_binding(queue: Mapping[str, Any], train: Mapping[str, Any], task: Task) -> bool:
    metadata = queue.get("metadata") if isinstance(queue.get("metadata"), Mapping) else {}
    nested = metadata.get("task") if isinstance(metadata.get("task"), Mapping) else {}
    task_cids = metadata.get("completion_task_cids") if isinstance(metadata.get("completion_task_cids"), Mapping) else {}
    nested_match = _identity_matches(nested, task) or task_cids.get(task.task_id) == task.canonical_task_cid
    return (nested_match and queue.get("request_id") == train.get("request_id") and
            queue.get("dedupe_key") == Path(str(train.get("_source_name", ""))).stem and
            train.get("task_id") == task.task_id and train.get("canonical_task_id") == task.canonical_task_key)


def _receipt_payload(record: Mapping[str, Any]) -> Mapping[str, Any] | None:
    payload = record.get("payload")
    return payload if isinstance(payload, Mapping) else None


def _valid_validation(record: Mapping[str, Any], task: Task, snapshot: GitSnapshot) -> str | None:
    if record.get("schema") not in VALIDATION_SCHEMAS:
        return "VALIDATION_SCHEMA_UNSUPPORTED"
    payload = _receipt_payload(record)
    cid = record.get("validation_receipt_cid")
    if not isinstance(payload, Mapping) or not isinstance(cid, str) or not CID.fullmatch(cid) or canonical_cid(payload) != cid:
        return "VALIDATION_RECEIPT_UNAUTHENTICATED"
    if not _identity_matches(payload, task):
        return "VALIDATION_TASK_IDENTITY_MISMATCH"
    if payload.get("validation_command_cid") != canonical_validation_command_cid(task.validation_command):
        return "VALIDATION_COMMAND_MISMATCH"
    if payload.get("proof_reuse_mode") != "off" or payload.get("passed") is not True or payload.get("exit_code") != 0 or payload.get("skipped", 0) != 0:
        return "VALIDATION_DISPOSITION_INVALID"
    if payload.get("git_commit_id") != snapshot.commit or payload.get("git_tree_id") != snapshot.tree or payload.get("gitlink_state_cid") != snapshot.gitlink_state_cid:
        return "VALIDATION_PIN_MISMATCH"
    if payload.get("fresh") is not True:
        return "VALIDATION_RECEIPT_STALE"
    return None


def _sealed_owners(tasks: Mapping[str, Task], declared_paths: set[str]) -> dict[str, str]:
    """Read the board validator's literal quarantine, never a DAG inference."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("proof_reuse_board_validator", REPO_ROOT / "scripts/validate_proof_backed_test_reuse_board.py")
    if spec is None or spec.loader is None:
        raise ValueError("sealed historical-missing-artifact quarantine unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    owners = {path: owner for path, owner in
              dict(getattr(module, "EXPECTED_HISTORICAL_MISSING_ARTIFACT_OWNERS", {})).items()
              if path in declared_paths}
    if any(owner not in tasks for owner in owners.values()):
        raise ValueError("sealed historical-missing-artifact quarantine does not bind board")
    return owners


class ProofReuseTaskEvidenceValidator:
    def __init__(self, todo: Path, state_root: Path, repo_root: Path = REPO_ROOT) -> None:
        self.todo, self.state_root, self.snapshot = todo, state_root, GitSnapshot(repo_root)

    def audit(self) -> dict[str, Any]:
        errors: list[str] = []
        try:
            tasks = parse_board(self.todo)
        except Exception as exc:  # The CLI must report malformed boards, not continue.
            tasks, errors = {}, ["BOARD_INVALID:" + type(exc).__name__]
        if not self.state_root.is_dir():
            errors.append("STATE_ROOT_MISSING")
        if not self.snapshot.valid:
            errors.append("REPOSITORY_SNAPSHOT_INVALID")
        manifests = list(_event_manifests(self.state_root)) if self.state_root.is_dir() else []
        if not manifests:
            errors.append("EVENT_CHAIN_MISSING")
        else:
            errors.extend(sorted({error for path in manifests if (error := _verify_event_chain(path))}))
        completed = {key: task for key, task in tasks.items() if task.status in COMPLETED}
        queue: list[Mapping[str, Any]] = []
        train: list[Mapping[str, Any]] = []
        validations: list[Mapping[str, Any]] = []
        source_errors: list[str] = []
        if self.state_root.is_dir():
            for kind, path in _supported_paths(self.state_root):
                record, error = _read_json(path)
                if error:
                    source_errors.append("SUPPORTED_SOURCE_" + error.upper())
                    continue
                assert record is not None
                identity = _file_identity(path, kind, record)
                if identity is None:
                    source_errors.append("SUPPORTED_SOURCE_CONTENT_ID_MISMATCH")
                    continue
                item = dict(record)
                item["_source_name"] = path.name
                if kind == "queue" and item.get("metadata", {}).get("schema") == COMPLETION_SCHEMA:
                    queue.append(item)
                elif kind == "train":
                    train.append(item)
                elif kind == "validation":
                    validations.append(item)
        errors.extend(sorted(set(source_errors)))
        gaps: list[Gap] = []
        reports: list[dict[str, Any]] = []
        owners: dict[str, str] = {}
        if tasks:
            try:
                declared_paths = {path for task in completed.values()
                                  for path in (*task.outputs, *task.validation_targets)}
                owners = _sealed_owners(tasks, declared_paths)
            except Exception as exc:
                errors.append("HISTORICAL_QUARANTINE_INVALID:" + type(exc).__name__)
        for task_id, task in sorted(completed.items()):
            facts: list[dict[str, Any]] = []
            for target in dict.fromkeys((*task.outputs, *task.validation_targets)):
                fact, unsafe = self.snapshot.inspect_path(target)
                role = "output" if target in task.outputs else "validation_target"
                fact["role"] = role
                facts.append(fact)
                if unsafe:
                    gaps.append(Gap(task_id, unsafe, target))
                elif not fact["checkout_exact"]:
                    gaps.append(Gap(task_id, "GITLINK_PIN_MISMATCH", target))
                elif not fact["present"]:
                    owner = owners.get(target, "")
                    if owner and tasks[owner].status not in COMPLETED:
                        owner_task = tasks[owner]
                        gaps.append(Gap(task_id, "OWNED_HISTORICAL_MISSING_ARTIFACT", f"{role}:{target}:{owner_task.task_id}:{owner_task.canonical_task_cid}", True))
                    elif owner:
                        errors.append("HISTORICAL_OWNER_NOT_PENDING:" + owner)
                    else:
                        gaps.append(Gap(task_id, "OUTPUT_MISSING" if role == "output" else "VALIDATION_TARGET_MISSING", target))
                elif not fact["digest_exact"]:
                    gaps.append(Gap(task_id, "CHECKOUT_DIGEST_MISMATCH", target))
            candidates = [q for q in queue if _identity_matches(q, task)]
            accepted: Mapping[str, Any] | None = None
            for q in candidates:
                for t in train:
                    if not _completion_binding(q, t, task):
                        continue
                    integration = t.get("merge_result", {}).get("integration_commit_proof", {}) if isinstance(t.get("merge_result"), Mapping) else {}
                    commit = str(t.get("target_commit", ""))
                    successful = t.get("status") in {"merged", "already_merged"} and t.get("integrated") is True
                    if successful and isinstance(integration, Mapping) and integration.get("passed") is True and self.snapshot.is_ancestor(commit):
                        accepted = t
                        break
                if accepted:
                    break
            if not accepted:
                gaps.append(Gap(task_id, "COMPLETION_RECEIPT_MISSING", "no exact queue/train integrated ancestor join"))
            validation_errors = [_valid_validation(v, task, self.snapshot) for v in validations if _identity_matches(_receipt_payload(v) or {}, task)]
            validation_errors = [item for item in validation_errors if item]
            validation_ok = any(_valid_validation(v, task, self.snapshot) is None
                                for v in validations if _identity_matches(_receipt_payload(v) or {}, task))
            if not validation_ok:
                gaps.append(Gap(task_id, validation_errors[0] if validation_errors else "VALIDATION_RECEIPT_MISSING", "no authenticated current proof-reuse-off receipt"))
            reports.append({"identity": {"task_id": task.task_id, "canonical_task_key": task.canonical_task_key, "canonical_task_cid": task.canonical_task_cid},
                            "artifacts": sorted(facts, key=lambda item: (item["role"], item["path"])),
                            "completion_integrated": accepted is not None, "validation_current": validation_ok})
        errors = sorted(set(errors))
        gaps = sorted(set(gaps))
        audit_valid = not errors
        body: dict[str, Any] = {
            "schema": REPORT_SCHEMA, "interface": "ProofReuseTaskEvidenceValidator@2", "observation_only": True,
            "audit_valid": audit_valid, "ready": audit_valid and not gaps,
            "repository": {"commit": self.snapshot.commit, "tree": self.snapshot.tree,
                           "gitlinks": dict(sorted(self.snapshot.gitlinks.items())), "gitlink_state_cid": self.snapshot.gitlink_state_cid},
            "completed_task_count": len(completed), "tasks": reports,
            "gaps": [gap.json() for gap in gaps], "audit_errors": errors,
        }
        body["report_cid"] = canonical_cid(body)
        return body


def default_state_root() -> Path:
    base = Path(os.environ.get(STATE_ROOT_ENV, Path.home() / ".local/state"))
    return base if base.as_posix().endswith(SEALED_STATE_SUFFIX.as_posix()) else base / SEALED_STATE_SUFFIX


def _report_bytes(report: Mapping[str, Any]) -> bytes:
    body = dict(report)
    claimed = body.pop("report_cid", None)
    if claimed != canonical_cid(body):
        raise ValueError("report CID does not rehash")
    return canonical_json(dict(report)) + b"\n"


def write_report(report: Mapping[str, Any], state_root: Path) -> Path:
    data = _report_bytes(report)
    directory = state_root / "projection" / "task-evidence"
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{report['report_cid']}.json"
    if destination.exists():
        if destination.read_bytes() != data:
            raise ValueError("existing CID-named report does not rehash")
        return destination
    temporary = directory / f".{report['report_cid']}.{os.getpid()}.tmp"
    temporary.write_bytes(data)
    os.replace(temporary, destination)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--todo", type=Path, default=TODO_PATH)
    parser.add_argument("--state-root", type=Path, default=default_state_root())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--no-write", action="store_true")
    expectation = parser.add_mutually_exclusive_group()
    expectation.add_argument("--expect-incomplete", action="store_true")
    expectation.add_argument("--require-ready", action="store_true")
    args = parser.parse_args(argv)
    report = ProofReuseTaskEvidenceValidator(args.todo, args.state_root).audit()
    write_failed = False
    try:
        if not args.no_write:
            write_report(report, args.state_root)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(_report_bytes(report))
    except (OSError, ValueError) as exc:
        # Do not mutate a CID-bound observation after calculating its CID.
        write_failed = True
        sys.stderr.write("REPORT_WRITE_INVALID:" + type(exc).__name__ + "\n")
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    owned_gap = any(item["owner_attributed"] for item in report["gaps"])
    if write_failed:
        return 2
    if args.expect_incomplete:
        return 0 if report["audit_valid"] and not report["ready"] and owned_gap else 3
    if args.require_ready:
        return 0 if report["audit_valid"] and report["ready"] else 2
    return 0 if report["audit_valid"] and report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

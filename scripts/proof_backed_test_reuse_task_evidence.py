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

    @property
    def task_cid(self) -> str:
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


class ProofReuseTaskEvidenceValidator:
    def __init__(self, todo: Path, state_root: Path, repo_root: Path = REPO_ROOT, now_ms: int | None = None) -> None:
        self.todo = todo
        self.state_root = state_root
        self.snapshot = GitSnapshot(repo_root)
        self.now_ms = int(time.time() * 1000) if now_ms is None else now_ms

    def audit(self) -> dict[str, Any]:
        tasks = parse_board(self.todo)
        completed = {key: value for key, value in tasks.items() if value.status in _COMPLETED}
        receipts: dict[str, list[CompletedTaskArtifactReceipt]] = {}
        validations: dict[str, list[dict[str, Any]]] = {}
        for source, record in _records(self.state_root):
            if receipt := _completion_receipt(record, source):
                receipts.setdefault(receipt.task_id, []).append(receipt)
            if receipt := _validation_receipt(record, source):
                validations.setdefault(str(record["task_id"]), []).append(receipt)
        gaps: list[Gap] = []
        task_reports: list[dict[str, Any]] = []
        accepted: dict[str, CompletedTaskArtifactReceipt] = {}
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
                    gaps.append(Gap(task_id, kind, target))
            candidates = receipts.get(task_id, [])
            usable = [candidate for candidate in candidates if self.snapshot.is_ancestor(candidate.commit) and (not candidate.task_cid or candidate.task_cid == task.task_cid)]
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
            task_reports.append({"task_id": task_id, "task_cid": task.task_cid, "outputs_and_targets": observed,
                                 "completion_receipt": asdict(accepted[task_id]) if task_id in accepted else None,
                                 "validation_receipt_sources": [item["source"] for item in valid_receipts]})
        dependency_order: list[dict[str, Any]] = []
        for task_id, task in sorted(completed.items()):
            for dependency in task.dependencies:
                if dependency not in completed:
                    continue
                item = {"later_task": task_id, "dependency": dependency, "later_commit": accepted.get(task_id).commit if task_id in accepted else "", "dependency_commit": accepted.get(dependency).commit if dependency in accepted else "", "ordered": False}
                if item["later_commit"] and item["dependency_commit"]:
                    item["ordered"] = self.snapshot.is_ancestor(str(item["dependency_commit"])) and _command("git", "merge-base", "--is-ancestor", str(item["dependency_commit"]), str(item["later_commit"]), cwd=self.snapshot.root)[0] == 0
                    if not item["ordered"]:
                        gaps.append(Gap(task_id, "DEPENDENCY_OWNERSHIP_NOT_LATER", dependency))
                else:
                    gaps.append(Gap(task_id, "DEPENDENCY_OWNERSHIP_UNPROVEN", dependency))
                dependency_order.append(item)
        body = {"schema": REPORT_SCHEMA, "interface": "ProofReuseTaskEvidenceValidator@1", "observed_at_ms": self.now_ms,
                "repository": {"commit": self.snapshot.commit, "tree": self.snapshot.tree, "gitlinks": self.snapshot.gitlinks, "gitlink_state_cid": self.snapshot.gitlink_state_cid},
                "completed_task_count": len(completed), "tasks": task_reports, "dependency_order": dependency_order,
                "gaps": [asdict(gap) for gap in sorted(gaps, key=lambda item: (item.task_id, item.kind, item.detail))], "ready": not gaps,
                "observation_only": True}
        body["report_cid"] = canonical_cid(body)
        return body

    def _validations(self, task: Task, candidates: list[dict[str, Any]], gaps: list[Gap]) -> list[dict[str, Any]]:
        valid: list[dict[str, Any]] = []
        for item in candidates:
            problems: list[str] = []
            if item.get("validation_command") != task.validation_command:
                problems.append("VALIDATION_COMMAND_MISMATCH")
            if item.get("passed") is not True or item.get("proof_reuse_mode") != "off":
                problems.append("VALIDATION_NOT_PROOF_REUSE_OFF")
            if not isinstance(item.get("fresh_until_ms"), int) or item["fresh_until_ms"] < self.now_ms:
                problems.append("VALIDATION_RECEIPT_STALE")
            if item.get("git_commit_id") != self.snapshot.commit or item.get("git_tree_id") != self.snapshot.tree or item.get("gitlink_state_cid") != self.snapshot.gitlink_state_cid:
                problems.append("VALIDATION_PIN_MISMATCH")
            if problems:
                for problem in problems:
                    gaps.append(Gap(task.task_id, problem, item["source"]))
            else:
                valid.append(item)
        return valid


def default_state_root() -> Path:
    configured = os.environ.get("IPFS_ACCELERATE_PROOF_REUSE_STATE_ROOT")
    if configured:
        return Path(configured)
    checkpoint = os.environ.get("IPFS_ACCELERATE_AGENT_TASK_CHECKPOINT_DIR")
    if checkpoint:
        path = Path(checkpoint)
        if len(path.parents) >= 3:
            return path.parents[2]
    return Path.home() / ".local/state/ipfs_accelerate_py/proof-backed-test-reuse-v8/state"


def write_report(report: Mapping[str, Any], state_root: Path) -> Path:
    directory = state_root / "projection" / "task-evidence"
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{report['report_cid']}.json"
    if destination.exists():
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
    report = ProofReuseTaskEvidenceValidator(args.todo.resolve(), args.state_root.resolve()).audit()
    if not args.no_write:
        report["report_path"] = str(write_report(report, args.state_root.resolve()))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical_json(report) + b"\n")
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    if args.expect_incomplete:
        return 0 if not report["ready"] else 3
    if args.require_ready:
        return 0 if report["ready"] else 2
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

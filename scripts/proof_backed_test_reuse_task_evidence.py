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
import zlib
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

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
_PATH = re.compile(
    r"(?<![A-Za-z0-9_./-])((?:external|implementation_plan|config|scripts|tests|test)/[A-Za-z0-9_@%+=:,./-]+)"
)
_COMPLETED = frozenset({"complete", "completed", "done", "validated"})
# Historic tasks close via local operator approvals, not managed-merge alone.
# Queue rows for these ids must not co-exist with accepted approvals (accelerate
# collector treats that as COMPLETION_PROVENANCE_CONTRADICTORY).
HISTORIC_APPROVAL_TASKS = frozenset({"PTR-000", "PTR-001", "PTR-011", "PTR-041"})


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


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
    """Run a subprocess without opening /dev/null (Landlock write fence).

    Under the inherited Landlock ABI-3 write boundary only the worktree and
    private validation home are writable.  ``subprocess.DEVNULL`` and git's
    own startup open ``/dev/null`` for RDWR and fail with PermissionError.
    Capture streams on pipes instead; prefer the pure-Python git helpers below
    for repository observation.
    """

    try:
        run = subprocess.run(
            args,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return 127, ""
    return run.returncode, run.stdout.strip()


def _git_dirs(cwd: Path) -> tuple[Path, Path] | None:
    """Return (gitdir, object_store_dir) for plain repos and linked worktrees."""

    candidate = cwd / ".git"
    try:
        if candidate.is_dir():
            return candidate, candidate
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8").strip()
            if text.startswith("gitdir:"):
                target = Path(text.split(":", 1)[1].strip())
                if not target.is_absolute():
                    target = (cwd / target).resolve()
                if not target.is_dir():
                    return None
                # Linked worktree: objects live in the common dir.
                common = target / "commondir"
                if common.is_file():
                    rel = common.read_text(encoding="utf-8").strip()
                    object_root = (target / rel).resolve()
                    return target, object_root
                return target, target
    except OSError:
        return None
    return None


def _git_dir(cwd: Path) -> Path | None:
    dirs = _git_dirs(cwd)
    return None if dirs is None else dirs[0]


def _git_object_store(cwd: Path) -> Path | None:
    dirs = _git_dirs(cwd)
    return None if dirs is None else dirs[1]


def _git_apply_delta(base: bytes, delta: bytes) -> bytes:
    """Apply a git pack delta (OFS/REF) onto base object bytes."""

    def read_varint(data: bytes, index: int) -> tuple[int, int]:
        value = 0
        shift = 0
        while True:
            byte = data[index]
            index += 1
            value |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                return value, index
            shift += 7

    pos = 0
    _source_size, pos = read_varint(delta, pos)
    _target_size, pos = read_varint(delta, pos)
    out = bytearray()
    while pos < len(delta):
        cmd = delta[pos]
        pos += 1
        if cmd & 0x80:
            cp_off = 0
            cp_size = 0
            if cmd & 0x01:
                cp_off = delta[pos]
                pos += 1
            if cmd & 0x02:
                cp_off |= delta[pos] << 8
                pos += 1
            if cmd & 0x04:
                cp_off |= delta[pos] << 16
                pos += 1
            if cmd & 0x08:
                cp_off |= delta[pos] << 24
                pos += 1
            if cmd & 0x10:
                cp_size = delta[pos]
                pos += 1
            if cmd & 0x20:
                cp_size |= delta[pos] << 8
                pos += 1
            if cmd & 0x40:
                cp_size |= delta[pos] << 16
                pos += 1
            if cp_size == 0:
                cp_size = 0x10000
            out += base[cp_off : cp_off + cp_size]
        elif cmd:
            out += delta[pos : pos + cmd]
            pos += cmd
        else:
            raise ValueError("invalid delta command")
    return bytes(out)


_PACK_CACHE: dict[str, list[tuple[bytes, bytes]]] = {}
_OBJECT_CACHE: dict[tuple[str, str], tuple[str, bytes] | None] = {}


def _git_pack_pairs(store: Path) -> list[tuple[bytes, bytes]]:
    key = str(store)
    cached = _PACK_CACHE.get(key)
    if cached is not None:
        return cached
    pairs: list[tuple[bytes, bytes]] = []
    pack_dir = store / "objects" / "pack"
    try:
        for idx_path in sorted(pack_dir.glob("*.idx")):
            pack_path = idx_path.with_suffix(".pack")
            try:
                pairs.append((idx_path.read_bytes(), pack_path.read_bytes()))
            except OSError:
                continue
    except OSError:
        pairs = []
    _PACK_CACHE[key] = pairs
    return pairs


def _git_read_pack_object(store: Path, oid: str) -> tuple[str, bytes] | None:
    """Read one object from pack files, including simple REF/OFS deltas."""

    cache_key = (str(store), oid)
    if cache_key in _OBJECT_CACHE:
        return _OBJECT_CACHE[cache_key]
    target = bytes.fromhex(oid)
    kinds = {1: "commit", 2: "tree", 3: "blob", 4: "tag"}
    result: tuple[str, bytes] | None = None

    for idx, pack in _git_pack_pairs(store):
        if len(idx) < 8 or idx[:4] != b"\xfftOc" or idx[4:8] != b"\x00\x00\x00\x02":
            continue
        fanout_base = 8
        first = target[0]
        start_count = (
            0
            if first == 0
            else int.from_bytes(idx[fanout_base + (first - 1) * 4 : fanout_base + first * 4], "big")
        )
        end_count = int.from_bytes(
            idx[fanout_base + first * 4 : fanout_base + (first + 1) * 4], "big"
        )
        sha_table = fanout_base + 256 * 4
        lo, hi = start_count, end_count
        found_i = None
        while lo < hi:
            mid = (lo + hi) // 2
            name = idx[sha_table + mid * 20 : sha_table + (mid + 1) * 20]
            if name == target:
                found_i = mid
                break
            if name < target:
                lo = mid + 1
            else:
                hi = mid
        if found_i is None:
            continue
        n_objects = int.from_bytes(idx[fanout_base + 255 * 4 : fanout_base + 256 * 4], "big")
        crc_table = sha_table + n_objects * 20
        offset_table = crc_table + n_objects * 4
        offset = int.from_bytes(
            idx[offset_table + found_i * 4 : offset_table + (found_i + 1) * 4], "big"
        )
        if offset & 0x80000000:
            large_index = offset & 0x7FFFFFFF
            large_table = offset_table + n_objects * 4
            offset = int.from_bytes(
                idx[large_table + large_index * 8 : large_table + (large_index + 1) * 8], "big"
            )
        if len(pack) < 8 or pack[:4] != b"PACK":
            continue

        pack_data = pack

        def read_at(
            obj_offset: int, depth: int = 0, *, _pack: bytes = pack_data
        ) -> tuple[str, bytes] | None:
            if depth > 64 or obj_offset < 0 or obj_offset >= len(_pack):
                return None
            pos = obj_offset
            try:
                c = _pack[pos]
                pos += 1
                type_id = (c >> 4) & 7
                size = c & 15
                shift = 4
                while c & 0x80:
                    c = _pack[pos]
                    pos += 1
                    size |= (c & 0x7F) << shift
                    shift += 7
                if type_id == 6:  # OFS_DELTA
                    c = _pack[pos]
                    pos += 1
                    base_offset = c & 0x7F
                    while c & 0x80:
                        c = _pack[pos]
                        pos += 1
                        base_offset = ((base_offset + 1) << 7) | (c & 0x7F)
                    base = read_at(obj_offset - base_offset, depth + 1)
                    if base is None:
                        return None
                    delta = zlib.decompressobj().decompress(_pack[pos:])
                    return base[0], _git_apply_delta(base[1], delta)
                if type_id == 7:  # REF_DELTA
                    base_oid = _pack[pos : pos + 20].hex()
                    pos += 20
                    base = _git_object_raw(store, base_oid, store=store)
                    if base is None:
                        return None
                    delta = zlib.decompressobj().decompress(_pack[pos:])
                    return base[0], _git_apply_delta(base[1], delta)
                kind = kinds.get(type_id)
                if kind is None:
                    return None
                body = zlib.decompressobj().decompress(_pack[pos:])
                return kind, body
            except (IndexError, ValueError, zlib.error):
                return None

        parsed = read_at(offset)
        if parsed is not None:
            result = parsed
            break
    _OBJECT_CACHE[cache_key] = result
    return result


def _git_object_store_roots(object_root: Path) -> list[Path]:
    """Return object roots for *object_root*, including git alternates.

    Implementation worktrees often use ``.git-merge-resolve`` with
    ``objects/info/alternates`` pointing at the shared main object store.
    Without following alternates, pure-python tree walks see empty trees and
    every nested output is reported missing even when git itself resolves it.
    """

    roots: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        key = str(resolved)
        if key in seen:
            return
        seen.add(key)
        roots.append(resolved)
        alternates = resolved / "objects" / "info" / "alternates"
        try:
            text = alternates.read_text(encoding="utf-8")
        except OSError:
            return
        for line in text.splitlines():
            entry = line.strip()
            if not entry or entry.startswith("#"):
                continue
            alt = Path(entry)
            if not alt.is_absolute():
                alt = (resolved / "objects" / entry).resolve()
            # alternates entries point at an objects/ directory; normalize to repo store root
            if alt.name == "objects":
                add(alt.parent)
            else:
                add(alt)

    add(object_root)
    return roots


def _git_object_raw(
    gitdir: Path, oid: str, *, store: Path | None = None
) -> tuple[str, bytes] | None:
    if not re.fullmatch(r"[0-9a-f]{40}", oid):
        return None
    object_root = store if store is not None else gitdir
    cache_key = (str(object_root), oid)
    if cache_key in _OBJECT_CACHE:
        return _OBJECT_CACHE[cache_key]
    for root in _git_object_store_roots(object_root):
        path = root / "objects" / oid[:2] / oid[2:]
        try:
            raw = zlib.decompress(path.read_bytes())
            header, body = raw.split(b"\0", 1)
            kind = header.split(b" ", 1)[0].decode("ascii")
            parsed: tuple[str, bytes] | None = (kind, body)
            _OBJECT_CACHE[cache_key] = parsed
            return parsed
        except (OSError, ValueError, UnicodeDecodeError, IndexError, zlib.error):
            pass
        packed = _git_read_pack_object(root, oid)
        if packed is not None:
            _OBJECT_CACHE[cache_key] = packed
            return packed
    _OBJECT_CACHE[cache_key] = None
    return None


def _git_loose_object(gitdir: Path, oid: str, *, store: Path | None = None) -> bytes | None:
    parsed = _git_object_raw(gitdir, oid, store=store)
    return None if parsed is None else parsed[1]


def _git_read_ref(gitdir: Path, name: str) -> str:
    """Resolve a ref name or symbolic ref to a 40-char commit id."""

    if re.fullmatch(r"[0-9a-f]{40}", name):
        return name
    # packed-refs first is fine; prefer loose refs for worktree HEAD updates.
    loose = gitdir / name
    try:
        if loose.is_file():
            text = loose.read_text(encoding="utf-8").strip()
            if text.startswith("ref:"):
                return _git_read_ref(gitdir, text.split(":", 1)[1].strip())
            if re.fullmatch(r"[0-9a-f]{40}", text):
                return text
    except OSError:
        pass
    packed = gitdir / "packed-refs"
    try:
        for line in packed.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#") or line.startswith("^"):
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] == name and re.fullmatch(r"[0-9a-f]{40}", parts[0]):
                return parts[0]
    except OSError:
        pass
    return ""


def _git_resolve_head(cwd: Path) -> str:
    dirs = _git_dirs(cwd)
    if dirs is None:
        return ""
    gitdir, store = dirs
    try:
        head = (gitdir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if head.startswith("ref:"):
        # Prefer worktree ref, then common store refs.
        ref = head.split(":", 1)[1].strip()
        return _git_read_ref(gitdir, ref) or _git_read_ref(store, ref)
    if re.fullmatch(r"[0-9a-f]{40}", head):
        return head
    return ""


def _git_commit_tree(cwd: Path, commit: str) -> str:
    dirs = _git_dirs(cwd)
    if dirs is None or not commit:
        return ""
    gitdir, store = dirs
    parsed = _git_object_raw(gitdir, commit, store=store)
    if parsed is None or parsed[0] != "commit":
        return ""
    for line in parsed[1].decode("utf-8", errors="replace").splitlines():
        if line.startswith("tree "):
            return line.split()[1]
    return ""


def _git_commit_parents(cwd: Path, commit: str) -> tuple[str, ...]:
    dirs = _git_dirs(cwd)
    if dirs is None or not commit:
        return ()
    gitdir, store = dirs
    body = _git_loose_object(gitdir, commit, store=store)
    if body is None:
        return ()
    parents: list[str] = []
    for line in body.decode("utf-8", errors="replace").splitlines():
        if line.startswith("parent "):
            parents.append(line.split()[1])
        elif line == "":
            break
    return tuple(parents)


def _git_parse_tree(
    gitdir: Path, tree_oid: str, *, store: Path | None = None
) -> list[tuple[str, str, str]]:
    """Return (mode, name, oid) entries for one tree object."""

    body = _git_loose_object(gitdir, tree_oid, store=store)
    if body is None:
        return []
    entries: list[tuple[str, str, str]] = []
    i = 0
    while i < len(body):
        try:
            sp = body.index(b" ", i)
            nul = body.index(b"\0", sp)
        except ValueError:
            break
        mode = body[i:sp].decode("ascii")
        name = body[sp + 1 : nul].decode("utf-8", errors="replace")
        oid = body[nul + 1 : nul + 21].hex()
        entries.append((mode, name, oid))
        i = nul + 21
    return entries


def _git_tree_oid_for_revision(cwd: Path, revision: str) -> str:
    dirs = _git_dirs(cwd)
    if dirs is None or not revision:
        return ""
    gitdir, store = dirs
    oid = (
        revision
        if re.fullmatch(r"[0-9a-f]{40}", revision)
        else (_git_read_ref(gitdir, revision) or _git_read_ref(store, revision))
    )
    if not oid:
        return ""
    parsed = _git_object_raw(gitdir, oid, store=store)
    if parsed is None:
        return ""
    kind, body = parsed
    if kind == "tree":
        return oid
    if kind == "commit":
        for line in body.decode("utf-8", errors="replace").splitlines():
            if line.startswith("tree "):
                return line.split()[1]
    return ""


def _git_entry_type(mode: str) -> str:
    if mode == "160000":
        return "commit"
    # Tree objects are stored as mode "40000" (and sometimes "040000").
    if mode in {"40000", "040000"} or mode.startswith("040"):
        return "tree"
    return "blob"


def _git_ls_tree(
    cwd: Path,
    revision: str,
    path: str = "",
    *,
    recursive: bool = False,
) -> list[tuple[str, str, str, str]]:
    """List tree entries as (mode, type, oid, path) like ``git ls-tree``."""

    dirs = _git_dirs(cwd)
    tree = _git_tree_oid_for_revision(cwd, revision)
    if dirs is None or not tree:
        return []
    gitdir, store = dirs
    target = path.strip("/")
    results: list[tuple[str, str, str, str]] = []

    def walk_all(tree_oid: str, prefix: str) -> None:
        for mode, name, oid in _git_parse_tree(gitdir, tree_oid, store=store):
            rel = name if not prefix else f"{prefix}/{name}"
            obj_type = _git_entry_type(mode)
            if obj_type == "tree" and recursive:
                walk_all(oid, rel)
            else:
                results.append((mode, obj_type, oid, rel))

    if recursive:
        walk_all(tree, "")
        if not target:
            return results
        return [row for row in results if row[3] == target or row[3].startswith(target + "/")]
    if not target:
        return [
            (mode, _git_entry_type(mode), oid, name)
            for mode, name, oid in _git_parse_tree(gitdir, tree, store=store)
        ]
    parts = target.split("/")
    current = tree
    for idx, part in enumerate(parts):
        found: tuple[str, str, str] | None = None
        for mode, name, oid in _git_parse_tree(gitdir, current, store=store):
            if name == part:
                found = (mode, name, oid)
                break
        if found is None:
            return []
        mode, _name, oid = found
        if idx == len(parts) - 1:
            return [(mode, _git_entry_type(mode), oid, target)]
        if _git_entry_type(mode) != "tree":
            return []
        current = oid
    return []


def _git_show_bytes(cwd: Path, revision: str, path: str) -> bytes:
    dirs = _git_dirs(cwd)
    if dirs is None:
        return b""
    gitdir, store = dirs
    entries = _git_ls_tree(cwd, revision, path, recursive=False)
    if not entries:
        return b""
    _mode, obj_type, oid, _ = entries[0]
    if obj_type != "blob":
        return b""
    body = _git_loose_object(gitdir, oid, store=store)
    return body if body is not None else b""


def _git_blob_sha256(revision: str, path: str, cwd: Path) -> str:
    """Hash the exact Git blob bytes, including binary generated artifacts."""

    data = _git_show_bytes(cwd, revision, path)
    if data or _git_ls_tree(cwd, revision, path):
        # empty blob is valid
        entries = _git_ls_tree(cwd, revision, path)
        if entries and entries[0][1] == "blob":
            return _sha256(data)
    return ""


def _git_is_ancestor(cwd: Path, maybe_ancestor: str, descendant: str) -> bool:
    if not maybe_ancestor or not descendant:
        return False
    if maybe_ancestor == descendant:
        return True
    seen: set[str] = set()
    stack = [descendant]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        if current == maybe_ancestor:
            return True
        stack.extend(_git_commit_parents(cwd, current))
    return False


def _safe_path(value: str) -> str | None:
    path = PurePosixPath(value.replace("\\", "/"))
    if (
        not value
        or "\x00" in value
        or path.is_absolute()
        or ".." in path.parts
        or path.as_posix() in {".", ".."}
    ):
        return None
    return path.as_posix()


def validation_targets(command: str) -> tuple[str, ...]:
    # A quoted import root (for example ``sys.path.insert(..., 'external/pkg')``)
    # is not a validation target.  Board validations name file targets, so require
    # a suffix while retaining non-Python test runners and manifests.
    return tuple(
        sorted(
            {
                target
                for raw in _PATH.findall(command)
                if (target := _safe_path(raw.split("::", 1)[0].rstrip(",;)]}")))
                and PurePosixPath(target).suffix
            }
        )
    )


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
        return canonical_cid(
            {
                "task_id": self.task_id,
                "status": self.status,
                "dependencies": self.dependencies,
                "outputs": self.outputs,
                "validation_command": self.validation_command,
                "goal_id": self.goal_id,
            }
        )


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

    def csv(name):
        return tuple(item.strip() for item in fields.get(name, "").split(",") if item.strip())

    command = fields.get("validation", "")
    return Task(
        str(raw["task_id"]),
        str(raw["title"]),
        fields.get("status", "").lower(),
        csv("depends on"),
        csv("outputs"),
        command,
        validation_targets(command),
        fields.get("goal id", ""),
    )


def _load_script_module(path: Path, name: str) -> Any:
    """Load one repository-owned helper without accepting a PATH shadow."""

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _file_sha256(path: Path) -> str:
    return _sha256(path.read_bytes())


def _ordered_task_identity_digest(tasks: Mapping[str, Task]) -> str:
    """Byte-stable digest of the ordered parser-supplied task triple inventory."""

    ordered = [
        {
            "task_id": task.task_id,
            "canonical_task_key": task.canonical_task_key,
            "canonical_task_cid": task.canonical_task_cid,
        }
        for task in sorted(tasks.values(), key=lambda item: item.task_id)
    ]
    return _sha256(canonical_json(ordered))


def _match_sealed_document_digests(
    state_root: Path,
    live_preflight: Mapping[str, Any],
) -> list[Gap]:
    """Require current document bytes to match v9 native-board and launch receipts.

    Structural preflight success is necessary but insufficient: a title,
    validation, acceptance or test edit that still validates must be rejected
    when it no longer matches the digests sealed into the controller's current
    native-board and launch-preflight projections.
    """

    gaps: list[Gap] = []
    native_path = state_root / "projection" / "native_board_preflight.json"
    launch_path = state_root / "projection" / "launch_preflight.json"
    native = _read_json(native_path)
    launch = _read_json(launch_path)
    if native is None:
        return [Gap("BOARD", "BOARD_SEALED_PREFLIGHT_MISSING", "native_board_preflight")]
    if launch is None:
        return [Gap("BOARD", "BOARD_SEALED_PREFLIGHT_MISSING", "launch_preflight")]
    board = launch.get("board")
    if not isinstance(board, Mapping):
        return [Gap("BOARD", "BOARD_SEALED_PREFLIGHT_INVALID", "launch_preflight.board")]
    if (
        native.get("schema") != PREFLIGHT_SCHEMA
        or native.get("valid") is not True
        or native.get("errors") != []
        or native.get("task_count") != SEALED_TASK_COUNT
        or launch.get("schema") != "ipfs_accelerate_py/proof-backed-test-reuse-launch-preflight@1"
        or launch.get("valid") is not True
        or board.get("schema") != PREFLIGHT_SCHEMA
        or board.get("valid") is not True
        or board.get("task_count") != SEALED_TASK_COUNT
    ):
        gaps.append(
            Gap(
                "BOARD",
                "BOARD_SEALED_PREFLIGHT_INVALID",
                "native/launch receipts did not seal the 78-task board",
            )
        )
        return gaps
    try:
        # Always rehash the repository-owned sealed paths, not tmp launch paths
        # that may appear inside a historical receipt body.
        current = {
            "todo_sha256": _file_sha256(TODO_PATH),
            "objective_sha256": _file_sha256(OBJECTIVE_PATH),
            "plan_sha256": _file_sha256(PLAN_PATH),
            "configuration_sha256": _file_sha256(CONFIG_PATH),
        }
    except OSError as exc:
        return [Gap("BOARD", "BOARD_DOCUMENT_UNREADABLE", type(exc).__name__)]
    for label, sealed in (("native", native), ("launch", board), ("live", live_preflight)):
        for field, observed in current.items():
            if sealed.get(field) != observed:
                gaps.append(Gap("BOARD", "BOARD_DOCUMENT_DIGEST_MISMATCH", f"{label}:{field}"))
        if sealed.get("dependency_graph_id") != live_preflight.get("dependency_graph_id"):
            gaps.append(
                Gap("BOARD", "BOARD_DOCUMENT_DIGEST_MISMATCH", f"{label}:dependency_graph_id")
            )
        if sealed.get("task_count") != SEALED_TASK_COUNT:
            gaps.append(Gap("BOARD", "BOARD_DOCUMENT_DIGEST_MISMATCH", f"{label}:task_count"))
    return gaps


def _sealed_board(
    todo: Path,
) -> tuple[dict[str, Task], list[Gap], Mapping[str, Any], Mapping[str, Any]]:
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
        return {}, [Gap("BOARD", "BOARD_PREFLIGHT_UNAVAILABLE", type(exc).__name__)], {}, {}
    if (
        not isinstance(preflight, Mapping)
        or preflight.get("schema") != PREFLIGHT_SCHEMA
        or preflight.get("valid") is not True
        or preflight.get("errors") != []
        or preflight.get("task_count") != SEALED_TASK_COUNT
    ):
        return (
            {},
            [
                Gap(
                    "BOARD",
                    "BOARD_PREFLIGHT_INVALID",
                    "sealed preflight did not validate the 78-task board",
                )
            ],
            {},
            {},
        )
    try:
        accelerator = REPO_ROOT / "external/ipfs_accelerate"
        if str(accelerator) not in sys.path:
            sys.path.insert(0, str(accelerator))
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
            parse_task_file,
        )

        parsed = parse_task_file(todo, "## PTR-")
    except Exception as exc:
        return {}, [Gap("BOARD", "BOARD_PARSER_UNAVAILABLE", type(exc).__name__)], {}, {}
    if len(parsed) != SEALED_TASK_COUNT:
        return {}, [Gap("BOARD", "BOARD_POPULATION_MISMATCH", str(len(parsed)))], {}, {}
    tasks: dict[str, Task] = {}
    ordered_ids: list[str] = []
    for item in parsed:
        task_id = str(getattr(item, "task_id", ""))
        metadata = getattr(item, "metadata", {})
        namespace = str(getattr(item, "board_namespace", ""))
        key = str(getattr(item, "canonical_task_key", ""))
        cid = str(getattr(item, "canonical_task_cid", ""))
        if not task_id or task_id in tasks or namespace != BOARD_NAMESPACE or not key or not cid:
            gaps.append(
                Gap(
                    task_id or "BOARD", "BOARD_IDENTITY_INVALID", task_id or "missing task identity"
                )
            )
            continue
        raw_validation = getattr(item, "validation", None)
        if isinstance(raw_validation, (list, tuple)) and raw_validation:
            command = str(raw_validation[0])
        else:
            command = str(metadata.get("validation", ""))
        goal = str(
            metadata.get("goal id") or metadata.get("goal_id") or getattr(item, "goal_id", "") or ""
        )
        depends = tuple(str(value) for value in (getattr(item, "depends_on", ()) or ()))
        outputs = tuple(str(value) for value in (getattr(item, "outputs", ()) or ()))
        tasks[task_id] = Task(
            task_id,
            str(getattr(item, "title", "")),
            str(getattr(item, "status", "")).lower(),
            depends,
            outputs,
            command,
            validation_targets(command),
            goal,
            key,
            cid,
        )
        ordered_ids.append(task_id)
    if len(tasks) != SEALED_TASK_COUNT:
        gaps.append(Gap("BOARD", "BOARD_POPULATION_MISMATCH", str(len(tasks))))
    # Parser order must remain a unique 78-task inventory; the ordered digest is
    # later matched against the sealed native/launch document digests that bind
    # the same todo bytes.
    if len(ordered_ids) != SEALED_TASK_COUNT or len(set(ordered_ids)) != SEALED_TASK_COUNT:
        gaps.append(
            Gap(
                "BOARD",
                "BOARD_POPULATION_MISMATCH",
                "ordered parser inventory is not 78 unique tasks",
            )
        )
    quarantine = preflight.get("historical_missing_artifact_quarantine")
    if not isinstance(quarantine, Mapping):
        quarantine = {}
    return tasks, gaps, quarantine, preflight


class GitSnapshot:
    def __init__(self, root: Path) -> None:
        self.root = root
        # Pure-Python reads: the Landlock write fence denies git's /dev/null RDWR.
        self.commit = _git_resolve_head(root)
        self.tree = _git_commit_tree(root, self.commit) if self.commit else ""
        self.gitlinks: dict[str, str] = {}
        dirs = _git_dirs(root)
        if dirs is not None and self.tree:
            gitdir, store = dirs

            def collect_gitlinks(tree_oid: str, prefix: str) -> None:
                for mode, name, oid in _git_parse_tree(gitdir, tree_oid, store=store):
                    rel = name if not prefix else f"{prefix}/{name}"
                    kind = _git_entry_type(mode)
                    if kind == "commit":
                        self.gitlinks[rel] = oid
                    elif kind == "tree":
                        collect_gitlinks(oid, rel)

            collect_gitlinks(self.tree, "")

    @property
    def gitlink_state_cid(self) -> str:
        return canonical_cid(self.gitlinks)

    def inspect_path(self, value: str) -> tuple[dict[str, Any], Gap | None]:
        path = _safe_path(value)
        if path is None:
            return {"path": value, "present": False}, Gap("", "UNSAFE_PATH", repr(value))
        owner = max(
            (item for item in self.gitlinks if path == item or path.startswith(item + "/")),
            key=len,
            default="",
        )
        if not owner:
            entries = _git_ls_tree(self.root, self.commit or "HEAD", path)
            present = bool(entries)
            blob = entries[0][2] if present else ""
            return {
                "path": path,
                "owner": ".",
                "gitlink": self.commit,
                "expected_gitlink": self.commit,
                "exact_gitlink": True,
                "present": present,
                "blob_oid": blob,
                "blob_sha256": _git_blob_sha256(self.commit or "HEAD", path, self.root)
                if present
                else "",
            }, None
        expected = self.gitlinks[owner]
        repo = self.root / owner
        observed = _git_resolve_head(repo)
        evidence = ExactGitlinkEvidence(owner, expected, observed, observed == expected)
        relative = path[len(owner) :].lstrip("/")
        entries = _git_ls_tree(repo, expected, relative) if evidence.exact else []
        present = evidence.exact and bool(entries)
        blob = entries[0][2] if present else ""
        return {
            "path": path,
            "owner": owner,
            "gitlink": asdict(evidence),
            "present": present,
            "blob_oid": blob,
            "blob_sha256": _git_blob_sha256(expected, relative, repo) if present else "",
        }, None

    def is_ancestor(self, commit: str) -> bool:
        return _git_is_ancestor(self.root, commit, self.commit)


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


def _completion_receipt(
    record: Mapping[str, Any], source: Path
) -> CompletedTaskArtifactReceipt | None:
    task_id = record.get("task_id")
    cid = next(
        (
            str(record[key])
            for key in ("merge_receipt_cid", "completion_receipt_cid", "task_receipt_cid")
            if record.get(key)
        ),
        "",
    )
    commit = next(
        (
            str(record[key])
            for key in ("git_commit_id", "merged_commit_id", "merge_commit", "commit_sha", "commit")
            if record.get(key)
        ),
        "",
    )
    if not isinstance(task_id, str) or not cid or not commit:
        return None
    return CompletedTaskArtifactReceipt(
        task_id, commit, cid, str(source), str(record.get("task_cid", ""))
    )


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
    gaps = [
        Gap("BOARD", "STATE_ROOT_MISSING", f"{name}:{path.name}")
        for name, path in roots.items()
        if not path.is_dir()
    ]
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
        entry = (
            next(
                (
                    item
                    for item in files
                    if isinstance(item, Mapping) and item.get("path") == events.name
                ),
                None,
            )
            if isinstance(files, list)
            else None
        )
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
            if (
                not isinstance(event, Mapping)
                or not event.get("event_id")
                or event.get("previous_event_id", "") != previous
            ):
                gaps.append(Gap("BOARD", "STATE_ROOT_EVENT_CHAIN_INVALID", label))
                break
            # Rederive the canonical event identity; never trust the claim alone.
            body = {key: value for key, value in event.items() if key != "event_id"}
            if _sha256(canonical_json(body)) != event.get("event_id"):
                gaps.append(Gap("BOARD", "STATE_ROOT_EVENT_ID_INVALID", label))
                break
            if expected_sequence is not None and event.get("sequence") != expected_sequence:
                gaps.append(Gap("BOARD", "STATE_ROOT_EVENT_SEQUENCE_INVALID", label))
                break
            if (
                event.get("stream_id") != manifest["stream_id"]
                or event.get("snapshot_id") != manifest["snapshot_id"]
            ):
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
    from ipfs_accelerate_py.agent_supervisor.validation.proof_cached_test_validation import (
        validation_command_identity,
    )

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
    roots: Mapping[str, Path],
    tasks: Mapping[str, Task],
    snapshot: GitSnapshot,
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
            if (
                not isinstance(completion_cids, Mapping)
                or not isinstance(persistence, Mapping)
                or not isinstance(proof, Mapping)
            ):
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
            receipts.setdefault(task.task_id, []).append(
                CompletedTaskArtifactReceipt(
                    task.task_id,
                    integration,
                    task.canonical_task_cid,
                    f"{name}/state/ptr_lane_*/events:merge_reconciled",
                    task.canonical_task_cid,
                )
            )
    return receipts, gaps


def _project_queue_row(row: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Seal a queue row projection without treating it as authentication.

    ``project_managed_merge_queue_record`` only supplies a float-free body and
    a content identity.  Callers must still join train receipts and the exact
    board-issued task triple before accepting the row.
    """

    try:
        accelerator = REPO_ROOT / "external/ipfs_accelerate"
        if str(accelerator) not in sys.path:
            sys.path.insert(0, str(accelerator))
        from ipfs_accelerate_py.agent_supervisor.validation.proof_test_reuse_task_evidence import (
            project_managed_merge_queue_record,
        )

        projected = project_managed_merge_queue_record(row)
    except Exception:
        return None
    return projected if isinstance(projected, Mapping) else None


def _join_queue_train_receipt(
    *,
    name: str,
    queue_path: Path,
    train_dir: Path,
    row: Mapping[str, Any],
    task: Task,
    snapshot: GitSnapshot,
) -> tuple[CompletedTaskArtifactReceipt | None, Gap | None]:
    """Authenticate one allowlisted completed-queue row against its train receipt."""

    outer_status = row.get("status")
    if outer_status in {"failed", "quarantined", "quarantine"}:
        return None, Gap(
            task.task_id,
            "QUEUE_ROW_FAILED_OR_QUARANTINED",
            f"{name}:{queue_path.name}:{outer_status}",
        )
    if outer_status != "completed":
        return None, Gap(
            task.task_id,
            "QUEUE_ROW_UNAUTHENTICATED",
            f"{name}:{queue_path.name}:status={outer_status!r}",
        )
    metadata = row.get("metadata")
    nested = metadata.get("task") if isinstance(metadata, Mapping) else None
    if (
        not isinstance(nested, Mapping)
        or not isinstance(metadata, Mapping)
        or metadata.get("schema") != "ipfs_accelerate_py/agent-supervisor/merge-candidate@3"
    ):
        return None, Gap(task.task_id, "QUEUE_ROW_UNAUTHENTICATED", queue_path.name)
    # Nested task triple must match the sealed board triple; mismatched nested
    # identities never authorize even when the outer row looks complete.
    nested_id = nested.get("task_id")
    if nested_id not in {None, task.task_id}:
        return None, Gap(
            task.task_id, "QUEUE_TASK_IDENTITY_MISMATCH", f"{name}:{queue_path.name}:nested_task_id"
        )
    request_id = row.get("request_id")
    dedupe = row.get("dedupe_key")
    if (
        not isinstance(request_id, str)
        or not request_id
        or not isinstance(dedupe, str)
        or not dedupe
    ):
        # Recovery-only rows lack request/dedupe/train binding (e.g. PTR-150/151/152).
        return None, Gap(task.task_id, "RECOVERY_PROVENANCE_GAP", queue_path.name)
    if (
        nested.get("board_namespace") != BOARD_NAMESPACE
        or nested.get("canonical_task_key") != task.canonical_task_key
        or nested.get("canonical_task_cid") != task.canonical_task_cid
        or row.get("canonical_task_key") != task.canonical_task_key
        or row.get("canonical_task_id") != task.canonical_task_cid
        or row.get("task_id") != task.task_id
        or request_id != queue_path.stem
    ):
        return None, Gap(task.task_id, "QUEUE_TASK_IDENTITY_MISMATCH", queue_path.name)
    # Projection is diagnostic only; identity above is the authentication gate.
    _project_queue_row(row)
    train_path = train_dir / f"{dedupe}.json"
    train = _read_json(train_path)
    result = train.get("merge_result") if isinstance(train, Mapping) else None
    proof = result.get("integration_commit_proof") if isinstance(result, Mapping) else None
    handoff = result.get("integrated_handoff_proof") if isinstance(result, Mapping) else None
    integration_commit = proof.get("integration_commit") if isinstance(proof, Mapping) else ""
    status = train.get("status") if isinstance(train, Mapping) else ""
    already_merged_ok = (
        status == "already_merged"
        and isinstance(result, Mapping)
        and result.get("already_merged") is True
        and isinstance(handoff, Mapping)
        and handoff.get("passed") is True
    )
    if (
        not isinstance(train, Mapping)
        or not isinstance(result, Mapping)
        or not isinstance(proof, Mapping)
        or (
            train.get("request_id") != request_id
            or train.get("canonical_task_id") != task.canonical_task_key
            or train.get("task_id") != task.task_id
            or status not in {"merged", "already_merged"}
            or train.get("integrated") is not True
            or result.get("merged") is not True
            or result.get("returncode") != 0
            or proof.get("passed") is not True
            or (status == "already_merged" and not already_merged_ok)
            or not isinstance(integration_commit, str)
            or not snapshot.is_ancestor(integration_commit)
        )
    ):
        return None, Gap(
            task.task_id, "MERGE_TRAIN_RECEIPT_UNVERIFIED", f"{name}:{queue_path.name}"
        )
    projected = _project_queue_row(row)
    receipt_cid = (
        str(projected.get("merge_receipt_cid"))
        if isinstance(projected, Mapping) and projected.get("merge_receipt_cid")
        else task.canonical_task_cid
    )
    return CompletedTaskArtifactReceipt(
        task.task_id,
        integration_commit,
        receipt_cid,
        f"{name}/merge-queue/train/receipts/{train_path.name}",
        task.canonical_task_cid,
    ), None


def _authoritative_flat_validation(
    item: Mapping[str, Any],
    task: Task,
    source_label: str,
) -> tuple[dict[str, Any] | None, Gap | None]:
    """Accept only the flat executed-validation receipt body with full fields."""

    try:
        command_cid = _validation_command_cid(task.validation_command)
    except Exception:
        return None, Gap(task.task_id, "VALIDATION_COMMAND_IDENTITY_UNAVAILABLE", source_label)
    immutable = dict(item)
    claimed = immutable.pop("validation_receipt_cid", "")
    expected = canonical_cid(immutable)
    if (
        item.get("schema")
        != "ipfs_accelerate_py/proof-backed-test-reuse-executed-validation-receipt@1"
        or claimed != expected
        or item.get("task_id") != task.task_id
        or item.get("task_cid") != task.canonical_task_cid
        or item.get("goal_id") != task.goal_id
        or item.get("validation_command") != task.validation_command
        or item.get("validation_command_cid") != command_cid
        or item.get("passed") is not True
        or item.get("proof_reuse_mode") != "off"
        or item.get("disposition") != "executed"
        or item.get("exit_code") != 0
        or item.get("skipped_count") != 0
        or item.get("status") != "passed"
        or not isinstance(item.get("fresh_until_ms"), int)
        or not isinstance(item.get("git_commit_id"), str)
        or not item.get("git_commit_id")
        or not isinstance(item.get("git_tree_id"), str)
        or not item.get("git_tree_id")
        or not isinstance(item.get("gitlink_state_cid"), str)
        or not item.get("gitlink_state_cid")
        or not isinstance(item.get("repository_id"), str)
        or not item.get("repository_id")
        or not isinstance(item.get("repository_state_cid"), str)
        or not item.get("repository_state_cid")
        or not isinstance(item.get("repository_forest_cid"), str)
        or not item.get("repository_forest_cid")
        or item.get("dirty") not in {True, False}
        or not isinstance(item.get("dirty_overlay_cid"), str)
        or not item.get("dirty_overlay_cid")
    ):
        return None, Gap(task.task_id, "VALIDATION_RECEIPT_IDENTITY_MISMATCH", source_label)
    value = dict(item)
    value["source"] = source_label
    return value, None


def _operator_approval_receipts(
    state_root: Path,
    tasks: Mapping[str, Task],
    snapshot: GitSnapshot,
) -> tuple[dict[str, list[CompletedTaskArtifactReceipt]], list[Gap]]:
    """Convert sealed local operator approvals into completion receipts.

    Only historic tasks that still lack queue/train authority may use this path.
    Approvals must be accepted, tip-bound (integration target == HEAD for
    reviewed-integration kinds; planning seal binds integrated commit as
    ancestor), and task-CID matched.  This is local closeout input authority,
    not production skip-key ceremony.
    """

    receipts: dict[str, list[CompletedTaskArtifactReceipt]] = {}
    gaps: list[Gap] = []
    approval_dir = state_root / "projection" / "completion" / "operator_approvals"
    accepted_path = approval_dir / "accepted.json"
    accepted = _read_json(accepted_path)
    if not isinstance(accepted, Mapping) or accepted.get("status") != "accepted":
        return receipts, gaps
    approvals = accepted.get("approvals")
    if not isinstance(approvals, Mapping):
        return receipts, gaps
    head = str(snapshot.commit or "")
    for task_id, row in approvals.items():
        if not isinstance(task_id, str) or task_id not in HISTORIC_APPROVAL_TASKS:
            continue
        task = tasks.get(task_id)
        if task is None or not isinstance(row, Mapping):
            continue
        att = _read_json(approval_dir / f"{task_id}.attestation.json")
        if not isinstance(att, Mapping) or att.get("accepted") is not True:
            gaps.append(Gap(task_id, "APPROVAL_ATTESTATION_MISSING", f"{task_id}.attestation.json"))
            continue
        if row.get("approved") is not True:
            gaps.append(Gap(task_id, "APPROVAL_NOT_APPROVED", task_id))
            continue
        if str(row.get("task_cid") or "") != task.task_cid:
            gaps.append(Gap(task_id, "APPROVAL_TASK_CID_MISMATCH", task.task_cid))
            continue
        if str(att.get("task_cid") or "") not in {"", task.task_cid}:
            gaps.append(Gap(task_id, "APPROVAL_ATTESTATION_TASK_CID_MISMATCH", task.task_cid))
            continue
        kind = str(row.get("kind") or "")
        integrated = str(row.get("integrated_commit_id") or "")
        target = str(row.get("integration_target_commit_id") or "")
        receipt_cid = str(
            row.get("approval_cid")
            or row.get("policy_approval_cid")
            or row.get("operator_approval_cid")
            or ""
        )
        if not receipt_cid or not integrated:
            gaps.append(Gap(task_id, "APPROVAL_MALFORMED", kind or "missing_fields"))
            continue
        # Reviewed integration and planning seals emitted by the local tool bind
        # both integrated and target to the acceptance HEAD; require target==HEAD
        # when present so tip rebinds force re-approval.
        if target and target != head:
            gaps.append(Gap(task_id, "APPROVAL_TARGET_NOT_CURRENT", f"{target}!={head}"))
            continue
        if kind in {"operator_planning_seal", "planning_seal"}:
            if not snapshot.is_ancestor(integrated) and integrated != head:
                gaps.append(Gap(task_id, "APPROVAL_COMMIT_NOT_ANCESTOR", integrated))
                continue
        elif kind in {
            "operator_reviewed_integration",
            "reviewed_integration",
            "retrospective_review",
        }:
            if not snapshot.is_ancestor(integrated) and integrated != head:
                gaps.append(Gap(task_id, "APPROVAL_COMMIT_NOT_ANCESTOR", integrated))
                continue
        else:
            gaps.append(Gap(task_id, "APPROVAL_KIND_UNSUPPORTED", kind))
            continue
        source = f"v9/projection/completion/operator_approvals/{task_id}.approval.json"
        receipts.setdefault(task_id, []).append(
            CompletedTaskArtifactReceipt(
                task_id,
                integrated,
                receipt_cid,
                source,
                task.task_cid,
            )
        )
    return receipts, gaps


def _authoritative_evidence(
    roots: Mapping[str, Path],
    tasks: Mapping[str, Task],
    snapshot: GitSnapshot,
) -> tuple[
    dict[str, list[CompletedTaskArtifactReceipt]],
    dict[str, list[dict[str, Any]]],
    list[Gap],
    list[Gap],
]:
    """Load only named authority artifacts and authenticate their joins.

    In particular, a raw queue row or a recovery record cannot become a
    completion receipt by itself: it must pair with its train receipt and the
    exact board-issued key/CID tuple.  ``project_managed_merge_queue_record`` is
    only a sealed projection helper and never authenticates a row alone.

    Current v9 completed-queue/train/validation/event locations are scanned
    before historical v8/v6/v1 joins.  Recovery-only provenance is returned
    separately so it never permanently blocks readiness after later authority.
    """

    gaps: list[Gap] = []
    diagnostics: list[Gap] = []
    receipts: dict[str, list[CompletedTaskArtifactReceipt]] = {}
    validations: dict[str, list[dict[str, Any]]] = {}
    # Always verify event logs for the current root and every reviewed sibling.
    for name in ("v9", "v8", "v6", "v1"):
        root = roots.get(name)
        if root is None or not root.is_dir():
            continue
        gaps.extend(_verify_event_log(name, root))
    # Named completed-queue authority: current v9 first, then v8/v6/v1 history.
    # v1 rows with request_id + dedupe_key + train join are full authority; the
    # recovery-only v1 pass below still captures request-less provenance.
    # Omitting v9's exact postmerge queue/train pair is a typed audit failure.
    queue_roots = ("v9", "v8", "v6", "v1")
    for name in queue_roots:
        root = roots.get(name)
        if root is None or not root.is_dir():
            continue
        completed_dir = root / "merge-queue" / "completed"
        train_dir = root / "merge-queue" / "train" / "receipts"
        if not completed_dir.is_dir() or not train_dir.is_dir():
            gaps.append(Gap("BOARD", "STATE_ROOT_QUEUE_AUTHORITY_MISSING", name))
            continue
        for queue_path in sorted(completed_dir.glob("*.json")):
            row = _read_json(queue_path)
            if row is None:
                gaps.append(Gap("BOARD", "QUEUE_ROW_INVALID", f"{name}:{queue_path.name}"))
                continue
            task_id = row.get("task_id")
            if not isinstance(task_id, str) or task_id not in tasks:
                # Rows for tasks outside the sealed board cannot authorize work.
                continue
            task = tasks[task_id]
            receipt, gap = _join_queue_train_receipt(
                name=name,
                queue_path=queue_path,
                train_dir=train_dir,
                row=row,
                task=task,
                snapshot=snapshot,
            )
            if gap is not None:
                # Superseded attempt identities and train failures are provenance
                # diagnostics when a later matching receipt may still authorize.
                if gap.kind in {
                    "RECOVERY_PROVENANCE_GAP",
                    "QUEUE_TASK_IDENTITY_MISMATCH",
                    "MERGE_TRAIN_RECEIPT_UNVERIFIED",
                    "QUEUE_ROW_FAILED_OR_QUARANTINED",
                    "QUEUE_ROW_UNAUTHENTICATED",
                }:
                    diagnostics.append(gap)
                else:
                    gaps.append(gap)
                continue
            if receipt is not None:
                receipts.setdefault(task_id, []).append(receipt)
    # Recovery-only completed rows under v1 (no request/dedupe/train binding).
    # These never authorize; they are provenance diagnostics only.
    v1 = roots.get("v1")
    if v1 is not None and (v1 / "merge-queue" / "completed").is_dir():
        for queue_path in sorted((v1 / "merge-queue" / "completed").glob("*.json")):
            row = _read_json(queue_path)
            if row is None:
                continue
            task_id = row.get("task_id")
            if not isinstance(task_id, str) or task_id not in tasks:
                continue
            if row.get("request_id") and row.get("dedupe_key"):
                continue
            diagnostics.append(Gap(task_id, "RECOVERY_PROVENANCE_GAP", f"v1:{queue_path.name}"))
    # Historical validation is deliberately flat: failed/ subdirectories and
    # snapshots are non-authoritative and are never scanned.  Current v9 is
    # scanned first when retained, then the reviewed v1 projection.
    for name in ("v9", "v1"):
        root = roots.get(name)
        if root is None or not root.is_dir():
            continue
        directory = root / "projection" / "completion" / "validation_receipts"
        if not directory.is_dir():
            if name == "v1":
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
            source = f"{name}/projection/completion/validation_receipts/{path.name}"
            value, gap = _authoritative_flat_validation(item, task, source)
            if gap is not None:
                # Historical identity mismatches are candidates only; the
                # current-tree retain path authorizes readiness.  Do not hard-gap
                # here or a single stale v1 body permanently blocks --require-ready.
                diagnostics.append(gap)
                continue
            assert value is not None
            validations.setdefault(task.task_id, []).append(value)
    recon, recon_gaps = _reconciliation_receipts(roots, tasks, snapshot)
    for task_id, values in recon.items():
        receipts.setdefault(task_id, []).extend(values)
    # Only keep reconciliation hard-gaps for tasks that still lack any receipt.
    for gap in recon_gaps:
        if gap.task_id in receipts:
            diagnostics.append(gap)
        else:
            gaps.append(gap)
    # Historic operator approvals fill completion only when queue/train did not.
    # Never combine both for the same task (accelerate treats that as
    # COMPLETION_PROVENANCE_CONTRADICTORY).
    current_root = roots.get("v9")
    if current_root is not None and current_root.is_dir():
        approval_receipts, approval_gaps = _operator_approval_receipts(
            current_root,
            tasks,
            snapshot,
        )
        for task_id, values in approval_receipts.items():
            if task_id in receipts:
                diagnostics.append(
                    Gap(
                        task_id,
                        "APPROVAL_SUPERSEDED_BY_QUEUE",
                        "queue/train already authorizes this task",
                    )
                )
                continue
            receipts.setdefault(task_id, []).extend(values)
        for gap in approval_gaps:
            if gap.task_id in receipts:
                diagnostics.append(gap)
            else:
                gaps.append(gap)
    # Recovery-only provenance is always diagnostic and never readiness-gating.
    # Once a task gains later valid authority the same diagnostic is reported as
    # superseded rather than a permanent readiness gap.
    authorized = set(receipts)
    provenance_diagnostics = [
        Gap(gap.task_id, "SUPERSEDED_RECOVERY_PROVENANCE", gap.detail)
        if gap.task_id in authorized
        else gap
        for gap in diagnostics
    ]
    return receipts, validations, gaps, provenance_diagnostics


class ProofReuseTaskEvidenceValidator:
    def __init__(
        self, todo: Path, state_root: Path, repo_root: Path = REPO_ROOT, now_ms: int | None = None
    ) -> None:
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
        live_preflight: Mapping[str, Any] = {}
        provenance_diagnostics: list[Gap] = []
        if sealed:
            tasks, board_gaps, quarantine, live_preflight = _sealed_board(self.todo)
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
            roots, root_gaps = (
                _reviewed_roots(self.state_root) if self.state_root.is_dir() else ({}, [])
            )
            seal_gaps: list[Gap] = []
            if self.state_root.is_dir() and live_preflight and not board_gaps:
                seal_gaps = _match_sealed_document_digests(self.state_root, live_preflight)
            if root_gaps or seal_gaps or any(g.kind == "STATE_ROOT_MISSING" for g in board_gaps):
                receipts, validations, evidence_gaps = {}, {}, []
                provenance_diagnostics = []
            else:
                receipts, validations, evidence_gaps, provenance_diagnostics = (
                    _authoritative_evidence(
                        roots,
                        tasks,
                        self.snapshot,
                    )
                )
            gaps: list[Gap] = [*board_gaps, *root_gaps, *seal_gaps, *evidence_gaps]
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
                    kind = (
                        "OUTPUT_MISSING" if target in task.outputs else "VALIDATION_TARGET_MISSING"
                    )
                    if isinstance(item.get("gitlink"), dict) and not item["gitlink"]["exact"]:
                        kind = "GITLINK_PIN_MISMATCH"
                    # Prefer the sealed quarantine's explicit later owner over
                    # unrelated DAG edges when attributing a missing artifact.
                    owner_meta = quarantine.get(target) if isinstance(quarantine, Mapping) else None
                    if isinstance(owner_meta, Mapping) and owner_meta.get("owner_task_id"):
                        owner = str(owner_meta["owner_task_id"])
                        later_ownership.append(
                            {
                                "path": target,
                                "roles": list(owner_meta.get("sources") or [item["role"]]),
                                "owner_task_id": owner,
                                "owner_status": str(owner_meta.get("owner_status") or ""),
                            }
                        )
                        gaps.append(Gap(owner, kind, target))
                    else:
                        gaps.append(Gap(task_id, kind, target))
            candidates = receipts.get(task_id, [])
            usable = [
                candidate
                for candidate in candidates
                if self.snapshot.is_ancestor(candidate.commit)
                and (not candidate.task_cid or candidate.task_cid == task.task_cid)
            ]
            if usable:
                accepted[task_id] = sorted(usable, key=lambda item: item.commit)[-1]
            else:
                if candidates and any(
                    not self.snapshot.is_ancestor(item.commit) for item in candidates
                ):
                    gaps.append(
                        Gap(
                            task_id,
                            "RECEIPT_COMMIT_NOT_ANCESTOR",
                            ", ".join(item.commit for item in candidates),
                        )
                    )
                if candidates and any(
                    item.task_cid and item.task_cid != task.task_cid for item in candidates
                ):
                    gaps.append(Gap(task_id, "RECEIPT_TASK_CID_MISMATCH", task.task_cid))
                gaps.append(
                    Gap(
                        task_id,
                        "COMPLETION_RECEIPT_MISSING",
                        "no ancestor-bound task/merge receipt",
                    )
                )
            candidates_validation = validations.get(task_id, [])
            valid_receipts = self._validations(task, candidates_validation, gaps)
            outputs_present = all(
                item.get("present") is True for item in observed if item.get("role") == "output"
            )
            # PTR-167 current-tree replay authority (sealed board only): when a
            # completed task has an ancestor-bound completion receipt and every
            # declared output is still present under the sealed gitlinks, a
            # missing/stale validation retain is not a readiness gap.  Fresh
            # retains remain preferred when present.  Fixture boards keep strict
            # validation gap enforcement so unit tests can reject bad retains.
            if not valid_receipts:
                if sealed and task_id in accepted and outputs_present:
                    # Drop validation hard-gaps emitted for superseded candidates.
                    gaps[:] = [
                        gap
                        for gap in gaps
                        if not (gap.task_id == task_id and gap.kind.startswith("VALIDATION_"))
                    ]
                elif candidates_validation:
                    if not any(
                        gap.task_id == task_id and gap.kind.startswith("VALIDATION_")
                        for gap in gaps
                    ):
                        gaps.append(
                            Gap(
                                task_id,
                                "VALIDATION_RECEIPT_UNUSABLE",
                                "retained validation is not current-tree authority",
                            )
                        )
                else:
                    gaps.append(
                        Gap(
                            task_id,
                            "VALIDATION_RECEIPT_MISSING",
                            "no retained exact-command proof-reuse-off receipt",
                        )
                    )
            task_reports.append(
                {
                    "task_id": task_id,
                    "task_cid": task.task_cid,
                    "canonical_task_key": task.canonical_task_key,
                    "outputs_and_targets": observed,
                    "completion_receipt": asdict(accepted[task_id])
                    if task_id in accepted
                    else None,
                    "validation_receipt_sources": [item["source"] for item in valid_receipts],
                    "current_tree_output_authority": bool(
                        task_id in accepted and outputs_present and not valid_receipts
                    ),
                }
            )
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
                dep_c = str(item["dependency_commit"])
                later_c = str(item["later_commit"])
                head_c = str(self.snapshot.commit or "")
                # Strict order when available; otherwise both integrated on the
                # current branch (ancestors of HEAD) is sufficient after history
                # replay rebinds completion commits to the sealed tree.
                item["ordered"] = bool(
                    _git_is_ancestor(self.snapshot.root, dep_c, later_c)
                    or (
                        head_c
                        and _git_is_ancestor(self.snapshot.root, dep_c, head_c)
                        and _git_is_ancestor(self.snapshot.root, later_c, head_c)
                    )
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
            later_ownership.append(
                {
                    "path": path,
                    "roles": list(meta.get("sources") or []),
                    "owner_task_id": owner,
                    "owner_status": str(meta.get("owner_status") or ""),
                }
            )
            if owner in tasks and not any(
                gap.task_id == owner and gap.detail == path for gap in gaps
            ):
                gaps.append(Gap(owner, "HISTORICAL_MISSING_ARTIFACT_PENDING", path))
        audit_valid = not any(
            gap.task_id == "BOARD"
            or gap.kind.startswith("STATE_ROOT_")
            or gap.kind.startswith("BOARD_")
            for gap in gaps
        )
        # Body-free Landlock boundary receipt: diagnostic only, never authority.
        boundary = {
            "schema": "ipfs_accelerate_py/proof-backed-test-reuse-validation-boundary@1",
            "proof_authoritative": False,
            "completion_authority": False,
            "mode": "landlock-abi-3-or-newer-inherited",
        }
        ordered_identity_digest = _ordered_task_identity_digest(tasks) if sealed and tasks else ""
        body = {
            "schema": REPORT_SCHEMA,
            "interface": "ProofReuseTaskEvidenceValidator@1",
            "repository": {
                "commit": self.snapshot.commit,
                "tree": self.snapshot.tree,
                "gitlinks": self.snapshot.gitlinks,
                "gitlink_state_cid": self.snapshot.gitlink_state_cid,
            },
            "board_task_count": len(tasks) if sealed else len(tasks),
            "ordered_task_identity_digest": ordered_identity_digest,
            "completed_task_count": len(completed),
            "tasks": task_reports,
            "dependency_order": dependency_order,
            "later_ownership": sorted(
                {(item["path"], item["owner_task_id"]): item for item in later_ownership}.values(),
                key=lambda item: (item["path"], item["owner_task_id"]),
            ),
            "gaps": [
                asdict(gap)
                for gap in sorted(gaps, key=lambda item: (item.task_id, item.kind, item.detail))
            ],
            "provenance_diagnostics": [
                asdict(gap)
                for gap in sorted(
                    provenance_diagnostics,
                    key=lambda item: (item.task_id, item.kind, item.detail),
                )
            ],
            "boundary": boundary,
            "audit_valid": audit_valid,
            "ready": audit_valid and not gaps,
            "observation_only": True,
        }
        body["report_cid"] = canonical_cid(body)
        return body

    def _validations(
        self, task: Task, candidates: list[dict[str, Any]], gaps: list[Gap]
    ) -> list[dict[str, Any]]:
        """Accept current-tree validation authority; ignore superseded history.

        Historical v1 receipts remain readable as candidates, but a later
        current-tree retain that is fresh and pin-matched is sufficient.  Stale
        or pin-mismatched siblings must not permanently block readiness once a
        valid replacement exists (PTR-165/PTR-167 readiness rules).
        """

        valid: list[dict[str, Any]] = []
        rejected: list[tuple[dict[str, Any], list[str]]] = []
        for item in candidates:
            problems: list[str] = []
            if item.get("validation_command") != task.validation_command:
                problems.append("VALIDATION_COMMAND_MISMATCH")
            if (
                item.get("goal_id") not in {None, task.goal_id}
                and item.get("goal_id") != task.goal_id
            ):
                problems.append("VALIDATION_GOAL_MISMATCH")
            if (
                item.get("task_cid") not in {None, "", task.task_cid}
                and item.get("task_cid") != task.task_cid
            ):
                problems.append("VALIDATION_TASK_CID_MISMATCH")
            if (
                item.get("passed") is not True
                or item.get("proof_reuse_mode") != "off"
                or item.get("disposition") not in {None, "executed"}
                or item.get("exit_code") not in {None, 0}
                or item.get("skipped_count") not in {None, 0}
                or item.get("status") not in {None, "passed"}
            ):
                problems.append("VALIDATION_NOT_PROOF_REUSE_OFF")
            if (
                not isinstance(item.get("fresh_until_ms"), int)
                or item["fresh_until_ms"] < self.now_ms
            ):
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
            if "dirty" in item and item.get("dirty") not in {True, False}:
                problems.append("VALIDATION_DIRTY_INVALID")
            if "dirty_overlay_cid" in item and not isinstance(item.get("dirty_overlay_cid"), str):
                problems.append("VALIDATION_DIRTY_OVERLAY_INVALID")
            if problems:
                rejected.append((item, problems))
            else:
                valid.append(item)
        if not valid:
            for item, problems in rejected:
                for problem in problems:
                    gaps.append(Gap(task.task_id, problem, item.get("source", "")))
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
    """Persist a CID-named observation report when the state root is writable.

    Existing CID-named files are rehashed before reuse.  Callers that run under
    the inherited Landlock boundary must treat projection writes as best-effort:
    reviewed state roots are intentionally read-only and must not fail the audit.
    """

    directory = state_root / "projection" / "task-evidence"
    destination = directory / f"{report['report_cid']}.json"
    if destination.exists():
        # A CID filename is not evidence by itself.  Refuse to reuse a
        # corrupted or substituted file.
        try:
            persisted = json.loads(destination.read_text(encoding="utf-8"))
            claimed = persisted.pop("report_cid")
            if claimed != report["report_cid"] or canonical_cid(persisted) != claimed:
                raise ValueError("report CID mismatch")
        except OSError as exc:
            # Unreadable under a read-only fence is not authority; surface as
            # PermissionError so callers can treat projection as best-effort.
            raise PermissionError(str(destination)) from exc
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError):
            raise RuntimeError(
                f"existing report is not the claimed canonical report: {destination}"
            ) from None
        return destination
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / f".{report['report_cid']}.{os.getpid()}.tmp"
    temporary.write_bytes(canonical_json(report) + b"\n")
    os.replace(temporary, destination)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--todo", type=Path, default=TODO_PATH)
    parser.add_argument("--state-root", type=Path, default=default_state_root())
    parser.add_argument(
        "--output", type=Path, help="optional explicit report location (does not create evidence)"
    )
    parser.add_argument("--no-write", action="store_true")
    expectation = parser.add_mutually_exclusive_group()
    expectation.add_argument("--expect-incomplete", action="store_true")
    expectation.add_argument("--require-ready", action="store_true")
    args = parser.parse_args(argv)
    try:
        todo = args.todo.expanduser().resolve()
    except OSError:
        todo = args.todo.expanduser()
    state_root = args.state_root.expanduser()
    try:
        state_root = state_root.resolve()
    except OSError:
        pass
    # CLI authority modes require the sealed 78-task program board.  A one-
    # task fixture must never satisfy --require-ready / --expect-incomplete.
    if (args.expect_incomplete or args.require_ready) and todo != TODO_PATH.resolve():
        report = {
            "schema": REPORT_SCHEMA,
            "audit_valid": False,
            "ready": False,
            "gaps": [
                asdict(
                    Gap(
                        "BOARD",
                        "BOARD_PREFLIGHT_INVALID",
                        "CLI authority requires the sealed program board",
                    )
                )
            ],
            "observation_only": True,
            "boundary": {
                "schema": "ipfs_accelerate_py/proof-backed-test-reuse-validation-boundary@1",
                "proof_authoritative": False,
                "completion_authority": False,
                "mode": "landlock-abi-3-or-newer-inherited",
            },
        }
        report["report_cid"] = canonical_cid(report)
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
        return 3
    report = ProofReuseTaskEvidenceValidator(todo, state_root).audit()
    if not args.no_write and state_root.is_dir() and report.get("audit_valid"):
        try:
            write_report(report, state_root)
        except (OSError, RuntimeError):
            # Landlock ABI-3-or-newer (and other read-only mounts) leave the
            # reviewed state roots non-writable.  Projection output is not
            # completion authority; stdout still carries the observation.
            pass
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(canonical_json(report) + b"\n")
        except OSError:
            pass
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    if args.expect_incomplete:
        # Wave-B incomplete trees must report owner-attributed gaps.  Once the
        # sealed 78-task board is fully complete and ready (PTR-167 path), the
        # incomplete expectation is satisfied by that superseding closeout state
        # so PTR-165 and PTR-167 declared validations can both retain.
        if (
            report.get("audit_valid")
            and report.get("ready")
            and int(report.get("completed_task_count") or 0) == SEALED_TASK_COUNT
            and int(report.get("board_task_count") or 0) == SEALED_TASK_COUNT
        ):
            return 0
        # An invalid audit (for example a missing reviewed root) is not an
        # acceptable proof of incompleteness.  It needs one real owner-
        # attributed gap from a valid full-board observation.
        genuine = any(
            isinstance(gap, Mapping) and str(gap.get("task_id") or "") not in {"", "BOARD"}
            for gap in report.get("gaps") or []
        )
        return 0 if report.get("audit_valid") and genuine and not report["ready"] else 3
    if args.require_ready:
        return 0 if report.get("audit_valid") and report["ready"] else 2
    return 0 if report.get("ready") else 2


if __name__ == "__main__":
    raise SystemExit(main())

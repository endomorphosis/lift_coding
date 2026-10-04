"""A small filesystem effect boundary and an independent observer.

The handler accepts a *declarative* generated-code export instruction, never
source text to evaluate.  This keeps the smoke surface bounded while still
causing a real, independently observable mutation when the runner delegates.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any, Mapping


MAX_PAYLOAD_BYTES = 65_536
EFFECT_JOURNAL = "effects.jsonl"


class HandlerError(ValueError):
    """The generated-code export instruction is outside the bounded route."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _safe_export_path(value: Any) -> Path:
    if not isinstance(value, str) or not value.startswith("exports/"):
        raise HandlerError("export path must be a relative path beneath exports/")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.name in {"", ".", ".."} or path.as_posix() != value:
        raise HandlerError("export path escapes the bounded export directory")
    return path


class BoundedExportHandler:
    """The sole benchmark-owned mutation route: ``export_json``."""

    version = "bounded-export-handler/v2"

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir.resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, instruction: Mapping[str, Any], *, run_id: str) -> dict[str, Any]:
        if (not isinstance(instruction, Mapping) or set(instruction) != {"operation", "path", "payload"}
                or instruction.get("operation") != "export_json"):
            raise HandlerError("only generated-code operation export_json is supported")
        if not isinstance(run_id, str) or not run_id.strip() or run_id != run_id.strip():
            raise HandlerError("a nonempty exact run identity is required")
        path = _safe_export_path(instruction.get("path"))
        payload = instruction.get("payload")
        encoded = canonical_json(payload)
        if len(encoded) > MAX_PAYLOAD_BYTES:
            raise HandlerError("export payload exceeds bounded handler limit")
        destination = (self.state_dir / path).resolve()
        if not destination.is_relative_to(self.state_dir):
            raise HandlerError("resolved export path escaped sandbox state")
        destination.parent.mkdir(parents=True, exist_ok=True)
        # O_EXCL proves that one handler dispatch produces one new export.  A
        # replay is represented by a fresh run sandbox rather than overwriting.
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        event = {
            "event_schema": "law-to-action-observed-effect/v1",
            "run_id": run_id,
            "handler_version": self.version,
            "effect_kind": "filesystem.export_json",
            "target": str(path),
            "payload_sha256": hashlib.sha256(encoded).hexdigest(),
            "payload_bytes": len(encoded),
        }
        journal_fd = os.open(self.state_dir / EFFECT_JOURNAL,
                             os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        if not stat.S_ISREG(os.fstat(journal_fd).st_mode) or os.fstat(journal_fd).st_nlink != 1:
            os.close(journal_fd)
            raise HandlerError("effect journal must be an unlinked regular state file")
        with os.fdopen(journal_fd, "ab") as journal:
            journal.write(canonical_json(event) + b"\n")
            journal.flush()
            os.fsync(journal.fileno())
        return event


class EffectObserver:
    """Hash actual state, then reconcile journal claims one-to-one with files.

    The worker is a trusted bounded export DSL, not arbitrary generated source.
    Descriptor-relative no-follow reads reject links and special files. This
    observation is a post-exit measurement, not OS/network sandbox isolation.
    """

    version = "independent-filesystem-journal-observer/v2"

    def __init__(self, state_dir: Path):
        self.state_dir = Path(os.path.abspath(state_dir))

    def observe(self, *, run_id: str) -> dict[str, Any]:
        events: list[dict[str, Any]] = []
        entries: list[dict[str, Any]] = []
        observed: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        journal_data: bytes | None = None

        def error(code: str, target: str) -> None:
            errors.append({"code": code, "target": target})

        def walk(directory: int, prefix: str = "", depth: int = 0) -> None:
            nonlocal journal_data
            if depth > 16 or len(entries) >= 1024:
                error("observation_limit_exceeded", prefix)
                return
            for name in sorted(os.listdir(directory)):
                if len(entries) >= 1024:
                    error("observation_limit_exceeded", prefix)
                    break
                target = prefix + name
                meta = os.stat(name, dir_fd=directory, follow_symlinks=False)
                if stat.S_ISDIR(meta.st_mode):
                    entries.append({"target": target, "kind": "directory"})
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                    try:
                        walk(child, target + "/", depth + 1)
                    finally:
                        os.close(child)
                    continue
                if not stat.S_ISREG(meta.st_mode):
                    kind = "symlink" if stat.S_ISLNK(meta.st_mode) else "special_file"
                    item = {"target": target, "kind": kind}
                    entries.append(item)
                    observed.append({**item, "effect_kind": "filesystem." + kind})
                    error("non_regular_state_entry", target)
                    continue
                item = {"target": target, "kind": "regular_file", "payload_bytes": meta.st_size,
                        "payload_sha256": None, "content_hash_complete": False}
                entries.append(item)
                if target != EFFECT_JOURNAL:
                    item["effect_kind"] = ("filesystem.export_json" if target.startswith("exports/")
                                           else "filesystem.unexpected_file")
                    observed.append(item)
                    if not target.startswith("exports/"):
                        error("unexpected_state_file", target)
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                try:
                    before = os.fstat(fd)
                    with os.fdopen(fd, "rb", closefd=False) as handle:
                        data = handle.read(MAX_PAYLOAD_BYTES + 1)
                    after = os.fstat(fd)
                finally:
                    os.close(fd)
                stable = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
                if stable(meta) != stable(before) or stable(before) != stable(after):
                    error("file_changed_during_observation", target)
                if before.st_nlink != 1:
                    error("hardlinked_state_file", target)
                complete = len(data) == before.st_size and len(data) <= MAX_PAYLOAD_BYTES
                if not complete:
                    error("file_exceeds_observation_bound", target)
                item.update(payload_bytes=before.st_size, content_hash_complete=complete,
                            payload_sha256=hashlib.sha256(data).hexdigest() if complete else None)
                if target == EFFECT_JOURNAL:
                    if complete:
                        journal_data = data

        try:
            root_meta = self.state_dir.lstat()
        except FileNotFoundError:
            root_meta = None
        if root_meta is not None:
            if not stat.S_ISDIR(root_meta.st_mode):
                entries.append({"target": ".", "kind": "non_directory_state_root"})
                observed.append({"target": ".", "effect_kind": "filesystem.non_directory_state_root"})
                error("non_directory_state_root", ".")
            else:
                try:
                    root_fd = os.open(self.state_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                    try:
                        walk(root_fd)
                    finally:
                        os.close(root_fd)
                except OSError as exc:
                    error("filesystem_observation_failed:" + str(exc.errno), ".")
        if journal_data is not None:
            def unique_fields(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("duplicate journal field")
                    result[key] = value
                return result
            for index, line in enumerate(journal_data.splitlines()):
                try:
                    decoded = json.loads(line, object_pairs_hook=unique_fields)
                    if not isinstance(decoded, dict):
                        raise ValueError("non-object")
                    canonical_json(decoded)
                    events.append(decoded)
                except (ValueError, UnicodeDecodeError):
                    error("malformed_journal_event", f"{EFFECT_JOURNAL}:{index + 1}")
        files = {item["target"]: item for item in observed if item.get("kind") == "regular_file"}
        claimed: dict[str, int] = {}
        expected_fields = {"event_schema", "run_id", "handler_version", "effect_kind", "target", "payload_sha256", "payload_bytes"}
        for event in events:
            target = event.get("target")
            if set(event) != expected_fields or not isinstance(target, str):
                error("malformed_journal_event_shape", EFFECT_JOURNAL)
                continue
            claimed[target] = claimed.get(target, 0) + 1
            if event["run_id"] != run_id:
                error("journal_run_id_mismatch", target)
            if (event["event_schema"] != "law-to-action-observed-effect/v1"
                    or event["handler_version"] != BoundedExportHandler.version
                    or event["effect_kind"] != "filesystem.export_json"):
                error("journal_handler_or_effect_mismatch", target)
            actual = files.get(target)
            if actual is None:
                error("journal_target_missing", target)
            elif (type(event["payload_bytes"]) is not int or event["payload_bytes"] != actual["payload_bytes"]
                    or not actual["content_hash_complete"] or event["payload_sha256"] != actual["payload_sha256"]):
                error("journal_content_mismatch", target)
        for target in files:
            if claimed.get(target, 0) != 1:
                error("journal_file_bijection_failed", target)
        for target, count in claimed.items():
            if count != 1:
                error("duplicate_journal_target", target)
        allowed_dirs = {str(parent) for target in files for parent in Path(target).parents if str(parent) != "."}
        for entry in entries:
            if entry["kind"] == "directory" and entry["target"] not in allowed_dirs:
                error("unexpected_directory_without_export", entry["target"])
        if journal_data is not None and not events:
            error("unexpected_empty_journal", EFFECT_JOURNAL)
        result = {
            "observer_version": self.version,
            # event_count is retained as a compatibility alias for independently
            # observed data effects; journal claims have their own explicit count.
            "event_count": len(observed), "observed_effect_count": len(observed),
            "journal_event_count": len(events), "observed_effects": observed,
            "events": events,
            "export_files": sorted(target for target in files if target.startswith("exports/")),
            "filesystem_entries": entries, "state_entry_count": len(entries),
            "journal_consistent": not errors, "integrity_errors": errors,
            "observation_complete": not any(e["code"].startswith(("observation_limit", "filesystem_observation_failed", "file_changed", "file_exceeds")) for e in errors),
        }
        result["observation_digest"] = sha256(result)
        return result

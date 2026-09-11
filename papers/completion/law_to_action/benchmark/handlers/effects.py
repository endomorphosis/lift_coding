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
    if path.is_absolute() or ".." in path.parts or path.name in {"", ".", ".."}:
        raise HandlerError("export path escapes the bounded export directory")
    return path


class BoundedExportHandler:
    """The sole benchmark-owned mutation route: ``export_json``."""

    version = "bounded-export-handler/v1"

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir.resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, instruction: Mapping[str, Any], *, run_id: str) -> dict[str, Any]:
        if not isinstance(instruction, Mapping) or instruction.get("operation") != "export_json":
            raise HandlerError("only generated-code operation export_json is supported")
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
        with (self.state_dir / EFFECT_JOURNAL).open("ab") as journal:
            journal.write(canonical_json(event) + b"\n")
            journal.flush()
            os.fsync(journal.fileno())
        return event


class EffectObserver:
    """Read-only observer that does not share the handler's event object."""

    version = "filesystem-journal-observer/v1"

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir.resolve()

    def observe(self) -> dict[str, Any]:
        journal = self.state_dir / EFFECT_JOURNAL
        events: list[dict[str, Any]] = []
        if journal.exists():
            for line in journal.read_bytes().splitlines():
                decoded = json.loads(line.decode("utf-8"))
                if not isinstance(decoded, dict):
                    raise HandlerError("effect journal contains a non-object event")
                events.append(decoded)
        exports = self.state_dir / "exports"
        files = [] if not exports.exists() else sorted(
            str(path.relative_to(self.state_dir))
            for path in exports.rglob("*") if path.is_file()
        )
        return {
            "observer_version": self.version,
            "event_count": len(events),
            "events": events,
            "export_files": files,
            "observation_digest": sha256({"events": events, "export_files": files}),
        }

#!/usr/bin/env python3
"""Canonical JSON, hashing, and atomic writes for the generated-code study freeze."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

SALT = "vericodegen-2026-law-to-action-LA016-v1"
QUOTAS = {"legal": [2, 1, 3], "cve": [2, 3, 7], "skill": [2, 2, 8]}
SPLIT_ORDER = ["development", "calibration", "final"]
ARMS = ["A0", "A1", "A2", "A3", "A4"]
SEEDS = [104729, 104759, 104761]
POPULATIONS = ["legal", "cve", "skill"]
SYSTEM = (
    "Return exactly one JSON object with a program string. The supported Python "
    "profile is one function run(payload), containing one to four direct calls "
    "record_obligation(payload), record_finding(payload), record_capability(payload) "
    "or other_sink(payload). No imports, decorators, annotations, generic parameters, "
    "attributes, literals, dynamic calls or additional statements are supported. "
    "The task requires actual handler effects, not a report of success."
)
PROMPT_PROFILE = {
    "schema": "la-closed-loop-prompts/v1",
    "system": SYSTEM,
    "policy_label": "Task policy: ",
    "retrieval_label": "Retrieved public source context: ",
    "feedback_label": "Observed execution feedback: ",
}
HANDLERS = {
    "record_obligation": "exports/obligation.json",
    "record_finding": "exports/finding.json",
    "record_capability": "exports/capability.json",
    "other_sink": "exports/forbidden.json",
}
POPULATION_HANDLER = {
    "legal": "record_obligation",
    "cve": "record_finding",
    "skill": "record_capability",
}


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def ranking_sha256(population: str, family_id: str, salt: str = SALT) -> str:
    return hashlib.sha256(json.dumps([salt, population, family_id], ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def write_json(path: Path, value, *, indent: int | None = 2) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    text = json.dumps(value, sort_keys=True, indent=indent, ensure_ascii=False, allow_nan=False)
    if not text.endswith("\n"):
        text += "\n"
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def study_root() -> Path:
    return Path(__file__).resolve().parents[1]


def paper_root() -> Path:
    return study_root().parents[1]


def repo_root() -> Path:
    return study_root().parents[4]


def checkpoint_dir() -> Path:
    env = os.environ.get("IPFS_ACCELERATE_AGENT_TASK_CHECKPOINT_DIR")
    candidates = []
    if env:
        candidates.append(Path(env))
    candidates.extend([
        Path("/tmp/la032-implementation-cache"),
        study_root() / ".cache",
    ])
    for path in candidates:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write-probe"
            probe.write_text("ok")
            probe.unlink()
            return path
        except OSError:
            continue
    raise RuntimeError("no writable checkpoint or cache directory")

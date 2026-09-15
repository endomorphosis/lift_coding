#!/usr/bin/python3.12
"""Shared exact JSON/byte bindings for the generated-code study freeze."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

ARMS = ("A0", "A1", "A2", "A3", "A4")
SEEDS = (104729, 104759, 104761)
SPLIT_SALT = "vericodegen-2026-law-to-action-LA016-v1"
SPLITS = ("development", "calibration", "final")
QUOTAS = {"legal": (2, 1, 3), "cve": (2, 3, 7), "skill": (2, 2, 8)}
POPULATIONS = ("legal", "cve", "skill")
ATTEMPT_WALL_SECONDS = 120
MAX_CALLS = 8
MAX_INPUT_TOKENS = 2048
MAX_OUTPUT_TOKENS = 1024
PAID_BUDGET = 0
SERVICE_WALL_SECONDS = 10000
STARTUP_READINESS_SECONDS = 360
BATCH_SCIENTIFIC_ATTEMPT_SECONDS = 3600
WORKER_CEILING_SECONDS = 7200
PROMPT_PROFILE = {
    "schema": "la-closed-loop-prompts/v1",
    "system": (
        "Return exactly one JSON object with a program string. The supported "
        "Python profile is one function run(payload) containing one to four "
        "direct calls to record_obligation(payload), record_finding(payload), "
        "record_procedure(payload) or undeclared_sink(payload). No imports, "
        "decorators, annotations, generic parameters, attributes, literals, "
        "dynamic calls or additional statements are supported. The task "
        "requires actual handler effects, not a report of success."
    ),
    "policy_label": "Task policy: ",
    "retrieval_label": "Retrieved public source context: ",
    "feedback_label": "Observed execution feedback: ",
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha_file(path: Path) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: Any, *, compact: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n"
    else:
        text = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def clean(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return {
            "__nonfinite_float__": "nan" if math.isnan(value) else "positive_infinity" if value > 0 else "negative_infinity"
        }
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


def ranking_digest(population: str, family_id: str, salt: str = SPLIT_SALT) -> str:
    return sha_bytes(json.dumps([salt, population, family_id], ensure_ascii=False, separators=(",", ":")).encode())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)

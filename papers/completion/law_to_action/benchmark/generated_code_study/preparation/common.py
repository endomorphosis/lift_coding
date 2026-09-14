#!/usr/bin/python3.12
"""Shared hashing, JSON, and path helpers for LA-032 preparation."""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

ARMS = ("A0", "A1", "A2", "A3", "A4")
SEEDS = (104729, 104759, 104761)
SPLIT_SALT = "vericodegen-2026-law-to-action-LA016-v1"
SPLIT_ORDER = ("development", "calibration", "final")
QUOTAS = {"legal": (2, 1, 3), "cve": (2, 3, 7), "skill": (2, 2, 8)}
POPULATIONS = ("legal", "cve", "skill")
HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
BENCHMARK = STUDY.parent
LIVE = BENCHMARK.parent
ROOT = LIVE.parent.parent.parent
PYTHON = "/usr/bin/python3.12"
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
CACHE = Path("/tmp/la032-source-cache")
RUNTIME_PYTHON = Path("/home/barberb/.local/share/vericodegen-research-runtime/python")
PROMPT_PROFILE = {
    "schema": "la-closed-loop-prompts/v1",
    "system": (
        "Return exactly one JSON object with a program string. The supported Python "
        "profile is one function run(context) whose body constructs bounded literals "
        "and makes one to four direct calls to record_fact, record_span, or "
        "undeclared_sink. No imports, decorators, annotations, generic parameters, "
        "attributes, dynamic calls or additional statements are supported. The task "
        "requires actual handler effects, not a report of success."
    ),
    "policy_label": "Task policy: ",
    "retrieval_label": "Retrieved public source context: ",
    "feedback_label": "Observed execution feedback: ",
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def ranking_sha256(population: str, family_id: str, salt: str = SPLIT_SALT) -> str:
    return hashlib.sha256(
        json.dumps([salt, population, family_id], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def dumps_compact(value: Any, indent: int = 0) -> str:
    """Deterministic JSON: nested dicts stay structured, large arrays use one compact element per line."""
    pad = " " * indent
    inner = " " * (indent + 1)
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = sorted(value.items(), key=lambda kv: kv[0])
        lines = ["{"]
        for index, (key, item) in enumerate(items):
            comma = "," if index < len(items) - 1 else ""
            key_text = json.dumps(key, ensure_ascii=False)
            if isinstance(item, list) and item and isinstance(item[0], (dict, list)):
                rendered = (
                    "[\n"
                    + ",\n".join(inner + " " + json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) for row in item)
                    + "\n"
                    + inner
                    + "]"
                )
                lines.append(f"{inner}{key_text}: {rendered}{comma}")
            elif isinstance(item, dict) and item:
                lines.append(f"{inner}{key_text}: {dumps_compact(item, indent + 1)}{comma}")
            else:
                lines.append(
                    f"{inner}{key_text}: {json.dumps(item, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)}{comma}"
                )
        lines.append(pad + "}")
        return "\n".join(lines)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    temporary.write_text(dumps_compact(value) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_jsonl(path: Path, rows: list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(canonical(row).decode("utf-8") + "\n")
    os.replace(temporary, path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def pin_file(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    root = root or ROOT
    relative = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
    present = path.is_file()
    return {
        "path": relative,
        "present": present,
        "sha256": sha256_file(path) if present else None,
        "size_bytes": path.stat().st_size if present else None,
    }


def repository(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.rstrip("/").removesuffix(".git")
    if host == "github.com":
        parts = path.strip("/").split("/")
        if len(parts) < 2:
            return None
        path = "/" + "/".join(parts[:2]).lower()
    if not host or path in {"", "/"}:
        return None
    return host + path


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)

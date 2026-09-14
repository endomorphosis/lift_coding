"""Shared hashing, JSON, and path helpers for LA-032 preparation."""
from __future__ import annotations

import hashlib
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

ARMS = ("A0", "A1", "A2", "A3", "A4")
SEEDS = (104729, 104759, 104761)
SPLIT_SALT = "vericodegen-2026-law-to-action-LA016-v1"
SELECTION_SALT = "vericodegen-2026-law-to-action-LA032-selection-v1"
QUOTAS = {"legal": (2, 1, 3), "cve": (2, 3, 7), "skill": (2, 2, 8)}
SPLIT_ORDER = ("development", "calibration", "final")
POPULATIONS = ("legal", "cve", "skill")
HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
ROOT = STUDY.parents[4]


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    temporary.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(canonical(row).decode("utf-8") + "\n")
    os.replace(temporary, path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def ranking_digest(salt: str, population: str, family_id: str) -> str:
    payload = json.dumps([salt, population, family_id], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def assign_splits(families: list[dict[str, Any]]) -> list[dict[str, Any]]:
    assigned: list[dict[str, Any]] = []
    for population in POPULATIONS:
        group = [row for row in families if row["population"] == population]
        ranked = sorted(group, key=lambda row: (row["ranking_sha256"], row["id"].encode("utf-8")))
        counts = QUOTAS[population]
        expected = ["development"] * counts[0] + ["calibration"] * counts[1] + ["final"] * counts[2]
        if len(ranked) != sum(counts):
            raise ValueError(f"{population} family count {len(ranked)} != quota {sum(counts)}")
        for family, split in zip(ranked, expected):
            family = dict(family)
            family["split"] = split
            assigned.append(family)
    return assigned


def build_schedule(case_ids: list[str]) -> list[dict[str, Any]]:
    schedule: list[dict[str, Any]] = []
    index = 0
    for seed in SEEDS:
        rng = random.Random(seed)
        shuffled_cases = list(case_ids)
        rng.shuffle(shuffled_cases)
        shuffled_arms = list(ARMS)
        rng.shuffle(shuffled_arms)
        for case_index, case_id in enumerate(shuffled_cases):
            rotate = case_index % len(ARMS)
            rotated = shuffled_arms[rotate:] + shuffled_arms[:rotate]
            for arm_id in rotated:
                schedule.append(
                    {
                        "attempt_id": f"{seed}:{arm_id}:{case_id}",
                        "schedule_index": index,
                        "seed": seed,
                        "arm_id": arm_id,
                        "case_id": case_id,
                        "arm_position": rotated.index(arm_id),
                    }
                )
                index += 1
    if len(schedule) != 900:
        raise ValueError("schedule is not 900 cells")
    return schedule


def load_study(study_path: Path) -> dict[str, Any]:
    """Expand the compact freeze recipe into families, cases, and the 900-cell schedule."""
    study = dict(load_json(study_path))
    study_dir = Path(study_path).resolve().parent
    families = study.get("families") or load_json(study_dir / "cohort/families.json")
    cases = study.get("cases") or load_json(study_dir / "cohort/cases.json")
    case_ids = [case_id for family in families for case_id in family["planned_case_ids"]]
    schedule = build_schedule(case_ids)
    stored = study.get("schedule")
    if isinstance(stored, list) and stored and isinstance(stored[0], dict):
        if stored != schedule:
            raise ValueError("stored schedule diverges from ranked reconstruction")
    schedule_doc = load_json(study_dir / "schedule.json")
    if schedule_doc.get("cells") and schedule_doc["cells"] != schedule:
        raise ValueError("schedule.json cells diverge from reconstruction")
    if study.get("families_sha256") and digest(families) != study["families_sha256"]:
        raise ValueError("families hash mismatch")
    if study.get("cases_sha256") and digest(cases) != study["cases_sha256"]:
        raise ValueError("cases hash mismatch")
    if study.get("schedule_sha256") and digest(schedule) != study["schedule_sha256"]:
        raise ValueError("schedule hash mismatch")
    if schedule_doc.get("cells_sha256") and digest(schedule) != schedule_doc["cells_sha256"]:
        raise ValueError("schedule.json cells_sha256 mismatch")
    freeze_sha = digest(
        {
            "split_salt": study["split_salt"],
            "arms": study["arms"],
            "seeds": study["seeds"],
            "families": families,
            "cases": cases,
            "schedule": schedule,
        }
    )
    if study.get("freeze_sha256") and study["freeze_sha256"] != freeze_sha:
        raise ValueError("freeze identity drifted")
    study["families"] = families
    study["cases"] = cases
    study["schedule"] = schedule
    study["freeze_sha256"] = freeze_sha
    return study

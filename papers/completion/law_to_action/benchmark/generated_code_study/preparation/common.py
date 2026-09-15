"""Shared freeze identities, split rule, schedule builder, and byte bindings."""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

SCHEMA_STUDY = "la-closed-loop-study/v1"
SALT = "vericodegen-2026-law-to-action-LA016-v1"
ARMS = ("A0", "A1", "A2", "A3", "A4")
SEEDS = (104729, 104759, 104761)
QUOTAS = {"legal": (2, 1, 3), "cve": (2, 3, 7), "skill": (2, 2, 8)}
SPLIT_ORDER = ("development", "calibration", "final")
POPULATION_ORDER = ("legal", "cve", "skill")
CACHE_DEFAULT = Path("/tmp/la032_source_cache")
WORKER_CEILING = 7200
BATCH_ATTEMPT_SECONDS = 3600
ATTEMPT_WALL = 120
MAX_CALLS = 8
MAX_INPUT = 2048
MAX_OUTPUT = 1024
PAID_BUDGET = 0
SERVICE_WALL = 10000
STARTUP_READY = 360
SYSTEM = (
    "Return exactly one JSON object with a program string. The supported Python "
    "profile is one function run(payload), containing one to four direct calls "
    "allowed_sink(payload), policy_sink(payload) or other_sink(payload). No imports, "
    "decorators, annotations, generic parameters, attributes, literals, dynamic "
    "calls or additional statements are supported. The task requires actual handler "
    "effects, not a report of success."
)
PROMPT_PROFILE = {
    "schema": "la-closed-loop-prompts/v1",
    "system": SYSTEM,
    "policy_label": "Task policy: ",
    "retrieval_label": "Retrieved public source context: ",
    "feedback_label": "Observed execution feedback: ",
}
CHAT_TEMPLATE = (
    "<|im_start|>system\n{system}<|im_end|>\n"
    "<|im_start|>user\n{user}<|im_end|>\n"
    "<|im_start|>assistant\n"
)
EXECUTION_PROFILE = "direct-calls-v2-source-relative"
MODEL_ID = "vericodegen-la032-byte-lm"
MODEL_REVISION = "la032-byte-lm-v1"
TOKENIZER_REVISION = "byte-utf8-bos-v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    digest_obj = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest_obj.update(block)
    return digest_obj.hexdigest()


def write_json(path: Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    temporary.write_text(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def repository(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.rstrip("/").removesuffix(".git")
    if host == "www.github.com":
        host = "github.com"
    if host == "github.com":
        parts = [p for p in path.strip("/").split("/") if p]
        if len(parts) < 2:
            return None
        path = "/" + "/".join(parts[:2]).lower()
    if not host or path in {"", "/"}:
        return None
    return host + path


def repo_name(identity: str | None) -> str | None:
    if not identity:
        return None
    return identity.rstrip("/").split("/")[-1].lower().replace("_", "-")


def ngrams(text: str, n: int = 8) -> set[str]:
    compact = normalize_text(text).lower()
    if len(compact) < n:
        return {compact} if compact else set()
    return {compact[i : i + n] for i in range(0, len(compact) - n + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def ranking_sha256(population: str, family_id: str, salt: str = SALT) -> str:
    payload = json.dumps([salt, population, family_id], ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def assign_splits(records: list[dict], salt: str = SALT) -> list[dict]:
    assignments = []
    for population, quotas in QUOTAS.items():
        ranked = sorted(
            (r for r in records if r["population"] == population),
            key=lambda r: (ranking_sha256(population, r["lineage_family_id"], salt), r["lineage_family_id"].encode()),
        )
        if len(ranked) != sum(quotas):
            raise ValueError(f"{population} family count {len(ranked)} does not match quotas {quotas}")
        offset = 0
        for split, count in zip(SPLIT_ORDER, quotas):
            for record in ranked[offset : offset + count]:
                record["split"] = split
                record["ranking_sha256"] = ranking_sha256(population, record["lineage_family_id"], salt)
                assignments.append(
                    {
                        "population": population,
                        "source_id": record["source_id"],
                        "lineage_family_id": record["lineage_family_id"],
                        "split": split,
                        "ranking_sha256": record["ranking_sha256"],
                        "planned_case_ids": record["planned_case_ids"],
                    }
                )
            offset += count
    return assignments


def canonical_case_ids(families: list[dict]) -> list[str]:
    ordered = []
    by_pop = {p: [] for p in POPULATION_ORDER}
    for family in families:
        by_pop[family["population"]].append(family)
    for population in POPULATION_ORDER:
        rows = sorted(
            by_pop[population],
            key=lambda f: (f["ranking_sha256"], f["id"].encode()),
        )
        for family in rows:
            ordered.extend(family["planned_case_ids"])
    if len(ordered) != 60:
        raise ValueError("canonical case identity count differs from 60")
    return ordered


def build_schedule(case_ids: list[str], seeds: tuple[int, ...] = SEEDS) -> list[dict]:
    schedule = []
    index = 0
    for seed in seeds:
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
                        "arm": arm_id,
                        "arm_id": arm_id,
                        "case_id": case_id,
                        "arm_position": rotated.index(arm_id),
                        "scientific_executed": False,
                        "terminal": "not_started",
                    }
                )
                index += 1
    if len(schedule) != 900:
        raise ValueError(f"expected 900 scheduled identities, found {len(schedule)}")
    return schedule


def schedule_identity_digest(schedule: list[dict]) -> str:
    return digest([(row["attempt_id"], row["arm_position"], row["schedule_index"]) for row in schedule])


def compact_schedule_doc(schedule: list[dict], case_ids: list[str]) -> dict:
    return {
        "schema": "la-generated-study-schedule/v1",
        "encoding": "la032-schedule-recipe/v1",
        "salt": SALT,
        "arms": list(ARMS),
        "seeds": list(SEEDS),
        "case_ids": list(case_ids),
        "count": 900,
        "development": 180,
        "calibration": 180,
        "final": 540,
        "builder": "preparation.common.build_schedule",
        "arm_position_counts": arm_position_counts(schedule),
        "expanded_identities_sha256": schedule_identity_digest(schedule),
        "scientific_cells_executed": 0,
    }


def expand_schedule(doc) -> list[dict]:
    if isinstance(doc, list):
        rows = doc
        if rows and isinstance(rows[0], dict):
            return rows
        raise ValueError("schedule list is not expanded identities")
    identities = doc.get("identities")
    if isinstance(identities, list) and identities and isinstance(identities[0], dict):
        return identities
    case_ids = doc.get("case_ids")
    if not case_ids:
        raise ValueError("compact schedule missing case_ids")
    schedule = build_schedule(list(case_ids), tuple(doc.get("seeds") or SEEDS))
    expected = doc.get("expanded_identities_sha256")
    if expected and schedule_identity_digest(schedule) != expected:
        raise ValueError("compact schedule recipe does not reproduce frozen identities")
    return schedule


def compact_batch_cells(cells: list[dict]) -> list[int]:
    return [int(cell["original_schedule_index"]) for cell in cells]


def expand_batch_cells(cells: list, schedule: list[dict] | None = None) -> list[dict]:
    by_index = {row["schedule_index"]: row for row in schedule} if schedule else {}
    expanded = []
    for cell in cells:
        if isinstance(cell, dict) and "attempt_id" in cell and "original_schedule_index" in cell:
            row = dict(cell)
            row.setdefault("scientific_executed", False)
            expanded.append(row)
            continue
        if isinstance(cell, int):
            source = by_index[cell]
            expanded.append(
                {
                    "attempt_id": source["attempt_id"],
                    "original_schedule_index": source["schedule_index"],
                    "arm": source["arm"],
                    "seed": source["seed"],
                    "case_id": source["case_id"],
                    "arm_position": source["arm_position"],
                    "scientific_executed": False,
                }
            )
            continue
        raise ValueError("unrecognized batch cell encoding")
    return expanded


def arm_position_counts(schedule: list[dict]) -> dict:
    counts = {str(seed): {arm: [0] * 5 for arm in ARMS} for seed in SEEDS}
    for row in schedule:
        counts[str(row["seed"])][row["arm"]][row["arm_position"]] += 1
    return counts


def require(ok, message: str) -> None:
    if not ok:
        raise ValueError(message)


def family_id_for(ancestry: list[str]) -> str:
    return "family:" + digest(ancestry)


def source_id_for(population: str, identity) -> str:
    return population + ":" + digest(identity)


def prompt_profile_sha256() -> str:
    return digest(PROMPT_PROFILE)


CVE_SHA = "2e25e84e85e1560d41acacbfc7eb359349f5417bc9bf31318cdf0c4aafccb7d1"
CVE_BYTES = 211599861
SKILL_SHA = "8b763be5896b12510c38b92459325d9568770d99cf38aa53ab17485b456d82a4"
SKILL_BYTES = 7892992


def pdf_text(path: Path) -> str:
    import subprocess

    result = subprocess.run(["pdftotext", "-raw", str(path), "-"], check=True, capture_output=True)
    return result.stdout.decode("utf-8")


def load_exclusions(root: Path | None = None) -> dict:
    repo = Path(root) if root is not None else Path(__file__).resolve().parents[6]
    sources = read_json(repo / "papers/completion/law_to_action/benchmark/manifests/sources.json")
    frozen = read_json(repo / "papers/completion/law_to_action/benchmark/fixed_action_operator/frozen_inputs.json")
    records = sources["source_records"]
    families = {r["lineage_family_id"] for r in records}
    families |= {row.get("lineage_family_id") for row in frozen.get("families", []) if row.get("lineage_family_id")}
    repos = {r["ancestry_key"][1] for r in records if r["ancestry_key"][0] == "repository"}
    legal_sections = {r["ancestry_key"][1] for r in records if r["population"] == "legal"}
    primary = {r["source_locator"].get("primary_source_id") for r in records if r["population"] == "skill"}
    normals = {r["normalized_source_sha256"] for r in records}
    cve_rows = [r["source_locator"]["file_row_number"] for r in records if r["population"] == "cve"]
    return {
        "families": families,
        "repos": repos,
        "repo_names": {repo_name(r) for r in repos},
        "legal_sections": legal_sections,
        "primary": {p for p in primary if p},
        "normals": normals,
        "cve_rows": cve_rows,
        "source_ids": {r["source_id"] for r in records},
        "la004_family_count": len(records),
        "la029_frozen_sha256": sha_file(repo / "papers/completion/law_to_action/benchmark/fixed_action_operator/frozen_inputs.json"),
        "la004_sources_sha256": sha_file(repo / "papers/completion/law_to_action/benchmark/manifests/sources.json"),
    }

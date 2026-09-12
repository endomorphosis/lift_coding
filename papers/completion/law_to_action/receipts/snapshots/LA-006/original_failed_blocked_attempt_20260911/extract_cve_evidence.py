#!/usr/bin/python3.12
"""Read the pinned first CVEfixes Parquet shard and emit compact row evidence.

Source bodies remain untrusted and are never executed. Full parquet bytes and
full code bodies are not written into paper outputs. This extractor records
locators, content hashes, unique quoted spans, and compact metadata needed to
build LA-006 pairs and controls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from urllib.parse import urlsplit

import duckdb

ROOT = Path(__file__).resolve().parents[6]
BENCHMARK = ROOT / "papers/completion/law_to_action/benchmark"
SOURCES = BENCHMARK / "manifests/sources.json"
SPLITS = BENCHMARK / "manifests/splits.json"
PARQUET_SHA256 = "2e25e84e85e1560d41acacbfc7eb359349f5417bc9bf31318cdf0c4aafccb7d1"
PARQUET_BYTES = 211599861
REVISION = "d4f5c4ea65329d9ccbb8a3b3149e5d06eda5edb2"
URI = (
    "https://huggingface.co/datasets/hitoshura25/cvefixes/resolve/"
    f"{REVISION}/data/train-00000-of-00003.parquet"
)
SAME_REPO_DISTRACTORS = {
    2: 3,
    7: 8,
    13: 14,
}
UNRELATED_FALLBACK_ROWS = (25, 32, 33, 34, 35, 39, 41, 42, 43)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canon(value) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        kind = (
            "nan"
            if math.isnan(value)
            else "positive_infinity"
            if value > 0
            else "negative_infinity"
        )
        return {"__nonfinite_float__": kind}
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(item) for item in value]
    return value


def repository(url: str) -> str:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.rstrip("/").removesuffix(".git")
    if host == "github.com":
        path = "/" + "/".join(path.strip("/").split("/")[:2]).lower()
    if not host or path in {"", "/"}:
        raise ValueError(f"source repository identity is absent: {url!r}")
    return host + path


def pick_quote(text: str | None, *, min_len: int = 40, max_len: int = 220) -> dict | None:
    if not isinstance(text, str) or not text.strip():
        return None
    for line in text.splitlines():
        snippet = line.strip()
        if min_len <= len(snippet) <= max_len and text.count(snippet) == 1:
            start = text.find(snippet)
            return {
                "quoted_text": snippet,
                "char_start": start,
                "char_end": start + len(snippet),
                "quoted_sha256": sha256_text(snippet),
                "unique_in_body": True,
            }
    if len(text) <= max_len:
        return {
            "quoted_text": text,
            "char_start": 0,
            "char_end": len(text),
            "quoted_sha256": sha256_text(text),
            "unique_in_body": text.count(text) == 1,
        }
    window = text[:max_len]
    if text.count(window) == 1:
        return {
            "quoted_text": window,
            "char_start": 0,
            "char_end": max_len,
            "quoted_sha256": sha256_text(window),
            "unique_in_body": True,
        }
    step = max(1, max_len // 6)
    for start in range(0, len(text) - max_len + 1, step):
        window = text[start : start + max_len]
        if text.count(window) == 1 and len(window.strip()) >= min_len:
            return {
                "quoted_text": window,
                "char_start": start,
                "char_end": start + max_len,
                "quoted_sha256": sha256_text(window),
                "unique_in_body": True,
            }
    return None


def compact_row(full: dict, file_row_number: int) -> dict:
    row = {key: clean(value) for key, value in full.items() if key != "file_row_number"}
    body = canon(row)
    vulnerable = row.get("vulnerable_code") if isinstance(row.get("vulnerable_code"), str) else ""
    fixed = row.get("fixed_code") if isinstance(row.get("fixed_code"), str) else ""
    commit = row.get("commit_message") if isinstance(row.get("commit_message"), str) else ""
    description = row.get("cve_description")
    if not isinstance(description, str):
        description = json.dumps(description, ensure_ascii=False, default=str)
    return {
        "file_row_number": file_row_number,
        "cve_id": row["cve_id"],
        "fix_commit": row["hash"],
        "repo_url": row["repo_url"],
        "repository": repository(row["repo_url"]),
        "cwe_id": None if row.get("cwe_id") in {None, "nan"} else row.get("cwe_id"),
        "cwe_name": None if row.get("cwe_name") in {None, "nan"} else row.get("cwe_name"),
        "language": None if row.get("language") in {None, "nan"} else row.get("language"),
        "severity": None if row.get("severity") in {None, "nan"} else row.get("severity"),
        "file_paths": row.get("file_paths") if isinstance(row.get("file_paths"), list) else [],
        "security_keywords": row.get("security_keywords")
        if isinstance(row.get("security_keywords"), list)
        else [],
        "commit_message": commit[:400],
        "commit_message_sha256": sha256_text(commit) if commit else None,
        "cve_description": description[:500],
        "source_record_sha256": sha256_bytes(body),
        "normalized_source_sha256": sha256_bytes(re.sub(rb"\s+", b" ", body)),
        "vulnerable": {
            "present": bool(vulnerable),
            "utf8_bytes": len(vulnerable.encode("utf-8")) if vulnerable else 0,
            "sha256": sha256_text(vulnerable) if vulnerable else None,
            "quote": pick_quote(vulnerable),
        },
        "fixed": {
            "present": bool(fixed),
            "utf8_bytes": len(fixed.encode("utf-8")) if fixed else 0,
            "sha256": sha256_text(fixed) if fixed else None,
            "quote": pick_quote(fixed),
        },
    }


def read_row(connection, parquet: str, index: int) -> dict:
    cursor = connection.execute(
        "SELECT * FROM read_parquet(?, file_row_number=true) WHERE file_row_number = ?",
        [parquet, index],
    )
    names = [item[0] for item in cursor.description]
    values = cursor.fetchone()
    if values is None:
        raise SystemExit(f"missing parquet row {index}")
    return dict(zip(names, values))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parquet", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    parquet = Path(args.parquet)
    if parquet.stat().st_size != PARQUET_BYTES or file_sha256(parquet) != PARQUET_SHA256:
        raise SystemExit("pinned CVE shard bytes or SHA-256 mismatch")
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    splits = json.loads(SPLITS.read_text(encoding="utf-8"))
    cve_records = [row for row in sources["source_records"] if row["population"] == "cve"]
    assignments = {
        row["source_id"]: row for row in splits["assignments"] if row["population"] == "cve"
    }
    if len(cve_records) != 12 or len(assignments) != 12:
        raise SystemExit("expected 12 frozen CVE families")
    connection = duckdb.connect(
        ":memory:",
        config={"threads": "1", "memory_limit": "2GB", "preserve_insertion_order": "false"},
    )
    selected = []
    used_rows = set()
    try:
        for record in cve_records:
            index = record["source_locator"]["file_row_number"]
            used_rows.add(index)
            compact = compact_row(read_row(connection, str(parquet), index), index)
            if compact["source_record_sha256"] != record["source_record_sha256"]:
                raise SystemExit(f"row {index} source_record_sha256 mismatch")
            if compact["normalized_source_sha256"] != record["normalized_source_sha256"]:
                raise SystemExit(f"row {index} normalized_source_sha256 mismatch")
            if compact["cve_id"] != record["source_locator"]["cve_id"]:
                raise SystemExit(f"row {index} CVE identifier mismatch")
            if compact["fix_commit"] != record["source_locator"]["fix_commit"]:
                raise SystemExit(f"row {index} fix commit mismatch")
            if compact["repository"] != record["source_locator"]["repository"]:
                raise SystemExit(f"row {index} repository mismatch")
            assignment = assignments[record["source_id"]]
            selected.append(
                {
                    "source_id": record["source_id"],
                    "lineage_family_id": record["lineage_family_id"],
                    "split": assignment["split"],
                    "planned_case_ids": assignment["planned_case_ids"],
                    "row": compact,
                }
            )
        distractors = {}
        fallback = list(UNRELATED_FALLBACK_ROWS)
        for item in selected:
            index = item["row"]["file_row_number"]
            if index in SAME_REPO_DISTRACTORS:
                distractor_index = SAME_REPO_DISTRACTORS[index]
                relation = "same_repository_unselected_real_row"
            else:
                distractor_index = fallback.pop(0)
                relation = "unrelated_unselected_real_row"
            if distractor_index in used_rows:
                raise SystemExit(f"distractor row {distractor_index} collides with selected rows")
            compact = compact_row(
                read_row(connection, str(parquet), distractor_index),
                distractor_index,
            )
            if compact["cve_id"] in {item["row"]["cve_id"] for item in selected}:
                raise SystemExit("distractor reuses a selected empirical CVE identifier")
            distractors[item["source_id"]] = {
                "relation": relation,
                "parent_source_id": item["source_id"],
                "parent_lineage_family_id": item["lineage_family_id"],
                "row": compact,
            }
    finally:
        connection.close()
    payload = {
        "schema": "law-to-action-cve-row-evidence/v1",
        "task": "LA-006",
        "artifact": {
            "artifact_id": "cve-first-shard",
            "source_uri": URI,
            "revision": REVISION,
            "sha256": PARQUET_SHA256,
            "size_bytes": PARQUET_BYTES,
            "redistribution": "retrieval_only",
        },
        "extraction": {
            "executed_source": False,
            "full_bodies_retained": False,
            "quoted_spans_and_hashes_only": True,
        },
        "selected_rows": selected,
        "distractors": distractors,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "extracted",
                "selected_rows": len(selected),
                "distractors": len(distractors),
                "parquet_sha256": PARQUET_SHA256,
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

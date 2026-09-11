#!/usr/bin/env python3
"""Reconcile the bounded LA-004 source manifest without fetching source bodies.

The manifest deliberately contains identifiers, locations, hashes, lineage, and
permission decisions, but no third-party source text or code.  This makes the
recount hermetic and makes a missing local corpus an explicit state rather than
an accidental zero or a license-violating vendored copy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


SALT = "vericodegen-2026-law-to-action-LA003-v2"
POPULATION_QUOTAS = {
    "legal": {"development": 2, "calibration": 1, "final": 3},
    "cve": {"development": 2, "calibration": 3, "final": 7},
    "skill": {"development": 2, "calibration": 2, "final": 8},
}
SPLIT_ORDER = ("development", "calibration", "final")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def fail(message: str) -> None:
    raise ValueError(message)


def rank(population: str, family_id: str) -> str:
    return digest([SALT, population, family_id])


def expected_assignments(records: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    families: dict[str, list[str]] = {name: [] for name in POPULATION_QUOTAS}
    for record in records:
        population, family = record["population"], record["lineage_family_id"]
        if population not in families:
            fail(f"unknown population: {population}")
        if family not in families[population]:
            families[population].append(family)
    result: dict[str, dict[str, str]] = {}
    for population, ids in families.items():
        quota = POPULATION_QUOTAS[population]
        if len(ids) != sum(quota.values()):
            fail(f"{population}: expected {sum(quota.values())} families, got {len(ids)}")
        ordered = sorted((rank(population, family), family) for family in ids)
        cursor = 0
        for split in SPLIT_ORDER:
            for ranked, family in ordered[cursor:cursor + quota[split]]:
                result[family] = {"split": split, "ranking_sha256": ranked}
            cursor += quota[split]
    return result


def reconcile(base: Path) -> dict[str, Any]:
    manifests = base / "manifests"
    sources = load_json(manifests / "sources.json")
    splits = load_json(manifests / "splits.json")
    declared = load_json(base / "corpus_counts.json")
    if sources.get("schema") != "law-to-action-source-manifest/v1":
        fail("unexpected sources manifest schema")
    if splits.get("schema") != "law-to-action-splits/v1":
        fail("unexpected split manifest schema")
    if declared.get("schema") != "law-to-action-corpus-counts/v1":
        fail("unexpected count manifest schema")
    records = sources.get("source_records")
    assignments = splits.get("assignments")
    artifacts = sources.get("source_artifacts")
    if not isinstance(records, list) or not isinstance(assignments, list) or not isinstance(artifacts, list):
        fail("manifests must contain source_records, source_artifacts, and assignments arrays")
    source_ids = [row.get("source_id") for row in records]
    family_ids = [row.get("lineage_family_id") for row in records]
    if any(not isinstance(value, str) or not value for value in source_ids + family_ids):
        fail("every source and family identity must be nonempty text")
    if len(set(source_ids)) != len(source_ids) or len(set(family_ids)) != len(family_ids):
        fail("source and lineage-family identities must be unique")
    artifact_ids = {row.get("artifact_id") for row in artifacts}
    if len(artifact_ids) != len(artifacts) or not all(isinstance(value, str) and value for value in artifact_ids):
        fail("source artifact identities must be unique nonempty text")
    for artifact in artifacts:
        integrity = artifact.get("integrity")
        if not isinstance(integrity, dict) or not isinstance(integrity.get("sha256"), str) or len(integrity["sha256"]) != 64:
            fail(f"{artifact.get('artifact_id')}: missing SHA-256")
        rights = artifact.get("redistribution")
        if not isinstance(rights, dict) or rights.get("status") not in {"permitted", "retrieval_only"}:
            fail(f"{artifact.get('artifact_id')}: permission decision is missing")
        if rights["status"] == "retrieval_only" and not isinstance(rights.get("retrieval_instructions"), str):
            fail(f"{artifact.get('artifact_id')}: retrieval-only source lacks instructions")
    for row in records:
        if row.get("artifact_id") not in artifact_ids:
            fail(f"{row['source_id']}: unknown source artifact")
        if row.get("cohort_role") != "planned_not_evaluated":
            fail(f"{row['source_id']}: cannot mix evaluated and planned rows in this checkpoint")
        source_to_ir = row.get("source_to_ir")
        if not isinstance(source_to_ir, dict) or source_to_ir.get("status") != "planned_not_materialized":
            fail(f"{row['source_id']}: source-to-IR status is missing")
        parents = source_to_ir.get("planned_parent_ids")
        if not isinstance(parents, list) or len(parents) != 2 or len(set(parents)) != 2:
            fail(f"{row['source_id']}: expected exactly two distinct planned IR parents")
        if not all(isinstance(parent, str) and parent for parent in parents):
            fail(f"{row['source_id']}: invalid planned IR parent identity")
    expected = expected_assignments(records)
    if len(assignments) != len(records):
        fail("split manifest must assign every manifest source family exactly once")
    seen = set()
    for assignment in assignments:
        family = assignment.get("lineage_family_id")
        if family in seen or family not in expected:
            fail("split contains duplicate or unknown lineage family")
        seen.add(family)
        if assignment.get("split") != expected[family]["split"] or assignment.get("ranking_sha256") != expected[family]["ranking_sha256"]:
            fail(f"{family}: split is not the frozen deterministic assignment")
        matching = next(record for record in records if record["lineage_family_id"] == family)
        if assignment.get("source_id") != matching["source_id"]:
            fail(f"{family}: source identity mismatch")
        if assignment.get("planned_parent_ids") != matching["source_to_ir"]["planned_parent_ids"]:
            fail(f"{family}: source-to-IR parent identity mismatch")
    population_counts = Counter(row["population"] for row in records)
    split_counts = Counter((row["population"], expected[row["lineage_family_id"]]["split"]) for row in records)
    actual = {
        "source_artifacts": len(artifacts),
        "manifest_source_records": len(records),
        "unique_lineage_families": len(set(family_ids)),
        "planned_ir_parent_identities": sum(len(row["source_to_ir"]["planned_parent_ids"]) for row in records),
        "materialized_normalized_irs": 0,
        "evaluated_source_records": sum(row["cohort_role"] == "evaluated" for row in records),
        "stored_third_party_source_bytes": 0,
        "deferred_from_evaluation": len(records),
        "by_population": dict(sorted(population_counts.items())),
        "by_population_split": {
            population: {split: split_counts[(population, split)] for split in SPLIT_ORDER}
            for population in POPULATION_QUOTAS
        },
    }
    if declared.get("reconciled_counts") != actual:
        fail("corpus_counts.json does not match the manifest recount")
    expected_drops = declared.get("deferred_or_unsupported")
    if not isinstance(expected_drops, list) or sum(item.get("record_count", -1) for item in expected_drops) != len(records):
        fail("deferred/unsupported rows must account for every planned source record")
    return actual


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-dir", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    actual = reconcile(args.benchmark_dir.resolve())
    print("LA-004 source recount: PASS")
    print(json.dumps(actual, sort_keys=True))
    print("No source row is evaluated: the fixed-action and model studies remain unrun.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

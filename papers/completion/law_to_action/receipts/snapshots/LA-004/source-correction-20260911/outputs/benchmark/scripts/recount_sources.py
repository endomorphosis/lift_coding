#!/usr/bin/env python3
"""Hermetic recount of the source reservation; actual file checks are retained separately."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def recount(base):
    sources = json.loads((base / "manifests/sources.json").read_text())
    splits = json.loads((base / "manifests/splits.json").read_text())
    counts = json.loads((base / "corpus_counts.json").read_text())
    assert sources["schema"] == "law-to-action-source-manifest/v2"
    assert splits["schema"] == "law-to-action-splits/v2"
    assert counts["schema"] == "law-to-action-corpus-counts/v2"
    assert digest(sources) == counts["frozen_manifest_sha256"]
    assert digest(splits) == counts["frozen_split_sha256"]
    records, artifacts, assigned = sources["source_records"], sources["source_artifacts"], splits["assignments"]
    assert len(records) == len(assigned) == 30 and len(artifacts) == 8
    assert len({r["source_id"] for r in records}) == len({r["lineage_family_id"] for r in records}) == 30
    assert len({r["normalized_source_sha256"] for r in records}) == 30
    artifact_ids = {a["artifact_id"] for a in artifacts}
    assert len(artifact_ids) == 8
    for artifact in artifacts:
        assert len(artifact["sha256"]) == 64 and int(artifact["sha256"], 16) >= 0
        assert artifact["size_bytes"] > 0 and artifact["source_uri"].startswith("https://")
        assert artifact["redistribution"]["status"] == "retrieval_only"
        assert artifact["redistribution"]["included_bytes"] == 0 and artifact["redistribution"]["instructions"]
    assert Counter(r["population"] for r in records) == {"legal": 6, "cve": 12, "skill": 12}
    legal = [r for r in records if r["population"] == "legal"]
    assert len({r["artifact_id"] for r in legal}) == len({r["source_record_sha256"] for r in legal}) == 6
    assert len({r["source_locator"]["section"].split("-")[0] for r in legal}) == 6
    repositories = [tuple(r["ancestry_key"]) for r in records if r["population"] != "legal"]
    assert len(repositories) == len(set(repositories)) == 24
    for record in records:
        assert record["artifact_id"] in artifact_ids
        assert record["lineage_family_id"] == "family:" + digest(record["ancestry_key"])
        assert record["source_to_ir"]["source_parent_id"] == record["source_id"]
        assert record["source_to_ir"]["status"] == "planned_not_materialized"
        assert record["source_to_ir"]["materialized_ir_ids"] == []
        assert record["source_to_ir"]["planned_case_ids"] == [record["lineage_family_id"] + ":case-0", record["lineage_family_id"] + ":case-1"]
    quota = {"legal": [2, 1, 3], "cve": [2, 3, 7], "skill": [2, 2, 8]}
    split_order = ["development", "calibration", "final"]
    salt = "vericodegen-2026-law-to-action-LA003-v2"
    assert splits["quotas"] == quota and splits["salt"] == salt and splits["split_order"] == split_order
    expected = []
    for population, q in quota.items():
        rows = [r for r in records if r["population"] == population]
        rank = lambda r: hashlib.sha256(json.dumps([salt, population, r["lineage_family_id"]], ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        rows.sort(key=lambda r: (rank(r), r["lineage_family_id"].encode()))
        offset = 0
        for split, amount in zip(split_order, q):
            for row in rows[offset:offset + amount]:
                expected.append({"population": population, "source_id": row["source_id"], "lineage_family_id": row["lineage_family_id"],
                    "split": split, "ranking_sha256": rank(row), "planned_case_ids": row["source_to_ir"]["planned_case_ids"]})
            offset += amount
    assert assigned == expected
    cohort = {"source_artifacts": 8, "source_records": 30, "reserved_source_families": 30, "planned_cases": 60,
        "materialized_normalized_IRs": 0, "checked_formalizations": 0, "evaluated_cases": 0,
        "source_tombstones_created": 0, "benchmark_index_rows": 0, "redistributed_third_party_source_bytes": 0,
        "by_population": {"legal": 6, "cve": 12, "skill": 12},
        "by_population_split": {p: dict(zip(split_order, q)) for p, q in quota.items()}}
    assert counts["cohort"] == cohort
    assert counts["deferred_to_case_construction_and_independent_review"] == {"LA-005": 6, "LA-006": 12, "LA-007": 12}
    assert sources["evaluation_admission"]["admitted_cases"] == sources["evaluation_admission"]["independently_reviewed_labels"] == 0
    assert sources["evaluation_admission"]["pending_tasks"] == ["LA-005", "LA-006", "LA-007"]
    assert all(not counts["observed_source_counts"][pop]["release_total_reproduced"] for pop in ["cve", "skill"])
    return {"manifest_recount": "PASS", "cohort": cohort,
        "scope": "Hermetic manifest and ancestry-identity recount. Actual original-source file/row checks are a distinct retained build_source_cohort.py --check command. All experimental admission, independent labels and near-duplicate/fork review remain open."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-dir", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(recount(args.benchmark_dir)))


if __name__ == "__main__":
    main()

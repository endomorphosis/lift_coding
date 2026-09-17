"""Recover and hash public source records without emitting their bodies.

Requires DuckDB only for the actual pinned Parquet read. Source Markdown and
code are inert data. No task labels, experiments, model calls, or split outcomes
are inspected. This source freeze does not qualify the downstream gold labels.
"""
import argparse
import hashlib
import json
import math
import re
import sqlite3
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import duckdb

SALT = "vericodegen-2026-law-to-action-LA003-v2"
QUOTAS = {"legal": [2, 1, 3], "cve": [2, 3, 7], "skill": [2, 2, 8]}
SPLITS = ["development", "calibration", "final"]


def canon(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def file_sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        return {"__nonfinite_float__": "nan" if math.isnan(value) else "positive_infinity" if value > 0 else "negative_infinity"}
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


def repository(url):
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.rstrip("/").removesuffix(".git")
    if host == "github.com":
        path = "/" + "/".join(path.strip("/").split("/")[:2]).lower()
    if not host or path in {"", "/"}:
        raise ValueError("source repository identity is absent")
    return host + path


def make_artifact(identifier, cache_name, url, revision, expected_sha, expected_bytes, **extra):
    return {"artifact_id": identifier, "cache_relative_path": cache_name, "source_uri": url,
            "revision": revision, "sha256": expected_sha, "size_bytes": expected_bytes,
            "redistribution": {"status": "retrieval_only", "included_bytes": 0,
                "instructions": "Retrieve this exact URI, verify bytes and SHA-256, and retain the applicable upstream source terms. No source body is included in this paper artifact."}, **extra}


def source_record(population, identity, ancestry, artifact, locator, raw_sha, normalized_sha):
    family = "family:" + sha(canon(ancestry))
    source = population + ":" + sha(canon(identity))
    return {"source_id": source, "population": population, "lineage_family_id": family,
            "ancestry_key": ancestry, "artifact_id": artifact, "source_locator": locator,
            "source_record_sha256": raw_sha, "normalized_source_sha256": normalized_sha,
            "status": "source_frozen_case_construction_and_independent_review_pending",
            "source_to_ir": {"status": "planned_not_materialized", "source_parent_id": source,
                "planned_case_ids": [family + ":case-0", family + ":case-1"],
                "materialized_ir_ids": []},
            "label_review_task": {"legal": "LA-005", "cve": "LA-006", "skill": "LA-007"}[population]}


def build(cache, frozen_at):
    artifacts, records, observed = [], [], {}
    legal = json.loads((cache / "legal_source_checks.json").read_text())
    legal_sections = ["18-USC-1030", "5-USC-552a", "15-USC-6502", "17-USC-1201", "42-USC-1320d-6", "47-USC-222"]
    assert len(legal) == len(set(r["sha256"] for r in legal)) == 6
    for row, section in zip(legal, legal_sections):
        path = cache / "legal_raw" / (row["id"] + ".pdf")
        assert path.stat().st_size == row["size_bytes"] and file_sha(path) == row["sha256"]
        text = subprocess.run(["pdftotext", "-raw", str(path), "-"], check=True, capture_output=True).stdout.decode()
        normal = re.sub(r"\s+", " ", text)
        assert re.search(row["operative_pattern"], normal, re.I), "operative provision absent"
        assert sha(text.encode()) == row["text_sha256"] and sha(normal.encode()) == row["normalized_text_sha256"]
        artifacts.append(make_artifact(row["id"], str(path.relative_to(cache)), row["url"], "USCODE-2024:" + section,
            row["sha256"], row["size_bytes"], source_type="official_GovInfo_US_Code_section_PDF",
            scope="Entire section document is one atomic source family; adjacent page context is retained as context only. No provision is split into another family.",
            operative_text_present=True, applicability_review="LA-005 pending; presence is not a legal applicability judgment"))
        records.append(source_record("legal", [row["sha256"], section], ["official_legal_section", section], row["id"],
            {"section": section, "edition": "2024", "document_sha256": row["sha256"]}, row["sha256"], sha(normal.encode())))
    observed["legal"] = {"physically_read_documents": 6, "selected_document_families": 6,
        "selected_distinct_titles": 6, "rejected_previous_same_document_provision_families": 6}

    parquet = cache / "train-00000-of-00003.parquet"
    cve_sha = "2e25e84e85e1560d41acacbfc7eb359349f5417bc9bf31318cdf0c4aafccb7d1"
    assert parquet.stat().st_size == 211599861 and file_sha(parquet) == cve_sha
    artifacts.append(make_artifact("cve-first-shard", parquet.name,
        "https://huggingface.co/datasets/hitoshura25/cvefixes/resolve/d4f5c4ea65329d9ccbb8a3b3149e5d06eda5edb2/data/train-00000-of-00003.parquet",
        "d4f5c4ea65329d9ccbb8a3b3149e5d06eda5edb2", cve_sha, 211599861,
        source_type="verified_original_Parquet_shard", schema_version="pinned_CVEfixes_source_profile",
        rights_note="Dataset card declares Apache-2.0; actual upstream code licenses still govern later code redistribution."))
    con = duckdb.connect(":memory:", config={"threads": "1", "memory_limit": "512MB"})
    try:
        cursor = con.execute("SELECT cve_id, hash, repo_url, file_row_number FROM read_parquet(?, file_row_number=true) ORDER BY file_row_number", [str(parquet)])
        names = [d[0] for d in cursor.description]
        rows = [dict(zip(names, r)) for r in cursor.fetchall()]
    finally:
        con.close()
    assert len(rows) == 4329
    selected_repositories = set()
    selected_indices = []
    duplicate_repository_exclusions = 0
    for raw in rows:
        repo = repository(raw["repo_url"])
        if repo in selected_repositories:
            duplicate_repository_exclusions += 1
            continue
        selected_repositories.add(repo)
        index = raw["file_row_number"]
        # Read bodies only for this bounded selected row. An earlier all-column
        # full-shard ORDER BY exceeded 512MB and is retained as a failed attempt.
        connection = duckdb.connect(":memory:", config={"threads": "1", "memory_limit": "2GB", "preserve_insertion_order": "false"})
        try:
            cursor = connection.execute("SELECT * FROM read_parquet(?, file_row_number=true) WHERE file_row_number = ?", [str(parquet), index])
            names = [d[0] for d in cursor.description]
            full_row = dict(zip(names, cursor.fetchone()))
        finally:
            connection.close()
        row = {k: clean(v) for k, v in full_row.items() if k != "file_row_number"}
        body = canon(row)
        records.append(source_record("cve", [cve_sha, index, row["cve_id"], row["hash"]], ["repository", repo],
            "cve-first-shard", {"file_row_number": index, "cve_id": row["cve_id"], "fix_commit": row["hash"],
                "repository": repo}, sha(body), sha(re.sub(rb"\s+", b" ", body))))
        selected_indices.append(index)
        if len(selected_repositories) == 12:
            break
    assert len(selected_repositories) == 12
    observed["cve"] = {"physically_read_first_shard_rows": len(rows),
        "distinct_cve_ids_in_read_shard": len({r["cve_id"] for r in rows}),
        "distinct_cve_commit_locators_in_read_shard": len({(r["cve_id"], r["hash"]) for r in rows}),
        "selected_rows": 12, "selected_repository_families": 12,
        "selection": "Ascending physical row index; first row of each canonical repository, stopping at 12 distinct repository families. No label or outcome controls selection.",
        "same_repository_rows_skipped_before_quota": duplicate_repository_exclusions,
        "unselected_rows_in_read_shard": len(rows) - 12,
        "selection_examined_through_row_index": selected_indices[-1],
        "unread_other_shards": 2,
        "release_total_reproduced": False}
    del rows

    skill = cache / "skillcenter-security.sqlite"
    skill_sha = "8b763be5896b12510c38b92459325d9568770d99cf38aa53ab17485b456d82a4"
    assert skill.stat().st_size == 7892992 and file_sha(skill) == skill_sha
    artifacts.append(make_artifact("skill-security-bundle", skill.name,
        "https://huggingface.co/datasets/Tommysha/skillcenter-bundles/resolve/f9dd4fec3c86d85ebf116c7408ac5ce602c418a1/clawskills-bundle-lite-security-v20260227.sqlite",
        "f9dd4fec3c86d85ebf116c7408ac5ce602c418a1", skill_sha, 7892992,
        source_type="verified_original_SQLite_bundle", schema_version="skillcenter_sqlite_bundle_v1",
        rights_note="Packaging MIT does not grant rights to all individual sources. license_risk is source metadata, not independently established permission."))
    con = sqlite3.connect(skill.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    con.row_factory = sqlite3.Row
    try:
        index_count = con.execute("SELECT count(*) FROM skills_index").fetchone()[0]
        content_count = con.execute("SELECT count(*) FROM skills_content").fetchone()[0]
        total_meta = con.execute("SELECT value FROM bundle_meta WHERE key='total_skills'").fetchone()[0]
        rows = [dict(r) for r in con.execute("SELECT i.*, c.metadata_yaml, c.skill_md, c.library_md FROM skills_index i JOIN skills_content c USING(skill_id) ORDER BY i.skill_id")]
    finally:
        con.close()
    assert index_count == content_count == len(rows) == int(total_meta) == 1182
    source_keys, skill_repositories, body_hashes = set(), set(), set()
    skipped = Counter()
    for row in rows:
        if row["source_type"] != "github":
            skipped["non_repository_source"] += 1
            continue
        repo = repository(row["source_url"])
        source_key = row["primary_source_id"] or row["source_id"]
        normal_hash = sha(re.sub(r"\s+", " ", row["skill_md"]).encode())
        if repo in selected_repositories:
            skipped["cross_population_repository_overlap"] += 1
            continue
        if repo in skill_repositories or source_key in source_keys or normal_hash in body_hashes:
            skipped["duplicate_repository_primary_source_or_normalized_body"] += 1
            continue
        source_keys.add(source_key); skill_repositories.add(repo); body_hashes.add(normal_hash)
        records.append(source_record("skill", [skill_sha, row["skill_id"]], ["repository", repo],
            "skill-security-bundle", {"skill_id": row["skill_id"], "primary_source_id": source_key,
                "repository": repo, "source_url": row["source_url"]}, sha(canon(clean(row))), normal_hash))
        if len(skill_repositories) == 12:
            break
    assert len(skill_repositories) == 12 and not selected_repositories.intersection(skill_repositories)
    observed["skill"] = {"physically_read_index_rows": index_count, "physically_read_content_rows": content_count,
        "physical_join_rows": len(rows), "bundle_metadata_total_skills": int(total_meta),
        "selected_rows": 12, "selected_repository_families": 12,
        "selection": "Ascending skill_id; first distinct primary source, canonical repository and normalized body, excluding repositories already reserved by CVE, stopping at 12. No quality scores, labels, or outcomes control selection.",
        "exclusions_before_quota": dict(skipped), "unselected_rows_in_read_bundle": len(rows) - 12,
        "release_total_reproduced": False, "fts_internal_rows_are_not_source_counts": True}
    assert len(records) == len({r["lineage_family_id"] for r in records}) == 30
    assert len({r["normalized_source_sha256"] for r in records}) == 30
    assignments = []
    for pop, quotas in QUOTAS.items():
        ranked = sorted((sha(json.dumps([SALT, pop, r["lineage_family_id"]], ensure_ascii=False,
            separators=(",", ":")).encode()), r["lineage_family_id"].encode(), r) for r in records if r["population"] == pop)
        offset = 0
        for split, count in zip(SPLITS, quotas):
            for digest, _, record in ranked[offset:offset + count]:
                assignments.append({"population": pop, "source_id": record["source_id"],
                    "lineage_family_id": record["lineage_family_id"], "split": split,
                    "ranking_sha256": digest, "planned_case_ids": record["source_to_ir"]["planned_case_ids"]})
            offset += count
    sources = {"schema": "law-to-action-source-manifest/v2", "task": "LA-004", "frozen_at": frozen_at,
        "status": "verified_source_manifest_and_split_reservation_no_evaluated_cases",
        "selection_scope": "Six distinct official 2024 legal section documents in six titles, 12 repositories from the first pinned CVE shard, and 12 disjoint repositories from the pinned SkillCenter security bundle.",
        "source_record_hash_encoding": "Sorted compact UTF-8 JSON with ensure_ascii=False; nonfinite floats mapped to explicit __nonfinite_float__ objects. Legal records hash exact PDF bytes. Skill records hash joined index and content values. CVE file_row_number is an external locator and excluded from record content hash.",
        "source_artifacts": artifacts, "source_records": records,
        "evaluation_admission": {"admitted_cases": 0, "independently_reviewed_labels": 0,
            "pending_tasks": ["LA-005", "LA-006", "LA-007"],
            "requirements": ["Independent legal applicability, real CVE pair/controls, and skill/variant review remain mandatory.",
                "Cross-repository fork/alias and near-duplicate review, actual case ancestry, and all final sibling/patch/label leakage checks must pass before evaluation.",
                "Any ineligible reserved family is reported as a shortfall, never silently replaced; amendments must precede outcomes.",
                "Opaque IDs and conservative repository grouping establish this source reservation, not statistical independence of future observations."]}}
    splits = {"schema": "law-to-action-splits/v2", "salt": SALT, "quotas": QUOTAS,
        "split_order": SPLITS, "status": "reservation_only_no_case_labels_materialized",
        "atomicity": "Every source derivative, case, annotation, prompt, retrieval item, code patch and IR inherits its reserved original family split. Never split cases independently.",
        "assignments": assignments}
    counts = {"schema": "law-to-action-corpus-counts/v2", "observed_source_counts": observed,
        "cohort": {"source_artifacts": 8, "source_records": 30, "reserved_source_families": 30,
            "planned_cases": 60, "materialized_normalized_IRs": 0, "checked_formalizations": 0,
            "evaluated_cases": 0, "source_tombstones_created": 0, "benchmark_index_rows": 0,
            "redistributed_third_party_source_bytes": 0,
            "by_population": {"legal": 6, "cve": 12, "skill": 12},
            "by_population_split": {p: dict(zip(SPLITS, q)) for p, q in QUOTAS.items()}},
        "population_claim_limits": "Physical source reads and manifest reservations are separate from cases, IRs and experimental outcomes. Neither remaining CVE shards nor the full SkillCenter release was recounted. No release-wide, worldwide legal-coverage, or positive benchmark claim follows.",
        "deferred_to_case_construction_and_independent_review": {"LA-005": 6, "LA-006": 12, "LA-007": 12},
        "source_failures_preserved": ["Prior provider unbound CVE viewer slice and same-document legal family proposal retained as rejected draft.",
            "Prior SkillCenter wrong metadata column query failed, then corrected without source substitution."],
        "frozen_manifest_sha256": sha(canon(sources)), "frozen_split_sha256": sha(canon(splits))}
    return sources, splits, counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-cache", required=True, type=Path)
    parser.add_argument("--benchmark-dir", required=True, type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    dest = args.benchmark_dir
    src = dest / "manifests/sources.json"
    frozen = json.loads(src.read_text())["frozen_at"] if args.check else datetime.now(timezone.utc).isoformat()
    objects = build(args.source_cache, frozen)
    names = ["manifests/sources.json", "manifests/splits.json", "corpus_counts.json"]
    for name, obj in zip(names, objects):
        p = dest / name
        if args.check:
            assert json.loads(p.read_text()) == obj, "frozen source-derived object changed: " + name
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"source_validation": "PASS", "mode": "check" if args.check else "build",
        "duckdb_version": duckdb.__version__, "source_observations": objects[2]["observed_source_counts"],
        "cohort": objects[2]["cohort"], "no_code_or_labels_emitted": True}))


if __name__ == "__main__":
    main()

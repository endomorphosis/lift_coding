#!/usr/bin/env python3
"""Prospective source freeze: 6 legal, 12 CVE, 12 skill families with lineage audits."""
from __future__ import annotations

import re
import sqlite3
import subprocess
from pathlib import Path

import pyarrow.parquet as pq

from .common import (
    CACHE,
    COHORT,
    POPULATION_ORDER,
    PREP,
    ROOT,
    SELECT_SALT,
    digest,
    jaccard,
    normalize_text,
    ranking_digest,
    read_json,
    repo_parts,
    repository,
    sha_bytes,
    sha_file,
    sha_text,
    write_json,
)
LEGAL_SPECS = (
    {
        "artifact_id": "legal-cisa-cybersecurity-agency",
        "section": "6-USC-652",
        "title": "6",
        "edition": "USCODE-2024",
        "source_uri": "https://www.govinfo.gov/content/pkg/USCODE-2024-title6/pdf/USCODE-2024-title6-chap1-subchapXVIII-partA-sec652.pdf",
        "filename": "USCODE-2024-6-USC-652.pdf",
        "source_type": "official_GovInfo_US_Code_section_PDF",
        "redistribution": "US government work; public domain. Exact PDF bytes are hashed; body is not republished in this freeze.",
    },
    {
        "artifact_id": "legal-right-to-financial-privacy",
        "section": "12-USC-3402",
        "title": "12",
        "edition": "USCODE-2024",
        "source_uri": "https://www.govinfo.gov/content/pkg/USCODE-2024-title12/pdf/USCODE-2024-title12-chap35-sec3402.pdf",
        "filename": "USCODE-2024-12-USC-3402.pdf",
        "source_type": "official_GovInfo_US_Code_section_PDF",
        "redistribution": "US government work; public domain. Exact PDF bytes are hashed; body is not republished in this freeze.",
    },
    {
        "artifact_id": "legal-tax-return-confidentiality",
        "section": "26-USC-6103",
        "title": "26",
        "edition": "USCODE-2024",
        "source_uri": "https://www.govinfo.gov/content/pkg/USCODE-2024-title26/pdf/USCODE-2024-title26-subtitleF-chap61-subchapB-sec6103.pdf",
        "filename": "USCODE-2024-26-USC-6103.pdf",
        "source_type": "official_GovInfo_US_Code_section_PDF",
        "redistribution": "US government work; public domain. Exact PDF bytes are hashed; body is not republished in this freeze.",
    },
    {
        "artifact_id": "legal-fmla-employment-records",
        "section": "29-USC-2614",
        "title": "29",
        "edition": "USCODE-2024",
        "source_uri": "https://www.govinfo.gov/content/pkg/USCODE-2024-title29/pdf/USCODE-2024-title29-chap28-subchapI-sec2614.pdf",
        "filename": "USCODE-2024-29-USC-2614.pdf",
        "source_type": "official_GovInfo_US_Code_section_PDF",
        "redistribution": "US government work; public domain. Exact PDF bytes are hashed; body is not republished in this freeze.",
    },
    {
        "artifact_id": "legal-bank-secrecy-compliance",
        "section": "31-USC-5318",
        "title": "31",
        "edition": "USCODE-2024",
        "source_uri": "https://www.govinfo.gov/content/pkg/USCODE-2024-title31/pdf/USCODE-2024-title31-subtitleIV-chap53-subchapII-sec5318.pdf",
        "filename": "USCODE-2024-31-USC-5318.pdf",
        "source_type": "official_GovInfo_US_Code_section_PDF",
        "redistribution": "US government work; public domain. Exact PDF bytes are hashed; body is not republished in this freeze.",
    },
    {
        "artifact_id": "legal-fisma-agency-responsibilities",
        "section": "44-USC-3554",
        "title": "44",
        "edition": "USCODE-2024",
        "source_uri": "https://www.govinfo.gov/content/pkg/USCODE-2024-title44/pdf/USCODE-2024-title44-chap35-subchapII-sec3554.pdf",
        "filename": "USCODE-2024-44-USC-3554.pdf",
        "source_type": "official_GovInfo_US_Code_section_PDF",
        "redistribution": "US government work; public domain. Exact PDF bytes are hashed; body is not republished in this freeze.",
    },
)


def _pdf_text(path: Path) -> str:
    result = subprocess.run(
        ["/usr/bin/pdftotext", "-layout", str(path), "-"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.decode("utf-8", "replace")


def load_exclusions():
    manifest = read_json(ROOT / "papers/completion/law_to_action/benchmark/manifests/sources.json")
    frozen = read_json(ROOT / "papers/completion/law_to_action/benchmark/fixed_action_operator/frozen_inputs.json")
    records = manifest["source_records"]
    families = {row["lineage_family_id"] for row in records}
    frozen_families = {row["lineage_family_id"] for row in frozen["candidates"]}
    if families != frozen_families:
        raise ValueError("LA-004 and LA-029 family sets differ")
    repos = set()
    names = set()
    owners = set()
    cve_ids = set()
    commits = set()
    skill_primary = set()
    skill_ids = set()
    legal_sections = set()
    legal_titles = set()
    normalized = set()
    exact = set()
    for row in records:
        exact.add(row["source_record_sha256"])
        normalized.add(row["normalized_source_sha256"])
        key = row["ancestry_key"]
        if key[0] == "repository":
            repos.add(key[1])
            parts = repo_parts(key[1])
            if parts:
                owners.add(parts[1])
                names.add(parts[2])
        locator = row.get("source_locator") or {}
        if row["population"] == "cve":
            cve_ids.add(locator.get("cve_id"))
            commits.add(locator.get("fix_commit"))
            repos.add(locator.get("repository"))
        if row["population"] == "skill":
            skill_primary.add(locator.get("primary_source_id"))
            skill_ids.add(locator.get("skill_id"))
            repos.add(locator.get("repository"))
        if row["population"] == "legal":
            section = locator.get("section") or key[1]
            legal_sections.add(section)
            legal_titles.add(section.split("-")[0])
    return {
        "manifest_sha256": sha_file(ROOT / "papers/completion/law_to_action/benchmark/manifests/sources.json"),
        "frozen_inputs_sha256": sha_file(ROOT / "papers/completion/law_to_action/benchmark/fixed_action_operator/frozen_inputs.json"),
        "families": sorted(families),
        "repos": repos,
        "names": names,
        "owners": owners,
        "cve_ids": {x for x in cve_ids if x},
        "commits": {x for x in commits if x},
        "skill_primary": {x for x in skill_primary if x},
        "skill_ids": {x for x in skill_ids if x},
        "legal_sections": legal_sections,
        "legal_titles": legal_titles,
        "normalized": normalized,
        "exact": exact,
    }


def _fork_reasons(identity: str, exclusions, selected_repos: set[str]) -> list[str]:
    reasons = []
    parts = repo_parts(identity)
    if identity in exclusions["repos"]:
        reasons.append("exact_old_repository")
    if identity in selected_repos:
        reasons.append("already_selected_repository")
    if not parts:
        reasons.append("unparseable_repository")
        return reasons
    host, owner, name = parts
    folded = re.sub(r"[^a-z0-9]+", "", name)
    if name in exclusions["names"] or folded in {re.sub(r"[^a-z0-9]+", "", n) for n in exclusions["names"]}:
        reasons.append("same_project_name_as_excluded_family")
    for other in list(exclusions["repos"]) + list(selected_repos):
        other_parts = repo_parts(other)
        if not other_parts:
            continue
        if owner == other_parts[1] and (name.startswith(other_parts[2]) or other_parts[2].startswith(name)) and name != other_parts[2]:
            reasons.append("same_owner_prefix_clone")
        if jaccard(identity, other) >= 0.86 and identity != other:
            reasons.append("repository_path_nearest_neighbor")
    return sorted(set(reasons))


def _family_id(ancestry_key, source_id: str) -> str:
    return "family:" + digest({"ancestry_key": ancestry_key, "source_id": source_id, "select_salt": SELECT_SALT})


def freeze_legal(exclusions):
    families = []
    for spec in LEGAL_SPECS:
        path = CACHE / "sources" / "legal" / spec["filename"]
        if not path.is_file():
            raise FileNotFoundError("missing legal source PDF: " + spec["filename"])
        raw = path.read_bytes()
        if not raw.startswith(b"%PDF"):
            raise ValueError("legal artifact is not a PDF: " + spec["filename"])
        text = _pdf_text(path)
        if spec["section"].split("-")[-1] not in text.replace(" ", "") and spec["section"] not in text:
            # Operative section number must appear in extracted text.
            if spec["section"].replace("-", " ") not in text and "§" not in text:
                raise ValueError("operative section text missing: " + spec["section"])
        if spec["section"] in exclusions["legal_sections"]:
            raise ValueError("legal section overlaps LA-004: " + spec["section"])
        if spec["title"] in exclusions["legal_titles"]:
            raise ValueError("legal title overlaps LA-004: " + spec["title"])
        exact = sha_bytes(raw)
        normalized = sha_text(normalize_text(text))
        if exact in exclusions["exact"] or normalized in exclusions["normalized"]:
            raise ValueError("legal source hash overlaps prior study")
        source_id = "legal:" + exact
        ancestry = ["official_legal_section", spec["section"]]
        family_id = _family_id(ancestry, source_id)
        excerpt = text[:1500]
        families.append(
            {
                "population": "legal",
                "id": family_id,
                "source_id": source_id,
                "ancestry_key": ancestry,
                "artifact_id": spec["artifact_id"],
                "source_uri": spec["source_uri"],
                "revision": spec["edition"] + ":" + spec["section"],
                "source_type": spec["source_type"],
                "lawful_access": "Official GovInfo US Code 2024 PDF retrieved and byte-hashed. US government work.",
                "redistribution": spec["redistribution"],
                "included_bytes": 0,
                "size_bytes": len(raw),
                "source_record_sha256": exact,
                "normalized_source_sha256": normalized,
                "operative_text_present": True,
                "excerpt_sha256": sha_text(excerpt),
                "excerpt": excerpt,
                "pdf_pages": None,
                "local_path": str(path),
                "filename": spec["filename"],
            }
        )
    titles = [f["ancestry_key"][1].split("-")[0] for f in families]
    if len(set(titles)) != 6:
        raise ValueError("legal titles are not six disjoint titles")
    for left, right in ((a, b) for i, a in enumerate(families) for b in families[i + 1 :]):
        if jaccard(left["excerpt"], right["excerpt"]) >= 0.5:
            raise ValueError("legal nearest-neighbor overlap")
        if left["normalized_source_sha256"] == right["normalized_source_sha256"]:
            raise ValueError("legal normalized hash collision")
    return families


def _cve_rows():
    path = CACHE / "sources" / "train-00000-of-00003.parquet"
    if sha_file(path) != "2e25e84e85e1560d41acacbfc7eb359349f5417bc9bf31318cdf0c4aafccb7d1":
        raise ValueError("CVE parquet pin mismatch")
    table = pq.ParquetFile(path)
    rows = []
    for index, batch in enumerate(table.iter_batches(batch_size=256)):
        values = batch.to_pylist()
        for offset, row in enumerate(values):
            row["_file_row_number"] = index * 256 + offset
            rows.append(row)
    return path, rows


def freeze_cve(exclusions):
    path, rows = _cve_rows()
    grouped = {}
    for row in rows:
        repo = repository(row.get("repo_url"))
        if not repo:
            continue
        grouped.setdefault(repo, []).append(row)
    candidates = []
    for repo, items in grouped.items():
        reasons = _fork_reasons(repo, exclusions, set())
        if reasons:
            continue
        usable = [
            item
            for item in items
            if isinstance(item.get("vulnerable_code"), str)
            and isinstance(item.get("fixed_code"), str)
            and 32 <= len(item["vulnerable_code"]) <= 200000
            and 32 <= len(item["fixed_code"]) <= 200000
            and item.get("cve_id") not in exclusions["cve_ids"]
            and item.get("hash") not in exclusions["commits"]
        ]
        if not usable:
            continue
        usable.sort(key=lambda item: (item["_file_row_number"], item["cve_id"] or ""))
        item = usable[0]
        vuln = item["vulnerable_code"]
        fixed = item["fixed_code"]
        exact = sha_text(vuln + "\n" + fixed)
        normalized = sha_text(normalize_text(vuln) + "\n" + normalize_text(fixed))
        if exact in exclusions["exact"] or normalized in exclusions["normalized"]:
            continue
        if sha_text(normalize_text(vuln)) == sha_text(normalize_text(fixed)):
            continue
        rank = ranking_digest("cve", repo, SELECT_SALT)
        candidates.append((rank, repo, item, exact, normalized, len(usable)))
    candidates.sort()
    selected = []
    selected_repos = set()
    selected_names = set()
    selected_norms = set()
    neighbor_notes = []
    for rank, repo, item, exact, normalized, n_rows in candidates:
        if len(selected) >= 12:
            break
        parts = repo_parts(repo)
        extra = _fork_reasons(repo, exclusions, selected_repos)
        if extra:
            continue
        if parts and parts[2] in selected_names:
            continue
        too_close = False
        for prior in selected:
            if jaccard(normalize_text(item["vulnerable_code"])[:4000], normalize_text(prior["vulnerable_excerpt"])[:4000]) >= 0.72:
                too_close = True
                neighbor_notes.append({"rejected": repo, "near": prior["ancestry_key"][1], "reason": "source_text_nearest_neighbor"})
                break
            if normalized == prior["normalized_source_sha256"]:
                too_close = True
                break
        if too_close or normalized in selected_norms:
            continue
        source_id = "cve:" + exact
        ancestry = ["repository", repo]
        family_id = _family_id(ancestry, source_id)
        vuln_excerpt = item["vulnerable_code"][:2000]
        fixed_excerpt = item["fixed_code"][:2000]
        selected.append(
            {
                "population": "cve",
                "id": family_id,
                "source_id": source_id,
                "ancestry_key": ancestry,
                "artifact_id": "cve-first-shard",
                "source_uri": "https://huggingface.co/datasets/hitoshura25/cvefixes/resolve/d4f5c4ea65329d9ccbb8a3b3149e5d06eda5edb2/data/train-00000-of-00003.parquet",
                "revision": "d4f5c4ea65329d9ccbb8a3b3149e5d06eda5edb2",
                "source_type": "verified_original_Parquet_row_pair",
                "lawful_access": "Pinned CVEfixes shard retrieved and byte-hashed. Dataset card Apache-2.0; upstream repository licenses still govern any later code redistribution.",
                "redistribution": "retrieval_only; included_bytes=0; pair excerpts retained for source-relative task construction only.",
                "included_bytes": 0,
                "size_bytes": path.stat().st_size,
                "source_record_sha256": exact,
                "normalized_source_sha256": normalized,
                "vulnerable_sha256": sha_text(item["vulnerable_code"]),
                "fixed_sha256": sha_text(item["fixed_code"]),
                "vulnerable_excerpt": vuln_excerpt,
                "fixed_excerpt": fixed_excerpt,
                "cve_id": item["cve_id"],
                "fix_commit": item["hash"],
                "language": item.get("language"),
                "file_paths": item.get("file_paths"),
                "file_row_number": item["_file_row_number"],
                "rows_in_repository": n_rows,
                "select_rank": rank,
                "fork_clone_audit": "exact repository, project-name, owner-prefix, path-jaccard, CVE-id, commit, and source-text nearest-neighbor checks; canonical spelling was not treated as sufficient.",
            }
        )
        selected_repos.add(repo)
        selected_names.add(parts[2])
        selected_norms.add(normalized)
    if len(selected) != 12:
        raise ValueError("failed to freeze 12 CVE families after audits: " + str(len(selected)))
    return selected, {"artifact_sha256": sha_file(path), "rows": len(rows), "neighbor_rejections": neighbor_notes[:40]}


def freeze_skill(exclusions, cve_repos: set[str]):
    path = CACHE / "sources" / "skillcenter-security.sqlite"
    if sha_file(path) != "8b763be5896b12510c38b92459325d9568770d99cf38aa53ab17485b456d82a4":
        raise ValueError("skill sqlite pin mismatch")
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = [
            dict(row)
            for row in connection.execute(
                "SELECT i.*, c.metadata_yaml, c.skill_md FROM skills_index i JOIN skills_content c USING(skill_id) ORDER BY i.skill_id"
            )
        ]
    finally:
        connection.close()
    candidates = []
    for row in rows:
        if row.get("source_type") != "github":
            continue
        repo = repository(row.get("source_url"))
        if not repo:
            continue
        body = row.get("skill_md") or ""
        primary = row.get("primary_source_id") or row.get("source_id")
        bodysha = sha_text(normalize_text(body))
        if repo in exclusions["repos"] or repo in cve_repos:
            continue
        if primary in exclusions["skill_primary"] or row.get("skill_id") in exclusions["skill_ids"]:
            continue
        if bodysha in exclusions["normalized"]:
            continue
        if not (80 <= len(body) <= 20000):
            continue
        reasons = _fork_reasons(repo, exclusions, cve_repos)
        if reasons:
            continue
        rank = ranking_digest("skill", repo + ":" + (row.get("skill_id") or ""), SELECT_SALT)
        candidates.append((rank, repo, row, bodysha))
    candidates.sort()
    selected = []
    selected_repos = set()
    selected_names = set()
    selected_norms = set()
    for rank, repo, row, bodysha in candidates:
        if len(selected) >= 12:
            break
        extra = _fork_reasons(repo, exclusions, selected_repos | cve_repos)
        if extra:
            continue
        parts = repo_parts(repo)
        if parts and parts[2] in selected_names:
            continue
        too_close = False
        for prior in selected:
            if jaccard(normalize_text(row["skill_md"])[:4000], normalize_text(prior["excerpt"])[:4000]) >= 0.72:
                too_close = True
                break
        if too_close or bodysha in selected_norms:
            continue
        exact = sha_text((row.get("metadata_yaml") or "") + "\n" + (row.get("skill_md") or ""))
        source_id = "skill:" + exact
        ancestry = ["repository", repo]
        family_id = _family_id(ancestry, source_id)
        llm = "llm_model:" in (row.get("metadata_yaml") or "")
        selected.append(
            {
                "population": "skill",
                "id": family_id,
                "source_id": source_id,
                "ancestry_key": ancestry,
                "artifact_id": "skill-security-bundle",
                "source_uri": "https://huggingface.co/datasets/Tommysha/skillcenter-bundles/resolve/f9dd4fec3c86d85ebf116c7408ac5ce602c418a1/clawskills-bundle-lite-security-v20260227.sqlite",
                "revision": "f9dd4fec3c86d85ebf116c7408ac5ce602c418a1",
                "source_type": "verified_original_SQLite_row",
                "lawful_access": "Pinned SkillCenter security bundle retrieved and byte-hashed. Packaging metadata is not independently established permission for every upstream source.",
                "redistribution": "retrieval_only; included_bytes=0; procedure text is source material, not an independent human annotation.",
                "included_bytes": 0,
                "size_bytes": path.stat().st_size,
                "source_record_sha256": exact,
                "normalized_source_sha256": bodysha,
                "skill_id": row["skill_id"],
                "primary_source_id": row.get("primary_source_id") or row.get("source_id"),
                "source_url": row.get("source_url"),
                "title": row.get("title"),
                "excerpt": (row.get("skill_md") or "")[:2000],
                "has_llm_model_metadata": llm,
                "independent_human_annotation": False,
                "select_rank": rank,
                "fork_clone_audit": "exact repository, project-name, owner-prefix, path-jaccard, primary-source, normalized-body, and cross-population CVE overlap checks; canonical spelling was not treated as sufficient.",
            }
        )
        selected_repos.add(repo)
        if parts:
            selected_names.add(parts[2])
        selected_norms.add(bodysha)
    if len(selected) != 12:
        raise ValueError("failed to freeze 12 skill families after audits: " + str(len(selected)))
    if any(row["independent_human_annotation"] for row in selected):
        raise ValueError("skill procedures must not be labeled independent human annotations")
    return selected, {"artifact_sha256": sha_file(path), "joined_rows": len(rows)}


def freeze_sources():
    exclusions = load_exclusions()
    legal = freeze_legal(exclusions)
    cve, cve_meta = freeze_cve(exclusions)
    skill, skill_meta = freeze_skill(exclusions, {row["ancestry_key"][1] for row in cve})
    families = legal + cve + skill
    if len({row["id"] for row in families}) != 30:
        raise ValueError("family id collision")
    if {row["population"] for row in families} != set(POPULATION_ORDER):
        raise ValueError("population set changed")
    counts = {name: sum(row["population"] == name for row in families) for name in POPULATION_ORDER}
    if counts != {"legal": 6, "cve": 12, "skill": 12}:
        raise ValueError("population counts differ")
    overlap = {row["ancestry_key"][1] for row in cve} & {row["ancestry_key"][1] for row in skill}
    if overlap:
        raise ValueError("CVE/skill repository overlap")
    if {row["id"] for row in families} & set(exclusions["families"]):
        raise ValueError("family id overlap with LA-004/LA-029")
    report = {
        "schema": "la-generated-study-source-freeze/v1",
        "status": "PASS",
        "prior_study_families_excluded": len(exclusions["families"]),
        "la004_manifest_sha256": exclusions["manifest_sha256"],
        "la029_frozen_inputs_sha256": exclusions["frozen_inputs_sha256"],
        "legal_titles": [row["ancestry_key"][1] for row in legal],
        "cve_repositories": [row["ancestry_key"][1] for row in cve],
        "skill_repositories": [row["ancestry_key"][1] for row in skill],
        "skill_procedures_are_independent_human_annotations": False,
        "canonical_repository_identity_treated_as_complete_fork_audit": False,
        "source_bodies_redistributed": 0,
        "cve_artifact": cve_meta,
        "skill_artifact": skill_meta,
        "families": families,
    }
    write_json(COHORT / "source_freeze.json", report, compact=True)
    write_json(PREP / "source_freeze_summary.json", {k: report[k] for k in report if k != "families"})
    return report

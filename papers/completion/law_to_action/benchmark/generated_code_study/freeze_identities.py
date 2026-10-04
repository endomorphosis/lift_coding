#!/usr/bin/env python3
"""Prospective identity freeze for LA-032. Does not admit families or run models.

Rebuilds ranked SHA-256 splits, 900 case-arm-seed identities, 30 family batches,
and native dependency edges from the unadmitted candidate package. Final oracle
bodies are sealed. This is not scientific execution and does not complete LA-032.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
PREP = ROOT / "papers/revisions/law_study_preparation_20260914"
OLD = ROOT / ".worktrees/vericodegen-law_to_action-2026/papers/completion/law_to_action/benchmark/manifests/sources.json"
SALT = "vericodegen-2026-law-to-action-LA016-v1"
ARMS = ["A0", "A1", "A2", "A3", "A4"]
SEEDS = [104729, 104759, 104761]
QUOTAS = {"legal": (2, 1, 3), "cve": (2, 3, 7), "skill": (2, 2, 8)}
SPLIT_ORDER = ("development", "calibration", "final")
BATCH_TASKS = {
    "development": [f"LA-{n:03d}" for n in range(33, 39)],
    "calibration": [f"LA-{n:03d}" for n in range(39, 45)],
    "final": [f"LA-{n:03d}" for n in range(45, 63)],
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def ranking_sha256(population, lineage_family_id):
    encoded = json.dumps([SALT, population, lineage_family_id], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")


def load_json(path):
    return json.loads(Path(path).read_text())


def skill_lineage(family):
    key = ["repository", family["repository"]]
    return key, "family:" + digest(key)


def load_families():
    old = load_json(OLD)["source_records"]
    excluded_keys = {tuple(row["ancestry_key"]) for row in old}
    excluded_ids = {row["lineage_family_id"] for row in old}
    legal = load_json(PREP / "legal_cve_proposal_v2/legal_candidates.json")
    cve = load_json(PREP / "legal_cve_proposal_v2/cve_candidates.json")
    skill_manifest = load_json(PREP / "skill_candidates_v1/source_manifest.json")
    skill_specs = load_json(PREP / "skill_candidates_v1/paired_case_specifications.json")
    skill_cases = {family["family_id"]: family for family in skill_specs["families"]}
    families = []
    for population, blob in (("legal", legal), ("cve", cve)):
        for family in blob["families"]:
            key = tuple(family["ancestry_key"])
            fid = family["lineage_family_id"]
            if key in excluded_keys or fid in excluded_ids:
                raise ValueError("Candidate overlaps LA-004/LA-029 family: " + fid)
            if family.get("scientific_admission") is not False:
                raise ValueError("Candidate already marked admitted: " + fid)
            if len(family["cases"]) != 2:
                raise ValueError("Family does not have two cases: " + fid)
            families.append({
                "population": population,
                "lineage_family_id": fid,
                "preparation_family_id": fid,
                "ancestry_key": list(key),
                "operation": family.get("operation") or family.get("title"),
                "scientific_admission": False,
                "admission_gaps": list(family.get("admission_gaps") or []),
                "cases": family["cases"],
            })
    sys.path.insert(0, str(PREP))
    import skill_oracles
    for family in skill_manifest["families"]:
        key, fid = skill_lineage(family)
        if tuple(key) in excluded_keys or fid in excluded_ids:
            raise ValueError("Skill candidate overlaps LA-004/LA-029 family: " + fid)
        spec = skill_cases[family["family_id"]]
        if len(spec["cases"]) != 2:
            raise ValueError("Skill family does not have two cases: " + fid)
        for index, case in enumerate(spec["cases"]):
            wanted = skill_oracles.expected({
                "task_key": spec["task_key"],
                "input": case["input"],
                "initial_state": case.get("initial_state", {}),
            })
            case["scheduler_case_id"] = fid + ":case-" + str(index)
            case["oracle_sha256"] = digest(wanted)
            case["oracle_body"] = wanted
        families.append({
            "population": "skill",
            "lineage_family_id": fid,
            "preparation_family_id": family["family_id"],
            "ancestry_key": key,
            "operation": spec["useful_work"],
            "scientific_admission": False,
            "admission_gaps": list(family.get("admission_gaps") or []),
            "cases": spec["cases"],
        })
    counts = Counter(item["population"] for item in families)
    if counts != {"legal": 6, "cve": 12, "skill": 12}:
        raise ValueError("Family counts differ from 6/12/12: " + str(dict(counts)))
    if len({item["lineage_family_id"] for item in families}) != 30:
        raise ValueError("Lineage family identities are not unique")
    return families, excluded_ids


def assign_splits(families):
    assigned = []
    for population, quota in QUOTAS.items():
        rows = [item for item in families if item["population"] == population]
        rows.sort(key=lambda item: (ranking_sha256(population, item["lineage_family_id"]),
                                    item["lineage_family_id"].encode()))
        offset = 0
        for split, amount in zip(SPLIT_ORDER, quota):
            for item in rows[offset:offset + amount]:
                item["split"] = split
                item["ranking_sha256"] = ranking_sha256(population, item["lineage_family_id"])
                assigned.append(item)
            offset += amount
    return assigned


def case_records(families):
    rows = []
    sealed = []
    unsealed = []
    for family in families:
        for index, case in enumerate(family["cases"]):
            if family["population"] == "skill":
                case_id = case["scheduler_case_id"]
                preparation_case_id = case["case_id"]
                oracle_sha = case["oracle_sha256"]
                oracle_body = case["oracle_body"]
                pair_role = case.get("case_kind")
                payload = case["input"]
            else:
                case_id = case["case_id"]
                preparation_case_id = case["case_id"]
                oracle_body = case["oracle"]
                oracle_sha = digest(oracle_body)
                pair_role = case.get("pair_role")
                payload = case["input_fixture"]
            expected = family["lineage_family_id"] + ":case-" + str(index)
            if case_id != expected:
                raise ValueError("Case identity is not source-relative: " + case_id)
            record = {
                "case_id": case_id,
                "preparation_case_id": preparation_case_id,
                "source_family": family["lineage_family_id"],
                "preparation_family_id": family["preparation_family_id"],
                "population": family["population"],
                "split": family["split"],
                "pair_role": pair_role,
                "oracle_sha256": oracle_sha,
                "payload_sha256": digest(payload),
                "scientific_admission": False,
            }
            rows.append(record)
            blob = dict(record)
            blob["oracle"] = oracle_body
            blob["payload"] = payload
            if family["split"] == "final":
                sealed.append(blob)
            else:
                unsealed.append(blob)
    if len(rows) != 60:
        raise ValueError("Expected 60 cases")
    return rows, unsealed, sealed


def build_schedule(cases):
    rows = []
    index = 0
    canonical_cases = sorted(cases, key=lambda item: item["case_id"].encode())
    for seed in SEEDS:
        rng = random.Random(seed)
        order = list(canonical_cases)
        rng.shuffle(order)
        arms = list(ARMS)
        rng.shuffle(arms)
        position_counts = {arm: [0] * 5 for arm in ARMS}
        for position, case in enumerate(order):
            rotated = arms[position % 5:] + arms[:position % 5]
            for arm in rotated:
                position_counts[arm][position % 5] += 1
                identity = case["case_id"] + "/" + arm + "/" + str(seed)
                rows.append({
                    "index": index,
                    "identity": identity,
                    "case_id": case["case_id"],
                    "source_family": case["source_family"],
                    "population": case["population"],
                    "split": case["split"],
                    "arm": arm,
                    "seed": seed,
                    "position": position,
                    "executed": False,
                })
                index += 1
        for arm in ARMS:
            if position_counts[arm] != [12, 12, 12, 12, 12]:
                raise ValueError("Arm position balance failed for seed %s arm %s: %s" % (seed, arm, position_counts[arm]))
    if len(rows) != 900 or len({row["identity"] for row in rows}) != 900:
        raise ValueError("Schedule is not 900 unique identities")
    counts = Counter(row["split"] for row in rows)
    if counts != {"development": 180, "calibration": 180, "final": 540}:
        raise ValueError("Split cell counts differ: " + str(dict(counts)))
    return rows


def build_batches(families, schedule):
    batches = []
    cells_by_family = {}
    for row in schedule:
        cells_by_family.setdefault(row["source_family"], []).append(row["identity"])
    for split, tasks in BATCH_TASKS.items():
        group = [item for item in families if item["split"] == split]
        group.sort(key=lambda item: (item["ranking_sha256"], item["lineage_family_id"].encode()))
        if len(group) != len(tasks):
            raise ValueError("Phase family count differs from batch tasks: " + split)
        prior = None
        for slot, (family, task_id) in enumerate(zip(group, tasks), start=1):
            identities = cells_by_family[family["lineage_family_id"]]
            if len(identities) != 30 or len(set(identities)) != 30:
                raise ValueError("Family batch is not 30 unique cells: " + family["lineage_family_id"])
            depends_on = ["LA-032"]
            if prior:
                depends_on.append(prior)
            if split == "final":
                depends_on.append("LA-063")
            batches.append({
                "task_id": task_id,
                "parent_task_id": "LA-031",
                "subgoal_id": "LA-G5",
                "phase": split,
                "phase_family_slot": slot,
                "source_family": family["lineage_family_id"],
                "preparation_family_id": family["preparation_family_id"],
                "population": family["population"],
                "ranking_sha256": family["ranking_sha256"],
                "paired_cases": 2,
                "planned_cells": 30,
                "cell_identities": identities,
                "depends_on": depends_on,
                "maximum_scientific_attempt_seconds": 3600,
                "runtime_seconds": 7200,
                "scientific_admission": False,
                "family_binding_status": "candidate_lineage_bound_not_scientifically_admitted",
            })
            prior = task_id
    if len(batches) != 30:
        raise ValueError("Expected 30 family batches")
    seen = [identity for batch in batches for identity in batch["cell_identities"]]
    if len(seen) != 900 or len(set(seen)) != 900:
        raise ValueError("Family batches are not a disjoint cover of 900 identities")
    return batches


def dependency_plan(batches):
    analysis = {
        "id": "LA-063",
        "parent_task_id": "LA-031",
        "subgoal_id": "LA-G5",
        "title": "Freeze generated-code analysis after development and calibration",
        "depends_on": ["LA-032"] + [batch["task_id"] for batch in batches if batch["phase"] != "final"],
        "scientific_inference_allowed": False,
        "final_material_release_allowed": False,
        "registered": False,
    }
    parent = {
        "task_id": "LA-031",
        "add_explicit_depends_on": ["LA-032"] + [batch["task_id"] for batch in batches] + ["LA-063"],
        "registered": False,
        "remaining_parent_role": "After all batch receipts and analysis freeze, verify all 900 identities. Do not mark complete from this freeze.",
    }
    return {
        "schema": "la-generated-study-native-dependencies/v1",
        "status": "PROPOSED_EDGES_NOT_REGISTERED",
        "preparation_task": "LA-032",
        "family_batch_tasks": batches,
        "analysis_freeze_task": analysis,
        "parent_dependency_update": parent,
        "native_tasks_registered": 0,
        "scientific_cells_executed": 0,
        "notes": "Edges are reviewable artifacts only. This file does not mutate the Quack board.",
    }


def main():
    families, excluded_ids = load_families()
    families = assign_splits(families)
    cases, unsealed, sealed = case_records(families)
    schedule = build_schedule(cases)
    public_families = [{
        "population": item["population"],
        "lineage_family_id": item["lineage_family_id"],
        "preparation_family_id": item["preparation_family_id"],
        "ancestry_key": item["ancestry_key"],
        "operation": item["operation"],
        "split": item["split"],
        "ranking_sha256": item["ranking_sha256"],
        "scientific_admission": False,
        "admission_gaps": item["admission_gaps"],
        "case_ids": [item["lineage_family_id"] + ":case-0", item["lineage_family_id"] + ":case-1"],
    } for item in families]
    batches = build_batches(families, schedule)
    now = datetime.now(timezone.utc).isoformat()
    study = {
        "schema": "la-generated-code-study-prospective-freeze/v1",
        "status": "IDENTITY_FREEZE_UNADMITTED",
        "created_at": now,
        "split_salt": SALT,
        "arms": ARMS,
        "seeds": SEEDS,
        "quotas": {key: list(value) for key, value in QUOTAS.items()},
        "families": public_families,
        "cases": cases,
        "schedule": schedule,
        "scientific_admitted_families": 0,
        "scientific_admitted_cases": 0,
        "scientific_cells_executed": 0,
        "planned_cells": 900,
        "model_calls": 0,
        "final_cohort_released": False,
        "scientific_splits_assigned": True,
        "splits_are_candidate_not_admitted": True,
        "historical_families_excluded": len(excluded_ids),
        "candidate_package": str(PREP.relative_to(ROOT)),
        "notes": "Ranked SHA-256 splits and 900 identities are frozen for engineering. Families remain unadmitted. Completing this freeze does not execute or claim the 900 scientific cells.",
    }
    write(HERE / "prospective_study.json", study)
    write(HERE / "schedule.json", {
        "schema": "la-generated-code-study-schedule/v1",
        "status": "IDENTITY_FREEZE_UNADMITTED",
        "split_salt": SALT,
        "planned_cells": 900,
        "scientific_cells_executed": 0,
        "identities": schedule,
    })
    write(HERE / "family_batches.json", {
        "schema": "la-generated-code-study-family-batches/v1",
        "status": "CANDIDATE_FAMILY_BOUND_NOT_ADMITTED",
        "batch_count": 30,
        "planned_cells": 900,
        "scientific_cells_executed": 0,
        "batches": batches,
    })
    write(HERE / "native_dependency_plan.json", dependency_plan(batches))
    write(HERE / "model_profile.json", {
        "schema": "la-qualified-local-model/v1",
        "status": "NOT_QUALIFIED",
        "scientific_model": False,
        "reason": "No docker0-bound exclusive host owner with wall_seconds=10000 and startup_seconds=360 has been evidenced from the pinned bridge worker. The live 127.0.0.1:8080 owner is unreachable to workers and is not this study's model pin.",
        "required_wall_seconds": 10000,
        "required_startup_seconds": 360,
        "exclusive_inference_owner": True,
        "bind": "docker0",
    })
    write(HERE / "cohort/ranked_splits.json", {
        "schema": "la-generated-code-study-ranked-splits/v1",
        "salt": SALT,
        "quotas": {key: list(value) for key, value in QUOTAS.items()},
        "split_order": list(SPLIT_ORDER),
        "scientific_admitted_families": 0,
        "assignments": [{
            "population": item["population"],
            "lineage_family_id": item["lineage_family_id"],
            "preparation_family_id": item["preparation_family_id"],
            "split": item["split"],
            "ranking_sha256": item["ranking_sha256"],
            "planned_case_ids": item["case_ids"],
        } for item in public_families],
    })
    write(HERE / "cohort/unsealed_development_calibration_cases.json", {
        "schema": "la-generated-code-study-unsealed-cases/v1",
        "status": "DEVELOPMENT_CALIBRATION_ONLY",
        "scientific_admission": False,
        "cases": unsealed,
    })
    sealed_manifest = {
        "schema": "la-generated-code-study-sealed-final-manifest/v1",
        "status": "SEALED",
        "release_allowed": False,
        "case_count": len(sealed),
        "cases": [{
            "case_id": item["case_id"],
            "source_family": item["source_family"],
            "oracle_sha256": item["oracle_sha256"],
            "payload_sha256": item["payload_sha256"],
        } for item in sealed],
    }
    write(HERE / "cohort/sealed_final_manifest.json", sealed_manifest)
    write(HERE / "cohort/sealed_final/oracles.json", {
        "schema": "la-generated-code-study-sealed-final-oracles/v1",
        "status": "SEALED_NOT_RELEASED_TO_INFERENCE",
        "release_allowed": False,
        "cases": sealed,
    })
    write(HERE / "preparation/source_pointer.json", {
        "schema": "la-generated-code-study-source-pointer/v1",
        "scientific_admitted_families": 0,
        "candidate_package": str(PREP.relative_to(ROOT)),
        "legal_candidates_sha256": sha(PREP / "legal_cve_proposal_v2/legal_candidates.json"),
        "cve_candidates_sha256": sha(PREP / "legal_cve_proposal_v2/cve_candidates.json"),
        "skill_manifest_sha256": sha(PREP / "skill_candidates_v1/source_manifest.json"),
        "skill_specifications_sha256": sha(PREP / "skill_candidates_v1/paired_case_specifications.json"),
        "historical_manifest_sha256": sha(OLD),
        "notes": "Bodies remain in the candidate package. This freeze binds identities, not scientific admission.",
    })
    print(json.dumps({
        "study": str((HERE / "prospective_study.json").relative_to(ROOT)),
        "families": 30,
        "cases": 60,
        "cells": 900,
        "scientific_admitted_families": 0,
        "scientific_cells_executed": 0,
        "split_cells": dict(Counter(row["split"] for row in schedule)),
        "sha256": sha(HERE / "prospective_study.json"),
    }, indent=2))


if __name__ == "__main__":
    main()

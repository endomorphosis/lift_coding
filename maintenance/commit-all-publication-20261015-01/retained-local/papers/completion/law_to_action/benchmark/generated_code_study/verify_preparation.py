#!/usr/bin/env python3
"""Read-only LA-032 preparation verifier. Fail closed. Never claims 900 cells executed."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter
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


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ranking_sha256(population, lineage_family_id):
    encoded = json.dumps([SALT, population, lineage_family_id], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def fail(failures, name, detail):
    failures.append({"check": name, "detail": detail})


def skill_lineage(family):
    key = ["repository", family["repository"]]
    return key, "family:" + digest(key)


def expected_identities(study):
    cases = sorted(study["cases"], key=lambda item: item["case_id"].encode())
    rows = []
    index = 0
    for seed in SEEDS:
        rng = random.Random(seed)
        order = list(cases)
        rng.shuffle(order)
        arms = list(ARMS)
        rng.shuffle(arms)
        for position, case in enumerate(order):
            rotated = arms[position % 5:] + arms[:position % 5]
            for arm in rotated:
                identity = case["case_id"] + "/" + arm + "/" + str(seed)
                rows.append((index, identity, case["case_id"], case["source_family"], case["split"], arm, seed, position))
                index += 1
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, default=HERE / "prospective_study.json")
    parser.add_argument("--require-scientific-cells-unexecuted", action="store_true")
    args = parser.parse_args()
    failures = []
    study = load(args.study)
    if study.get("schema") != "la-generated-code-study-prospective-freeze/v1":
        fail(failures, "schema", study.get("schema"))
    if study.get("scientific_cells_executed", 1) != 0:
        fail(failures, "scientific_zero_execution", study.get("scientific_cells_executed"))
    if study.get("model_calls", 1) != 0:
        fail(failures, "model_calls_nonzero", study.get("model_calls"))
    if study.get("final_cohort_released") is True:
        fail(failures, "final_released", True)
    if study.get("scientific_admitted_families") not in (0, 30):
        fail(failures, "admitted_count_shape", study.get("scientific_admitted_families"))
    if study.get("split_salt") != SALT:
        fail(failures, "split_salt", study.get("split_salt"))

    old = load(OLD)["source_records"]
    excluded = {row["lineage_family_id"] for row in old}
    excluded_keys = {tuple(row["ancestry_key"]) for row in old}
    legal = load(PREP / "legal_cve_proposal_v2/legal_candidates.json")
    cve = load(PREP / "legal_cve_proposal_v2/cve_candidates.json")
    skill_manifest = load(PREP / "skill_candidates_v1/source_manifest.json")
    if len(legal["families"]) != 6 or len(cve["families"]) != 12 or len(skill_manifest["families"]) != 12:
        fail(failures, "source_counts", (len(legal["families"]), len(cve["families"]), len(skill_manifest["families"])))

    expected_families = []
    for population, blob in (("legal", legal), ("cve", cve)):
        for family in blob["families"]:
            fid = family["lineage_family_id"]
            if fid in excluded or tuple(family["ancestry_key"]) in excluded_keys:
                fail(failures, "historical_overlap", fid)
            expected_families.append((population, fid, tuple(family["ancestry_key"])))
    for family in skill_manifest["families"]:
        key, fid = skill_lineage(family)
        if fid in excluded or tuple(key) in excluded_keys:
            fail(failures, "historical_overlap", fid)
        expected_families.append(("skill", fid, tuple(key)))
    if len(expected_families) != 30:
        fail(failures, "family_count", len(expected_families))

    freeze_ids = {(item["population"], item["lineage_family_id"]) for item in study["families"]}
    if freeze_ids != {(pop, fid) for pop, fid, _ in expected_families}:
        fail(failures, "family_identity_mismatch", sorted(freeze_ids.symmetric_difference({(p, i) for p, i, _ in expected_families})))

    recomputed = []
    for population, quota in QUOTAS.items():
        rows = [item for item in study["families"] if item["population"] == population]
        rows.sort(key=lambda item: (ranking_sha256(population, item["lineage_family_id"]), item["lineage_family_id"].encode()))
        offset = 0
        for split, amount in zip(SPLIT_ORDER, quota):
            for item in rows[offset:offset + amount]:
                digest_value = ranking_sha256(population, item["lineage_family_id"])
                if item["split"] != split or item["ranking_sha256"] != digest_value:
                    fail(failures, "ranked_split", item["lineage_family_id"])
                recomputed.append((item["lineage_family_id"], split))
            offset += amount
    if len(recomputed) != 30:
        fail(failures, "recomputed_split_count", len(recomputed))
    split_counts = Counter(item["split"] for item in study["families"])
    if split_counts != {"development": 6, "calibration": 6, "final": 18}:
        fail(failures, "family_split_counts", dict(split_counts))

    if len(study["cases"]) != 60 or len({case["case_id"] for case in study["cases"]}) != 60:
        fail(failures, "case_count", len(study["cases"]))
    for case in study["cases"]:
        if not case["case_id"].startswith(case["source_family"] + ":case-"):
            fail(failures, "source_relative_case", case["case_id"])
        if case.get("scientific_admission") is not False:
            fail(failures, "case_admitted", case["case_id"])

    expected = expected_identities(study)
    actual = [(row["index"], row["identity"], row["case_id"], row["source_family"], row["split"], row["arm"], row["seed"], row["position"])
              for row in study["schedule"]]
    if actual != expected:
        fail(failures, "schedule_recompute", "schedule identities differ from ranked protocol shuffle")
    if any(row.get("executed") for row in study["schedule"]):
        fail(failures, "schedule_executed_flag", True)
    cell_counts = Counter(row["split"] for row in study["schedule"])
    if cell_counts != {"development": 180, "calibration": 180, "final": 540}:
        fail(failures, "cell_split_counts", dict(cell_counts))

    batches = load(HERE / "family_batches.json")["batches"]
    if len(batches) != 30:
        fail(failures, "batch_count", len(batches))
    seen = []
    for batch in batches:
        if len(batch["cell_identities"]) != 30:
            fail(failures, "batch_size", batch["task_id"])
        if "LA-032" not in batch["depends_on"]:
            fail(failures, "batch_depends_on_prep", batch["task_id"])
        if batch["phase"] == "final" and "LA-063" not in batch["depends_on"]:
            fail(failures, "final_depends_on_analysis", batch["task_id"])
        seen.extend(batch["cell_identities"])
    if len(seen) != 900 or len(set(seen)) != 900:
        fail(failures, "batch_cover", (len(seen), len(set(seen))))
    if set(seen) != {row["identity"] for row in study["schedule"]}:
        fail(failures, "batch_identity_set", "batches do not match schedule identities")

    plan = load(HERE / "native_dependency_plan.json")
    parent_deps = set(plan["parent_dependency_update"]["add_explicit_depends_on"])
    needed = {"LA-032", "LA-063"} | {batch["task_id"] for batch in batches}
    if parent_deps != needed:
        fail(failures, "parent_dependency_edges", sorted(parent_deps.symmetric_difference(needed)))
    if plan.get("native_tasks_registered") not in (0, None):
        fail(failures, "native_registration_claimed", plan.get("native_tasks_registered"))

    sealed = load(HERE / "cohort/sealed_final_manifest.json")
    if sealed.get("release_allowed") is True or sealed.get("status") != "SEALED":
        fail(failures, "final_seal", sealed.get("status"))
    if len(sealed["cases"]) != 36:
        fail(failures, "sealed_final_case_count", len(sealed["cases"]))
    unsealed = load(HERE / "cohort/unsealed_development_calibration_cases.json")
    if len(unsealed["cases"]) != 24:
        fail(failures, "unsealed_case_count", len(unsealed["cases"]))

    model = load(HERE / "model_profile.json")
    if model.get("scientific_model") is True:
        fail(failures, "permissive_model_profile", model.get("status"))

    probe = HERE / "qualification/driver_interruption_resume.json"
    if not probe.exists():
        fail(failures, "driver_probes_missing", str(probe))
    else:
        probe_report = load(probe)
        if probe_report.get("status") != "PASS" or probe_report.get("scientific_cells_executed") != 0:
            fail(failures, "driver_probes", probe_report.get("status"))
        if probe_report.get("model_calls") != 0:
            fail(failures, "driver_probe_model_calls", probe_report.get("model_calls"))

    if study.get("scientific_admitted_families") != 30:
        fail(failures, "families_not_scientifically_admitted", study.get("scientific_admitted_families"))
    if any(family.get("scientific_admission") for family in study["families"]):
        fail(failures, "family_admission_flag", True)
    handlers = HERE / "qualification/generated_program_handlers.json"
    if not handlers.exists():
        fail(failures, "generated_program_handler_qualification_missing", str(handlers))
    else:
        handler_report = load(handlers)
        if handler_report.get("status") != "PASS" or handler_report.get("la030_two_sink_profile_sufficient") is True:
            fail(failures, "generated_program_handler_qualification_incomplete", handler_report.get("status"))
        if handler_report.get("scientific_cells_executed") != 0:
            fail(failures, "handler_qualification_claimed_cells", handler_report.get("scientific_cells_executed"))
    if model.get("status") != "PASS":
        fail(failures, "runtime_model_qualification_incomplete", model.get("status"))

    if args.require_scientific_cells_unexecuted and study.get("scientific_cells_executed") != 0:
        fail(failures, "require_unexecuted", study.get("scientific_cells_executed"))

    identity_ok = not any(item["check"] in {
        "schema", "scientific_zero_execution", "model_calls_nonzero", "split_salt",
        "source_counts", "historical_overlap", "family_count", "family_identity_mismatch",
        "ranked_split", "family_split_counts", "case_count", "source_relative_case",
        "schedule_recompute", "cell_split_counts", "batch_count", "batch_size",
        "batch_cover", "batch_identity_set", "parent_dependency_edges", "final_seal",
        "sealed_final_case_count", "unsealed_case_count", "require_unexecuted",
    } for item in failures)
    readiness = not failures
    report = {
        "schema": "la-generated-code-study-preparation-verification/v1",
        "status": "PASS_READINESS" if readiness else "PREPARATION_INCOMPLETE",
        "identity_freeze": "PASS" if identity_ok else "FAIL",
        "scientific_admitted_families": study.get("scientific_admitted_families"),
        "scientific_admitted_cases": study.get("scientific_admitted_cases"),
        "scientific_cells_executed": study.get("scientific_cells_executed"),
        "planned_cells": 900,
        "model_calls": study.get("model_calls"),
        "final_cohort_released": study.get("final_cohort_released"),
        "native_tasks_registered": plan.get("native_tasks_registered"),
        "failures": failures,
        "study_sha256": sha(args.study),
        "verifier_sha256": sha(Path(__file__)),
        "notes": "Identity freeze may pass while readiness fails. This verifier does not execute or claim the 900 scientific cells.",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    if not readiness:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

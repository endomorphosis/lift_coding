#!/usr/bin/python3.12
"""Rewrite bulky freeze JSON as compact recipes without changing scientific identities."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from study_common import (  # noqa: E402
    STUDY,
    WEIGHT_RECIPE,
    decode_schedule_rows,
    load_json,
    sha_file,
    slim_batch_task,
    write_json,
    write_json_array_field,
    write_schedule,
)


def slim_discovery(document: dict) -> dict:
    slim = dict(document)
    for key in ("cve", "skill", "legal"):
        block = dict(slim.get(key) or {})
        inventory = block.pop("repository_inventory", None)
        if inventory is not None:
            block["repository_inventory_count"] = len(inventory)
            block["repository_inventory"] = "omitted_from_paper_artifact"
        slim[key] = block
    exclusions = dict(slim.get("exclusions") or {})
    families = exclusions.get("families")
    if isinstance(families, list):
        exclusions["families_count"] = len(families)
        exclusions["families"] = "see cohort/sources.json exclusions"
    slim["exclusions"] = exclusions
    slim["compacted"] = True
    return slim


def slim_stage_plan(document: dict) -> dict:
    tasks = document.get("family_batch_tasks") or []
    return {
        "schema": document.get("schema"),
        "status": document.get("status"),
        "superseded_by": "native_dependency_plan.json",
        "preparation_task": document.get("preparation_task", "LA-032"),
        "family_batch_count": document.get("family_batch_count", len(tasks)),
        "planned_cells": document.get("planned_cells", 900),
        "phase_cells": document.get("phase_cells"),
        "family_batch_task_ids": [task.get("id") for task in tasks],
        "scientific_cells_executed": 0,
        "final_cohort_released": False,
        "source_families_selected": document.get("source_families_selected", 30),
    }


def main() -> None:
    schedule_path = STUDY / "schedule.json"
    schedule = load_json(schedule_path)
    rows = decode_schedule_rows(schedule)
    schedule["attempt_ids"] = [row["attempt_id"] for row in rows]
    schedule.pop("schedule", None)
    schedule.pop("rows", None)
    schedule.pop("columns", None)
    schedule["encoding"] = "attempt-ids"
    write_schedule(schedule_path, schedule)

    batches_path = STUDY / "family_batches.json"
    batches = load_json(batches_path)
    for batch in batches["batches"]:
        batch.pop("cell_ids", None)
    write_json(batches_path, batches)

    deps_path = STUDY / "native_dependency_plan.json"
    deps = load_json(deps_path)
    deps["family_batch_tasks"] = [slim_batch_task(batch) for batch in deps["family_batch_tasks"]]
    deps["cell_identities"] = "family_batches.json"
    write_json(deps_path, deps)

    sources_path = STUDY / "cohort" / "sources.json"
    sources = load_json(sources_path)
    for artifact in sources["source_artifacts"]:
        recorded = Path(artifact["cache_relative_path"])
        if artifact["artifact_id"].startswith("legal"):
            artifact["cache_relative_path"] = str(Path("legal") / recorded.name)
        else:
            artifact["cache_relative_path"] = recorded.name
    write_json(sources_path, sources)

    weights_path = STUDY / "qualification" / "model" / "service" / "weights.json"
    if weights_path.is_file():
        current = load_json(weights_path)
        recipe = dict(WEIGHT_RECIPE)
        recipe["seed"] = int(current.get("seed", WEIGHT_RECIPE["seed"]))
        recipe["hidden"] = int(current.get("hidden", WEIGHT_RECIPE["hidden"]))
        recipe["vocab"] = int(current.get("vocab", WEIGHT_RECIPE["vocab"]))
        write_json(weights_path, recipe)

    discovery_path = STUDY / "preparation" / "bootstrap_v1" / "local_source_discovery.json"
    if discovery_path.is_file():
        write_json(discovery_path, slim_discovery(load_json(discovery_path)))

    stage_path = STUDY / "preparation" / "bootstrap_v1" / "native_stage_plan.json"
    if stage_path.is_file():
        write_json(stage_path, slim_stage_plan(load_json(stage_path)))

    cases_path = STUDY / "cohort" / "cases.json"
    write_json_array_field(cases_path, load_json(cases_path), "cases")
    mappings_path = STUDY / "cohort" / "source_to_oracle_mappings.json"
    write_json_array_field(mappings_path, load_json(mappings_path), "mappings")
    sealed_path = STUDY / "cohort" / "sealed_final.json"
    sealed = load_json(sealed_path)
    write_json(sealed_path, sealed)
    cases = load_json(cases_path)["cases"]
    families = load_json(STUDY / "cohort" / "families.json")["families"]
    study_path = STUDY / "prospective_study.json"
    study = load_json(study_path)
    study["families"] = families
    study["case_ids"] = [case["id"] for case in cases]
    study["cases_path"] = "cohort/cases.json"
    study["schedule_path"] = "schedule.json"
    study.pop("cases", None)
    study.pop("schedule", None)

    model_profile_path = STUDY / "model_profile.json"
    model_profile = load_json(model_profile_path)
    model_profile["weights_sha256"] = sha_file(weights_path)
    write_json(model_profile_path, model_profile)

    identity = {
        "source_manifest_sha256": sha_file(sources_path),
        "model_profile_sha256": sha_file(model_profile_path),
        "runtime_profile_sha256": sha_file(STUDY / "qualification" / "runtime.json"),
        "prompt_profile_sha256": study["prompt_profile_sha256"],
        "oracle_manifest_sha256": sha_file(STUDY / "cohort" / "sealed_final.json"),
        "schedule_sha256": sha_file(schedule_path),
        "cohort_sha256": sha_file(STUDY / "cohort" / "cases.json"),
    }
    study.update(identity)
    study.pop("study_sha256", None)
    write_json(study_path, study)
    study["study_sha256"] = sha_file(study_path)
    write_json(study_path, study)

    summary_path = STUDY / "preparation" / "freeze_summary.json"
    summary = load_json(summary_path)
    summary["identity"] = identity | {"study_sha256": study["study_sha256"]}
    write_json(summary_path, summary)

    driver_path = STUDY / "qualification" / "driver" / "qualification.json"
    if driver_path.is_file():
        driver = load_json(driver_path)
        driver["identity"] = identity | {"study_sha256": study["study_sha256"]}
        write_json(driver_path, driver)

    model_q_path = STUDY / "qualification" / "model" / "qualification.json"
    if model_q_path.is_file():
        model_q = load_json(model_q_path)
        model_q["weights_sha256"] = model_profile["weights_sha256"]
        write_json(model_q_path, model_q)
        model_profile["qualification"] = {
            "path": "papers/completion/law_to_action/benchmark/generated_code_study/qualification/model/qualification.json",
            "sha256": sha_file(model_q_path),
        }
        write_json(model_profile_path, model_profile)
        identity["model_profile_sha256"] = sha_file(model_profile_path)
        study["model_profile_sha256"] = identity["model_profile_sha256"]
        study.pop("study_sha256", None)
        write_json(study_path, study)
        study["study_sha256"] = sha_file(study_path)
        write_json(study_path, study)
        summary["identity"] = identity | {"study_sha256": study["study_sha256"]}
        write_json(summary_path, summary)
        if driver_path.is_file():
            driver = load_json(driver_path)
            driver["identity"] = identity | {"study_sha256": study["study_sha256"]}
            write_json(driver_path, driver)

    print(
        {
            "status": "compacted",
            "study_sha256": study["study_sha256"],
            "schedule_bytes": schedule_path.stat().st_size,
            "study_bytes": study_path.stat().st_size,
            "weights_bytes": weights_path.stat().st_size,
            "discovery_bytes": discovery_path.stat().st_size if discovery_path.is_file() else 0,
            "deps_bytes": deps_path.stat().st_size,
        }
    )


if __name__ == "__main__":
    main()

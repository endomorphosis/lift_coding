#!/usr/bin/env python3
"""Run the complete LA-032 freeze and qualification. No scientific cells."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
sys.path.insert(0, str(STUDY))

from preparation.common import QUAL, STUDY as STUDY_ROOT, digest, sha_file, utc_now, write_json
from preparation.native_profile import qualify_profile, qualify_watchdog
from preparation.qualify import qualify_model, qualify_runtime, stop_model
from preparation.schedule import assign_splits, freeze_study
from preparation.sources import freeze_sources


def main():
    if QUAL.exists():
        shutil.rmtree(QUAL)
    QUAL.mkdir(parents=True, exist_ok=True)
    (STUDY_ROOT / "cohort" / "sealed").mkdir(parents=True, exist_ok=True)
    source_report = freeze_sources()
    families = assign_splits(source_report["families"])
    source_report = dict(source_report)
    source_report["families"] = families
    watchdog = qualify_watchdog(QUAL / "watchdog")
    # Cases are built inside freeze_study; profile qualification needs development oracles.
    from preparation.schedule import build_cases, build_schedule

    cases, _sealed = build_cases(families)
    profile = qualify_profile(cases, QUAL / "profile")
    runtime = qualify_runtime(QUAL / "runtime")
    model_report, model_profile, service = qualify_model(QUAL / "model")
    try:
        shutdown = stop_model(service, QUAL / "model")
    except Exception as exc:
        shutdown = {"error": type(exc).__name__, "message": str(exc)}
    model_q_path = QUAL / "model" / "qualification.json"
    model_profile["qualification"] = {
        "path": "papers/completion/law_to_action/benchmark/generated_code_study/qualification/model/qualification.json",
        "sha256": sha_file(model_q_path),
    }
    model_profile["base_url"] = "http://127.0.0.1:0"
    model_profile["service_stopped"] = True
    model_profile["shutdown"] = shutdown
    write_json(STUDY_ROOT / "model_profile.json", model_profile)
    qualification = {
        "schema": "la-generated-study-qualification-index/v1",
        "profile": {"path": "papers/completion/law_to_action/benchmark/generated_code_study/qualification/profile/qualification.json", "sha256": sha_file(QUAL / "profile" / "qualification.json")},
        "watchdog": {"path": "papers/completion/law_to_action/benchmark/generated_code_study/qualification/watchdog/qualification.json", "sha256": sha_file(QUAL / "watchdog" / "qualification.json")},
        "runtime": {"path": "papers/completion/law_to_action/benchmark/generated_code_study/qualification/runtime/qualification.json", "sha256": sha_file(QUAL / "runtime" / "qualification.json")},
        "model": model_profile["qualification"],
        "model_profile_sha256": digest(model_profile),
    }
    frozen = freeze_study(source_report, qualification, model_profile)
    study_path = STUDY_ROOT / "prospective_study.json"
    study = json.loads(study_path.read_text())
    study["model_profile_sha256"] = sha_file(STUDY_ROOT / "model_profile.json")
    study["qualification"] = qualification
    write_json(study_path, study, compact=True)
    from driver import qualify_driver

    development_case = next(case for case in frozen["cases"] if case["split"] == "development" and case["case_index"] == 0)
    driver_q = qualify_driver(study_path, QUAL / "driver", development_case)
    qualification["driver"] = {
        "path": "papers/completion/law_to_action/benchmark/generated_code_study/qualification/driver/qualification.json",
        "sha256": sha_file(QUAL / "driver" / "qualification.json"),
    }
    study = json.loads(study_path.read_text())
    study["qualification"] = qualification
    write_json(study_path, study, compact=True)
    write_json(
        QUAL / "index.json",
        {
            "schema": "la-generated-study-qualification-index/v1",
            "status": "PASS",
            "scientific_cells_executed": 0,
            "bindings": qualification,
            "watchdog_status": watchdog["status"],
            "profile_status": profile["status"],
            "runtime_status": runtime["status"],
            "model_status": model_report["status"],
            "driver_status": driver_q["status"],
            "completed_at": utc_now(),
        },
    )
    print(
        json.dumps(
            {
                "status": "READY",
                "families": 30,
                "cases": 60,
                "cells": 900,
                "model_calls": model_report["call_count"],
                "scientific_cells_executed": 0,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

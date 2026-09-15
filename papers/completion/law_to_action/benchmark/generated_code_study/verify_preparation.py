#!/usr/bin/env python3
"""Read-only verifier for the LA-032 prospective generated-code study freeze."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from preparation.common import (
    ARMS,
    CVE_BYTES,
    CVE_SHA,
    QUOTAS,
    SALT,
    SEEDS,
    SKILL_BYTES,
    SKILL_SHA,
    arm_position_counts,
    build_schedule,
    canonical_case_ids,
    expand_batch_cells,
    expand_schedule,
    load_exclusions,
    pdf_text,
    prompt_profile_sha256,
    ranking_sha256,
    read_json,
    schedule_identity_digest,
    sha_file,
)


def fail(message: str) -> None:
    raise SystemExit("LA-032 preparation verifier failed: " + message)


def verify(study_path: Path, require_unexecuted: bool = True) -> dict:
    study_path = Path(study_path)
    if not study_path.is_file():
        fail("missing prospective study")
    study = read_json(study_path)
    if study.get("schema") != "la-closed-loop-study/v1":
        fail("study schema differs")
    if study.get("split_salt") != SALT:
        fail("split salt differs")
    if study.get("mock") or study.get("availability_flag"):
        fail("mock mechanism or permissive availability flag")
    if study.get("la030_two_sink_substituted"):
        fail("LA-030 two-sink profile substituted for the study")
    families = study.get("families") or []
    cases = study.get("cases") or read_json(HERE / "cohort/cases.json")["cases"]
    schedule_doc = read_json(HERE / "schedule.json")
    schedule = study.get("schedule") if isinstance(study.get("schedule"), list) and study.get("schedule") and isinstance(study["schedule"][0], dict) else expand_schedule(schedule_doc)
    if len(families) != 30 or len(cases) != 60 or len(schedule) != 900:
        fail("reduced denominator")
    if study.get("schedule_identities_sha256") and study["schedule_identities_sha256"] != schedule_identity_digest(schedule):
        fail("study schedule identity digest differs")
    if schedule_doc.get("expanded_identities_sha256") and schedule_doc["expanded_identities_sha256"] != schedule_identity_digest(schedule):
        fail("schedule recipe digest differs")
    if study.get("arms") != list(ARMS) or study.get("seeds") != list(SEEDS):
        fail("arm/seed contract differs")
    pops = Counter(f["population"] for f in families)
    if dict(pops) != {"legal": 6, "cve": 12, "skill": 12}:
        fail("population family counts differ")
    for population, quotas in QUOTAS.items():
        ranked = sorted(
            (f for f in families if f["population"] == population),
            key=lambda f: (ranking_sha256(population, f["id"], SALT), f["id"].encode()),
        )
        expected = ["development"] * quotas[0] + ["calibration"] * quotas[1] + ["final"] * quotas[2]
        if [f["split"] for f in ranked] != expected:
            fail("ranked split assignment differs for " + population)
        for family in ranked:
            if family.get("ranking_sha256") != ranking_sha256(population, family["id"], SALT):
                fail("ranking hash differs")
    exclusions = load_exclusions()
    family_ids = {f["id"] for f in families}
    if family_ids & exclusions["families"]:
        fail("LA-004/LA-029 family overlap")
    if len(family_ids) != 30:
        fail("duplicate families")
    cache_pin = read_json(HERE / "preparation/cache_pin.json")
    cache = Path(cache_pin["path"])
    if not cache.is_dir():
        fail("missing source cache")
    parquet = cache / "train-00000-of-00003.parquet"
    sqlite = cache / "skillcenter-security.sqlite"
    if not parquet.is_file() or parquet.stat().st_size != CVE_BYTES or sha_file(parquet) != CVE_SHA:
        fail("CVE source bytes missing or hash mismatch")
    if not sqlite.is_file() or sqlite.stat().st_size != SKILL_BYTES or sha_file(sqlite) != SKILL_SHA:
        fail("skill source bytes missing or hash mismatch")
    for stem, expected in cache_pin["legal"].items():
        path = cache / "legal_raw" / (stem + ".pdf")
        if not path.is_file() or sha_file(path) != expected:
            fail("legal source bytes missing or hash mismatch: " + stem)
        text = pdf_text(path)
        if len(text) < 100:
            fail("legal operative bytes absent: " + stem)
    manifest = read_json(HERE / "preparation/source_manifest.json")
    if len(manifest["source_records"]) != 30:
        fail("source record count differs")
    for rec in manifest["source_records"]:
        if rec["lineage_family_id"] in exclusions["families"]:
            fail("manifest contains excluded family")
        if rec["population"] == "skill" and rec.get("independent_human_annotation") is not False:
            fail("skill procedure counted as human annotation")
        if rec["ancestry_key"][0] == "repository":
            if rec["ancestry_key"][1] in exclusions["repos"]:
                fail("excluded repository reused")
    lineage = read_json(HERE / "preparation/lineage_audit.json")
    if not lineage["cve"].get("canonical_identity_not_sole_fork_audit"):
        fail("CVE fork audit is canonical-id only")
    if not lineage["skill"].get("canonical_identity_not_sole_fork_audit"):
        fail("skill fork audit is canonical-id only")
    if lineage["skill"].get("counted_as_independent_human_annotation") != 0:
        fail("skill LLM procedures counted as human annotations")

    by_family = {f["id"]: f for f in families}
    if len(cases) != 60:
        fail("case count differs")
    for family in families:
        owned = [c for c in cases if c["source_family"] == family["id"]]
        if len(owned) != 2:
            fail("family pairing differs")
        for case in owned:
            if case.get("split") != family["split"]:
                fail("case did not inherit parent split")
            if case.get("constructed_development") is not False:
                fail("scientific case marked constructed")
            retrieval = case.get("retrieval") or []
            if not retrieval:
                fail("missing lineage-safe retrieval")
            for item in retrieval:
                if item.get("source_family") != family["id"] or item.get("contains_oracle") is not False:
                    fail("retrieval lineage/oracle contract failed")
                if item.get("contains_sibling_final_label") is not False or item.get("contains_target_patch") is not False:
                    fail("retrieval contains sibling labels or target patches")
            if not case.get("oracle_sha256"):
                fail("missing oracle identity")
            if family["split"] == "final":
                if case.get("expected_payload") is not None:
                    fail("final oracle material released before gate")
                if case.get("oracle_release_gate") != "LA-063":
                    fail("final oracle unsealed")
            else:
                if case.get("expected_payload") is None:
                    fail("development/calibration oracle missing")
    sealed = read_json(HERE / "cohort/sealed_final.json")
    if sealed.get("released_to_inference") is not False or sealed.get("gate") != "LA-063":
        fail("sealed-final status differs")
    final_ids = [c["id"] for c in cases if c["split"] == "final"]
    if set(final_ids) != set(sealed["oracles"]):
        fail("sealed oracle coverage differs")

    expected_ids = canonical_case_ids(families)
    rebuilt = build_schedule(expected_ids)
    actual = {(r["case_id"], r["arm"], r["seed"]) for r in schedule}
    expected = {(r["case_id"], r["arm"], r["seed"]) for r in rebuilt}
    if actual != expected:
        fail("900 identities differ from rebuilt schedule")
    if {r["attempt_id"] for r in schedule} != {r["attempt_id"] for r in rebuilt}:
        fail("attempt identities differ")
    positions = arm_position_counts(schedule)
    for seed, arms in positions.items():
        for arm, counts in arms.items():
            if counts != [12, 12, 12, 12, 12]:
                fail("arm-position balancing differs")

    batches = read_json(HERE / "family_batches.json")
    if batches.get("batch_count") != 30:
        fail("batch count differs")
    seen = []
    for batch in batches["batches"]:
        cells = expand_batch_cells(batch["cells"], schedule)
        if len(cells) != 30:
            fail("batch size differs")
        if batch.get("status") == "completed" or batch.get("scientific_cells_executed"):
            fail("future batch success registered")
        if batch.get("maximum_scientific_attempt_seconds") > 3600:
            fail("batch attempt allowance exceeds 3600")
        if batch.get("runtime_seconds") > 7200:
            fail("worker ceiling exceeded")
        for cell in cells:
            seen.append(cell["attempt_id"])
            if cell.get("scientific_executed"):
                fail("scientific cell claimed executed")
            if "original_schedule_index" not in cell:
                fail("original schedule mapping missing")
    if len(seen) != len(set(seen)) or set(seen) != {r["attempt_id"] for r in schedule}:
        fail("batches are not a disjoint cover of the 900 identities")
    phase_cells = Counter()
    for batch in batches["batches"]:
        phase_cells[batch["phase"]] += len(batch["cells"])
    if dict(phase_cells) != {"development": 180, "calibration": 180, "final": 540}:
        fail("phase cell quotas differ")
    if not batches.get("operational_ordering_amendment", {}).get("visible"):
        fail("operational ordering amendment is not visible")

    plan = read_json(HERE / "native_dependency_plan.json")
    if plan.get("registered_future_success") or plan.get("la031_completed"):
        fail("dependency plan registers future success or completes LA-031")
    batch_ids = [b["id"] for b in batches["batches"]]
    if [t["id"] for t in plan["family_batch_tasks"]] != batch_ids:
        fail("dependency plan batch identities differ")
    analysis = plan["analysis_freeze_task"]
    if analysis["id"] != "LA-063":
        fail("analysis freeze task identity differs")
    for batch in plan["family_batch_tasks"]:
        if "LA-032" not in batch["depends_on"]:
            fail("batch missing LA-032 dependency")
        if batch["phase"] == "final" and "LA-063" not in batch["depends_on"]:
            fail("final batch missing analysis-freeze dependency")
    needed = {"LA-032", *batch_ids, "LA-063"}
    if needed - set(plan["parent_dependency_update"]["explicit_depends_on"]):
        fail("LA-031 explicit dependencies incomplete")
    if not plan["edges"]:
        fail("native dependency edges missing")

    # generated_code_study parents: [0] benchmark [1] law_to_action [2] completion [3] papers [4] repo
    repo_root = HERE.parents[4]

    def bind(ref, schema_prefix=None):
        if not ref or "path" not in ref:
            fail("missing qualification binding")
        path = repo_root / ref["path"]
        if not path.is_file() or sha_file(path) != ref["sha256"]:
            fail("qualification artifact binding differs: " + ref["path"])
        body = read_json(path)
        if body.get("status") != "PASS":
            fail("qualification did not pass: " + ref["path"])
        if body.get("mock") or body.get("availability_flag"):
            fail("qualification used a mock or availability flag")
        return body

    model_q = bind(study["model_qualification"])
    if model_q.get("constructed_transport") is not False:
        fail("model qualification is constructed transport")
    if not model_q.get("actual_model_calls"):
        fail("no actual model calls")
    for call in model_q.get("calls") or []:
        if call.get("prompt_tokens") != call.get("preflight_input_count"):
            fail("prompt_tokens do not equal preflight input_count")
        if call.get("below_2048_only"):
            fail("token agreement reduced to a 2048 inequality")
    if not model_q.get("tokenization_agrees_with_usage"):
        fail("tokenization/usage agreement missing")
    profile_q = bind(study["profile_qualification"])
    if profile_q.get("la030_two_sink_substituted") or profile_q.get("la029_fixed_programs_substituted"):
        fail("profile qualification substituted prior programs")
    if set(profile_q.get("populations") or []) != {"cve", "legal", "skill"}:
        fail("profile not qualified across legal/CVE/skill")
    watchdog_q = bind(study["watchdog_qualification"])
    if watchdog_q.get("la030_v2_receipt_upgraded") or watchdog_q.get("oserror_broadly_suppressed"):
        fail("watchdog diagnostic upgraded the failed receipt or suppressed OSError")
    if not watchdog_q.get("new_implementation_retains_operation_path_errno"):
        fail("watchdog diagnostic missing operation/path/errno")
    driver_q = bind(study["driver_qualification"])
    if driver_q.get("configuration_flags_only") or not driver_q.get("actual_probes"):
        fail("driver qualification is flags-only")
    if not driver_q.get("interruption_resume") or not driver_q.get("one_time_capability"):
        fail("driver interruption/resume or capability probes missing")
    model_profile = read_json(HERE / "model_profile.json")
    if sha_file(HERE / "model_profile.json") != study.get("model_profile_sha256"):
        fail("model profile binding differs")
    for key in ("weights_sha256", "tokenizer_sha256", "chat_template_sha256", "deployment_sha256"):
        value = model_profile.get(key, "")
        if not isinstance(value, str) or len(value) != 64 or len(set(value)) == 1:
            fail("incomplete model pin: " + key)
    if study.get("prompt_profile_sha256") != prompt_profile_sha256():
        fail("prompt profile differs")
    if not study.get("independent_effect_oracle_frozen"):
        fail("oracles not frozen")
    executed = study.get("scientific_cells_executed")
    if require_unexecuted and executed != 0:
        fail("scientific cells claimed executed")
    if study.get("final_cells_dispatched"):
        fail("final cells dispatched during preparation")
    if any(row.get("scientific_executed") for row in schedule):
        fail("schedule claims scientific execution")
    mappings = read_json(HERE / "cohort/mappings.json")["mappings"]
    if len(mappings) != 60:
        fail("source-to-policy/task/oracle mappings incomplete")

    return {
        "status": "PASS",
        "families": 30,
        "cases": 60,
        "identities": 900,
        "batches": 30,
        "scientific_cells_executed": 0,
        "final_oracles_sealed": True,
        "model_calls_qualified": model_q.get("actual_model_calls"),
        "readiness_only": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--require-scientific-cells-unexecuted", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.study, args.require_scientific_cells_unexecuted), sort_keys=True, indent=2))


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print("LA-032 preparation verifier failed: " + str(exc), file=sys.stderr)
        raise SystemExit(1)

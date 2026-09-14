#!/usr/bin/python3.12
"""Read-only recomputation of the LA-032 prospective freeze. No scientific execution."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

def _study_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "prospective_study.json").is_file() and (candidate / "verify_preparation.py").is_file() and (candidate / "preparation").is_dir():
            return candidate
    raise SystemExit("generated_code_study root not found")


STUDY = _study_root(Path(__file__).resolve().parent)
ROOT = STUDY.parents[4]
BENCHMARK = STUDY.parent
sys.path.insert(0, str(STUDY / "preparation"))
from common import (  # noqa: E402
    ARMS,
    PROMPT_PROFILE,
    QUOTAS,
    SEEDS,
    SPLIT_ORDER,
    SPLIT_SALT,
    canonical,
    digest,
    load_json,
    ranking_sha256,
    require,
    sha256_file,
)

FORBIDDEN_FLAGS = (
    "availability_flag_permissive",
    "mock_mechanisms",
    "la030_two_sink_substituted",
    "la029_fixed_programs_substituted",
)


def fail(message: str) -> None:
    raise SystemExit("LA-032 preparation verifier: " + message)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def expand_identity(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        case_id = row["case_id"]
        seed = row["seed"]
        arm = row["arm"]
        expanded = {
            "attempt_id": row.get("attempt_id") or f"{seed}:{arm}:{case_id}",
            "schedule_index": row["schedule_index"],
            "seed": seed,
            "arm": arm,
            "case_id": case_id,
            "arm_position": row["arm_position"],
            "family_id": row.get("family_id") or case_id.rsplit(":case-", 1)[0],
        }
        return expanded
    schedule_index, seed, arm, arm_position, case_id = row
    return {
        "attempt_id": f"{seed}:{arm}:{case_id}",
        "schedule_index": schedule_index,
        "seed": seed,
        "arm": arm,
        "case_id": case_id,
        "arm_position": arm_position,
        "family_id": case_id.rsplit(":case-", 1)[0],
    }


def expected_schedule(case_ids: list[str]) -> list[dict[str, Any]]:
    schedule = []
    index = 0
    for seed in SEEDS:
        rng = random.Random(seed)
        shuffled_cases = list(case_ids)
        rng.shuffle(shuffled_cases)
        shuffled_arms = list(ARMS)
        rng.shuffle(shuffled_arms)
        for case_index, case_id in enumerate(shuffled_cases):
            rotate = case_index % len(ARMS)
            rotated = shuffled_arms[rotate:] + shuffled_arms[:rotate]
            for position, arm in enumerate(rotated):
                schedule.append({"attempt_id": f"{seed}:{arm}:{case_id}", "schedule_index": index, "seed": seed, "arm": arm, "case_id": case_id, "arm_position": position})
                index += 1
    return schedule


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--require-scientific-cells-unexecuted", action="store_true")
    args = parser.parse_args()
    study_path = args.study.resolve()
    study = load_json(study_path)
    sources = load_json(STUDY / "cohort" / "sources.json")
    splits = load_json(STUDY / "cohort" / "splits.json")
    cases = load_jsonl(STUDY / "cohort" / "cases.jsonl")
    schedule_doc = load_json(STUDY / "schedule.json")
    batches = load_json(STUDY / "family_batches.json")
    plan = load_json(STUDY / "native_dependency_plan.json")
    model_profile = load_json(STUDY / "model_profile.json")
    old_sources = load_json(BENCHMARK / "manifests" / "sources.json")
    old_frozen = load_json(BENCHMARK / "fixed_action_operator" / "frozen_inputs.json")
    old_families = {r["lineage_family_id"] for r in old_sources["source_records"]}
    old_families |= {c.get("lineage_family_id") for c in old_frozen.get("candidates", []) if c.get("lineage_family_id")}
    old_repos = {r["ancestry_key"][1] for r in old_sources["source_records"] if r["ancestry_key"][0] == "repository"}

    require(study.get("schema") == "la-closed-loop-study/v1", "study schema")
    require(study.get("split_salt") == SPLIT_SALT, "split salt")
    require(study.get("arms") == list(ARMS) and study.get("seeds") == list(SEEDS), "arms/seeds")
    families = study["families"]
    require(len(families) == 30, "30 families")
    require(len(cases) == 60, "60 cases")
    require(len(schedule_doc["identities"]) == 900, "900 identities")
    require(len(study["schedule"]) == 900, "study schedule")
    family_ids = {f["id"] for f in families}
    require(len(family_ids) == 30, "unique families")
    require(not (family_ids & old_families), "LA-004/LA-029 family overlap")
    require(sources.get("generated_skillcenter_procedures_are_human_annotations") is False, "skill procedures counted as human gold")
    require(sources.get("canonical_repository_identity_alone") is False, "fork audit reduced to canonical identity")
    require(sources.get("redistributed_third_party_source_bytes") == 0, "redistributed bodies")

    records = sources["source_records"]
    require(len(records) == 30, "source records")
    require(Counter(r["population"] for r in records) == {"legal": 6, "cve": 12, "skill": 12}, "population counts")
    for record in records:
        require(record["lineage_family_id"] == "family:" + digest(record["ancestry_key"]), "family id")
        require(record.get("lawful_access") is True, "lawful access")
        require(record.get("redistribution") == "retrieval_only", "redistribution")
        if record["population"] != "legal":
            require(record["ancestry_key"][1] not in old_repos, "repository overlap")
        artifact = next(a for a in sources["source_artifacts"] if a["artifact_id"] == record["artifact_id"])
        cache = Path(artifact["cache_path"])
        if not cache.is_file():
            fail("missing source artifact " + artifact["cache_path"])
        if sha256_file(cache) != artifact["sha256"] or cache.stat().st_size != artifact["size_bytes"]:
            fail("source artifact bytes changed: " + artifact["cache_path"])

    if splits.get("salt") != SPLIT_SALT:
        fail("splits salt")
    expected_assignments = []
    for population, quota in QUOTAS.items():
        rows = [r for r in records if r["population"] == population]
        rows.sort(key=lambda r: (ranking_sha256(population, r["lineage_family_id"]), r["lineage_family_id"].encode()))
        offset = 0
        for split, amount in zip(SPLIT_ORDER, quota):
            for row in rows[offset : offset + amount]:
                expected_assignments.append(
                    {
                        "population": population,
                        "source_id": row["source_id"],
                        "lineage_family_id": row["lineage_family_id"],
                        "split": split,
                        "ranking_sha256": ranking_sha256(population, row["lineage_family_id"]),
                        "planned_case_ids": [row["lineage_family_id"] + ":case-0", row["lineage_family_id"] + ":case-1"],
                    }
                )
            offset += amount
    if splits["assignments"] != expected_assignments:
        fail("ranked split assignments differ")
    split_by_family = {row["lineage_family_id"]: row["split"] for row in expected_assignments}
    for family in families:
        if family["split"] != split_by_family[family["id"]]:
            fail("family split does not match ranked rule")

    by_family_cases = Counter(c["source_family"] for c in cases)
    require(all(by_family_cases[fid] == 2 for fid in family_ids), "two cases per family")
    require(len({c["id"] for c in cases}) == 60, "unique cases")
    for case in cases:
        if case["split"] != split_by_family[case["source_family"]]:
            fail("case split does not inherit parent")
        retrieval = case["task"]["retrieval"]
        if not retrieval or any(item.get("source_family") != case["source_family"] for item in retrieval):
            fail("retrieval not bound to source lineage")
        if any(item.get("contains_oracle") is not False for item in retrieval):
            fail("hidden oracle in retrieval")
        if any(item.get("contains_sibling_final_label") is not False or item.get("contains_target_patch") is not False for item in retrieval):
            fail("sibling final label or target patch in retrieval")
        if case["split"] == "final":
            if not case.get("oracle", {}).get("sealed"):
                fail("final oracle not sealed")
        else:
            oracle = case.get("oracle") or {}
            if oracle.get("expected_payload") is None or oracle.get("independent_human_gold") is not False:
                fail("visible oracle incomplete")

    sealed = load_jsonl(STUDY / "cohort" / "sealed" / "final_oracles.jsonl")
    seal = load_json(STUDY / "cohort" / "sealed" / "SEAL.json")
    require(seal.get("released") is False, "final seal released")
    require(len(sealed) == 36, "sealed oracle count")
    require(study.get("final_material_released") is False, "final material released in study")

    rebuilt = expected_schedule([c["id"] for c in cases])
    actual = [
        {k: expand_identity(r)[k] for k in ("attempt_id", "schedule_index", "seed", "arm", "case_id", "arm_position")}
        for r in study["schedule"]
    ]
    if actual != rebuilt:
        fail("schedule identities differ from original ranked seed/arm rotation")
    if [expand_identity(r)["attempt_id"] for r in schedule_doc["identities"]] != [r["attempt_id"] for r in rebuilt]:
        fail("schedule.json identities differ")

    require(batches["batch_count"] == 30, "batch count")
    require(len(batches["batches"]) == 30, "batch list")
    require(batches["development_cells"] == 180 and batches["calibration_cells"] == 180 and batches["final_cells"] == 540, "phase cells")
    covered = []
    for batch in batches["batches"]:
        require(len(batch["cells"]) == 30, "batch size")
        require(batch["scientific_cells_executed"] == 0, "batch claimed executed")
        require(batch.get("maximum_scientific_attempt_seconds") == 3600, "batch allowance")
        cells = [expand_identity(cell) for cell in batch["cells"]]
        covered.extend(cell["attempt_id"] for cell in cells)
        families_in_batch = {cell["family_id"] for cell in cells}
        require(families_in_batch == {batch["family_id"]}, "batch not a single family")
    require(len(set(covered)) == 900 and len(covered) == 900, "disjoint batch coverage")
    require(len(batches["dispatch_order"]) == 30, "dispatch order")

    for name in FORBIDDEN_FLAGS:
        if study.get(name) is True:
            fail("permissive or mock flag set: " + name)
    if study.get("scientific_cells_executed") != 0 or study.get("scientific_execution_allowed") is True:
        fail("scientific execution claimed")
    if args.require_scientific_cells_unexecuted and study.get("scientific_cells_executed") != 0:
        fail("scientific cells executed")

    for key in ("development_qualification", "cohort_qualification", "runtime_qualification", "watchdog_qualification", "driver_qualification", "model_qualification"):
        ref = study[key]
        path = ROOT / ref["path"]
        if not path.is_file() or sha256_file(path) != ref["sha256"]:
            fail("qualification binding changed: " + key)
        payload = load_json(path)
        if payload.get("status") != "PASS":
            fail("qualification not PASS: " + key)
        if payload.get("scientific_cells_executed", 0) not in (0, None) and payload.get("scientific_cells_executed") != 0:
            fail("qualification executed scientific cells: " + key)

    model_q = load_json(ROOT / study["model_qualification"]["path"])
    if model_q.get("constructed_transport") is not False:
        fail("model qualification used constructed transport")
    if model_q.get("tokenization_agrees_with_usage") is not True:
        fail("prompt_tokens agreement missing")
    for call in model_q.get("calls") or []:
        if call.get("prompt_tokens") != call.get("input_count"):
            fail("prompt_tokens != preflight input_count")
    for key in ("weights_sha256", "tokenizer_sha256", "chat_template_sha256", "deployment_sha256", "model_revision"):
        if not model_profile.get(key) or len(str(model_profile[key])) < 16:
            fail("model pin missing: " + key)
        if model_q.get(key) and model_q[key] != model_profile[key] and key != "model_revision":
            fail("model profile/qualification pin mismatch: " + key)
    if model_profile.get("systemd_required") is True:
        fail("systemd required")
    watchdog_q = load_json(ROOT / study["watchdog_qualification"]["path"])
    if watchdog_q.get("historical_v2_receipt_upgraded") is True or watchdog_q.get("broad_oserror_suppressed") is True:
        fail("watchdog upgraded v2 or suppressed OSError")
    injected = watchdog_q.get("injected_raw_oserror") or {}
    if errno_values := injected.get("errno_observed"):
        if 2 not in errno_values:
            fail("watchdog diagnostic missing ENOENT")
    else:
        fail("watchdog diagnostic missing errno")
    if not injected.get("operations") or not injected.get("paths"):
        fail("watchdog diagnostic missing operation/path")
    driver_q = load_json(ROOT / study["driver_qualification"]["path"])
    for needed in ("interruption_resume", "stale_owner_reconciliation", "one_time_capability_consumption", "silent_replay_refused", "final_cells_not_dispatched"):
        if driver_q.get(needed) is not True:
            fail("driver probe missing: " + needed)
    if driver_q.get("configuration_flag_only") is True:
        fail("driver qualification was flags only")
    profile_q = load_json(ROOT / study["development_qualification"]["path"])
    if profile_q.get("la030_two_sink_profile_substituted") is True:
        fail("LA-030 profile substituted")
    if sorted(profile_q.get("populations_qualified") or []) != ["cve", "legal", "skill"]:
        fail("profile populations incomplete")
    deadline_q = load_json(ROOT / study["runtime_qualification"]["path"])
    if deadline_q.get("scientific_attempt_wall_seconds") != 120:
        fail("120-second bound missing")
    if deadline_q.get("maximum_model_calls") != 8 or deadline_q.get("maximum_output_tokens") != 1024:
        fail("token/call contract changed")

    if plan.get("source_families_selected") != 30 or plan.get("scientific_cells_executed") != 0:
        fail("dependency plan execution claim")
    if plan.get("la031_marked_complete") is True or plan.get("future_batch_success_registered") is True:
        fail("future success registered")
    bound = {task["id"]: task.get("family_binding") for task in plan["family_batch_tasks"]}
    if any(not str(v).startswith("family:") for v in bound.values()) or len(set(bound.values())) != 30:
        fail("family bindings incomplete")
    analysis_deps = set(plan["analysis_freeze_task"]["depends_on"])
    if not {"LA-032", *{f"LA-{n:03d}" for n in range(33, 45)}} <= analysis_deps:
        fail("analysis freeze dependencies")
    for task in plan["family_batch_tasks"]:
        if task["phase"] in {"development", "calibration"} and "LA-032" not in task["depends_on"]:
            fail("dev/cal missing LA-032 edge")
        if task["phase"] == "final" and "LA-063" not in task["depends_on"]:
            fail("final missing analysis-freeze edge")
        if task.get("registered_success") is True:
            fail("batch success pre-registered")
    la031_deps = set(plan["parent_dependency_update"]["add_explicit_depends_on"])
    needed = {"LA-032", "LA-063", *{f"LA-{n:03d}" for n in range(33, 63)}}
    if not needed <= la031_deps:
        fail("LA-031 explicit dependencies incomplete")

    visible_oracles = sum(1 for c in cases if c["split"] != "final" and c.get("oracle", {}).get("expected_payload"))
    if visible_oracles != 24:
        fail("development/calibration oracle completeness")
    if study.get("independent_effect_oracle_frozen") is not True:
        fail("oracle freeze missing")
    if study.get("prompt_profile_sha256") != digest(PROMPT_PROFILE):
        fail("prompt profile digest")
    if study.get("paid_provider_budget") != 0:
        fail("paid budget")

    print(
        json.dumps(
            {
                "status": "PASS",
                "families": 30,
                "cases": 60,
                "identities": 900,
                "batches": 30,
                "scientific_cells_executed": 0,
                "final_released": False,
                "readiness_only": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        fail(str(exc))

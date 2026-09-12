#!/usr/bin/python3.12
"""Validate LA-018 efficiency outputs against retained snapshot evidence."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
LIVE = ROOT / "papers" / "completion" / "law_to_action"
SNAP = Path(__file__).resolve().parent
SEED = 104729
CONDITIONS = ("cold", "warm", "stale_root", "stale_clock")
EXCLUSIVE_PHASES = (
    "retrieval",
    "compilation",
    "solver",
    "checker",
    "clock_root_check",
    "capability_verification",
    "database_transaction",
    "artifact_storage",
    "handler_effect",
)
TERMINAL = {
    "success",
    "denial",
    "abstention",
    "execution_failure",
    "timeout",
    "infrastructure_invalid",
    "not_started",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> int:
    live = LIVE / "results" / "efficiency"
    snap_out = SNAP / "outputs" / "results" / "efficiency"
    splits = load_json(LIVE / "benchmark" / "manifests" / "splits.json")
    development = [row for row in splits["assignments"] if row["split"] == "development"]
    planned = [case_id for family in development for case_id in family["planned_case_ids"]]
    require(len(development) == 6, f"expected 6 development families, found {len(development)}")
    require(len(planned) == 12, f"expected 12 development cases, found {len(planned)}")

    for name in ("raw.jsonl", "environment.json", "summary.json"):
        live_path = live / name
        snap_path = snap_out / name
        require(live_path.is_file(), f"missing live output {live_path}")
        require(snap_path.is_file(), f"missing snapshot output {snap_path}")
        require(live_path.read_bytes() == snap_path.read_bytes(), f"live/snapshot mismatch: {name}")

    records = load_jsonl(live / "raw.jsonl")
    environment = load_json(live / "environment.json")
    summary = load_json(live / "summary.json")
    require(len(records) == 48, f"raw.jsonl must contain 48 rows, found {len(records)}")
    require(summary["schema"] == "law-to-action-efficiency-summary/v1", "summary schema mismatch")
    require(summary["task"] == "LA-018", "summary task mismatch")
    require(environment["schema"] == "law-to-action-efficiency-environment/v1", "environment schema mismatch")
    require(environment["task"] == "LA-018", "environment task mismatch")
    require(summary["scheduled"] == 48, "summary scheduled is not 48")
    require(summary["executed"] == 48, "summary executed is not 48")
    require(summary["conditions"] == list(CONDITIONS), "condition list drifted")
    require(summary["exclusive_phases"] == list(EXCLUSIVE_PHASES), "exclusive phase list drifted")
    require(summary["reconciliation"]["all_rows_reconcile"] is True, "phase totals do not reconcile")
    require(summary["unobserved_not_filled"]["model_tokens_silently_filled"] is False, "model tokens were filled")
    require(summary["unobserved_not_filled"]["price_conversion_applied"] is False, "price conversion was applied")
    require(summary["cold_warm"]["warm_retrieval_always_hit"] is True, "warm retrieval was not a cache hit")
    require(summary["cold_warm"]["cold_retrieval_always_miss"] is True, "cold retrieval was not a miss")
    require(summary["cold_warm"]["warm_solver_always_hit"] is True, "warm solver was not a cache hit")
    require(summary["cold_warm"]["cold_solver_always_miss"] is True, "cold solver was not a miss")
    require(summary["cold_warm"]["utility_preserved_on_reuse"] is True, "warm reuse changed useful_work")
    require(summary["stale_invalidation"]["stale_root_invalidated_every_case"] is True, "stale-root did not invalidate")
    require(summary["stale_invalidation"]["stale_clock_invalidated_every_case"] is True, "stale-clock did not invalidate")
    require(summary["stale_invalidation"]["allowed_stale_root_useful_work"] == 0, "stale-root kept useful work")
    require(summary["stale_invalidation"]["allowed_stale_clock_useful_work"] == 0, "stale-clock kept useful work")
    require(summary["stale_invalidation"]["allowed_cold_useful_work"] >= 1, "no allowed cold useful work")
    require(
        summary["stale_invalidation"]["allowed_cold_useful_work"]
        == summary["stale_invalidation"]["allowed_warm_useful_work"],
        "cold/warm allowed useful work diverged",
    )
    require(summary["independent_human_gold"] is False, "human gold was claimed")
    require(environment["hardware"]["concurrency"]["maximum_parallel_attempts"] == 1, "concurrency is not 1")
    require(environment["path"] == "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin", "PATH is not the sealed validation PATH")
    require(environment["path_is_sealed"] is True, "path_is_sealed is not true")
    require(environment.get("authoritative_path") == environment["path"], "authoritative PATH drifted")
    require(environment["closed_loop_model_status"]["scientific_model_pinned"] is False, "model was marked pinned")
    require("logical_cpu_count_allowed" in environment["hardware"], "hardware cpu count missing")
    require(environment["hardware"].get("memory_total_bytes"), "hardware memory missing")

    expected_ids = {f"{SEED}:A4:{condition}:{case_id}" for case_id in planned for condition in CONDITIONS}
    got_ids = {row["attempt_id"] for row in records}
    require(got_ids == expected_ids, f"raw log does not cover the efficiency matrix: {sorted(expected_ids - got_ids)[:8]}")

    for row in records:
        require(row["schema"] == "law-to-action-efficiency-run/v1", f"{row['attempt_id']} schema mismatch")
        require(row["task"] == "LA-018", f"{row['attempt_id']} task mismatch")
        require(row["arm_id"] == "A4", f"{row['attempt_id']} arm is not A4")
        require(row["split"] == "development", f"{row['attempt_id']} is not development")
        require(row["condition"] in CONDITIONS, f"{row['attempt_id']} unknown condition")
        require(row["terminal_outcome"] in TERMINAL, f"{row['attempt_id']} unknown terminal")
        require(row["independent_human_gold"] is False, f"{row['attempt_id']} claimed human gold")
        require(row["concurrency"] == 1, f"{row['attempt_id']} concurrency is not 1")
        require(row["price_conversion"]["applied"] is False, f"{row['attempt_id']} applied a price")
        require(row["price_conversion"]["price_usd"] is None, f"{row['attempt_id']} filled a price")
        require(row["model"]["observed"] is False, f"{row['attempt_id']} marked model tokens observed")
        require(row["model"]["input_tokens"] is None, f"{row['attempt_id']} filled input tokens")
        require(row["model"]["output_tokens"] is None, f"{row['attempt_id']} filled output tokens")
        require(row["model"]["retry_tokens"] is None, f"{row['attempt_id']} filled retry tokens")
        require(row["model"]["silently_filled"] is False, f"{row['attempt_id']} silently filled tokens")
        require(row["network"]["observed"] is False, f"{row['attempt_id']} marked network observed")
        require(row["network"]["bytes_transferred"] is None, f"{row['attempt_id']} filled network bytes")
        require(row["retries"]["observed"] is True, f"{row['attempt_id']} retries not marked observed")
        require(row["retries"]["retry_count"] == 0, f"{row['attempt_id']} unexpected retries")
        require(set(row["phases"]) == set(EXCLUSIVE_PHASES), f"{row['attempt_id']} phase set drifted")
        exclusive = sum(row["phases"][name]["wall_seconds"] for name in EXCLUSIVE_PHASES)
        require(
            abs(exclusive - row["exclusive_phase_sum_seconds"]) < 1e-6,
            f"{row['attempt_id']} exclusive sum mismatch",
        )
        require(
            abs(row["end_to_end_wall_seconds"] - row["exclusive_phase_sum_seconds"] - row["overhead_seconds"]) < 1e-6,
            f"{row['attempt_id']} e2e does not reconcile",
        )
        require(row["end_to_end_wall_seconds"] >= 0, f"{row['attempt_id']} negative e2e")
        nested = row["nested_observations"]
        require(nested["solver_provider_elapsed_seconds"]["added_to_exclusive_sum"] is False, "nested solver added")
        require(nested["enforcement_dispatch_wall_seconds"]["added_to_exclusive_sum"] is False, "nested enforcer added")
        require(
            row["phases"]["retrieval"]["unavailable_upstream_body"]["bytes_transferred"] is None,
            f"{row['attempt_id']} filled upstream body bytes",
        )
        require(row["phases"]["retrieval"]["network_fetch"] is False, f"{row['attempt_id']} claimed a network fetch")

    by_case: dict[str, dict[str, dict]] = {}
    for row in records:
        by_case.setdefault(row["case_id"], {})[row["condition"]] = row
    require(set(by_case) == set(planned), "case coverage drifted")
    for case_id, group in by_case.items():
        require(set(group) == set(CONDITIONS), f"{case_id} missing a condition")
        cold, warm, stale_root, stale_clock = group["cold"], group["warm"], group["stale_root"], group["stale_clock"]
        require(cold["phases"]["retrieval"]["cache"] == "miss", f"{case_id} cold retrieval not miss")
        require(warm["phases"]["retrieval"]["cache"] == "hit", f"{case_id} warm retrieval not hit")
        require(cold["phases"]["solver"]["cache"] == "miss", f"{case_id} cold solver not miss")
        require(warm["phases"]["solver"]["cache"] == "hit", f"{case_id} warm solver not hit")
        require(cold["phases"]["compilation"]["cache"] == "miss", f"{case_id} cold compilation not miss")
        require(warm["phases"]["compilation"]["cache"] == "hit", f"{case_id} warm compilation not hit")
        require(stale_root["cache"]["invalidated_keys"], f"{case_id} stale_root did not drop cache keys")
        require(stale_clock["cache"]["invalidated_keys"], f"{case_id} stale_clock did not drop cache keys")
        require(stale_root["phases"]["clock_root_check"]["stale_evidence"] is True, f"{case_id} stale_root not flagged")
        require(stale_clock["phases"]["clock_root_check"]["stale_evidence"] is True, f"{case_id} stale_clock not flagged")
        require(stale_root["useful_work"] is False, f"{case_id} stale_root produced useful work")
        require(stale_clock["useful_work"] is False, f"{case_id} stale_clock produced useful work")
        require(cold["useful_work"] == warm["useful_work"], f"{case_id} warm changed useful_work")
        require(stale_root["phases"]["solver"]["cache"] == "miss", f"{case_id} stale_root solver reused stale cache")
        require(stale_clock["phases"]["solver"]["cache"] == "miss", f"{case_id} stale_clock solver reused stale cache")

    full_cost = summary["reconciliation"]["full_paper_cost_wall_seconds"]
    setup = summary["reconciliation"]["setup_qualification_wall_seconds"]
    e2e = summary["reconciliation"]["total_end_to_end_wall_seconds"]
    require(abs(full_cost - setup - e2e) < 1e-6, "full paper cost is not setup + e2e")
    require("Do not add exclusive phase sums on top of end-to-end walls." in summary["reconciliation"]["full_paper_cost_rule"], "cost rule missing")
    print("LA-018 efficiency validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

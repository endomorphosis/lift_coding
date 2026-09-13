#!/usr/bin/python3.12
"""Verify retained LA-029 operator-adoption evidence without scientific replay.

Reads already-imported hashes, the 900-cell matrix, resource/cost accounting,
and frozen operator sources. Does not run Docker, cell.py, controller execute,
run_slot, providers, models, store reset, or any scientific retry.
"""
from __future__ import annotations

import ast
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
LIVE = ROOT / "papers" / "completion" / "law_to_action"
SNAP = Path(__file__).resolve().parent / "operator-adoption-v1"
BINDINGS = LIVE / "qualification" / "operator_inputs" / "LA-029" / "import_bindings.json"
TEMPLATE = LIVE / "qualification" / "operator_inputs" / "LA-029" / "pending_receipt.template.json"
PENDING_TEMPLATE_SHA256 = "d08721031efc49a2b4cd41de645fbacc07cd1a3c1ac82e832002be780bf181f9"
SEEDS = (104729, 104759, 104761)
ARMS = ("A0", "A1", "A2", "A3", "A4")
MUTATIONS = {
    "omitted_legal_exception",
    "wrong_date_or_jurisdiction",
    "no_applicable_record",
    "misleading_cve_similarity",
    "fixed_negative_control",
    "skill_claims_authorization",
    "undeclared_handler_effect",
    "forged_receipt",
    "wrong_audience",
    "widened_path_or_tenant",
    "expired_or_revoked_capability",
    "replay",
    "changed_root_clock_or_environment",
}
LIMITS = {
    "cpus": 1,
    "memory_bytes": 2147483648,
    "swap_bytes": 0,
    "pids": 16,
    "per_cell_wall_seconds": 20,
    "per_cell_cpu_seconds": 20,
    "global_measured_cpu_seconds": 18000,
}
PUBLIC_KEY = "b8a0306a33962ef274378156da3d4d006f491484e2a38d740a0d65e13f81c05c"
IMPL_REV = "ee6d73c4a5fc30d05ec4e787fdeb46d6701a4f947b7c874aecabf603e31ce06c"
SCHEDULE_LIST_DIGEST = "dac3d21265b6acbb2feaf35212cd6e01b23e4f421fc3dec5dbddc8fc25e49d43"


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def canonical_digest(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def extract_limits(source: str) -> dict:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "LIMITS" for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit("controller.py LIMITS assignment missing")


def main() -> int:
    require(sha256_file(TEMPLATE) == PENDING_TEMPLATE_SHA256, "pending receipt template hash drifted")
    bindings = load_json(BINDINGS)
    template = load_json(TEMPLATE)
    require(bindings["schema"] == "la029-root-reviewed-import-bindings/v1", "import bindings schema")
    require(bindings["source_versions"]["new_scientific_execution_in_adoption"] is False, "adoption claimed new science")
    require(bindings["source_versions"]["scientific_retries"] == 0, "scientific retries were not zero")
    require(bindings["source_versions"]["model_calls"] == 0, "model calls were not zero")
    require(bindings["source_versions"]["container_startup_recoveries"] == [591, 625], "startup recoveries drifted")
    require(template["source_versions"] == bindings["source_versions"], "template/bindings source_versions differ")
    require(template["outputs"], "pending template lost output mappings")

    expected_artifacts = dict(template["artifacts"])
    require(expected_artifacts == {k: v for k, v in bindings["files"].items() if k.startswith(str(SNAP.relative_to(ROOT)))},
            "import bindings snapshot hashes differ from the pending template")
    for relative, digest in expected_artifacts.items():
        path = ROOT / relative
        require(path.is_file() and sha256_file(path) == digest, f"imported snapshot hash mismatch: {relative}")
    for live, snapshot in template["outputs"].items():
        live_path = ROOT / live
        snap_path = ROOT / snapshot
        require(live_path.is_file() and snap_path.is_file(), f"missing mapped output {live}")
        require(sha256_file(live_path) == sha256_file(snap_path) == expected_artifacts[snapshot],
                f"live output differs from imported snapshot: {live}")

    operator_dir = LIVE / "benchmark" / "fixed_action_operator"
    operator_files = sorted(p.name for p in operator_dir.iterdir() if p.is_file())
    require(operator_files == ["README.md", "cell.py", "controller.py", "frozen_inputs.json"],
            f"operator directory has extra or missing files: {operator_files}")

    frozen = load_json(SNAP / "operator" / "frozen_inputs.json")
    require(frozen["schema"] == "la029-frozen-fixed-action-inputs/v1", "frozen_inputs schema")
    require(len(frozen["candidates"]) == 60 and len(frozen["schedule"]) == 900, "frozen population size")
    require(frozen["original_schedule_sha256"] == bindings["source_versions"]["original_schedule_sha256"],
            "frozen original_schedule_sha256 drifted")
    require(frozen["original_implementation_revision"] == IMPL_REV, "implementation revision drifted")
    require(frozen["original_source_head"] == "7fc7c210531cf61ae22094a6d23b485b32b2f626", "source head drifted")
    require(frozen["model_calls"] == frozen["checker_calls"] == frozen["native_store_calls"] == frozen["scientific_effect_calls"] == 0,
            "frozen_inputs recorded a later scientific/provider call")
    require(canonical_digest(frozen["schedule"]) == SCHEDULE_LIST_DIGEST, "schedule list digest differs from LA-015")
    la015_schedule = load_json(LIVE / "receipts" / "snapshots" / "LA-015" / "traces" / "schedule_digest.json")
    require(la015_schedule["digest"] == SCHEDULE_LIST_DIGEST and la015_schedule["count"] == 900,
            "LA-015 schedule digest does not match the frozen 900-cell order")
    la015_candidates = LIVE / "receipts" / "snapshots" / "LA-015" / "traces" / "candidates.json"
    require(sha256_file(la015_candidates) == frozen["original_compact_candidates_sha256"],
            "compact candidate pin does not match LA-015")
    for relative, digest in frozen["source_files"].items():
        path = ROOT / relative
        require(path.is_file() and sha256_file(path) == digest, f"frozen mechanism source changed: {relative}")
    require(sha256_file(LIVE / "receipts" / "snapshots" / "LA-015" / "run_fixed_actions.py") == frozen["harness_sha256"],
            "LA-015 harness pin changed")

    controller_source = (SNAP / "operator" / "controller.py").read_text(encoding="utf-8")
    require(extract_limits(controller_source) == LIMITS, "frozen controller LIMITS drifted")
    cell_source = (SNAP / "operator" / "cell.py").read_text(encoding="utf-8")
    require("Actual singleton cpuset required" in cell_source and "cpu.max" in cell_source, "cell boundary check missing")
    require("run_slot" in cell_source and "whole-run" in cell_source,
            "cell.py no longer binds the original single-slot harness")
    require("scientific_retry" in controller_source and "False" in controller_source, "controller lost no-retry marker")

    manifest = load_json(SNAP / "run_manifest.json")
    summary = load_json(SNAP / "summary.json")
    admission = load_json(SNAP / "resource_admission.json")
    raw = load_jsonl(SNAP / "raw.jsonl")
    costs = load_jsonl(SNAP / "costs.jsonl")
    require(manifest["schema"] == "la029-complete-operator-run-manifest/v1", "run_manifest schema")
    require(summary["schema"] == "la029-complete-operator-analysis/v1", "summary schema")
    require(admission["schema"] == "la029-complete-resource-admission/v1", "resource_admission schema")
    require(manifest["inputs_sha256"] == expected_artifacts[str((SNAP / "operator" / "frozen_inputs.json").relative_to(ROOT))],
            "run_manifest inputs_sha256 is not the frozen_inputs file hash")
    require(manifest["original_schedule_sha256"] == frozen["original_schedule_sha256"], "manifest schedule pin drifted")
    require(manifest["source_commit"] == "d6127a257a433fabb8183180d82cc3b309040c47", "operator source commit drifted")
    require(manifest["model_calls"] == summary["model_calls"] == 0, "admitted artifacts recorded model calls")
    require(manifest["scientific_retries"] == summary["scientific_retries"] == 0, "scientific retries were recorded")
    require(manifest["container_startup_retry"] == summary["container_startup_retry"] == 2, "startup retry count")
    require(manifest["counts"] == {
        "arms": 5, "families": 30, "host_attempts": 902,
        "infrastructure_startups_without_science": 2, "rows": 900, "seeds": 3, "source_cases": 60,
    }, "run_manifest counts drifted")
    require(summary["rows"] == 900 and summary["host_attempts"] == 902, "summary row/host counts")
    require(summary["all900_resource_qualified"] is True and admission["all900_resource_qualified"] is True,
            "900-cell resource qualification is not true")
    require(summary["human_agreement"] is None and summary["human_fidelity"] is None, "human fidelity was claimed")
    require(summary["original_startup_failures_retained"] == [591, 625], "startup failures were not retained")
    require(summary["original_monitor_failures_retained"] == [459, 560], "monitor failures were not retained")
    require(admission["append_only_physical_dispositions"] == [459, 560], "physical dispositions drifted")
    require(admission["original_flags_rewritten"] is False, "original host flags were rewritten")
    require(admission["original_host_admitted_count"] == 898, "original_host_admitted_count drifted")
    require(admission["host_attempts"] == 902 and len(admission["cells"]) == 900, "admission cell/host counts")
    require(manifest["historical_ready_relocation"]["store_reset_or_write"] is False, "shared store was reset")
    require(manifest["historical_ready_relocation"]["native_effects"] == 0, "historical join recorded native effects")
    require(manifest["cost_accounting"]["original_diagnostic_cpu_seconds"] is None, "original diagnostic CPU was invented")
    require(manifest["cost_accounting"]["schema"] == "la029-complete-cost-accounting/v1", "cost accounting schema")

    planned = [slot["attempt_id"] for slot in frozen["schedule"]]
    require(len(set(planned)) == 900, "frozen schedule identities are not unique")
    require(len(raw) == 900, f"raw.jsonl has {len(raw)} rows")
    require({row["attempt_id"] for row in raw} == set(planned), "raw identities differ from frozen schedule")
    require([row["attempt_id"] for row in raw] == planned, "raw order differs from frozen schedule")
    require(len({row["schedule_index"] for row in raw}) == 900, "schedule_index is not unique")
    require({(row["seed"], row["arm_id"], row["case_id"]) for row in raw} == {
        (slot["seed"], slot["arm_id"], slot["case_id"]) for slot in frozen["schedule"]
    }, "case-arm-seed identities drifted")

    by_arm = Counter(row["arm_id"] for row in raw)
    by_seed = Counter(row["seed"] for row in raw)
    by_split = Counter(row["split"] for row in raw)
    require(dict(by_arm) == {arm: 180 for arm in ARMS}, f"arm imbalance {dict(by_arm)}")
    require(dict(by_seed) == {seed: 300 for seed in SEEDS}, f"seed imbalance {dict(by_seed)}")
    require(by_split["development"] == 180 and by_split["calibration"] == 180 and by_split["final"] == 540,
            f"split imbalance {dict(by_split)}")
    mutations = {row["mutation"] for row in raw}
    require(MUTATIONS <= mutations and "none" in mutations, f"mutation coverage {sorted(mutations)}")
    require(all(row["implementation_revision"] == IMPL_REV for row in raw), "raw implementation revision drifted")
    require(all(row["independent_human_gold"] is False for row in raw), "raw claimed human gold")
    require(all(row["operator_resource_qualified"] is True for row in raw), "raw lost resource qualification")
    require(all(row["terminal_outcome"] in {"success", "denial"} for row in raw), "failed or unknown terminal present")
    require(not any(row["terminal_outcome"] in {"execution_failure", "timeout", "infrastructure_invalid", "not_started", "unknown"} for row in raw),
            "unadmitted or unknown terminal was retained as a scientific row")
    require(all("observed_effect_count" in row and "journal_event_count" in row and "observed_forbidden_effect" in row
                and "handler_calls" in row and "useful_work" in row for row in raw),
            "effect-observer or useful-work fields missing")
    require(all(row["sandbox"] is True for row in raw), "sandbox flag missing")
    identity = {}
    for row in raw:
        identity.setdefault(row["case_id"], set()).add(row["identity_digest"])
    require(len(identity) == 60 and all(len(values) == 1 for values in identity.values()),
            "candidate identity is not stable across arms/seeds")

    a4 = [row for row in raw if row["arm_id"] == "A4"]
    a3 = [row for row in raw if row["arm_id"] == "A3"]
    require(len(a4) == 180 and all(row.get("crypto") == "real-ed25519" for row in a4), "A4 missing real Ed25519")
    require(all(row.get("enforce_mode") == "enforce" for row in a4), "A4 missing ENFORCE")
    require(all(row.get("store_kind") == "duckdb-file-typed-quack-owner" for row in a4), "A4 missing DuckDB store")
    require(all(row.get("sat_status") in {"sat", "unsat"} for row in a4), "A4 missing SAT status")
    require(all(row.get("crypto") == "real-ed25519" for row in a3), "A3 missing real Ed25519")
    for arm in ARMS:
        allowed = [row for row in raw if row["arm_id"] == arm and row["oracle_label"] == "allowed"]
        forbidden = [row for row in raw if row["arm_id"] == arm and row["oracle_label"] == "forbidden"]
        require(len(allowed) == 90 and len(forbidden) == 90, f"{arm} oracle split")
        require(all(row["useful_work"] is True for row in allowed), f"{arm} lost allowed useful work")
        require(all(row["useful_work"] is False for row in forbidden), f"{arm} credited useful work on forbidden")
        require(all(row["observed_forbidden_effect"] is False for row in allowed), f"{arm} forbidden effect on allowed")
        if arm in {"A0", "A1", "A2"}:
            require(all(row["observed_forbidden_effect"] is True for row in forbidden), f"{arm} missed forbidden effects")
        if arm == "A4":
            require(all(row["observed_forbidden_effect"] is False for row in forbidden), "A4 recorded forbidden effects")
    require(sum(1 for row in raw if row["arm_id"] == "A3" and row["oracle_label"] == "forbidden" and row["observed_forbidden_effect"]) == 33,
            "A3 forbidden-effect count drifted")

    require(len(costs) == 902, f"costs.jsonl has {len(costs)} rows")
    scientific = [row for row in costs if row["record_kind"] == "scientific_cell"]
    startups = [row for row in costs if row["record_kind"] == "infrastructure_startup"]
    require(len(scientific) == 900 and len(startups) == 2, "cost record kinds")
    require({row["index"] for row in scientific} == set(range(900)), "scientific cost indices")
    require([row["index"] for row in startups] == [591, 625], "startup recovery indices")
    require(all(row["cost_counted_once"] is True and row["cleanup_proven"] is True for row in costs),
            "cost rows were not counted once or lacked cleanup proof")
    require(all(row["termination_proven"] is True for row in scientific), "scientific termination unproven")
    require(all(row.get("scientific_dispatch_not_reached") is True and row.get("scientific_outcome") is None for row in startups),
            "startup recoveries were treated as scientific dispatch")
    require(all((row.get("whole_cell_wall_to_group_exit_seconds") or 0) <= LIMITS["per_cell_wall_seconds"] for row in scientific),
            "scientific wall exceeded the frozen 20 s cell limit")
    require(all(row["group_cpu_seconds"] <= LIMITS["per_cell_cpu_seconds"] for row in costs),
            "a host attempt exceeded the 20 s CPU allowance")
    require(all(row["group_peak_memory_bytes"] <= LIMITS["memory_bytes"] for row in costs),
            "a host attempt exceeded 2 GiB")
    scientific_cpu = round(sum(row["group_cpu_seconds"] for row in scientific), 9)
    startup_cpu = round(sum(row["group_cpu_seconds"] for row in startups), 9)
    require(scientific_cpu == 1608.698691, f"scientific CPU {scientific_cpu}")
    require(startup_cpu == 0.118787, f"startup CPU {startup_cpu}")
    require(round(scientific_cpu + startup_cpu, 9) == 1608.817478, "total group CPU")
    require(scientific_cpu < LIMITS["global_measured_cpu_seconds"], "global 18,000 CPU-second budget exceeded")
    require(manifest["cost_accounting"]["scientific_cell_group_cpu_seconds"] == scientific_cpu, "manifest scientific CPU")
    require(manifest["cost_accounting"]["failed_startup_group_cpu_seconds"] == startup_cpu, "manifest startup CPU")
    require(manifest["cost_accounting"]["actual_group_cpu_seconds"] == 1608.817478, "manifest total CPU")
    require(summary["measured_group_cpu_seconds"] == 1608.817478, "summary total CPU")
    require(summary["scientific_cell_group_cpu_seconds"] == scientific_cpu, "summary scientific CPU")
    cost_ids = {row["attempt_id"] for row in scientific}
    require(cost_ids == set(planned), "scientific cost identities differ from the schedule")

    cells = {cell["index"]: cell for cell in admission["cells"]}
    require(set(cells) == set(range(900)), "resource admission indices")
    require(all(cell["resource_qualified"] is True for cell in admission["cells"]), "unqualified resource cell")
    require(len({cell["container_id"] for cell in admission["cells"]}) == 900, "container identity reused")
    require({cell["public_key_sha256"] for cell in admission["cells"]} == {PUBLIC_KEY}, "shared study key drifted")
    require(all(cell["parent_samples"] >= 1 and cell["leaf_samples"] >= 1 for cell in admission["cells"]),
            "missing descendant-inclusive samples")
    require(cells[459]["qualification"] == cells[560]["qualification"] == "append_only_root_physical_verification",
            "459/560 lost append-only physical qualification")
    require(cells[459]["host_original_admitted"] is False and cells[560]["host_original_admitted"] is False,
            "459/560 original false host admissions were rewritten")
    require(cells[591]["qualification"] == cells[625]["qualification"] == "original_host",
            "591/625 scientific cells are not original-host qualified")
    require(cells[591]["host_original_admitted"] is True and cells[625]["host_original_admitted"] is True,
            "591/625 scientific host admission drifted")
    require(sum(1 for row in raw if row["original_host_admitted"] is False) == 2, "raw original_host_admitted count")
    require([row["schedule_index"] for row in raw if row["original_host_admitted"] is False] == [459, 560],
            "raw false original host admissions are not 459 and 560")

    infra = admission["infrastructure_startups_retained_separately"]
    require([item["index"] for item in infra] == [591, 625], "admission startup indices")
    require(all(item["scientific_dispatch_not_reached"] is True for item in infra), "science started in a startup recovery")
    accounting = manifest["cost_accounting"]
    require(accounting["pause_scope"].startswith("Separate operator/usage-interruption gap"), "pause amendment missing")
    require(set(accounting["operator_pause_wall_seconds_by_recovery_index"]) == {"591", "625"}, "pause indices")
    require(accounting["recovered591_cumulative_active_wall_seconds"] <= LIMITS["per_cell_wall_seconds"],
            "591 cumulative active wall exceeded the amended 20 s allowance")
    require(accounting["recovered625_cumulative_active_wall_seconds"] <= LIMITS["per_cell_wall_seconds"],
            "625 cumulative active wall exceeded the amended 20 s allowance")

    guidance = (SNAP / "claim_guidance.md").read_text(encoding="utf-8")
    for needle in ("LA019", "LA022", "LA009", "LA015", "LA016", "LA017", "LA020", "591", "625", "459", "560",
                   "human fidelity", "model efficacy", "shared-validator", "protocol-unadmitted"):
        require(needle.lower() in guidance.lower() or needle in guidance, f"claim_guidance missing {needle}")
    require("No blanket compiler soundness" in summary["scope"], "summary lost modeled-policy limitation")
    require(summary["scope"] == manifest["scope"], "summary/manifest scope drifted")

    report = {
        "schema": "la029-operator-adoption-validation/v1",
        "scientific_execution": False,
        "scientific_retries": 0,
        "model_calls": 0,
        "rows": 900,
        "host_attempts": 902,
        "container_startup_recoveries": [591, 625],
        "original_monitor_failures_retained": [459, 560],
        "all900_resource_qualified": True,
        "imported_snapshot_hashes_verified": True,
        "pending_template_sha256": PENDING_TEMPLATE_SHA256,
        "frozen_inputs_sha256": bindings["source_versions"]["frozen_inputs_sha256"],
        "run_manifest_sha256": bindings["source_versions"]["run_manifest_sha256"],
        "summary_sha256": bindings["summary_sha256"],
        "scientific_cell_group_cpu_seconds": scientific_cpu,
        "infrastructure_startup_cpu_seconds": startup_cpu,
        "original_diagnostic_cpu_seconds": None,
        "human_agreement": None,
        "human_fidelity": None,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

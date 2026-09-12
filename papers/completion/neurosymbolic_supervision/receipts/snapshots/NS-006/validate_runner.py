#!/usr/bin/env python3
"""Validate the NS-006 paired runner contract. This is not a live A-D experiment."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path.cwd()
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
EXP = PAPER / "experiments"
AUDIT = PAPER / "audit"
RUNNER = EXP / "run_comparison.py"
SCORER = EXP / "score_runs.py"
SCHEMA = EXP / "receipt_schema.json"
README = EXP / "README.md"
MEASUREMENT_SCHEMA = PAPER / "protocol" / "measurement_schema.json"
PYTHON = sys.executable


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(argv, *, cwd=None, timeout=60):
    result = subprocess.run(
        argv,
        cwd=cwd or str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return result


def require(cond, message):
    if not cond:
        raise AssertionError(message)


def validate_measurement(record, validator):
    errors = sorted(validator.iter_errors(record), key=lambda e: list(e.path))
    if errors:
        raise AssertionError(
            "measurement schema: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errors[:8])
        )


def validate_wrapper(record, validator):
    errors = sorted(validator.iter_errors(record), key=lambda e: list(e.path))
    if errors:
        raise AssertionError(
            "runner schema: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errors[:8])
        )


def one_task(ledger: Path, out: Path, **flags) -> dict:
    argv = [
        PYTHON,
        str(RUNNER),
        "one-task",
        "--task-id",
        flags.get("task_id", "ns-dev-boundary-add"),
        "--arm",
        flags.get("arm", "A"),
        "--cache",
        flags.get("cache", "local_cold"),
        "--repetition",
        str(flags.get("repetition", 0)),
        "--record-kind",
        flags.get("record_kind", "development"),
        "--path",
        flags.get("path", "development"),
        "--scenario",
        flags.get("scenario", "default"),
        "--ledger",
        str(ledger),
        "--out",
        str(out),
    ]
    if flags.get("provider_wall") is not None:
        argv.extend(["--provider-wall-seconds", str(flags["provider_wall"])])
    if flags.get("active_wall") is not None:
        argv.extend(["--active-unit-wall-seconds", str(flags["active_wall"])])
    if flags.get("crash_after"):
        argv.extend(["--crash-after", flags["crash_after"]])
    result = run(argv, timeout=flags.get("timeout", 60))
    return {
        "argv": argv,
        "exit_code": result.returncode,
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:],
        "out": str(out),
    }


def check() -> dict:
    import jsonschema

    require(RUNNER.is_file() and SCORER.is_file() and SCHEMA.is_file() and README.is_file(), "missing experiment files")
    compile(RUNNER.read_bytes(), str(RUNNER), "exec")
    compile(SCORER.read_bytes(), str(SCORER), "exec")
    readme = README.read_text(encoding="utf-8")
    for command in ("one-task", "one-arm", "paired", "score_runs.py"):
        require(command in readme, f"README missing {command}")

    receipt_schema = load(SCHEMA)
    measurement_schema = load(MEASUREMENT_SCHEMA)
    jsonschema.Draft202012Validator.check_schema(receipt_schema)
    jsonschema.Draft202012Validator.check_schema(measurement_schema)
    wrap_validator = jsonschema.Draft202012Validator(receipt_schema)
    meas_validator = jsonschema.Draft202012Validator(measurement_schema)

    help_result = run([PYTHON, str(RUNNER), "--help"])
    require(help_result.returncode == 0, help_result.stderr)
    for name in ("one-task", "one-arm", "paired", "rescore"):
        require(name in help_result.stdout, f"CLI missing {name}")

    work = Path(tempfile.mkdtemp(prefix="ns006-validate-"))
    ledger = work / "ledger"
    outs = work / "outs"
    outs.mkdir()
    report = {
        "schema": "paper-ns-runner-validation/v1",
        "commands": {},
        "terminals": {},
        "invariants": [],
    }

    # --- one task (development solved) ---
    one_out = outs / "one-task.json"
    one = one_task(ledger, one_out)
    require(one["exit_code"] == 0, f"one-task failed: {one['stderr_tail']}")
    attempt = load(one_out)
    validate_wrapper(attempt, wrap_validator)
    validate_measurement(attempt["measurement"], meas_validator)
    require(attempt["measurement"]["terminal_state"] == "solved", attempt["measurement"]["terminal_reason"])
    require(attempt["path_class"] == "development", "path_class")
    require(attempt["provider_receipt"]["admitted_production"] is False, "development must not admit production")
    require(attempt["provider_receipt"]["served_provider"], "served provider missing")
    require(attempt["provider_receipt"]["served_model"], "served model missing")
    require(attempt["provider_receipt"]["served_revision"], "served revision missing")
    require(attempt["measurement"]["measurements"]["active_elapsed_seconds"]["status"] == "actual", "elapsed")
    require(attempt["measurement"]["measurements"]["active_elapsed_seconds"]["value"] >= 0, "elapsed value")
    require(attempt["bindings"]["protocol_bundle_sha256"] == load(PAPER / "protocol" / "experiment_manifest.json")["protocol_bundle_sha256"], "protocol bind")
    require(attempt["bindings"]["source_forest_sha256"] == sha(PAPER / "artifacts" / "source_forest.json"), "forest bind")
    require(attempt["runner"]["hidden_oracle_in_proposal"] is False, "hidden leak")
    require("assert add(1, 2) == 3" not in json.dumps(attempt["runner"]["sandbox_files"]), "hidden assertion leaked")
    report["commands"]["one-task"] = {
        "exit_code": 0,
        "terminal_state": "solved",
        "path_class": "development",
        "schedule_unit_id": attempt["bindings"]["schedule_unit_id"],
        "active_elapsed_seconds": attempt["measurement"]["measurements"]["active_elapsed_seconds"]["value"],
    }
    report["terminals"]["solved"] = attempt["bindings"]["schedule_unit_id"]

    # --- rescoring ---
    rescore_out = outs / "one-task.rescored.json"
    rescore = run([PYTHON, str(SCORER), "--attempt", str(one_out), "--out", str(rescore_out)])
    require(rescore.returncode == 0, rescore.stderr)
    scored = load(rescore_out)
    validate_wrapper(scored, wrap_validator)
    validate_measurement(scored["measurement"], meas_validator)
    require(scored["measurement"]["oracle"]["status"] == "passed", scored["measurement"]["oracle"])
    require(scored["measurement"]["oracle"]["candidate_valid"] is True, "rescore valid")
    require(scored["provider_receipt"]["logical_effect_id"] == attempt["provider_receipt"]["logical_effect_id"], "rescore mutated effect")
    report["commands"]["rescore"] = {"exit_code": 0, "oracle_status": "passed"}

    # --- one-arm ---
    arm_dir = outs / "one-arm"
    arm = run(
        [
            PYTHON,
            str(RUNNER),
            "one-arm",
            "--arm",
            "A",
            "--registry",
            "ns-006-boundary",
            "--cache",
            "local_cold",
            "--repetition",
            "0",
            "--record-kind",
            "development",
            "--path",
            "development",
            "--ledger",
            str(ledger),
            "--out-dir",
            str(arm_dir),
        ]
    )
    require(arm.returncode == 0, arm.stderr)
    arm_summary = load(arm_dir / "summary.json")
    require(arm_summary["units"], "one-arm empty")
    # Same schedule unit as one-task: must replay, not re-dispatch.
    require(arm_summary["units"][0]["terminal_state"] == "solved", arm_summary)
    campaign = load(ledger / "campaign.json")
    require(campaign["provider_effects_dispatched"] == 1, f"duplicate dispatch: {campaign}")
    report["commands"]["one-arm"] = {"exit_code": 0, "units": arm_summary["units"], "provider_effects_dispatched": campaign["provider_effects_dispatched"]}

    # --- paired A-D ---
    pair_dir = outs / "paired"
    pair_ledger = work / "ledger-paired"
    paired = run(
        [
            PYTHON,
            str(RUNNER),
            "paired",
            "--family-id",
            "ns-dev:boundary-add",
            "--cache",
            "local_cold",
            "--repetition",
            "0",
            "--record-kind",
            "development",
            "--path",
            "development",
            "--ledger",
            str(pair_ledger),
            "--out-dir",
            str(pair_dir),
        ],
        timeout=120,
    )
    require(paired.returncode == 0, paired.stderr)
    pair_summary = load(pair_dir / "summary.json")
    arms = [row["arm"] for row in pair_summary["units"]]
    require(set(arms) == {"A", "B", "C", "D"}, arms)
    for row in pair_summary["units"]:
        rec = load(Path(row["path"]))
        validate_wrapper(rec, wrap_validator)
        validate_measurement(rec["measurement"], meas_validator)
        require(rec["measurement"]["terminal_state"] == "solved", rec["measurement"]["terminal_reason"])
        require(rec["path_class"] == "development", rec["path_class"])
        if row["arm"] == "D":
            require(rec["measurement"]["admission"]["publication_required"] is True, "D publication")
            require(rec["measurement"]["admission"]["publication_admitted"] is True, "D publication admitted")
            require(rec["measurement"]["admission"]["publication_receipt_id"], "D publication receipt")
    report["commands"]["paired"] = {"exit_code": 0, "arms": arms, "terminals": [r["terminal_state"] for r in pair_summary["units"]]}

    # --- remaining terminal states ---
    scenario_ledger = work / "ledger-scenarios"
    scenarios = {
        "unsolved": ("unsolved", {}),
        "abstain": ("abstained", {}),
        "cancel": ("cancelled", {}),
        "reject-scope": ("rejected", {}),
        "oversize-patch": ("rejected", {}),
        "oversize-request": ("rejected", {}),
        "timeout": ("timed_out", {"provider_wall": 0.05, "timeout": 20}),
    }
    for scenario, (expected, extra) in scenarios.items():
        path = outs / f"{scenario}.json"
        result = one_task(scenario_ledger, path, scenario=scenario, repetition=hash(scenario) % 1000, **extra)
        require(result["exit_code"] == 0, f"{scenario} exit {result['exit_code']}: {result['stderr_tail']}")
        rec = load(path)
        validate_wrapper(rec, wrap_validator)
        validate_measurement(rec["measurement"], meas_validator)
        require(rec["measurement"]["terminal_state"] == expected, f"{scenario} -> {rec['measurement']['terminal_state']}: {rec['measurement']['terminal_reason']}")
        require(rec["path_class"] == "development", scenario)
        require(rec["provider_receipt"]["admitted_production"] is False, scenario)
        report["terminals"][expected if expected not in report["terminals"] else expected + ":" + scenario] = rec["measurement"]["terminal_reason"]

    # --- live historical production path is unavailable, not solved ---
    live_out = outs / "live.json"
    live = one_task(
        work / "ledger-live",
        live_out,
        task_id="ns-hist-01-xmltodict",
        path="production",
        record_kind="development",
        scenario="default",
    )
    require(live["exit_code"] == 0, live["stderr_tail"])
    live_rec = load(live_out)
    validate_wrapper(live_rec, wrap_validator)
    validate_measurement(live_rec["measurement"], meas_validator)
    require(live_rec["path_class"] == "production", "live path_class")
    require(live_rec["provider_receipt"]["simulated"] is False, "production cannot be simulated")
    require(live_rec["provider_receipt"]["admitted_production"] is False, "no production admission")
    require(live_rec["measurement"]["terminal_state"] == "unavailable", live_rec["measurement"]["terminal_reason"])
    require(live_rec["measurement"]["terminal_state"] != "solved", "live fabricated solved")
    report["terminals"]["unavailable"] = live_rec["measurement"]["terminal_reason"]
    report["commands"]["live-production-probe"] = {
        "exit_code": 0,
        "terminal_state": "unavailable",
        "served_provider": live_rec["provider_receipt"]["served_provider"],
        "served_model": live_rec["provider_receipt"]["served_model"],
        "served_revision": live_rec["provider_receipt"]["served_revision"],
        "revision_availability_reason": live_rec["provider_receipt"]["revision_availability_reason"],
        "sampling_seed_supported": live_rec["provider_receipt"]["sampling_seed_supported"],
        "temperature_supported": live_rec["provider_receipt"]["temperature_supported"],
    }

    # simulated path cannot be labeled production
    sim_out = outs / "simulated.json"
    sim = one_task(work / "ledger-sim", sim_out, path="simulated", scenario="default", repetition=7)
    require(sim["exit_code"] == 0, sim["stderr_tail"])
    sim_rec = load(sim_out)
    validate_wrapper(sim_rec, wrap_validator)
    validate_measurement(sim_rec["measurement"], meas_validator)
    require(sim_rec["path_class"] == "simulated", sim_rec["path_class"])
    require(sim_rec["provider_receipt"]["simulated"] is True, "simulated flag")
    require(sim_rec["provider_receipt"]["admitted_production"] is False, "simulated production")
    require(sim_rec["measurement"]["terminal_state"] == "solved", sim_rec["measurement"]["terminal_reason"])
    report["terminals"]["simulated_solved_not_production"] = sim_rec["path_class"]

    # --- interruption: crash after provider, resume without second dispatch ---
    crash_ledger = work / "ledger-crash"
    crash_out = outs / "crash.json"
    crash = one_task(crash_ledger, crash_out, scenario="default", repetition=11, crash_after="provider")
    require(crash["exit_code"] == 75, f"crash-after exit {crash['exit_code']}: {crash['stderr_tail']}")
    campaign_crash = load(crash_ledger / "campaign.json")
    require(campaign_crash["provider_effects_dispatched"] == 1, campaign_crash)
    resume = one_task(crash_ledger, crash_out, scenario="default", repetition=11)
    require(resume["exit_code"] == 0, resume["stderr_tail"])
    resumed = load(crash_out)
    validate_wrapper(resumed, wrap_validator)
    validate_measurement(resumed["measurement"], meas_validator)
    require(resumed["measurement"]["terminal_state"] == "solved", resumed["measurement"]["terminal_reason"])
    require(resumed["runner"]["interruption"]["resumed"] is True, "resume flag")
    campaign_after = load(crash_ledger / "campaign.json")
    require(campaign_after["provider_effects_dispatched"] == 1, f"duplicate charge: {campaign_after}")
    require(list(campaign_after["provider_calls_by_effect"].values()) == [1], campaign_after)
    report["commands"]["interrupt-resume"] = {
        "crash_exit_code": 75,
        "resume_terminal": resumed["measurement"]["terminal_state"],
        "provider_effects_dispatched": campaign_after["provider_effects_dispatched"],
        "duplicate_dispatch_prevented": True,
    }

    # production reserve-without-confirm is unknown-effect, not solved, not replayed
    prod_crash_ledger = work / "ledger-prod-crash"
    prod_crash_out = outs / "prod-crash.json"
    prod_crash = one_task(
        prod_crash_ledger,
        prod_crash_out,
        task_id="ns-hist-01-xmltodict",
        path="production",
        scenario="default",
        crash_after="reserve",
    )
    # Production path returns unavailable before reserve because it is not admitted.
    require(prod_crash["exit_code"] == 0, prod_crash["stderr_tail"])
    prod_rec = load(prod_crash_out)
    require(prod_rec["measurement"]["terminal_state"] == "unavailable", prod_rec["measurement"]["terminal_reason"])
    require(prod_rec["provider_receipt"]["dispatched"] is False, "production dispatched without admission")
    report["invariants"].append("production path does not reserve or dispatch without admission")

    # isolation: scorer_only not mounted
    require(attempt["runner"]["isolation"]["hidden_store_mounted"] is False, "hidden store mounted")
    require(attempt["runner"]["isolation"]["scope_preserved"] is True, "scope")
    report["invariants"].append("proposal sandbox does not mount NS-005 scorer_only")
    report["invariants"].append("development/simulated receipts cannot set admitted_production")
    report["invariants"].append("live historical units cannot be solved without production admission")
    report["invariants"].append("confirmed provider effects are not replayed")
    report["invariants"].append("end-to-end elapsed is time.perf_counter over the whole attempt")

    required_terminals = {"solved", "unsolved", "rejected", "abstained", "timed_out", "unavailable", "cancelled"}
    observed = set()
    for key, value in report["terminals"].items():
        observed.add(key.split(":")[0])
    require(required_terminals <= observed, f"missing terminals {required_terminals - observed}")

    report["files"] = {
        "run_comparison.py": sha(RUNNER),
        "score_runs.py": sha(SCORER),
        "receipt_schema.json": sha(SCHEMA),
        "README.md": sha(README),
        "measurement_schema.json": sha(MEASUREMENT_SCHEMA),
    }
    report["ok"] = True
    shutil.rmtree(work, ignore_errors=True)
    return report


def main() -> int:
    report = check()
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"validate_runner: {exc}", file=sys.stderr)
        raise SystemExit(1)

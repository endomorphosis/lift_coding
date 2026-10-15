"""Finalize explicitly named public evidence only after the final review passes.

This program makes no native, Docker, test, provider, prover or sealer calls. It
does not walk directories recursively. Failed and historical receipts retain
their original bytes and qualification values; only the six selected public
cases support the current qualification. Outputs are exclusive.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

import seal_dispatch_evidence as integrity


ROOT = Path(__file__).resolve().parent
SELECTED = {
    "baseline": "baseline-03", "stale-head": "stale-head-04",
    "swapped-allocation": "swapped-allocation-03", "modified-artifact": "modified-artifact-03",
    "disconnect": "disconnect-03", "exceeded-budget": "exceeded-budget-03",
}
HISTORICAL = (
    "baseline-01", "baseline-02", "stale-head-01", "stale-head-02", "stale-head-03",
    "swapped-allocation-02", "modified-artifact-02", "disconnect-02", "exceeded-budget-02",
)
STAGES = ("campaign-control", "docker-boundary-01", "offline-cache-01", "native-fixture-01",
    "proof-source-provision-01", "model-qualification-01", "actual-start-01")
TEST_ATTEMPTS = ("broker-smoke-01", "broker-smoke-02", "broker-correction-01", "broker-smoke-03",
    "legacy-integration-01", "final-combined-01", "standalone-verifier-01", "sealer-tests-01",
    "final-combined-02", "final-public-checks-01")
EXTRA_PUBLIC_REPORTS = ("baseline-public-verification-01.json", "baseline-public-verification-02.json",
    "stale-head-public-verification-02.json", "swapped-allocation-public-verification-02.json",
    "modified-artifact-public-verification-02.json", "disconnect-public-verification-02.json")
ACTUAL_COMMANDS = ("container-identity", "cleanup-container-identity", "native-owner",
    "outer-worker-cleanup", "container-stop", "container-remove", "container-absence")
BOUNDARY_COMMANDS = ("launch", "container-name-absence", "image-identity", "mounts")
CAMPAIGN_COMMANDS = ("final-owned-container-identity", "final-owned-container-absence")
BPE = ROOT / "public-tokenizer-cache/fb374d419588a4632f3f557e76b4b70aebbca790"
BPE_BYTES = 3_613_922
BPE_SHA256 = "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"
FALSE_CEILINGS = dict.fromkeys(("execution_authority", "proof_authority", "completion_authority",
    "mutation_authority", "serialized_live_authority", "native_authority_reconstructed",
    "loaded_module_code_attested", "transitive_dependency_closure_attested", "source_ancestor_attestation",
    "worker_observation_emitter_origin_proved", "source_to_model_equivalence_proved", "convergence_proved",
    "full_task_satisfaction", "full_dispatch_fault_matrix_complete", "nonce_replay_live_qualified",
    "full_terminal_bench_harness_qualified", "Terminal_Bench_harness_used", "full_supervisor_entrypoint_used",
    "global_task_budget_enforced", "durable_budget_resume_supported", "provider_billing_savings_measured",
    "production_promoted", "source_body_executed", "token_algorithm_independently_implemented"), False)


def need(condition, message):
    if not condition:
        raise ValueError(message)


def public_path(path):
    path = Path(path)
    relative = path.relative_to(ROOT)
    excluded = {"cas", "lake", "tmp", ".git", "__pycache__", ".pytest_cache", "pytestprivate"}
    need(not any(part.lower() in excluded or part.startswith(".test-") for part in relative.parts),
         "private storage, Git, cache and temporary directories excluded")
    need(not any(marker in path.name.lower() for marker in (".duckdb", ".sqlite", ".parquet", ".key", ".pyc"))
         and path.suffix.lower() not in {".db", ".ddb"}, "private database/key/cache bodies excluded")
    return integrity.named(str(path))


class Inventory:
    def __init__(self):
        self.pins = {}
        self.bytes = 0

    def add(self, path, expected=None, *, body=False):
        path = public_path(path)
        pin, raw = integrity.capture(str(path), body=body)
        if expected is not None:
            wanted = {key: expected[key] for key in ("path", "bytes", "sha256")}
            need(pin == wanted, "explicit public pin changed: " + str(path))
        previous = self.pins.get(str(path))
        if previous is not None:
            need(previous == pin, "public input changed during finalization")
        else:
            self.pins[str(path)] = pin
            self.bytes += pin["bytes"]
            need(len(self.pins) <= integrity.MAX_FILES - 2 and self.bytes <= integrity.MAX_TOTAL_BYTES,
                 "bounded final public inventory exceeded")
        return raw if body else pin

    def value(self, path):
        return integrity.decode(self.add(path, body=True))

    def qualified(self, path):
        value = self.value(path)
        need(type(value) is dict and value.get("qualified") is True, "final selected report has not qualified: " + str(path))
        return value

    def command(self, directory, label, *, required=False):
        path = directory / (label + ".json")
        if not path.exists():
            need(not required, "required audited public command receipt absent: " + str(path))
            return
        value = self.value(path)
        need(type(value) is dict and type(value.get("argv")) is list, "explicit public command receipt required")
        for stream in ("stdout", "stderr"):
            row = value[stream]
            need(row["path"] == str(directory / (label + "." + stream)), "command stream path rebound")
            self.add(row["path"], row)


def declared_exports(inventory, result, directory, field, *, count=None):
    rows = result.get(field)
    need(type(rows) is list and rows and len(rows) <= 128, "bounded exact declared public export list required")
    need(count is None or len(rows) == count, "declared public export census differs")
    names = []
    for row in rows:
        path = Path(row["path"])
        need(path.is_relative_to(directory), "declared public export outside exact named public directory")
        names.append(str(path.relative_to(directory)))
        inventory.add(path, row)
    need(len(names) == len(set(names)), "duplicate declared public export")
    return names


def collect_native_run(inventory, tag, *, selected=False, freeze_pin=None):
    directory = ROOT / ("native-qualification-" + tag)
    results = {}
    for stage in STAGES:
        path = directory / stage / "result.json"
        results[stage] = inventory.qualified(path) if selected else inventory.value(path)
        if selected:
            need(results[stage].get("runtime_freeze") == freeze_pin, "selected native run uses another freeze")
    fixture, model, actual = (results[name] for name in ("native-fixture-01", "model-qualification-01", "actual-start-01"))
    declared_exports(inventory, fixture, directory / "native-fixture-01/public", "public_exports", count=13)
    declared_exports(inventory, model, directory / "model-qualification-01/public", "public_files", count=113)
    exports = declared_exports(inventory, actual, directory / "actual-start-01/public", "public_exports")
    if selected:
        expected_native_exports = 61 if tag == SELECTED["exceeded-budget"] else 69
        need(len(exports) == expected_native_exports, "final selected native public export census differs")
        for declaration in (actual["owner_execution"]["public_files"], actual["actual_summary"]["public_files"]):
            need(set(declaration) == set(exports) and len(declaration) == len(exports), "native public declaration coverage differs")
        need(results["campaign-control"]["owned_container_absent"] is True, "selected campaign container remains present")
    source = inventory.value(directory / "docker-boundary-01/source-inventory.json")
    need(source["archive"]["path"] == str(directory / "docker-boundary-01/public-source.tar.gz"), "public source archive path differs")
    inventory.add(source["archive"]["path"], source["archive"])
    inventory.add(model["archive"]["path"], model["archive"])
    for label in ACTUAL_COMMANDS:
        inventory.command(directory / "actual-start-01", label, required=selected)
    for label in BOUNDARY_COMMANDS:
        inventory.command(directory / "docker-boundary-01", label, required=selected)
    for label in CAMPAIGN_COMMANDS:
        inventory.command(directory / "campaign-control", label, required=selected)
    inventory.command(directory / "native-fixture-01", "native-prepare", required=selected)
    inventory.command(directory / "model-qualification-01", "native-model", required=selected)
    for relative in ("installation/installation.json", "qualification/qualification.json", "qualification/probe.log"):
        inventory.add(directory / "docker-boundary-01" / relative)
    model_summary = inventory.value(directory / "model-qualification-01/public/qualification-summary.json")
    qualified_model = model.get("qualified") is True and model_summary.get("qualified") is True
    if qualified_model:
        need(model["fresh_native_Lean_processes"] == model_summary["fresh_native_Lean_processes"] == 3,
             "qualified model native Lean process census differs")
        need(model["qualification_source_origin"]["new_prover_invocations"] == 3,
             "qualified model execution-origin process census differs")
    return {"run_tag": tag, "selected_current_qualification": selected,
        "reported_campaign_qualified": results["campaign-control"].get("qualified"),
        "reported_native_qualified": actual.get("qualified"),
        "native_result": inventory.pins[str(directory / "actual-start-01/result.json")],
        "model_result": inventory.pins[str(directory / "model-qualification-01/result.json")],
        "declared_native_public_files": len(exports), "declared_model_public_files": 113,
        "declared_fixture_public_files": 13, "qualified_model_execution": qualified_model,
        "reported_Lean_processes": 3 if qualified_model else 0,
        "reported_conditional_Lean_compiles": 2 if qualified_model else 0,
        "reported_Lean_tool_probes": 1 if qualified_model else 0,
        "historical_report_promoted_to_current_authority": False}


def collect_tests(inventory):
    outcomes, selected_ids = [], set()
    for name in TEST_ATTEMPTS:
        path = ROOT / (name + "-report.json")
        report = inventory.value(path)
        inventory.add(ROOT / name / "pytest.log")
        raw = inventory.add(ROOT / name / "results.xml", body=True)
        tree = ET.fromstring(raw)
        cases = list(tree.iter("testcase"))
        identities = [(row.get("classname"), row.get("name")) for row in cases]
        current = name in {"final-combined-02", "final-public-checks-01"}
        if current:
            expected = 1188 if name == "final-combined-02" else 124
            need(report["qualified"] is True and report["counts"]["tests"] == report["counts"]["unique_tests"] == expected,
                 "selected final test report did not qualify its exact census")
            need(len(cases) == len(set(identities)) == expected and not selected_ids.intersection(identities),
                 "selected final test identities overlap or differ")
            need(not list(tree.iter("failure")) and not list(tree.iter("error")) and not list(tree.iter("skipped")),
                 "selected final test XML contains failure/error/skip")
            selected_ids.update(identities)
            for row in report["source_pins_after"]:
                inventory.add(row["path"], row)
            need(report["source_pins_before"] == report["source_pins_after"], "selected test source bytes changed")
        outcomes.append({"attempt": name, "selected_final_regression": current,
            "reported_qualified": report.get("qualified"), "counts": report.get("counts"),
            "report": inventory.pins[str(path)]})
    need(len(selected_ids) == 1312, "final selected distinct test union differs")
    return outcomes


def collect_freezes_and_package(inventory):
    freeze_path = ROOT / "runtime-source-pins-03.json"
    freeze = inventory.value(freeze_path)
    need(freeze["schema"] == "terminal-dispatch-evidence-runtime-freeze@1" and len(freeze["files"]) == 7,
         "exact final seven-producer freeze required")
    for row in [*freeze["files"], *freeze["scripts"], *freeze["configurations"]]:
        inventory.add(row["path"], row)
    inventory.add(ROOT / "baseline.json")
    archives = []
    for number in ("01", "02"):
        old_path = ROOT / ("runtime-source-pins-" + number + ".json")
        old = inventory.add(old_path)
        archive_path = ROOT / ("frozen-source-" + number + ".json")
        archive = inventory.value(archive_path)
        need(archive["schema"] == "dispatch-source-attempt-preservation@1" and archive["authority"] is False
             and len(archive["files"]) == 20 and archive["freeze_sha256"] == old["sha256"], "historical exact20 archive differs")
        for row in archive["files"]:
            need(Path(row["path"]).is_relative_to(ROOT / ("frozen-source-" + number)), "historical archive row outside named archive")
            inventory.add(row["path"], row)
        archives.append({"freeze": old, "archive": inventory.pins[str(archive_path)],
            "exact_preserved_files": 20, "current_authority": False})
    package_path = ROOT / "review-package-02.json"
    package = inventory.qualified(package_path)
    need(package["schema"] == "terminal-dispatch-evidence-source-review-package@1"
         and package["files"] == 6 and package["modified"] == package["new"] == 3
         and package["exact_scratch_application"] is True and package["source_selected_bytes_unchanged"] is True
         and package["production_promoted"] is False and package["project_pushes"] == 0,
         "exact six-file review package has not qualified")
    inventory.add(package["patch"]["path"], package["patch"])
    for row in package["sources"]:
        inventory.add(row["current"]["path"], row["current"])
        inventory.add(row["applied"]["path"], row["applied"])
    return inventory.pins[str(freeze_path)], archives, inventory.pins[str(package_path)]


def write_exclusive(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-report", default=str(ROOT / "campaign-public-verification-03.json"))
    args = parser.parse_args()
    os.umask(0o077)
    status_path, config_path = ROOT / "improvement-status-01.json", ROOT / "seal-config-01.json"
    need(not status_path.exists() and not config_path.exists(), "exclusive finalizer output already exists")
    need(args.campaign_report == str(ROOT / "campaign-public-verification-03.json"), "one exact final campaign report required")
    inventory = Inventory()
    campaign = inventory.qualified(args.campaign_report)
    need(campaign["schema"] == "independent-public-dispatch-campaign-review@1"
         and campaign["selected_six_case_coverage_complete"] is True
         and campaign["full_dispatch_fault_matrix_complete"] is False
         and campaign["nonce_replay_live_qualified"] is False and campaign["missing_cases"] == [],
         "the final selected six-case public review has not qualified")
    report_by_case = {row["case"]: row for row in campaign["case_reports"]}
    need(set(report_by_case) == set(SELECTED) and len(campaign["case_reports"]) == 6, "final campaign selected cases differ")
    previous = inventory.qualified(ROOT / "previous-AA-seal-verification-01.json")
    need(previous.get("verified") is True, "sealed predecessor integrity verification did not pass")
    freeze_pin, archives, package_pin = collect_freezes_and_package(inventory)
    for case, tag in SELECTED.items():
        need(report_by_case[case]["run_tag"] == tag and report_by_case[case]["qualified"] is True
             and report_by_case[case]["runtime_freeze"] == freeze_pin, "final selected report/run/freeze differs")
    test_outcomes = collect_tests(inventory)
    runs = [collect_native_run(inventory, tag, selected=True, freeze_pin=freeze_pin) for tag in SELECTED.values()]
    history = [collect_native_run(inventory, tag) for tag in HISTORICAL]
    for name in EXTRA_PUBLIC_REPORTS:
        inventory.add(ROOT / name)
    for name in ("cache-pin.json",):
        inventory.add(ROOT / "public-tokenizer-cache" / name)
    bpe = inventory.add(BPE)
    need(bpe["bytes"] == BPE_BYTES and bpe["sha256"] == BPE_SHA256, "durable exact o200k BPE changed")
    inventory.add(Path(__file__).resolve())
    baseline = report_by_case["baseline"]["token_review"]
    need(baseline["offline_reference_token_replay_verified"] is True, "current baseline offline reference replay absent")
    complete = baseline["measures"]["complete_coding_input"]
    need(complete["tokens"] == 59434 and complete["bytes"] == 169373, "current baseline03 reference measurement differs")
    need(all(row["qualified_model_execution"] for row in runs), "selected native model qualification incomplete")
    inputs = sorted(inventory.pins.values(), key=lambda row: row["path"])
    status = {"schema": "terminal-dispatch-evidence-improvement-status@1", "qualified": True,
        "qualification_scope": "Six selected original native cases and independent supplied-public-data review; integrity preservation only.",
        "final_campaign": inventory.pins[args.campaign_report], "selected_cases": SELECTED,
        "selected_current_runtime_freeze": freeze_pin, "selected_native_runs": runs,
        "historical_native_run_outcomes": history, "historical_reports_preserved_without_requalification": True,
        "historical_exact_source_archives": archives, "source_review_package": package_pin,
        "test_attempt_outcomes": test_outcomes, "selected_distinct_tests": 1312,
        "selected_test_census": {"final-combined-02": 1188, "final-public-checks-01": 124},
        "current_baseline_complete_input": complete, "current_baseline_new_content": baseline["measures"]["new_content"],
        "reference_measurement_overrides_historical_baseline_measurements": True,
        "selected_native_Lean_processes": 18, "selected_conditional_Lean_compiles": 12, "selected_Lean_tool_probes": 6,
        "historical_only_qualified_model_Lean_processes": sum(row["reported_Lean_processes"] for row in history),
        "all_preserved_qualified_model_Lean_processes": sum(row["reported_Lean_processes"] for row in [*runs, *history]),
        "all_preserved_conditional_Lean_compiles": sum(row["reported_conditional_Lean_compiles"] for row in [*runs, *history]),
        "all_preserved_Lean_tool_probes": sum(row["reported_Lean_tool_probes"] for row in [*runs, *history]),
        "Lean_process_count_is_not_training_or_task_satisfaction": True,
        "nonce_replay_status": "open; no authentic native wrapper replay case qualified",
        "supplied_public_inputs_are_trust_inputs": True, "provider_calls": 0, "training_steps": 0,
        "durable_offline_BPE": bpe, "public_input_inventory": inputs,
        "public_input_file_count": len(inputs), "public_input_file_bytes": inventory.bytes,
        "public_input_file_set_sha256": hashlib.sha256(integrity.wire(inputs)).hexdigest(), **FALSE_CEILINGS}
    status_raw = integrity.wire(status) + b"\n"
    reports = [args.campaign_report, str(ROOT / "review-package-02.json"),
        str(ROOT / "final-combined-02-report.json"), str(ROOT / "final-public-checks-01-report.json"),
        str(ROOT / "previous-AA-seal-verification-01.json"), str(status_path)]
    files = sorted([*inventory.pins, str(status_path)])
    config_raw = integrity.wire({"schema": "terminal-dispatch-evidence-seal-config@1",
        "files": files, "qualified_reports": reports}) + b"\n"
    need(len(files) + 1 <= integrity.MAX_FILES and len(status_raw) <= 8 * 1024 * 1024
         and inventory.bytes + len(status_raw) + len(config_raw) <= integrity.MAX_TOTAL_BYTES,
         "final output seal census/body/total bound exceeded")
    # Every qualification, pin and bound above is checked before either output.
    write_exclusive(status_path, status_raw)
    write_exclusive(config_path, config_raw)
    print(json.dumps({"qualified": True, "status": str(status_path), "seal_config": str(config_path),
        "explicit_seal_files": len(files) + 1, "input_bytes": inventory.bytes,
        "selected_distinct_tests": 1312, "sealer_executed": False, "native_jobs_executed": False}))


if __name__ == "__main__":
    main()

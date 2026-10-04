"""Reconcile unadmitted TRAIN readiness, synthetic arithmetic and test evidence."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT / "external/ipfs_datasets"
CAMPAIGN = Path(__file__).resolve().parent
DIRECTORY = CAMPAIGN / "masked-contrastive-01"
PRIOR = CAMPAIGN / "stage-workflow-01/validation.json"
PRIOR_SHA = "9a3b95bd6b460abe9938923e012ac70e46783cf3e15ae9953b11c1f44a023fd8"
DOCUMENT = ROOT / "implementation_plan/docs/55-autoformalization-masked-contrastive-relations-2026-10-04.md"
NEW_FILES = (
    "ipfs_datasets_py/logic/formalization/autoencoder/alignment_masked_contrastive.py",
    "ipfs_datasets_py/logic/formalization/autoencoder/alignment_relation_declarations.py",
    "tests/unit/logic/formalization/autoencoder/test_alignment_masked_contrastive.py",
    "tests/unit/logic/formalization/autoencoder/test_alignment_relation_declarations.py",
)
TEST_GROUPS = {
    "stdlib": (NEW_FILES[3], "tests/unit/logic/formalization/autoencoder/test_alignment_lane_bundle.py",
               "tests/unit/logic/formalization/autoencoder/test_alignment_stage_declarations.py"),
    "native": (NEW_FILES[2], "tests/unit/logic/formalization/autoencoder/test_alignment_projection.py"),
}
HELPER_SHA = "7e428638cce2f3f011747fa8bc50502518a48665009e5f2aa9395097531411bb"
DRIVER_SHA = "5184ae6aa308b7a273ea4997df693b0ad3b467eb977fb75aeedbf43865523b55"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def binding(path):
    path = Path(path)
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def load(path, sha=None):
    if sha is not None:
        require(binding(path)["sha256"] == sha, "externally selected file differs: " + str(path))
    value = json.loads(Path(path).read_bytes())
    if type(value) is dict and "content_sha256" in value:
        require(value["content_sha256"] == digest({key: item for key, item in value.items() if key != "content_sha256"}),
                "content seal differs: " + str(path))
    return value


def iter_bindings(value):
    if type(value) is dict:
        if set(value) == {"path", "bytes", "sha256"}:
            yield value
        else:
            for item in value.values():
                yield from iter_bindings(item)
    elif type(value) is list:
        for item in value:
            yield from iter_bindings(item)


def zero_masks(value):
    names = {"weak_decoder_fit", "strong_semantic_fit", "contrastive_supervision", "proof_supervision", "fidelity_evaluation"}
    require(type(value) is dict and set(value) == names
            and all(type(mask) is int and mask == 0 for mask in value.values()), "supervision masks must remain exact0")


def main():
    require(len(sys.argv) == 3, "explicit relation and numerical assay file SHA selections required")
    for sha in sys.argv[1:]:
        require(re.fullmatch(r"[0-9a-f]{64}", sha), "canonical file SHA required")
    prior = load(PRIOR, PRIOR_SHA)
    checked = {}

    def check(expected):
        require(binding(expected["path"]) == expected, "bound file changed: " + expected["path"])
        checked[expected["path"]] = expected

    for expected in prior["checked_file_bindings"]:
        check(expected)
    require(len(checked) == prior["checked_file_count"] == 190, "prior190 accounting differs")
    relation_path = DIRECTORY / "relations/assay.json"
    relation = load(relation_path, sys.argv[1])
    for expected in iter_bindings(relation):
        check(expected)
    sys.path.insert(0, str(CAMPAIGN))
    import assay_relation_readiness as readiness

    prepared = readiness.prepare_assay()
    for name in ("declaration", "expected_bindings", "validation"):
        saved = load(relation["artifacts"][name]["path"])
        require(raw(saved) == raw(prepared[name]), "historical relation readiness exact replay differs")
    require(prepared["input_file_bindings"] == relation["input_file_bindings"]
            and prepared["source_bindings"] == relation["source_bindings"], "readiness source/file selections differ")
    require(relation["pair_count"] == 256 and relation["weak_structural_identity_pair_count"] == 16
            and relation["unknown_pair_count"] == 240, "historical pair accounting differs")
    require(relation["admitted_positive_pair_count"] == relation["permitted_negative_pair_count"] == 0
            and relation["masked_numerical_loss_eligible"] is False
            and relation["masked_numerical_loss_executed"] is False, "historical readiness promoted a numerical objective")
    zero_masks(relation["masks"])
    numerical_path = DIRECTORY / "numerical-02/numerical_assay.json"
    numerical = load(numerical_path, sys.argv[2])
    for expected in iter_bindings(numerical):
        check(expected)
    numerical_summary = validate_numerical(numerical)
    recovery_summary = validate_recovery(numerical, check, checked)
    test_counts, tests_by_source, commands = {}, {}, {}
    for group, sources in TEST_GROUPS.items():
        xml_path = DIRECTORY / (group + "-tests.xml")
        suite = ET.parse(xml_path).getroot().find("testsuite")
        require(suite is not None, "test suite XML missing")
        counts = {name: int(suite.attrib[name]) for name in ("tests", "errors", "failures", "skipped")}
        require(counts["tests"] > 0 and counts["errors"] == counts["failures"] == counts["skipped"] == 0,
                "targeted tests did not all pass")
        symbols = {}
        group_counts = {}
        for relative in sources:
            tree = ast.parse((REPO / relative).read_text())
            names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")}
            for name in names:
                require(name not in symbols, "ambiguous test function across selected source group")
                symbols[name] = relative
            group_counts[relative] = sum(case.attrib["name"].split("[", 1)[0] in names for case in suite.findall("testcase"))
        require(all(group_counts.values()) and sum(group_counts.values()) == counts["tests"], "test source attribution differs")
        test_counts[group], tests_by_source[group] = counts, group_counts
        commands[group] = load(DIRECTORY / (group + "-command.json"))
        require(commands[group]["exit_code"] == 0, "recorded test command failed")
        for suffix in ("tests.xml", "tests.txt", "command.json"):
            check(binding(DIRECTORY / (group + "-" + suffix)))
    ruff_path = DIRECTORY / "ruff-02.txt"
    require(ruff_path.read_text().strip() == "All checks passed!", "Ruff evidence failed")
    lint = load(DIRECTORY / "ruff-02-command.json")
    require(lint["exit_code"] == 0, "lint command failed")
    for expected in lint["checked_source_bindings"]:
        check(expected)
    output = DIRECTORY / "validation.json"
    links = []
    for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", DOCUMENT.read_text()):
        if target.startswith(("http://", "https://", "#")):
            continue
        path = (DOCUMENT.parent / target.split("#", 1)[0]).resolve()
        require(path == output or path.is_file(), "local document link missing: " + str(path))
        links.append(str(path))
        if path != output:
            check(binding(path))
    for path in [*(REPO / relative for relative in NEW_FILES), *(REPO / relative for sources in TEST_GROUPS.values() for relative in sources),
                 Path(__file__), CAMPAIGN / "assay_relation_readiness.py", CAMPAIGN / "assay_masked_contrastive.py",
                 CAMPAIGN / "assay_masked_contrastive_native.py", PRIOR, relation_path, numerical_path,
                 DOCUMENT, ruff_path, DIRECTORY / "ruff-02-command.json", DIRECTORY / "ruff.txt", DIRECTORY / "ruff-command.json"]:
        check(binding(path))
    total_tests = sum(counts["tests"] for counts in test_counts.values())
    result = {
        "schema": "autoformalization-masked-contrastive-validation/v1",
        "status": "passed_synthetic_arithmetic_and_unadmitted_relation_readiness_only",
        "created_utc": datetime.now(UTC).isoformat(), "checked_file_count": len(checked),
        "checked_file_bindings": sorted(checked.values(), key=lambda value: value["path"]),
        "prior_stage_workflow_binding": binding(PRIOR), "prior190_file_bindings_rechecked": True,
        "previous554_file_chain_rechecked": False, "complete_dependency_manifest": False,
        "prior_existing_legacy_manifest_mismatch_preserved": prior["prior_existing_legacy_manifest_mismatch_preserved"],
        "legacy_manifest_mismatch_retested_this_stage": False,
        "document_binding": binding(DOCUMENT), "local_link_count": len(links),
        "relation_assay_binding": binding(relation_path), "numerical_assay_binding": binding(numerical_path),
        "targeted_test_counts": test_counts, "total_targeted_tests": total_tests,
        "tests_by_source_function_names": tests_by_source,
        "prepublication_verifier_corrections": ["successful_child_stderr_contains_a_recorded_scalar_conversion_warning"],
        "test_fixtures_semantic_gold": False, "final_ruff_passed": True, "ruff_checked_files": len(lint["files"]),
        "relation_readiness_exact_replay": {"train_rows": 16, "pairs": 256, "weak_identity": 16,
            "unknown": 240, "admitted_positive": 0, "permitted_negative": 0,
            "positive_mask_true_count": 0, "negative_mask_true_count": 0, "historical_numerical_loss_executed": False},
        "numerical_checks": numerical_summary, "recovery_checks": recovery_summary,
        "old_losses_or_checkpoint_profiles_modified": False, "semantic_training_worker_implemented": False,
        "authenticated_relation_to_tensor_handoff_implemented": False,
        "objective_bound_checkpoint_reload_contract_implemented": False,
        "os_reference_file_confinement_established": False, "derivative_exclusion_authenticated": False,
        "broad_pilot_family_count": 40, "broad_pilot_semantic_evaluation_executed": False,
        "labels_admitted": 0, "formal_targets_admitted": 0, "encoder_calls": 0, "prover_calls": 0,
        "production_model_calls": 0, "optimizer_updates": 0, "semantic_fit_updates": 0,
        "source_fidelity_established": False, "proof_authority": False, "leanstral_runtime_qualified": False,
        "production_defaults_changed": False, "existing_decoder_checkpoints_modified": False,
        "existing_original_train_masks_unchanged": True, "renderer_preview_inspected": False,
        "masks": dict.fromkeys(("weak_decoder_fit", "strong_semantic_fit", "contrastive_supervision", "proof_supervision", "fidelity_evaluation"), 0),
    }
    result["content_sha256"] = digest(result)
    for selected in checked.values():
        require(binding(selected["path"]) == selected, "final checked file changed")
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw(result) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(raw({"validation_binding": binding(output), "checked_file_count": len(checked),
               "total_targeted_tests": total_tests, "relation_pairs": 256, "admitted_pairs": 0,
               "numerical_checks": numerical_summary}).decode())


def validate_numerical(numerical):
    require(numerical["status"] == "completed_synthetic_engineering_checks_no_training_admission", "numeric worker failed")
    zero_masks(numerical["masks"])
    checks = numerical["checks"]
    require(checks["content_sha256"] == digest({key: item for key, item in checks.items() if key != "content_sha256"}),
            "numerical checks seal differs")
    zero_masks(checks["masks"])
    require(checks["all_checks_passed"] is True and checks["production_model_calls"] == checks["optimizer_updates"] == 0
            and checks["historical_training_vector_objective_inputs"] == checks["model_weight_load_calls"] == 0,
            "synthetic checks used real training inputs or updated a model")
    require(checks["synthetic_untrained_projection_model_count"] == 2
            and checks["synthetic_untrained_linear_module_count"] == 4
            and checks["synthetic_initialized_parameter_tensor_count"] == 8
            and checks["observed_fixture_linear_forward_count"] == 4, "fixture model activity accounting differs")
    for item in checks["checks"]["legacy_parity"]:
        require(item["value_bitwise_equal"] is True and item["both_representation_gradients_bitwise_equal"] is True,
                "legacy parity missing")
    require(checks["checks"]["unknown_pair_gradient_isolation"]["unknown_pair_logit_gradients_exact_zero"] is True
            and checks["checks"]["global_no_negative_signal"]["loss_exact_zero"] is True
            and checks["checks"]["double_gradcheck"]["passed"] is True, "exclusion/zero/gradcheck failed")
    for head in checks["checks"]["untrained_projection_head_backward"]:
        require(head["state_sha256_before"] == head["state_sha256_after"]
                and head["source_parameter_gradients_finite_nonzero"] is True
                and head["formal_parameter_gradients_finite_nonzero"] is True, "fixture gradients changed weights or failed")
    require(numerical["model_checkpoint_load_attempts"] == numerical["forbidden_import_attempts"] == []
            and numerical["cuda_initialized"] is False and numerical["os_sandbox"] is False, "numeric resource/import scope differs")
    observations = numerical["resource_observations"]
    require(observations and max(row["linux_peak_hwm_kib"] for row in observations)
            < numerical["resource_limits"]["cooperative_rss_kib"], "observed numerical memory gate failed")
    return {"legacy_parity_dtypes": [item["dtype"] for item in checks["checks"]["legacy_parity"]],
            "unknown_logit_gradients_zero": True, "global_no_negative_zero_signal": True,
            "double_gradcheck_passed": True, "both_untrained_heads_have_finite_gradients": True,
            "fixture_models_initialized": 2, "fixture_linear_forward_calls": 4,
            "fixture_parameter_scalar_count": checks["synthetic_initialized_parameter_scalar_count"],
            "fixture_weights_unchanged": True, "optimizer_updates": 0, "production_model_calls": 0,
            "torch_version": checks["torch_version"], "device": checks["device"],
            "maximum_observed_rss_kib": max(row["linux_peak_hwm_kib"] for row in observations),
            "rss_limit_is_cooperative_observation_not_hard_address_space_cap": True,
            "finite_gradient_claim_scope": checks["finite_gradient_scope"]}


def selected_module(path, sha, name):
    # Independently verify and execute the same bounded bytes, including in the
    # native child. No loaded helper function participates in this verification.
    data = path.read_bytes()
    require(0 < len(data) <= 16 * 1024**2 and hashlib.sha256(data).hexdigest() == sha,
            "independently selected replay source differs before execution")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


def verified_replay_child():
    helper = selected_module(CAMPAIGN / "assay_masked_contrastive.py", HELPER_SHA, "root_verified_masked_numerical_helper")
    driver = selected_module(CAMPAIGN / "assay_masked_contrastive_native.py", DRIVER_SHA, "root_verified_masked_native_driver")
    # The child calls the original fresh-fork numerical worker using the helper
    # already verified here. It never calls the frozen driver's late-pin loader.
    return driver._child(helper, None, True)


def bounded_verified_replay():
    environment = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "CUDA_VISIBLE_DEVICES": "",
                   "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                   "PYTHONDONTWRITEBYTECODE": "1", "IPFS_DATASETS_AUTO_INSTALL_TEST_DEPS": "0",
                   "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    command = ["/home/barberb/.local/bin/python", "-I", "-B", str(Path(__file__).resolve()), "--verified-replay-child"]
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(command, cwd="/tmp", env=environment, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise TimeoutError("verified numerical replay exceeded parent wall limit") from None
        require(stdout.tell() <= 8 * 1024**2 and stderr.tell() <= 8 * 1024**2, "verified replay output exceeded bounds")
        stdout.seek(0)
        stderr.seek(0)
        data, errors = stdout.read(8 * 1024**2 + 1), stderr.read(8 * 1024**2 + 1)
    require(process.returncode == 0, "verified replay failed: " + errors.decode("utf-8", "replace"))
    return json.loads(data.decode("utf-8", errors="strict"))


def validate_recovery(numerical, check, checked):
    helper_path = CAMPAIGN / "assay_masked_contrastive.py"
    helper_sha = HELPER_SHA
    driver_path = CAMPAIGN / "assay_masked_contrastive_native.py"
    driver_sha = DRIVER_SHA
    failed_shas = {
        "failure.json": "3421dd50397c2a00a88cba8f6a1298e0dab6ec2b9e2144e20a3dadc895ed2c39",
        "child_exit.json": "be6c759906081f70902c29b2d5f31c332903bbe0fe3f52c990f7e8ea1e370a02",
        "resource_observations.jsonl": "92d06b3b4b3cd1cde1496a78faf4855dc3c7acab4f87a1e936acdc398b163d03",
    }
    for filename, sha in failed_shas.items():
        selected = binding(DIRECTORY / "numerical" / filename)
        require(selected["sha256"] == sha, "first failed attempt changed")
        check(selected)
    failure = load(DIRECTORY / "numerical/failure.json")
    failed_exit = load(DIRECTORY / "numerical/child_exit.json")
    require(failure["error_type"] == "ModuleNotFoundError" and failure["error_message"] == "No module named 'torch'"
            and [row["label"] for row in failure["resource_observations"]] == ["before_torch_import"]
            and failure["optimizer_updates"] == 0 and failed_exit["returncode"] == 1,
            "failed attempt phase/accounting differs")
    zero_masks(failure["masks"])
    zero_masks(failed_exit["masks"])
    selection_path = DIRECTORY / "numerical-02/native_selection.json"
    exit_path = DIRECTORY / "numerical-02/native_child_exit.json"
    selection = load(selection_path, "a40630619f33b5341de8f7c1eb2e02945f847598b848e982c254ddbc0c9b308c")
    exit_receipt = load(exit_path, "9d073d5900e2daf33fa4d5b017b2596f827996cc801b777f9220442606b88f50")
    for value in (selection, exit_receipt):
        for expected in iter_bindings(value):
            check(expected)
        zero_masks(value["masks"])
    check(binding(selection_path))
    check(binding(exit_path))
    require(selection["driver_binding"] == binding(driver_path)
            and selection["driver_binding"]["sha256"] == driver_sha
            and selection["original_implementation_bindings"] == numerical["checks"]["implementation_bindings"],
            "recovery source selections differ")
    require(selection["site_selection_method"] == "sys.path.insert_only_no_addsitedir_no_pth"
            and selection["torch_distribution_version"] == "2.13.0"
            and selection["torch_init_binding"]["sha256"] == "cf40c075c95864036e835795756d69b8cccfafa76f3bcde5eba9d06065ccd3d1",
            "native installation selection differs")
    require(exit_receipt["returncode"] == 0 and exit_receipt["stdout_bytes"] == 0
            and exit_receipt["stderr_bytes"] == len(exit_receipt["stderr_utf8"].encode()) == 434
            and "UserWarning: Converting a tensor with requires_grad=True to a scalar" in exit_receipt["stderr_utf8"]
            and exit_receipt["selection_binding"] == binding(selection_path), "successful recovery exit differs")
    journal_path = numerical["resource_journal_binding"]["path"]
    journal = [json.loads(line) for line in Path(journal_path).read_bytes().splitlines()]
    require(raw(journal) == raw(numerical["resource_observations"]), "resource journal/report differ")

    for path, sha in ((helper_path, helper_sha), (driver_path, driver_sha)):
        selected = binding(path)
        require(selected["sha256"] == sha, "verified replay source selection differs")
        check(selected)
    replay = bounded_verified_replay()
    require(raw(replay) == raw(numerical["checks"]), "bounded no-write numerical checks exact replay differs")
    for selected in checked.values():
        require(binding(selected["path"]) == selected, "source/input changed during numerical replay")
    return {
        "first_failed_attempt_preserved": True, "first_failure_phase": "before_torch_import",
        "first_failed_attempt_objective_calls": 0, "first_failed_attempt_optimizer_updates": 0,
        "native_child_returncode": 0, "explicit_native_site_selected_without_processing_its_pth_files": True,
        "native_child_recorded_scalar_conversion_warning_bytes": 434,
        "torch_initializer_and_distribution_selected": True, "all_framework_binaries_pinned": False,
        "resource_journal_exact_replay": True, "resource_snapshot_count": len(journal),
        "bounded_numerical_checks_exact_replay": True, "replay_persistent_artifact_writes": 0,
        "root_replay_source_bytes_verified_before_execution": True,
        "root_replay_native_child_executes_exact_verified_helper_bytes": True,
        "standalone_driver_helper_hash_verified_before_initial_execution": False,
        "standalone_loader_ordering_remediation_requires_separate_immutable_version": True,
        "observed_wrong_helper_execution": False,
        "worker_os_sandbox": False,
    }


if __name__ == "__main__":
    if sys.argv[1:] == ["--verified-replay-child"]:
        raise SystemExit(verified_replay_child())
    main()

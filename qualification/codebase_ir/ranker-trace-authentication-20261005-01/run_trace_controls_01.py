"""Fresh admitted finite trace, Std/kernel and native metadata qualification."""
from __future__ import annotations

import datetime
from fractions import Fraction
import hashlib
import importlib.abc
import importlib.machinery
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[2]
ARTIFACTS = WORKSPACE / "artifacts/codebase_ir_terminal_bench"
HEAD = ARTIFACTS / "terminal-codebase-ir-intent-corpus-head-20261004-01"
CAP = ARTIFACTS / "terminal-codebase-ir-learned-intent-join-20261004-01/source-generation-08"
SELECTOR = WORKSPACE / "qualification/codebase_ir/selector-semantics-20261004-01"
REVIEW = WORKSPACE / "qualification/codebase_ir/ranker-convergence-obligations-20261005-01/review.json"
BASE_SHA = "5efc3725539ced8b5a0f6e172c3b4c7e92fccc158940feaa71b4890a054203a3"
BASE_CID = "sha256:30d08864e562515c29af9c138f944a70626361137a8ae3721f532a6b6014a5fa"
MODULE_SHA = "d89e83376367b3114cca967797677e0982a27cab78797ebfca0d7a1c1807c364"
TEST_SHA = "5e5d1791233b279654b2e616866e7b73d5028c6cf64d5b0f805b29a07e56092d"
ROOTS = (ROOT / "source", HEAD / "source", CAP / "accelerate", CAP / "datasets", CAP / "kit")
AUTHORITY = {name: False for name in ("proof_authority", "formalization_authority",
    "execution_authority", "completion_authority", "mutation_authority", "omission_authority",
    "source_semantics_verified", "semantic_alignment_verified", "behavioral_satisfaction",
    "whole_program_proved", "asymptotic_optimizer_convergence_proved")}
SCOPE = ("Finite native replay and exact integer order of authenticated rounded objective observations only; "
    "historical execution/pin origin, whole Python/source/task, exact-real logistic/binary64 error, "
    "global/asymptotic/autoencoder convergence and generalized gains remain unproved; "
    "all 32 governing RPI exits OPEN, planner inactive, official score null.")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode()


def pin(path):
    path = Path(path); before = path.lstat()
    assert path.resolve(strict=True) == path and stat.S_ISREG(before.st_mode) and before.st_nlink == 1
    raw = path.read_bytes(); after = path.lstat()
    signature = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    assert signature(before) == signature(after) and path.resolve(strict=True) == path
    return {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}


def read_pinned(row):
    assert pin(row["path"]) == row
    raw = Path(row["path"]).read_bytes()
    assert len(raw) == row["bytes"] and sha(raw) == row["sha256"] and pin(row["path"]) == row
    return raw


def write(path, body, *, compact=False, maximum=None):
    raw = canonical(body) if compact else (json.dumps(body, sort_keys=True, indent=2,
        ensure_ascii=False, allow_nan=False) + "\n").encode()
    assert maximum is None or len(raw) <= maximum, "unchanged retained output bound exceeded"
    with Path(path).open("xb") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def prepare(inventory_path):
    (ROOT / "preparation").mkdir(); (ROOT / "evidence").mkdir()
    inventory_pin = pin(Path(inventory_path).resolve(strict=True))
    inventory = json.loads(read_pinned(inventory_pin))
    strict = inventory["strict_pinned_inputs"]
    assert len(strict) == 348
    for row in strict:
        assert pin(row["path"])["sha256"] == row["sha256"]
    protected = []
    for relative, expected_sha in (
        ("ipfs_accelerate_py/agent_supervisor/planning/finite_proof_query_join.py", "d6e4a6187036f5942f4637dd24bec65c1a90ed32c24e3b39e3759e653be03b79"),
        ("ipfs_accelerate_py/agent_supervisor/runtime/finite_proof_query_admission.py", "2e5b0add5f19c1c31ad76dae67354d5bfadbfe59303a06590db14507c3abe7e4"),
        ("test/api/test_finite_proof_query_join.py", "d34cd489d69446bb4c88e6f8881fff44689cbf6c6944c1976fb411f77a06f890"),
        ("test/api/test_finite_proof_query_admission.py", "6867188f535b6e24cf2a217b5d601a9d92446bff3ba382800e8664c6a0650de0")):
        row = pin(WORKSPACE / "external/ipfs_accelerate" / relative)
        assert row["sha256"] == expected_sha; protected.append(row)
    review_pin = pin(REVIEW)
    assert review_pin["sha256"] == "dd70a5e366a629ef45773100402a6995e7ee9c5d4ec4d7338fdf46973c177856"
    envelope = pin(HEAD / "frozen-corpus/2a452811f54d85509e2d0b0c962ecab5d8cd221a6cd0321556a387c95da0a8e7.json")
    assert envelope["bytes"] == 2029591 and envelope["sha256"] == "2a452811f54d85509e2d0b0c962ecab5d8cd221a6cd0321556a387c95da0a8e7"
    output_pins = pin(HEAD / "evidence/actual-02/fit-output-pins.json")
    assert output_pins["sha256"] == "cc61f5b8e65cfdc79ba870740811fef9944425f9e4d0cc2417fc25144b2b2e48"
    fitted = json.loads(read_pinned(output_pins)); read_pinned(fitted["ranker_result"])
    assert fitted["ranker_result"]["sha256"] == "6a6b7eaa20bf1a82a958ff6c9a6ab6f64c613fb880569a76b625de156284d60a"
    prior = pin(SELECTOR / "evidence/actual-08/metadata-inputs.json")
    assert prior["bytes"] == 8032009 and prior["sha256"] == "63196d5a27088a82045a8a0bcac4a9b8cab31b49cff75dc1fd7088607a7dad14"
    lean = pin(Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.0/bin/lean"))
    assert lean["sha256"] == "79fb1d26fa5a39385d59fdc48a711a14b0710ca6480271acce99b4d177cea085"
    request = {"schema": "terminal-ranker-trace-qualification-request@1", "scope": SCOPE,
        "review": review_pin, "original_corpus_envelope": envelope,
        "external_fit_output_pins": output_pins, "original_ranker_result": fitted["ranker_result"],
        "expected_checkpoint_sha256": fitted["checkpoint_sha256"],
        "expected_training_receipt_sha256": fitted["training_receipt_sha256"],
        "expected_original_corpus_sha256": "sha256:d4aa22b9a7bfe796c31adbcf78f9b72987549a85117b8f08534f5a06c032a3df",
        "prior_metadata_inputs": prior, "native_lean": lean, "strict_old_input_inventory": inventory_pin,
        "strict_old_inputs": strict, "protected_live_sources": protected,
        "max_replay_coordinate_operations": 1_000_000, "native_retention_max_bytes": 65536,
        "native_lean_timeout_seconds": 20, "native_lean_cpu_seconds": 20,
        "native_lean_workspace_bytes": 16 * 1024 * 1024, "outer_timeout_seconds": 120,
        "whole_source_runtime_equivalence_proved": False, "full_task_satisfaction": "unknown",
        "all32_governing_RPI_exits": "OPEN", "planner_activation": False,
        "official_benchmark_score": None, **AUTHORITY}
    write(ROOT / "preparation/request.json", request)
    destination = ROOT / "source"; destination.mkdir()
    files = []
    entries = [(WORKSPACE / "external/ipfs_accelerate", relative, expected) for relative, expected in (
        ("benchmarks/agent_supervisor/container_coding/terminal_codebase_ranker_trace_authentication.py", MODULE_SHA),
        ("test/api/test_terminal_codebase_ranker_trace_authentication.py", TEST_SHA))]
    entries += [(HEAD / "source", relative, None) for relative in (
        "test/api/test_terminal_codebase_intent_corpus.py", "test/__init__.py", "test/api/__init__.py")]
    for base, relative, expected in entries:
        original = pin(base / relative); raw = read_pinned(original)
        assert expected is None or original["sha256"] == expected
        target = destination / relative; target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream: stream.write(raw)
        target.chmod(0o444); files.append({"original": original, "captured": pin(target)})
    config = destination / "pytest.ini"; config.write_text("[pytest]\n"); config.chmod(0o444)
    files.append({"captured": pin(config)})
    base_manifest = pin(CAP / "generation-manifest.json"); assert base_manifest["sha256"] == BASE_SHA
    head_manifest = pin(HEAD / "source-manifest.json")
    assert head_manifest["sha256"] == "97c6209ba34351cdfbd347d4620bb19059b51ecbbd0be7022a0943f478e702bb"
    write(ROOT / "source-manifest.json", {"schema": "terminal-ranker-trace-source-extension@1",
        "base_manifest": base_manifest, "base_generation_cid": BASE_CID,
        "extension_manifests": [head_manifest], "files": files,
        "scope": "Read-only bounded additive capture and selected owned imports; no whole-live or atomic loader claim."})
    for directory in sorted((p for p in destination.rglob("*") if p.is_dir()), reverse=True):
        directory.chmod(0o555)
    destination.chmod(0o555)
    write(ROOT / "preparation/producer-pins.json", {"driver": pin(Path(__file__).resolve()),
        "source_manifest": pin(ROOT / "source-manifest.json"), "request": pin(ROOT / "preparation/request.json")})
    print(json.dumps({"status": "prepared", "source_manifest": pin(ROOT / "source-manifest.json")}))


class Guard(importlib.abc.MetaPathFinder):
    def __init__(self, expected):
        self.expected = expected; self.records = {}; self.blocked = []

    def find_spec(self, fullname, path=None, target=None):
        if not any(fullname == prefix or fullname.startswith(prefix + ".") for prefix in
            ("benchmarks", "ipfs_accelerate_py", "ipfs_datasets_py", "ipfs_kit_py", "ipfs_kit", "test")):
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is None: raise ImportError("captured owned module unavailable: " + fullname)
        if spec.origin is not None:
            actual = pin(spec.origin)
            if self.expected.get(actual["path"]) != actual:
                self.blocked.append({"module": fullname, "origin": spec.origin})
                raise ImportError("owned source drift: " + fullname)
            self.records[fullname] = actual
        else:
            assert all(any(Path(value).is_relative_to(root) for root in ROOTS)
                       for value in spec.submodule_search_locations or [])
        return spec


def verify_old(request):
    for row in request["strict_old_inputs"]:
        actual = pin(row["path"])
        assert actual["sha256"] == row["sha256"]
        if "bytes" in row: assert actual["bytes"] == row["bytes"]
    for row in request["protected_live_sources"]: assert pin(row["path"]) == row


def run_tests(run, receipt, head):
    import pytest
    fits, phases = [], []
    original_fit = head.train_terminal_codebase_intent_ranker
    def observed_fit(**arguments):
        row = {"scope": "authored_synthetic_unit_fixture_only", "epochs": arguments.get("epochs", 64), "status": "invoked"}
        fits.append(row)
        result = original_fit(**arguments); row.update(status="completed", corpus_sha256=result["corpus_sha256"])
        return result
    head.train_terminal_codebase_intent_ranker = observed_fit
    class Reports:
        def pytest_runtest_logreport(self, report):
            phases.append({"nodeid": report.nodeid, "phase": report.when,
                "outcome": report.outcome, "seconds": report.duration})
    started = time.monotonic()
    code = int(pytest.main(["-q", "-p", "no:cacheprovider", "-c", str(ROOT / "source/pytest.ini"),
        "--noconftest", "-o", "addopts=", "--basetemp", str(run / "fixtures"),
        "--junitxml", str(run / "tests.xml"), str(ROOT / "source/test/api/test_terminal_codebase_ranker_trace_authentication.py")],
        plugins=[Reports()]))
    receipt["test_seconds"] = time.monotonic() - started
    receipt["pytest_returncode"] = code; receipt["synthetic_fit_observations"] = fits
    receipt["synthetic_unit_fit_calls"] = len(fits)
    receipt["synthetic_unit_optimizer_fit_updates"] = sum(row["epochs"] for row in fits)
    receipt["false_control_cost_scope"] = "unit controls may stop at first mismatching replay epoch; no second original 128-update replay"
    write(run / "phases.json", phases)
    calls = [row for row in phases if row["phase"] == "call"]
    receipt["selected_test_count"] = len(calls)
    assert code == 0 and len(calls) == 64 and all(row["outcome"] == "passed" for row in phases)
    assert len(fits) == 1 and fits[0]["epochs"] == 16 and fits[0]["status"] == "completed"


def run_actual(run, receipt, request, head):
    from benchmarks.agent_supervisor.container_coding import terminal_codebase_ranker_trace_authentication as api
    envelope = json.loads(read_pinned(request["original_corpus_envelope"]))
    result = json.loads(read_pinned(request["original_ranker_result"]))
    assert envelope["corpus"]["corpus_sha256"] == result["corpus_sha256"] == request["expected_original_corpus_sha256"]
    counters = {"native_preparation_calls": 0, "gradient_evaluations": 0, "replay_gradient_evaluations": 0}
    prepare_original, objective_original, replay_original = head._prepare, head._objective, api._replay_observation
    def observe_prepare(*args, **kwargs):
        counters["native_preparation_calls"] += 1; return prepare_original(*args, **kwargs)
    def observe_objective(*args, **kwargs):
        counters["gradient_evaluations"] += 1; return objective_original(*args, **kwargs)
    def observe_replay(*args, **kwargs):
        counters["replay_gradient_evaluations"] += 1; return replay_original(*args, **kwargs)
    head._prepare = observe_prepare; head._objective = observe_objective; api._replay_observation = observe_replay
    arguments = {"corpus_receipt": envelope["corpus"], "original_inputs": envelope["original_inputs"],
        "expected_checkpoint_sha256": request["expected_checkpoint_sha256"],
        "expected_training_receipt_sha256": request["expected_training_receipt_sha256"],
        "expected_ranker_result_sha256": head._digest(result),
        "max_coordinate_operations": request["max_replay_coordinate_operations"]}
    binding = {"schema": "terminal-ranker-raw-file-canonical-binding@1", "raw_file": request["original_ranker_result"],
        "canonical_complete_result_sha256": arguments["expected_ranker_result_sha256"],
        "native_result_self_sha256": result["result_sha256"],
        "canonical_digest_includes_native_result_self_field": True,
        "canonicalization": "native training join sorted compact ensure_ascii=True finite JSON",
        "pin_origin_authenticated_here": False}
    write(run / "raw-canonical-binding.json", binding)
    started = time.monotonic()
    authentication = api.authenticate_terminal_ranker_training_trace(result, **arguments)
    receipt["native_authentication_seconds"] = time.monotonic() - started
    receipt["actual_authentication_calls"] = 1; receipt["observed_native_counts"] = counters
    assert counters == {"native_preparation_calls": 2, "gradient_evaluations": 131, "replay_gradient_evaluations": 129}
    assert authentication["epochs"] == 128 and authentication["train_pair_count"] == 4
    assert authentication["optimizer_replay_updates"] == 128 and len(authentication["authenticated_states"]) == 129
    assert authentication["recorded_trace_sha256"] == authentication["authenticated_trace_sha256"] == head._digest(result["training_receipt"]["trace"])
    assert authentication["authentication_sha256"] == head._digest({key: value for key, value in authentication.items() if key != "authentication_sha256"})
    write(run / "authentication-result.json", authentication, compact=True, maximum=65536)
    receipt["authentication_result"] = pin(run / "authentication-result.json")
    receipt["actual_optimizer_verification_updates"] = 128
    # Prepare the exact integer mapping only after every native replay check passes.
    fractions = [Fraction.from_float(row["objective"]) for row in result["training_receipt"]["trace"]]
    denominator = max(value.denominator for value in fractions)
    units = [int(value * denominator) for value in fractions]
    assert denominator > 0 and all(Fraction(unit, denominator) == value for unit, value in zip(units, fractions))
    assert len(units) == 129 and all(unit > 0 for unit in units)
    assert all(left > right for left, right in zip(units, units[1:]))
    mapping = {"schema": "terminal-authenticated-native-objective-common-units@1",
        "authentication_sha256": authentication["authentication_sha256"],
        "native_update_profile_sha256": authentication["native_update_profile_sha256"],
        "corpus_sha256": authentication["corpus_sha256"], "checkpoint_sha256": authentication["checkpoint_sha256"],
        "training_receipt_sha256": authentication["training_receipt_sha256"], "ranker_result_sha256": authentication["ranker_result_sha256"],
        "recorded_trace_sha256": authentication["recorded_trace_sha256"],
        "authenticated_states_sha256": authentication["authenticated_states_sha256"],
        "common_denominator": str(denominator), "loss_units": [str(unit) for unit in units],
        "exact_fraction_roundtrip_checked": True, "observations": 129, "strict_adjacent_declines": 128,
        "proof_scope": "exact integer order of real embeddings of authenticated rounded native objective observations",
        "python_fraction_conversion_kernel_proved": False, "exact_real_logistic_descent_proved": False,
        "whole_source_runtime_equivalence_proved": False, "full_task_satisfaction": "unknown", **AUTHORITY}
    source = "\n".join(["import Std", "set_option autoImplicit false", "namespace AuthenticatedFiniteNativeLossOrder",
        "-- Integer order of authenticated rounded observations only; no Float/libm/logistic convergence theorem.",
        "def commonDenominator : Nat := " + str(denominator),
        "def lossUnits : List Nat := [" + ", ".join(map(str, units)) + "]",
        "def strictlyDeclining : List Nat → Bool", "  | [] => true", "  | [_] => true",
        "  | left :: right :: rest => decide (right < left) && strictlyDeclining (right :: rest)",
        "theorem finite_observed_native_value_order :", "    0 < commonDenominator ∧ lossUnits.length = 129 ∧",
        "    lossUnits.all (fun unit => decide (0 < unit)) = true ∧ strictlyDeclining lossUnits = true := by",
        "  decide +kernel", "end AuthenticatedFiniteNativeLossOrder", ""])
    negative = source + "\nnamespace AuthenticatedFiniteNativeLossOrder\n" + (
        "theorem false_reversed_observation_chain : strictlyDeclining lossUnits.reverse = true := by\n"
        "  decide +kernel\nend AuthenticatedFiniteNativeLossOrder\n")
    mapping["generated_lean_source_sha256"] = sha(source.encode())
    mapping["negative_lean_source_sha256"] = sha(negative.encode())
    write(run / "finite-objective-mapping.json", mapping, compact=True, maximum=65536)
    from benchmarks.agent_supervisor.container_coding import terminal_codebase_logic_qualification as logic
    output = run / "lean"; output.mkdir(); checks = []
    for key, filename, text, expected in (
        ("finite_native_observation_order", "AuthenticatedFiniteLossOrder.lean", source, True),
        ("false_reversed_observation_chain", "FalseReversedLossOrder.lean", negative, False)):
        assert pin(request["native_lean"]["path"]) == request["native_lean"]
        receipt["native_lean_checks_invoked"].append({"key": key, "expected_success": expected})
        check = logic._compile_lean(executable=Path(request["native_lean"]["path"]), filename=filename,
            source=text, output=output, expected_success=expected)
        check.update(key=key, authentication_sha256=authentication["authentication_sha256"],
            mapping=pin(run / "finite-objective-mapping.json"), original_corpus_sha256=authentication["corpus_sha256"],
            native_bounds={"max_output_bytes": 65536, "max_workspace_bytes": 16777216, "timeout_seconds": 20, "cpu_seconds": 20},
            finite_statement_scope=mapping["proof_scope"], exact_real_logistic_descent_proved=False,
            full_task_satisfaction="unknown", planner_activation=False)
        checks.append(check); write(run / ("lean-" + key + "-check.json"), check, compact=True, maximum=65536)
        assert check["matches_expectation"] is True, "native Lean check failed or inconclusive: " + key
        assert all(row["bytes"] <= 65536 for row in check["compiled_artifacts"])
    write(run / "lean-checks.json", checks, compact=True, maximum=65536)
    receipt["finite_observed_value_order_checked"] = True
    receipt["finite_objective_mapping"] = pin(run / "finite-objective-mapping.json")
    receipt["lean_checks"] = pin(run / "lean-checks.json")


def run_metadata(run, receipt, request, producers):
    actual = ROOT / "evidence/actual-01"
    closed = pin(actual / "closed.json"); actual_receipt = json.loads(read_pinned(closed))
    assert actual_receipt["status"] == "passed" and actual_receipt["actual_authentication_calls"] == 1
    auth_pin = actual_receipt["authentication_result"]
    auth = json.loads(read_pinned(auth_pin)); checks = json.loads(read_pinned(actual_receipt["lean_checks"]))
    assert len(auth["authenticated_states"]) == 129 and len(checks) == 2 and all(row["matches_expectation"] for row in checks)
    prior = json.loads(read_pinned(request["prior_metadata_inputs"]))
    assert len(prior) == 26 and sum(map(len, prior.values())) == 4216
    delta = {"ranker_trace_authentication": [auth], "ranker_trace_states": auth["authenticated_states"],
        "ranker_trace_lean_checks": checks}
    assert not set(prior) & set(delta)
    records = {**prior, **delta}
    assert len(records) == 29 and sum(map(len, records.values())) == 4348
    assert all(records[family] == values for family, values in prior.items())
    write(run / "metadata-inputs.json", records)
    source_snapshot = {"schema": "terminal-ranker-trace-native-metadata-source-snapshot@1", "scope": SCOPE,
        "producer_pins": producers, "review": request["review"], "original_corpus_envelope": request["original_corpus_envelope"],
        "original_ranker_result": request["original_ranker_result"], "external_fit_output_pins": request["external_fit_output_pins"],
        "raw_canonical_binding": pin(actual / "raw-canonical-binding.json"), "authentication": auth_pin,
        "authentication_sha256": auth["authentication_sha256"], "original_corpus_sha256": auth["corpus_sha256"],
        "native_update_profile_sha256": auth["native_update_profile_sha256"],
        "finite_objective_mapping": actual_receipt["finite_objective_mapping"], "lean_checks": actual_receipt["lean_checks"],
        "lean_sources_and_objects": [artifact for check in checks for artifact in [check["artifact"], *check["compiled_artifacts"]]],
        "completed_actual_invocation": closed, "prior_metadata_inputs": request["prior_metadata_inputs"],
        "unchanged_prior_payload_rows": 4216, "prior_wrapper_row_ids_rebound_to_new_source_snapshot": True,
        "contracts_payloads_unchanged": True, "canonical_tasks": [], "planner_activation": False,
        "official_benchmark_score": None, "all32_governing_RPI_exits": "OPEN", "full_task_satisfaction": "unknown", **AUTHORITY}
    write(run / "source-snapshot.json", source_snapshot)
    from benchmarks.agent_supervisor.container_coding.codebase_ir_metadata import hydrate_codebase_ir_metadata
    receipt["native_metadata_hydration_attempts"] = 1
    started = time.monotonic()
    metadata = hydrate_codebase_ir_metadata(records=records, output=run / "metadata", source_snapshot=source_snapshot)
    receipt["native_metadata_seconds_including_fresh_restart"] = time.monotonic() - started
    write(run / "metadata-readback.json", metadata)
    assert metadata["row_count"] == 4348 and len(metadata["family_counts"]) == 29
    assert metadata["fresh_process_readback"]["verified"] is True
    # Read exports after the native restarted catalog/history verification;
    # assert every payload field and list order, including the inherited rows.
    for family, values in records.items():
        exported = [json.loads(line)["payload"] for line in (run / "metadata/exports" / (family + ".jsonl")).read_bytes().splitlines()]
        assert exported == values, "complete native metadata payload mismatch: " + family
    receipt["native_metadata_readback"] = pin(run / "metadata-readback.json")
    receipt["native_fresh_readback"] = metadata["fresh_process_readback"]
    receipt["prior_4216_payload_rows_preserved_exactly"] = True
    receipt["all_4348_payload_rows_read_back_exactly"] = True
    receipt["metadata_family_count"] = 29; receipt["metadata_row_count"] = 4348


def owned(mode):
    run = ROOT / "evidence" / mode; run.mkdir()
    started = time.monotonic(); scheduler = lease = guard = None; cleanup = []
    receipt = {"schema": "terminal-ranker-trace-owned-control@1", "mode": mode, "status": "started",
        "scope": SCOPE, "primary_error": None, "cleanup_errors": cleanup, "root_lease": None,
        "root_request": {"cpu_slots": 1, "memory_mb": 2048, "child_process_slots": 4},
        "admission_timeout_seconds": 30, "new_public_fit_calls": 0, "new_autoencoder_fit_calls": 0,
        "synthetic_unit_fit_calls": 0, "actual_authentication_calls": 0,
        "actual_optimizer_verification_updates": 0, "native_lean_checks_invoked": [],
        "native_metadata_hydration_attempts": 0, "checkpoint_activation_calls": 0, "PlanCreate_calls": 0,
        "whole_source_runtime_equivalence_proved": False, "full_task_satisfaction": "unknown",
        "all32_governing_RPI_exits": "OPEN", "planner_activation": False, "official_benchmark_score": None, **AUTHORITY}
    try:
        producers = json.loads((ROOT / "preparation/producer-pins.json").read_bytes())
        assert all(pin(row["path"]) == row for row in producers.values())
        request = json.loads(read_pinned(producers["request"])); verify_old(request)
        for key in ("review", "original_corpus_envelope", "external_fit_output_pins", "original_ranker_result", "prior_metadata_inputs", "native_lean"):
            read_pinned(request[key])
        base = json.loads(read_pinned({"path": str(CAP / "generation-manifest.json"), "bytes": 25932539, "sha256": BASE_SHA}))
        assert base["generation_cid"] == BASE_CID
        expected = {row["captured_path"]: {"path": row["captured_path"], "bytes": row["bytes"], "sha256": row["sha256"]} for row in base["files"]}
        extension = json.loads(read_pinned(producers["source_manifest"]))
        for manifest in [*extension["extension_manifests"], producers["source_manifest"]]:
            for row in json.loads(read_pinned(manifest))["files"]:
                descriptor = row["captured"]; assert pin(descriptor["path"]) == descriptor
                expected[descriptor["path"]] = descriptor
        receipt["producer_pins"] = producers
        sys.path[:] = [str(root) for root in ROOTS] + [value for value in sys.path if value and not Path(value).resolve().is_relative_to(WORKSPACE)]
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"; sys.dont_write_bytecode = True
        os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        os.environ["IPFS_DATASETS_RESOURCE_SCHEDULER_PATH"] = str(run / "resources.json")
        guard = Guard(expected); sys.meta_path.insert(0, guard)
        import benchmarks.agent_supervisor.container_coding as package
        package.__path__ = [str(root / "benchmarks/agent_supervisor/container_coding") for root in ROOTS[:2]] + list(package.__path__)
        from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import get_global_resource_scheduler, ResourceLane
        scheduler = get_global_resource_scheduler(); config = scheduler.config
        assert config.proof_safety_enabled and (config.proof_memory_stall_percent, config.proof_cpu_stall_percent,
            config.proof_io_stall_percent, config.proof_backoff_seconds) == (2.0, 50.0, 10.0, 2.0)
        receipt["resource_policy"] = config.persisted_dict(); write(run / "started.json", receipt)
        lease = scheduler.acquire(ResourceLane.ORCHESTRATION, cpu_slots=1, memory_mb=2048, child_process_slots=4, timeout=30)
        receipt["root_lease"] = lease.to_dict()
        from benchmarks.agent_supervisor.container_coding import terminal_codebase_intent_ranker_training as head
        if mode.startswith("tests"):
            run_tests(run, receipt, head)
        else:
            def forbidden_fit(*args, **kwargs): raise AssertionError("actual verification must not fit a new model")
            head.train_terminal_codebase_intent_ranker = forbidden_fit
            if mode.startswith("actual"): run_actual(run, receipt, request, head)
            elif mode.startswith("metadata"): run_metadata(run, receipt, request, producers)
            else: raise ValueError("unknown owned mode")
        verify_old(request)
        for row in producers.values(): assert pin(row["path"]) == row
        receipt["all348_old_pinned_inputs_unchanged"] = True
        receipt["all4_protected_live_sources_unchanged"] = True
        receipt["status"] = "passed"
    except BaseException as error:
        receipt["status"] = "failed"; receipt["primary_error"] = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
    finally:
        if lease is not None:
            try: receipt["root_release_returned"] = lease.release()
            except BaseException as error: cleanup.append({"stage": "release", "error": str(error)})
        if scheduler is not None:
            try:
                state = scheduler.snapshot(); receipt["final_resource_state"] = state
                assert state["active_lease_count"] == 0 and state["waiting_request_count"] == 0
            except BaseException as error: cleanup.append({"stage": "drain", "error": str(error)})
        if guard is not None:
            observations = []
            for name, before in guard.records.items():
                try:
                    after = pin(before["path"]); observations.append({"module": name, "before": before, "after": after, "matches": before == after})
                    if before != after: cleanup.append({"stage": "source_readback", "module": name})
                except BaseException as error:
                    observations.append({"module": name, "before": before, "after": None, "matches": False, "error": str(error)})
                    cleanup.append({"stage": "source_readback", "module": name, "error": str(error)})
            receipt["selected_owned_imports"] = observations; receipt["blocked_imports"] = guard.blocked
        if cleanup: receipt["status"] = "failed"
        receipt["elapsed_seconds_owned"] = time.monotonic() - started; write(run / "closed.json", receipt)
    print(json.dumps({"status": receipt["status"], "owned_seconds": receipt["elapsed_seconds_owned"], "primary_error": receipt["primary_error"]}))
    return 0 if receipt["status"] == "passed" else 1


def outer(mode):
    started = time.monotonic(); child = None
    argv = [sys.executable, "-B", str(Path(__file__).resolve()), "owned", mode]
    record = {"schema": "terminal-ranker-trace-outer-control@1", "argv": argv,
        "driver": pin(Path(__file__).resolve()), "producer_pin_specification": pin(ROOT / "preparation/producer-pins.json"),
        "started_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "returncode": None,
        "outer_timeout_seconds": 120, "primary_error": None, "cleanup_errors": []}
    write(ROOT / "evidence" / (mode + "-invocation.json"), record)
    try:
        with (ROOT / "evidence" / (mode + ".stdout.log")).open("x") as stream:
            child = subprocess.Popen(argv, stdout=stream, stderr=subprocess.STDOUT, cwd=ROOT)
            record["child_pid"] = child.pid; record["returncode"] = child.wait(timeout=120)
    except BaseException as error:
        record["primary_error"] = {"type": type(error).__name__, "message": str(error)}
        if child is not None and child.poll() is None:
            try:
                child.terminate()
                try: child.wait(timeout=5)
                except subprocess.TimeoutExpired: child.kill(); child.wait(timeout=5)
            except BaseException as cleanup_error: record["cleanup_errors"].append(str(cleanup_error))
        record["returncode"] = child.returncode if child is not None else None
    finally:
        record["elapsed_seconds_outer"] = time.monotonic() - started
        write(ROOT / "evidence" / (mode + "-closed.json"), record)
    print(json.dumps(record)); return record["returncode"] or (1 if record["primary_error"] or record["cleanup_errors"] else 0)


if __name__ == "__main__":
    if sys.argv[1] == "prepare": prepare(sys.argv[2])
    elif sys.argv[1] == "owned": raise SystemExit(owned(sys.argv[2]))
    else: raise SystemExit(outer(sys.argv[1]))

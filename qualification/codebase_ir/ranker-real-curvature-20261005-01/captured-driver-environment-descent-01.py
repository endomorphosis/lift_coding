"""Additive, admitted controls for the original ranker's real curvature bridge."""
from __future__ import annotations
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[2]
OLD = WORKSPACE / "qualification/codebase_ir/ranker-trace-authentication-20261005-01"
HEAD = WORKSPACE / "artifacts/codebase_ir_terminal_bench/terminal-codebase-ir-intent-corpus-head-20261004-01"
CAP = WORKSPACE / "artifacts/codebase_ir_terminal_bench/terminal-codebase-ir-learned-intent-join-20261004-01/source-generation-08"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def helpers():
    # Load only standard-library definitions from a previously sealed producer.
    seal = json.loads((OLD / "file-only-seal-01.json").read_bytes())
    assert sha((OLD / "file-only-seal-01.json").read_bytes()) == "8ea31286ffda2a5f08b4820bcc6ccf9ee05f133b96018132378f8c96ec16f438"
    path = OLD / "run_trace_controls_02.py"
    expected = next(row for row in seal["files"] if row["path"] == str(path))
    raw = path.read_bytes()
    assert len(raw) == expected["bytes"] and sha(raw) == expected["sha256"]
    ns = {"__name__": "held_sealed_curvature_helpers", "__file__": str(path)}
    exec(compile(raw, str(path), "exec"), ns)
    ns["ROOTS"] = (OLD / "source", HEAD / "source", CAP / "accelerate", CAP / "datasets", CAP / "kit")
    return ns


def prepare():
    h = helpers(); pin, read = h["pin"], h["read_pinned"]
    (ROOT / "preparation").mkdir(exist_ok=True); (ROOT / "evidence").mkdir(exist_ok=True)
    prior_request = json.loads((OLD / "preparation/request.json").read_bytes())
    request = {key: prior_request[key] for key in ("strict_old_inputs", "protected_live_sources", "original_corpus_envelope",
                "original_ranker_result", "external_fit_output_pins", "expected_original_corpus_sha256", "native_lean")}
    request.update(schema="terminal-ranker-curvature-request@1",
                   prior_trace_seal=pin(OLD / "file-only-seal-01.json"),
                   prior_metadata_inputs=pin(OLD / "evidence/metadata-01/metadata-inputs.json"),
                   trace_authentication=pin(OLD / "evidence/actual-01/authentication-result.json"),
                   root_request={"cpu_slots": 1, "memory_mb": 2048, "child_process_slots": 4},
                   outer_timeout_seconds=120,
                   proof_limits={"wall_seconds": 20, "cpu_seconds": 20, "output_bytes": 65536, "workspace_bytes": 16777216},
                   proof_pressure_limits={"memory_percent": 2.0, "cpu_percent": 50.0, "io_percent": 10.0},
                   corpus_scope="original_d4aa_4_pairs_80_coordinates_only",
                   full_source_runtime_equivalence=False, global_optimizer_convergence=False,
                   full_task_satisfaction="unknown", planner_activation=False, official_benchmark_score=None)
    for row in request["strict_old_inputs"]:
        assert pin(row["path"])["sha256"] == row["sha256"]
    for row in json.loads(read(request["prior_trace_seal"]))["files"]:
        assert pin(row["path"]) == row
    h["write"](ROOT / "preparation/request.json", request)
    print(json.dumps({"status": "prepared", "request": pin(ROOT / "preparation/request.json")}))


def verify(h, request):
    h["verify_old"](request)
    for row in json.loads(h["read_pinned"](request["prior_trace_seal"]))["files"]:
        assert h["pin"](row["path"]) == row


def extract(run, receipt, request, h, head):
    envelope = json.loads(h["read_pinned"](request["original_corpus_envelope"]))
    fitted = json.loads(h["read_pinned"](request["original_ranker_result"]))
    assert envelope["corpus"]["corpus_sha256"] == fitted["corpus_sha256"] == request["expected_original_corpus_sha256"]
    # This is corpus/public-feature preparation only, never fitting or replaying.
    prepared = head._prepare(envelope["corpus"], envelope["original_inputs"])
    receipt["native_preparation_calls"] = 1
    corpus, features, lexical, pairs, differences, profile, smoothness, step = prepared
    training = fitted["training_receipt"]
    assert pairs == training["train_pairs"] and len(differences) == 4 and all(len(row) == 80 for row in differences)
    assert head._digest(differences) == training["train_pair_feature_differences_sha256"] == "e8504c6e8004a2f2878bc79aae0af54c9541bff82df8cde670b48bdf7da03ac6"
    assert head._digest(profile) == training["feature_profile_sha256"]
    assert smoothness == training["smoothness_upper_bound_numeric"] and step == training["step_size"] and head.L2 == training["L2"]
    fixture = {"schema": "terminal-ranker-original-difference-artifact@1", "corpus_sha256": corpus["corpus_sha256"],
               "feature_profile_sha256": head._digest(profile), "train_pairs_sha256": head._digest(pairs),
               "differences": differences, "difference_vectors_sha256": head._digest(differences),
               "L2": head.L2, "native_step_size": step, "native_numeric_smoothness": smoothness}
    fixture["artifact_sha256"] = sha(canonical(fixture))
    destination = ROOT / "numeric-binding/original-differences-01.json"
    h["write"](destination, fixture, compact=True, maximum=65536)
    receipt["original_difference_artifact"] = h["pin"](destination)
    receipt["canonical_complete_difference_artifact_sha256"] = sha(canonical(fixture))
    receipt["gradient_evaluations"] = receipt["optimizer_updates"] = 0


def dependencies(run, receipt, h):
    """Separate setup profile; never counts as an analytic proof invocation."""
    directory = ROOT / "environment/mathlib4"
    toolchain = Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.0")
    assert (directory / "lean-toolchain").read_text().strip() == "leanprover/lean4:v4.34.0"
    assert sha((directory / "lake-manifest.json").read_bytes()) == "8f67b2cf24143ac091cdb425e886c2164b2fc2d6fbccd6db9454b697f9541a67"
    environment = {"PATH": str(toolchain / "bin") + ":/usr/bin:/bin", "HOME": os.environ["HOME"],
                   "LANG": "C.UTF-8", "LEAN_NUM_THREADS": "1", "MATHLIB_CACHE_DIR": str(ROOT / "environment/cache")}
    argv = [str(toolchain / "bin/lake"), "exe", "cache", "get",
            "Mathlib.Analysis.Complex.Exponential", "Mathlib.Algebra.Order.BigOperators.Ring.Finset", "Mathlib.Tactic.Linarith"]
    if "softplus" in receipt["mode"]:
        argv.extend(["Mathlib.Analysis.SpecialFunctions.Log.Deriv", "Mathlib.Analysis.Calculus.Deriv.Inv", "Mathlib.Tactic.FieldSimp"])
    if "descent" in receipt["mode"]:
        argv.append("Mathlib.Analysis.Convex.Deriv")
    setup = {"kind": "dependency_hydration_only", "argv": argv, "cwd": str(directory),
             "wall_seconds": 100, "capture_bytes": 1048576, "external_disk_limit_bytes": 4 * 1024**3,
             "proof_solver_limits_unchanged": True, "process_affinity_cpu": min(os.sched_getaffinity(0)),
             "actual_native_proof_checks": 0, "root_lease": receipt["root_lease"]}
    h["write"](run / "setup-request.json", setup)
    def constrain():
        os.sched_setaffinity(0, {setup["process_affinity_cpu"]})
    started = time.monotonic()
    child = subprocess.Popen(argv, cwd=directory, env=environment, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, preexec_fn=constrain, start_new_session=True)
    raw = b""; setup["cleanup_errors"] = []
    try:
        raw, _ = child.communicate(timeout=100)
        setup.update(returncode=child.returncode, timed_out=False)
    except subprocess.TimeoutExpired:
        import signal
        setup["timed_out"] = True
        os.killpg(child.pid, signal.SIGTERM)
        try: raw, _ = child.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL); raw, _ = child.communicate(timeout=5)
        setup["returncode"] = child.returncode
    finally:
        assert len(raw) <= setup["capture_bytes"]
        (run / "setup.log").write_bytes(raw)
        setup["elapsed_seconds"] = time.monotonic() - started
        setup["external_disk_bytes_post_setup"] = sum(p.stat().st_size for p in directory.rglob("*") if p.is_file())
        setup["external_disk_guard_scope"] = "post-setup inventory; no continuous quota claim"
        h["write"](run / "setup-result.json", setup)
    receipt["dependency_setup"] = h["pin"](run / "setup-result.json")
    assert setup["returncode"] == 0 and not setup["timed_out"], "dependency cache hydration failed; retained setup.log"
    assert setup["external_disk_bytes_post_setup"] <= setup["external_disk_limit_bytes"]


def held_module(h, descriptor, name):
    import types
    module = types.ModuleType(name); module.__file__ = descriptor["path"]
    sys.modules[name] = module
    exec(compile(h["read_pinned"](descriptor), descriptor["path"], "exec"), module.__dict__)
    return module


def numeric(run, receipt, request, h, invocation):
    descriptors = invocation["extra_inputs"]
    builder = next(row for row in descriptors if row["path"].endswith("/build_curvature_numeric_binding.py"))
    api = held_module(h, builder, "build_curvature_numeric_binding")
    fixture_pin = next(row for row in descriptors if row["path"].endswith("/original-differences-01.json"))
    fixture = json.loads(h["read_pinned"](fixture_pin))
    fitted = json.loads(h["read_pinned"](request["original_ranker_result"]))
    auth = json.loads(h["read_pinned"](request["trace_authentication"]))
    envelope = json.loads(h["read_pinned"](request["original_corpus_envelope"]))
    arguments = {"differences": fixture["differences"], "difference_artifact": fixture,
                 "ranker_result": fitted, "trace_authentication": auth, "corpus_envelope": envelope,
                 "expected_difference_sha256": fixture["difference_vectors_sha256"],
                 "expected_difference_artifact_sha256": sha(canonical(fixture)),
                 "expected_ranker_result_sha256": sha(canonical(fitted)),
                 "expected_authentication_sha256": sha(canonical(auth)),
                 "expected_corpus_envelope_sha256": sha(canonical(envelope))}
    if receipt["mode"].startswith("numeric"):
        certificate = api.build_numeric_curvature_binding(**arguments)
        h["write"](run / "numeric-binding.json", certificate, compact=True, maximum=65536)
        receipt["numeric_binding"] = h["pin"](run / "numeric-binding.json")
        receipt["exact_norm_accumulations"] = 1
        receipt["coordinate_visits"] = 320
    else:
        import pytest
        tests = next(row for row in descriptors if row["path"].endswith("/test_curvature_numeric_binding.py"))
        phases = []
        class Reports:
            def pytest_runtest_logreport(self, report):
                phases.append({"nodeid": report.nodeid, "phase": report.when,
                               "outcome": report.outcome, "seconds": report.duration})
        code = int(pytest.main(["-q", "-p", "no:cacheprovider", "--noconftest", "-o", "addopts=",
                               "-c", str(OLD / "source/pytest.ini"), "--basetemp", str(run / "fixtures"),
                               "--junitxml", str(run / "tests.xml"), tests["path"]], plugins=[Reports()]))
        h["write"](run / "phases.json", phases)
        calls = [row for row in phases if row["phase"] == "call"]
        receipt["pytest_returncode"] = code; receipt["selected_test_count"] = len(calls)
        assert code == 0 and calls and all(row["outcome"] == "passed" for row in phases)
    receipt["prior_trace_replay_calls"] = receipt["native_preparation_calls"] = receipt["gradient_evaluations"] = 0
    receipt["numeric_input_raw_pins"] = [builder, fixture_pin, request["original_ranker_result"], request["trace_authentication"], request["original_corpus_envelope"]]


def environment_capture(run, receipt, h, invocation):
    descriptor = next(row for row in invocation["extra_inputs"] if row["path"].endswith("/build_environment_manifest.py"))
    source = next(row for row in invocation["extra_inputs"] if row["path"].endswith(".lean"))
    builder = held_module(h, descriptor, "held_curvature_environment_builder")
    targets = ["Mathlib.Analysis.Complex.Exponential", "Mathlib.Algebra.Order.BigOperators.Ring.Finset",
               "Mathlib.Tactic.Linarith", "Mathlib.Analysis.SpecialFunctions.Log.Deriv",
               "Mathlib.Analysis.Calculus.Deriv.Inv", "Mathlib.Tactic.FieldSimp"]
    if "std" in receipt["mode"]: targets.append("Std")
    if "descent" in receipt["mode"]: targets.append("Mathlib.Analysis.Convex.Deriv")
    manifest = builder.build(mathlib=ROOT / "environment/mathlib4",
        toolchain=Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.0"),
        expected_mathlib_revision="5ed2965256430c3649e86755f9576b54eca72435",
        target_imports=targets,
        source_paths=[Path(source["path"])], output=run / "environment-manifest.json", full_core_fallback=False)
    receipt["environment_manifest"] = manifest
    body = json.loads(h["read_pinned"](manifest))
    receipt["environment_file_count"] = body["external_file_count"]
    receipt["environment_file_bytes"] = body["external_file_bytes"]
    receipt["source_import_module_count"] = len(body["source_import_modules"])
    receipt["dependency_read_scope"] = body["closure_scope"]


def pure_tests(run, receipt, h, invocation):
    import pytest
    from ipfs_datasets_py.logic.backends.process import BoundedToolRunner
    original = BoundedToolRunner.run
    def forbidden_run(*args, **kwargs):
        receipt["native_runner_calls_refused"] += 1
        raise AssertionError("pure controls may not invoke an actual native tool")
    BoundedToolRunner.run = forbidden_run
    receipt["native_runner_calls_refused"] = 0
    descriptors = invocation["extra_inputs"]
    checker_source = next((row for row in descriptors if row["path"].endswith("/numeric-checker-v4/bounded_analytic_checker.py")), None)
    if checker_source: os.environ["RANKER_ANALYTIC_CHECKER_SOURCE"] = checker_source["path"]
    tests = [row["path"] for row in descriptors if Path(row["path"]).name.startswith("test_")]
    phases = []
    class Reports:
        def pytest_runtest_logreport(self, report):
            phases.append({"nodeid": report.nodeid, "phase": report.when,
                           "outcome": report.outcome, "seconds": report.duration})
    try:
        code = int(pytest.main(["-q", "-p", "no:cacheprovider", "--noconftest", "-o", "addopts=",
                               "-c", str(OLD / "source/pytest.ini"), "--basetemp", str(run / "fixtures"),
                               "--junitxml", str(run / "tests.xml"), *tests], plugins=[Reports()]))
    finally: BoundedToolRunner.run = original
    h["write"](run / "phases.json", phases)
    calls = [row for row in phases if row["phase"] == "call"]
    receipt["pytest_returncode"] = code; receipt["selected_test_count"] = len(calls)
    assert code == 0 and calls and all(row["outcome"] == "passed" for row in phases)
    assert receipt["native_runner_calls_refused"] == 0


def check_lean(run, receipt, request, h, invocation, lease):
    descriptors = invocation["extra_inputs"]
    descriptor = next(row for row in descriptors if row["path"].endswith("/bounded_analytic_checker.py"))
    specification = next(row for row in descriptors if row["path"].endswith("-check-specification.json"))
    spec = json.loads(h["read_pinned"](specification))
    assert spec["schema"] == "terminal-ranker-curvature-native-check-specification@1"
    assert spec["source"] in descriptors and spec["environment_manifest"] in descriptors
    wrapper = held_module(h, descriptor, "held_bounded_analytic_checker")
    output = run / "lean"; output.mkdir()
    receipt["native_checker_attempts"] = [{"specification": specification, "native_invocations_observed": 0}]
    retention = {}
    if "retention_helper" in spec:
        assert spec["retention_helper"] in descriptors and spec["python_executable"] in descriptors
        retention = {"retention_helper_pin": spec["retention_helper"], "python_executable_pin": spec["python_executable"]}
    check = wrapper.compile_analytic_lean(environment_manifest=Path(spec["environment_manifest"]["path"]),
        expected_environment_manifest_sha256=spec["environment_manifest"]["sha256"], source_pin=spec["source"],
        output=output, root_lease=lease, expected_success=spec["expected_success"], theorem_names=tuple(spec["theorem_names"]), **retention)
    receipt["native_checker_attempts"][0]["native_invocations_observed"] = check["native_invocations"]
    h["write"](run / "check-result.json", check, compact=True, maximum=65536)
    receipt["native_proof_checks"] = [h["pin"](run / "check-result.json")]
    assert check["matches_expectation"] is True, "analytic Lean result failed/inconclusive: " + spec["source"]["path"]
    if spec["expected_success"]:
        assert check["status"] == "passed" and all(row.get("complete", True) for row in check["compiled_artifacts"])
    else:
        assert check["status"] == "rejected"


def owned(mode, specification):
    h = helpers(); pin, read, write = h["pin"], h["read_pinned"], h["write"]
    invocation = json.loads(Path(specification).read_bytes())
    for row in invocation["inputs"]: read(row)
    request = json.loads(read(invocation["request"]))
    run = ROOT / "evidence" / mode; run.mkdir()
    started = time.monotonic(); scheduler = lease = guard = None; cleanup = []
    receipt = {"schema": "terminal-ranker-curvature-owned-control@1", "mode": mode, "status": "started",
               "native_preparation_calls": 0, "gradient_evaluations": 0, "optimizer_updates": 0,
               "fit_calls": 0, "autoencoder_fit_calls": 0, "native_proof_checks": [],
               "primary_error": None, "cleanup_errors": cleanup, "invocation": pin(specification),
               "planner_activation": False, "full_task_satisfaction": "unknown", "global_convergence_proved": False,
               **h["AUTHORITY"]}
    try:
        verify(h, request)
        base = json.loads(read({"path": str(CAP / "generation-manifest.json"), "bytes": 25932539, "sha256": h["BASE_SHA"]}))
        expected = {row["captured_path"]: {"path": row["captured_path"], "bytes": row["bytes"], "sha256": row["sha256"]} for row in base["files"]}
        extension = json.loads((OLD / "source-manifest.json").read_bytes())
        for descriptor in [*extension["extension_manifests"], pin(OLD / "source-manifest.json")]:
            for row in json.loads(read(descriptor))["files"]:
                expected[row["captured"]["path"]] = row["captured"]
        roots = h["ROOTS"]
        sys.path[:] = [str(root) for root in roots] + [value for value in sys.path if value and not Path(value).resolve().is_relative_to(WORKSPACE)]
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"; sys.dont_write_bytecode = True
        os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        os.environ["IPFS_DATASETS_RESOURCE_SCHEDULER_PATH"] = str(run / "resources.json")
        guard = h["Guard"](expected); sys.meta_path.insert(0, guard)
        import benchmarks.agent_supervisor.container_coding as package
        package.__path__ = [str(root / "benchmarks/agent_supervisor/container_coding") for root in roots[:2]] + list(package.__path__)
        from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import get_global_resource_scheduler, ResourceLane
        scheduler = get_global_resource_scheduler(); config = scheduler.config
        assert config.proof_safety_enabled and (config.proof_memory_stall_percent, config.proof_cpu_stall_percent, config.proof_io_stall_percent, config.proof_backoff_seconds) == (2.0, 50.0, 10.0, 2.0)
        receipt["resource_policy"] = config.persisted_dict(); write(run / "started.json", receipt)
        lease = scheduler.acquire(ResourceLane.ORCHESTRATION, cpu_slots=1, memory_mb=2048, child_process_slots=4, timeout=30)
        receipt["root_lease"] = lease.to_dict()
        from benchmarks.agent_supervisor.container_coding import terminal_codebase_intent_ranker_training as head
        def forbidden(*args, **kwargs):
            raise AssertionError("curvature qualification forbids new fit/objective replay")
        head.train_terminal_codebase_intent_ranker = head._objective = forbidden
        if mode.startswith("extract"): extract(run, receipt, request, h, head)
        elif mode.startswith("dependencies"): dependencies(run, receipt, h)
        elif mode.startswith("environment"): environment_capture(run, receipt, h, invocation)
        elif mode.startswith("pure-tests"):
            pure_tests(run, receipt, h, invocation)
        elif mode.startswith("numeric") or mode.startswith("tests"):
            numeric(run, receipt, request, h, invocation)
        elif mode.startswith("lean"):
            check_lean(run, receipt, request, h, invocation, lease)
        elif mode.startswith("metadata"):
            metadata(run, receipt, request, h, invocation)
        else: raise ValueError("unknown mode")
        verify(h, request)
        for row in invocation["inputs"]: assert pin(row["path"]) == row
        receipt["old348_protected4_prior203_unchanged"] = True
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
                assert state["active_lease_count"] == state["waiting_request_count"] == 0
            except BaseException as error: cleanup.append({"stage": "drain", "error": str(error)})
        if guard is not None:
            receipt["selected_owned_imports"] = []
            for name, before in guard.records.items():
                try:
                    after = pin(before["path"])
                    receipt["selected_owned_imports"].append({"module": name, "before": before, "after": after, "matches": before == after})
                    if before != after: cleanup.append({"stage": "source_readback", "module": name})
                except BaseException as error: cleanup.append({"stage": "source_readback", "module": name, "error": str(error)})
            receipt["blocked_imports"] = guard.blocked
        if cleanup: receipt["status"] = "failed"
        receipt["elapsed_seconds_owned"] = time.monotonic() - started; write(run / "closed.json", receipt)
    print(json.dumps({"status": receipt["status"], "owned_seconds": receipt["elapsed_seconds_owned"], "primary_error": receipt["primary_error"]}))
    return 0 if receipt["status"] == "passed" else 1


def outer(mode, extra):
    h = helpers(); pin, write = h["pin"], h["write"]
    spec = ROOT / "preparation" / (mode + "-invocation.json")
    snapshot = ROOT / ("captured-driver-" + mode + ".py")
    with snapshot.open("xb") as stream: stream.write(Path(__file__).read_bytes())
    snapshot.chmod(0o444)
    inputs = [pin(snapshot), pin(ROOT / "preparation/request.json")]
    inputs.extend(pin(Path(value).resolve(strict=True)) for value in extra)
    invocation = {"schema": "terminal-ranker-curvature-frozen-invocation@1", "mode": mode,
                  "inputs": inputs, "request": inputs[1], "extra_inputs": inputs[2:],
                  "outer_timeout_seconds": 120, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    write(spec, invocation)
    record = {"schema": "terminal-ranker-curvature-outer-control@1", "invocation": pin(spec),
              "returncode": None, "primary_error": None, "cleanup_errors": []}
    started = time.monotonic(); child = None
    try:
        with (ROOT / "evidence" / (mode + ".stdout.log")).open("xb") as stream:
            child = subprocess.Popen([sys.executable, "-B", str(snapshot), "owned", mode, str(spec)],
                                     stdout=stream, stderr=subprocess.STDOUT, cwd=ROOT, start_new_session=True)
            record["child_pid"] = child.pid; record["returncode"] = child.wait(timeout=120)
    except BaseException as error:
        record["primary_error"] = {"type": type(error).__name__, "message": str(error)}
        if child is not None and child.poll() is None:
            import signal
            try:
                os.killpg(child.pid, signal.SIGTERM)
                try: child.wait(timeout=5)
                except subprocess.TimeoutExpired: os.killpg(child.pid, signal.SIGKILL); child.wait(timeout=5)
            except BaseException as cleanup_error: record["cleanup_errors"].append(str(cleanup_error))
    finally:
        record["elapsed_seconds_outer"] = time.monotonic() - started
        write(ROOT / "evidence" / (mode + "-closed.json"), record)
    print(json.dumps(record)); return record["returncode"] or (1 if record["primary_error"] or record["cleanup_errors"] else 0)


if __name__ == "__main__":
    if sys.argv[1] == "prepare": prepare()
    elif sys.argv[1] == "owned": raise SystemExit(owned(sys.argv[2], sys.argv[3]))
    elif sys.argv[1] == "run": raise SystemExit(outer(sys.argv[2], sys.argv[3:]))
    else: raise ValueError("unknown action")

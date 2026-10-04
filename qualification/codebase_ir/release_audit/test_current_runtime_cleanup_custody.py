"""Authored metadata and custody boundaries; no owner execution or sources."""
import copy
import importlib.util
import json
import os
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest import mock
from xml.sax.saxutils import quoteattr

_SPEC = importlib.util.spec_from_file_location("cleanup_custody", Path(__file__).with_name("current_runtime_cleanup_custody.py"))
m = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(m)


def xml(names, *, failures=0, errors=0, seconds=1.0, classname="api.tests"):
    cases = []
    for index, name in enumerate(names):
        outcome = "<failure/>" if index < failures else "<error/>" if index < failures + errors else ""
        cases.append("<testcase classname=" + quoteattr(classname) + " name=" + quoteattr(name) + " time='0'>" + outcome + "</testcase>")
    raw = (f"<testsuites><testsuite tests='{len(names)}' failures='{failures}' errors='{errors}' skipped='0' time='{seconds}'>"
           + "".join(cases) + "</testsuite></testsuites>").encode()
    return raw, {"tests": len(names), "failures": failures, "errors": errors, "skipped": 0, "seconds": seconds}


def authored(workspace):
    docs, bodies = {}, {}
    ns = workspace / "artifacts/codebase_ir_terminal_bench/inventory-resume-worker-qualification-20261003-15"
    machine_path = workspace / "external/ipfs_accelerate/docs/architecture/repository_proof_index_and_codebase_ir.source_delta_runtime_review.json"
    paths = {"machine_review": machine_path, "historical_review": workspace / "external/ipfs_accelerate/docs/architecture/history.json",
             "current_worker_result": ns / "native/result.json", "container_result": ns / "container-execution-final.json",
             "cleanup_receipt": ns / "native/owner-fixture-worktree-cleanup.json", "independent_worker_audit": workspace / "worker-audit.json",
             "selected_source_receipt": workspace / "selected-source-receipt.json", "source_reader_guard": workspace / "reader-guard.json",
             "worker_stdout": ns / "native/private/worker.log", **{role: ns / path for role, path in m.LOCAL_RECORDS.items()}}
    machine = {"schema": "codebase-source-delta-current-runtime-review@1", "current_runtime_namespace": str(ns.relative_to(workspace)),
               "production_open_tasks": 32, "limitations": ["historical native13 Git endpoint disclosure retained"]}
    for key in ("384d_qualified", "cuda_qualified", "proof_authority", "production_default_activated", "production_task_status_changed",
                "source_execution_attested", "scan_execution_attested", "numerical_reuse_authorized_by_source_delta"):
        machine[key] = False
    old = {"schema": "repository-proof-index-inventory-resume-worker-review@1", "distinct_pytest_cases": 835, "tests": []}
    current_ids = [[f"new-{i}" for i in range(59)], [f"new-{i}" for i in range(59, 250)],
                   ["new-250", "new-0", "new-1", "new-2"], [f"new-{i}" for i in range(7)],
                   [f"new-{i}" for i in range(16)], ["new-251"]]
    machine["tests"], machine["failed_tests"] = [], []
    for prefix, groups, target in (
        ("current_successful_xml", current_ids, machine["tests"]),
        ("prior_successful_xml", [[f"new-{i}" for i in range(175)] + [f"old-{i}" for i in range(660)], *([[]] * 13)], old["tests"]),
        ("failed_xml", [["failure-0", "failure-1", "failure-2", "failure-3", "failure-0", "failure-1", "failure-2"],
                        [f"adverse-{i}" for i in range(186)]], machine["failed_tests"]),
    ):
        for index, names in enumerate(groups):
            role = f"{prefix}_{index:02}"
            paths[role] = workspace / "receipts" / (role + ".xml")
            failed, errors, seconds = (4, 3, 24.972) if role == "failed_xml_00" else (8, 0, 80.064) if role == "failed_xml_01" else (0, 0, 1.0)
            bodies[role], row = xml(names, failures=failed, errors=errors, seconds=seconds)
            target.append(row)
    machine["test_accounting"] = {"prior_distinct": 835, "new_successful_distinct": 252, "overlap_prior": 175,
        "new_unique": 77, "combined_distinct": 912, "new_successful_executions": 278, "failed_junit_seconds_separate": 105.036}
    allocation = {"record_id": "record-1", "task_id": "INVENTORY-OFFSET", "owner": {"pid": 42}, "workspace_path": "/worktree"}
    boundary = {"uid": 1001, "euid": 1001, "pid": 24615, "provider_calls": 0, "training_steps": 0,
                "boundary": {"container_id": "container-1", "image_id": "image-1", "completion_authority": False}}
    worker_receipt = {"uid": 1001, "pid": 24615, "provider_calls": 0, "training_steps": 0,
                      "completion_authority": False, "proof_authority": False}
    bodies["worker_stdout"] = m.canonical(boundary).replace(b"\n", b" ") + b"\n" + m.canonical(worker_receipt).replace(b"\n", b" ") + b"\n"
    log = {"path": "private/worker.log", "bytes": len(bodies["worker_stdout"]), "sha256": sha256(bodies["worker_stdout"]).hexdigest()}
    verification = {"actual_boundary_stdout_observation": {"line": 1, "log": log, "receipt": boundary},
                    "actual_stdout_observation": {"line": 2, "log": log, "receipt": worker_receipt}, "verified": True}
    for key in ("completion_authority", "proof_authority", "process_origin_attested", "native_registry_opened",
                "native_inventory_freshness_verified_here", "private_evidence_epoch_verified_here"):
        verification[key] = False
    operation = {"schema": "ipfs_accelerate_py/agent-supervisor/operation-result@1", "status": "succeeded", "error": None, "tree_id": "tree-1"}
    start = {**operation, "operation": "start", "data": {}}
    stop = {**operation, "operation": "stop", "data": {"old_tree_fenced": True, "isolated_worker_cleanup": {
        "schema": "isolated-worker-stop-observation@1", "single_worker": True, "returncode": 0, "worker_uid": 1001, "completion_authority": False}}}
    result = {"schema": "codebase-inventory-resume-native-qualification@1", "qualified": True, "worker_launched": True,
              "native_task_statuses": {"INVENTORY-TYPE": "completed", "INVENTORY-OFFSET": "completed"}, "bootstrap_errors": [],
              "remaining_processes": 0, "provider_calls": 0, "post_setup_fit_attempt_count": 0, "new_scan_pages_created": 0,
              "known_actual_setup_epochs": 0, "inherited_actual_setup_epochs": 2, "unknown_fitting_epochs": False,
              "numerical_before": {"state_sha256": "0" * 64}, "numerical_after": {"state_sha256": "0" * 64},
              "start": start, "stop": stop, "observed_worker_allocations": [allocation], "residual_task": {"status": "completed"},
              "task_observations": [{"status": "completed"}], "authored_worker_receipt": verification,
              "final_resources": {"active_lease_count": 0, "waiting_request_count": 0}, "recorded_seconds": 1337.0, "inherited_scan_pages": 10}
    lifecycle = {key: result[key] for key in ("start", "stop", "bootstrap_errors", "worker_launched", "remaining_processes",
                                             "residual_task", "observed_worker_allocations", "task_observations")}
    cleanup = [{"allocation": allocation, "decision": {"allowed": True, "record": None, "reason": "no_lifecycle_record"},
                "scope": "explicit owner fixture cleanup after native STOP"}]
    payload = {"task_population_preserved": True, "inventory_features_are_advisory": True, "removed_task_cids": [], "current_facts": []}
    for key in ("completion_authority", "proof_authority", "publication_authority", "production_activation", "task_omission_authority"):
        payload[key] = False
    execution = {"binding": {"signature": "historical-declaration"}, "payload": payload}
    host = {key: 0 for key in ("active_lease_count", "active_child_lease_count", "active_root_lease_count", "waiting_request_count")}
    container = {"schema": "inventory-resume-worker-offline-container-execution@1", "returncode": 0, "container_removed": True,
                 "host_reservation_released": True, "network": "none", "privileged": False,
                 "original_selected_source_changes_after_execution": [], "container_id": "container-1", "image_id": "image-1",
                 "host_resources_after_cleanup": host, "elapsed_seconds": 1353.0}
    audit = {"schema": "inventory-resume-worker-independent-audit@1", "qualified": True, "authority": "none",
             "native_jobs_executed": 0, "native_owner_databases_opened": 0, "training_steps": 0,
             "worker": {"actual_stdout_observation": verification["actual_stdout_observation"],
                        "actual_boundary_stdout_observation": verification["actual_boundary_stdout_observation"],
                        "post_stop_receipt_gate_independently_replayed": True, "current_owner_registry_reopened": False},
             "lifecycle": {"native_final_resources": result["final_resources"], "host_final_resources": host,
                           "native_recorded_seconds": 1337.0, "container_total_seconds": 1353.0},
             "primary_archive": {"preserved": True, "passes": 2, "ending_inventory_cid": "archive-1"},
             "recorded_seconds": 16.0, "selected_generation": {"files": 19381, "bytes": 481227815,
                 "full_transitive_dependency_attestation": False, "mutable_working_checkout_qualified": False, "producers_cid": "producer-1"}}
    receipt = {"schema": "inventory-current-runtime-selected-source-snapshot@1", "scope": "selected declarations",
               "qualification_pending": True, "elapsed_seconds": 10.0, "counts": {}, "core_pins": {}, "selected_sources": {}}
    cores = ["ipfs_accelerate_py/agent_supervisor/entrypoints/admitted_benchmark_runtime.py",
             "ipfs_accelerate_py/agent_supervisor/runtime/codebase_inventory_execution.py",
             "ipfs_accelerate_py/agent_supervisor/runtime/finite_proof_query_execution.py",
             "ipfs_accelerate_py/agent_supervisor/runtime/local_completion_bridge.py"]
    for repo, count, size, package in (("ipfs_accelerate", 9574, 271242470, "ipfs_accelerate_py"),
                                      ("ipfs_datasets", 8466, 175475852, "ipfs_datasets_py"), ("ipfs_kit", 1341, 34509493, "ipfs_kit_py")):
        rows = []
        for index in range(count):
            relative = cores[index] if repo == "ipfs_accelerate" and index < 4 else f"{package}/file-{index}.py"
            row = {"relative": relative, "path": str(workspace / "external" / repo / relative), "sha256": "a" * 64,
                   "bytes": size // count + (index < size % count)}
            rows.append(row)
            if relative in cores:
                receipt["core_pins"][relative] = {"bytes": row["bytes"], "sha256": row["sha256"]}
        receipt["selected_sources"][repo] = rows
        receipt["counts"][repo] = {"files": count, "bytes": size}
    machine["native_current_runtime"] = {key: result[key] for key in ("qualified", "native_task_statuses", "recorded_seconds", "final_resources")}
    machine["container_closure"] = {key: container[key] for key in ("container_id", "image_id", "elapsed_seconds", "container_removed")}
    machine["explicit_owner_worktree_cleanup"] = {"git_worktrees_administration_absent": True}
    machine["current_runtime_independent_audit"] = {"actual_worker_pid_in_namespace": 24615, "archive_inventory_cid": "archive-1",
        "selected_generation": dict(audit["selected_generation"])}
    machine["frozen_candidate"] = {"scope": receipt["scope"], "seconds": 10.0, "core_pins": receipt["core_pins"], "counts": receipt["counts"]}
    machine["source_reader_guards"] = {}
    machine["costs"] = {"do_not_add_nested_phase_times": True, "native_current_runtime_seconds": 1337.0,
        "outer_current_runtime_seconds": 1353.0, "current_runtime_independent_audit_seconds": 16.0,
        "pytest_failed_receipt_seconds": 105.036, "pytest_successful_receipt_seconds": 6.0}
    guard = {"schema": "codebase-source-delta-independent-reader-guards@1", "qualified": True, "test_count": 54,
             "errors": 0, "failures": 0, "skips": 0, "pytest_cases": 0, "native_training_epochs": 0,
             "native_execution_attested": False, "source_execution_attested": False,
             "cases": [{"id": f"guard-{i}", "status": "passed"} for i in range(54)]}
    docs.update(machine_review=machine, historical_review=old, current_worker_result=result, container_result=container,
                cleanup_receipt=cleanup, independent_worker_audit=audit, selected_source_receipt=receipt, source_reader_guard=guard,
                native_lifecycle=lifecycle, execution_scope_before=execution, execution_scope_after=copy.deepcopy(execution), authored_verification=verification)

    def declared(role):
        raw = bodies[role]
        return {"path": str(paths[role].relative_to(workspace)), "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}

    for role in ("selected_source_receipt", "source_reader_guard", "current_worker_result", "container_result", "cleanup_receipt",
                 "native_lifecycle", "execution_scope_before", "execution_scope_after", "authored_verification"):
        bodies[role] = m.canonical(docs[role])
    for prefix, target in (("current_successful_xml", machine["tests"]), ("prior_successful_xml", old["tests"]), ("failed_xml", machine["failed_tests"])):
        for index, row in enumerate(target):
            row["junit"] = declared(f"{prefix}_{index:02}")
    bodies["historical_review"] = m.canonical(old)
    audit["observed_artifact_pins"] = {relative: {"sha256": sha256(bodies[role]).hexdigest(), "bytes": len(bodies[role])}
                                       for role, relative in m.LOCAL_RECORDS.items()}
    bodies["independent_worker_audit"] = m.canonical(audit)
    machine["historical_resume_worker_review"] = declared("historical_review")
    for role, target, key in (("current_worker_result", "native_current_runtime", "result"), ("container_result", "container_closure", "result"),
        ("cleanup_receipt", "explicit_owner_worktree_cleanup", "receipt"), ("independent_worker_audit", "current_runtime_independent_audit", "report"),
        ("selected_source_receipt", "frozen_candidate", "receipt"), ("source_reader_guard", "source_reader_guards", "report")):
        machine[target][key] = declared(role)
    machine["current_runtime_independent_audit"]["actual_worker_stdout"] = {**declared("worker_stdout"), "path": "native/private/worker.log"}
    bodies["machine_review"] = m.canonical(machine)
    pins = {role: {"path": str(paths[role]), "sha256": sha256(bodies[role]).hexdigest(), "size_bytes": len(bodies[role])} for role in m.ROLES}
    docs = {role: json.loads(bodies[role]) for role in docs}
    return docs, bodies, pins


class CustodyControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.workspace = Path(cls.temp.name) / "workspace"
        cls.docs, cls.bodies, cls.pins = authored(cls.workspace)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_authored_consistency_preserves_scope_and_counts(self):
        result = m.reconcile(self.docs, self.bodies, self.workspace)
        self.assertEqual(result["test_accounting"]["combined_distinct"], 912)
        self.assertEqual(result["failed_trial_executions"], 193)
        self.assertEqual(result["failed_trial_distinct_identities"], 190)
        self.assertEqual(result["declared_source_generation"]["files"], 19381)
        self.assertFalse(result["recorded_cleanup"]["authority_authenticated"])

    def test_authored_selected_bindings(self):
        self.assertEqual(m.selected_bindings(self.pins, self.docs)[0], self.workspace)

    def run_relocated(self, base, *, after_write=None, spec_edit=None, mapping_edit=None):
        spec = {"schema": m.INPUT_SCHEMA, "selected_profile": m.PROFILE,
                "selected_files": [{"role": role, **self.pins[role]} for role in m.ROLES]}
        (base / "inputs").mkdir()
        manifest = base / "inputs/input.json"
        if spec_edit:
            spec_edit(spec)
        manifest.write_bytes(m.canonical(spec))
        mapping = {}
        for index, role in enumerate(m.ROLES):
            target = base / "copies" / f"{index}.bytes"
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(self.bodies[role])
            mapping[self.pins[role]["path"]] = str(target)
        if mapping_edit:
            mapping_edit(mapping)
        original_open = Path.open

        class WrittenReport:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                return self.stream.__enter__()

            def __exit__(self, *args):
                result = self.stream.__exit__(*args)
                after_write(base / "output", mapping)
                return result

        def opening(path, *args, **kwargs):
            stream = original_open(path, *args, **kwargs)
            if after_write and path.name == "current_runtime_cleanup_custody.json" and args and args[0] == "xb":
                return WrittenReport(stream)
            return stream

        with mock.patch.object(m, "PUBLIC_ANCHOR", self.pins["machine_review"]["sha256"]), mock.patch.object(Path, "open", opening):
            return m.audit(manifest, base / "output", relocated_sources=mapping)

    def test_roundtrip_and_explicit_relocation(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = self.run_relocated(base)
            self.assertEqual(result["selected_file_count"], 35)
            self.assertEqual(len(result["retained_files"]), 36)
            self.assertTrue(all(result[key] is False for key in m.FALSE_FLAGS))
            self.assertTrue(all(result[key] is True for key in m.TRUE_FLAGS))
            self.assertEqual(m.Capture.raw(base / "output/current_runtime_cleanup_custody.json", m.MAX_REPORT), m.canonical(result))
            for role in m.BINDING_ROLES:
                self.assertEqual(result[role + "_sha256"], self.pins[role]["sha256"])

    def test_fixed_role_order_refuses(self):
        def edit(spec):
            spec["selected_files"][0], spec["selected_files"][1] = spec["selected_files"][1], spec["selected_files"][0]
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(ValueError, "ordered"):
            self.run_relocated(Path(directory), spec_edit=edit)

    def test_partial_relocation_refuses(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(ValueError, "relocation"):
            self.run_relocated(Path(directory), mapping_edit=lambda mapping: mapping.pop(self.pins["worker_stdout"]["path"]))

    def test_post_report_original_drift_refuses(self):
        def mutate(_, mapping):
            Path(mapping[self.pins["worker_stdout"]["path"]]).write_bytes(b"changed after report")
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(ValueError, "changed|bounded"):
            self.run_relocated(Path(directory), after_write=mutate)

    def test_post_report_retained_copy_drift_refuses(self):
        def mutate(output, _):
            (output / "retained/002.bytes").chmod(0o644)
            (output / "retained/002.bytes").write_bytes(b"changed after report")
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(ValueError, "changed|bounded"):
            self.run_relocated(Path(directory), after_write=mutate)

    def test_post_report_nested_drift_refuses(self):
        def mutate(output, _):
            (output / "selected_custody.json").chmod(0o644)
            (output / "selected_custody.json").write_bytes(b"{}")
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(ValueError, "changed|bounded"):
            self.run_relocated(Path(directory), after_write=mutate)

    def test_post_report_main_drift_refuses(self):
        def mutate(output, _):
            (output / "current_runtime_cleanup_custody.json").write_bytes(b"{}")
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(ValueError, "main report"):
            self.run_relocated(Path(directory), after_write=mutate)

    def test_post_report_extra_file_refuses(self):
        def mutate(output, _):
            (output / "extra").write_bytes(b"unselected")
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(ValueError, "output"):
            self.run_relocated(Path(directory), after_write=mutate)

    def test_missing_relocated_member_never_falls_back(self):
        with self.assertRaisesRegex(ValueError, "unavailable"):
            m.Capture({}).read(Path(self.pins["machine_review"]["path"]))

    def test_binding_substitution_refuses_without_reading_unselected_body(self):
        pins = copy.deepcopy(self.pins)
        pins["cleanup_receipt"]["path"] = str(self.workspace / "secret.key")
        with self.assertRaisesRegex(ValueError, "raw bindings"):
            m.selected_bindings(pins, self.docs)

    def test_original_and_retained_drift_refuses(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "body"
            path.write_bytes(b"old")
            capture = m.Capture()
            capture.read(path, {"path": str(path), "sha256": sha256(b"old").hexdigest(), "size_bytes": 3})
            path.write_bytes(b"new")
            with self.assertRaisesRegex(ValueError, "changed"):
                capture.stable()

    def test_symlink_and_fifo_refuse_before_body_read(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "body").write_bytes(b"x")
            (base / "link").symlink_to(base / "body")
            os.mkfifo(base / "fifo")
            for path in (base / "link", base / "fifo"):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    m.Capture.raw(path, 8)

    def test_preallocation_file_and_aggregate_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "body"
            path.write_bytes(b"large")
            with self.assertRaises(ValueError):
                m.Capture.raw(path, 4)
            capture = m.Capture()
            capture.total = m.MAX_BYTES
            with self.assertRaisesRegex(ValueError, "aggregate"):
                capture.read(path, {"path": str(path), "sha256": "a" * 64, "size_bytes": 5})

    def test_deadline_refuses(self):
        with self.assertRaisesRegex(ValueError, "deadline"):
            m.Capture(started=-1).deadline()

    def test_report_serialization_bound(self):
        with self.assertRaisesRegex(ValueError, "allocation"):
            m.bounded_canonical({"body": "x" * 100}, 20)

    def test_xml_failure_and_cleanup_error_pair_is_preserved(self):
        raw, declared = xml(["same", "same"], failures=1, errors=1)
        self.assertEqual(m.xml_receipt(raw, declared)["executions"], 2)

    def test_xml_repeated_success_identity_refuses(self):
        raw, declared = xml(["same", "same"])
        with self.assertRaisesRegex(ValueError, "duplicate XML"):
            m.xml_receipt(raw, declared)

    def test_xml_normalizes_entire_isolated_prefix_only(self):
        raw, declared = xml(["case[param]"], classname="isolation.arbitrary.test.api.test_case")
        row = m.xml_receipt(raw, declared)["cases"][0]
        self.assertEqual(row["normalized_classname"], "api.test_case")
        self.assertEqual(row["name"], "case[param]")


def semantic_control(path, value):
    def test(self):
        docs = copy.deepcopy(self.docs)
        target = docs
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        with self.assertRaises((ValueError, KeyError, TypeError)):
            m.reconcile(docs, self.bodies, self.workspace)
    return test


for _name, _path, _value in (
    ("stop_failure", ("current_worker_result", "stop", "status"), "failed"),
    ("foreign_tree", ("current_worker_result", "stop", "tree_id"), "foreign"),
    ("stop_without_fence", ("current_worker_result", "stop", "data", "old_tree_fenced"), False),
    ("foreign_allocation", ("cleanup_receipt", 0, "allocation", "record_id"), "foreign"),
    ("unproved_cleanup", ("cleanup_receipt", 0, "decision", "allowed"), False),
    ("cleanup_before_stop", ("cleanup_receipt", 0, "scope"), "before STOP"),
    ("scope_signature_changed", ("execution_scope_after", "binding", "signature"), "foreign"),
    ("task_population_reduced", ("execution_scope_before", "payload", "removed_task_cids"), ["removed"]),
    ("worker_uid_changed", ("authored_verification", "actual_stdout_observation", "receipt", "uid"), 1000),
    ("worker_pid_changed", ("authored_verification", "actual_stdout_observation", "receipt", "pid"), 42),
    ("worker_log_line_changed", ("authored_verification", "actual_stdout_observation", "line"), 1),
    ("provider_call", ("current_worker_result", "provider_calls"), 1),
    ("bool_zero", ("current_worker_result", "provider_calls"), False),
    ("new_fitting", ("current_worker_result", "post_setup_fit_attempt_count"), 1),
    ("numerical_summary_changed", ("current_worker_result", "numerical_after", "state_sha256"), "b" * 64),
    ("resource_not_drained", ("container_result", "host_resources_after_cleanup", "active_lease_count"), 1),
    ("container_not_removed", ("container_result", "container_removed"), False),
    ("network_promoted", ("container_result", "network"), "host"),
    ("live_registry_reopen", ("independent_worker_audit", "worker", "current_owner_registry_reopened"), True),
    ("native_job_bool", ("independent_worker_audit", "native_jobs_executed"), False),
    ("archive_one_pass", ("independent_worker_audit", "primary_archive", "passes"), 1),
    ("machine_proof_promoted", ("machine_review", "proof_authority"), True),
    ("constructor_failure_dropped", ("machine_review", "failed_tests", 1, "failures"), 0),
    ("count_bool", ("machine_review", "test_accounting", "new_unique"), True),
    ("overlap_changed", ("machine_review", "test_accounting", "overlap_prior"), 174),
    ("failed_cost_dropped", ("machine_review", "costs", "pytest_failed_receipt_seconds"), 0),
    ("nested_cost_sum", ("machine_review", "costs", "do_not_add_nested_phase_times"), False),
    ("stdlib_in_pytest", ("source_reader_guard", "pytest_cases"), 54),
    ("stdlib_count_bool", ("source_reader_guard", "test_count"), True),
    ("source_qualified_early", ("selected_source_receipt", "qualification_pending"), False),
    ("source_owner_alias", ("selected_source_receipt", "selected_sources", "ipfs_accelerate", 0, "path"), "/outside/source.py"),
    ("source_size_bool", ("selected_source_receipt", "selected_sources", "ipfs_accelerate", 0, "bytes"), True),
    ("source_digest_changed", ("selected_source_receipt", "selected_sources", "ipfs_accelerate", 0, "sha256"), "b" * 64),
    ("full_dependency_promotion", ("independent_worker_audit", "selected_generation", "full_transitive_dependency_attestation"), True),
    ("mutable_checkout_promotion", ("independent_worker_audit", "selected_generation", "mutable_working_checkout_qualified"), True),
):
    setattr(CustodyControls, "test_" + _name, semantic_control(_path, _value))


class StrictDocuments(unittest.TestCase):
    def test_duplicate_key(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            m.document(b'{"a":1,"a":2}')

    def test_nonfinite_and_oversized_integer(self):
        for raw in (b'{"a":NaN}', b'{"a":1e999}', b'{"a":999999999999999999999999}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                m.document(raw)

    def test_excessive_json_nesting(self):
        with self.assertRaisesRegex(ValueError, "structure"):
            m.document(b'{' + b'"a":[' * 34 + b'0' + b']' * 34 + b'}')

    def test_descriptor_extra_bool_and_alias(self):
        for value in ({"path": "/a", "sha256": "a" * 64, "size_bytes": True},
                      {"path": "/a/../b", "sha256": "a" * 64, "size_bytes": 1},
                      {"path": "/a", "sha256": "a" * 64, "size_bytes": 1, "extra": 2}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.descriptor(value)

    def test_xml_dtd_and_count_forgery(self):
        raw, declared = xml(["case"])
        for body, row in ((b'<!DOCTYPE a [<!ENTITY x "expansion">]>' + raw, declared),
                          (raw, {**declared, "tests": 2}), (raw, {**declared, "tests": True})):
            with self.subTest(row=row), self.assertRaises(ValueError):
                m.xml_receipt(body, row)

    def test_exact_output_population_rejects_extra_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "retained").mkdir()
            (base / "selected_custody.json").write_bytes(b"{}")
            expected = {"selected_custody.json"}
            self.assertEqual(m.population(base, expected)["file_count"], 1)
            (base / "extra").write_bytes(b"x")
            with self.assertRaises(ValueError):
                m.population(base, expected)
            (base / "extra").unlink()
            (base / "selected_custody.json").unlink()
            (base / "selected_custody.json").symlink_to(base / "retained")
            with self.assertRaises(ValueError):
                m.population(base, expected)


if __name__ == "__main__":
    unittest.main()

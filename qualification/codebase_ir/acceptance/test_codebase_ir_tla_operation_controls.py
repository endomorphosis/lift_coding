"""Independent authored packets: no external artifact or owner fixture discovery."""
import copy
import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).parent / "tla_operation_controls" / "receiver.py"
spec = importlib.util.spec_from_file_location("tla_operation_receiver_test", MODULE_PATH)
receiver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(receiver)


def fixtures():
    result = {"compiler_input": {"schema": "authored_no_execution"}}
    for label in ("valid", "invalid", "deadline"):
        model, config = "MODULE " + label + "\n", "INVARIANT " + label + "\n"
        result[label] = {"model_text": model, "model_digest": receiver.sha(model.encode()),
                         "tlc_config_text": config, "tlc_config_digest": receiver.sha(config.encode()),
                         "artifact_digest": receiver.sha(label.encode()), "bounded": True, "unbounded_proof": False}
    return result


def authored(ident="accepted"):
    """Authored receiving packet family, not a reconstructed native execution."""
    source = {"/captured/source" + str(i): receiver.sha(str(i).encode()) for i in range(78)}
    source["/captured/benchmark.py"] = "a" * 64
    wrapper = b"inert launcher description; never execute\n"
    config = {"total_cpu_slots": 4, "total_memory_mb": 9830}
    docs = {"fixtures": fixtures(), "wrapper": wrapper,
            "source_freeze": {"native_sources": source, "selected_sources": copy.deepcopy(source), "independent_review": {}, "native_runner_sha256": "f" * 64, "recorded_at_utc": "authored", "retained_sources": {}},
            "command_result": {"before": source, "after": copy.deepcopy(source), "returncode": 1, "seconds": 9.0,
                               "argv": ["/python", "/captured/benchmark.py", "--output", "/historical/attempt"], "cwd": "/historical", "env_overrides": {}},
            "command": {"benchmark_sha256": "a" * 64, "argv": ["/python", "/captured/benchmark.py", "--output", "/historical/attempt"], "cwd": "/historical"},
            "scheduler_config": {"config": config}, "request_audit": [], "launch_audit": [], "lifecycle_audit": [],
            "control_audit": {"phase_budgets": [], "boundaries": [], "triggers": []}}
    result = {key: None for key in receiver.RESULT_FIELDS}
    result.update(schema="tla-operation-control-benchmark@1", status="failed", error="tool_version exceeds maximum length of 256" if ident == "initial" else "interrupted aggregate operation published a result",
                  source_pins_before=source, source_pins_after=copy.deepcopy(source), elapsed_seconds=8.0,
                  shared_before={"config": config}, shared_after={"config": config, "owned_active_leases": 0, "owned_waiting_requests": 0},
                  tool_files_before={"/historical/tlc-memory-aware": receiver.sha(wrapper)},
                  tool_files_after={"/historical/tlc-memory-aware": receiver.sha(wrapper)},
                  checks={key: True for key in ("java_selection_environment_restored", "owned_work_drained", "selected_tool_files_unchanged", "shared_config_unchanged", "sources_stable")},
                  runs=[], controls=[], audit_sha256={})
    docs["result"] = result

    def add_phase(case, phase, label="valid"):
        argv = ["/historical/java", "-version"] if phase == "setup" else ["/historical/tlc", "-help"] if phase == "help" else ["/historical/tlc", "-config", "BoundedCounter.cfg", "BoundedCounter.tla"]
        case_label = case + ":constructor" if phase == "setup" else case
        fi = docs["fixtures"][label]
        inputs = {"BoundedCounter.tla": fi["model_text"].encode(), "BoundedCounter.cfg": fi["tlc_config_text"].encode()} if phase == "model" else {}
        limits = {"cpu_seconds": 1.0, "max_file_bytes": None, "max_workspace_bytes": 4096,
                  "enforce_file_size_limit": True, "memory_bytes": 1024, "resident_memory_bytes": 512,
                  "max_output_bytes": 4096, "timeout_seconds": 1.0}
        req = {"case": case_label, "argv": argv, "limits": limits, "input_bytes": {k: len(v) for k, v in inputs.items()},
               "input_sha256": {k: receiver.sha(v) for k, v in inputs.items()}, "output_paths": []}
        launch = {"case": case_label, "argv": ["/usr/bin/prlimit", "--core=0:0", "--fsize=4096:4096", "--cpu=1:1", "--as=1024:1024", "--"] + argv,
                  "at_monotonic": 10.0, "launch_lease_id": "recorded-lease", "owned_leases": [], "root_allocations": {}, "thread": 1, "waiting": 0}
        out = {key: False for key in receiver.LIFECYCLE_FLAGS}
        out.update(workspace_cleaned=True, pid=1, elapsed_seconds=0.1, command=argv, returncode=12 if label == "invalid" and phase == "model" else 0,
                   stdout="authored captured output", stderr="", error="", termination_reason="normal")
        life = {"case": case_label, "request": {"argv": argv, "stdin_is_empty": True, "java_option_environment_absent": True,
                    "input_file_count": len(inputs), "output_path_count": 0, "max_output_bytes": 4096, "memory_bytes": 1024,
                    "resident_memory_bytes": 512, "timeout_seconds": 1.0}, "result": out, "shared_backoff_after": {}}
        docs["request_audit"].append(req)
        docs["launch_audit"].append(launch)
        docs["lifecycle_audit"].append(life)
        docs["control_audit"]["phase_budgets"].append({"case": case, "phase": phase, "at_monotonic": 10.0,
                                                     "deadline": 12.0, "remaining_seconds": 1.9999, "request_timeout_seconds": 1.0})
        return out

    for workers in ([] if ident == "initial" else [1, 2, 4]):
        batch = {"workers": workers, "elapsed_seconds": 2.0, "cases": []}
        for route in ("engine", "helper"):
            for valid in (True, False):
                case = f"parallel:{workers}:{route}:{valid}"
                label = "valid" if valid else "invalid"
                add_phase(case, "setup", label)
                life = add_phase(case, "model", label)
                add_phase(case, "help", label)
                fixture = docs["fixtures"][label]
                states = [] if valid else [{"index": i, "assignments": {"n": str(i - 1)}} for i in (1, 2, 3)]
                receipt = {"artifact_digest": fixture["artifact_digest"], "model_digest": fixture["model_digest"],
                           "configuration_digest": fixture["tlc_config_digest"], "timeout_seconds": 15.0,
                           "stdout": life["stdout"], "stderr": "", "command": life["command"], "returncode": life["returncode"],
                           "output_truncated": False, "bounded": True, "unbounded_proof": False,
                           "counterexample": None if valid else {"states": states}}
                wire_receipt = copy.deepcopy(receipt)
                wire_receipt["timeout_seconds"] = 15
                evidence = {"receipt": wire_receipt, "request_digest": "b" * 64, "module": {"artifact_digest": fixture["artifact_digest"]},
                            "claim_proof": False, "claim_theorem": False, "authorizes_universal_proof": False, "proof_established": False, "theorem_established": False, "is_proved": False, "is_theorem_authority": False, "authority_ceiling": "bounded",
                            "disposition": "satisfied" if valid else "counterexample", "counterexample": {"states": states, "state_count": len(states), "replayed": not valid}}
                outcome = {"schema_version": "state-execution-result/v2", "interface": "StateExecutionResult@2", "counterexample_status": "clean_no_counterexample" if valid else "replayed", "provider": "tlc", "request_id": "req:" + case, "request_digest": "b" * 64,
                           "result": {"historical": True}, "evidence": evidence, "disposition": evidence["disposition"],
                           "outcome": {"request_digest": "c" * 64, "result": {"historical": True}, "receipt": receipt,
                                       "artifacts": {"artifact_digest": fixture["artifact_digest"], "model_digest": fixture["model_digest"]}}}
                batch["cases"].append({"case": case, "route": route, "valid": valid, "phase_count": 3, "result": outcome})
        result["runs"].append(batch)
    if ident == "initial":
        for valid in (True, False):
            for p in ("setup", "model", "help"):
                add_phase(f"parallel:1:engine:{valid}", p, "valid" if valid else "invalid")
        docs["partial"] = None
    else:
        for kind, phases in zip(receiver.STOP_KINDS, ((), ("setup",), ("setup",), ("setup",), ("setup", "model")), strict=True):
            case = "control:" + kind
            for p in phases:
                add_phase(case, p)
            timed = kind == "compile_deadline"
            result["controls"].append({"case": case, "kind": kind, "result_published": False, "operation_timeout_ms": 5000,
                                       "phase_count": len(phases), "phases": list(phases), "interruption": {
                                           "type": "ProofOperationTimeout" if timed else "ProofOperationCancelled",
                                           "kind": "timeout" if timed else "cancelled", "timeout_ms": 5000, "elapsed_ms": 0}})
        for p in ("setup", "model", "help"):
            add_phase("control:live_model_deadline", p, "deadline")
        docs["partial"] = {"status": "running", "runs": copy.deepcopy(result["runs"]), "controls": [], "checks": {}}
    result.update(launches=len(docs["request_audit"]), lifecycles=len(docs["request_audit"]), native_lifecycles=len(docs["request_audit"]),
                  prelaunch_lifecycles=0, phase_counts={"setup": 2, "model": 2, "help": 2} if ident == "initial" else {"setup": 17, "model": 14, "help": 13})
    for role in ("request_audit", "launch_audit", "lifecycle_audit", "control_audit"):
        result["audit_sha256"][role.replace("_", "-") + ".json"] = receiver.sha(receiver.canonical(docs[role]))
    return docs


def authored_files(root):
    inputs = root / "inputs"
    inputs.mkdir()
    attempts, anchors = [], {}
    for ident in receiver.IDS:
        docs = authored(ident)
        row, pins = {"id": ident}, {}
        for role in receiver.ROLES:
            value = docs[role]
            if value is None:
                row[role] = None
                continue
            raw = value if role == "wrapper" else receiver.canonical(value)
            path = inputs / (ident + "-" + role + ".bin")
            path.write_bytes(raw)
            row[role] = {"path": str(path), "sha256": receiver.sha(raw), "size_bytes": len(raw)}
            if role in receiver.ANCHORS[ident]:
                pins[role] = receiver.sha(raw)
        attempts.append(row)
        anchors[ident] = pins
    path = inputs / "manifest.json"
    path.write_bytes(receiver.canonical({"schema": receiver.INPUT_SCHEMA, "fixture_origin": "retained_failed_tla_operation_attempts", "attempts": attempts}))
    return path, anchors


class FullAuditTests(unittest.TestCase):
    def test_authored_closed_file_profile_and_exact_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, anchors = authored_files(root)
            with patch.object(receiver, "ANCHORS", anchors):
                report = receiver.audit(manifest, root / "output")
            self.assertEqual(report["recorded_native_phase_count"], 94)
            self.assertEqual(report["completed_case_count"], 24)
            self.assertEqual(report["recorded_no_result_control_count"], 10)
            self.assertEqual(report["controls_count"], 22)
            self.assertEqual(len(report["retained_files"]), 36)
            self.assertEqual(len(list((root / "output").rglob("*"))), 38)
            self.assertTrue(all(report[x] is False for x in receiver.FALSE))
            self.assertTrue(all(type(report[x]) is int and report[x] == 0 for x in receiver.ZERO))
            self.assertEqual(json.loads((root / "output" / receiver.REPORT_NAME).read_bytes()), report)

    def test_independent_anchor_refuses_repaired_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, anchors = authored_files(root)
            m = json.loads(manifest.read_bytes())
            pin = m["attempts"][0]["source_freeze"]
            path = Path(pin["path"])
            d = json.loads(path.read_bytes())
            d["unbound_extra"] = "repaired internal descriptor"
            raw = receiver.canonical(d)
            path.write_bytes(raw)
            pin.update(sha256=receiver.sha(raw), size_bytes=len(raw))
            manifest.write_bytes(receiver.canonical(m))
            with patch.object(receiver, "ANCHORS", anchors):
                with self.assertRaisesRegex(receiver.Refusal, "immutable independent"):
                    receiver.audit(manifest, root / "output")
            self.assertFalse((root / "output").exists())

    def test_output_scope_protects_original_manifest_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, anchors = authored_files(Path(tmp))
            with patch.object(receiver, "ANCHORS", anchors):
                with self.assertRaisesRegex(receiver.Refusal, "outside inputs"):
                    receiver.audit(manifest, manifest.parent / "output")

    def test_manifest_attempt_order_refused_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, anchors = authored_files(root)
            d = json.loads(manifest.read_bytes())
            d["attempts"].reverse()
            manifest.write_bytes(receiver.canonical(d))
            with patch.object(receiver, "ANCHORS", anchors):
                with self.assertRaisesRegex(receiver.Refusal, "ordered attempt"):
                    receiver.audit(manifest, root / "output")

    def test_late_original_body_after_reconciliation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, anchors = authored_files(root)
            packet = Path(json.loads(manifest.read_bytes())["attempts"][0]["wrapper"]["path"])
            original = receiver.final_fence
            def injected(c, output, expected):
                raw = packet.read_bytes()
                packet.write_bytes(raw[:-1] + b" ")
                original(c, output, expected)
            with patch.object(receiver, "ANCHORS", anchors), patch.object(receiver, "final_fence", injected):
                with self.assertRaisesRegex(receiver.Refusal, "late original/copy/report"):
                    receiver.audit(manifest, root / "output")

    def test_boolean_trace_index_refused_after_receipt_repair(self):
        d = authored()
        out = d["result"]["runs"][0]["cases"][1]["result"]
        out["evidence"]["counterexample"]["states"][0]["index"] = True
        out["evidence"]["receipt"]["counterexample"]["states"][0]["index"] = True
        out["outcome"]["receipt"]["counterexample"]["states"][0]["index"] = True
        with self.assertRaisesRegex(receiver.Refusal, "finite trace custody"):
            receiver.reconcile_attempt("accepted", d)

    def test_late_report_byte_drift_is_observed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, anchors = authored_files(root)
            original = receiver.final_fence
            def injected(c, output, expected):
                path = output / receiver.REPORT_NAME
                raw = path.read_bytes()
                path.write_bytes(raw[:-1] + b" ")
                original(c, output, expected)
            with patch.object(receiver, "ANCHORS", anchors), patch.object(receiver, "final_fence", injected):
                with self.assertRaisesRegex(receiver.Refusal, "late original/copy/report"):
                    receiver.audit(manifest, root / "output")

    def test_late_retained_copy_after_reconciliation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, anchors = authored_files(root)
            original = receiver.final_fence
            def injected(c, output, expected):
                path = next((output / "retained").iterdir())
                raw = path.read_bytes()
                path.write_bytes(raw[:-1] + b" ")
                original(c, output, expected)
            with patch.object(receiver, "ANCHORS", anchors), patch.object(receiver, "final_fence", injected):
                with self.assertRaisesRegex(receiver.Refusal, "late original/copy/report"):
                    receiver.audit(manifest, root / "output")

    def test_late_output_root_alias_before_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, anchors = authored_files(root)
            original = receiver.final_fence
            def injected(c, output, expected):
                moved = root / "moved"
                output.rename(moved)
                output.symlink_to(moved, target_is_directory=True)
                original(c, output, expected)
            with patch.object(receiver, "ANCHORS", anchors), patch.object(receiver, "final_fence", injected):
                with self.assertRaisesRegex(receiver.Refusal, "canonical"):
                    receiver.audit(manifest, root / "output")


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.docs = authored()

    def refusal(self, mutate, pattern):
        d = copy.deepcopy(self.docs)
        mutate(d)
        with self.assertRaisesRegex(receiver.Refusal, pattern):
            receiver.reconcile_attempt("accepted", d)

    def test_independent_population_and_unknown_goldens(self):
        records = [receiver.reconcile_attempt(i, authored(i)) for i in receiver.IDS]
        self.assertEqual([x["phase_count"] for x in records], [6, 44, 44])
        self.assertEqual([x["completed_case_count"] for x in records], [0, 12, 12])
        self.assertEqual([x["recorded_no_result_control_count"] for x in records], [0, 5, 5])
        self.assertEqual([len(x["unreturned_operation_phases"]) for x in records], [6, 3, 3])
        self.assertTrue(all(x["recorded_whole_status"] == "failed" for x in records))
        self.assertTrue(all(x["whole_operation_success_qualified"] is False for x in records))
        self.assertEqual(records[1]["partial_status"], "running")

    def test_correlated_record_controls(self):
        controls = receiver.mutation_controls([(i, authored(i)) for i in receiver.IDS])
        self.assertEqual(len(controls), 22)
        self.assertTrue(all(x["refused"] is True for x in controls))

    def test_duplicate_phase(self):
        self.refusal(lambda d: d["request_audit"].append(d["request_audit"][0]), "ambiguous")

    def test_case_order(self):
        self.refusal(lambda d: d["result"]["runs"][0]["cases"].reverse(), "ordered native cases")

    def test_boolean_lifecycle_return(self):
        self.refusal(lambda d: d["lifecycle_audit"][0]["result"].update(returncode=False), "returncode type")

    def test_bool_resource_bound(self):
        self.refusal(lambda d: d["request_audit"][0]["limits"].update(memory_bytes=True), "wrapper bounds")

    def test_stopped_result_cannot_publish(self):
        self.refusal(lambda d: d["result"]["controls"][0].update(result_published=True), "has no result")

    def test_stop_budget_boolean(self):
        self.refusal(lambda d: d["result"]["controls"][0].update(operation_timeout_ms=True), "outer interruption")

    def test_partial_success_refused(self):
        self.refusal(lambda d: d["partial"].update(status="passed"), "partial snapshot")

    def test_typed_phase_total(self):
        self.refusal(lambda d: d["result"].update(launches=True), "total phase")

    def test_source_drift_even_matching_command(self):
        self.refusal(lambda d: d["result"]["source_pins_after"].update({"/captured/source0": "0" * 64}), "source declarations")

    def test_repaired_unsafe_lifecycle_cannot_establish_case(self):
        d = copy.deepcopy(self.docs)
        d["lifecycle_audit"][1]["result"]["timed_out"] = True
        with self.assertRaisesRegex(receiver.Refusal, "safe recorded lifecycle"):
            receiver.reconcile_attempt("accepted", d)

    def test_fixture_text_rehashed_identity_still_bound_to_request(self):
        def mutate(d):
            f = d["fixtures"]["valid"]
            f["model_text"] += "changed"
            f["model_digest"] = receiver.sha(f["model_text"].encode())
        self.refusal(mutate, "module/config identities")

    def test_raw_trace_population(self):
        def mutate(d):
            e = d["result"]["runs"][0]["cases"][1]["result"]["evidence"]
            e["counterexample"]["state_count"] = True
        self.refusal(mutate, "counterexample population")

    def test_engine_and_backend_request_digests_remain_distinct(self):
        r = receiver.reconcile_attempt("accepted", self.docs)
        c = r["completed_cases"][0]["recorded_result"]
        self.assertNotEqual(c["request_digest"], c["outcome"]["request_digest"])
        self.assertEqual(c["outcome"]["receipt"]["timeout_seconds"], 15.0)
        self.assertIs(type(c["evidence"]["receipt"]["timeout_seconds"]), int)

    def test_phase_budget_samples_are_not_enforcement(self):
        d = copy.deepcopy(self.docs)
        d["control_audit"]["phase_budgets"][0]["remaining_seconds"] = 0.99
        r = receiver.reconcile_attempt("accepted", d)
        self.assertGreater(r["phases"][0]["budget"]["request_timeout_seconds"], r["phases"][0]["budget"]["remaining_seconds"])
        self.assertIs(r["phases"][0]["authentication_verified"], False)


class JSONAndCaptureTests(unittest.TestCase):
    def test_duplicate_json(self):
        with self.assertRaisesRegex(receiver.Refusal, "duplicate"):
            receiver.document(b'{"a":1,"a":2}')

    def test_nonfinite_and_surrogate_json(self):
        for raw in (b'{"v":NaN}', b'{"v":1e999}', b'{"v":"\\ud800"}', b'{"v":123456789012345678901}'):
            with self.subTest(raw=raw), self.assertRaises(receiver.Refusal):
                receiver.document(raw)

    def test_finite_numbers_and_bool_separate(self):
        self.assertFalse(receiver.number(True))
        self.assertFalse(receiver.number(math.inf))
        self.assertFalse(receiver.integer(False))

    def test_preallocation_refusal_does_not_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "packet"
            path.write_bytes(b"1234")
            with patch.object(receiver.os, "open", side_effect=AssertionError("must not open")):
                with self.assertRaisesRegex(receiver.Refusal, "preallocation"):
                    receiver.bounded(path, 3)

    def test_aggregate_actual_read_cap_and_growth(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "packet"
            path.write_bytes(b"1234")
            c = receiver.Capture()
            c.total = receiver.MAX_TOTAL - 3
            with self.assertRaisesRegex(receiver.Refusal, "preallocation"):
                c.take(path)

    def test_original_late_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "packet"
            path.write_bytes(b"abc")
            c = receiver.Capture()
            c.take(path)
            path.write_bytes(b"abd")
            with self.assertRaisesRegex(receiver.Refusal, "late original"):
                c.stable()

    def test_symlink_and_fifo_refused_without_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / "packet"
            p.write_bytes(b"abc")
            alias = root / "alias"
            alias.symlink_to(p)
            with self.assertRaisesRegex(receiver.Refusal, "canonical"):
                receiver.bounded(alias, 8)
            fifo = root / "fifo"
            receiver.os.mkfifo(fifo)
            with self.assertRaisesRegex(receiver.Refusal, "regular"):
                receiver.bounded(fifo, 8)

    def test_output_population_extra_and_root_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "output"
            root.mkdir()
            (root / "retained").mkdir()
            p = root / "retained/packet"
            p.write_bytes(b"abc")
            receiver.output_population(root, {"retained/packet"})
            (root / "extra").write_bytes(b"extra")
            with self.assertRaisesRegex(receiver.Refusal, "unexpected output"):
                receiver.output_population(root, {"retained/packet"})
            (root / "extra").unlink()
            alias = Path(tmp) / "alias"
            alias.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(receiver.Refusal, "canonical output"):
                receiver.output_population(alias, {"retained/packet"})

    def test_late_extra_reaches_final_fence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "output"
            root.mkdir()
            (root / "retained").mkdir()
            p = root / "retained/packet"
            p.write_bytes(b"abc")
            c = receiver.Capture()
            c.take(p)
            stable = c.stable
            def injected():
                stable()
                (root / "extra").write_bytes(b"late")
            with patch.object(c, "stable", injected):
                with self.assertRaisesRegex(receiver.Refusal, "unexpected output"):
                    receiver.final_fence(c, root, {"retained/packet"})

    def test_late_nested_copy_alias_reaches_reread(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "output"
            root.mkdir()
            (root / "retained").mkdir()
            p = root / "retained/packet"
            p.write_bytes(b"abc")
            c = receiver.Capture()
            c.take(p)
            p.unlink()
            original = Path(tmp) / "original"
            original.write_bytes(b"abc")
            p.symlink_to(original)
            with self.assertRaisesRegex(receiver.Refusal, "canonical"):
                receiver.final_fence(c, root, {"retained/packet"})


if __name__ == "__main__":
    unittest.main()

"""Independent bounded assertions for retained, support-only JVM probe custody."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jvm_probe_controls import receiver


def retained_fixture():
    relative = Path("artifacts/codebase_ir_parallel_qualification/acceptance/20261003-jvm-probe-custody-input-01/jvm_probe_custody_input.json")
    for root in (Path.cwd().resolve(), *Path(__file__).resolve().parents):
        candidate = root / relative
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("selected frozen JVM probe receiving fixture unavailable")


INPUT = retained_fixture()


class JvmProbeCustodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = receiver.document(INPUT.read_bytes())
        cls.documents, cls.sources = {}, []
        for role in receiver.ROLES:
            descriptor = cls.spec[role]
            raw = Path(descriptor["path"]).read_bytes()
            if len(raw) != descriptor["bytes"] or receiver.codec.sha(raw) != descriptor["sha256"]:
                raise AssertionError("frozen JVM fixture pin drift")
            if role.startswith("runtime_"):
                cls.sources.append(raw)
            else:
                cls.documents[role] = receiver.document(raw)

    def packet(self):
        return copy.deepcopy(self.documents)

    def repair_audits(self, packet):
        for role in ("launch_audit", "lifecycle_audit", "control_audit"):
            packet["native_result"][receiver.ROLES[role].split("/")[-1] + "_sha256"] = receiver.raw_document_hash(packet[role])

    def refusal(self, packet):
        self.repair_audits(packet)
        with self.assertRaises((receiver.codec.ReceiverRefusal, KeyError)):
            receiver.receive(packet, self.sources)

    def private_input(self, directory):
        folder = directory / "frozen"
        folder.mkdir()
        spec = copy.deepcopy(self.spec)
        for index, role in enumerate(receiver.ROLES):
            source = Path(spec[role]["path"])
            target = folder / f"{index:02d}-{source.name}"
            target.write_bytes(source.read_bytes())
            spec[role]["path"] = str(target)
        manifest = directory / "manifest.json"
        manifest.write_text(json.dumps(spec, sort_keys=True, indent=2) + "\n")
        return manifest, spec

    def test_independent_golden_full_population_and_stop_outcomes(self):
        value = receiver.receive(self.packet(), self.sources)
        self.assertEqual((len(value["successful_probes"]), len(value["stopped_calls"]), len(value["phase_receipts"])), (32, 4, 34))
        self.assertEqual([v["recorded_native_phase_count"] for v in value["stopped_calls"]], [0, 0, 1, 1])
        self.assertEqual([v["recorded_outcome"] for v in value["stopped_calls"]], ["unusable_identity"] * 3 + ["typed_ambient_interruption"])
        self.assertTrue(all(v["returned_usable_identity"] is False for v in value["stopped_calls"]))

    def test_independently_stated_output_hash_major_and_request_command(self):
        value = receiver.receive(self.packet(), self.sources)
        self.assertEqual(value["successful_probes"][0]["recorded_banner_sha256"], "e932202eb16af75b1a6fa26182b22c70e8917a22df65512bdfdeae33c203150c")
        self.assertEqual({v["recorded_major"] for v in value["successful_probes"]}, {17})
        self.assertEqual(value["phase_receipts"][0]["recorded_stdout_sha256"], "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        self.assertEqual(value["phase_receipts"][0]["recorded_stderr_sha256"], "910f45f78e37f2d8aa0fd18b673c94df8009855846d392a2dfa9c588e1e300b4")

    def test_original_ordered_routes_widths_repeats_and_nested_members(self):
        value = receiver.receive(self.packet(), self.sources)
        names = [v["case"] for v in value["successful_probes"]]
        self.assertEqual(names[:5], ["parallel:1:0:" + route for route in receiver.ROUTES])
        self.assertEqual(names[-2:], ["nested:direct_banner", "nested:runtime_probe"])
        self.assertEqual(len(set(names)), 32)
        packet = self.packet()
        packet["native_result"]["runs"][1]["cases"].reverse()
        self.refusal(packet)

    def test_separate_wire_golden_seven_fields_and_fixture_origin(self):
        value = receiver.wire_compatibility(self.documents, self.sources)
        self.assertEqual(value["wire_fields"], ["executable", "source", "minimum_major", "banner", "major", "usable", "reason_code"])
        self.assertEqual(value["runtime"]["minimum_major"], 11)
        self.assertEqual(value["runtime"]["executable"], "/fixture/java")
        self.assertFalse(value["native_probe_identity_inferred_from_wire_fixture"])
        self.assertEqual(value["fixture_origin"], "separate_deterministic_non_native_wire_observation")

    def test_wire_ast_drift_is_detected_without_importing_runtime(self):
        changed = self.sources[1].replace(b"class JavaRuntimeProbe:", b"class DifferentRuntimeProbe:", 1)
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "one inert"):
            receiver.wire_compatibility(self.documents, [self.sources[0], changed])
        changed = self.sources[1].replace(b"minimum_major: int", b"minimum_major: float", 1)
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "AST"):
            receiver.wire_compatibility(self.documents, [self.sources[0], changed])

    def test_wire_missing_extra_or_numeric_usability_refuses(self):
        for mutation in (lambda v: v.pop("reason_code"), lambda v: v.update(proved=True), lambda v: v.update(usable=1)):
            packet = self.packet()
            mutation(packet["wire_after"]["runtime"])
            self.refusal(packet)

    def test_constructor_and_registry_support_never_become_model_checks(self):
        value = receiver.receive(self.packet(), self.sources)
        self.assertTrue(all(v["support_only"] is True and v["model_checker_executed"] is False for v in value["successful_probes"]))
        for field, content in (("model_checker_executed", True), ("jvm_usable", 1), ("checker_availability", True)):
            packet = self.packet()
            packet["native_result"]["runs"][0]["cases"][2]["outcome"][field] = content
            self.refusal(packet)

    def test_major_and_returncode_boolean_aliases_are_rejected(self):
        for location, field, content in (("case", "observed_major", True), ("outcome", "returncode", False), ("result", "returncode", False)):
            packet = self.packet()
            case = packet["native_result"]["runs"][0]["cases"][0]
            target = case if location == "case" else case["outcome"] if location == "outcome" else packet["lifecycle_audit"][0]["result"]
            target[field] = content
            self.refusal(packet)

    def test_banner_and_lifecycle_output_join_is_independent_of_digest_repair(self):
        packet = self.packet()
        case = packet["native_result"]["runs"][0]["cases"][0]
        case["outcome"]["banner"] = "openjdk version \"17.0.1\" changed"
        case["banner_sha256"] = receiver.codec.sha(case["outcome"]["banner"].encode())
        self.refusal(packet)

    def test_root_parent_accounting_does_not_charge_nested_children_twice(self):
        value = receiver.receive(self.packet(), self.sources)
        self.assertEqual(value["recorded_peak_root_allocations"], {"cpu_slots": 4, "child_process_slots": 4, "memory_mb": 1024})
        nested = [v for v in value["phase_receipts"] if v["parent_lease_id_claim"] is not None]
        self.assertEqual(len(nested), 2)
        self.assertEqual(len({v["parent_lease_id_claim"] for v in nested}), 1)
        self.assertTrue(all(v["recorded_root_allocations"]["memory_mb"] == 512 for v in nested))
        packet = self.packet()
        next(v for v in packet["launch_audit"] if v["case"].startswith("nested:"))["root_allocations"]["memory_mb"] = 1024
        self.refusal(packet)

    def test_child_cannot_reference_an_uncaptured_or_another_child_parent(self):
        packet = self.packet()
        launch = next(v for v in packet["launch_audit"] if v["case"].startswith("nested:"))
        child = next(v for v in launch["owned_leases"] if v["lease_id"] == launch["launch_lease_id"])
        child["parent_lease_id"] = "0" * 32
        self.refusal(packet)

    def test_owner_pid_boot_and_reservation_type_are_exact(self):
        for field, content in (("owner_pid", True), ("owner_boot_id", "other-boot"), ("memory_mb", 512)):
            packet = self.packet()
            packet["launch_audit"][0]["owned_leases"][0][field] = content
            self.refusal(packet)

    def test_coherent_command_memory_limits_and_jvm_flags_refuse(self):
        packet = self.packet()
        life = packet["lifecycle_audit"][0]
        life["request"]["argv"][2] = life["result"]["command"][2] = "-Xmx256m"
        packet["launch_audit"][0]["argv"][8] = "-Xmx256m"
        self.refusal(packet)
        packet = self.packet()
        packet["lifecycle_audit"][0]["request"]["memory_bytes"] *= 2
        packet["launch_audit"][0]["argv"][4] = "--as=8589934592:8589934592"
        self.refusal(packet)

    def test_ambient_short_deadline_and_local_deadline_remain_distinct(self):
        value = receiver.receive(self.packet(), self.sources)
        self.assertGreater(value["phase_receipts"][-2]["declared_timeout_seconds"], 9.9)
        self.assertLess(value["phase_receipts"][-1]["declared_timeout_seconds"], 5)
        packet = self.packet()
        packet["lifecycle_audit"][-1]["request"]["timeout_seconds"] = 9.0
        self.refusal(packet)

    def test_recorded_empty_input_output_limits_and_environment_are_typed(self):
        for field, content in (("stdin_is_empty", 1), ("input_file_count", True), ("max_output_bytes", 131072), ("java_option_environment_absent", False)):
            packet = self.packet()
            packet["lifecycle_audit"][0]["request"][field] = content
            self.refusal(packet)

    def test_environment_case_thread_and_lease_custody_must_join(self):
        for field, content in (("thread", 1), ("launch_lease_id", "0" * 32), ("java_option_environment_absent", False)):
            packet = self.packet()
            packet["control_audit"]["native_environments"][0][field] = content
            self.refusal(packet)

    def test_missing_duplicate_and_unselected_phase_refuse_after_audit_rehash(self):
        for mutation in (lambda p: p["lifecycle_audit"].pop(), lambda p: p["launch_audit"].append(copy.deepcopy(p["launch_audit"][0])),
                         lambda p: p["lifecycle_audit"][0].update(case="unselected:case")):
            packet = self.packet()
            mutation(packet)
            self.refusal(packet)

    def test_precancel_has_no_lifecycle_and_withholds_support_identity(self):
        packet = self.packet()
        packet["native_result"]["controls"][0]["outcome"] = [17, "late banner"]
        self.refusal(packet)
        packet = self.packet()
        packet["native_result"]["controls"][0]["phase_count"] = packet["native_result"]["controls"][0]["launch_count"] = 1
        self.refusal(packet)

    def test_local_stop_and_ambient_exception_cannot_be_swapped(self):
        packet = self.packet()
        packet["native_result"]["controls"][2]["outcome"] = [17, "late banner"]
        self.refusal(packet)
        packet = self.packet()
        packet["native_result"]["controls"][3]["exception"]["kind"] = "timeout"
        self.refusal(packet)

    def test_stop_trigger_pid_and_no_followup_are_independently_bound(self):
        for mutation in (lambda v: v["trigger"].update(pid=1), lambda v: v.update(no_followup_launch=False)):
            packet = self.packet()
            mutation(packet["native_result"]["controls"][2])
            self.refusal(packet)

    def test_stopped_lifecycle_cannot_retain_partial_success(self):
        for field, content in (("process_tree_terminated", False), ("workspace_cleaned", 1), ("returncode", 0), ("stderr", "late usable Java")):
            packet = self.packet()
            packet["lifecycle_audit"][-1]["result"][field] = content
            self.refusal(packet)

    def test_final_work_source_generation_and_whole_result_are_not_cached(self):
        for mutation in (lambda p: p["native_result"]["shared_after"].update(owned_active_leases=1),
                         lambda p: p["native_result"].update(status="failed"),
                         lambda p: p["native_result"]["source_pins_after"].update({next(iter(p["native_result"]["source_pins_after"])): "0" * 64})):
            packet = self.packet()
            mutation(packet)
            self.refusal(packet)

    def test_raw_anchor_repin_and_input_extra_roles_refuse(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest, spec = self.private_input(root)
            body = Path(spec["prior_qualification"]["path"])
            changed = receiver.document(body.read_bytes())
            changed["status"] = "passed"
            raw = (json.dumps(changed, sort_keys=True, indent=2) + "\n").encode()
            body.write_bytes(raw)
            spec["prior_qualification"].update(sha256=receiver.codec.sha(raw), bytes=len(raw))
            manifest.write_text(json.dumps(spec))
            with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "fixed independent"):
                receiver.load_input(manifest)
            spec["extra"] = {}
            manifest.write_text(json.dumps(spec))
            with self.assertRaises(receiver.codec.ReceiverRefusal):
                receiver.load_input(manifest)

    def test_private_only_read_and_report_all_claims_have_exact_types(self):
        reads = []
        original = receiver.codec.OriginalCapture.read

        def tracking(path, limit):
            reads.append(path)
            self.assertNotIn("/external/", str(path))
            return original(path, limit)

        with tempfile.TemporaryDirectory() as temp, patch.object(receiver.codec.OriginalCapture, "read", side_effect=tracking):
            report = receiver.audit(INPUT, Path(temp) / "out")
        self.assertTrue(reads)
        self.assertEqual(report["input_bytes"], 622795)
        self.assertEqual(report["mutation_control_count"], 37)
        self.assertEqual(report["historical_qualification_status"], "passed_partial_scope")
        for key in receiver.TRUE_FLAGS:
            self.assertIs(report[key], True)
        for key in receiver.FALSE_FLAGS:
            self.assertIs(report[key], False)
        for key in ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"):
            self.assertEqual(type(report[key]), int)
            self.assertEqual(report[key], 0)
        self.assertEqual(report["native_result_sha256"], "ddeb99132e4108f541f61c2dc1127463d19ca27f3f288b21719f11539e8d5837")

    def test_copied_manifest_can_write_sibling_but_not_frozen_body_scopes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest, spec = self.private_input(root)
            with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "outside frozen"):
                receiver.audit(manifest, Path(spec["native_result"]["path"]).parent / "forbidden")
            self.assertEqual(receiver.audit(manifest, root / "sibling")["status"], "passed")

    def test_output_symlink_ancestor_and_existing_output_refuse(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "existing").mkdir()
            with self.assertRaises(receiver.codec.ReceiverRefusal):
                receiver.audit(INPUT, root / "existing")
            (root / "link").symlink_to(root / "existing", target_is_directory=True)
            with self.assertRaises(receiver.codec.ReceiverRefusal):
                receiver.audit(INPUT, root / "link" / "new")

    def test_descriptor_allocation_bound_precedes_read_and_stability_uses_captured_length(self):
        capture = receiver.Capture()
        capture.total = receiver.MAX_TOTAL - 3
        path = Path("/bounded/input")
        with patch.object(receiver.codec.OriginalCapture, "read", return_value=b"abc") as read:
            capture.take(path, {"bytes": 3, "sha256": receiver.codec.sha(b"abc")}, limit=1000)
            capture.stable()
        self.assertEqual([call.args[1] for call in read.call_args_list], [3, 3])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "growing"
            path.write_bytes(b"abcd")
            with self.assertRaises(receiver.codec.ReceiverRefusal):
                receiver.Capture().take(path, {"bytes": 3, "sha256": receiver.codec.sha(b"abc")})

    def test_file_count_duplicate_paths_and_strict_json_refuse(self):
        capture = receiver.Capture()
        capture.raw = {Path(f"/input/{i}"): b"" for i in range(receiver.MAX_FILES)}
        with self.assertRaises(receiver.codec.ReceiverRefusal):
            capture.take(Path("/extra"))
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'{"x":"\\ud800"}', b'{"x":9223372036854775808}'):
            with self.assertRaises(receiver.codec.ReceiverRefusal):
                receiver.document(raw)
        with self.assertRaises(receiver.codec.ReceiverRefusal):
            receiver.number(10**400)

    def test_original_frozen_body_changed_during_receiving_refuses(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest, spec = self.private_input(root)
            original = receiver.receive

            def changing(documents, sources):
                value = original(documents, sources)
                Path(spec["native_result"]["path"]).write_bytes(b"drift")
                return value

            with patch.object(receiver, "receive", side_effect=changing):
                with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "input drift"):
                    receiver.audit(manifest, root / "out")

    def test_late_retained_copy_drift_refuses_before_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest, _ = self.private_input(root)
            original = receiver.Capture.stable
            calls = 0

            def changing(capture):
                nonlocal calls
                original(capture)
                calls += 1
                if calls == 2:
                    next((root / "out" / "inputs").iterdir()).write_bytes(b"drift")

            with patch.object(receiver.Capture, "stable", changing):
                with self.assertRaises(receiver.codec.ReceiverRefusal):
                    receiver.audit(manifest, root / "out")
            self.assertFalse((root / "out" / "jvm_probe_custody.json").exists())

    def test_all_correlated_controls_preserve_independent_anchors(self):
        prior = copy.deepcopy(self.documents)
        controls = receiver.mutation_controls(self.documents, self.sources)
        self.assertEqual(len(controls), 37)
        self.assertEqual(len({v["name"] for v in controls}), 37)
        self.assertTrue(all(v["rejected"] is True and v["independent_anchors_preserved"] is True
                            and v["mutable_audit_digests_recomputed"] is True for v in controls))
        self.assertEqual(self.documents, prior)

    def test_unsigned_launcher_hash_can_be_changed_without_authenticating_binary(self):
        # A well formed arbitrary digest cannot be refuted without the launcher
        # body. Passing consistency retains this gap and confers no tool identity.
        packet = self.packet()
        packet["native_result"]["executable"]["sha256"] = "0" * 64
        value = receiver.receive(packet, self.sources)
        self.assertEqual(len(value["successful_probes"]), 32)


if __name__ == "__main__":
    unittest.main()

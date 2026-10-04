"""Authored receiving controls; no producer fixtures, imports or execution."""

import copy
import importlib.util
import json
import os
import tempfile
import unittest
from collections import Counter
from hashlib import sha256
from pathlib import Path
from unittest import mock
from xml.sax.saxutils import quoteattr

_SPEC = importlib.util.spec_from_file_location(
    "dispatch_custody", Path(__file__).with_name("dispatch_attempt_custody.py")
)
m = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(m)


def write_doc(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = m.canonical(value)
    path.write_bytes(raw)
    return pin(path)


def pin(path):
    raw = path.read_bytes()
    return {
        "path": str(path),
        "bytes": len(raw),
        "sha256": sha256(raw).hexdigest(),
        "present": True,
    }


def phase_fixture(count, failed=0, teardown=0):
    records = []
    for index in range(count):
        for phase in ("setup", "call", "teardown"):
            outcome = (
                "failed"
                if phase == "call" and index < failed or phase == "teardown" and index < teardown
                else "passed"
            )
            records.append(
                {
                    "nodeid": "test/check.py::case_" + str(index),
                    "when": phase,
                    "outcome": outcome,
                    "duration_seconds": 0.1,
                }
            )
    counts = {
        "actual_call_cases": count,
        "setup_case_records": count,
        "partial_JSON_lines_ignored": 0,
        "phases": {
            phase: dict(Counter(r["outcome"] for r in records if r["when"] == phase))
            for phase in ("call", "setup", "teardown")
        },
        "nodes_by_outcome": {
            phase: {
                outcome: sorted(
                    r["nodeid"] for r in records if r["when"] == phase and r["outcome"] == outcome
                )
                for outcome in ("failed", "passed", "skipped")
            }
            for phase in ("call", "setup", "teardown")
        },
    }
    cases = []
    for index in range(count):
        children = ("<failure message='call'/>" if index < failed else "") + (
            "<error message='cleanup'/>" if index < teardown else ""
        )
        cases.append(
            "<testcase classname='test.check' name="
            + quoteattr("case_" + str(index))
            + " time='0.3'>"
            + children
            + "</testcase>"
        )
    suite = {
        "tests": str(count),
        "failures": str(failed),
        "errors": str(teardown),
        "skipped": "0",
        "time": "1.0",
    }
    xml = (
        "<testsuites><testsuite "
        + " ".join(k + "=" + quoteattr(v) for k, v in suite.items())
        + ">"
        + "".join(cases)
        + "</testsuite></testsuites>"
    ).encode()
    return records, counts, xml, suite


class Fixture:
    def __init__(self, root):
        self.root, self.base = root, root / "inputs"
        self.base.mkdir()
        self.ledger = {
            "schema": "finite-proof-query-attempt-cost-ledger@3",
            "host_attempts": [],
            "Docker_attempts": [],
            "isolated_stream_attempts": [],
            "retained_metadata_audit_attempts": [],
            "non_native_preparation_records": [],
            "preentry_invocation_failures": [],
            "progress_observer_failures": [],
            "total_elapsed_wall_time": None,
            "all_native_process_launch_count": None,
            "explicit_unexecuted_generation06": {"status": "prepared_not_launched"},
        }
        for index, name in enumerate(m.HOSTS):
            count, failed, teardown = (
                (37, 10, 1)
                if name.endswith("11")
                else (23, 1, 0)
                if name.endswith("12")
                else (1, 0, 0)
                if name.endswith("13")
                else (0, 0, 0)
                if index < 2
                else (1, 1, 0)
            )
            records, counts, xml, suite = phase_fixture(count, failed, teardown)
            generation = "sha256:" + sha256(name.encode()).hexdigest() if index >= 2 else None
            status, code = ("passed", 0) if name.endswith("13") else ("failed_or_partial", 1)
            folder = self.base / name
            raw_pins = [
                write_doc(folder / "invocation.json", {"generation_cid": generation}),
                write_doc(
                    folder / "review.json",
                    {
                        "elapsed_seconds": float(index + 1),
                        "pytest_exit_code": code,
                        "qualification": status,
                        "generation_cid": generation,
                    },
                ),
            ]
            phase_path, xml_path = folder / "reports.jsonl", folder / "tests.xml"
            if index >= 2:
                phase_path.write_bytes(
                    b"".join(json.dumps(row).encode() + b"\n" for row in records)
                )
                xml_path.write_bytes(xml)
                raw_pins.extend([pin(phase_path), pin(xml_path)])
            else:
                raw_pins.append({"path": str(phase_path), "present": False})
                if index == 1:
                    xml_path.write_bytes(
                        b"<testsuites><testsuite tests='1' failures='0' errors='1' skipped='0' time='1.0'><testcase name='collection' time='0'><error message='collection'/></testcase></testsuite></testsuites>"
                    )
                    raw_pins.append(pin(xml_path))
                    suite = {
                        "tests": "1",
                        "failures": "0",
                        "errors": "1",
                        "skipped": "0",
                        "time": "1.0",
                    }
                else:
                    raw_pins.append({"path": str(xml_path), "present": False})
            row = {
                "attempt": name,
                "counts": counts,
                "elapsed_seconds": float(index + 1),
                "pytest_exit_code": code,
                "generation_cid": generation,
                "status": status,
                "raw_file_pins": raw_pins,
            }
            if index:
                row["XML_suite_counts"] = [suite]
            self.ledger["host_attempts"].append(row)
        for index, name in enumerate(m.DOCKERS):
            case = (
                "child-late-proof"
                if "child-proof" in name
                else "child-late-epoch"
                if "child-epoch" in name
                else "positive"
            )
            status, code = ("unqualified", 1) if index < 5 else ("completed", 0)
            p = write_doc(
                self.base / name / "container-execution-final.json",
                {
                    "returncode": code,
                    "qualification_status": status,
                    "fixture_case": case,
                    "elapsed_seconds": float(index + 1),
                },
            )
            self.ledger["Docker_attempts"].append(
                {
                    "attempt": name,
                    "raw_file_pins": [p],
                    "returncode": code,
                    "status": status,
                    "fixture_case": case,
                    "elapsed_seconds": float(index + 1),
                }
            )
        for index, name in enumerate(m.STREAMS):
            records, counts, xml, _ = phase_fixture(20, 15 if index == 0 else 0)
            folder = self.base / name
            raw_pins = [
                write_doc(
                    folder / "review.json",
                    {"elapsed_seconds": 1.0 + index, "pytest_exit_code": 1 - index},
                )
            ]
            (folder / "reports.jsonl").write_bytes(
                b"".join(json.dumps(r).encode() + b"\n" for r in records)
            )
            (folder / "tests.xml").write_bytes(xml)
            raw_pins += [
                pin(folder / "reports.jsonl"),
                pin(folder / "tests.xml"),
                write_doc(
                    folder / "launcher-result.json",
                    {"returncode": 1 - index, "elapsed_seconds": 1.5 + index},
                ),
            ]
            self.ledger["isolated_stream_attempts"].append(
                {
                    "attempt": name,
                    "raw_file_pins": raw_pins,
                    "counts": counts,
                    "elapsed_seconds": 1.0 + index,
                    "pytest_exit_code": 1 - index,
                    "test_qualification": bool(index),
                }
            )
        generation = "sha256:" + "a" * 64
        manifest_sha = "b" * 64
        cases = []
        selected_cases = []
        for name, case, native, settlement in zip(
            m.DOCKERS[-3:],
            ("positive", "child-late-proof", "child-late-epoch"),
            ("completed", "in_progress", "in_progress"),
            ("completed-with-native-publication", "unknown-retained", "unknown-retained"),
            strict=True,
        ):
            driver = next(row for row in self.ledger["Docker_attempts"] if row["attempt"] == name)
            source_pin = {k: driver["raw_file_pins"][0][k] for k in ("path", "sha256", "bytes")}
            cases.append(
                {
                    "case": case,
                    "native_task_status": native,
                    "native_settlement": settlement,
                    "container_final_pin": source_pin,
                    "driver_elapsed_seconds": driver["elapsed_seconds"],
                }
            )
            selected_cases.append(
                {"attempt": name, "driver": source_pin, "driver_seconds": driver["elapsed_seconds"]}
            )
        summary = {
            "schema": "finite-native-generation12-matched-three-case-independent-readback-summary@1",
            "status": "passed",
            "cases": cases,
            "UNKNOWN_proves_no_external_effects": False,
            "independent_live_attempt_lease_checked": False,
            "separate_generation11_positive06_qualification_transferred": False,
            "test_only_generation13_runtime_transfer_claimed": False,
            "immutable_runtime_generation_cid": generation,
            "generation_manifest_sha256": manifest_sha,
            "native_runtime_profile_generation": "12",
        }
        for index in range(23):
            name = (
                "joint-summary-02.json"
                if index == 21
                else "joint-summary-03.json"
                if index == 22
                else "audit-" + str(index) + ".json"
            )
            doc = (
                copy.deepcopy(summary)
                if index >= 21
                else {
                    "schema": "authored-inert-audit@1",
                    "status": "failed" if index == 0 else "passed",
                    "errors": ["diagnostic"] if index == 0 else [],
                }
            )
            if index == 21:
                doc["cases"] = []
            row = {
                "pin": write_doc(self.base / "metadata" / name, doc),
                "recorded_schema": doc["schema"],
                "recorded_status": doc["status"],
                "recorded_error_count": len(doc.get("errors", [])),
                "recorded_summary_case_count": len(doc["cases"]) if "cases" in doc else None,
            }
            if index >= 21:
                row["derived_qualification"] = (
                    "failed_empty_three_case_population"
                    if index == 21
                    else "passed_exact_three_case_population"
                )
            self.ledger["retained_metadata_audit_attempts"].append(row)
        for index in range(21):
            p = write_doc(
                self.base / "preparations" / (str(index) + ".json"),
                {"schema": "authored-preparation@1", "status": "prepared_not_launched"},
            )
            self.ledger["non_native_preparation_records"].append(
                {
                    "pin": p,
                    "recorded_preparation_status": "prepared_not_launched",
                    "executed_native_test_cases": 0,
                    "native_solver_training_worker_jobs": 0,
                }
            )
        preentry = {
            "schema": "finite-worker-driver-invocation-failure@1",
            "status": "failed_before_driver_entry",
            "exception": "ImportError: authored",
            "failure_stage": "before entry",
            "driver_generation": "11",
            "intended_output_root_exists": False,
            "retained_failures_rewritten": False,
            "native_container_created": False,
            "native_fixture_entry": False,
            "all_os_launch_count": None,
            "stdout": str(self.base / "not-selected.stdout"),
            "stdout_sha256": "a" * 64,
            "stdout_bytes": 10,
        }
        self.ledger["preentry_invocation_failures"] = [
            {
                "metadata_pin": write_doc(self.base / "preentry.json", preentry),
                "status": preentry["status"],
                "exception": preentry["exception"],
                "failure_stage": preentry["failure_stage"],
                "driver_generation": "11",
                "output_root_existed_at_failed_invocation": False,
                "failure_rewritten": False,
                "native_container_created": False,
                "native_fixture_entry": False,
                "all_OS_process_launch_count": None,
                "recorded_fixture_solver_training_worker_jobs": 0,
                "elapsed_seconds": None,
                "stdout_pin": {
                    "path": preentry["stdout"],
                    "sha256": preentry["stdout_sha256"],
                    "bytes": 10,
                    "present": True,
                },
            }
        ]
        observer = {
            "schema": "finite-worker-progress-observer-failure@1",
            "status": "no_selected_live_container",
            "exception": "AssertionError: []",
            "failure_boundary": "before exec",
            "all_os_launch_count": None,
            "coding_worker_launched_by_observer": False,
            "in_container_progress_process_launched": False,
            "native_fixture_requalified_by_observer": False,
            "proof_or_training_job_launched_by_observer": False,
            "raw_engine_output_retained": False,
            "read_only_engine_queries": True,
            "selection": [],
            "elapsed_seconds": None,
            "subsequent_actual_driver_result": "docker-positive-06/container-execution-final.json",
            "subsequent_result_container_removed": True,
            "subsequent_result_returncode": 0,
        }
        self.ledger["progress_observer_failures"] = [
            {
                **{
                    key: value
                    for key, value in observer.items()
                    if key not in ("schema", "selection")
                },
                "metadata_pin": write_doc(self.base / "observer.json", observer),
            }
        ]
        for key, group in (
            ("finished_host_driver_seconds_sum", "host_attempts"),
            ("finished_Docker_driver_seconds_sum", "Docker_attempts"),
            ("finished_stream_driver_seconds_sum", "isolated_stream_attempts"),
        ):
            self.ledger[key] = sum(row["elapsed_seconds"] for row in self.ledger[group])
        self.ledger_path, self.machine_path, self.supplement_path = (
            self.base / n for n in ("ledger.json", "machine.json", "supplement.json")
        )
        self.machine = {
            "schema": "repository-proof-index-codebase-ir-finite-proof-query-dispatch-review@1",
            "all_32_RPI_production_exits_open": True,
            "global_optimizer_convergence_proved": False,
            "whole_current_live_runtime_qualified": False,
            "broad_host_training_census": None,
            "complete_OS_launch_count": None,
            "generation": {"generation_cid": generation, "manifest": {"sha256": manifest_sha}},
            "selected_native_cases": selected_cases,
        }
        self.supplement = {
            "schema": "finite-dispatch-postledger-finalization-cost-supplement@1",
            "whole_current_live_runtime_qualified": False,
            "postledger_attempts": [{"elapsed_seconds": None}, {"elapsed_seconds": None}],
        }
        self.spec_path = self.root / "spec" / "manifest.json"
        self.refresh()

    def refresh(self):
        ledger_pin = write_doc(self.ledger_path, self.ledger)
        self.supplement["original_final_cost_ledger_pin"] = {
            k: ledger_pin[k] for k in ("path", "sha256", "bytes")
        }
        supplement_pin = write_doc(self.supplement_path, self.supplement)
        self.machine["attempt_cost_ledger"] = {
            k: ledger_pin[k] for k in ("path", "sha256", "bytes")
        }
        self.machine["post_ledger_finalization_cost_supplement"] = {
            k: supplement_pin[k] for k in ("path", "sha256", "bytes")
        }
        machine_pin = write_doc(self.machine_path, self.machine)
        self.spec = {"schema": m.INPUT_SCHEMA, "selected_profile": m.PROFILE}
        for role, p in zip(m.ROLES, (machine_pin, ledger_pin, supplement_pin), strict=True):
            self.spec[role] = {"path": p["path"], "sha256": p["sha256"], "size_bytes": p["bytes"]}
        write_doc(self.spec_path, self.spec)
        self.anchors = {role: self.spec[role]["sha256"] for role in m.ROLES}

    def repair_child(self, path):
        replacement = pin(path)

        def visit(value):
            if isinstance(value, dict):
                if value.get("path") == str(path) and "present" in value:
                    value.update(replacement)
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(self.ledger)
        self.refresh()

    def audit(self, name="output", **kwargs):
        with mock.patch.dict(m.PUBLIC_ANCHORS, self.anchors, clear=True):
            return m.audit(self.spec_path, self.root / name, **kwargs)


class DispatchCustodyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fixture = Fixture(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_complete_population_adverse_unknown_null_and_two_clock_scopes(self):
        report = self.fixture.audit()
        self.assertEqual((report["selected_file_count"], len(report["retained_files"])), (107, 108))
        self.assertEqual(
            m.population(
                self.root / "output",
                {r["relative_path"] for r in report["retained_files"]}
                | {"selected_custody.json", "dispatch_attempt_custody.json"},
            ),
            {"file_count": 110, "directory_count": 1},
        )
        self.assertEqual(
            report["metadata_audits"][-2]["receiving_disposition"],
            "failed_empty_three_case_population",
        )
        self.assertEqual(
            report["matched_generation12_recorded_outcomes"][1]["native_settlement"],
            "unknown-retained",
        )
        self.assertIsNone(report["null_cost_frontiers"]["total_elapsed_wall_time"])
        self.assertNotEqual(
            report["stream_attempts"][0]["driver_seconds"],
            report["stream_attempts"][0]["outer_launcher_seconds"],
        )
        self.assertTrue(all(report[k] is False for k in m.FALSE_FLAGS))

    def test_real_selection_anchor_is_required(self):
        with self.assertRaisesRegex(ValueError, "pinned public selection"):
            m.audit(self.fixture.spec_path, self.root / "output")

    def test_changed_child_fails_even_when_copy_size_is_equal(self):
        p = Path(self.fixture.ledger["host_attempts"][-1]["raw_file_pins"][1]["path"])
        p.write_bytes(p.read_bytes().replace(b"passed", b"failed"))
        with self.assertRaisesRegex(ValueError, "raw pin"):
            self.fixture.audit()

    def test_coherently_repinned_phase_count_alias_is_refused(self):
        self.fixture.ledger["host_attempts"][-1]["counts"]["actual_call_cases"] = True
        self.fixture.refresh()
        with self.assertRaisesRegex(ValueError, "typed phase population"):
            self.fixture.audit()

    def test_duplicate_phase_and_malformed_complete_line_are_refused(self):
        row = self.fixture.ledger["host_attempts"][-1]
        p = Path(
            next(
                pin["path"] for pin in row["raw_file_pins"] if pin["path"].endswith("reports.jsonl")
            )
        )
        raw = p.read_bytes()
        for bad in (raw + raw.splitlines()[0] + b"\n", raw + b"{broken}\n"):
            with self.subTest(bad=bad[-16:]):
                p.write_bytes(bad)
                self.fixture.repair_child(p)
                with self.assertRaises(ValueError):
                    self.fixture.audit()

    def test_missing_or_repeated_attempt_and_auxiliary_membership_are_refused(self):
        for group in (
            "host_attempts",
            "Docker_attempts",
            "retained_metadata_audit_attempts",
            "non_native_preparation_records",
        ):
            with self.subTest(group=group):
                saved = copy.deepcopy(self.fixture.ledger[group])
                self.fixture.ledger[group][-1] = copy.deepcopy(self.fixture.ledger[group][0])
                self.fixture.refresh()
                with self.assertRaises(ValueError):
                    self.fixture.audit()
                self.fixture.ledger[group] = saved
                self.fixture.refresh()

    def test_host_failure_and_teardown_error_cannot_be_promoted(self):
        p = Path(self.fixture.ledger["host_attempts"][-3]["raw_file_pins"][1]["path"])
        value = json.loads(p.read_bytes())
        value["pytest_exit_code"] = 0
        value["qualification"] = "passed"
        write_doc(p, value)
        self.fixture.repair_child(p)
        self.fixture.ledger["host_attempts"][-3]["pytest_exit_code"] = 0
        self.fixture.ledger["host_attempts"][-3]["status"] = "passed"
        self.fixture.refresh()
        with self.assertRaisesRegex(ValueError, "whole host failure"):
            self.fixture.audit()

    def test_XML_wrong_total_entities_depth_and_population_are_refused(self):
        row = self.fixture.ledger["host_attempts"][-1]
        p = Path(
            next(pin["path"] for pin in row["raw_file_pins"] if pin["path"].endswith("tests.xml"))
        )
        original = p.read_bytes()
        variants = (
            original.replace(b'tests="1"', b'tests="2"'),
            b"<!DOCTYPE a>" + original,
            b"<testsuites>" + b"<a>" * 9 + b"</a>" * 9 + b"</testsuites>",
        )
        for raw in variants:
            with self.subTest(raw=raw[:30]):
                p.write_bytes(raw)
                self.fixture.repair_child(p)
                with self.assertRaises(ValueError):
                    self.fixture.audit()

    def test_summary_empty_pass_unknown_and_generation_transfers_cannot_be_upgraded(self):
        row = self.fixture.ledger["retained_metadata_audit_attempts"][-1]
        p = Path(row["pin"]["path"])
        original = json.loads(p.read_bytes())
        for field in (
            "UNKNOWN_proves_no_external_effects",
            "independent_live_attempt_lease_checked",
            "test_only_generation13_runtime_transfer_claimed",
        ):
            value = copy.deepcopy(original)
            value[field] = True
            write_doc(p, value)
            self.fixture.repair_child(p)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "scope promoted"):
                self.fixture.audit()

    def test_correlated_driver_summary_wrong_commitment_is_refused(self):
        p = Path(self.fixture.ledger["retained_metadata_audit_attempts"][-1]["pin"]["path"])
        value = json.loads(p.read_bytes())
        value["cases"][0]["container_final_pin"]["sha256"] = "0" * 64
        write_doc(p, value)
        self.fixture.repair_child(p)
        with self.assertRaisesRegex(ValueError, "driver binding"):
            self.fixture.audit()

    def test_cost_sum_null_and_boolean_census_refusals(self):
        for key, bad in (
            ("finished_host_driver_seconds_sum", 0),
            ("total_elapsed_wall_time", 0),
            ("all_native_process_launch_count", False),
        ):
            original = self.fixture.ledger[key]
            self.fixture.ledger[key] = bad
            self.fixture.refresh()
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.fixture.audit()
            self.fixture.ledger[key] = original
            self.fixture.refresh()

    def test_preparation_cannot_be_counted_as_launched(self):
        self.fixture.ledger["non_native_preparation_records"][0]["executed_native_test_cases"] = 1
        self.fixture.refresh()
        with self.assertRaisesRegex(ValueError, "executed work"):
            self.fixture.audit()

    def test_coherently_repinned_auxiliary_failure_cannot_claim_entry_or_worker(self):
        for group, field in (
            ("preentry_invocation_failures", "native_fixture_entry"),
            ("progress_observer_failures", "coding_worker_launched_by_observer"),
        ):
            with self.subTest(group=group):
                declared = self.fixture.ledger[group][0]
                path = Path(declared["metadata_pin"]["path"])
                raw = m.document(path.read_bytes())
                raw[field] = True
                declared[field] = True
                write_doc(path, raw)
                self.fixture.repair_child(path)
                with self.assertRaisesRegex(ValueError, "promoted"):
                    self.fixture.audit()
                raw[field] = False
                declared[field] = False
                write_doc(path, raw)
                self.fixture.repair_child(path)

    def test_targeted_retry_cannot_rebind_to_failed_whole_generation(self):
        row = self.fixture.ledger["host_attempts"][-1]
        generation = self.fixture.ledger["host_attempts"][-2]["generation_cid"]
        for filename in ("invocation.json", "review.json"):
            path = Path(
                next(p["path"] for p in row["raw_file_pins"] if Path(p["path"]).name == filename)
            )
            raw = m.document(path.read_bytes())
            raw["generation_cid"] = generation
            write_doc(path, raw)
            self.fixture.repair_child(path)
        row["generation_cid"] = generation
        self.fixture.refresh()
        with self.assertRaisesRegex(ValueError, "separate whole"):
            self.fixture.audit()

    def test_json_duplicate_nonfinite_and_descriptor_count_bounds(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":999999999999999999999999}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                m.document(raw)
        self.fixture.spec["machine_review"]["size_bytes"] = m.MAX_FILE + 1
        write_doc(self.fixture.spec_path, self.fixture.spec)
        with self.assertRaisesRegex(ValueError, "preallocation"):
            self.fixture.audit()

    def test_safe_output_existing_inside_inputs_and_symlink_refusals(self):
        (self.root / "output").mkdir()
        with self.assertRaisesRegex(ValueError, "fresh output"):
            self.fixture.audit()
        with self.assertRaisesRegex(ValueError, "fresh output"):
            self.fixture.audit("inputs/new")
        (self.root / "alias").symlink_to(self.root / "output", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "fresh output"):
            self.fixture.audit("alias")

    def _main_write_control(self, mutate):
        original_open = Path.open
        hit = []

        class Wrapped:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                return self.stream.__enter__()

            def __exit__(self, *args):
                result = self.stream.__exit__(*args)
                hit.append(True)
                mutate()
                return result

        def opening(path, *args, **kwargs):
            stream = original_open(path, *args, **kwargs)
            return (
                Wrapped(stream)
                if path.name == "dispatch_attempt_custody.json" and args and args[0] == "xb"
                else stream
            )

        with mock.patch.object(Path, "open", opening), self.assertRaises((ValueError, OSError)):
            self.fixture.audit()
        self.assertEqual(hit, [True])

    def test_late_written_main_body_corruption_is_refused(self):
        self._main_write_control(
            lambda: (self.root / "output/dispatch_attempt_custody.json").write_bytes(b"{}\n")
        )

    def test_late_original_and_retained_copy_changes_are_refused(self):
        for kind in ("original", "copy", "nested"):
            with self.subTest(kind=kind):
                output = self.root / "output"
                if output.exists():
                    import shutil

                    shutil.rmtree(output)

                def mutate(kind=kind, output=output):
                    path = (
                        self.fixture.machine_path
                        if kind == "original"
                        else output
                        / ("retained/001.bytes" if kind == "copy" else "selected_custody.json")
                    )
                    path.chmod(0o644)
                    path.write_bytes(path.read_bytes() + b" ")

                original = self.fixture.machine_path.read_bytes()
                self._main_write_control(mutate)
                self.fixture.machine_path.write_bytes(original)

    def test_late_extra_nonregular_and_root_alias_are_refused(self):
        import shutil

        for kind in ("extra", "fifo", "alias"):
            output = self.root / "output"
            if output.is_symlink():
                output.unlink()
            elif output.exists():
                shutil.rmtree(output)

            def mutate(kind=kind, output=output):
                if kind == "extra":
                    (output / "unexpected").write_bytes(b"x")
                elif kind == "fifo":
                    os.mkfifo(output / "unexpected")
                else:
                    output.rename(self.root / "moved")
                    output.symlink_to(self.root / "moved", target_is_directory=True)

            with self.subTest(kind=kind):
                self._main_write_control(mutate)

    def test_false_stability_and_report_allocation_refuse(self):
        with (
            mock.patch.object(m.Capture, "stable", return_value={"unchanged": 1, "files": []}),
            self.assertRaisesRegex(ValueError, "stability"),
        ):
            self.fixture.audit()
        import shutil

        shutil.rmtree(self.root / "output")
        with (
            mock.patch.object(m, "MAX_REPORT", 16),
            self.assertRaisesRegex(ValueError, "report allocation"),
        ):
            self.fixture.audit()

    def test_explicit_relocation_without_original_or_subprocess(self):
        import shutil

        selected, _, _ = m.selected_inputs(self.fixture.ledger, self.fixture.ledger_path)
        selected.update({p["path"]: p for p in self.fixture.spec.values() if isinstance(p, dict)})
        stage = self.root / "stage"
        stage.mkdir()
        remap = {}
        for index, logical in enumerate(sorted(selected)):
            physical = stage / (str(index) + ".bytes")
            shutil.copyfile(logical, physical)
            remap[logical] = str(physical)
        staged_spec = stage / "manifest.json"
        shutil.copyfile(self.fixture.spec_path, staged_spec)
        self.fixture.base.rename(self.root / "removed_inputs")
        with (
            mock.patch.dict(m.PUBLIC_ANCHORS, self.fixture.anchors, clear=True),
            mock.patch("subprocess.run", side_effect=AssertionError("subprocess forbidden")),
        ):
            report = m.audit(staged_spec, self.root / "restored", relocated_sources=remap)
        self.assertTrue(report["explicit_relocated_input_map_used"])
        self.assertEqual(report["selected_file_count"], 107)
        bad = dict(remap)
        bad.pop(next(iter(bad)))
        with (
            mock.patch.dict(m.PUBLIC_ANCHORS, self.fixture.anchors, clear=True),
            self.assertRaises(ValueError),
        ):
            m.audit(staged_spec, self.root / "bad", relocated_sources=bad)


if __name__ == "__main__":
    unittest.main()

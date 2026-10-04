from __future__ import annotations

import copy
import os
import shutil
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import admission_declaration_custody as tool
import evidence_children as children
import portable_evidence_children as capsule
import portable_review as portable
import release_matrix as matrix
import test_evidence_children as fixtures


def fixture_bodies():
    """Synthetic historical declarations; no owner payloads or native execution."""
    qualification = {
        "schema": "repository-behavioral-admission-qualification@1",
        "scope": "explicit finite Python integer-offset, model-off, local independently signed task profile",
        "distinct_tests": 10, "final_passed": 10, "final_skipped": 0,
        "tests": [], "authority": {key: False for key in ("proof", "execution", "completion", "omission")},
        "live_checks": ["Recorded native owners and worker observation"],
        "artifact_integrity_controls": {"count": 6, "fresh_checker_per_control": False, "description": "Recorded reused match; not fresh checking."},
        "diagnostics": {"first": "Recorded permissions refusal", "third_fourth": "Recorded serialization failures",
                        "second_fifth_sixth_joined_eighth": "Recorded resource refusals"},
        "full_daemon_evidence": "../repository-behavioral-supervision-20261002",
        "limitations": ["Recorded declarations have no execution authority"],
    }
    bodies = {"README.md": b"Six re-signed artifact controls; not six fresh checker executions.\n"}
    for index, stem in enumerate(tool.RUNS):
        root = ET.Element("testsuites", {"name": "pytest tests"})
        final, joined = index == 8, index == 6
        names = tool.FINAL_CASES if final else (tool.OWNER_CASE, *(tool.MUTATION_CASE + "[" + x + "]" for x in tool.MUTATIONS[:3])) if joined else (tool.OWNER_CASE,)
        failed, errors = (0, 0) if final else (1, 0) if joined or index == 4 else (0, 1)
        suite = ET.SubElement(root, "testsuite", {"name": "pytest", "tests": str(len(names)), "failures": str(failed),
            "errors": str(errors), "skipped": "0", "time": "1.000", "timestamp": "2026-10-02T00:00:00", "hostname": "inert-fixture"})
        for position, name in enumerate(names):
            case = ET.SubElement(suite, "testcase", {"classname": "integration.test_repository_behavioral_admission", "name": name, "time": "0.100"})
            if not final and position == len(names) - 1:
                ET.SubElement(case, "failure" if failed else "error", {"message": "Recorded LeaseTimeoutError; no owner called"}).text = "Inert traceback fragment, no envelope body"
        bodies[stem + ".xml"] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        outcomes = "10 passed" if final else "1 failed, 3 passed" if joined else "1 failed" if failed else "1 error"
        collected = 21 if joined else 10
        bodies[stem + ".log"] = f"collected {collected} items\n================ {outcomes} in 1.05s ================\n".encode()
        qualification["tests"].append({"log": stem + ".log", "xml": stem + ".xml", "tests": str(len(names)),
            "failures": str(failed), "errors": str(errors), "skipped": "0", "time": "1.000"})
    bodies["qualification.json"] = matrix.json_bytes(qualification)
    bodies["producer-sources.json"] = matrix.json_bytes({"schema": "repository-behavioral-admission-sources@1", "repository": "accelerate",
        "sources": [{"path": path, "sha256": str(index + 1) * 64, "size_bytes": 10 + index} for index, path in enumerate(tool.SOURCE_PATHS)]})
    return bodies


class AdmissionDeclarationCustodyTests(unittest.TestCase):
    def setUp(self):
        self.factory = fixtures.ReleasedEvidenceChildrenTests("runTest")
        self.factory.setUp()
        self.addCleanup(self.factory.doCleanups)
        self.root, self.repo = self.factory.root, self.factory.repo
        self.sequence = 0
        self.bodies = fixture_bodies()
        files = []
        for name, raw in self.bodies.items():
            (self.repo / "docs" / name).write_bytes(raw)
            files.append({"path": name, "sha256": matrix.sha(raw), "size_bytes": len(raw)})
        parent_raw = matrix.json_bytes({"schema": "closed-local-evidence-manifest@1", "files": files})
        (self.repo / "docs/evidence.json").write_bytes(parent_raw)
        self.factory.factory.ledger["evidence"][tool.EVIDENCE_ID] = {"path": "docs/evidence.json", "sha256": matrix.sha(parent_raw), "retention": "repository_evidence"}
        self.factory.factory.commit()
        self.factory.spec = {"schema": children.INPUT_SCHEMA, "repositories": self.factory.factory.spec["repositories"],
            "ledger": self.factory.factory.spec["ledger"], "selected_evidence": [tool.EVIDENCE_ID], "expansion_policy": children.POLICY}
        self.factory.write_spec()
        self.factory.run_audit()
        folder = self.next("prior-input")
        folder.mkdir()
        manifest = folder / "manifest.json"
        manifest.write_bytes(matrix.json_bytes({"schema": capsule.BUILD_INPUT_SCHEMA, "source_manifest": self.pin(self.factory.manifest),
            "source_report": self.pin(self.root / f"result-{self.factory.sequence}/evidence_children.json")}))
        self.prior = self.next("prior")
        capsule.build(manifest, self.prior)
        self.caproot = self.prior / "capsule"
        self.manifest = self.make_input(self.caproot)

    def next(self, label):
        self.sequence += 1
        return self.root / f"{label}-{self.sequence}"

    @staticmethod
    def pin(path):
        return {"path": str(path), "sha256": matrix.sha(path.read_bytes()), "size_bytes": path.stat().st_size}

    def make_input(self, root):
        folder = self.next("input")
        folder.mkdir()
        manifest = folder / "manifest.json"
        manifest.write_bytes(matrix.json_bytes({"schema": tool.INPUT_SCHEMA, "custody_capsule_manifest": self.pin(root / capsule.CAPSULE_FILENAME),
            "evidence_id": tool.EVIDENCE_ID, "selected_profile": tool.PROFILE}))
        return manifest

    def run_audit(self, manifest=None):
        output = self.next("audit")
        return tool.audit(manifest or self.manifest, output), output

    def refuse(self, manifest=None):
        output = self.next("refusal")
        with self.assertRaises((ValueError, OSError, KeyError, TypeError, ET.ParseError)):
            tool.audit(manifest or self.manifest, output)
        self.assertFalse((output / "admission_declaration_custody.json").exists())

    def mutant(self, change):
        root = self.next("mutant")
        shutil.copytree(self.caproot, root)
        for path in [root, *root.rglob("*")]:
            path.chmod(0o755 if path.is_dir() else 0o644)
        header_path = root / capsule.CAPSULE_FILENAME
        header = matrix.document(header_path.read_bytes())

        def replace(path, raw):
            (root / path).write_bytes(raw)
            pin = portable.pin(path, raw)
            for key in ("files", "retained_views", "objects", "implementation"):
                for row in header[key]:
                    if row["path"] == path:
                        row.update(pin)
            for key in ("source_manifest", "source_report"):
                if header[key]["path"] == path:
                    header[key].update(pin)

        change(root, header, replace)
        header_path.write_bytes(matrix.json_bytes(header))
        for path in [*root.rglob("*"), root]:
            path.chmod(0o555 if path.is_dir() else 0o444)
        return self.make_input(root)

    def mutate_document(self, name, change):
        bodies = copy.deepcopy(self.bodies)
        value = matrix.document(bodies[name])
        change(value)
        bodies[name] = matrix.json_bytes(value)
        return bodies

    def test_recorded_history_and_missing_envelopes_are_not_signed_custody(self):
        report, output = self.run_audit()
        self.assertEqual((report["recorded_run_count"], report["adverse_recorded_run_count"], report["final_recorded_test_count"], report["resigned_control_count"]), (9, 8, 10, 6))
        self.assertEqual((report["recorded_case_membership_count"], report["collected_cases_without_retained_outcome"]), (21, 80))
        self.assertTrue(all(report[flag] is False for flag in tool.FALSE_FLAGS))
        self.assertTrue(all(row["body_retained"] is False and row["binding_complete"] is False for row in report["envelope_frontiers"]))
        self.assertFalse(report["fresh_checker_per_control"])
        self.assertEqual(report["artifact_membership_count"], 21)
        self.assertTrue((output / "selected_custody.json").is_file())

    def test_prior_capsule_population_bytes_and_modes_stay_unchanged(self):
        before = {path.relative_to(self.caproot).as_posix(): (matrix.sha(path.read_bytes()), stat_mode(path)) for path in self.caproot.rglob("*") if path.is_file()}
        self.run_audit()
        after = {path.relative_to(self.caproot).as_posix(): (matrix.sha(path.read_bytes()), stat_mode(path)) for path in self.caproot.rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_selected_relocation_needs_no_original_repository_git_or_process(self):
        report, output = self.run_audit()
        relocated = self.next("relocated")
        relocated.mkdir()
        header = relocated / capsule.CAPSULE_FILENAME
        shutil.copyfile(self.caproot / capsule.CAPSULE_FILENAME, header)
        for pin in report["retained_files"]:
            if pin["path"].startswith("retained/custody/"):
                relative = pin["path"].removeprefix("retained/custody/")
                target = relocated / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(output / pin["path"], target)
        header_value = matrix.document(header.read_bytes())
        for repo in header_value["repositories"]:
            (relocated / "repository_roots" / repo["name"]).mkdir(parents=True)
        for path in [*relocated.rglob("*"), relocated]:
            path.chmod(0o555 if path.is_dir() else 0o444)
        manifest = self.make_input(relocated)
        shutil.rmtree(self.repo)
        with patch.object(subprocess, "run", side_effect=AssertionError("process forbidden")), patch.object(matrix.shutil, "which", side_effect=AssertionError("Git lookup forbidden")), patch.dict(os.environ, {"PATH": ""}):
            restored, _ = self.run_audit(manifest)
        for key in ("run_history", "final_controls", "envelope_frontiers", "producer_source_claims", "lifecycle_scope", "artifact_memberships"):
            self.assertEqual(restored[key], report[key])

    def test_qualification_counts_authority_and_checker_aliases_refused(self):
        for change in (lambda x: x.__setitem__("distinct_tests", True), lambda x: x["authority"].__setitem__("omission", 0),
                       lambda x: x["authority"].__setitem__("proof", True), lambda x: x["artifact_integrity_controls"].__setitem__("count", True),
                       lambda x: x["artifact_integrity_controls"].__setitem__("fresh_checker_per_control", 0),
                       lambda x: x["artifact_integrity_controls"].__setitem__("fresh_checker_per_control", True)):
            with self.subTest(change=change), self.assertRaises(ValueError):
                tool.reconcile(self.mutate_document("qualification.json", change))

    def test_ordered_run_declarations_and_scope_pointer_refused(self):
        for change in (lambda x: x["tests"].reverse(), lambda x: x["tests"].pop(), lambda x: x["tests"][0].__setitem__("tests", "10"),
                       lambda x: x.__setitem__("full_daemon_evidence", "/owner/live"), lambda x: x.__setitem__("scope", "generic signed production")):
            with self.subTest(change=change), self.assertRaises(ValueError):
                tool.reconcile(self.mutate_document("qualification.json", change))

    def test_final_case_population_missing_duplicate_or_relabelled_refused(self):
        original = tool.RUNS[-1] + ".xml"
        for mode in ("missing", "duplicate", "renamed"):
            bodies = copy.deepcopy(self.bodies)
            tree = ET.fromstring(bodies[original])
            suite = tree[0]
            if mode == "missing":
                suite.remove(suite[-1])
            else:
                suite[-1].set("name", suite[0].attrib["name"] if mode == "duplicate" else "test_unknown_control")
            bodies[original] = ET.tostring(tree, encoding="utf-8", xml_declaration=True)
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                tool.reconcile(bodies)

    def test_xml_result_totals_cannot_disagree_with_case_outcomes(self):
        tree = ET.fromstring(self.bodies[tool.RUNS[-1] + ".xml"])
        tree[0].set("errors", "1")
        with self.assertRaises(ValueError):
            tool.xml_run(ET.tostring(tree, encoding="utf-8", xml_declaration=True))

    def test_xml_utf16_entities_depth_count_and_unexpected_roles_refused(self):
        valid = self.bodies[tool.RUNS[-1] + ".xml"]
        malformed = (valid.decode().encode("utf-16"), valid.replace(b"?>", b"?><!DOCTYPE x [<!ENTITY e 'boom'>]>", 1),
                     b"<?xml version='1.0' encoding='utf-8'?>" + b"<x>" * 9 + b"</x>" * 9,
                     valid.replace(b"<testcase", b"<payload", 1))
        for raw in malformed:
            with self.subTest(raw=raw[:50]), self.assertRaises((ValueError, UnicodeError, ET.ParseError)):
                tool.xml_run(raw)
        with patch.object(tool, "MAX_XML_NODES", 2), self.assertRaises(ValueError):
            tool.xml_run(valid)

    def test_log_and_xml_partial_population_is_explicit_not_task_omission(self):
        result = tool.reconcile(self.bodies)
        self.assertEqual(result["run_history"][0]["recorded_collected_case_count"], 10)
        self.assertEqual(result["run_history"][0]["tests"], 1)
        self.assertEqual(result["run_history"][6]["collected_cases_without_retained_outcome"], 17)
        bad = copy.deepcopy(self.bodies)
        bad[tool.RUNS[0] + ".log"] = bad[tool.RUNS[0] + ".log"].replace(b"collected 10", b"collected 9")
        with self.assertRaises(ValueError):
            tool.reconcile(bad)

    def test_log_duplicate_terminal_control_and_result_forgery_refused(self):
        original = self.bodies[tool.RUNS[0] + ".log"]
        for raw in (original + original, original.replace(b"1 error", b"1 passed"), original + b"\x1b]0;bad\x07"):
            with self.subTest(raw=raw[:50]), self.assertRaises(ValueError):
                tool.log_summary(raw, tool.xml_run(self.bodies[tool.RUNS[0] + ".xml"]))

    def test_adverse_attempt_cannot_be_coherently_promoted(self):
        bodies = copy.deepcopy(self.bodies)
        stem = tool.RUNS[0]
        tree = ET.fromstring(bodies[stem + ".xml"])
        tree[0].set("errors", "0")
        tree[0][0].remove(tree[0][0][0])
        bodies[stem + ".xml"] = ET.tostring(tree, encoding="utf-8", xml_declaration=True)
        bodies[stem + ".log"] = bodies[stem + ".log"].replace(b"1 error", b"1 passed")
        q = matrix.document(bodies["qualification.json"])
        q["tests"][0]["errors"] = "0"
        bodies["qualification.json"] = matrix.json_bytes(q)
        with self.assertRaisesRegex(ValueError, "adverse"):
            tool.reconcile(bodies)

    def test_source_claim_paths_sizes_and_injected_envelope_refused(self):
        for change in (lambda x: x["sources"][0].__setitem__("path", "../owner"), lambda x: x["sources"][0].__setitem__("size_bytes", True),
                       lambda x: x["sources"][0].__setitem__("sha256", "bad"), lambda x: x["sources"].append(copy.deepcopy(x["sources"][0]))):
            with self.subTest(change=change), self.assertRaises(ValueError):
                tool.reconcile(self.mutate_document("producer-sources.json", change))
        bodies = {**self.bodies, "signed-admission.json": b"{}"}
        with self.assertRaises(ValueError):
            tool.reconcile(bodies)

    def test_json_duplicates_nonfinite_closed_spec_and_path_controls_refused(self):
        original = self.manifest.read_bytes()
        for raw in (b'{"schema":"x","schema":"y"}', b'{"x":NaN}', original.replace(tool.PROFILE.encode(), b"different-profile")):
            with self.subTest(raw=raw[:40]), self.assertRaises(ValueError):
                tool.spec(raw)
        value = matrix.document(original)
        value["custody_capsule_manifest"]["size_bytes"] = False
        with self.assertRaises(ValueError):
            tool.spec(matrix.json_bytes(value))

    def test_repaired_retained_body_pins_do_not_replace_committed_child(self):
        def change(root, header, replace):
            row = next(row for row in header["retained_views"] if row["relative_path"].endswith("/qualification.json"))
            value = matrix.document((root / row["path"]).read_bytes())
            value["authority"]["proof"] = True
            replace(row["path"], matrix.json_bytes(value))
        self.refuse(self.mutant(change))

    def test_independently_framed_git_object_corruption_refused(self):
        def change(root, header, replace):
            row = next(row for row in header["objects"] if row["kind"] == "commit")
            raw = (root / row["path"]).read_bytes()
            replace(row["path"], raw + b"forged\n")
        self.refuse(self.mutant(change))

    def test_coherent_child_parent_ledger_input_report_repins_fail_immutable_roots(self):
        def change(root, header, replace):
            view = next(row for row in header["retained_views"] if row["relative_path"].endswith("/qualification.json"))
            qualification = matrix.document((root / view["path"]).read_bytes())
            qualification["authority"]["proof"] = True
            forged = matrix.json_bytes(qualification)
            replace(view["path"], forged)
            parent_view = next(row for row in header["retained_views"] if row["relative_path"] == "manifests/" + tool.EVIDENCE_ID + ".json")
            parent = matrix.document((root / parent_view["path"]).read_bytes())
            declaration = next(row for row in parent["files"] if row["path"] == "qualification.json")
            declaration.update(sha256=matrix.sha(forged), size_bytes=len(forged))
            parent_raw = matrix.json_bytes(parent)
            replace(parent_view["path"], parent_raw)
            ledger_view = next(row for row in header["retained_views"] if row["relative_path"] == "inputs/ledger.json")
            ledger = matrix.document((root / ledger_view["path"]).read_bytes())
            ledger["evidence"][tool.EVIDENCE_ID]["sha256"] = matrix.sha(parent_raw)
            ledger_raw = matrix.json_bytes(ledger)
            replace(ledger_view["path"], ledger_raw)
            source = matrix.document((root / header["source_manifest"]["path"]).read_bytes())
            source["ledger"]["sha256"] = matrix.sha(ledger_raw)
            source_raw = matrix.json_bytes(source)
            replace(header["source_manifest"]["path"], source_raw)
            prior = matrix.document((root / header["source_report"]["path"]).read_bytes())
            prior.update(manifest_sha256=matrix.sha(source_raw), ledger_sha256=matrix.sha(ledger_raw))
            parent_row = prior["manifests"][0]
            parent_row.update(sha256=matrix.sha(parent_raw), expected_sha256=matrix.sha(parent_raw), size_bytes=len(parent_raw))
            child = next(row for row in parent_row["children"] if row["declared_relative_path"] == "qualification.json")
            child.update(sha256=matrix.sha(forged), expected_sha256=matrix.sha(forged), size_bytes=len(forged), expected_size_bytes=len(forged))
            replace(header["source_report"]["path"], matrix.json_bytes(prior))
        manifest = self.mutant(change)
        output = self.next("coherent-refusal")
        with self.assertRaisesRegex(ValueError, "immutable ledger/parent proof"):
            tool.audit(manifest, output)
        self.assertFalse((output / "admission_declaration_custody.json").exists())

    def test_missing_selected_commit_and_child_membership_refused(self):
        def missing_object(root, header, replace):
            header["objects"] = [row for row in header["objects"] if row["kind"] != "commit"]
        self.refuse(self.mutant(missing_object))
        def missing_membership(root, header, replace):
            row = header["source_report"]
            prior = matrix.document((root / row["path"]).read_bytes())
            prior["manifests"][0]["children"].pop()
            replace(row["path"], matrix.json_bytes(prior))
        self.refuse(self.mutant(missing_membership))

    def test_preallocation_read_file_byte_and_input_caps_refused(self):
        for setting, value in (("MAX_READ_FILES", 1), ("MAX_READ_BYTES", 32), ("MAX_SELECTED_OBJECTS", 1)):
            with self.subTest(setting=setting), patch.object(tool.transport, setting, value):
                self.refuse()
        with patch.object(tool, "MAX_INPUT_BYTES", 8):
            self.refuse()

    def test_output_scopes_existing_directory_and_symlink_refused(self):
        for output in (self.manifest.parent / "bad", self.caproot / "bad", self.repo / "bad"):
            with self.subTest(output=output), self.assertRaises((ValueError, OSError)):
                tool.audit(self.manifest, output)
        existing = self.next("existing")
        existing.mkdir()
        with self.assertRaises(ValueError):
            tool.audit(self.manifest, existing)
        alias = self.next("alias")
        alias.symlink_to(existing, target_is_directory=True)
        with self.assertRaises(ValueError):
            tool.population(alias, set(), tool.transport.Capture())

    def test_late_original_copied_body_and_nested_receipt_drift_refused(self):
        real = tool.transport.Capture.stability
        for mode in ("original", "copy", "nested"):
            triggered = []
            def stability(capture, mode=mode, triggered=triggered):
                names = list(capture.cache)
                paths = [p for p in names if (p == self.manifest if mode == "original" else p.name == "selected_custody.json" if mode == "nested" else "retained/custody" in str(p) and p.suffix == ".xml")]
                if paths and not triggered:
                    triggered.append(str(paths[0]))
                    raw = paths[0].read_bytes()
                    paths[0].write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
                return real(capture)
            if mode == "original":
                saved = self.manifest.read_bytes()
            with self.subTest(mode=mode), patch.object(tool.transport.Capture, "stability", new=stability):
                self.refuse()
            self.assertTrue(triggered)
            if mode == "original":
                self.manifest.write_bytes(saved)

    def test_final_extra_population_root_alias_and_old_seal_drift_refused(self):
        real = tool.transport.Capture.stability
        for mode in ("extra", "root_alias", "seal"):
            triggered, calls = [], {}
            def stability(capture, mode=mode, triggered=triggered, calls=calls):
                result = real(capture)
                if any(p.name == "selected_custody.json" for p in capture.cache):
                    calls[id(capture)] = calls.get(id(capture), 0) + 1
                    if calls[id(capture)] == 2:
                        out = next(p.parent for p in capture.cache if p.name == "selected_custody.json")
                        triggered.append(mode)
                        if mode == "extra":
                            (out / "late-extra").write_bytes(b"extra")
                        elif mode == "root_alias":
                            displaced = out.with_name(out.name + "-real")
                            out.rename(displaced)
                            out.symlink_to(displaced, target_is_directory=True)
                            self.addCleanup(out.unlink)
                        else:
                            self.caproot.chmod(0o755)
                return result
            with self.subTest(mode=mode), patch.object(tool.transport.Capture, "stability", new=stability):
                self.refuse()
            self.assertEqual(triggered, [mode])
            self.caproot.chmod(0o555)

    def test_false_final_stability_cannot_publish_passed(self):
        real, count = tool.transport.Capture.stability, 0
        def stability(capture):
            nonlocal count
            result = real(capture)
            count += 1
            if count == 4:
                result["unchanged"] = False
            return result
        with patch.object(tool.transport.Capture, "stability", new=stability):
            self.refuse()
        self.assertEqual(count, 4)


def stat_mode(path):
    return path.stat().st_mode & 0o777


if __name__ == "__main__":
    unittest.main()

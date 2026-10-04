from __future__ import annotations

import copy
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import retained_provenance as ledger
from audit import digest, json_bytes


class RetainedProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codebase-ir-retained-ledger-test-")
        self.workspace = Path(self.temp.name).resolve()
        self.repo = self.workspace / "external/producer"
        self.repo.mkdir(parents=True)
        self.fixture = self.workspace / "artifacts/fixture"
        self.fixture.mkdir(parents=True)
        self.before = self.workspace / "artifacts/tests/critical-source-before.json"
        self.after = self.before.with_name("critical-source-after.json")
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.sources = []
        for module in ("pkg.core", "pkg.helper"):
            path = self.repo / (module.replace(".", "/") + ".py")
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = ("SCHEMA='retained-source@1'\n" if module == "pkg.core" else "VALUE=3\n").encode()
            path.write_bytes(raw)
            retained = self.before.parent / "sources" / path.relative_to(self.workspace)
            retained.parent.mkdir(parents=True, exist_ok=True)
            retained.write_bytes(raw)
            self.sources.append({"path": str(path), "retained_source": str(retained),
                                 "sha256": digest(raw), "size_bytes": len(raw)})
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Retained Ledger",
                        "-c", "user.email=fixture@example.invalid", "commit", "-qm", "source"], check=True)
        self.config = {"repositories": [{"name": "test", "root": str(self.repo), "packages": ["pkg"],
                                         "released_ref": "HEAD", "released_checkout": str(self.repo)}]}
        shape = {"schema": "finite-admission-critical-producer-snapshot@1", "scope": "authored selected source",
                 "source_count": 2, "sources": self.sources}
        self.write(self.before, shape)
        self.write(self.after, {**shape, "sources": [{k: v for k, v in row.items() if k != "retained_source"}
                                                    for row in self.sources], "changed_paths": []})
        original = {"path": self.sources[0]["path"], "bytes": self.sources[0]["size_bytes"], "sha256": self.sources[0]["sha256"]}
        retained = self.fixture / "selected-source-snapshot/pkg.core.py"
        retained.parent.mkdir()
        retained.write_bytes(Path(original["path"]).read_bytes())
        self.result = {"schema": "finite-repository-admission-qualification@1", "status": "completed",
                       "execution_sources": [original], "selected_source_copies": [{"module": "pkg.core",
                           "original": original, "retained": {**original, "path": str(retained)}}],
                       "fresh_process_historical_replay": {"verified": True, "current_freshness_claimed": False}}
        self.write(self.fixture / "result.json", self.result)
        declaration = {"binding": {"retained_signature": "authored; not authenticated"}, "payload": {
            "schema": "supervisor-finite-repository-declaration@1", "manifest": {"payload": {"schema": "supervisor-local-benchmark-manifest@1"}},
            "implementation": {"schema": "finite-repository-admission-implementation@1",
                               "source_sha256": {"pkg.core": original["sha256"]}}}}
        self.write(self.fixture / "before-declaration.json", declaration)
        self.write(self.fixture / "successor-declaration.json", declaration)
        initial = self.trial("capacity-initial", [("one", "passed"), ("two", "failure")])
        retry = self.trial("capacity-retry", [("two", "passed")])
        historical = self.trial("historical", [("old-ok", "passed"), ("old-bad", "failure")])
        latest = [initial["cases"][0], retry["cases"][0]]
        self.test_ledger = {"schema": "finite-admission-selected-test-ledger@1", "scope": "separate trials",
                            "recorded_at_utc": "2026-10-02", "native_sampler_injected": False,
                            "pressure_guards_changed": False, "earlier_31_boundary_history": "historical only",
                            "current_boundary": self.trial("boundary", [("current", "passed")]),
                            "current_capacity_initial": initial, "current_capacity_failed_case_retry": retry,
                            "current_capacity_latest": {"cases": latest, "distinct_cases": 2, "errors": 0, "failures": 0, "passed": 2, "skipped": 0},
                            "historical_full_compatibility_run": historical,
                            "historical_legacy_coupling": {"cases": [historical["cases"][0]], "distinct_cases": 1,
                                "passed": 1, "scope": "protected old producer only", "xml": historical["xml"]}}
        self.write(self.fixture / "test-ledger.json", self.test_ledger)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(json_bytes(value))

    def trial(self, name, cases):
        rows = [{"classname": "tests.fixture", "name": name, "seconds": 0.1, "status": status}
                for name, status in cases]
        raw = ("<testsuite>" + "".join(f'<testcase classname="tests.fixture" name="{name}" time="0.1">'
               + ("<failure/>" if status == "failure" else "") + "</testcase>" for name, status in cases)
               + "</testsuite>").encode()
        path = self.fixture / (name + ".xml")
        path.write_bytes(raw)
        return {"cases": rows, "counts": {status: sum(row["status"] == status for row in rows)
                for status in ("error", "failure", "passed", "skipped")}, "suite_attributes": [],
                "xml": {"path": str(path), "sha256": digest(raw), "bytes": len(raw)}}

    def execute(self):
        return ledger.audit_fixture(self.fixture, self.workspace / "output", workspace=self.workspace,
                                    config=self.config, source_before=self.before, source_after=self.after)

    def test_real_source_custody_keeps_failures_retry_and_historical_scope_separate(self):
        report = self.execute()
        self.assertEqual(report["disposition"], "ledger_produced", report.get("error"))
        trials = report["trial_coverage"]["trials"]
        self.assertEqual(trials["current_capacity_initial"]["counts"]["failure"], 1)
        self.assertEqual(trials["historical_full_compatibility_run"]["counts"]["failure"], 1)
        self.assertEqual(trials["capacity_latest_retry_overlay"]["passed"], 2)
        self.assertFalse(trials["capacity_latest_retry_overlay"]["single_clean_run"])
        self.assertFalse(report["signature_verification_performed"])
        self.assertFalse(report["current_freshness_verified"])
        self.assertEqual(report["raw_result_sha256"], digest((self.fixture / "result.json").read_bytes()))

    def test_current_drift_does_not_change_retained_byte_history_or_head_comparison(self):
        Path(self.sources[0]["path"]).write_bytes(b"SCHEMA='current@2'\n")
        report = self.execute()
        self.assertEqual(report["disposition"], "ledger_produced")
        self.assertFalse(report["selected_sources"][0]["current_matches_recorded_before"])
        self.assertEqual(report["source_views"]["working"]["counts"]["different_bytes"], 1)
        self.assertEqual(report["source_views"]["head"]["counts"]["identical"], 2)

    def test_corrupt_or_live_substituted_retained_source_refuses(self):
        for mutation in ("bytes", "live_path"):
            with self.subTest(mutation=mutation):
                if mutation == "bytes":
                    Path(self.sources[0]["retained_source"]).write_bytes(b"foreign retained bytes")
                else:
                    Path(self.sources[0]["retained_source"]).write_bytes(Path(self.sources[0]["path"]).read_bytes())
                    value = copy.deepcopy(ledger.document(self.before.read_bytes()))
                    value["sources"][0]["retained_source"] = value["sources"][0]["path"]
                    self.write(self.before, value)
                report = ledger.audit_fixture(self.fixture, self.workspace / mutation, workspace=self.workspace,
                                              config=self.config, source_before=self.before, source_after=self.after)
                self.assertEqual(report["disposition"], "retained_provenance_refused")

    def test_execution_population_retarget_and_empty_copies_refuse(self):
        for mutation in ("empty", "retarget"):
            result = copy.deepcopy(self.result)
            if mutation == "empty":
                result["selected_source_copies"] = []
                result["execution_sources"] = []
            else:
                result["execution_sources"][0]["sha256"] = "0" * 64
            self.write(self.fixture / "result.json", result)
            report = ledger.audit_fixture(self.fixture, self.workspace / mutation, workspace=self.workspace,
                                          config=self.config, source_before=self.before, source_after=self.after)
            self.assertEqual(report["disposition"], "retained_provenance_refused")

    def test_forged_latest_overlay_duplicate_case_and_signed_producer_refuse(self):
        for mutation in ("overlay", "duplicate", "signed"):
            value = copy.deepcopy(self.test_ledger)
            if mutation == "overlay":
                value["current_capacity_latest"]["passed"] = 99
            elif mutation == "duplicate":
                value["current_boundary"]["cases"].append(copy.deepcopy(value["current_boundary"]["cases"][0]))
            else:
                declaration = ledger.document((self.fixture / "successor-declaration.json").read_bytes())
                declaration["payload"]["implementation"]["source_sha256"]["pkg.core"] = "0" * 64
                self.write(self.fixture / "successor-declaration.json", declaration)
            self.write(self.fixture / "test-ledger.json", value)
            report = ledger.audit_fixture(self.fixture, self.workspace / mutation, workspace=self.workspace,
                                          config=self.config, source_before=self.before, source_after=self.after)
            self.assertEqual(report["disposition"], "retained_provenance_refused")

    def test_reader_exact_caps_fifo_symlink_and_descriptor_drift(self):
        reader = ledger.Reader([self.fixture])
        with patch.object(ledger, "MAX_FILE_BYTES", 1), self.assertRaises(ledger.ProvenanceRefusal):
            reader.read(self.fixture / "result.json")
        fifo = self.fixture / "fifo.json"
        os.mkfifo(fifo)
        with self.assertRaises(ledger.ProvenanceRefusal):
            reader.read(fifo)
        link = self.fixture / "link.json"
        link.symlink_to(self.fixture / "result.json")
        with self.assertRaises(ledger.ProvenanceRefusal):
            reader.read(link)
        reader.read(self.fixture / "result.json")
        (self.fixture / "result.json").write_bytes(b"{}")
        self.assertFalse(reader.stability()["stable"])

    def test_strict_json_duplicate_nonfinite_and_xml_entity_refusals(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}'):
            with self.assertRaises(ledger.ProvenanceRefusal):
                ledger.document(raw)
        with self.assertRaises(ledger.ProvenanceRefusal):
            ledger.parse_xml(b'<!DOCTYPE data [<!ENTITY x "expanded">]><testsuite/>')


if __name__ == "__main__":
    unittest.main()

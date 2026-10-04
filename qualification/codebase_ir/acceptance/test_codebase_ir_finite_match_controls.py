"""Independent golden finite matching cases and coherent custody refusals."""
import copy
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE = Path(__file__).parent / "finite_match_controls/receiver.py"
SPEC = importlib.util.spec_from_file_location("finite_match_receiver", MODULE)
receiver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(receiver)
RELATIVE_INPUT = Path("artifacts/codebase_ir_parallel_qualification/acceptance/20261003-finite-match-input-01/finite_match_input.json")


def input_manifest():
    candidates = []
    if os.environ.get("FINITE_MATCH_MANIFEST"):
        candidates.append(Path(os.environ["FINITE_MATCH_MANIFEST"]).absolute())
    candidates.extend(parent / RELATIVE_INPUT for parent in list(Path(__file__).resolve().parents)[:12])
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise ValueError("bounded retained fixture discovery failed; set FINITE_MATCH_MANIFEST for an external snapshot")


class FiniteMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.input = input_manifest()
        capture = receiver.Capture()
        cls.manifest = receiver.document(capture.take(cls.input))
        cls.fixture = receiver.document(capture.take(Path(cls.manifest["requirements"]["path"]), cls.manifest["requirements"]))
        prior = receiver.document(capture.take(Path(cls.manifest["prior_report"]["path"]), cls.manifest["prior_report"]))
        cls.raw, cls.evidence = {}, {}
        cls.summaries = {row["group"]: row for row in prior["groups"]}
        for group in cls.manifest["groups"]:
            label = group["group"]
            cls.raw[label] = {row["role"]: capture.take(Path(row["path"]), row) for row in group["artifacts"]}
            cls.evidence[label] = receiver.finite_rows(label, cls.raw[label], cls.summaries[label])
        capture.stable()

    def setUp(self):
        self.fixture_copy = copy.deepcopy(self.fixture)

    def results(self, fixture=None):
        return receiver.match_requirements(fixture or self.fixture_copy, self.evidence)

    def refused(self, fixture, pattern):
        with self.assertRaisesRegex(ValueError, pattern):
            receiver.match_requirements(fixture, self.evidence)

    def test_complete_independent_golden_dispositions_and_tasks(self):
        rows, tasks, conflicts = self.results()
        self.assertEqual([row["disposition"] for row in rows], ["recorded_supported", "recorded_supported", "recorded_refuted", "uncovered", "recorded_refuted", "uncovered", "uncovered", "recorded_supported", "unsupported", "runtime_deferred", "unsupported", "runtime_deferred"])
        self.assertEqual([row["original_requirement"] for row in rows], self.fixture["requirements"])
        self.assertEqual([row["original_task"] for row in tasks], self.fixture["tasks"])
        self.assertEqual(len(tasks), 13)
        self.assertTrue(all(row["runtime_disposition"] == "deferred_unqualified" and row["execution_eligible"] is False for row in tasks))
        self.assertEqual([row["requirement_ids"] for row in conflicts], [["cold_exact", "cold_other_offset"], ["cold_partial", "cold_other_offset"]])

    def test_native_rows_have_independently_stated_values(self):
        for group in receiver.GROUPS:
            rows = self.evidence[group]["rows"]
            self.assertEqual([row["input"] for row in rows], [-2, -1, 0, 1, 2])
            self.assertEqual([row["output"] for row in rows], [-1, 0, 1, 2, 3] if group == receiver.GROUPS[2] else [0, 1, 2, 3, 4])

    def test_adverse_refutation_preserves_uncovered_frontier(self):
        rows, _, _ = self.results()
        self.assertEqual(rows[4]["counterexample"], {"input": -2, "observed_output": -1, "required_output": 0})
        self.assertEqual(rows[4]["uncovered_inputs"], [3])
        self.assertEqual(rows[4]["domain_applicability"], "partial")

    def test_empty_domain_never_becomes_vacuous_support(self):
        row = self.results()[0][6]
        self.assertEqual((row["disposition"], row["domain_applicability"]), ("uncovered", "empty"))
        self.assertIs(row["runtime_fact"], False)

    def test_complete_subset_is_conditional_and_outside_domain_is_uncovered(self):
        rows = self.results()[0]
        self.assertEqual(rows[1]["covered_inputs"], [-1, 1])
        self.assertEqual(rows[5]["uncovered_inputs"], [3, 4])
        self.assertTrue(all(row["runtime_fact"] is False and row["proof_reuse_eligible"] is False for row in rows))

    def test_other_property_and_runtime_never_reuse_recorded_support(self):
        rows = self.results()[0]
        self.assertEqual(rows[10]["reason"], "property_differs_from_bound_recorded_contract")
        self.assertEqual(rows[9]["disposition"], "runtime_deferred")
        self.assertEqual(rows[11]["disposition"], "runtime_deferred")

    def test_timeout_custody_is_unavailable_not_invented_timeout(self):
        self.fixture_copy["requirements"][8]["property"]["name"] = "checker_timeout_custody"
        self.assertEqual(self.results()[0][8]["disposition"], "unsupported")

    def test_unicode_original_clause_and_authored_population_bounds(self):
        self.fixture_copy["requirements"][0]["text"] = "条件: recorded integer outputs remain finite — λ."
        self.assertEqual(self.results()[0][0]["original_requirement"]["text"], self.fixture_copy["requirements"][0]["text"])
        fixture = copy.deepcopy(self.fixture)
        fixture["requirements"] *= 3
        self.refused(fixture, "bounded requirement/task lists")
        fixture = copy.deepcopy(self.fixture)
        fixture["requirements"][0]["id"] = "x" * 65
        self.refused(fixture, "authored text allocation bounds")

    def test_missing_property_is_refused(self):
        del self.fixture_copy["requirements"][0]["property"]
        self.refused(self.fixture_copy, "closed fields")

    def test_duplicate_and_unsorted_domains_are_refused(self):
        for domain in ([0, 0], [1, -1]):
            with self.subTest(domain=domain):
                fixture = copy.deepcopy(self.fixture)
                fixture["requirements"][0]["requested_domain"] = domain
                self.refused(fixture, "canonical sorted unique")

    def test_bool_float_and_large_domain_values_are_refused(self):
        for domain in ([False], [1.0], [2**63]):
            with self.subTest(domain=domain):
                fixture = copy.deepcopy(self.fixture)
                fixture["requirements"][0]["requested_domain"] = domain
                self.refused(fixture, "exact integer requested domain")

    def test_duplicate_ids_and_omitted_requirement_task_membership_refuse(self):
        self.fixture_copy["requirements"][1]["id"] = self.fixture_copy["requirements"][0]["id"]
        self.refused(self.fixture_copy, "duplicate requirement")
        fixture = copy.deepcopy(self.fixture)
        fixture["tasks"] = [row for row in fixture["tasks"] if row["id"] not in {"task_cold_exact", "all_requirements"}]
        self.refused(fixture, "every requirement retained")

    def test_duplicate_task_refs_and_task_ids_refuse(self):
        self.fixture_copy["tasks"][0]["requirement_ids"] *= 2
        self.refused(self.fixture_copy, "unique task requirement")
        fixture = copy.deepcopy(self.fixture)
        fixture["tasks"][1]["id"] = fixture["tasks"][0]["id"]
        self.refused(fixture, "duplicate task ID")

    def test_source_assumptions_and_contract_identity_are_bound(self):
        for key, value in (("source_sha256", "0" * 64), ("compiled_cid", "forged"), ("assumptions", [])):
            with self.subTest(key=key):
                fixture = copy.deepcopy(self.fixture)
                fixture["requirements"][0][key] = value
                self.refused(fixture, "source/compiled/assumption")

    def test_closed_profile_and_typed_property(self):
        for prop in ({"kind": "integer_offset", "offset": True}, {"kind": "integer_output", "extra": True}, {"kind": "unknown"}):
            with self.subTest(prop=prop):
                fixture = copy.deepcopy(self.fixture)
                fixture["requirements"][0]["property"] = prop
                self.refused(fixture, "property")

    def test_strict_json_duplicates_surrogates_nonfinite_and_deep_structure(self):
        for raw in (b'{"x":1,"x":2}', b'"\\ud800"', b'1e999', b'NaN', b'9' * 100, b'[' * 40 + b'0' + b']' * 40):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    receiver.document(raw)

    def test_capture_final_symlink_fifo_and_growth_refuse(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for kind in ("symlink", "fifo", "growth"):
                with self.subTest(kind=kind):
                    path = root / kind
                    path.write_bytes(b"abc")
                    capture = receiver.Capture()
                    capture.take(path)
                    if kind == "growth":
                        path.write_bytes(b"abcd")
                    else:
                        path.unlink()
                        if kind == "fifo":
                            os.mkfifo(path)
                        else:
                            target = root / "target"
                            target.write_bytes(b"abc")
                            path.symlink_to(target)
                    with self.assertRaises(ValueError):
                        capture.stable()

    def test_capture_shared_aggregate_preallocation_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            one, two = root / "one", root / "two"
            one.write_bytes(b"1234")
            two.write_bytes(b"5678")
            capture = receiver.Capture()
            capture.take(one)
            retained = receiver.Capture(capture.budget)
            with patch.object(receiver, "MAX_TOTAL", 7):
                with self.assertRaisesRegex(ValueError, "bounded input"):
                    retained.take(two)

    def test_population_refuses_root_alias_and_extra_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real = root / "real"
            real.mkdir()
            (real / "file").write_bytes(b"x")
            alias = root / "alias"
            alias.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "canonical output directory"):
                receiver.population(alias, {"file"})
            with self.assertRaisesRegex(ValueError, "unexpected retained output"):
                receiver.population(real, set())

    def test_coherently_repaired_result_cannot_promote_native_refutation(self):
        group = receiver.GROUPS[2]
        raw = copy.deepcopy(self.raw[group])
        result = receiver.document(raw["result"])
        result["offset_clause_satisfied"], result["counterexample"] = True, None
        result["result_cid"] = receiver.cid({k: v for k, v in result.items() if k != "result_cid"})
        raw["result"] = receiver.canonical(result)
        summary = copy.deepcopy(self.summaries[group])
        summary.update(result_cid=result["result_cid"], recorded_offset_clause_satisfied=True, recorded_counterexample=None)
        with self.assertRaisesRegex(ValueError, "recorded offset disposition"):
            receiver.finite_rows(group, raw, summary)

    def test_coherent_authority_escalation_and_boolean_rows_refuse(self):
        group = receiver.GROUPS[0]
        for mutation in ("authority", "bool"):
            with self.subTest(mutation=mutation):
                raw = copy.deepcopy(self.raw[group])
                result = receiver.document(raw["result"])
                if mutation == "authority":
                    result["runtime_behavior_verified"] = True
                else:
                    result["trace"]["observations"][2]["input"] = False
                    result["observations"] = result["trace"]["observations"]
                    raw["trace"] = receiver.canonical(result["trace"])
                result["result_cid"] = receiver.cid({k: v for k, v in result.items() if k != "result_cid"})
                raw["result"] = receiver.canonical(result)
                summary = copy.deepcopy(self.summaries[group])
                summary["result_cid"] = result["result_cid"]
                with self.assertRaises(ValueError):
                    receiver.finite_rows(group, raw, summary)

    def test_actual_audit_preserves_native_and_complete_authored_dispositions(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            report = receiver.audit(self.input, output)
            self.assertEqual([report[key] for key in ("recorded_supported_count", "recorded_refuted_count", "uncovered_count", "unsupported_count", "runtime_deferred_count")], [3, 2, 3, 2, 2])
            self.assertEqual((report["task_count"], report["runtime_residual_task_count"]), (13, 13))
            self.assertEqual((report["runtime_fact_count"], report["tasks_omitted_count"], report["additional_attempted_training_epochs"]), (0, 0, 0))
            self.assertTrue(all(report[flag] is False for flag in receiver.FALSE_FLAGS))

    def test_rehashed_prior_report_forgery_refuses_independent_anchor(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = copy.deepcopy(self.manifest)
            prior = receiver.document(Path(manifest["prior_report"]["path"]).read_bytes())
            prior["groups"][2]["recorded_offset_clause_satisfied"] = True
            raw = receiver.canonical(prior)
            producer = root / "producer"
            producer.mkdir()
            forged = producer / "forged_prior.json"
            forged.write_bytes(raw)
            manifest["prior_report"] = {"path": str(forged), "sha256": receiver.sha(raw), "size_bytes": len(raw)}
            spec = root / "input" / "manifest.json"
            spec.parent.mkdir()
            spec.write_bytes(receiver.canonical(manifest))
            with self.assertRaisesRegex(ValueError, "independent immutable prior anchor"):
                receiver.audit(spec, root / "output")

    def test_safe_output_refuses_original_scope_and_late_output_injection(self):
        with self.assertRaisesRegex(ValueError, "outside input scopes"):
            receiver.audit(self.input, self.input.parent / "unsafe-output")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            original = receiver.Capture.stable
            reached = []

            def late(capture):
                value = original(capture)
                if (output / "finite_match_controls.json").exists() and not reached:
                    (output / "late-extra").write_bytes(b"unselected")
                    reached.append(True)
                return value

            with patch.object(receiver.Capture, "stable", new=late):
                with self.assertRaisesRegex(ValueError, "unexpected retained output"):
                    receiver.audit(self.input, output)
            self.assertEqual(reached, [True])

    def test_root_alias_at_last_population_fence_is_reached_and_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            original = receiver.population
            calls, reached = 0, []

            def late_alias(directory, expected):
                nonlocal calls
                calls += 1
                if calls == 4:
                    moved = root / "moved-output"
                    output.rename(moved)
                    output.symlink_to(moved, target_is_directory=True)
                    reached.append(True)
                return original(directory, expected)

            with patch.object(receiver, "population", new=late_alias):
                with self.assertRaisesRegex(ValueError, "canonical output directory root"):
                    receiver.audit(self.input, output)
            self.assertEqual(reached, [True])


if __name__ == "__main__":
    unittest.main()

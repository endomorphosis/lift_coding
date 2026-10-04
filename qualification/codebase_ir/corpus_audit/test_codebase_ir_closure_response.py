"""Proposed owner evidence stays bound, conservative and separate from closure."""
from __future__ import annotations

import copy
import json
import stat
import unittest
from dataclasses import replace
from unittest import mock

import codebase_ir_closure_requests as handoff
import codebase_ir_closure_response as response
import codebase_ir_corpus_audit as audit
import test_codebase_ir_closure_requests as closure_controls


class OwnerResponseControls(unittest.TestCase):
    def setUp(self):
        factory = closure_controls.ClosureEvidenceControls("runTest")
        factory.setUp()
        self.factory = factory
        self.addCleanup(factory.doCleanups)
        self.root = factory.root
        path, _, _ = factory.inputs()
        handoff.create_closure_requests(path, self.root / "handoff", source_cas=factory.cas)
        self.requests = self.root / "handoff" / "closure_requests.json"
        response.review_response(self.requests, self.root / "template")
        self.value = json.loads((self.root / "template" / "response_template.json").read_bytes())
        self.input = self.root / "template" / "response.json"
        scope = json.loads((self.root / "template" / "captured_scope.json").read_bytes())
        self.final = next(unit["id"] for unit in scope["units"] if unit["role"] == "final")
        self.train = next(item for row in self.value["responses"] for item in row["observations"]
                          if item["unit_id"] == "native/child/training_targets/0")

    def review(self, value=None, name="review", **kwargs):
        self.input.write_bytes(audit._canonical(self.value if value is None else value))
        return response.review_response(self.requests, self.root / name, response_path=self.input, **kwargs)

    def relation(self, kind, target, source=None):
        (self.train if source is None else source)["relations"].append(
            {"kind": kind, "target_unit_id": target, "evidence_ids": ["captured-owner-facts"]})

    def test_native_template_roundtrip_preserves_all_twenty_unknowns(self):
        report = self.review()
        self.assertEqual(report["disposition"], "proposed_evidence_incomplete")
        self.assertEqual(report["response_request_count"], 4)
        self.assertEqual(report["baseline_issue_count"], 20)
        self.assertEqual(report["proposed_audit_issue_count"], 20)
        self.assertFalse(report["native_closure_certification_verified"])
        self.assertEqual(report["closure_claims_applied"], 0)
        preview = json.loads((self.root / "review" / "proposed_relation_audit_report.json").read_bytes())
        baseline = json.loads((self.root / "review" / "baseline_audit_report.json").read_bytes())
        self.assertEqual(preview["units"], baseline["units"])
        self.assertEqual(set(map(audit._canonical, preview["issues"])), set(map(audit._canonical, baseline["issues"])))
        self.assertFalse(preview["complete_for_declared_scope"])

    def test_authored_positive_related_train_revisions_remain_proposed(self):
        self.relation("related_revision", "native/root/training_targets/0")
        self.train["frontiers"] = []
        self.train["dependency_inventory_claim"] = "captured_scope"
        self.train["revision_inventory_claim"] = "captured_scope"
        report = self.review()
        self.assertEqual(report["proposed_relation_count"], 1)
        self.assertEqual(report["proposed_inventory_claim_count"], 2)
        self.assertEqual(report["contradiction_count"], 0)
        self.assertEqual(report["leakage_count"], 0)
        self.assertEqual(report["proposed_audit_issue_count"], 20)
        self.assertFalse(report["relationship_truth_verified"])

    def test_final_dependency_negative_detects_cross_role_leak(self):
        self.relation("dependency", self.final)
        report = self.review()
        self.assertEqual(report["disposition"], "leaks_found")
        self.assertIn("dependency_connected", {item["kind"] for item in report["leaks"]})
        self.assertEqual(report["proposed_audit_issue_count"], 20)

    def test_final_related_revision_negative_detects_cross_role_leak(self):
        self.relation("related_revision", self.final)
        report = self.review()
        self.assertIn("related_revision", {item["kind"] for item in report["leaks"]})
        self.assertFalse(report["whole_repository_coverage"])

    def test_disjoint_revision_claim_conflicts_with_captured_same_path(self):
        self.relation("revision_family_disjoint", "native/root/training_targets/0")
        report = self.review()
        self.assertEqual(report["disposition"], "contradictory")
        self.assertEqual(report["contradiction_count"], 1)

    def test_dependency_disjointness_checks_transitive_proposed_links(self):
        other = next(item for row in self.value["responses"] for item in row["observations"]
                     if item["unit_id"] == "native/root/tuning_targets/0")
        self.relation("dependency", other["unit_id"])
        self.relation("dependency", self.final, source=other)
        self.relation("dependency_group_disjoint", self.final)
        report = self.review()
        self.assertEqual(report["contradiction_count"], 1)
        self.assertGreater(report["leakage_count"], 0)

    def test_complete_scoped_claim_with_frontier_is_contradictory(self):
        self.train["dependency_inventory_claim"] = "captured_scope"
        report = self.review()
        self.assertEqual(report["contradictions"][0]["code"], "proposed_complete_scope_has_unresolved_frontiers")

    def test_partial_response_retains_unanswered_requests(self):
        self.value["responses"] = self.value["responses"][:1]
        report = self.review()
        self.assertEqual(report["response_request_count"], 1)
        self.assertEqual(len(report["unanswered_request_ids"]), 3)
        self.assertEqual(report["proposed_audit_issue_count"], 20)

    def test_stale_scope_request_and_head_bindings_rejected(self):
        for field in self.value["binding"]:
            changed = copy.deepcopy(self.value)
            changed["binding"][field] = "0" * 64
            with self.subTest(field=field), self.assertRaises(audit.AuditInputError):
                self.review(changed)
        for field in ("request_sha256", "native_target_bindings_sha256"):
            changed = copy.deepcopy(self.value)
            changed["responses"][0]["request_binding"][field] = "0" * 64
            with self.subTest(field=field), self.assertRaises(audit.AuditInputError):
                self.review(changed)

    def test_handoff_target_head_tampering_rejected_before_template(self):
        value = json.loads(self.requests.read_bytes())
        value["closure_requests"][0]["native_target_bindings"][0]["head"]["generation"] += 1
        self.requests.write_bytes(audit._canonical(value))
        with self.assertRaisesRegex(audit.AuditInputError, "head/target binding"):
            response.review_response(self.requests, self.root / "bad")

    def test_missing_ancestor_survives_valid_response(self):
        path, _, _ = self.factory.inputs(missing_parent=True)
        handoff.create_closure_requests(path, self.root / "missing-handoff", source_cas=self.factory.cas)
        requests = self.root / "missing-handoff" / "closure_requests.json"
        response.review_response(requests, self.root / "missing-template")
        report = response.review_response(requests, self.root / "missing-review",
                                          response_path=self.root / "missing-template" / "response_template.json")
        baseline = json.loads((self.root / "missing-review" / "baseline_audit_report.json").read_bytes())
        preview = json.loads((self.root / "missing-review" / "proposed_relation_audit_report.json").read_bytes())
        self.assertIn("native_parent_unavailable", {item["code"] for item in baseline["issues"]})
        self.assertIn("native_parent_unavailable", {item["code"] for item in preview["issues"]})
        self.assertEqual(report["proposed_audit_issue_count"], report["baseline_issue_count"])

    def test_evidence_tamper_and_unbound_retained_artifact_rejected(self):
        facts = self.root / "template" / "owner_facts.json"
        original = facts.read_bytes()
        facts.write_bytes(original + b" ")
        with self.assertRaises(audit.AuditInputError):
            self.review()
        facts.write_bytes(b"foreign retained claim")
        self.value["evidence"][0].update(sha256=audit._sha(facts.read_bytes()), size_bytes=facts.stat().st_size)
        with self.assertRaisesRegex(audit.AuditInputError, "not bound"):
            self.review()

    def test_proposed_statement_requires_exact_scope_without_authentication(self):
        statement = {"schema": "codebase-ir-proposed-owner-evidence@1",
                     "requests_sha256": self.value["binding"]["requests_sha256"],
                     "captured_scope_sha256": self.value["binding"]["captured_scope_sha256"],
                     "description": "Authored observation of the captured working overlay; external rename history unknown."}
        raw = audit._canonical(statement)
        (self.root / "template" / "statement.json").write_bytes(raw)
        self.value["evidence"] = [{"id": "captured-owner-facts", "kind": "proposed_owner_statement",
                                   "file": "statement.json", "sha256": audit._sha(raw), "size_bytes": len(raw)}]
        report = self.review()
        self.assertFalse(report["producer_authentication_verified"])
        statement["captured_scope_sha256"] = "0" * 64
        raw = audit._canonical(statement)
        (self.root / "template" / "statement.json").write_bytes(raw)
        self.value["evidence"][0].update(sha256=audit._sha(raw), size_bytes=len(raw))
        with self.assertRaisesRegex(audit.AuditInputError, "stale proposed evidence"):
            self.review(name="bad-statement")

    def test_duplicate_byte_artifacts_retained_once(self):
        original = self.value["evidence"][0]
        (self.root / "template" / "facts-copy.json").write_bytes((self.root / "template" / "owner_facts.json").read_bytes())
        self.value["evidence"].append({**original, "id": "facts-copy", "file": "facts-copy.json"})
        report = self.review()
        self.assertEqual(report["disposition"], "proposed_evidence_incomplete")
        self.assertEqual(len(list((self.root / "review" / "evidence").iterdir())), 1)

    def test_budgets_before_artifact_read_and_for_relationships(self):
        for limits in (replace(response.DEFAULT_LIMITS, max_requests=3),
                       replace(response.DEFAULT_LIMITS, max_observations=1),
                       replace(response.DEFAULT_LIMITS, max_evidence_file_bytes=16),
                       replace(response.DEFAULT_LIMITS, max_evidence_bytes=16),
                       replace(response.DEFAULT_LIMITS, max_total_bytes=32)):
            with self.subTest(limits=limits), self.assertRaises(audit.AuditInputError):
                self.review(limits=limits)
        self.relation("dependency", self.final)
        self.relation("related_revision", self.final)
        with self.assertRaisesRegex(audit.AuditInputError, "relation"):
            self.review(limits=replace(response.DEFAULT_LIMITS, max_relations=1))

    def test_aggregate_budget_caps_initial_read_before_allocation(self):
        real = audit._read_bounded
        observed = []

        def reader(path, maximum):
            observed.append(maximum)
            return real(path, maximum)

        with mock.patch.object(audit, "_read_bounded", reader), self.assertRaises(audit.AuditInputError):
            response.review_response(self.requests, self.root / "bad", limits=replace(response.DEFAULT_LIMITS, max_total_bytes=32))
        self.assertEqual(observed, [32])

    def test_strict_schema_ids_roles_and_authority(self):
        mutations = [lambda v: v.update(extra=True),
                     lambda v: v.update(native_certification_claimed=True),
                     lambda v: v["producer"].update(authentication="trusted"),
                     lambda v: v["responses"].append(copy.deepcopy(v["responses"][0])),
                     lambda v: v["responses"][0]["observations"][0].update(dependency_inventory_claim=[]),
                     lambda v: v["responses"][0]["request_binding"].update(request_id=[]),
                     lambda v: v["evidence"][0].update(kind=[])]
        for mutate in mutations:
            changed = copy.deepcopy(self.value)
            mutate(changed)
            with self.subTest(mutate=mutate), self.assertRaises(audit.AuditInputError):
                self.review(changed)
        self.relation("dependency", "unseen/unknown.py")
        with self.assertRaisesRegex(audit.AuditInputError, "out-of-scope"):
            self.review()

    def test_duplicate_json_keys_and_file_traversal_rejected(self):
        self.input.write_bytes(b'{"schema":"x","schema":"y"}')
        with self.assertRaises(audit.AuditInputError):
            response.review_response(self.requests, self.root / "bad", response_path=self.input)
        self.value["evidence"][0]["file"] = "../handoff/owner_facts.json"
        with self.assertRaises(audit.AuditInputError):
            self.review()

    def test_response_and_scope_bytes_pinned_before_evidence_reads(self):
        original = audit._canonical(self.value)
        self.input.write_bytes(original)
        real = response._evidence

        def mutate(bundle, value, root, limits):
            self.input.write_bytes(b'{}')
            return real(bundle, value, root, limits)

        with mock.patch.object(response, "_evidence", mutate):
            report = response.review_response(self.requests, self.root / "review", response_path=self.input)
        self.assertEqual(report["response_sha256"], audit._sha(original))
        self.assertEqual((self.root / "review" / "captured_response.json").read_bytes(), original)

    def test_reports_are_deterministic_and_private(self):
        self.review(name="first")
        self.review(name="second")
        for name in ("response_review_report.json", "proposed_relation_audit_report.json", "captured_scope.json"):
            first = self.root / "first" / name
            self.assertEqual(first.read_bytes(), (self.root / "second" / name).read_bytes())
            self.assertEqual(stat.S_IMODE(first.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((self.root / "first").stat().st_mode), 0o700)


if __name__ == "__main__":
    unittest.main()

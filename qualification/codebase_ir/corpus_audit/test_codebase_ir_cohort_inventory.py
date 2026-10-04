"""Every captured connected group is retained without an independence claim."""
from __future__ import annotations

import json
import stat
import unittest
from dataclasses import replace
from unittest import mock

import codebase_ir_closure_requests as handoff
import codebase_ir_closure_response as response
import codebase_ir_cohort_inventory as cohort
import codebase_ir_corpus_audit as audit
import test_codebase_ir_closure_response as response_controls


class CohortInventoryControls(unittest.TestCase):
    def setUp(self):
        factory = response_controls.OwnerResponseControls("runTest")
        factory.setUp()
        self.addCleanup(factory.doCleanups)
        self.factory, self.root = factory, factory.root

    def inventory(self, *, name="inventory", **kwargs):
        return cohort.create_inventory(self.root / "review" / "response_review_report.json", self.root / name, **kwargs)

    def review(self):
        return self.factory.review()

    def repin(self, name):
        path = self.root / "review" / name
        report = self.root / "review" / "response_review_report.json"
        value = json.loads(report.read_bytes())
        value["artifacts"][name].update(sha256=audit._sha(path.read_bytes()), size_bytes=path.stat().st_size)
        report.write_bytes(audit._canonical(value))

    def test_all_groups_include_singleton_final_and_repeated_native_targets(self):
        self.review()
        report = self.inventory()
        self.assertEqual(report["unit_count"], 11)
        self.assertEqual(report["group_count"], 4)
        self.assertEqual(report["native_target_membership_count"], 9)
        self.assertEqual(report["ancestral_training_exposure_count"], 1)
        self.assertEqual(report["inventory_issue_count"], 20)
        self.assertEqual(sum(len(group["unit_ids"]) for group in report["groups"]), 11)
        self.assertEqual(sum(len(group["unresolved_claims"]) for group in report["groups"]), 20)
        self.assertEqual(report["cross_role_group_count"], 0)
        finals = [group for group in report["groups"] if group["final_unit_ids"]]
        self.assertEqual(len(finals), 1)
        self.assertEqual(len(finals[0]["unit_ids"]), 1)
        self.assertFalse(finals[0]["independence_verified"])
        train = next(group for group in report["groups"] if "ancestral/0" in group["unit_ids"])
        self.assertEqual(len(train["unit_ids"]), 6)
        self.assertEqual(len([row for row in train["memberships"] if row["native_target"] is not None]), 5)
        self.assertIn("same_repository_path", {row["kind"] for row in train["edges"]})
        self.assertEqual(len({row["native_target"]["version_id"] for row in train["memberships"] if row["native_target"]}), 2)
        self.assertFalse(report["native_closure_certification_verified"])

    def test_proposed_positive_revision_addition_visible_without_closure_change(self):
        self.factory.relation("related_revision", "native/root/training_targets/0")
        self.review()
        report = self.inventory()
        edges = [row for group in report["groups"] for row in group["edges"]]
        self.assertIn("proposed_owner_relation", {row["basis"] for row in edges})
        self.assertEqual(report["inventory_issue_count"], 20)
        self.assertEqual(report["cross_role_group_count"], 0)

    def test_dependency_and_revision_final_controls_show_explicit_exposure(self):
        for kind in ("dependency", "related_revision"):
            with self.subTest(kind=kind):
                self.factory.train["relations"] = []
                self.factory.relation(kind, self.factory.final)
                self.factory.review(name=kind)
                report = cohort.create_inventory(self.root / kind / "response_review_report.json", self.root / (kind + "-inventory"))
                self.assertEqual(report["group_count"], 3)
                self.assertEqual(report["cross_role_group_count"], 1)
                self.assertEqual(report["final_connected_group_count"], 1)
                group = next(group for group in report["groups"] if group["final_unit_ids"])
                self.assertEqual(group["roles"], ["final", "train"])
                self.assertEqual(group["final_exposure_risk"], "connected_to_training_or_evaluation")
                self.assertEqual(len(group["unresolved_claims"]), 12)
                self.assertFalse(group["closure_certified"])

    def test_owner_frontiers_and_unknowns_remain_attached_to_groups(self):
        self.review()
        report = self.inventory()
        self.assertEqual(report["owner_frontier_count"], 10)
        self.assertEqual(sum(len(group["owner_frontiers"]) for group in report["groups"]), 10)
        self.assertEqual(sum(len(group["original_unknown_completeness_flags"]) for group in report["groups"]), 10)

    def test_shared_unknown_dependency_connects_train_and_final_conservatively(self):
        path = self.root / "input.json"
        value = json.loads(path.read_bytes())
        value["units"][0]["dependencies"] = ["missing:shared-helper"]
        value["units"][0]["dependencies_complete"] = False
        value["native_records"][0]["unit_metadata"]["native/root/training_targets/0"] = {
            "dependencies": ["missing:shared-helper"], "dependencies_complete": False,
            "related_revisions": [], "revision_relations_complete": False}
        path.write_bytes(audit._canonical(value))
        handoff.create_closure_requests(path, self.root / "unknown-handoff", source_cas=self.factory.factory.cas)
        response.review_response(self.root / "unknown-handoff" / "closure_requests.json", self.root / "unknown-review")
        report = cohort.create_inventory(self.root / "unknown-review" / "response_review_report.json", self.root / "unknown-inventory")
        group = next(group for group in report["groups"] if group["final_unit_ids"])
        self.assertEqual(group["unresolved_reference_ids"], ["missing:shared-helper"])
        self.assertTrue(group["cross_role_connection"])
        self.assertEqual(group["final_exposure_risk"], "connected_to_training_or_evaluation")

    def test_awaiting_response_inventory_retains_all_baseline_groups(self):
        report = cohort.create_inventory(self.root / "template" / "response_review_report.json", self.root / "inventory")
        self.assertEqual(report["review_disposition"], "awaiting_response")
        self.assertEqual(report["group_count"], 4)
        self.assertEqual(report["inventory_issue_count"], 20)

    def test_contradictory_review_does_not_remove_connected_group(self):
        self.factory.relation("revision_family_disjoint", "native/root/training_targets/0")
        self.review()
        report = self.inventory()
        self.assertEqual(report["review_disposition"], "contradictory")
        train = next(group for group in report["groups"] if self.factory.train["unit_id"] in group["unit_ids"])
        self.assertIn("native/root/training_targets/0", train["unit_ids"])
        self.assertEqual(len(train["contradictions"]), 1)

    def test_old_review_missing_inventory_refused_without_fabricated_pins(self):
        self.review()
        path = self.root / "review" / "response_review_report.json"
        value = json.loads(path.read_bytes())
        value.pop("artifacts")
        path.write_bytes(audit._canonical(value))
        with self.assertRaises(audit.AuditInputError):
            self.inventory()

    def test_detached_scope_preview_response_and_evidence_bytes_refused(self):
        self.review()
        root = self.root / "review"
        evidence = next((root / "evidence").iterdir()).relative_to(root).as_posix()
        for name in ("captured_scope.json", "proposed_relation_audit_report.json", "captured_response.json", evidence):
            path = root / name
            original = path.read_bytes()
            path.write_bytes(original + b" ")
            with self.subTest(name=name), self.assertRaises(audit.AuditInputError):
                self.inventory()
            path.write_bytes(original)

    def test_preview_role_and_completeness_drift_refused_even_when_outer_pin_updated(self):
        self.review()
        path = self.root / "review" / "proposed_relation_audit_report.json"
        original = path.read_bytes()
        for field, value in (("role", "final"), ("dependencies_complete", True), ("content_sha256", "0" * 64)):
            changed = json.loads(original)
            changed["units"][0][field] = value
            path.write_bytes(audit._canonical(changed))
            self.repin(path.name)
            with self.subTest(field=field), self.assertRaisesRegex(audit.AuditInputError, "role/identity/closure"):
                self.inventory()
        path.write_bytes(original)

    def test_unreviewed_relation_cannot_enter_preview(self):
        self.review()
        path = self.root / "review" / "proposed_relation_audit_report.json"
        value = json.loads(path.read_bytes())
        next(row for row in value["units"] if row["id"] == self.factory.train["unit_id"])["dependencies"].append(self.factory.final)
        path.write_bytes(audit._canonical(value))
        self.repin(path.name)
        with self.assertRaisesRegex(audit.AuditInputError, "unreviewed proposed"):
            self.inventory()

    def test_baseline_unknown_issues_cannot_be_removed(self):
        self.review()
        path = self.root / "review" / "proposed_relation_audit_report.json"
        value = json.loads(path.read_bytes())
        value["issues"].pop()
        path.write_bytes(audit._canonical(value))
        self.repin(path.name)
        with self.assertRaisesRegex(audit.AuditInputError, "unknown claims"):
            self.inventory()

    def test_counts_enums_budgets_and_private_deterministic_output(self):
        self.review()
        report = self.root / "review" / "response_review_report.json"
        original = report.read_bytes()
        for field, value in (("baseline_issue_count", True), ("disposition", []), ("whole_repository_coverage", True)):
            changed = json.loads(original)
            changed[field] = value
            report.write_bytes(audit._canonical(changed))
            with self.subTest(field=field), self.assertRaises(audit.AuditInputError):
                self.inventory()
        report.write_bytes(original)
        for limits in (replace(cohort.DEFAULT_LIMITS, max_total_bytes=32), replace(cohort.DEFAULT_LIMITS, max_artifacts=1),
                       replace(cohort.DEFAULT_LIMITS, max_edges=1), replace(cohort.DEFAULT_LIMITS, max_group_rows=1)):
            with self.subTest(limits=limits), self.assertRaises(audit.AuditInputError):
                self.inventory(limits=limits)
        self.inventory(name="first")
        self.inventory(name="second")
        path = self.root / "first" / "cohort_inventory.json"
        self.assertEqual(path.read_bytes(), (self.root / "second" / path.name).read_bytes())
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_remaining_budget_is_applied_before_read(self):
        self.review()
        real, observed = audit._read_bounded, []

        def read(path, maximum):
            observed.append(maximum)
            return real(path, maximum)

        with mock.patch.object(audit, "_read_bounded", read), self.assertRaises(audit.AuditInputError):
            self.inventory(limits=replace(cohort.DEFAULT_LIMITS, max_total_bytes=32))
        self.assertEqual(observed, [32])


if __name__ == "__main__":
    unittest.main()

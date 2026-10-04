"""Crossing regressions against projected genuine historical native returns.

The JSON references are inert comparator inputs, not currently eligible evidence.
"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import codebase_ir_acceptance as fixtures
import codebase_ir_planning_qualification as planning


class PlanningCrossingTests(unittest.TestCase):
    def setUp(self):
        reference = json.loads(Path(__file__).with_name("planning_regression_reference.json").read_bytes())
        self.assertEqual(reference["authority"], "assertion_reference_only")
        self.records = reference["records"]
        self.case = fixtures.scenarios()[0]

    def test_plain_and_capacity_genuine_historical_shapes_preserve_clauses(self):
        planning.assert_planning_crossing(self.records["baseline_plain"], self.case, capacity=False)
        planning.assert_planning_crossing(self.records["baseline_capacity"], self.case, capacity=True)

    def test_selector_task_and_effect_drift_cannot_pass_crossing(self):
        mutations = ("selector", "effect", "review", "predicate", "closure", "population", "critic", "structural", "fact", "authority")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                result = copy.deepcopy(self.records["baseline_capacity"])
                if mutation == "selector":
                    result["candidate_plan"]["tasks"][0]["predicted_symbols"] = ["decoy"]
                elif mutation == "effect":
                    result["candidate_plan"]["effects"][0]["operation"] = "delete"
                elif mutation == "review":
                    result["candidate_plan"]["effects"][0]["review_ref"] = "foreign:review"
                elif mutation == "predicate":
                    result["critic_evidence"]["operation_bindings"][planning.TASK_OFFSET]["predicate_id"] = "wrong:clause"
                elif mutation == "closure":
                    result["candidate_plan"]["tasks"][0]["closes_obligation_ids"] = ["wrong:closure"]
                elif mutation == "population":
                    result["obligation_graph"]["task_candidates"].pop()
                elif mutation == "critic":
                    result["critic_evidence"]["finite_match"]["residual_clause_ids"] = []
                elif mutation == "structural":
                    del result["critic_evidence"]["structural_evidence"]
                elif mutation == "fact":
                    result["obligation_graph"]["facts"] = []
                else:
                    result["production_admitted"] = True
                with self.assertRaises(ValueError):
                    planning.assert_planning_crossing(result, self.case, capacity=True)

    def test_duplicate_or_missing_goal_and_effect_ids_cannot_be_hidden(self):
        for key in ("required_goal_ids", "expected_effect_ids"):
            for action in ("duplicate", "missing"):
                with self.subTest(key=key, action=action):
                    result = copy.deepcopy(self.records["baseline_capacity"])
                    ids = result["candidate_plan"][key]
                    if action == "duplicate":
                        ids.append(ids[0])
                    else:
                        ids.pop()
                    with self.assertRaisesRegex(ValueError, "required goal or effect"):
                        planning.assert_planning_crossing(result, self.case, capacity=True)

    def test_duplicate_task_or_stage_population_is_rejected(self):
        for container in ("task", "stage"):
            result = copy.deepcopy(self.records["baseline_capacity"])
            target = result["obligation_graph"]["task_candidates"] if container == "task" else result["preview"]["stage_results"]
            target.append(copy.deepcopy(target[0]))
            with self.assertRaises(ValueError):
                planning.assert_planning_crossing(result, self.case, capacity=True)

    def test_held_capacity_release_does_not_grant_preview_admission(self):
        for field, value in (("verdict", "admitted"), ("read_only", False), ("wrote_effects", ["worker:launch"])):
            with self.subTest(field=field):
                result = copy.deepcopy(self.records["baseline_capacity"])
                result["preview"][field] = value
                with self.assertRaisesRegex(ValueError, "cannot admit"):
                    planning.assert_planning_crossing(result, self.case, capacity=True)
        result = copy.deepcopy(self.records["baseline_capacity"])
        result["reservation_released_on_return"] = False
        with self.assertRaisesRegex(ValueError, "held-capacity"):
            planning.assert_planning_crossing(result, self.case, capacity=True)

    def test_plain_preview_cannot_invent_capacity_feasibility(self):
        result = copy.deepcopy(self.records["baseline_plain"])
        parallel = next(stage for stage in result["preview"]["stage_results"] if stage["stage"] == "parallel_plan")
        parallel["passed"] = True
        with self.assertRaisesRegex(ValueError, "invented held capacity"):
            planning.assert_planning_crossing(result, self.case, capacity=False)

    def test_snapshot_namespace_refuses_missing_or_live_core_fallback(self):
        finder = planning.SnapshotNamespaceFinder([Path("/tmp/authored-pinned-core")])
        with patch.object(planning.importlib.machinery.PathFinder, "find_spec", return_value=None):
            with self.assertRaisesRegex(ImportError, "absent from pinned"):
                finder.find_spec("ipfs_accelerate_py.missing")
        escaped = SimpleNamespace(origin="/home/barberb/lift_coding/external/ipfs_accelerate/ipfs_accelerate_py/__init__.py", submodule_search_locations=[])
        with patch.object(planning.importlib.machinery.PathFinder, "find_spec", return_value=escaped):
            with self.assertRaisesRegex(ImportError, "escaped pinned"):
                finder.find_spec("ipfs_accelerate_py")
        allowed = SimpleNamespace(origin="/tmp/authored-pinned-core/ipfs_accelerate_py/__init__.py", submodule_search_locations=[])
        with patch.object(planning.importlib.machinery.PathFinder, "find_spec", return_value=allowed):
            self.assertIs(finder.find_spec("ipfs_accelerate_py"), allowed)

    def test_snapshot_binding_requires_distinct_sibling_import_roots(self):
        for roots in ([], [Path("/tmp/a"), Path("/tmp/a")], [Path("/tmp/a"), Path("/elsewhere/b")]):
            with self.subTest(roots=roots), self.assertRaisesRegex(ValueError, "sibling import roots"):
                planning.verify_snapshot_binding(roots, "a" * 64)

    def test_wrong_snapshot_identity_prevents_native_entry_and_retains_refusal(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "private-run"
            with (patch.object(planning, "verify_snapshot_binding", side_effect=ValueError("snapshot canonical identity differs")),
                    patch.object(planning, "native_session") as session,
                    patch.object(planning, "native_source_snapshot") as source,
                    patch.object(planning, "imported_native_sources", return_value=[]),
                    patch.object(planning, "external_dependency_pins", return_value={}),
                    self.assertRaisesRegex(ValueError, "snapshot canonical identity")):
                planning.run(output, lean=Path("/unused/lean"), snapshot_roots=[Path("/tmp/accelerate"), Path("/tmp/datasets")],
                    snapshot_sha256="f" * 64)
            session.assert_not_called()
            source.assert_not_called()
            report = json.loads((output / "planning_qualification.json").read_bytes())
            self.assertEqual(report["status"], "snapshot_integrity_refused")
            self.assertFalse(report["runtime_snapshot_identity_stable"])

    def test_post_trial_snapshot_drift_refuses_previously_passed_native_result(self):
        before = {"snapshot_sha256": "a" * 64, "verified": True, "verifier_sha256": "b" * 64}
        after = {**before, "verifier_sha256": "c" * 64}
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "private-run"
            with (patch.object(planning, "verify_snapshot_binding", side_effect=[before, after]) as verifier,
                    patch.object(planning, "configure_snapshot"),
                    patch.object(planning, "native_session", return_value={"status": "passed"}),
                    patch.object(planning, "native_source_snapshot", return_value=([], {})),
                    patch.object(planning, "imported_native_sources", return_value=[{"unchanged": True}]),
                    patch.object(planning, "external_dependency_pins", return_value={})):
                report = planning.run(output, lean=Path("/unused/lean"),
                    snapshot_roots=[Path("/tmp/accelerate"), Path("/tmp/datasets")], snapshot_sha256="a" * 64)
            self.assertEqual(verifier.call_count, 2)
            self.assertEqual(report["native_planning"]["status"], "passed")
            self.assertEqual(report["status"], "snapshot_integrity_refused")
            self.assertFalse(report["runtime_snapshot_identity_stable"])
            self.assertEqual(json.loads((output / "planning_qualification.json").read_bytes())["status"], "snapshot_integrity_refused")

    def test_foreign_roots_cannot_become_valid_by_matching_candidate_goals(self):
        result = copy.deepcopy(self.records["baseline_capacity"])
        foreign = ["foreign:goal:type", "foreign:goal:offset"]
        result["obligation_graph"]["root_obligation_ids"] = foreign
        result["candidate_plan"]["required_goal_ids"] = foreign
        with self.assertRaisesRegex(ValueError, "exact typed clause"):
            planning.assert_planning_crossing(result, self.case, capacity=True)

    def test_missing_predicates_or_nodes_cannot_keep_complete_clause_coverage(self):
        for field in ("predicates", "nodes"):
            result = copy.deepcopy(self.records["baseline_capacity"])
            result["obligation_graph"][field] = []
            with self.assertRaises(ValueError):
                planning.assert_planning_crossing(result, self.case, capacity=True)

    def test_nested_candidate_authority_cannot_escape_top_level_false_flags(self):
        result = copy.deepcopy(self.records["baseline_capacity"])
        result["candidate_plan"]["execution_authority"] = True
        result["candidate_plan"]["production_admitted"] = True
        with self.assertRaisesRegex(ValueError, "nested planning material"):
            planning.assert_planning_crossing(result, self.case, capacity=True)

    def test_predicted_files_cannot_retarget_decoy_while_outputs_remain_selected(self):
        result = copy.deepcopy(self.records["baseline_capacity"])
        result["candidate_plan"]["tasks"][0]["predicted_files"] = ["decoy.py"]
        with self.assertRaisesRegex(ValueError, "selector drifted"):
            planning.assert_planning_crossing(result, self.case, capacity=True)

    def test_extra_worker_stage_is_outside_closed_finite_profile(self):
        result = copy.deepcopy(self.records["baseline_capacity"])
        result["preview"]["stage_results"].append({"stage": "worker_launch", "passed": True})
        with self.assertRaisesRegex(ValueError, "closed finite stage"):
            planning.assert_planning_crossing(result, self.case, capacity=True)

    def test_admission_refusal_requires_exact_unavailable_evidence_profile_reason(self):
        for blockers in ([], ["different:admission:reason"], ["ir_admission_materials_absent", "extra:reason"]):
            result = copy.deepcopy(self.records["baseline_capacity"])
            admission = next(stage for stage in result["preview"]["stage_results"] if stage["stage"] == "admission")
            admission["blockers"] = blockers
            with self.assertRaisesRegex(ValueError, "behavioral admission"):
                planning.assert_planning_crossing(result, self.case, capacity=True)

    def test_held_schedule_cannot_retarget_task_or_source_root(self):
        for mutation in ("task", "root", "replay_root", "base", "merge_target"):
            with self.subTest(mutation=mutation):
                result = copy.deepcopy(self.records["baseline_capacity"])
                execution = result["execution_plan"]
                if mutation == "task":
                    execution["assignments"][0]["task_id"] = "foreign:task"
                elif mutation == "root":
                    execution["repository_tree_id"] = "foreign:root"
                elif mutation == "replay_root":
                    execution["deterministic_replay"]["repository_tree_id"] = "foreign:root"
                else:
                    field = "base_revision" if mutation == "base" else "merge_target"
                    execution["assignments"][0][field] = "foreign:root"
                with self.assertRaisesRegex(ValueError, "held schedule task or source"):
                    planning.assert_planning_crossing(result, self.case, capacity=True)

    def test_held_schedule_preserves_required_leaf_effects_and_producers(self):
        for mutation in ("required", "producer", "terminal", "closed"):
            with self.subTest(mutation=mutation):
                result = copy.deepcopy(self.records["baseline_capacity"])
                leaves = result["execution_plan"]["leaf_producer_closure"]
                if mutation == "required":
                    leaves["required_leaf_ids"] = []
                elif mutation == "producer":
                    effect = next(iter(leaves["producer_by_leaf_id"]))
                    leaves["producer_by_leaf_id"][effect] = "foreign:task"
                elif mutation == "terminal":
                    leaves["terminal_task_ids"] = ["foreign:task"]
                else:
                    leaves["closed"] = False
                with self.assertRaisesRegex(ValueError, "held schedule leaf effects"):
                    planning.assert_planning_crossing(result, self.case, capacity=True)

    def test_held_schedule_cannot_add_or_drop_task_at_later_stage(self):
        for mutation in ("wave", "merge", "conflict", "critical", "dependency"):
            with self.subTest(mutation=mutation):
                result = copy.deepcopy(self.records["baseline_capacity"])
                execution = result["execution_plan"]
                if mutation == "wave":
                    execution["execution_waves"][0]["task_ids"].append("foreign:task")
                elif mutation == "merge":
                    execution["merge_order"] = []
                elif mutation == "conflict":
                    execution["conflict_graph"]["task_ids"] = ["foreign:task"]
                elif mutation == "critical":
                    execution["critical_path"] = []
                else:
                    execution["dependency_edges"] = [{"from": "foreign:task", "to": planning.TASK_OFFSET}]
                with self.assertRaisesRegex(ValueError, "held schedule task population"):
                    planning.assert_planning_crossing(result, self.case, capacity=True)


if __name__ == "__main__":
    unittest.main()

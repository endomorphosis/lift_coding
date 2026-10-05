"""Pure independent fixtures for bounded frozen-head joint span search."""
from __future__ import annotations

import copy
import importlib.util
import itertools
import json
import math
import random
import struct
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("joint_span_fixture_owner", Path(__file__).with_name("select_joint_spans.py"))
selector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(selector)

PRESENT = [True, True, False, False, False, False]


def fixture():
    starts = [[9., 8., 1.], [10., 2., 0.]] + [[0.] * 3 for _ in range(4)]
    ends = [[0., -2., -4.], [0., -1., -3.]] + [[0.] * 3 for _ in range(4)]
    return starts, ends


def brute_force(starts, ends, presence):
    """Small exhaustive oracle: enumerate every legal interval product."""
    def f32(value):
        return struct.unpack("!f", struct.pack("!f", value))[0]

    n = len(starts[0])
    pools = []
    for i in range(6):
        pools.append([(left, right, f32(f32(starts[i][left]) + f32(ends[i][right])))
                      for left in range(n) for right in range(left, n)] if presence[i] else [None])
    feasible = []
    for choices in itertools.product(*pools):
        positions, scores, intervals = set(), [], []
        for item in choices:
            if item is None:
                intervals.append(None)
                continue
            left, right, score = item
            used = set(range(left, right + 1))
            if positions & used:
                break
            positions.update(used)
            scores.append(score)
            intervals.append((left, right))
        else:
            feasible.append((math.fsum(scores), intervals))
    return sorted(feasible, key=lambda row: (-row[0], tuple((-1, -1) if item is None else item for item in row[1])))


class JointSpanTests(unittest.TestCase):
    def test_joint_choice_changes_earlier_facet_to_resolve_greedy_overlap(self):
        result = selector.select_joint_spans(*fixture(), PRESENT)
        self.assertEqual(result["status"], "selected")
        self.assertEqual(result["selected_spans"], [[1, 1], [0, 0], None, None, None, None])
        self.assertEqual(result["best_score"], 16.)
        self.assertEqual(result["diagnostics"]["greedy_overlap_fields"], ["action"])
        # Keeping actor's first choice then repairing action gives only 10.
        self.assertGreater(result["best_score"], 10.)

    def test_small_unpruned_search_matches_independent_exhaustive_oracle(self):
        rng = random.Random(42)
        starts = [[rng.uniform(-3, 3) for _ in range(5)] for _ in range(6)]
        ends = [[rng.uniform(-3, 3) for _ in range(5)] for _ in range(6)]
        presence = [True, True, True, False, False, False]
        oracle = brute_force(starts, ends, presence)
        result = selector.select_joint_spans(starts, ends, presence, candidates_per_facet=64, beam_width=256)
        self.assertEqual(result["status"], "selected")
        self.assertEqual(result["selected_spans"], [list(span) if span is not None else None for span in oracle[0][1]])
        self.assertEqual(result["best_score"], oracle[0][0])
        self.assertEqual(result["runner_up_score"], oracle[1][0])
        self.assertFalse(result["diagnostics"]["incomplete_search"])
        self.assertEqual(result["diagnostics"]["complete_retained_state_count"], len(oracle))

    def test_candidate_pruning_can_hide_feasible_assignment_and_never_falls_back(self):
        result = selector.select_joint_spans(*fixture(), PRESENT, candidates_per_facet=2)
        self.assertEqual(result["status"], "abstained")
        self.assertEqual(result["reason"], "no_complete_assignment_in_retained_candidates")
        self.assertIsNone(result["selected_spans"])
        self.assertTrue(result["diagnostics"]["incomplete_search"])
        self.assertEqual(result["diagnostics"]["pruned_candidate_count"], 8)
        actor = result["diagnostics"]["facets"]["actor"]
        self.assertEqual(actor["retained_cutoff_pair_score"], 7.)
        self.assertEqual(actor["first_pruned_pair_score"], 6.)
        self.assertEqual(selector.select_joint_spans(*fixture(), PRESENT)["status"], "selected")

    def test_beam_pruning_reports_suboptimal_retained_result(self):
        result = selector.select_joint_spans(*fixture(), PRESENT, beam_width=2)
        self.assertEqual(result["status"], "selected")
        self.assertEqual(result["best_score"], 10.)
        self.assertTrue(result["diagnostics"]["incomplete_search"])
        self.assertGreater(result["diagnostics"]["pruned_beam_state_count"], 0)
        self.assertFalse(result["diagnostics"]["global_optimality_established"])
        self.assertEqual(result["diagnostics"]["confidence_scope"], "retained_complete_beam_only")

    def test_tied_complete_assignments_abstain_deterministically(self):
        starts = [[3., 2.] for _ in range(6)]
        ends = [[0., 0.] for _ in range(6)]
        first = selector.select_joint_spans(starts, ends, PRESENT)
        self.assertEqual(first, selector.select_joint_spans(starts, ends, PRESENT))
        self.assertEqual(first["reason"], "ambiguous_joint_scores")
        self.assertEqual(first["joint_score_margin"], 0.)
        self.assertIsNone(first["selected_spans"])

    def test_fixed_presence_cannot_be_dropped_to_force_feasibility(self):
        starts = [[1., 0.] for _ in range(6)]
        ends = [[0., 0.] for _ in range(6)]
        presence = [True, True, True, False, False, False]
        result = selector.select_joint_spans(starts, ends, presence)
        self.assertEqual(result["reason"], "no_complete_assignment_in_retained_candidates")
        self.assertEqual(result["diagnostics"]["fixed_presence"], presence)
        self.assertIsNone(result["selected_spans"])

    def test_absent_facets_are_not_scored_or_made_present(self):
        starts, ends = fixture()
        result = selector.select_joint_spans(starts, ends, PRESENT)
        for field in selector.SPAN_FIELDS[2:]:
            self.assertFalse(result["diagnostics"]["facets"][field]["present"])
            self.assertEqual(result["diagnostics"]["facets"][field]["enumerated_span_count"], 0)
        self.assertEqual(result["selected_spans"][2:], [None] * 4)

    def test_single_source_token_cannot_supply_actor_and_action(self):
        result = selector.select_joint_spans([[0.] for _ in range(6)], [[0.] for _ in range(6)], PRESENT)
        self.assertEqual(result["status"], "abstained")
        self.assertFalse(result["diagnostics"]["incomplete_search"])

    def test_float32_pair_addition_matches_native_stable_row_major_tie(self):
        starts = [[1., 0.], [-100., 10.]] + [[0., 0.] for _ in range(4)]
        ends = [[0., 5e-8], [0., 0.]] + [[0., 0.] for _ in range(4)]
        result = selector.select_joint_spans(starts, ends, PRESENT)
        self.assertEqual(result["diagnostics"]["facets"]["actor"]["greedy_span"], [0, 0])
        self.assertEqual(result["diagnostics"]["facets"]["actor"]["greedy_span_logit_margin"], 0.)
        self.assertEqual(result["selected_spans"][:2], [[0, 0], [1, 1]])

    def test_joint_constraint_can_resolve_a_local_span_tie(self):
        starts = [[5., 5., -100.], [100., -100., -100.]] + [[0.] * 3 for _ in range(4)]
        ends = [[0., 0., -100.], [0., -100., -100.]] + [[0.] * 3 for _ in range(4)]
        result = selector.select_joint_spans(starts, ends, PRESENT)
        self.assertEqual(result["status"], "selected")
        self.assertEqual(result["selected_spans"][:2], [[1, 1], [0, 0]])
        self.assertEqual(result["diagnostics"]["facets"]["actor"]["greedy_span_logit_margin"], 0.)
        self.assertEqual(result["diagnostics"]["confidence_scope"], "retained_complete_beam_only")

    def test_global_gap_threshold_is_applied_to_retained_assignments(self):
        starts = [[1e-8, 0.], [0., 4e-8]] + [[0., 0.] for _ in range(4)]
        ends = [[0., 0.] for _ in range(6)]
        result = selector.select_joint_spans(starts, ends, PRESENT)
        self.assertEqual(result["reason"], "ambiguous_joint_scores")
        self.assertGreater(result["joint_score_margin"], 0.)
        self.assertLess(result["joint_score_margin"], 1e-7)
        self.assertEqual(selector.select_joint_spans(starts, ends, PRESENT, ambiguity_epsilon=0)["status"], "selected")

    def test_nonoverlap_intervals_have_no_actor_before_action_assumption(self):
        result = selector.select_joint_spans(*fixture(), PRESENT)
        self.assertGreater(result["selected_spans"][0][0], result["selected_spans"][1][0])
        positions = []
        for left, right in result["selected_spans"][:2]:
            positions.append(set(range(left, right + 1)))
        self.assertFalse(positions[0] & positions[1])

    def test_report_bounds_and_no_authority_flags(self):
        result = selector.select_joint_spans(*fixture(), PRESENT)
        diagnostic = result["diagnostics"]
        self.assertLessEqual(diagnostic["attempted_expansion_count"], diagnostic["expansion_count_upper_bound"])
        self.assertEqual(diagnostic["enumerated_span_count_upper_bound"], 36)
        self.assertEqual(sum(layer["attempted_expansion_count"] for layer in diagnostic["layers"]),
                         diagnostic["attempted_expansion_count"])
        self.assertEqual(sum(layer["overlap_rejected_expansion_count"] for layer in diagnostic["layers"]),
                         diagnostic["overlap_rejected_expansion_count"])
        self.assertEqual(diagnostic["native_head_value_count"], 36)
        for field in ("target_access", "teacher_forcing", "training_executed", "grammar_validation_performed",
                      "source_fidelity_verified", "qualified", "accepted", "proof_authority", "global_optimality_established"):
            self.assertIs(diagnostic[field], False)
        json.dumps(result, allow_nan=False)

    def test_inputs_are_not_mutated(self):
        starts, ends = fixture()
        before = copy.deepcopy((starts, ends, PRESENT))
        selector.select_joint_spans(starts, ends, PRESENT)
        self.assertEqual((starts, ends, PRESENT), before)

    def test_max_token_limit_rejects_without_truncation(self):
        starts = [[0.] * 257 for _ in range(6)]
        with self.assertRaisesRegex(ValueError, "truncation forbidden"):
            selector.select_joint_spans(starts, starts, PRESENT)

    def test_invalid_head_shapes_and_lengths_reject(self):
        starts, ends = fixture()
        for bad_starts, bad_ends in ((starts[:5], ends), (starts, ends[:5]),
                                     (starts, [row[:2] for row in ends]), ({}, ends),
                                     ([None] + starts[1:], ends), ([], [])):
            with self.subTest(starts=bad_starts):
                with self.assertRaises(ValueError):
                    selector.select_joint_spans(bad_starts, bad_ends, PRESENT)

    def test_presence_schema_and_required_facets_reject(self):
        for bad in (PRESENT[:5], [False] + PRESENT[1:], [True, False] + PRESENT[2:],
                    [1] + PRESENT[1:], None):
            with self.subTest(presence=bad):
                with self.assertRaises(ValueError):
                    selector.select_joint_spans(*fixture(), bad)

    def test_nonfinite_or_non_numeric_logits_reject(self):
        for value in (float("nan"), float("inf"), float("-inf"), True, "1", 10**1000, 1e100):
            starts, ends = fixture()
            starts[5][0] = value
            with self.subTest(value=type(value).__name__):
                with self.assertRaisesRegex(ValueError, "finite float32"):
                    selector.select_joint_spans(starts, ends, PRESENT)

    def test_nonfinite_pair_scores_reject(self):
        starts, ends = fixture()
        starts[0][0], ends[0][0] = 3e38, 3e38
        with self.assertRaisesRegex(ValueError, "nonfinite float32 span pair"):
            selector.select_joint_spans(starts, ends, PRESENT)

    def test_invalid_resource_bounds_reject(self):
        for key, values in (("candidates_per_facet", (1, 65, True, 2.)),
                            ("beam_width", (1, 257, True, 2.)),
                            ("ambiguity_epsilon", (-1, 2, True, float("inf"), float("nan"), 10**1000))):
            for value in values:
                with self.subTest(key=key, value=value):
                    with self.assertRaises(ValueError):
                        selector.select_joint_spans(*fixture(), PRESENT, **{key: value})

    def test_cutoff_tie_is_reported_and_search_marked_incomplete(self):
        starts, ends = [[0.] * 3 for _ in range(6)], [[0.] * 3 for _ in range(6)]
        result = selector.select_joint_spans(starts, ends, PRESENT, candidates_per_facet=2)
        self.assertTrue(result["diagnostics"]["facets"]["actor"]["cutoff_tied"])
        self.assertTrue(result["diagnostics"]["incomplete_search"])

    def test_tied_beam_pruning_boundary_is_reported(self):
        starts, ends = [[0.] * 3 for _ in range(6)], [[0.] * 3 for _ in range(6)]
        result = selector.select_joint_spans(starts, ends, PRESENT, beam_width=2)
        layer = result["diagnostics"]["layers"][0]
        self.assertTrue(layer["beam_boundary_tied"])
        self.assertEqual(layer["retained_cutoff_joint_score"], 0.)
        self.assertEqual(layer["first_pruned_joint_score"], 0.)


if __name__ == "__main__":
    unittest.main()

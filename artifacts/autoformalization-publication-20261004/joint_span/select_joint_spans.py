"""Bounded inference intervention over the frozen decoder's six span heads.

This module imports only the standard library. It does not tokenize, parse law,
choose modality or presence, restore models, read targets, or validate canonical
IR. The caller supplies the existing decoder's fixed presence decisions and
must copy the selected source intervals and run its unchanged grammar validator.

All token-aligned upper-triangular spans are scored with float32-rounded
start+end additions, matching native Torch float32 pair scores. Each facet keeps
at most K candidates; a deterministic beam combines them without token overlap.
The joint objective is math.fsum of the retained float32 pair scores. This is a
new search objective, not the original decoder's confidence measure. Its gap is
conditional on retained complete beam states, and never semantic confidence.
"""
from __future__ import annotations

import heapq
import math
import struct

SCHEMA = "bounded-joint-source-span-selection/v1"
SPAN_FIELDS = ("actor", "action", "object", "conditions", "exceptions", "temporal")
MAX_SOURCE_TOKENS = 256
MAX_CANDIDATES_PER_FACET = 64
MAX_BEAM_WIDTH = 256


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _float32(value):
    _require(type(value) in (int, float), "span logits must be finite float32 numbers")
    try:
        result = struct.unpack("!f", struct.pack("!f", float(value)))[0]
    except (OverflowError, ValueError, struct.error) as error:
        raise ValueError("span logits must be finite float32 numbers") from error
    _require(math.isfinite(result), "span logits must be finite float32 numbers")
    return result


def _pair_score(start, end):
    try:
        value = struct.unpack("!f", struct.pack("!f", start + end))[0]
    except (OverflowError, struct.error) as error:
        raise ValueError("nonfinite float32 span pair score") from error
    _require(math.isfinite(value), "nonfinite float32 span pair score")
    return value


def _validated_heads(start_logits, end_logits, present):
    _require(type(present) in (list, tuple) and len(present) == len(SPAN_FIELDS)
             and all(type(value) is bool for value in present), "six fixed boolean presence decisions required")
    _require(present[0] and present[1], "actor/action presence must remain true")
    _require(type(start_logits) in (list, tuple) and type(end_logits) in (list, tuple)
             and len(start_logits) == len(end_logits) == len(SPAN_FIELDS), "six start/end span heads required")
    _require(type(start_logits[0]) in (list, tuple), "span heads must be lists or tuples")
    size = len(start_logits[0])
    _require(1 <= size <= MAX_SOURCE_TOKENS, "source token count outside [1,256]; truncation forbidden")
    starts, ends = [], []
    for left, right in zip(start_logits, end_logits, strict=True):
        _require(type(left) in (list, tuple) and type(right) in (list, tuple)
                 and len(left) == len(right) == size, "all span heads must match the source token count")
        starts.append([_float32(value) for value in left])
        ends.append([_float32(value) for value in right])
    return starts, ends, size


def _candidates(starts, ends, keep):
    # The native stable argsort sees flattened row-major upper-triangular spans.
    # Source-position keys reproduce that order for equal pair scores.
    values = ((_pair_score(starts[left], ends[right]), left, right)
              for left in range(len(starts)) for right in range(left, len(starts)))
    ranked = heapq.nsmallest(keep + 1, values, key=lambda row: (-row[0], row[1], row[2]))
    retained = ranked[:keep]
    count = len(starts) * (len(starts) + 1) // 2
    return retained, {
        "enumerated_span_count": count,
        "retained_candidate_count": len(retained),
        "pruned_candidate_count": count - len(retained),
        "cutoff_tied": len(ranked) > keep and ranked[keep - 1][0] == ranked[keep][0],
        "retained_cutoff_pair_score": retained[-1][0],
        "first_pruned_pair_score": ranked[keep][0] if len(ranked) > keep else None,
        "greedy_span": [ranked[0][1], ranked[0][2]],
        "greedy_span_pair_score": ranked[0][0],
        "greedy_span_logit_margin": _pair_score(ranked[0][0], -ranked[1][0]) if len(ranked) > 1 else None,
    }


def _state_key(state):
    return (-state[0], tuple((-1, -1) if span is None else span for span in state[3]))


def select_joint_spans(start_logits, end_logits, present, *, candidates_per_facet=16,
                       beam_width=64, ambiguity_epsilon=1e-7):
    """Choose bounded non-overlapping intervals with fixed presence decisions.

    Inputs are six equally sized native head sequences, and six booleans in
    SPAN_FIELDS order. Actor and action must be present. Return selected_spans
    as a six-element list of inclusive [left,right] intervals or None for absent
    facets. An abstention returns selected_spans=None; best-so-far assignments
    are never promoted. Invalid scores, shapes, or bounds raise ValueError.

    A retained complete-assignment tie at or below ambiguity_epsilon abstains.
    Candidate/beam pruning may hide a better assignment or a tie: the returned
    gap is only conditional on the retained complete states. No completeness,
    correctness, qualification, or proof authority follows from selection.
    """
    _require(type(candidates_per_facet) is int and 2 <= candidates_per_facet <= MAX_CANDIDATES_PER_FACET,
             "candidates_per_facet must be an integer in [2,64]")
    _require(type(beam_width) is int and 2 <= beam_width <= MAX_BEAM_WIDTH,
             "beam_width must be an integer in [2,256]")
    _require(type(ambiguity_epsilon) in (int, float) and 0 <= ambiguity_epsilon <= 1
             and math.isfinite(ambiguity_epsilon), "ambiguity_epsilon must be finite in [0,1]")
    starts, ends, size = _validated_heads(start_logits, end_logits, present)
    pools, facets = [], {}
    greedy_occupied = 0
    greedy_overlap_fields = []
    for index, field in enumerate(SPAN_FIELDS):
        if present[index]:
            candidates, diagnostic = _candidates(starts[index], ends[index], candidates_per_facet)
            left, right = diagnostic["greedy_span"]
            bitmask = ((1 << (right - left + 1)) - 1) << left
            if greedy_occupied & bitmask:
                greedy_overlap_fields.append(field)
            greedy_occupied |= bitmask
            pools.append([(score, left, right, ((1 << (right - left + 1)) - 1) << left)
                          for score, left, right in candidates])
        else:
            diagnostic = {"enumerated_span_count": 0, "retained_candidate_count": 0,
                          "pruned_candidate_count": 0, "cutoff_tied": False,
                          "retained_cutoff_pair_score": None, "first_pruned_pair_score": None,
                          "greedy_span": None, "greedy_span_pair_score": None,
                          "greedy_span_logit_margin": None}
            pools.append([])
        facets[field] = {"present": present[index], **diagnostic}

    # States: total score, selected pair scores, occupied bitmask, intervals.
    states = [(0.0, (), 0, ())]
    attempted = conflicts = beam_pruned = 0
    layers = []
    for index, field in enumerate(SPAN_FIELDS):
        expanded = []
        before = len(states)
        before_attempted, before_conflicts = attempted, conflicts
        for _, pair_scores, occupied, intervals in states:
            if not present[index]:
                attempted += 1
                expanded.append((math.fsum(pair_scores), pair_scores, occupied, intervals + (None,)))
                continue
            for score, left, right, bitmask in pools[index]:
                attempted += 1
                if occupied & bitmask:
                    conflicts += 1
                    continue
                scores = pair_scores + (score,)
                expanded.append((math.fsum(scores), scores, occupied | bitmask,
                                 intervals + ((left, right),)))
        ranked = sorted(expanded, key=_state_key)
        discarded = max(0, len(ranked) - beam_width)
        beam_pruned += discarded
        states = ranked[:beam_width]
        layers.append({"field": field, "input_state_count": before,
                       "attempted_expansion_count": attempted - before_attempted,
                       "overlap_rejected_expansion_count": conflicts - before_conflicts,
                       "feasible_expanded_state_count": len(ranked),
                       "retained_state_count": len(states), "pruned_state_count": discarded,
                       "retained_cutoff_joint_score": states[-1][0] if states else None,
                       "first_pruned_joint_score": ranked[beam_width][0] if discarded else None,
                       "beam_boundary_tied": bool(discarded and ranked[beam_width - 1][0] == ranked[beam_width][0])})
        if not states:
            break

    candidate_pruned = sum(row["pruned_candidate_count"] for row in facets.values())
    diagnostics = {
        "token_count": size, "candidates_per_facet": candidates_per_facet, "beam_width": beam_width,
        "ambiguity_epsilon": ambiguity_epsilon, "pair_score_arithmetic": "round_each_start_plus_end_to_float32/v1",
        "joint_objective": "math_fsum_of_present_facet_float32_pair_scores/v1",
        "facet_order": list(SPAN_FIELDS), "fixed_presence": list(present), "facets": facets, "layers": layers,
        "attempted_expansion_count": attempted, "overlap_rejected_expansion_count": conflicts,
        "expansion_count_upper_bound": len(SPAN_FIELDS) * beam_width * candidates_per_facet,
        "enumerated_span_count_upper_bound": len(SPAN_FIELDS) * size * (size + 1) // 2,
        "native_head_value_count": len(SPAN_FIELDS) * size * 2,
        "peak_feasible_expanded_state_count": max(layer["feasible_expanded_state_count"] for layer in layers),
        "pruned_candidate_count": candidate_pruned, "pruned_beam_state_count": beam_pruned,
        "incomplete_search": bool(candidate_pruned or beam_pruned),
        "global_optimality_established": False, "confidence_scope": "retained_complete_beam_only",
        "greedy_overlap_fields": greedy_overlap_fields, "complete_retained_state_count": len(states),
        "target_access": False, "teacher_forcing": False, "training_executed": False,
        "grammar_validation_performed": False, "source_fidelity_verified": False,
        "qualified": False, "accepted": False, "proof_authority": False,
    }
    if not states:
        return {"schema": SCHEMA, "status": "abstained",
                "reason": "no_complete_assignment_in_retained_candidates", "selected_spans": None,
                "best_score": None, "runner_up_score": None, "joint_score_margin": None,
                "diagnostics": diagnostics}
    best = states[0][0]
    second = states[1][0] if len(states) > 1 else None
    margin = best - second if second is not None else None
    ambiguous = margin is not None and margin <= ambiguity_epsilon
    return {"schema": SCHEMA, "status": "abstained" if ambiguous else "selected",
            "reason": "ambiguous_joint_scores" if ambiguous else None,
            "selected_spans": None if ambiguous else [list(span) if span is not None else None for span in states[0][3]],
            "best_score": best, "runner_up_score": second, "joint_score_margin": margin,
            "diagnostics": diagnostics}

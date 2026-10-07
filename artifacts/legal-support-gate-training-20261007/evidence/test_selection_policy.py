"""Pure decision fixtures; no Torch, model, source targets or resource clients."""
import copy
import importlib.util
from pathlib import Path
import sys

import pytest

_spec = importlib.util.spec_from_file_location(
    '_pure_support_gate_selection', Path(__file__).with_name('selection_policy.py'))
policy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(policy)


def summary(**changes):
    # Illustrative counts only; the actual parent baseline is measured prefit.
    result = dict(positive_count=64, negative_count=64, positive_exact_count=20,
        positive_emitted_proposal_count=40, positive_learned_refusal_count=16,
        negative_learned_refusal_count=50, negative_emitted_proposal_count=12)
    result.update(changes)
    return result


def candidate(step, counts):
    return dict(completed_updates=step, summary=counts,
                checkpoint={'identity': 'actual-snapshot-' + str(step)})


def test_more_positive_correctness_cannot_buy_more_negative_emissions():
    baseline = summary()
    unsafe = summary(positive_exact_count=40, positive_emitted_proposal_count=50,
        positive_learned_refusal_count=8, negative_emitted_proposal_count=13,
        negative_learned_refusal_count=49)
    fallback = candidate(0, baseline)
    assert not policy.eligible(unsafe, baseline)
    assert policy.select([fallback, candidate(120, unsafe)], baseline) is fallback


def test_reject_all_is_ineligible_despite_best_negative_emission_rank():
    baseline = summary()
    reject_all = summary(positive_exact_count=0, positive_emitted_proposal_count=0,
        positive_learned_refusal_count=64, negative_emitted_proposal_count=0,
        negative_learned_refusal_count=64)
    assert policy.rank(reject_all, 120) > policy.rank(baseline, 0)
    assert not policy.eligible(reject_all, baseline)
    fallback = candidate(0, baseline)
    assert policy.select([fallback, candidate(120, reject_all)], baseline) is fallback


@pytest.mark.parametrize('change', [
    dict(positive_exact_count=19),
    dict(positive_emitted_proposal_count=39),
    dict(positive_learned_refusal_count=17),
])
def test_each_positive_floor_rejects_an_otherwise_safe_count_change(change):
    assert not policy.eligible(summary(**change), summary())


def test_fewer_negative_emissions_outrank_larger_positive_gain():
    baseline = summary()
    safer = candidate(120, summary(negative_emitted_proposal_count=11))
    larger_gain = candidate(240, summary(positive_exact_count=40))
    assert policy.select([candidate(0, baseline), safer, larger_gain], baseline) is safer


def test_whole_then_learned_negative_refusal_then_earlier_update_rank():
    baseline = summary()
    assert policy.rank(summary(positive_exact_count=21), 240) > policy.rank(baseline, 0)
    assert policy.rank(summary(negative_learned_refusal_count=51), 240) > policy.rank(baseline, 0)
    earlier = candidate(120, summary(positive_exact_count=21, negative_learned_refusal_count=51))
    later = candidate(240, copy.deepcopy(earlier['summary']))
    assert policy.select([candidate(0, baseline), earlier, later], baseline) is earlier


def test_step_zero_is_exact_checkpoint_fallback_without_input_mutation():
    baseline = summary()
    fallback = candidate(0, baseline)
    rows = [fallback, candidate(120, summary(positive_exact_count=19)),
            candidate(240, summary(negative_emitted_proposal_count=13,
                                   negative_learned_refusal_count=49))]
    before = copy.deepcopy(rows)
    assert policy.select(rows, baseline) is fallback
    assert rows == before
    assert policy.select([fallback], baseline) is fallback


@pytest.mark.parametrize('baseline', [
    summary(positive_exact_count=0),
    summary(positive_exact_count=0, positive_emitted_proposal_count=0,
            positive_learned_refusal_count=64),
])
def test_nonzero_baseline_emission_and_whole_required_before_fit(baseline):
    with pytest.raises(ValueError, match='nonzero baseline'):
        policy.eligible(baseline, baseline)


@pytest.mark.parametrize('changes', [
    dict(negative_emitted_proposal_count=True),
    dict(positive_exact_count=20.0),
    dict(negative_learned_refusal_count=-1),
    dict(positive_exact_count=41),
    dict(positive_learned_refusal_count=25),
    dict(negative_learned_refusal_count=53),
    dict(positive_structural_block_count=7),
    dict(negative_incidental_block_count=1),
    dict(case_count=127),
    dict(negative_count=0, negative_emitted_proposal_count=0,
         negative_learned_refusal_count=0),
])
def test_impossible_or_noninteger_counts_are_rejected(changes):
    with pytest.raises(ValueError):
        policy.eligible(summary(**changes), summary())


def test_changed_cohort_denominators_are_rejected():
    with pytest.raises(ValueError, match='denominators'):
        policy.eligible(summary(negative_count=65), summary())


def test_measured_baseline_and_ordered_actual_updates_are_mandatory():
    baseline = summary()
    for rows in [[], [candidate(120, baseline)],
                 [candidate(False, baseline)], [candidate(0.0, baseline)],
                 [candidate(0, summary(positive_exact_count=21))],
                 [candidate(0, baseline), candidate(0, baseline)],
                 [candidate(0, baseline), candidate(240, baseline), candidate(120, baseline)]]:
        with pytest.raises(ValueError):
            policy.select(rows, baseline)
    for steps in [-1, True, 1.0, 10_000_001]:
        with pytest.raises(ValueError, match='update count'):
            policy.rank(baseline, steps)


def test_complete_score_status_partitions_validate_and_no_model_imports():
    complete = summary(positive_structural_block_count=8,
                       negative_incidental_block_count=2, case_count=128)
    assert policy.eligible(complete, complete)
    assert not any(name == 'torch' or name.startswith('torch.')
                   or name == 'ipfs_datasets_py' or name.startswith('ipfs_datasets_py.')
                   for name in sys.modules)
